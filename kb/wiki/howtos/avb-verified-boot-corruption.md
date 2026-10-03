---
title: AVB / verified boot 报错：dm-verity corruption / Your device is corrupt / vbmeta verification failed
tags: [fastboot, recovery, xiaomi, avb, vbmeta, verified-boot]
keywords: ["dm-verity corruption", "Your device is corrupt", "vbmeta verification failed", "AVB", "disable-verity", "无法开机", "进不去系统"]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: avb
---

# AVB / verified boot 报错：dm-verity corruption / Your device is corrupt / vbmeta verification failed

## 症状

开机时出现完整性校验警告：

```
dm-verity corruption
Your device is corrupt. It can't be trusted and may not work properly.
```

```
AVB: vbmeta verification failed
```

其他常见伴随现象：

- bootloader 界面出现红字 / 黄字警告，需要按键才能继续，或者继续后卡住 / 自动重启。
- 刷入修改过的 boot、system 等分区（root、GSI、第三方内核）之后开始出现，之前正常。
- 刷过 `vbmeta` 后 `dm-verity corruption` 不再出现，但仍然无法进入系统。
- 已解锁设备日常也可能显示「设备已解锁」一类警告，这是解锁提示，与 `Your device is corrupt` 这类完整性校验失败不是同一回事。

## 原因

- **改了受 AVB 保护的分区，但 vbmeta 里的校验信息没同步更新**：AVB 会用 vbmeta（及其关联的 vbmeta_system 等，视机型而定）中的哈希 / 描述符校验各分区，任何改动都会让校验失败，于是报 `vbmeta verification failed` / `dm-verity corruption` / `Your device is corrupt`。
- **镜像与机型 / 版本不匹配**：刷了别机型或不同版本的 vbmeta、boot 等镜像，描述符与分区内容对不上，同样校验失败。
- **verity / verification 标志与实际分区状态不一致**：只刷了带 `--disable-verity` 的 vbmeta，却没有刷对应的其它分区镜像（或反过来），状态组合矛盾时就可能仍无法启动。
- **解锁后刷了非官方固件**：这类警告本身属于预期现象；若伴随无法开机，问题在于镜像不匹配或数据分区需要清理，而不是警告文字本身。

## 步骤

1. **确认已解锁**（未解锁无法刷 vbmeta）：

   ```
   fastboot getvar unlocked
   ```

   返回 `unlocked: yes` 再继续；不是 `yes` 先看 [[fastboot-unlock-token-verify-failed]]。

2. **确认在正确的 fastboot 环境**：vbmeta 属于物理分区，应在 bootloader fastboot（音量下 + 电源进入）下刷，不要在 fastbootd 里刷。用下面命令区分当前环境：

   ```
   fastboot getvar is-userspace
   ```

   `yes` 表示极可能是 fastbootd，需要回到 bootloader fastboot 再操作；识别与驱动问题见 [[fastboot-devices-not-detected]]。

3. **取官方镜像**：从本机对应版本的官方 fastboot 完整包里取 `vbmeta.img`。A/B 机型是否另有独立的 `vbmeta_system.img` 等，视机型而定（见 待确认），有就一并处理。

4. **按正确参数顺序刷写**（platform-tools 的标准写法是把标志放在 `flash` 之前）：

   ```
   fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img
   ```

   若本机存在独立的 vbmeta_system：

   ```
   fastboot --disable-verity --disable-verification flash vbmeta_system vbmeta_system.img
   ```

   网上常见写成 `fastboot flash vbmeta --disable-verity --disable-verification vbmeta.img`（标志放在分区名之后）。这种写法在部分 fastboot / platform-tools 版本上参数不会被解析，等于没有关掉校验，刷完仍报错 —— 请优先使用上面的标准顺序，并留意命令回显是否真的执行成功。

5. **明白这样做的风险与副作用，再决定要不要做**：

   - `--disable-verity` / `--disable-verification` 会关闭分区的完整性校验，等于放弃 AVB 的保护，系统被篡改时不再拦截，安全性下降。
   - 可能影响官方 OTA：校验状态与官方预期不一致时，OTA 可能拒绝安装或安装失败。
   - 部分机型 / 系统（尤其新版本 HyperOS）对非官方 vbmeta 还有额外校验，即使关了校验也可能仍拒绝启动。关校验不是万能的「修复开机」手段。
   - 只有在明确需要（刷第三方内核 / GSI / root 等）且接受上述后果时才使用；纯粹想消除开机警告、又希望保持官方状态的话，不该走这一步。

6. **想恢复官方校验状态**：刷回官方 vbmeta（不带 disable 标志）：

   ```
   fastboot flash vbmeta vbmeta.img
   ```

   注意：官方 vbmeta 要求其它被校验分区也是官方版本，只换 vbmeta 而其它分区仍是改过的镜像，照样校验失败。这种情况下需要刷官方完整 fastboot 包整机恢复：报错处理见 [[fastboot-flash-errors]]。

7. **刷完仍开不了机**：清数据后重试（改过分区 / 跨版本时必须清）：

   ```
   fastboot erase userdata
   ```

   或刷含清数据步骤的官方整包。数据分区挂载失败、卡 recovery 的排查见 [[recovery-cant-load-android-system]]。

8. **确认镜像本身没问题再反复刷**：同一个包重复刷 2～3 次仍失败，通常不是刷写动作问题，而是包 / 分区组合不对，换回官方同版本包验证。

## 验证

- 开机不再出现 `dm-verity corruption`、`Your device is corrupt. It can't be trusted`、`AVB: vbmeta verification failed`。注意解锁设备常见的「设备已解锁」警告属正常，不算修复失败。
- ```
  fastboot getvar unlocked
  ```

  与 `fastboot getvar current-slot` 返回值符合当前预期，设备能稳定进入系统而不是反复重启。
- 若目的是 root / GSI / 第三方内核：目标功能（如 root 管理工具）可用，且系统能正常开机、能正常读写数据。
- 若目的是恢复官方状态：能正常开机，且系统内版本信息与官方包一致。

## 待确认

- 具体哪些机型存在独立的 `vbmeta_system` / `vbmeta_vendor` 等分区，视机型与分区布局而定，待确认。
- 各 platform-tools 版本对 `--disable-verity` / `--disable-verification` 参数位置的解析行为差异，以及哪些 bootloader 会直接拒绝该标志，待确认。
- 新版 HyperOS 对非官方 vbmeta / 非官方分区的额外检测策略（是否仍允许启动）待确认。
- 关闭校验后官方 OTA 的失败表现随版本不同，具体行为待确认。
