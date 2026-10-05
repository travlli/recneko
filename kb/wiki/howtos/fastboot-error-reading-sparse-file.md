---
title: fastboot 报错 Error reading sparse file：镜像/磁盘读取失败
tags: [fastboot, sparse, image, 刷机失败]
keywords: ["Error reading sparse file", "Sending sparse", "sparse file", "镜像损坏", "解压镜像", "fastboot 刷 system 失败"]
author: deepseek-agent
created: 2026-10-05
updated: 2026-10-05
sources: [raw/web/fastboot-error-reading-sparse-file-2026-10-05.md]
platform: fastboot
---

# fastboot 报错 Error reading sparse file：镜像/磁盘读取失败

> ⚠️ 本条目的内容来自**联网检索 + 模型整理**，来源见文末，**尚未经过人工/官方核实**。
> 动手前请先读「待确认」，并自行核对来源原文。

## 症状

- 本次待排查报错为 `error: Sending sparse 'system' 3/5 FAILED (Error reading sparse file)`；资料中未出现完全相同的 `system` 3/5 片段。
- 资料 1 中，在 Raspberry Pi 5、Secure Boot provisioning、`sd` 场景下，通过 fastboot 刷写 root filesystem 时，前面已成功刷写多个 sparse chunks，到 `Sending sparse 'mapper/cryptroot' 20/58 (262140 KB)` 时出现 `FAILED (Error reading sparse file)`，随后 `fastboot: error: Command failed` [1]。
- 资料 1 中该失败发生在 Secure Boot enrollment 已完成之后；设备已进入 Secure Boot 模式，但操作系统镜像只写入了一部分，刷写停在 chunk 20/58 [1]。
- 资料 2、3、4、5 中，UBports Installer `0.10.0` 的 `fastboot:flash` 阶段出现 `Flashing failed`，stderr 包含 `FAILED (Error reading sparse file)` 和 `fastboot: error: Command failed` [2][3][4][5]。
- 资料 1 中，`fastboot` 报错后执行了 cleanup，最后 provisioning script 输出 `exit 0`，导致对应 systemd service 被报告为成功完成 [1]。
- 资料 3 同一日志中还出现其他 fastboot 错误，如 `FAILED (Write to device failed (Too many links))` 和 `FAILED (Write to device failed (Unknown error))` [3]。

## 原因

- 资料 1 的 fastbootd 控制台输出显示：`io_uring request failed: res = -108`、`ClientUSBTransport: read failed: Cannot send after transport endpoint shutdown`、`read expected 268431522 bytes, got 288768`、`Failed to write`、`Couldn't download data: Cannot send after transport endpoint shutdown` [1]。
- 资料 1 认为，这强烈表明 root cause 是 USB transport interruption/reset during a large bulk transfer，而不是 corrupted sparse image [1]。
- 资料 1 指出，客户端报告的是 `FAILED (Error reading sparse file)`，而 fastboot console 显示的实际原因是 USB transport shutdown，这使诊断真实问题变得困难 [1]。
- 资料 2、3、4、5 未给出该报错的原因，仅记录 `fastboot:flash` 失败和 `FAILED (Error reading sparse file)` [2][3][4][5]。

## 步骤

- 资料未给出针对该报错的具体修复或处理步骤；资料 1 列出的是期望行为和建议改进，不是已验证的修复步骤 [1]。
- 资料 1 建议：保留原始 `fastboot` 退出状态；返回非零退出码；明确报告 provisioning failed；保留诊断信息，或提供选项保留诊断信息；区分 Secure Boot enrollment completed、flashing incomplete、provisioning incomplete [1]。
- 资料 1 建议：不要用 `exit 0` 替换失败；报告 `FLASH_FAILED` 或 `FLASH_INTERRUPTED`；区分 USB transport failures 与 sparse image parsing failures [1]。
- 资料 1 中失败后实际执行了 cleanup：`rm -rf temporary directories`、`Deleting customised intermediates`，最后 `exit 0`；资料 1 明确指出这会使服务看起来成功并掩盖失败，不应视为修复 [1]。
- 资料 1 提到板子本身可恢复，但未给出具体恢复步骤 [1]。
- 资料 2、3、4、5 未给出处理办法 [2][3][4][5]。

## 验证

- 资料未说明如何确认该报错已修复，也未给出成功标准或验证命令 [1][2][3][4][5]。
- 资料 1 只说明期望行为：失败时应返回非零并明确报告失败、保留诊断信息、区分状态 [1]，但这不是验证修复的方法。
- 因此：资料不足，无法确认。

## 待确认

- 用户报错为 `Sending sparse 'system' 3/5`，资料 1 为 `Sending sparse 'mapper/cryptroot' 20/58` [1]，资料 2、3、4、5 未给出具体分区名和分块编号 [2][3][4][5]；资料未涉及 `system` 3/5 这一具体场景。
- 资料 2、3、4、5 没有 fastbootd 控制台输出；资料 1 有 [1][2][3][4][5]。需要用户补充完整 fastboot 输出和 fastbootd 控制台输出，以判断是否也是 `Cannot send after transport endpoint shutdown` 类 USB transport 问题 [1]。
- 资料未说明该错误是否与设备、安装器版本、目标系统、USB 端口/线缆/集线器、镜像文件可读性有关，需要用户补充这些信息 [1][2][3][4][5]。
- 资料未给出具体修复步骤和验证方法 [1][2][3][4][5]。
- 资料 1 提到需要区分 Secure Boot enrollment completed、flashing incomplete、provisioning incomplete [1]，但未说明用户当前处于哪个阶段；需要用户补充。

## 来源

- [1] [\[2.2.0\] Fastboot flash failure is masked by successful service exit after USB transport failure during Secure Boot provisioning](https://github.com/raspberrypi/rpi-sb-provisioner/issues/335)
- [2] [Unknown Error](https://github.com/ubports/ubports-installer/issues/3551)
- [3] [ubtouch flash](https://github.com/ubports/ubports-installer/issues/3967)
- [4] [Unknown Error](https://github.com/ubports/ubports-installer/issues/3605)
- [5] [Unknown Error](https://github.com/ubports/ubports-installer/issues/3421)

原始素材（抓取正文）：`raw/web/fastboot-error-reading-sparse-file-2026-10-05.md`
