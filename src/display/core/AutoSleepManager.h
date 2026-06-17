#ifndef AUTOSLEEPMANAGER_H
#define AUTOSLEEPMANAGER_H

#include <cstdint>

#include "constants.h"

// [display-auto-sleep] Display-only policy deciding when the screen should enter
// deep sleep. This is pure logic with NO hardware access and NO BLE/controller
// writes, so it also compiles and runs in the simulator and is easy to reason about.
//
// Two independent reasons, each with its own enable flag + timeout:
//   * NoController - the GaggiMate Controller (PCB) has been unreachable over BLE
//     for N ms. Touch does NOT block this countdown.
//   * Idle - the controller IS connected but the screen has not been touched for
//     M ms and no brew/steam/grind process is running (the boiler may still be
//     hot). Touch resets this idle countdown; an active process blocks it.
// Sleep is suppressed (both reasons) while OTA / firmware update / autotune is in
// progress.
class AutoSleepManager {
  public:
    enum class SleepReason { None, NoController, Idle };

    void setEnabled(bool enabled) { enabled_ = enabled; }
    bool isEnabled() const { return enabled_; }

    void setTimeoutMs(uint32_t timeoutMs) { timeoutMs_ = timeoutMs; }
    uint32_t timeoutMs() const { return timeoutMs_; }

    // [display-auto-sleep] Idle-while-connected policy (independent of the
    // no-controller one above). Sleeps after idleTimeoutMs_ of no touch while the
    // controller is connected and the machine is not busy.
    void setIdleEnabled(bool enabled) { idleEnabled_ = enabled; }
    bool isIdleEnabled() const { return idleEnabled_; }

    void setIdleTimeoutMs(uint32_t timeoutMs) { idleTimeoutMs_ = timeoutMs; }
    uint32_t idleTimeoutMs() const { return idleTimeoutMs_; }

    // True while a brew/steam/grind (or any other active) process is running, or
    // the machine is in a mode that drives the boiler on demand (steam/water).
    // Blocks idle-while-connected sleep so the screen stays on during use.
    void setMachineBusy(bool busy) { machineBusy_ = busy; }
    bool isMachineBusy() const { return machineBusy_; }

    // Temporarily block sleeping (OTA / update / Wi-Fi AP setup / web management).
    void setSuppressed(bool suppressed) { suppressed_ = suppressed; }
    bool isSuppressed() const { return suppressed_; }

    // When true and the controller is absent, sleep after a quarter of the timeout
    // (used when the battery is critically low). Display-only behaviour.
    void setForceShortTimeout(bool force) { forceShortTimeout_ = force; }

    bool isControllerConnected() const { return controllerConnected_; }
    uint32_t controllerDisconnectedSince() const { return controllerDisconnectedSince_; }

    // Begin with no connection yet (start the countdown at boot). A dedicated
    // "counting" flag tracks whether the timer is active, so the timestamp is a
    // plain value (no 0->1 coercion) and `now - controllerDisconnectedSince_`
    // can never underflow at now == 0 / the millis() wrap edge.
    void begin(uint32_t now) {
        controllerConnected_ = false;
        controllerDisconnectedSince_ = now;
        disconnectCountdownActive_ = true;
        lastUserInteractionAt_ = now;
    }

    void onControllerConnected(uint32_t now) {
        controllerConnected_ = true;
        lastControllerConnectedAt_ = now;
        disconnectCountdownActive_ = false; // cancel the countdown
        controllerDisconnectedSince_ = 0;
    }

    void onControllerDisconnected(uint32_t now) {
        // Only (re)start the countdown on a real transition, so repeated
        // "waiting" events don't keep pushing the deadline forward.
        if (controllerConnected_ || !disconnectCountdownActive_) {
            controllerDisconnectedSince_ = now;
            disconnectCountdownActive_ = true;
        }
        controllerConnected_ = false;
    }

    // Resets the UI idle timer only; does NOT block no-controller sleep.
    void onUserInteraction(uint32_t now) { lastUserInteractionAt_ = now; }
    uint32_t lastUserInteractionAt() const { return lastUserInteractionAt_; }

    // Returns why the display should sleep right now, or None.
    SleepReason evaluate(uint32_t now) const {
        if (suppressed_) {
            return SleepReason::None;
        }
        // No-controller: the PCB has been unreachable for the whole timeout.
        if (enabled_ && !controllerConnected_ && disconnectCountdownActive_) {
            const uint32_t timeout = forceShortTimeout_ ? (timeoutMs_ / 4) : timeoutMs_;
            if (now - controllerDisconnectedSince_ >= timeout) {
                return SleepReason::NoController;
            }
        }
        // Idle-while-connected: connected, not busy, untouched for the whole timeout.
        if (idleEnabled_ && controllerConnected_ && !machineBusy_ && lastUserInteractionAt_ != 0) {
            const uint32_t timeout = forceShortTimeout_ ? (idleTimeoutMs_ / 4) : idleTimeoutMs_;
            if (now - lastUserInteractionAt_ >= timeout) {
                return SleepReason::Idle;
            }
        }
        return SleepReason::None;
    }

    static const char *reasonName(SleepReason r) {
        switch (r) {
        case SleepReason::NoController:
            return "NO_CONTROLLER";
        case SleepReason::Idle:
            return "IDLE";
        default:
            return "NONE";
        }
    }

  private:
    bool enabled_ = DEFAULT_AUTO_SLEEP_NO_CONTROLLER;
    bool idleEnabled_ = DEFAULT_AUTO_SLEEP_IDLE;
    bool suppressed_ = false;
    bool forceShortTimeout_ = false;
    bool controllerConnected_ = false;
    bool machineBusy_ = false;
    bool disconnectCountdownActive_ = false;
    uint32_t timeoutMs_ = DEFAULT_NO_CONTROLLER_SLEEP_TIMEOUT_MS;
    uint32_t idleTimeoutMs_ = DEFAULT_IDLE_SLEEP_TIMEOUT_MS;
    uint32_t controllerDisconnectedSince_ = 0;
    uint32_t lastControllerConnectedAt_ = 0;
    uint32_t lastUserInteractionAt_ = 0;
};

#endif // AUTOSLEEPMANAGER_H
