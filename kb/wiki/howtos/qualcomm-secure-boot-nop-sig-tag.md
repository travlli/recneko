---
title: 安全启动认证失败：Only nop and sig tag can be received before authentication
tags: [qualcomm, xiaomi, secure-boot, authentication, qfil]
keywords: [Only nop and sig tag can be received before authentication, 认证失败, 安全启动, Sahara, QFIL, MiFlash]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: qualcomm
---

# 安全启动认证失败：Only nop and sig tag can be received before authentication

## 症状

设备能进 9008，端口也正常，但工具在发送 firehose programmer 后立刻报错并断开。典型日志（示例，措辞随工具版本略有差异）：

```text
Send Sahara image ...
ERROR: Only nop and sig tag can be received before authentication
```

```text
Sahara protocol error
Error: Authentication failed
```

典型表现是：每次点 Download 都在同一秒数内失败，设备从设备管理器里掉线又重新枚举成 9008；换成多个 ROM 包结果完全一样。

## 原因

- 该机型启用了安全启动（Secure Boot）/量产签名校验。PBL 在通过认证之前，只接受 `nop` 和 `sig`（签名）这两类 Sahara 包，主机发过去的未签名 programmer 直接被拒绝，于是报出这句话。
- 使用的 firehose programmer 不是该机型 OEM 签名的版本：拿了工程版/未签名 elf，或从别的机型、别的 ROM 复制了 `prog_firehose_*` 文件。
- 部分较新的机型/平台要求通过官方工具并登录有权限的账号完成认证后才能写入，纯本地离线工具无法完成这一步。

## 步骤

1. **停止反复重试**。这不是概率问题，重复点 Download 只会重复被拒，还可能让 USB 枚举反复异常。
2. **换回官方包内的 programmer**。用与机型完全对应的官方 ROM，直接使用该 ROM 目录里自带的 firehose programmer；重新完整解压一次，并关闭杀软对 `.elf` 等文件的实时拦截，避免文件被截断或隔离。
3. **排除文件被替换**。确认没有从其他 ROM/其他机型复制过 programmer，也没有被第三方工具改写过文件名；与官方包内原文件比对。
4. **确认工具侧的认证路径**。部分平台需要 MiFlash 走授权刷机模式（登录具备刷机权限的账号）才能通过认证；QFIL 侧则必须使用与该机型签名匹配的 programmer，二者不能互相替代。
5. **优先改走 fastboot**。如果设备还能进 fastboot，且 bootloader 已解锁，优先使用官方 fastboot 线刷包完成刷机，绕开 EDL 认证环节（解锁失败见 [[fastboot-unlock-failed]]）。
6. **走官方售后**。若确认是零售安全启动机型、手上没有可用的授权途径，交官方售后/授权维修点刷机是最可靠的路径。不要尝试用非官方「解锁/绕过」工具，风险高且通常无效。

## 验证

- 日志中不再出现该认证错误，Sahara 握手顺利通过并进入 firehose 写分区阶段（对照 [[qualcomm-sahara-firehose-error]] 的成功特征）；
- 或改用 fastboot 流程后 `fastboot flash` 不再返回认证/权限类 FAILED，设备能正常启动；
- 设备刷完后不再回落成 9008（若仍回落见 [[qualcomm-qdl-mode-stuck-bootloop]]）。

## 待确认

- 哪些具体机型/平台只接受授权刷机，边界不清；
- 是否存在官方公开的签名 programmer 分发渠道；
- 部分机型用官方包仍报认证失败时，是否与账号权限级别有关。
