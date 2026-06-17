# HANDOFF — GaggiMate T-RGB 显示屏固件改造（自用 fork 维护交接）

> 给**接手维护的新对话/工程师**。本文件力求自包含,读完即可上手。
> 配套参考:仓库根 `README.md` 末尾「本地改动 & 实施计划」节。
> 语言约定:中文沟通,技术术语保留英文。

---

## 0. 一句话概括
给 GaggiMate(开源 Gaggia 咖啡机控制器项目)的 **LilyGo T-RGB 显示屏**做了几个 **display-only** 改造(无 WiFi 自动休眠/触摸唤醒、电池显示、开机动画、恢复冲煮 profile),并修复了一连串问题(黑屏、主控版本不匹配、网页 UI 白屏、配 WiFi)。**原则:只改显示屏侧;controller 用同仓库的官方代码刷,只为对齐通信协议版本。**

## 1. 仓库 & 环境
- Fork:`dmq1219/gaggimate`,分支 `feature/display-auto-sleep-battery`,基于 upstream `jniebuhr/gaggimate` 的 master。上游 PR:https://github.com/jniebuhr/gaggimate/pull/773
- 工作目录:`~/Desktop/gaggiamate 自动关机` **(目录名带空格!部分脚本/sim 对空格敏感)**

## 2. 硬件（刷写前务必按 MAC 区分两块板！）
| 板 | 型号 | MAC | Flash/PSRAM | 备注 |
|---|---|---|---|---|
| **Display** | LilyGo T-RGB(ESP32-S3,480×480 圆屏,CST820 触摸) | `68:ee:8f:46:a7:80` | 16MB / 8MB | 我们改的就是这块 |
| **Controller** | GaggiMate Pro Rev 1.1(ESP32-S3) | `a8:46:74:92:60:24` | 8MB / 2MB | proto 3,带压力+调光;跑官方代码 |

- 机器:Gaggia Classic Pro。
- **两块板都枚举成 `/dev/cu.usbmodem*`(2301/2401 编号不固定)**。刷任何东西前先 `esptool flash_id` 读 MAC 认准目标板 —— **曾误把 controller 固件刷到 display 板 → 黑屏**(可重刷 display 固件救回)。

## 3. 构建 / 刷写（关键坑，务必看）
- **必须用 Python 3.11 的 pio**:`/opt/homebrew/bin/python3.11 -m platformio run -e display`。系统默认 `pio` 跑在 3.9,前置脚本用了 `datetime.UTC` 会直接崩。
- **改了 `src/display/lv_conf.h`(字体/`LV_USE_GIF` 等)后**:PlatformIO 不会重编 LVGL → 必须 `rm -rf .pio/build/display/libb3a/lvgl` 再 build,否则链接报 `undefined reference` 或行为不更新。
- **改了网页包(`web/` 源码)后**:`scripts/embed_webui.py` 不被 SCons 当依赖追踪 → 见 §5「网页白屏」;纯 C++/lv_conf 改动不需要重跑 `build_webui.sh`。
- 刷写:`... -m platformio run -e display -t upload --upload-port <display口>`(先按 MAC 认准)。
- **显示屏没连 controller 时约 1–2 分钟自动深睡 → USB 串口消失**。刷/读串口前点屏唤醒(=重启,约 12 秒重连 WiFi);彻底刷不进时用下载模式(按住 BOOT/IO0 + 点 RST/EN + 松 BOOT)。
- 整片擦除(`-t erase`)后第一次 upload 常报 `No serial data received`(S3 重新枚举)→ 重试一次即可。

