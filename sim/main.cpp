// Desktop simulator entry point. Runs the real display Controller on a single
// cooperative loop on the main thread (LVGL/SDL must stay on the main thread on
// macOS), driving the firmware's loop methods directly since the FreeRTOS tasks
// are no-ops in the simulator.
#include "ESPAsyncWebServer.h"
#include "SdlDriver.h"
#include <Arduino.h>
#include <cstdlib>
#include <cstring>
#include <display/core/Controller.h>
#include <display/plugins/ShotHistoryPlugin.h>
#include <display/ui/default/DefaultUI.h>
#include <display/ui/default/lvgl/ui.h>

// The generated UI event handlers reference this global (see main.h on device).
Controller controller;

int main(int argc, char **argv) {
    // Optional: `--screenshot <path> [delayMs]` renders for a bit, saves a BMP, exits.
    const char *shotPath = nullptr;
    unsigned long shotDelayMs = 4000;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--screenshot") == 0 && i + 1 < argc) {
            shotPath = argv[++i];
            if (i + 1 < argc)
                shotDelayMs = strtoul(argv[i + 1], nullptr, 10);
        }
    }

    controller.setup(); // builds the UI, installs the SDL driver, marks screen ready

    // The sim has a real network (the WebUI is reachable), so present as Wi-Fi
    // connected: seeding credentials sends setupWifi() down the STA path, and the
    // WiFi shim's begin() reports WL_CONNECTED. This makes the standby screen show
    // the clock and Wi-Fi icon (and avoids captive-portal AP mode). Seed only once.
    Settings &settings = controller.getSettings();
    if (settings.getWifiSsid().isEmpty())
        settings.setWifiSsid("GaggiMate-Sim");
    if (settings.getWifiPassword().isEmpty())
        settings.setWifiPassword("simulator");

    SdlDriver *drv = SdlDriver::getInstance();
    DefaultUI *ui = controller.getUI();
    const unsigned long start = millis();
    bool shotTaken = false;

    // Dev aid (sim only): GM_SIM_SCREEN=brew|steam|water|menu jumps to that control
    // screen ~1.5 s after boot so UI work can be screenshotted without touch input.
    const char *forceScreen = getenv("GM_SIM_SCREEN");
    bool screenForced = false;

    while (!drv->shouldQuit()) {
        if (forceScreen && !screenForced && ui && millis() - start >= 1500) {
            screenForced = true;
            if (strcmp(forceScreen, "steam") == 0) {
                controller.setMode(MODE_STEAM);
                ui->changeScreen(&ui_SimpleProcessScreen, &ui_SimpleProcessScreen_screen_init);
            } else if (strcmp(forceScreen, "water") == 0) {
                controller.setMode(MODE_WATER);
                ui->changeScreen(&ui_SimpleProcessScreen, &ui_SimpleProcessScreen_screen_init);
            } else if (strcmp(forceScreen, "menu") == 0) {
                ui->changeScreen(&ui_MenuScreen, &ui_MenuScreen_screen_init);
            } else if (strcmp(forceScreen, "status") == 0) {
                controller.setMode(MODE_BREW);
                controller.activate(); // start a brew -> transitions to StatusScreen
            } else { // "brew"
                controller.setMode(MODE_BREW);
                ui->changeScreen(&ui_BrewScreen, &ui_BrewScreen_screen_init);
            }
            // GM_SIM_ACTIVE=1 starts the process so active-only widgets (e.g. the
            // steam swirl goButton, shown only while steaming) become visible.
            if (getenv("GM_SIM_ACTIVE")) {
                controller.activate();
            }
        }
        controller.loop();      // connection lifecycle, comms pump, plugins
        controller.loopLogic(); // process + control logic (normally a FreeRTOS task)

        // Shot history sampling normally runs in its own FreeRTOS task (a no-op in
        // the sim), so drive record() here at its native cadence.
        {
            static unsigned long lastShotSample = 0;
            if (millis() - lastShotSample >= SHOT_LOG_SAMPLE_INTERVAL_MS) {
                lastShotSample = millis();
                ShotHistory.record();
            }
        }

        if (ui) {
            ui->loop();
            ui->loopProfiles();
        }
        gm_web_pump(); // service the embedded WebUI HTTP/WS server

        // Settings persistence normally runs in a deferred save task (a no-op in the
        // sim), so flush dirty settings to NVS periodically. save(true) is a cheap
        // no-op when nothing changed.
        {
            static unsigned long lastSave = 0;
            if (millis() - lastSave >= 2000) {
                lastSave = millis();
                controller.getSettings().save(true);
            }
        }

        drv->pumpAndRender();

        if (shotPath && !shotTaken && millis() - start >= shotDelayMs) {
            drv->screenshot(shotPath);
            shotTaken = true;
            break;
        }
        delay(5);
    }
    return 0;
}
