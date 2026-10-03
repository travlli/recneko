---
title: SP Flash Tool 报 STATUS_BROM_CMD_SEND_DA_FAIL / STATUS_DA_HASH_MISMATCH：DA 与 auth 文件不匹配
tags: [mtk, xiaomi, sp-flash-tool, download-agent, auth, 刷机报错]
keywords: [STATUS_BROM_CMD_SEND_DA_FAIL, STATUS_DA_HASH_MISMATCH, Download Agent, SP Flash Tool, 不识别, 无法开机]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: mtk
---

# SP Flash Tool 报 STATUS_BROM_CMD_SEND_DA_FAIL / STATUS_DA_HASH_MISMATCH：DA 与 auth 文件不匹配

## 症状

工具在把 DA（Download Agent）下发给设备时失败，日志出现下面这类状态串，随后连接中断：

```text
STATUS_BROM_CMD_SEND_DA_FAIL
STATUS_DA_HASH_MISMATCH
```

表现是：设备能短暂被识别（设备管理器出现 `MediaTek USB Port`），但马上掉线，根本进不到写入分区阶段；或者每次都在同一个位置失败，重试无效。

## 原因

- **DA 与芯片/平台不匹配**：BROM 只接受与自身平台匹配、且能通过校验的 DA。错版 DA 会导致下发（SEND_DA）直接失败。
- **DA 文件损坏或被改动**：哈希校验对不上（HASH_MISMATCH），常见于压缩包解压不全、文件被截断，或从不可靠渠道拿到的「魔改」DA。
- **安全启动 / 认证要求**：开启 Secure Boot 的机型，BROM 会拒绝未带正确签名的 DA，必须配套 auth 文件，详见 [[mtk-secure-boot-auth-file]]。
- **设备没真正停在 BROM**：处于 Preloader 模式或上电时序不对时，命令发出但设备已经跳走，也会表现为下发 DA 失败，见 [[mtk-brom-vs-preloader-mode]]。

## 步骤

1. 优先使用官方固件包/工具包内自带的 DA 与 scatter，不要用来路不明的「万能 DA」。
2. 重新解压或重新下载固件包，排除 HASH_MISMATCH 由文件损坏引起（可用压缩包内原始文件大小/校验做对比）。
3. 在 SP Flash Tool 的 **Download** 标签页检查 `Download Agent` 路径是否指向正确文件；若机型需要认证，在同一页设置 `Authentication File`，指向与机型/固件匹配的 auth 文件（常见文件名如 `auth_sv5.auth`，视机型而定）。
4. 换一个 SP Flash Tool 版本重试：不同版本对 DA 下发的时序与超时处理不同，能帮助区分兼容性问题。
5. 重建 BROM 环境：拔线、取下电池（可拆机型）、按住音量键；先点 `Download` 再上电池/插线，让工具在等待窗口内抓到设备。速度设为 **Full Speed**，换 USB 2.0 后置端口与可靠数据线。
6. 若报 HASH_MISMATCH 且已确认文件完好，通常是安全启动在拒绝该 DA：改用与机型匹配的 auth 文件 + 官方 DA；症状不变则按 [[mtk-secure-boot-auth-file]] 处理。
7. 以上都无效时，换一台电脑或重装 MTK USB VCOM 驱动后复现，以排除主机 USB 与驱动问题（[[mtk-brom-vs-preloader-mode]]）。

## 验证

- 日志中不再出现这两个状态串，DA 下发完成并进入读/写分区阶段，最终给出成功提示；
- 设备自动重启进入系统，设置 → 关于手机 的版本号与刷入固件一致；
- 对需要 auth 文件的机型，配置好 auth 后能连续两次稳定刷写成功，说明 DA + auth 组合正确。

## 待确认

- 这两个状态串在不同 SP Flash Tool / DA 版本中的输出位置与拼写可能略有差异（大小写、前缀），以实际日志为准。
- 各机型 auth 文件的命名规则与获取渠道不同，待确认。