## 4. 已实现的功能（均 display-only，我们加的）
1. **无 controller 自动深睡 + 触摸唤醒** — `src/display/core/AutoSleepManager.h`(纯逻辑)+ `DefaultUI::tickAutoSleep()`(接线,~第 368 行)。蓝牙连不上 controller 超过 `noControllerSleepTimeout`(默认 120s)→ `panelDriver->sleep()`(ESP32 深睡,ext1/GPIO1 接 CST820 INT,唤醒=重启)。**计时只看蓝牙连接状态**,与触摸/动画/屏幕活动无关。**已去掉 AP 模式拦截**(没配 WiFi 也能睡),仅 OTA 升级/PID 自整定时不睡。设置:`autoSleepNoController`(开关)、`noControllerSleepTimeout`。蓝牙事件接线在 `DefaultUI.cpp` ~156–182。
   **【新增 idle-sleep-while-connected】** 即使 controller 连着:屏幕超过 `idleSleepTimeout`(默认 120s)没被触摸、且没有进行中的进程(`controller->isActive()` —— 萃取/蒸汽/研磨/热水)→ 同样深睡。**热的空闲锅炉(MODE_BREW 待命)也算空闲、会睡**;只有进行中的进程,或 STEAM/WATER 模式(锅炉按需驱动)阻止睡。触摸重置空闲计时(走 LVGL `lv_disp_get_inactive_time`)。两套策略(无主控 / 连着但空闲)各自独立开关+超时,共用 `AutoSleepManager`(`SleepReason::NoController` / `Idle`)。设置:`autoSleepIdle`(开关)、`idleSleepTimeout`。
