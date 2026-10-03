---
title: MTK Secure Boot 与防回滚报错（S_DA_..._SECURE_BOOT）：auth 文件与小米机型刷机
tags: [mtk, xiaomi, secure-boot, auth, anti-rollback, 刷机报错]
keywords: [S_DA_..._SECURE_BOOT, secure boot, auth 文件, SP Flash Tool, 无法开机, 防回滚]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: mtk
---

# MTK Secure Boot 与防回滚报错（S_DA_..._SECURE_BOOT）：auth 文件与小米机型刷机

## 症状

SP Flash Tool 在 DA 阶段或写 preloader 阶段失败，日志出现 `S_DA_..._SECURE_BOOT` 形式的状态串（前缀与后缀随 SoC 与工具版本不同，见文末「待确认」）：

```text
S_DA_..._SECURE_BOOT
（前缀/后缀随 SOC 与工具版本不同）
```

伴随的典型表现：

- 换了好几份固件包、好几个 DA 都一样报错，设备进不了系统（卡 logo、反复重启）；
- 降级刷旧版固件时必报错，刷同版本或更新版本有时能正常（防回滚）；
- 设备 bootloader 处于锁定状态，fastboot 解锁失败或解锁开关不可用，相关流程见 [[fastboot-unlock-failed]]。

## 原因

- **Secure Boot Chain（SBC）开启**：BROM 只接受由厂商私钥签名的 DA 与镜像，SP Flash Tool 必须配合该机型对应的 auth 文件（认证文件）才能下发 DA。
- **防回滚（anti-rollback）**：设备记录了可接受的最低固件版本等级，刷入更低版本会被拒绝，表现为安全启动类报错或握手直接失败。
- **bootloader 锁定**：锁定时无法通过 fastboot 刷写第三方镜像，部分操作只能走官方认证刷机流程，或先按官方流程解锁。

## 步骤

1. 先确认要刷的固件版本不低于设备当前版本：优先刷与设备现版本相同或更新的官方固件，避免触发防回滚。
2. 准备本机型/本 SoC 对应的 auth 文件。文件名与获取渠道随机型而定（常见如 `auth_sv5.auth`，待确认）；用错机型的 auth 一定失败。
3. 在 SP Flash Tool 的 **Download** 标签页，分别设置好 `Download Agent`（官方 DA）与 `Authentication File`（auth 文件），再执行下载，参见 [[mtk-spflash-send-da-fail-hash-mismatch]]。
4. 换官方固件包自带的 DA + auth 组合重试；若仍报 secure boot 类错误，说明 auth 与设备密钥不匹配，需要找到真正对应本机型的 auth，而不是反复换固件版本。
5. 若 bootloader 处于锁定状态且需要解锁：按小米官方解锁流程操作（需要账号绑定与等待期，具体时长与政策待确认）；解锁失败参考 [[fastboot-unlock-failed]]。
6. 保持链路稳定，避免把「掉线」误判成安全启动问题：USB 2.0 后置端口、可靠数据线、**Full Speed**、规范进入 BROM，见 [[mtk-brom-vs-preloader-mode]]。
7. 不要尝试用改名、替换镜像签名或来源不明的「绕过工具」规避安全启动：既不可靠，也可能让设备进入更难恢复的状态。

## 验证

- 日志中不再出现 secure boot 类状态串，DA 正常下发并完成写入，工具给出成功提示；
- 设备自动重启进入系统，设置 → 关于手机 的版本号与刷入固件一致，且不低于原版本；
- 若做过解锁，可在 fastboot 下查看解锁状态（具体命令随机型而异）；
- 连续冷启动不卡 logo、不反复重启，基带与 IMEI（`*#06#`）正常。

## 待确认

- `S_DA_..._SECURE_BOOT` 的完整符号名（前缀/后缀，例如是否带额外的启用标记）随 SoC 与工具版本变化，待确认，不做臆测。
- 小米各机型 auth 文件的命名规则、获取渠道与官方维修流程，待确认。
- 小米解锁的具体等待期时长与政策，以及哪些 MTK 机型/芯片可以被现有手段绕过安全启动，均待确认。
