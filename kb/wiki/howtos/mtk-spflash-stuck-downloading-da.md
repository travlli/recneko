---
title: MTK SP Flash Tool 卡在 Downloading DA 或停在 100%：格式化 + 下载恢复流程
tags: [mtk, xiaomi, sp-flash-tool, format, recovery, 刷机]
keywords: [Downloading DA, SP Flash Tool, 卡在100%, 无法开机, 反复重启, Format All]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: mtk
---

# MTK SP Flash Tool 卡在 Downloading DA 或停在 100%：格式化 + 下载恢复流程

## 症状

- 点 `Download` 后日志停在 `Downloading DA` 不动，进度长时间无变化；
- 或者进度走到 100% 后卡住，工具界面不结束，而设备已经重启或掉线；
- 有时工具直接无响应，只能拔线，重试后仍然卡在同一位置。

```text
Downloading DA ...
（长时间无进展）

Download 100%
（工具卡住，设备已重启/掉线）
```

## 原因

- **DA 下发后卡住**：DA 需要被 BROM 接收、校验并执行；DA 与机型/平台不匹配、安全启动拒绝，或 USB 链路不稳时就会停在这一步，参见 [[mtk-spflash-send-da-fail-hash-mismatch]]。
- **100% 后的停顿**：很多情况下这是工具在等待设备重启或做校验/回读，并不等于失败；但若设备已掉线，或分区表与存储有异常，就会永久卡住。
- **旧数据与分区表冲突**：设备里存在损坏的引导，或残留的用户数据/加密分区（含 FRP）时，直接 `Download Only` 容易卡住，需要先格式化再写入。

## 步骤

1. 先在 100% 处多等一会儿（时长视机型与工具版本而定），观察设备是否自行重启进入系统；能正常开机就不必继续操作。
2. 卡在 `Downloading DA` 时先拔线重来：核对固件包与 DA 是否为该机型的官方包（[[mtk-spflash-error-4032-4004-4008]]），并把速度设为 **Full Speed**、换 USB 2.0 后置端口与可靠数据线。
3. 换环境复现：换一个 USB 端口、换一台电脑，排除主机 USB 供电与驱动问题（[[mtk-brom-vs-preloader-mode]]）。
4. 走「格式化 + 下载」恢复流程：
   1. 打开 **Format** 标签页执行整片擦除（Erase Flash），或在 **Download** 标签页选择 `Format All + Download`；
   2. 用同一份完整官方固件包（scatter 必须同源）执行下载，让 preloader 与各分区一起重建；
   3. 完成后把模式改回 `Download Only`，再刷一遍以确认可以重复成功。
   ⚠️ 格式化会清空全部数据，部分机型会丢 NVRAM/IMEI，操作前确认可以接受（能备份就先备份）。
5. 若工具提供擦 FRP、擦 NVRAM 之类的独立按钮，只在明确知道后果时才使用，不要为了「刷得进去」乱擦分区。
6. 每次操作前都让设备重新进入 BROM（拔电池/按键），不要在掉线状态下直接重试。
7. 换用另一个版本的 SP Flash Tool 复现，用于区分工具/DA 兼容性问题与设备硬件问题。
8. 多份固件包、多台电脑、多个工具版本都卡在同一位置，且反复出现存储读写错误时，按硬件故障（eMMC/NAND 或供电）处理，见 [[mtk-spflash-error-2004-2005-3004]]。

## 验证

- 日志出现完成/成功提示，设备自动重启进入系统；
- 设置 → 关于手机 的版本号与刷入固件一致，连续冷启动多次不卡 logo、不反复重启；
- 做过格式化的设备，检查 `*#06#` 的 IMEI、Wi-Fi、蓝牙、SIM 识别是否正常；
- 用 `Download Only` 再刷一次仍能一次走完，说明问题是真正解决而非偶然通过。

## 待确认

- 100% 后停顿的官方行为（是否一定在等待设备重启/校验）随工具版本而异，待确认。
- 哪些机型在 `Format All + Download` 后会丢 IMEI/NVRAM，视机型与固件而定，待确认。
