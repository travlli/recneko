---
title: MTK BROM 与 Preloader 模式：进入方式、USB VCOM 驱动与刷机中途掉线
tags: [mtk, xiaomi, brom, preloader, driver, usb]
keywords: [BROM, Preloader, MediaTek USB Port, MTK USB VCOM 驱动, 不识别, SP Flash Tool, 刷机掉线]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: mtk
---

# MTK BROM 与 Preloader 模式：进入方式、USB VCOM 驱动与刷机中途掉线

## 症状

- 设备管理器里设备「一闪而过」：插线后出现 `MediaTek PreLoader USB VCOM Port`（或 `MediaTek USB Port`），一两秒后消失；
- 或者完全**不识别**，显示为未知设备、带感叹号的设备；
- SP Flash Tool 能连上，但刷到一半（下发 DA、写 preloader、写分区）突然断开，报连接/状态类错误，例如 [[mtk-spflash-send-da-fail-hash-mismatch]] 里的状态串，或 [[mtk-spflash-error-4032-4004-4008]] 中的握手失败。

## 原因

- **两种模式本质不同**：BROM 是 SoC 内部固化的引导 ROM，即使 flash 里的引导已经损坏也依然存在，进入后长时间稳定在线，只跑 BROM 协议；Preloader 是 flash 里的第一级引导，上电后只存在很短时间，随即加载后续引导并重新枚举 USB 或直接断开——所以在 Preloader 窗口里刷机必然「中途掉线」。
- **驱动问题**：`MediaTek USB VCOM` 系列驱动没装好、被系统更新覆盖，或旧版未签名驱动在 Windows 10/11 上被驱动签名强制拦下，会导致设备认成未知设备或状态不稳定。
- **上电时序与供电**：先插线再按键、按早/按晚、USB Hub 或前置口供电不足、线材质量差，都会让设备在关键阶段掉线。

## 步骤

1. 装好 MTK USB VCOM 驱动：使用工具包或官方渠道提供的驱动安装程序；若旧驱动在 Windows 10/11 上装不上或报签名错误，临时禁用驱动签名强制后再安装，装完恢复。
2. 打开设备管理器观察设备名：稳定出现 `MediaTek USB Port` 通常表示处于 BROM；只出现 `MediaTek PreLoader USB VCOM Port` 且很快消失，说明抓到的是 Preloader 窗口。设备名与 VID/PID 随驱动版本与机型而异，必要时用硬件 ID 判断。
3. 规范进入 BROM：断开数据线 → 可拆电池机型取下电池 → 在 SP Flash Tool 里先点 `Download` 让工具进入等待 → 按住音量键（不同机型组合不同，见「待确认」）→ 接上数据线/电池。松手时机不对就断开重来。
4. 优化链路：直插主板后置 USB 2.0 端口，不用 Hub 与前置口，换一根可靠数据线；在 **Download** 标签页把速度降为 **Full Speed**；在 Windows 电源选项里关闭「USB 选择性暂停」，并在设备管理器中取消该 USB 设备的「允许计算机关闭此设备以节约电源」。
5. 若掉线发生在写入阶段，先按 [[mtk-spflash-error-4032-4004-4008]] 与 [[mtk-spflash-error-2004-2005-3004]] 排查固件包/DA 匹配，再回到供电与线材。
6. 若设备始终只在 Preloader 窗口出现：尝试让工具在设备上电瞬间自动抓取（是否支持自动检测随工具版本而定），或改用能更早介入的操作顺序；仍无法稳定进入 BROM 时，确认该机型是否对 BROM 有额外限制，见 [[mtk-secure-boot-auth-file]]。
7. 每次重试前都让设备彻底断电（取电池/断开线缆），不要在已掉线的状态下直接点 `Download`。

## 验证

- 设备管理器中设备名稳定存在，不再一闪而过；
- SP Flash Tool 能读出芯片信息并完整走完 DA 下载，全程不掉线；
- 刷写结束后设备自动重启进入系统；
- 连续两次刷写都能稳定复现成功，说明模式进入方式与驱动环境已可靠。

## 待确认

- 各具体机型进入 BROM 的按键组合、是否需要取电池、以及 BROM 的可见时间窗口，差异很大，需按机型确认。
- 不同 MTK USB VCOM 驱动版本在 Windows 10/11 上的兼容性表现不一致，待确认。
