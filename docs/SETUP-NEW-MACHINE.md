# 在新电脑上搭建本项目（迁移指南）

把这个 **GaggiMate 显示屏固件** 项目迁到新 Mac（电脑 B），并保证「编译 / 烧录 / 救砖」都稳。

- 终端用户烧录（给别人）：见 [`docs/FLASHING.md`](FLASHING.md)
- 维护背景 / 踩过的坑：见 [`HANDOFF.md`](../HANDOFF.md)
- 开发命令表：见 [`CONTRIBUTING.md`](../CONTRIBUTING.md)

---

## 0. 为什么「不要直接整盘拷文件夹」

代码、5 个冲煮 profile、本指南**都在 GitHub fork 上**：`https://github.com/dmq1219/gaggimate`。
直接拷文件夹会把临时构建产物（`.pio/`，上 G）和可能损坏的 `.git` 一起带过去。**从 fork 克隆最干净。**

---

## 1. 装工具链（电脑 B，一次性）

```bash
# Homebrew（若没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.11 node git
brew install sdl2                       # 仅桌面模拟器需要，可选
python3.11 -m pip install -U platformio
```

> ⚠️ **必须 Python 3.11+**（构建脚本用到 `datetime.UTC`）。本项目所有 pio 命令统一写成
> `python3.11 -m platformio ...`，避免系统默认 python 版本不对。

---

## 2. 克隆 + 切到工作分支

```bash
git clone https://github.com/dmq1219/gaggimate.git
cd gaggimate
git checkout feature/display-ux-redesign     # 你的 UI 改造分支：含全部改动 + 5 个 profile
```

> `feature/display-auto-sleep-battery` 是上游 PR #773 那条（只有 auto-sleep+battery）。
> 日常自用请用 `feature/display-ux-redesign`。

---

## 3. 从电脑 A 拷「不在 git 里」的东西（可选，但建议）

这些被 `.gitignore` 排除，克隆拿不到 —— 用 AirDrop / U盘 从 A 拷过去：

| 文件 / 目录 | 作用 | 必要性 |
|---|---|---|
| `display_flash_backup.bin` | 显示屏整盘 16MB 备份，**救砖用** | 强烈建议 |
| `data_p_orig_backup/` | 未改版 profile 原件 | 建议留底 |
| `*.pdf` / `改动效.pages` | UI 设计草稿 | 可不拷 |

其余 gitignore 的（`.pio/`、`src/version.h`、`src/display/webassets/`）都是**构建时自动生成**，不用拷。

---

## 4. 首次构建（会自动生成 version.h + 网页包）

```bash
scripts/build_webui.sh                          # 生成网页包并嵌入固件（改过 web/ 后必跑）
python3.11 -m platformio run -e display          # 编译显示屏固件
```

---

## 5. 烧录（⚠️ 务必先认 MAC，刷错板会黑屏）

本套有**两块板**，都枚举成 `/dev/cu.usbmodem*`（编号不固定）：

| 板 | 型号 | MAC | Flash / PSRAM |
|---|---|---|---|
| **显示屏** | LilyGo T-RGB | `68:ee:8f:46:a7:80` | 16MB / 8MB |
| 控制器 | GaggiMate Controller | `a8:46:74:92:60:24` | 8MB / 2MB |

**刷任何东西前，先读 MAC 认准目标板**（`esptool` 路径在第一次构建装好 espressif32 平台后才有）：

```bash
PORT=$(ls /dev/cu.usbmodem* | head -1)
python3.11 ~/.platformio/packages/tool-esptoolpy/esptool.py --port "$PORT" flash_id | grep -iE "MAC|flash size"
```

确认是显示屏（MAC `…a7:80`、16MB）后：

```bash
# 只刷 app 固件（保留 profile / WiFi / 设置）
python3.11 -m platformio run -e display -t upload   --upload-port "$PORT"

# 只刷文件系统（恢复 5 个 profile，会重写 LittleFS；WiFi/设置在 NVS，不受影响）
python3.11 -m platformio run -e display -t uploadfs  --upload-port "$PORT"
```

**烧录前让它别睡**：显示屏没连 controller 时会**很快深睡、断 USB**（端口消失）。两选一：
1. **下载模式**：按住 `BOOT`(IO0) → 点一下 `RST` → 松 `BOOT`（固件不跑＝不睡，端口稳）。
2. 把咖啡机开着，显示屏连上 controller 就不自动睡。

> 整片擦除后第一次 upload 偶报 `No serial data received`（S3 重新枚举）→ 重试一次即可。

---

## 6. 救砖 / 还原

```bash
# 误刷 / 黑屏：重刷一次显示屏固件即可救回（见 §5）
# 整盘还原到当初的备份：
python3.11 ~/.platformio/packages/tool-esptoolpy/esptool.py --port "$PORT" \
  write_flash 0x0 display_flash_backup.bin
```

---

## 7. 桌面模拟器（可选，免真机看 UI 效果）

模拟器对**带空格的路径**会编译失败，要从无空格路径构建：

```bash
rsync -a --exclude .pio --exclude .git ./ /tmp/gmsim/ && cd /tmp/gmsim
python3.11 -m platformio run -e display-sim
# 跳到指定控制屏并截图（GM_SIM_SCREEN=brew|steam|water|menu，GM_SIM_ACTIVE=1 启动进程）：
GM_SIM_SCREEN=brew ./.pio/build/display-sim/program --screenshot /tmp/shot.bmp 4500
```

---

## 8. 几个坑（详见 HANDOFF）

- **`POST /api/settings` 复选框「不出现＝false」**：改设置请用**网页 UI**（它一次发齐所有字段）；
  用 API 只发部分字段会把没带上的复选框（autoSleep*/clock24hFormat/…）全置成 false。
- 改 `web/` 源码后必须重跑 `scripts/build_webui.sh`（SCons 不追踪 `.incbin` 依赖，否则固件嵌旧网页包 → 白屏）。
- 改 `src/display/lv_conf.h` 后，删 `.pio/build/display/libb3a/lvgl` 再重编。
- **上游已换成 EEZ Studio UI**（`#779`），本分支建在旧 LVGL UI 上 —— 自用没问题，但合上游需在新 UI 上重写。
