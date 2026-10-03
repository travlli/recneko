---
title: Recovery 下 adb sideload 报错：failed to read command / 签名校验失败 / error: closed（含 EDL/9008 兜底思路）
tags: [recovery, fastboot, xiaomi, adb-sideload, ota, edl]
keywords: ["failed to read command", "error: closed", "adb sideload 失败", "签名校验失败", "卡recovery", "无法开机", "EDL"]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: recovery
---

# Recovery 下 adb sideload 报错：failed to read command / 签名校验失败 / error: closed（含 EDL/9008 兜底思路）

## 症状

PC 端执行 sideload 后立刻失败：

```
$ adb sideload miui_update.zip
serving: 'miui_update.zip'  (~0%)
adb: failed to read command: No error
```

```
$ adb sideload update.zip
adb: error: closed
```

Recovery 屏幕上的校验失败（原厂 recovery 典型文案）：

```
Verifying update package...
E: failed to verify whole-file signature
E: signature verification failed
Installation aborted.
```

其他常见伴随现象：

- 进度条卡在 0% 不动，或走到中途突然断开，recovery 报安装失败。
- 包能开始传输，但 recovery 报 assert / 机型不匹配一类错误后中止（TWRP 下常见 `E:Error in /sideload/package.zip (Status 7)` 形式的提示）。
- 反复重试都是同样的错误；`adb devices` 能看到设备，但状态不是 `sideload`。

## 原因

- **没有进入 recovery 的 sideload 模式**：`adb sideload` 只在 recovery 的 sideload 界面下有效。原厂 recovery 要先选 `Apply update from ADB`（应用来自 ADB 的更新）；TWRP 要先在 `Advanced → ADB Sideload` 滑动启动。在系统里或普通 recovery 界面直接执行，设备端会立刻断开，PC 端就报 `failed to read command` / `error: closed`。
- **adb / platform-tools 版本不匹配或混用**：过旧的 adb 与较新的 recovery 协议不兼容；PATH 里存在多份不同来源的 adb 也会出现莫名其妙的断连。
- **包的签名 / 格式不符合当前 recovery 的预期**：官方 OTA 由厂商密钥签名，第三方 zip 需要对应的第三方 recovery 才能接受；对 zip 做过改动（改包、重新打包）会破坏签名，从而 `signature verification failed`。包与机型不匹配也会在 assert / 校验阶段被拒。
- **传输链路不稳或电量不足**：劣质线材、Hub、USB 口供电/兼容性问题导致传输中断；电量过低时部分 recovery 会拒绝刷写。

## 步骤

1. **先在设备上进入正确的 sideload 模式**：

   - 原厂 recovery（音量键移动、电源键确认）：选择 `Apply update from ADB` / 「应用来自 ADB 的更新」→ 确认。屏幕应提示正在等待通过 ADB 发送安装包。
   - TWRP：`Advanced` → `ADB Sideload` → 滑动 `Swipe to Start Sideload`。

2. **在 PC 上确认设备处于 sideload 状态**：

   ```
   adb devices
   ```

   正常应输出 `<序列号>  sideload`。如果显示 `device` / `unauthorized` / 空列表，说明还没进对模式或驱动异常，先处理连接（fastboot 侧连接问题见 [[fastboot-devices-not-detected]]）。

3. **执行 sideload（路径含空格要加引号）**：

   ```
   adb sideload "D:\ota\miui_update.zip"
   ```

   正常结束时会显示传输比例（形如 `Total xfer: 1.00x`）并让设备继续安装。

4. **处理 `failed to read command` / `error: closed`**：

   1. 回到 recovery 重新进入 sideload 模式，再执行一次 —— 模式未就绪是最常见原因。
   2. 换线、换主板后置 USB 口（优先 USB 2.0），去掉 Hub，再试。
   3. 重启 adb 服务后重试：

      ```
      adb kill-server
      adb devices
      ```

   4. 更新 platform-tools 到官方最新版，并确认系统里只有一份 adb（临时把其它路径从 PATH 里移除或直接用完整路径调用）。
   5. 换一台电脑试，排除本机 USB 栈 / 第三方手机助手的干扰。

5. **处理签名 / 校验失败**：

   1. 换用与本机、与本 recovery 匹配的官方签名 OTA 包，不要使用改包或来源不明的包。
   2. **不要试图绕过签名校验**：绕过签名会让设备接受未经验证的镜像，风险远大于收益，也没有必要 —— 官方包本来就该通过校验。
   3. 校验包是否完整：重新下载（断点续传容易得到损坏文件），并与下载页给出的校验值比对，例如 Windows 下：

      ```
      certutil -hashfile "D:\ota\miui_update.zip" SHA256
      ```

   4. 解锁设备后，可先刷入与包匹配的第三方 recovery，再用该 recovery 刷对应签名的 zip。

6. **处理中途断开 / 大包失败**：先确认电量充足（接充电器操作），再重试；官方完整包体积大，建议用原装线直连后置 USB 口，途中不要动手机。

7. **同一台设备换个刷入途径**：recovery 侧始终失败时，改走 fastboot 线刷官方完整包：

   - 已解锁的情况下用官方 fastboot 整包刷写（含 `flash_all.bat` / `flash_all.sh`），报错排查见 [[fastboot-flash-errors]] 与 [[miflash-flash-script-errors]]。
   - 刷完如果卡 recovery / 数据分区挂载失败，见 [[recovery-cant-load-android-system]]。

8. **兜底：EDL / 9008 思路**：

   - 高通平台：设备进入 EDL（9008）模式后用官方工具重刷，进入方式与前提条件见 [[qualcomm-edl-9008-enter]]。
   - 联发科平台：用官方刷机工具（SP Flash Tool 一类），常见报错见 [[mtk-spflash-error-4032-4004-4008]]。
   - 重要前提：小米机型的 EDL 刷写通常需要官方授权账号或走售后渠道，普通用户不一定能自行完成。**不要使用来源不明的 firehose / 编程器文件**，也不要相信「免授权秒刷」的服务。
   - 如果整机连 EDL 也无法进入（PC 完全无枚举、无端口出现），基本属于硬件层面问题，走官方售后检测。

## 验证

- sideload 过程在 PC 端正常结束（出现类似 `Total xfer: 1.00x` 的完整传输比例），没有 `failed to read command` / `error: closed` / 签名报错。
- recovery 屏幕显示安装完成（原厂 recovery 出现安装成功 / 状态 0 一类提示，TWRP 显示成功），随后设备可正常重启。
- 设备能进入系统并完成开机向导；「设置 → 关于手机」中的版本号、安全补丁级别已更新为所刷 OTA 的版本。
- 若原本是系统内收到更新提示，开机后该更新提示消失、系统内检查更新显示已是最新。

## 待确认

- 不同 recovery（MIUI / HyperOS 原厂 recovery、TWRP）的 sideload 菜单名称与报错文案存在差异，具体以本机界面为准，待确认。
- 各 recovery 对电量阈值的要求，以及对 adb / platform-tools 最低版本的要求，待确认。
- 官方 OTA 是否允许 sideload、是否存在防回滚（rollback）校验，视机型与版本而定，待确认。
- 各平台 EDL / 9008 与官方工具的具体授权要求随机型与地区政策变化，待确认。
