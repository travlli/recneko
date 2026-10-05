---
title: 网络检索素材：error: Antirollback check error
type: web-research
retrieved: 2026-10-05
query: "Antirollback check error" xiaomi
model: deepseek-v4.1-flash
tokens: 10090
urls:
  - "[1] Major audio playback issues on alioth - https://github.com/PixelExperience/android-issues/issues/2183"
---

# 检索到的原始材料（不可变，勿改）

> 这是 `tools/research_kb.py` 联网检索后抓到的正文原文，作为 wiki 条目的依据。
> 未经人工复核，**不是官方文档**。

## 模型基于以上材料给出的整理（未经人工复核）

## 症状
- 在尝试刷入 fastboot MiUI 12.5 ROM 时出现报错：`Antirollback check error.` [1]
- 该报错出现在一个 PixelExperience alioth issue 的评论中；该 issue 原本报告的是音频播放问题，但评论中用户说尝试刷 fastboot MiUI 12.5 ROM 时收到该报错 [1]。
- 用户当时从基于 Android 11 的 PixelExperience 过来，尝试刷 fastboot MiUI 12.5 ROM 时遇到该报错；他也尝试安装基于 Android 11 的 LineageOS 作为跳板，但没有成功 [1]。
- 用户询问：“Is there a way to safely bypass this check?” [1]
- 另有评论称在 apollo/apolloPro（Mi 10T Pro）上也看到此问题 [1]。

## 原因
- 发帖者推测，该报错可能是因为他已有基于 Android 12 的 PixelExperience，却尝试刷 Android 11 ROM，和/或安装 PE 时 fastboot 被更新了 [1]。这是发帖者假设，资料未确认 [1]。
- 有评论认为可以编辑 bat 文件，移除 anti rollback checks 并降级 [1]。这属于社区经验/建议，不是官方原因 [1]。
- 有评论提出替代思路：刷 xiaomi.eu 的 MIUI 12.5，因为这些版本没有 anti-rollback checks [1]。这属于社区经验/建议，资料未说明其安全性或适用性 [1]。
- 资料未给出该报错的官方原因 [1]。

## 步骤
- 评论建议：编辑 bat 文件，移除 anti rollback checks 并降级；并建议在互联网上查找指南 [1]。这是社区建议，资料未给出具体操作，可能风险 [1]。
- 评论建议替代方案：尝试刷 xiaomi.eu 的 MIUI 12.5，因为它们没有 anti-rollback checks [1]。这是社区建议，资料未说明安全性或适用性 [1]。
- 发帖者后续给出的步骤是：1. 安装最新版 MiFlash；2. 下载最新 fastboot 版 MIUI 12.5；3. 移除 `flash_all.bat` 脚本中的 antirollback 部分；4. 重启到 bootloader/fastboot；5. 通过 MiFlash 刷入 MiUI fastboot ROM；6. 按设备说明重新刷入 PixelExperience [1]。
- 发帖者提醒：“Just be aware some steps may differ on your device” [1]。
- 资料未说明如何具体移除 `flash_all.bat` 中的 antirollback 部分，也未提供命令 [1]。
- 移除 antirollback 部分属于社区经验/可能风险，资料未提供官方安全保证 [1]。

## 验证
- 发帖者反馈：“So far it looks like it did fix the issues I was having.” [1]
- 发帖者还说只重新刷了几天，因此“not comfortable saying there is no more problems but so far so good!” [1]。
- 评论称：“Since this issue seems to have been resolved, I'm closing this issue.” [1]。
- 资料未给出单独验证 `Antirollback check error` 消失的命令、日志或检查方法；资料未涉及 [1]。

## 待确认
- 该报错的官方原因和安全官方绕过方式：资料未涉及 [1]。
- 如何具体移除 `flash_all.bat` 中的 antirollback 部分：资料未涉及 [1]。
- 编辑 bat 文件或绕过 anti-rollback 检查的风险：资料未涉及 [1]。
- xiaomi.eu MIUI 12.5 是否适用于所有设备和版本：资料未涉及 [1]。
- 是否必须从最新 MIUI 12.5 clean flash：资料中有评论询问，但未得到确认；资料未涉及 [1]。
- 用户当前设备、当前固件、目标固件、fastboot 版本：资料未涉及，需用户补充 [1]。
- 资料涉及 alioth 和 apollo/apolloPro（Mi 10T Pro），但该报错是否只在这些设备出现：资料未涉及 [1]。

