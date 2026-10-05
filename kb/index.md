---
title: 知识库目录
updated: 2026-10-05
---

# 知识库

> 找东西用搜索（🔍）最快；新条目加工后请在对应小节挂链接。
> 本文件由 `tools/build_kb.py` 依据各页面 frontmatter 自动生成，不要手工编辑。

## Howtos

- [[avb-verified-boot-corruption]] — AVB / verified boot 报错：dm-verity corruption / Your device is corrupt / vbmeta verification failed（`avb`）
  - 关键词：dm-verity corruption、Your device is corrupt、vbmeta verification failed、AVB
- [[fastboot-antirollback-check-error]] — fastboot 报错 Antirollback check error：防回滚校验触发（`fastboot`）
  - 关键词：Antirollback check error、anti-rollback、防回滚、回滚保护
- [[fastboot-data-transfer-failure-too-many-links]] — fastboot 报错 FAILED (data transfer failure (Too many links))：USB 链路不稳（`fastboot`）
  - 关键词：data transfer failure、Too many links、USB 传输失败、换数据线
- [[fastboot-devices-not-detected]] — fastboot devices 不识别 / waiting for any device：USB 驱动与 fastbootd 模式区分（`fastboot`）
  - 关键词：waiting for any device、fastboot devices、USB驱动、fastbootd
- [[fastboot-error-reading-sparse-file]] — fastboot 报错 Error reading sparse file：镜像/磁盘读取失败（`fastboot`）
  - 关键词：Error reading sparse file、Sending sparse、sparse file、镜像损坏
- [[fastboot-flash-errors]] — fastboot flash 失败：Partition table doesn't exist / not allowed in locked state / Flashing is not allowed（`fastboot`）
  - 关键词：Partition table doesn't exist、not allowed in locked state、Flashing is not allowed、fastboot flash failed
- [[fastboot-mismatching-image-and-device]] — fastboot/MiFlash 报错 Missmatching image and device：刷错包或机型不匹配（`fastboot`）
  - 关键词：Missmatching image and device、Mismatching image and device、机型不匹配、刷错包
- [[fastboot-unlock-token-verify-failed]] — fastboot 解锁失败：Token verify failed / Unlock failed / Please unlock your device first（含 168 小时等待）（`fastboot`）
  - 关键词：Token verify failed、Unlock failed、Please unlock your device first、168小时
- [[miflash-flash-all-lock-bat-missing]] — MiFlash 报错 can not found file flash_all_lock.bat：线刷包缺脚本（`fastboot`）
  - 关键词：flash_all_lock.bat、can not found file、找不到脚本、线刷包不完整
- [[miflash-not-catch-checkpoint-flash-not-done]] — MiFlash 报错 Not catch checkpoint / flash is not done：脚本校验未通过（`fastboot`）
  - 关键词：Not catch checkpoint、flash is not done、刷机未完成、flash_all_lock.bat
- [[mtk-brom-vs-preloader-mode]] — MTK BROM 与 Preloader 模式：进入方式、USB VCOM 驱动与刷机中途掉线（`mtk`）
  - 关键词：BROM、Preloader、MediaTek USB Port、MTK USB VCOM 驱动
- [[mtk-secure-boot-auth-file]] — MTK Secure Boot 与防回滚报错（S_DA_..._SECURE_BOOT）：auth 文件与小米机型刷机（`mtk`）
  - 关键词：S_DA_..._SECURE_BOOT、secure boot、auth 文件、SP Flash Tool
- [[mtk-spflash-error-2004-2005-3004]] — SP Flash Tool 报错 2004/2005/3004：DA 下载与 NAND/eMMC 初始化失败（`mtk`）
  - 关键词：ERROR 2004、ERROR 2005、ERROR 3004、SP Flash Tool
- [[mtk-spflash-error-4032-4004-4008]] — SP Flash Tool 报错 4032/4004/4008：BROM·DA 握手与存储不匹配（`mtk`）
  - 关键词：ERROR 4032、ERROR 4004、ERROR 4008、SP Flash Tool
- [[mtk-spflash-send-da-fail-hash-mismatch]] — SP Flash Tool 报 STATUS_BROM_CMD_SEND_DA_FAIL / STATUS_DA_HASH_MISMATCH：DA 与 auth 文件不匹配（`mtk`）
  - 关键词：STATUS_BROM_CMD_SEND_DA_FAIL、STATUS_DA_HASH_MISMATCH、Download Agent、SP Flash Tool
- [[mtk-spflash-stuck-downloading-da]] — MTK SP Flash Tool 卡在 Downloading DA 或停在 100%：格式化 + 下载恢复流程（`mtk`）
  - 关键词：Downloading DA、SP Flash Tool、卡在100%、无法开机
- [[miflash-flash-script-errors]] — MiFlash 常见报错：couldn't find flash script / 发送配置参数失败 / 系统找不到指定的文件（`qualcomm`）
  - 关键词：couldnt find flash script, 发送配置参数失败, 系统找不到指定的文件, The device is not in EDL mode, MiFlash 报错, 无法刷机
- [[qualcomm-edl-9008-enter]] — 高通 EDL（9008）模式进入方法与 Windows 驱动识别问题（`qualcomm`）
  - 关键词：9008、QDLoader 9008、900E、adb reboot edl
- [[qualcomm-emmc-ufs-flash-write-failure]] — 高通机型 eMMC/UFS 存储写入失败（Flash write failure / 存储读写错误）（`qualcomm`）
  - 关键词：FAILED (remote: Flash write failure)、存储读写错误、eMMC 损坏、UFS
- [[qualcomm-qdl-mode-stuck-bootloop]] — 高通机型刷机后卡在 QDL/9008 或反复重启的恢复（`qualcomm`）
  - 关键词：卡在9008、QDL模式、重启循环、刷机后无法开机
- [[qualcomm-sahara-firehose-error]] — 高通 Sahara / Firehose 协议报错（Sahara Fail / Failed to get sahara mode）（`qualcomm`）
  - 关键词：Sahara Fail、Firehose Fail、Failed to get sahara mode、Invalid Firehose programmer
- [[qualcomm-secure-boot-nop-sig-tag]] — 安全启动认证失败：Only nop and sig tag can be received before authentication（`qualcomm`）
  - 关键词：Only nop and sig tag can be received before authentication、认证失败、安全启动、Sahara
- [[recovery-adb-sideload-errors]] — Recovery 下 adb sideload 报错：failed to read command / 签名校验失败 / error: closed（含 EDL/9008 兜底思路）（`recovery`）
  - 关键词：failed to read command、error: closed、adb sideload 失败、签名校验失败
- [[recovery-cant-load-android-system]] — Recovery 报错：Can't load Android system. Your data may be corrupt / failed to mount /data / Unable to mount storage（含 wipe data 流程）（`recovery`）
  - 关键词：Can't load Android system. Your data may be corrupt、failed to mount /data、E:Unable to mount storage、卡recovery
- [[device-press-any-key-to-shutdown]] — 手机显示 press any key to shutdown：不是故障，是工具让设备等待（`unknown`）
  - 关键词：press any key to shutdown、按任意键关机、不是手机故障、USB 驱动
