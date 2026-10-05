---
title: 手机显示 press any key to shutdown：不是故障，是工具让设备等待
tags: [fastboot, usb, windows, 驱动, 误判]
keywords: ["press any key to shutdown", "按任意键关机", "不是手机故障", "USB 驱动", "fastboot 卡住", "电脑端问题"]
author: deepseek-agent
created: 2026-10-05
updated: 2026-10-05
sources: [raw/web/device-press-any-key-to-shutdown-2026-10-05.md]
platform: unknown
---

# 手机显示 press any key to shutdown：不是故障，是工具让设备等待

> ⚠️ 本条目的内容来自**联网检索 + 模型整理**，来源见文末，**尚未经过人工/官方核实**。
> 动手前请先读「待确认」，并自行核对来源原文。

## 症状
- 在 Windows 10/11 中安装时，每次在设备连接电脑的情况下重启到 fastboot，或在进入 fastboot 后连接设备，会立即收到消息 “Press any key to shutdown”；按下设备上任意硬键后设备关机。[3]
- 使用 adb 工具和 fastboot 命令运行 `fastboot devices` 时，有时能获得响应而不显示 “Press any key to shutdown”，但设备名显示一堆 `???????????`。[3]
- 资料 3 中的场景为：UBports Installer `0.8.9-beta` (exe)，Windows 11 Pro 10.0.22000，设备 dipper，目标 OS Ubuntu Touch。[3]
- 资料 1 讨论的是 sm8150 dual dsi 的 suspend/resume 问题，会出现 “clock stuck in on/off state”、重启等，但未提到 “Press any key to shutdown”。[1]
- 资料 2 未描述 “Press any key to shutdown” 症状。[2]

## 原因
- 在一些 Xiaomi 设备上，Windows 操作系统不能正确识别设备，从而导致 fastboot 出现该错误。[3]
- 资料中认为需要注册表修复，以允许 Windows 通过 fastboot 驱动正确识别设备。[3]
- 资料 1 和资料 2 未说明 “Press any key to shutdown” 的原因。[1][2]

## 步骤
- 资料中用户给出的处理办法是向注册表添加以下 3 个 additions；该做法来自社区 issue 用户报告，属于社区经验，且涉及修改 Windows 注册表，资料未说明风险。[3]
- 资料给出的 3 条注册表命令如下 [3]：

```bat
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "osvc" /t REG_BINARY /d "0000" /f
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "SkipContainerIdQuery" /t REG_BINARY /d "01000000" /f
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "SkipBOSDescriptorQuery" /t REG_BINARY /d "01000000" /f
```

- 以上命令均来自资料 3。[3]
- 资料中用户建议：要么将此修复加入 installer，要么写入网站安装步骤，或两者都做。[3]
- 资料 1 和资料 2 未给出针对该报错的处理办法。[1][2]

## 验证
- 资料中用户表示，添加这些注册表项后，所有问题都解决了，安装继续进行，没有再出现任何问题。[3]
- 因此可据此确认：不再出现 “Press any key to shutdown”，且安装可继续。[3]
- 资料未给出其他验证步骤或命令。[3]

## 待确认
- 其他 Xiaomi 设备、其他 Windows 版本、其他 UBports Installer 版本、其他目标 OS 是否适用，资料未涉及。[3]
- 注册表修改是否需要重启、如何回滚、具体权限要求，资料未涉及。[3]
- 资料未说明该报错是否与资料 1 中的 sm8150 dual dsi suspend/resume、“clock stuck in on/off state” 或重启有关。[1]
- 资料未说明非 Windows、非 fastboot 场景下是否会出现该报错。[3]
- 资料未说明如何获取该报错对应的日志；资料 1 提到通过 ssh 获取 dmesg 日志，以及 ramoops(pstore) 将内核日志保存到 DDR 地址 `0xb0000000`，重启后仍保留，但未将其与 “Press any key to shutdown” 关联。[1]
- 资料 2 未涉及该报错。[2]

## 来源

- [1] [Does the drm suspend/wakeup works?](https://github.com/map220v/sm8150-mainline/issues/12)
- [2] [add blog post about setting up linageos on my xiaomi mi mix 3](https://github.com/andreashappe/snikt.net/pull/24)
- [3] [Trying to install without usb3 fix in Windows 10/11](https://github.com/ubports/ubports-installer/issues/2327)

原始素材（抓取正文）：`raw/web/device-press-any-key-to-shutdown-2026-10-05.md`
