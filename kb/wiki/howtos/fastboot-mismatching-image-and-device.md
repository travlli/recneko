---
title: fastboot/MiFlash 报错 Missmatching image and device：刷错包或机型不匹配
tags: [fastboot, miflash, xiaomi, rom, 机型不匹配]
keywords: ["Missmatching image and device", "Mismatching image and device", "机型不匹配", "刷错包", "wrong rom", "rom 不匹配", "codename 不一致"]
author: deepseek-agent
created: 2026-10-05
updated: 2026-10-05
sources: [raw/web/fastboot-mismatching-image-and-device-2026-10-05.md]
platform: fastboot
---

# fastboot/MiFlash 报错 Missmatching image and device：刷错包或机型不匹配

> ⚠️ 本条目的内容来自**联网检索 + 模型整理**，来源见文末，**尚未经过人工/官方核实**。
> 动手前请先读「待确认」，并自行核对来源原文。

## 症状
在 fastboot 刷机时，执行包含如下检查的脚本会输出该错误：

```bash
fastboot $* getvar product 2>&1 | grep -E "^product: *camellia"
if [ $? -ne 0 ] ; then echo "error : Missmatching image and device"; exit 1; fi
```

即当 `fastboot getvar product` 的输出不匹配 `^product: *camellia` 时，脚本打印 `error : Missmatching image and device` 并退出。[2]

## 原因
- 脚本检查当前设备的 product 是否匹配镜像期望的设备代号 `camellia`；不匹配则报错，表示镜像与设备不匹配。[2]
- 资料中该案例的设备为 Redmi Note 10 5G，ROM 文件名包含 `CAMELLIA`，脚本期望 product 为 `camellia`。[2]
- 资料中评论指出该设备是 MTK，不能创建 non-ARB firmware；创建 non-arb fw zip 仅限 QCOM 设备；`anti: 1` 只表示存在，不代表 ARB 已启用。这些是资料中的背景信息，未直接解释该报错的修复。[2]

## 步骤
资料未涉及针对 `error : Missmatching image and device` 的具体处理办法。[2] 资料2只展示了触发该错误的脚本代码，以及关于 MTK、ARB、non-ARB firmware 的讨论，没有给出解决该报错的步骤。[2]

## 验证
资料未涉及如何验证该报错已修复。资料不足，无法确认。[2]

## 待确认
- 用户实际设备的 `fastboot getvar product` 输出是什么？[2]
- 用户刷入的 ROM/镜像对应哪个设备代号？是否与设备实际代号一致？[2]
- 用户是否在执行 `flash_all.sh` 或类似 fastboot 刷机脚本时遇到该报错？[2]
- 资料未涉及该报错与 ARB、MTK 平台之间的直接因果关系，需要用户补充完整命令与输出。[2]

## 来源

- [1] [Xiaomi Mi A3 support](https://github.com/Benjamin-Loison/android/issues/25)
- [2] [redmi note 10 5g: seems to not work](https://github.com/XiaomiFirmwareUpdater/xiaomi-flashable-firmware-creator/issues/40)

原始素材（抓取正文）：`raw/web/fastboot-mismatching-image-and-device-2026-10-05.md`
