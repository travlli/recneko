---
title: SP Flash Tool 报错 2004/2005/3004：DA 下载与 NAND/eMMC 初始化失败
tags: [mtk, xiaomi, sp-flash-tool, emmc, nand, 刷机报错]
keywords: [ERROR 2004, ERROR 2005, ERROR 3004, SP Flash Tool, 不识别, 无法开机]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: mtk
---

# SP Flash Tool 报错 2004/2005/3004：DA 下载与 NAND/eMMC 初始化失败

## 症状

SP Flash Tool 在 `Downloading DA` 阶段或紧随其后的存储初始化阶段中断，日志出现 2004 / 2005 / 3004 之类的错误码：

```text
ERROR: 2004
ERROR: 2005
ERROR: 3004
```

设备表现为不识别、卡 logo、无法开机；有的机型报错后 USB 设备会直接从设备管理器中消失。与握手/DRAM 阶段的报错（[[mtk-spflash-error-4032-4004-4008]]）不同，这类错误通常发生在工具已经连上设备、DA 已经开始跑之后。

## 原因

- **DA 与设备存储类型不匹配**：2004 / 2005 这类错误来自 DA 阶段，是 DA 在初始化或识别存储（NAND 或 eMMC）时失败。给 eMMC 机型用了只支持 NAND 的老 DA（或反之）是最常见的原因。
- **preloader 损坏或与芯片不匹配**：preloader 负责拉起后续引导并携带 EMI/存储参数；损坏或错版 preloader 会让 DA 拿不到正确的存储信息。
- **存储本体故障**：eMMC/NAND 虚焊、坏块、供电异常时，存储初始化会稳定失败，换固件包、换 DA 都无效。

## 步骤

1. 先确认目标机型的存储类型（eMMC 还是 NAND）与所用 DA 的适用范围，优先使用官方固件包自带的 DA 与 scatter，参考 [[mtk-spflash-error-4032-4004-4008]] 的匹配原则。
2. 重新解压或重新下载固件包，排除 preloader 文件损坏；确认 `scatter` 里 preloader 一项指向的文件确实存在。
3. 在 **Download** 标签页只勾 `Download Only`，速度设为 **Full Speed**，用 USB 2.0 后置端口与可靠数据线重试；进入 BROM 的方式见 [[mtk-brom-vs-preloader-mode]]。
4. 如果设备已经刷坏引导、反复报 2004 / 2005：先在 **Format** 标签页执行整片擦除（Erase Flash），或在 Download 页选 `Format All + Download`，刷入完整官方固件（必须含 preloader），之后再改回 `Download Only` 复刷一遍。注意格式化会清数据，部分机型会丢 IMEI/NVRAM。
5. 若 3004 出现在写入/分区阶段：核对 scatter 的分区表与固件包是否同源，改用该机型当前版本的完整固件包（不要只单独刷某一个分区）。
6. 换一个 SP Flash Tool 版本与官方 DA 组合重试，用于区分「工具/DA 兼容性问题」和「设备本身问题」。
7. 若用多套官方包、多台电脑都能稳定复现同样错误，且设备在其它工具下读芯片信息也异常，则按硬件故障处理：检查 eMMC/NAND 供电与焊接，必要时重植或更换存储芯片。

## 验证

- SP Flash Tool 走完全部进度并给出成功提示，设备自动重启进入系统；
- 设置 → 关于手机，版本号与刷入固件一致；
- 连续多次冷启动不卡 logo、不反复重启；
- 若做过格式化，检查 `*#06#` 的 IMEI 以及 Wi-Fi、蓝牙、SIM 识别是否正常。

## 待确认

- 2004 / 2005 / 3004 在各版本 SP Flash Tool 与各 DA 中的官方符号名（如 `S_DA_NAND_*` / `S_DA_EMMC_*` 系列）并不一致，本文只按「DA 阶段的存储初始化/读写失败」归类，具体对应关系待确认。
- 3004 是否在所有平台上都固定对应 eMMC 相关问题，待确认。
