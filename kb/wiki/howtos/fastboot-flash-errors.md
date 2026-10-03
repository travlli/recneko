---
title: fastboot flash 失败：Partition table doesn't exist / not allowed in locked state / Flashing is not allowed
tags: [fastboot, recovery, xiaomi, flash, bootloader]
keywords: ["Partition table doesn't exist", "not allowed in locked state", "Flashing is not allowed", "fastboot flash failed", "刷机失败", "解锁BL", "进不去系统"]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: fastboot
---

# fastboot flash 失败：Partition table doesn't exist / not allowed in locked state / Flashing is not allowed

## 症状

在 fastboot 下刷任意分区时，镜像已经 `Sending` 成功，但 `Writing` 阶段被 bootloader 拒绝：

```
$ fastboot flash boot boot.img
Sending 'boot' (65536 KB)                            OKAY [  1.532s]
Writing 'boot'                                       FAILED (remote: 'Partition table doesn't exist')
fastboot: error: Command failed
```

```
$ fastboot flash boot boot.img
Sending 'boot' (65536 KB)                            OKAY [  1.532s]
Writing 'boot'                                       FAILED (remote: 'not allowed in locked state')
fastboot: error: Command failed
```

```
$ fastboot flash system system.img
Sending sparse 'system' (262140 KB)                  OKAY [  6.201s]
Writing 'system'                                     FAILED (remote: 'Flashing is not allowed')
fastboot: error: Command failed
```

其他常见伴随现象：

- 只有部分分区报错，另外一些分区能刷成功。
- 换一个分区名再刷还是同样报错，或者报 `FAILED (remote: 'unknown partition')` 之类的近似错误。
- 报 `not allowed in locked state` / `Flashing is not allowed` 时，设备通常仍处于锁定状态，`fastboot getvar unlocked` 返回 `no`。

## 原因

- **镜像包与机型不匹配**：用了别的机型的 fastboot 包（或跨版本、跨平台包），包内分区名与本机 GPT 对不上，bootloader 就报 `Partition table doesn't exist` / 找不到分区。
- **bootloader 仍处于锁定（locked）状态**：小米设备解锁前禁止写入任何分区，表现就是 `not allowed in locked state` 或 `Flashing is not allowed`。解锁流程与等待期见 [[fastboot-unlock-token-verify-failed]]。
- **刷写环境选错了**：动态分区（逻辑分区，如 system/vendor/product 一类）只存在于用户空间 fastboot（fastbootd）里；在 bootloader fastboot 下这些分区不在 GPT 中，自然报找不到。反之 vbmeta、bootloader 相关分区必须在 bootloader fastboot 下刷。模式区分见 [[fastboot-devices-not-detected]]。
- **个别机型/区域版本对特定分区做了额外保护**，即使已解锁也不允许直接刷写，具体清单视机型而定（见 待确认）。

## 步骤

1. **先确认设备真的被 PC 识别**，避免把连接问题误判成刷写失败：

   ```
   fastboot devices
   ```

   正常应输出一行 `<序列号>  fastboot`。没有输出先处理 [[fastboot-devices-not-detected]]。

2. **确认机型与当前模式**：

   ```
   fastboot getvar product
   fastboot getvar current-slot
   fastboot getvar is-userspace
   ```

   `product` 应与你准备刷入的包对应；`is-userspace: yes` 表示当前是 fastbootd，`no`（或因锁定而不返回）表示 bootloader fastboot。

3. **确认目标分区是否存在**（把 `boot` 换成你要刷的分区名）：

   ```
   fastboot getvar partition-size:boot
   ```

   返回数值说明该分区在当前模式下可见；报错或返回空，说明这个分区名在当前 GPT 里不存在 —— 先别继续硬刷。

4. **如果是 `not allowed in locked state` / `Flashing is not allowed`**：停止反复重试，先去解锁 bootloader。解锁会清空全部数据，务必先备份。

   ```
   fastboot flashing unlock
   ```

   部分机型/版本用 `fastboot oem unlock`。解锁成功后确认：

   ```
   fastboot getvar unlocked
   ```

   返回 `unlocked: yes` 才算真正解锁。若报 `Token verify failed`、`Unlock failed`、提示等待 168 小时，见 [[fastboot-unlock-token-verify-failed]]。

5. **如果是 `Partition table doesn't exist`**，按下面顺序排查：

   1. 核对包与机型：只用本机对应的官方 fastboot 完整包（含 `flash_all.bat` / `flash_all.sh` 的整包），逐条执行包内脚本，而不是自己拼分区名。脚本执行报错的排查见 [[miflash-flash-script-errors]]。
   2. 判断该分区是不是逻辑分区：如果是，切到 fastbootd 再刷。

      ```
      adb reboot fastboot
      ```

      或设备已在 bootloader 时：

      ```
      fastboot reboot fastboot
      ```

      进入后用 `fastboot getvar is-userspace` 确认返回 `yes`，再重试 `fastboot flash <分区> <镜像>`。
   3. 确认镜像本身完整：重新解压 / 重新下载，避免解压中断产生半截镜像。
   4. 若整包脚本总是卡在同一个分区，先确认该分区名是否属于本机；不要为了「刷进去」而随意改名。

6. **A/B 机型补充分区槽位信息**（视 platform-tools 版本支持情况，参数形式可能不同）：

   ```
   fastboot getvar current-slot
   fastboot flash boot boot.img
   ```

   如需明确指定槽位，可用 `--slot` 相关参数或 `fastboot --set-active=a`，具体写法与 bootloader 支持情况以本机实测为准（见 待确认）。没有把握时不要同时改动两个槽位。

7. **换环境排除干扰**：换一根能传数据的线、换主板后置 USB 口（优先 USB 2.0）、去掉 Hub，再重新执行 `fastboot devices` 和刷写命令。

8. **兜底**：如果已经解锁、包也确认匹配，但 bootloader 始终拒绝写入，可考虑进入 EDL/9008 用官方工具重刷（需授权 / 售后渠道），见 [[qualcomm-edl-9008-enter]]；联发科平台另见 [[mtk-spflash-error-4032-4004-4008]]。不要使用来源不明的编程器文件。

## 验证

- 重新执行刷写命令，`Writing '<分区>'` 返回 `OKAY` 而不是 `FAILED`。
- `fastboot getvar unlocked` 返回 `unlocked: yes`（对应 locked 类报错已解决）。
- `fastboot reboot` 后设备能正常开机进入系统；或先在 recovery 中确认能挂载分区、能读写内部存储。
- 开机后在「设置 → 关于手机」中核对版本号与所刷固件一致；如仍无法开机，按 [[recovery-cant-load-android-system]] 处理数据分区问题。

## 待确认

- 具体哪些分区名只在 fastbootd（用户空间 fastboot）可见、哪些只在 bootloader fastboot 可刷，视机型与平台（高通 / 联发科）而定，待确认。
- `Partition table doesn't exist` 在不同 bootloader 版本、不同 platform-tools 版本下的精确触发条件存在差异，待确认。
- 部分机型即使解锁仍禁止刷写的分区清单（若存在）待确认。
- `--slot` 参数的正确写法与最低 platform-tools 版本要求待确认。