2. **电池显示** — `src/display/core/BatteryMonitor.h`(读 GPIO4 分压 ADC,**无电量计 IC**;% 走分段 LUT;充电=电压≥4200mV 的启发式判断,无充电状态引脚)。叠加层 `DefaultUI::setupBatteryOverlay()`,`lv_layer_top()` 顶部居中,**字体 Montserrat 20**(曾放大到 42,后按要求缩小一半)。阈值在 `constants.h`。
3. **开机/待机动画** — `ui_StandbyScreen` 的 logo 对象改用 `lv_gif` 播「咖啡豆抛接」GIF(替换 GaggiMate logo,居中、~半屏)。`lv_conf` 开 `LV_USE_GIF`;素材内嵌 `src/display/ui/default/lvgl/images/ui_img_coffee_anim.c`(240×228 循环 GIF,`lv_img_dsc` cf=RAW);`ui.h` 有 `LV_IMG_DECLARE(ui_img_coffee_anim)`。源素材 6 帧 PNG 在 `~/Documents/家庭管理/coffee_bean_animation_large/`(抠浅灰底→合成到深背景 `0x131313`→GIF)。
4. **恢复 5 个冲煮 profile** — `data/p/*.json`(9bar / Adaptive v2 / Cremina lever / Damian's LM Leva / Backflush)。**无秤版**:出液停止条件由「克数 volumetric」改成「泵水量 pumped ml」(用户没有蓝牙秤)。原始未改版备份在 `data_p_orig_backup/`。这些经 `uploadfs` 写入 display 的 LittleFS `/p/`,固件 migrate 自动收藏后显示。
5. **模式选择器 UI 改造(mode-selector)** — 解决「分不清当前在哪个模式 / 是在调还是已选中」。控制屏上方:**当前模式 = 居中彩色胶囊**(Brew=琥珀 `0xB0651A` / Steam=红 `0xE5392A` / Water=蓝 `0x1EA6FF`),**另两个模式 = 两旁可点标签**(固定排序 Steam<Water<Brew,低序在左、高序在右);**点旁标直接切到那个模式**(`onModeSelect`)。**防误触**:`onModeSelect` 开头有 `if (controller.isActive()) return;` —— 冲煮/蒸汽/出水**进行中时旁标点击被忽略**,不会误取消当前进程并切模式;要中止改用 chevron/菜单(那是有意操作,会 deactivate)。出现在全部 4 个模式屏:Brew 调参(BrewScreen)、冲煮中(StatusScreen)、Steam/Water(SimpleProcessScreen)。**Grind 已从菜单/选择器去掉**(GrindScreen 及研磨逻辑保留,菜单按钮永久隐藏,flex 自动重排为 3 键);选择器只在 Brew/Steam/Water 间循环。StatusScreen 还把温度行/INFUSION/阶段名整体下移腾出胶囊位(阶段名 phaseLabel 保留)。
   - 关键文件:复用助手 `ui_create_mode_pill/ui_create_mode_flank` + `onModeSelect` 在 `lvgl/ui_events.{cpp,h}`(无新文件,走 `extern "C"` 供生成的 C 屏调用);驱动 `DefaultUI.cpp::applyModeSelector` + 4 个 `effect_mgr` 反应式(每屏一个,依赖 `&mode`);各屏在 `_screen_init` 建 3 个对象 `*_modePill/_modeLeft/_modeRight`(替换原 `mainLabel3/5`)。颜色/排序都在 `DefaultUI.cpp` 的 `modeSelectorName/modeSelectorColor`。
   - **生成屏文件(`lvgl/screens/ui_*.c`)不要跑 clang-format**(`scripts/format.sh` 本就排除 `src/display/ui/**`;SquareLine 是宽行风格)。改动只手填,保持原风格。
   - **模拟器看图**:`sim/main.cpp` 加了 dev-only 钩子 `GM_SIM_SCREEN=brew|steam|water|status|menu`(开机 ~1.5s 跳到该屏)+ `GM_SIM_ACTIVE=1`(顺带 `activate()` 启动进程,让"只在活动时显示"的控件出现 —— 如**蒸汽 swirl goButton**)。仅 sim、不进设备固件。因目录带空格,sim 要从无空格副本构建:见 `/tmp/simshot.sh`(rsync→build→截图)。
   - 注:`_ui_flag_modify(obj, HIDDEN, value)` 的 value 是「**可见吗?**」(`_UI_MODIFY_FLAG_ADD==0`→加 HIDDEN=隐藏;1→清=显示)。原版蒸汽屏的 swirl goButton 只在 active 时显示、冷态隐藏 —— 现已被下面的「扭旋钮」GIF **取代**(见 §4.6)。
6. **蒸汽屏「扭旋钮」动画(steam-anim)** — Steam 模式机器自动加温到设定温(~145°C),原界面不直观。现 Steam 屏底部放一个**旋钮逆时针转动 + 虚线箭头**的循环 GIF,提示去扭机器上的蒸汽旋钮。
   - 素材 `src/display/ui/default/lvgl/images/ui_img_steam_knob_anim.c`(130×130,24 帧,`lv_img_dsc` cf=RAW,预合成到 0x131313);生成脚本 `scripts/make_steam_knob_gif.py`(Pillow,尺寸/帧数/速度可调,跑完写 `KNOB_C_OUT` 指定的 .c)。`ui.h` 加 `LV_IMG_DECLARE(ui_img_steam_knob_anim)`。
   - `ui_SimpleProcessScreen` 加 `steamKnob`(`lv_gif`,居中 y=108,默认隐藏);`DefaultUI` 反应式:**steam 模式显示旋钮 GIF、隐藏 goButton**;water 模式反之(显示 ▶ 启停键)。所以蒸汽屏不再有 swirl 键。
   - **坑(露方块)**:GIF 背景必须过 RGB565 后 = 屏幕背景。屏幕画 `0x131313`→565→`(16,16,16)`;但 Pillow 量化会把背景从 `(19,19,19)` 挪到 `(14,14,14)`→565→`(8,12,8)`,露出一个浅方块。脚本里**强制把背景调色板项设回 `(19,19,19)`** 解决。换主题色/背景色时要同步改。
7. **冲煮 / 热水按键动画(brew-anim / water-anim)** — Brew 屏的播放三角 ▶ 换成**咖啡机出液到两只杯子**的 3 帧循环 GIF;Water 屏的 ▶ 换成**玻璃杯接水(蓝水+水流)**的 3 帧循环 GIF(空闲也轮播)。两者**同高 128px**(原三角 40px,brew 先做 64 后按需求×2)。
   - 素材源 `brew button animation.pdf`(黑咖啡机+青杯,**白底**)、`water animation.pdf`(青杯+蓝水,**黑底**)。生成脚本 `scripts/make_brew_button_gif.py`(灰度像素**亮度反相**:白纸→深背景、黑咖啡机→白;彩色保留)、`scripts/make_water_button_gif.py`(按**饱和度**裁内容,**不饱和像素(黑/白)→深背景**、青/蓝保留)。两脚本都:裁同一 bbox 防抖、降采样平滑、**强制背景调色板项=`(19,19,19)`** 防方块;`TARGET_H` 环境变量可调(默认 128)。素材 `images/ui_img_{brew,water}_pour_anim.c`(cf=RAW)。
   - 实现:`ui_BrewScreen_startButton`、`ui_SimpleProcessScreen_waterAnim` 都是 **`lv_gif` + `CLICKABLE`**。Brew:变量名沿用 startButton,点=冲煮(`onBrewStart`)/长按=反冲(`onFlush`),y=112。Water:新 `waterAnim`,点=启停热水(走 `ui_event_SimpleProcessScreen_goButton`→`onSimpleProcessToggle`),y=110。`DefaultUI` 的 SimpleProcessScreen 反应式现在:**steam→显示 steamKnob、water→显示 waterAnim、goButton 永久隐藏**(两模式都用 GIF 了)。`ui.h` 加两个 `LV_IMG_DECLARE`。

## 5. 关键修复（本次会话）
- **网页 UI / 配网页白屏(真根因)**:固件里嵌的网页包 `gWebUiBlobStart` 曾只有 **1 字节空壳** —— PlatformIO **不追踪 `.incbin` 依赖**,`web_ui_blob.S.o` 在空占位阶段编过后没随真 `web_ui.bin` 重编。设备按清单偏移读 → 读到隔壁 flash 垃圾 → 浏览器 `ERR_CONTENT_DECODING_FAILED`。**网页包/服务器/传输本身都没问题**(早先「热点截断」判断是错的)。修复:删 `web_ui_blob.S.o` 重编 + **`scripts/embed_webui.py` 已加"包大小+sha256 指纹"注释**,包一变 `.S` 就变 → 强制重编,永久防回归。判定方法:`nm firmware.elf | grep gWebUiBlob` 看 End−Start≈437748。
- **主控连不上 / "Version mismatch, update controller"**:显示屏靠 service-UUID `e75bc5b6-ff6e-4337-9d31-0c128f2e6e68` 扫描连 controller,**不存地址/不配对**。mismatch = `PROTOCOL_VERSION`(`lib/NanoPbComm/src/Protocol.h`,本 master=3)两端不一致。修:从**同一仓库**编 controller 固件刷主控(`pio run -e controller -t upload`)→ proto 对齐。本 fork 没改 controller 代码(`git diff upstream/master -- src/controller lib/` 为空)。
- **WiFi**:配网页当时白屏,曾在 `Controller::connect()` 一次性 seed 家庭 WiFi 写入 NVS,**明文凭据已从源码删除**(NVS 已持久化)。设备现 `192.168.0.36` @ SSID "Deng wifi 24"。网页 UI 现可从家庭网络打开。NVS 被清空时,(已修好的)配网页可正常设 WiFi。

## 6. ⚠️ 设置接口的坑（很重要，别再踩）
`POST /api/settings` 里**复选框类字段用「出现=true，不出现=false」**(`request->hasArg`,见 `WebUIPlugin.cpp` handleSettings ~629–705)。**只发部分字段的 POST 会把没带上的复选框全部置成 false!** 受影响:`autoSleepNoController` / `autoSleepIdle` / `delayAdjust` / `clock24hFormat` / `autowakeupEnabled` / `homekit` / `boilerFillActive` / `smartGrindActive` / `homeAssistant` / `momentaryButtons`。
→ **改设置请优先用网页 UI**(它提交时一次发齐全部字段);若用 API,**必须带齐所有"该开"的复选框**。

## 7. 当前状态 & 待办（OPEN ITEMS）
- ✅ 网页 UI 已修好,可从 `http://192.168.0.36` 打开(需连 "Deng wifi 24")。
- ✅ 锅炉空闲自动待机(原机自带 `standbyTimeout`)= **600s(10min)**(本来是 15min,按需求改的;停加热)。
- ✅ 用户已在网页重新打开 **`autoSleepNoController`**;`noControllerSleepTimeout` 设为 **60s**。
- ⚠️ **待恢复**(被 §6 接口坑误关、默认本应为 `true`):**`delayAdjust`** 和 **`clock24hFormat`**。用网页打开即可,或发一条带齐所有该开复选框的 POST。其余被一起置 false 的(homekit/boilerFill/smartGrind/homeAssistant/autowakeup/momentaryButtons)默认本就是 false,无需管。
- 🔋 **电池过夜掉电异常待复测**:实测过夜 1000mAh@3.7V 从 88% → 62%(~26%)。**极可能是因为那晚自动休眠被误关、屏整夜没深睡**(亮/半亮态 ~几十 mA)。真深睡应是 µA 级,过夜只掉几 %。**自动休眠已重新打开 → 请重新过夜复测**;若仍异常,再查:深睡是否真进入(关机器后串口/USB 是否在 60s 后掉)、CST820 唤醒电路、WiFi 是否保持唤醒。
- ✅ **已实现「机器开着但闲置也让屏睡」(idle-sleep-while-connected)**:连着 controller 时,屏幕 `idleSleepTimeout`(**默认 120s**)没被触摸、且无进行中进程 → 深睡。**热的空闲锅炉(MODE_BREW 待命)也睡**;萃取/蒸汽/研磨/热水进行中、STEAM/WATER 模式不睡。设置 `autoSleepIdle` / `idleSleepTimeout`(网页 UI:Display Settings → Auto Sleep,默认开)。实现:`AutoSleepManager` 加 `SleepReason::Idle` + `setIdleEnabled/setIdleTimeoutMs/setMachineBusy`;接线在 `DefaultUI::tickAutoSleep()`。已编译通过(`pio run -e display`),网页包已重嵌并入固件。**待真机复测**:① 触摸是否重置计时;② 蒸汽/热水进行中不被误睡;③ 连着过夜的电流(深睡应 µA 级)。

## 8. 备份 / 安全网
- `display_flash_backup.bin` —— display 整片 16MB flash 备份(刷 profile 前所读),可整盘还原。
- `data_p_orig_backup/` —— 5 个 profile 的**原始(未改无秤版)**JSON。

## 9. 关键文件索引
- 自动休眠/唤醒:`src/display/core/AutoSleepManager.h`、`src/display/ui/default/DefaultUI.cpp`、`src/display/drivers/LilyGoDriver.h`、`src/display/drivers/LilyGo-T-RGB/LilyGo_RGBPanel.cpp`(深睡/ext1 唤醒)
- 电池:`src/display/core/BatteryMonitor.h`、`src/display/core/constants.h`
- 开机动画:`src/display/ui/default/lvgl/screens/ui_StandbyScreen.c`、`.../images/ui_img_coffee_anim.c`、`.../lvgl/ui.h`、`src/display/lv_conf.h`
- 模式选择器:`src/display/ui/default/lvgl/ui_events.{cpp,h}`(`onModeSelect` + `ui_create_mode_pill/flank`)、`DefaultUI.cpp`(`applyModeSelector` + 反应式 + 隐藏 grindBtn)、`lvgl/screens/ui_{Brew,Status,SimpleProcess}Screen.{c,h}`(`*_modePill/_modeLeft/_modeRight`)、模拟器钩子 `sim/main.cpp`(`GM_SIM_SCREEN`)
- 蒸汽扭旋钮动画:`.../images/ui_img_steam_knob_anim.c`、`scripts/make_steam_knob_gif.py`、`ui_SimpleProcessScreen.{c,h}`(`steamKnob`)、`DefaultUI.cpp`(steam 显示旋钮/隐 goButton)、`lvgl/ui.h`
- 冲煮/热水按键动画:`.../images/ui_img_{brew,water}_pour_anim.c`、`scripts/make_{brew,water}_button_gif.py`、`ui_BrewScreen.c`(`startButton` 改 `lv_gif`)、`ui_SimpleProcessScreen.{c,h}`(`waterAnim`)、`DefaultUI.cpp`(steam→knob / water→waterAnim / 隐 goButton)、`lvgl/ui.h`
- 网页嵌入:`scripts/embed_webui.py`、`scripts/build_webui.sh`、`src/display/webassets/`
- 设置/HTTP 接口:`src/display/core/Settings.{h,cpp}`、`src/display/plugins/WebUIPlugin.cpp`(handleSettings)
- 主控连接/协议:`lib/NanoPbComm/src/ble/BleClientTransport.cpp`、`lib/NanoPbComm/src/Protocol.h`
- 完整改动叙述见仓库根 `README.md` 末「本地改动 & 实施计划」节。
