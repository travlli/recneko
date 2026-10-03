---
title: 高通 Sahara / Firehose 协议报错（Sahara Fail / Failed to get sahara mode）
tags: [qualcomm, xiaomi, sahara, firehose, qfil]
keywords: [Sahara Fail, Firehose Fail, Failed to get sahara mode, Invalid Firehose programmer, 刷机失败, 9008]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: qualcomm
---

# 高通 Sahara / Firehose 协议报错（Sahara Fail / Failed to get sahara mode）

## 症状

设备已进入 9008，工具也能看到端口，但一点 Download / 刷机就报协议类错误，进度条根本不动。典型日志（示例，实际措辞随工具与版本略有差异）：

```text
Start flashing...
Send Sahara image ...
ERROR: Sahara Fail
```

```text
ERROR: Failed to get sahara mode!!
```

```text
ERROR: Invalid Firehose programmer
```

```text
Send Firehose image ...
ERROR: Firehose Fail
```

共同特征是：设备停在 9008 不消失，工具反复重试握手，或握手几秒后设备从设备管理器里掉线再重新出现。

## 原因

- Sahara 是高通 PBL 与主机之间的握手协议：主机必须先发送一个与 SoC 匹配、且签名被设备接受的 firehose programmer（`prog_firehose_*.elf` 一类文件），设备才会进入后续的镜像传输阶段。握手阶段谈崩就报 `Sahara Fail` / `Failed to get sahara mode`。
- firehose programmer 与机型/SoC/DDR 不匹配，或文件本身损坏、被换名、被其他 ROM 的文件覆盖，会直接报 `Invalid Firehose programmer` 或 `Firehose Fail`。
- 安全启动机型只接受 OEM 签名的 programmer，未签名/签名不符的会在认证环节被拒（日志里常伴随认证相关文字，见 [[qualcomm-secure-boot-nop-sig-tag]]）。
- USB 链路不稳定（劣质线、前置口、USB Hub、供电不足）或驱动异常，同样表现为握手超时/掉线，看起来就像协议错误。
- COM 口被占用：同时开着另一个 QFIL / MiFlash / 串口助手，导致本次连接打不开端口或周期性断开。

## 步骤

1. **只留一个工具**。关闭 MiFlash、QFIL、串口助手、手机助手等所有可能占用 COM 口的程序，然后重新打开要用的那一个。
2. **重建连接**。拔线，按 [[qualcomm-edl-9008-enter]] 重新进入 9008（`adb reboot edl` 或短接测试点），确认设备管理器里是 `Qualcomm HS-USB QDLoader 9008`。
3. **换物理链路**。用可靠数据线接主板后置 USB 2.0 口，去掉 Hub 和延长线。这一步能排掉相当一部分「假协议错误」。
4. **对齐 programmer**。使用与机型、SoC 严格对应的官方 ROM 里自带的 firehose 文件，不要把别的机型/别的 ROM 的 `prog_firehose_*` 混进来。
5. **QFIL 操作顺序**：Select Port 选 9008 端口 → Build Type 选 Flat Build → Programmer Path 指到 ROM 内的 firehose elf → Load XML 选 `rawprogram*.xml` 与 `patch*.xml` → Download。路径尽量短、纯英文、无空格。
6. **`Invalid Firehose programmer` 专项处理**：重新完整解压 ROM（解压中断、杀软拦截 elf 都会造成文件损坏），关闭杀软实时防护后再解压一次；仍报错就换官方完整包。
7. **`Failed to get sahara mode` 专项处理**：多半是设备没真正进 EDL 或握手中途掉线。每次失败后拔线重插、重新进入 9008，再重试 2–3 次；连续失败就换 USB 口、换线，而不是无脑点重试。
8. **交叉验证**。MiFlash 失败时改用 QFIL 刷同一套镜像，或反之；能定位是 ROM 包的问题还是工具/端口的问题。
9. **确认是安全启动拦截**。如果多套官方 programmer 都在认证阶段被拒，不要再反复尝试，改走官方授权刷机流程或售后（见 [[qualcomm-secure-boot-nop-sig-tag]]）。

## 验证

- 日志越过 Sahara 握手，进入 firehose 阶段，并出现逐个分区的写入条目，全程无 `ERROR`；
- 工具状态栏出现成功/完成提示（不同版本措辞不同，例如 Download Succeed / Finish Download 之类）；
- 设备自动重启，设备管理器里的 9008 端口消失，出现正常的 Android / MTP 设备；
- 若日志显示写分区阶段才失败（而不是握手），问题已转到存储侧，见 [[qualcomm-emmc-ufs-flash-write-failure]]。

## 待确认

- 各机型/SoC 对应的 firehose programmer 准确文件名与校验值；
- 较新平台是否必须走官方授权工具才能完成 Sahara 认证；
- 不同版本 QFIL / MiFlash 对这些报错的附加错误码。
