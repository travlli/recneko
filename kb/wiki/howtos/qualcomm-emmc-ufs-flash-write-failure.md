---
title: 高通机型 eMMC/UFS 存储写入失败（Flash write failure / 存储读写错误）
tags: [qualcomm, xiaomi, emmc, ufs, storage]
keywords: [FAILED (remote: Flash write failure), 存储读写错误, eMMC 损坏, UFS, 坏块, 9008, 分区表损坏]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: qualcomm
---

# 高通机型 eMMC/UFS 存储写入失败（Flash write failure / 存储读写错误）

## 症状

刷机过程能进入写分区阶段，但到某个分区就失败；或 fastboot 刷写时报远端写入失败：

```text
Sending 'system' (1048576 KB)   OKAY
Writing 'system'                FAILED (remote: Flash write failure)
Finished. Total time: 12.345s
```

EDL 工具侧可能表现为：

```text
ERROR: Failed to write to sector ...
存储读写错误
```

其他常见表现：每次都在同一个分区或同一位置失败；刷完依旧无法开机、卡在 logo（见 [[qualcomm-qdl-mode-stuck-bootloop]]）；有时能读出分区但写不进去。

## 原因

- eMMC/UFS 闪存存在坏块、寿命耗尽或颗粒/存储控制器损坏，写入操作返回错误。坏块常集中在写入频繁的 userdata 等分区，表现为「只有个别分区写失败」。
- 分区表（GPT）损坏，或 ROM 的 `rawprogram*.xml` / `patch*.xml` 与设备实际分区布局不一致，导致按错误的起始扇区写入。
- USB 链路或供电不稳导致写入过程中断，日志看起来也像写入失败——必须先排除线材/端口因素，再判定是存储问题。
- 刷了非本机型/非本存储版本的 XML，造成越界写入。

## 步骤

1. **先排除链路问题**：换原装数据线、插主板后置 USB 2.0 口、去掉 Hub，保证供电稳定，重新进 9008 后重试一次。这一步没过之前不要下「颗粒坏了」的结论。
2. **核对 ROM 与机型**：确认型号、存储容量/版本与 ROM 严格对应，不要混用其他机型或其他容量版本的 `rawprogram` / `patch` XML。
3. **只补刷失败分区**：如果只有个别分区（如 userdata、cache）失败，在 fastboot 下单独 `fastboot flash <分区> <镜像>`；若是数据分区损坏，可先 `fastboot erase userdata` 再重刷（会清空用户数据）。**注意不要随意擦写 persist、modemst/fsg 等校准分区**。
4. **需要重新分区的场景**：分区表损坏、GPT 与 XML 不匹配、或刷完仍读不出系统分区时，必须走「重新分区/全盘刷写」流程——使用 ROM 自带的 `rawprogram*.xml` 与 `patch*.xml`，在 QFIL 中启用与「下载前擦除全部」相关的选项（不同版本名称不同，如 Erase All Before Download 一类），或使用 MiFlash 的全刷脚本。
5. **重新分区的风险提示**：该操作会清除设备上的全部数据，包括 persist 等校准分区内容。执行前尽量确认是否有本机 persist 备份；没有备份时，指纹/传感器校准在擦除后无法通过刷机恢复（详见 [[qualcomm-qdl-mode-stuck-bootloop]]）。
6. **重刷后仍在同一位置写失败**：说明问题很可能在存储侧。可多次重复写同一分区观察是否稳定复现；用高通侧工具读取存储信息/自检（具体菜单名随工具版本不同），或换个 EDL 工具再验证一次。
7. **判定颗粒故障后的处理**：若「能读不能写」或同一扇区反复失败，基本可判定为存储颗粒或存储控制器故障，普通刷机无法修复，需要更换主板/存储芯片（维修级操作，需专业设备）。

## 验证

- 重新刷写同一分区不再返回 `FAILED (remote: Flash write failure)`，工具校验阶段无报错；
- 设备能正常开机进入系统，设置里显示的存储容量正确；
- 在系统内做一次大文件写入/删除测试（拷入大文件再删除），无掉盘、无卡死、无重新枚举；
- 冷启动/重启两次以上，系统仍能正常进入，说明写入内容已稳定落盘。

## 待确认

- 各机型存储颗粒型号与是否可单独更换；
- 各工具做坏块检测/存储自检的确切菜单路径与输出含义；
- 「能读不能写」在多大范围内可稳定判定为硬件故障（是否还存在固件层的可能原因）。