## 抓取到的来源正文

### [1] Major audio playback issues on alioth

URL: https://github.com/PixelExperience/android-issues/issues/2183

# Major audio playback issues on alioth

<!-- INSTRUCTIONS
What not to report
- Bugs in unofficial builds or anything not downloaded from our official portal
- Missing Builds
- Problems with the website
- Asking for device support
- Feature requests

Make sure not to use extra mods when reporting a problem (for example: Magisk)

If you need help please check our Telegram group at https://t.me/pixelexperiencechat

Anything between <!- - and - -> won't be shown when your issue is created. 
-->

## Build date
<!--- Anything that can help us identify the build you are using -->

PixelExperience_alioth-12.1-20220331-0705-OFFICIAL


## Expected Behavior
<!--- Tell us what should happen -->

Audio should playback smoothly


## Current Behavior
<!--- Tell us what happens instead of the expected behavior -->

Major skipping, UI freezing, and sometimes unresponsive volume rocker


## Possible Solution
<!--- Not obligatory, but suggest a fix/reason for the bug, -->

No clue, not really familiar with the inner-workings of Android. I do have logs and a video example but it seems the validation bot doesn't like me including them here. 


## Steps to Reproduce
<!--- Provide a link to a live example, or an unambiguous set of steps to -->
<!--- reproduce this bug. Include code to reproduce, if relevant -->

1. Install any currently available build of PE
2. Start playing a video or audio
3. Continue using the device normally (change volume, open other apps, lock device, etc.)


<!-- THIS SECTION IS MANDATORY. If it is not filled out correctly, your issue will be marked as invalid.
Example:
/device polaris (found at https://wiki.pixelexperience.org/devices/)
/version eleven or eleven_plus (for plus version)
-->

/device alioth
/version twelve


--- 评论 ---
Issue created! You can close at any time by commenting ```/close```

--- 评论 ---
[logcat.txt](https://github.com/PixelExperience/android-issues/files/8448020/logcat.txt)

https://user-images.githubusercontent.com/47618761/162350825-a0ad986b-34a9-46cd-a842-31294bd579a7.mp4

--- 评论 ---
That's odd. I just checked and Spotify works fine on my device, as well as YouTube, YT Music, and other media consumption services, without weird glitches or stutters. Did you do a clean flash from the latest build of MIUI 12.5?

--- 评论 ---
No, I came straight from PE based on Android 11. Do you have a link to download the stock ROM? The websites I've found seem a bit sketchy to me.

Update: Tried to flash the fastboot MiUI 12.5 ROM but I am getting an "Antirollback check error." I assume this is because I have PixelExperience based on Android 12 when I try to flash an Android 11 ROM and/or fastboot got updated when installing PE? I've tried to install the latest LineageOS ROM based on Android 11 as a stepping stone of sorts but to no avail. Is there a way to safely bypass this check?

--- 评论 ---
I believe that you can edit the bat file to remove the anti rollback checks and downgrade. Look for guides on the internet for instructions. Alternatively, you can try flashing a xiaomi.eu build of MIUI 12.5, as those have no anti-rollback checks.

--- 评论 ---
Sure I'll give that a go and see what happens. Knowing me I'll probably screw something up but that's why is a testing phone haha

--- 评论 ---
Also seeing this issue on apollo/apolloPro (Mi 10T Pro) - did updating the stock firmware (presumably using the pre-built zip with flash scripts) help @Sentosa2012 ?

--- 评论 ---
> Also seeing this issue on apollo/apolloPro (Mi 10T Pro) - did updating the stock firmware (presumably using the pre-built zip with flash scripts) help @Sentosa2012 ?

So far it looks like it did fix the issues I was having. I only got round to reflashing my device a couple days ago so I'm not comfortable saying there is no more problems but so far so good!

The steps I took are as follows:
1. Install the latest version of MiFlash
2. Download the latest fastboot version of MiUI 12.5
3. Remove the antirollback section of the flash_all.bat script
4. Reboot into bootloader/fastboot
5. Flash the MiUI fastboot ROM via MiFlash
6. Reflash PixelExperience according to your device's instructions

Just be aware some steps may differ on your device

--- 评论 ---
Since this issue seems to have been resolved, I'm closing this issue. Feel free to open a new issue in the future if you need to report a bug.

--- 评论 ---
/close
