---
title: fastboot 解锁失败：Token verify failed / Unlock failed / Please unlock your device first（含 168 小时等待）
tags: [fastboot, recovery, xiaomi, unlock, bootloader, mi-account]
keywords: ["Token verify failed", "Unlock failed", "Please unlock your device first", "168小时", "解锁BL", "小米账号绑定", "flashing unlock"]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: fastboot
---

# fastboot 解锁失败：Token verify failed / Unlock failed / Please unlock your device first（含 168 小时等待）

## 症状

PC 端解锁工具或命令行报错：

```
$ fastboot flashing unlock
...
FAILED (remote: 'Token verify failed')
fastboot: error: Command failed
```

```
$ fastboot oem unlock
...
FAILED (remote: 'Unlock failed')
fastboot: error: Command failed
```

还没解锁就去刷分区时：

```
$ fastboot flash boot boot.img
Sending 'boot' (65536 KB)                            OKAY [  1.532s]
Writing 'boot'                                       FAILED (remote: 'Please unlock your device first')
fastboot: error: Command failed
```

小米解锁工具（PC 端）侧的表现：

- 提示需要等待 **168 小时**（7 天）后才能解锁，或提示账号与设备未绑定 / 绑定未满时长。
- 提示当前账号本月或本周期内解锁配额已用尽。
- 报 token 相关错误，或点击解锁后进度停住然后失败。

## 原因

- **解锁前置条件没满足**：小米设备的官方流程要求在手机上登录小米账号、联网，并在开发者选项里把「账号与设备」绑定；绑定成功后通常还要等待 168 小时才能执行解锁。等待期内退出账号、恢复出厂设置或刷机，计时可能被重置。
- **`Token verify failed`**：PC 端解锁工具拿到的解锁 token 与设备/账号不匹配或已失效。常见诱因：账号与手机登录的账号不是同一个、绑定关系已被重置、使用了非官方或过旧的解锁工具、网络环境（代理/VPN）或系统时间异常。
- **`Unlock failed`**：等待期未满、账号与设备未绑定、账号解锁配额已用尽，或该机型/运营商版本本身不允许解锁。
- **`Please unlock your device first`**：这是结果而不是解锁失败——设备仍是 locked 状态，所有写分区操作都被拒绝。先把解锁做掉，见 [[fastboot-flash-errors]]。

## 步骤

1. **在手机上完成账号绑定**（路径随 MIUI / HyperOS 版本略有差异）：

   1. 设置 → 关于手机 → 连续点击「MIUI 版本 / 版本号」开启开发者选项。
   2. 设置 → 更多设置 → 开发者选项 → 找到「设备解锁状态」一类的入口。
   3. 登录你的小米账号，联网，执行「绑定账号和设备」。
   4. 绑定成功后界面会给出可解锁时间（通常为 168 小时后）。

2. **等待期内不要动这些**：不要退出小米账号、不要恢复出厂设置、不要刷机或改分区。否则绑定计时可能归零，需要重新等 168 小时。

3. **PC 端准备官方解锁工具**：使用小米官方的解锁工具（Mi Unlock），并在工具里登录与手机**同一个**小米账号。不要使用来源不明的第三方解锁工具或「跳过等待」服务。

4. **进 fastboot 并解锁**：

   ```
   fastboot devices
   ```

   确认设备被识别（无输出见 [[fastboot-devices-not-detected]]），然后：

   ```
   fastboot flashing unlock
   ```

   部分机型/版本需要用：

   ```
   fastboot oem unlock
   ```

   命令行方式在部分机型上可能被要求改用官方工具完成，以工具提示为准。

5. **看到等待提示时**：只能等，没有可靠的跳过的办法。任何声称「付费跳过 168 小时」「秒解锁」的服务都有盗号、盗取解锁权限或植入风险，不要尝试。

6. **`Token verify failed` 的重试清单**（按顺序做完再试一次）：

   1. 确认手机与 PC 端登录的是同一个小米账号。
   2. 关闭 PC 上的代理 / VPN，检查系统时间是否准确（时间偏差会让 token 校验失败）。
   3. 换一根能传数据的线、换主板后置 USB 口，重新插拔后重进 fastboot。
   4. 更新解锁工具到官方最新版，更新 platform-tools。
   5. 重新执行一次「绑定账号和设备」，等绑定关系生效后再尝试解锁。

7. **解锁成功后的注意点**：解锁会清空全部用户数据（相当于 wipe data），解锁前先备份。设备开机时通常会出现解锁状态警告，属正常现象。

8. **不要随手回锁**：`fastboot flashing lock` 可以重新上锁，但如果当前系统不是官方完整固件、或分区内容与官方校验不一致，回锁后可能直接无法开机。确认整机已刷回官方包再考虑回锁。

## 验证

- ```
  fastboot getvar unlocked
  ```

  返回 `unlocked: yes`（未解锁时为 `no`）。
- 手机「设置 → 开发者选项 → 设备解锁状态」显示已解锁；开机时出现解锁警告画面（视机型）。
- 重新执行刷写命令不再报 `not allowed in locked state` / `Flashing is not allowed` / `Please unlock your device first`；分区刷写见 [[fastboot-flash-errors]]。
- 解锁后如出现开机校验报错（dm-verity / vbmeta），见 [[avb-verified-boot-corruption]]。

## 待确认

- 绑定的前置条件（是否必须插 SIM 卡、是否必须开启「查找设备」等）随 MIUI / HyperOS 版本与地区版本变化，待确认。
- 单个账号的解锁配额（数量与周期）、是否额外要求小米社区等级或答题，官方政策会调整，以官方解锁页说明为准，待确认。
- 部分运营商定制机、企业机或特定型号不支持自助解锁，待确认。
- `fastboot flashing unlock` 与 `fastboot oem unlock` 在具体机型上的可用性差异待确认。
