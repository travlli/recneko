---
title: 高通 EDL（9008）模式进入方法与 Windows 驱动识别问题
tags: [qualcomm, xiaomi, edl, driver, windows]
keywords: [9008, QDLoader 9008, 900E, adb reboot edl, 短接测试点, 不识别, 无法进入EDL, Qualcomm HS-USB]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: qualcomm
---

# 高通 EDL（9008）模式进入方法与 Windows 驱动识别问题

## 症状

设备黑屏、插上 USB 后电脑无反应，或设备管理器里出现的不是 EDL 端口；刷机工具（MiFlash / QFIL）里点 Refresh 看不到设备，或提示设备不在 EDL 模式。

典型「设备管理器」状态（示例）：

```text
端口 (COM 和 LPT)
  Qualcomm HS-USB QDLoader 9008 (COM5)      ← 正常，EDL，可刷机
  Qualcomm HS-USB Diagnostics 900E (COM6)   ← 只是诊断口，MiFlash/QFIL 不认
其他设备
  QUSB__BULK                                ← 驱动没装好，系统没认成端口
Android Phone
  Android Composite ADB Interface           ← 只进了 adb，没进 EDL
```

命令侧常见表现：

```text
C:\platform-tools> adb reboot edl

C:\platform-tools> adb devices
List of devices attached
（无输出，设备已进入 EDL 或已断链）
```

如果设备管理器只出现 `900E`、`Android` 或 `QUSB__BULK`，都属于「没有真正进入 EDL / 驱动没装好」，不能直接刷机。

## 原因

- EDL（Emergency Download）是高通 SoC 由底层引导程序暴露的下载模式，在 Windows 上表现为 USB VID/PID 对应的 `Qualcomm HS-USB QDLoader 9008` 端口；MiFlash、QFIL 只认这个 9008 端口。
- `900E` 是高通诊断（Diagnostics）口，常见于系统内切换到诊断模式、或已开机的设备；它**不是** EDL，用它刷机必然失败。
- 驱动未安装或未正确安装时，Windows 会把设备归到「其他设备」，显示为 `QUSB__BULK` 之类的未知设备（具体名称随 Windows 版本和平台略有差异）。
- 能否进入 EDL 取决于机型与 bootloader 策略：有的机型只听 `adb reboot edl`，有的必须短接测试点，零售机还可能直接拒绝本地进入 EDL。

## 步骤

1. **先确认端口状态**。打开「设备管理器 → 端口 (COM 和 LPT)」，必须在刷机前看到 `Qualcomm HS-USB QDLoader 9008 (COMx)`。看到 900E / Android / QUSB__BULK 时，先按下面第 2–5 步让设备进入并识别为 9008，不要继续刷机。
2. **软件方式进 EDL**（优先，最省事）：
   - 系统能正常开机且 adb 已授权：`adb reboot edl`；
   - 能进 fastboot：试 `fastboot oem edl`（部分机型支持，不支持会直接返回错误）；
   - 已 root：可用 `su -c "reboot edl"` 之类的等价命令。
3. **短接测试点进 EDL**（系统进不去、adb 不可用时）：
   - 拆机找到主板上的 EDL 测试点（通常成对、相邻，丝印可能是 EDL / TP / 两个小焊盘，具体位置随机型不同）；
   - 用镊子或细导线短接两个测试点，保持短接的同时插入 USB 线，电脑认到 9008 后再松开；
   - **不要凭猜测短接**：短错点可能烧毁主板。测试点位置以对应机型的点位图/拆机资料为准，找不到测试点的机型通常需要专用 EDL 夹具。
4. **组合键进 EDL**：部分较老机型和工程机可尝试「同时按住音量上 + 音量下，再插入 USB 线」。新机型/零售机是否响应视 bootloader 策略而定，不生效时不要反复长按，直接走短接测试点。
5. **安装/修复驱动**：
   - 在设备管理器里右键那个未知设备（或 9008/900E）→「更新驱动程序」→「浏览我的电脑以查找驱动程序」→ 指向 MiFlash / QFIL 安装目录里的高通 USB 驱动目录，并勾选「包括子文件夹」；也可以「让我从计算机上的可用驱动程序列表中选取」→ 选择「端口 (COM 和 LPT)」→「从磁盘安装」→ 选该目录下的高通驱动 inf 文件（不同驱动包里的文件名不一样，以目录中实际存在的 inf 为准）；
   - 若 Windows 提示驱动签名问题，选择继续安装；若系统直接拒绝安装，可在「高级启动」中临时禁用驱动程序强制签名，装完重启恢复（这一步会降低系统安全性，仅作最后手段）。
6. **换物理链路再试**：用带数据传输能力的原装线，插主板后置 USB 2.0 口，去掉 USB Hub 和延长线。前置口、USB 3.x 口和劣质线是高通 9008 握手失败的常见诱因。
7. **仍然只出现 900E**：说明设备当前不是 EDL 状态。重新执行第 2 步的命令或第 3 步的短接，直到设备管理器显示 9008；不要在 900E 状态下继续操作。
8. **进 9008 后工具仍不识别**：关闭其他占用串口的软件（串口助手、别的刷机工具、手机助手），再在 MiFlash 里点 Refresh，或在 QFIL 里点 Select Port 选择对应 COM 口。

## 验证

- 设备管理器中稳定存在 `Qualcomm HS-USB QDLoader 9008 (COMx)`，不闪断、不自动消失；
- MiFlash 点 Refresh 能列出设备，QFIL 的 Select Port 能列出同一个 COM 口；
- 开始刷机后日志能越过 Sahara 握手、进入写分区阶段（若卡在握手见 [[qualcomm-sahara-firehose-error]]，若工具报找不到脚本或设备不在 EDL 见 [[miflash-flash-script-errors]]）；
- 刷写成功且设备自动重启、不再停留在 9008。若刷完后设备还是 9008 或反复重启，见 [[qualcomm-qdl-mode-stuck-bootloop]]。

## 待确认

- 各具体机型的 EDL 测试点位置与可用组合键；
- 不同 Windows 11 版本对未签名驱动安装的具体策略差异；
- 各版本 MiFlash / QFIL 自带驱动目录的准确路径与 inf 文件名。
