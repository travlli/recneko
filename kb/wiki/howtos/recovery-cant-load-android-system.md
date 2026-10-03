---
title: Recovery 报错：Can't load Android system. Your data may be corrupt / failed to mount /data / Unable to mount storage（含 wipe data 流程）
tags: [recovery, fastboot, xiaomi, wipe-data, mount, data-partition]
keywords: ["Can't load Android system. Your data may be corrupt", "failed to mount /data", "E:Unable to mount storage", "卡recovery", "无法开机", "wipe data", "factory reset"]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: recovery
---

# Recovery 报错：Can't load Android system. Your data may be corrupt / failed to mount /data / Unable to mount storage（含 wipe data 流程）

## 症状

开机直接落到 recovery，屏幕显示：

```
Can't load Android system. Your data may be corrupt.
If you continue to get this message, you may need to
perform a factory data reset and erase all user data
stored on this device.

Try again
Factory data reset
```

在 recovery（原厂或 TWRP）里挂载 / 读取数据时：

```
E:failed to mount /data (Invalid argument)
Error: failed to mount /data
E:Unable to mount storage
```

其他常见伴随现象：

- TWRP 的 `Wipe` / `Mount` 页刷屏报 `Failed to mount '/data'`，内部存储显示 0MB 或明显偏小的容量。
- 反复点 `Try again` 依旧回到同一个界面。
- 进不去系统、卡 recovery，但 recovery 本身能正常启动和操作。

## 原因

- **/data 文件系统或加密元数据损坏**：异常断电、刷机中途断线、TWRP 里误操作格式化都可能造成；此时 recovery 无法解密/挂载用户数据，也就无法启动系统。
- **加密元数据与当前系统不匹配**：跨版本刷机、从新系统降级回旧系统、刷了第三方内核 / GSI，但保留了旧的数据分区，解密 key 对不上，表现就是「数据可能已损坏」并建议恢复出厂。
- **分区布局与固件不匹配**：刷入了非本机固件，或动态分区（super）布局与镜像不一致，导致 userdata 所在分区与系统预期不同。
- **存储硬件故障**：少数情况下是 UFS / eMMC 本身出问题（容量识别异常、反复挂载失败），这类只能走售后。

## 步骤

1. **先试一次最轻的处理**：在 `Can't load Android system` 界面选 `Try again`。偶发性挂载失败重启后可能自行恢复。

2. **仍失败则执行 wipe data / factory reset**（会清空全部用户数据，确认已无未备份内容再操作）：

   - 原厂 recovery（音量键移动、电源键确认）：
     1. 选择 `Wipe data/factory reset`（中文界面为「清除数据 / 恢复出厂设置」）→ 确认。
     2. 如有 `Wipe cache partition`（部分机型才有此独立项）一并执行。
     3. 选择 `Reboot system now`。
   - TWRP：
     1. `Wipe` → `Format Data` → 按提示输入 `yes` 回车。
     2. `Format Data` 会重建 /data 文件系统；只做普通的 `Wipe`（滑动清除）往往不足以修复挂载失败。

3. **TWRP 仍报 `Unable to mount storage`** 时，尝试修复文件系统：

   1. `Wipe` → `Repair or Change File System` → 选中 `/data`。
   2. 先试 `Repair File System`；不行再试 `Change File System` 并选择本机原本使用的文件系统类型（ext4 或 f2fs，视机型而定）。
   3. 注意：选错文件系统类型会导致系统无法挂载 /data，操作前先确认本机原本使用的类型；不确定就不要改（见 待确认）。

4. **用 fastboot 侧清数据**（已解锁的 bootloader）：

   ```
   fastboot devices
   fastboot erase userdata
   ```

   或使用 `-w` 参数在刷机时一并清数据（是否被 bootloader 支持视机型而定）：

   ```
   fastboot -w
   ```

   部分机型的加密元数据存放在独立分区，若清完 userdata 仍无法挂载，需要连同该分区一并清除 —— 分区名与是否存在视机型而定（见 待确认），不确定时优先走第 5 步整包刷机。

5. **刷官方完整 fastboot 包**（最稳妥）：用本机对应的官方 fastboot 整包（含 `flash_all.bat` / `flash_all.sh`）执行，会重建分区并清空数据，可同时修复分区布局与文件系统问题。整包刷写报错（如分区不存在 / 未解锁）见 [[fastboot-flash-errors]] 与 [[miflash-flash-script-errors]]。

6. **降级 / 跨版本刷机的规矩**：从新系统刷回旧版本时不要保留数据，先清数据再开机；保留旧数据几乎必然落到 `Can't load Android system`。

7. **刷完首次开机耐心等**：清数据后首次开机可能需要较长时间，期间不要断电、不要反复长按电源键；若超过合理时长仍黑屏/循环，回到 recovery 看是否仍在报挂载错误。

8. **若挂载一直失败且容量识别异常**：停止继续格式化，判定为存储硬件问题的可能性较大，走官方售后检测。

## 验证

- recovery 中 /data 能正常挂载：TWRP 的 `Mount` 页勾选 `Data` 不再报错，`Wipe` 页不再刷 `Unable to mount storage`，内部存储能显示正常容量并可读写文件。
- 设备能通过 recovery 的 `Reboot system now` 进入系统，并完成开机向导。
- 进入系统后「设置 → 存储」显示的总容量与机型标称一致，而非 0MB 或异常小容量。
- 若为刷机修复，开机后「设置 → 关于手机」的版本号与所刷固件一致。

## 待确认

- TWRP（及第三方 recovery）对具体机型 /data 加密方式（是否 metadata 加密）的兼容性不同，Format Data 与 Change File System 的可用性和后果需按机型确认，待确认。
- `fastboot -w` 是否被特定机型的 bootloader 支持，以及它具体清除哪些分区，待确认。
- 加密元数据所在分区名与是否存在（不同平台 / 机型差异较大），待确认。
- 不同 recovery 对电量阈值的要求，待确认。
