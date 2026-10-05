---
title: 网络检索素材：can not found file flash_all_lock.bat
type: web-research
retrieved: 2026-10-05
query: "flash_all_lock.bat" not found
model: deepseek-v4.1-flash
tokens: 8150
urls:
  - "[1] Xiaomi Mi A3 support - https://github.com/Benjamin-Loison/android/issues/25"
---

# 检索到的原始材料（不可变，勿改）

> 这是 `tools/research_kb.py` 联网检索后抓到的正文原文，作为 wiki 条目的依据。
> 未经人工复核，**不是官方文档**。

## 模型基于以上材料给出的整理（未经人工复核）

## 症状
资料不足，无法确认。资料 1 中没有出现“can not found file flash_all_lock.bat”这一报错，也没有描述该报错长什么样、在什么场景出现 [1]。资料 1 只涉及 Xiaomi Mi A3 support、LineageOS 编译/刷机相关讨论，以及 XiaomiADB、MiFlash、MiFlash Pro 等工具的调查 [1]。

## 原因
资料不足，无法确认。资料 1 未给出“can not found file flash_all_lock.bat”的原因 [1]。资料 1 中提到的相关内容包括 Xiaomi Mi A3、LineageOS、Fastboot ROM、Recovery ROM、Fastboot 模式、EDL 模式、Recovery 模式、XiaomiADB、MiFlash、MiFlash Pro 等 [1]，但这些内容没有说明该报错为何出现 [1]。

## 步骤
资料不足，无法确认。资料 1 未给出针对“can not found file flash_all_lock.bat”的处理办法 [1]。资料 1 中没有可对应到该报错的刷机步骤、命令或修复步骤 [1]。因此无法判断资料中的做法是否有风险，也无法标注哪些只是社区经验 [1]。

## 验证
资料不足，无法确认。资料 1 未说明如何确认“can not found file flash_all_lock.bat”已修复 [1]。

## 待确认
资料不足，无法确认。需要用户补充以下信息，但资料 1 未涉及：
- 出现该报错时使用的设备、系统、刷机工具、ROM 包和操作步骤 [1]。
- “flash_all_lock.bat”来自哪个工具或 ROM 包 [1]。
- 该报错是否与资料 1 中讨论的 Xiaomi Mi A3、LineageOS、XiaomiADB、MiFlash 或 MiFlash Pro 有关 [1]。

## 抓取到的来源正文

### [1] Xiaomi Mi A3 support

URL: https://github.com/Benjamin-Loison/android/issues/25

# Xiaomi Mi A3 support

# Compilation pipeline:

Rent Scaleway compilation server: [Improve_websites_thanks_to_open_source/issues/778#issuecomment-22759726](https://codeberg.org/Benjamin_Loison/Improve_websites_thanks_to_open_source/issues/778#issuecomment-22759726)
Bash script: [#issuecomment-4381515257](#issuecomment-4381515257)
What about importing signature keys to `~/.android-certs/` (necessary for some apps to work, see [Benjamin_Loison/Doctolib/issues/2](https://codeberg.org/Benjamin_Loison/Doctolib/issues/2))?
Publish to Oracle power VPS.
Update https://xdaforums.com/t/unofficial-rom-16-qpr2-lineageos-23-2-2026-06-06.4791723/

---

https://wiki.lineageos.org/devices/#xiaomi

I have on my Linux Mint Framework a VirtualBox Ubuntu virtual machine dedicated to compiling LineageOS for this device. Using Pegasus for this purpose seems to make more sense.

Related to #24, #46, [Benjamin_Loison/PlayStore/issues/2](https://gitea.lemnoslife.com/Benjamin_Loison/PlayStore/issues/2) and #63.

+74

--- 评论 ---
Could try to find the nearest supported phone I have to test #46 before potentially *breaking* such a Xiaomi Mi A3.

--- 评论 ---
A reason for adding support is to decrypt at reboot with password and at unlock with fingerprint. As of 08/08/24 verified that adding a fingerprint, in addition to password, works fine for unlock but at reboot requires the password, it also request the fingerprint but can use the password instead so it is kind of a bug concerning this aspect. So it is not a specific reason to move to LineageOS this device. Also note that can provide password to unlock instead of fingerprint.

--- 评论 ---
Currently have Android 10, with security patches from 05/08/20.

https://xmfirmwareupdater.com/miui/

EEA: https://xmfirmwareupdater.com/miui/laurel/stable/V12.0.23.0.RFQEUXM/ 2022-08-15
Global: https://xmfirmwareupdater.com/miui/laurel/stable/V12.0.26.0.RFQMIXM/ 2022-08-15

Both are available as recovery or fastboot. Both do not mention *beta*.

https://xmfirmwareupdater.com/miui/laurel/

Both are Android 11 based.

So this would upgrade to the superior Android version and get 2 years of security patches.

[Wikipedia: Android version history#Android 11 (1235610523)](https://en.wikipedia.org/w/index.php?title=Android_version_history&oldid=1235610523#Android_11):

> - Screen recorder.
> - Notification history.

> - One-time permissions.

> - Permissions auto-reset.

> - Since this version, apps no longer have access to other app's directories (including "Android/Data").

Related to [Benjamin_Loison/xmfirmwareupdater.github.io/issues/2](https://codeberg.org/Benjamin_Loison/xmfirmwareupdater.github.io/issues/2).

--- 评论 ---
<details>
<summary>See Signal discussion with:</summary>

```
-----BEGIN PGP MESSAGE-----

hF4DTQa9Wom5MBgSAQdATUIKtBVx0Zcq0M7/mXvaUH1L7W/ACTmZXeVqj+AmSUww
8d3VHTLLJFqCql2o5UT3BxEZal3by+m0H7dYCMpj9jh8dT2eZsDpTVotNLTBnI2q
0kAB0YaGJexi2/7U3lTn+ej5L9McS1eKD7QGMyHQbbyUWBADOfQFR93lb50SoeKG
udPxMlnKwEfytrAWiOeNOf8G
=hqyz
-----END PGP MESSAGE-----
```
</details>

from 1677879573857 to 1677894797400.

Oldest message mentioning *Mi A3* on my Signal Linux Mint 22 Cinnamon Framework 13.

--- 评论 ---
Related to [Benjamin_Loison/xmfirmwareupdater.github.io/issues/5](https://codeberg.org/Benjamin_Loison/xmfirmwareupdater.github.io/issues/5).

--- 评论 ---
![image](https://github.com/user-attachments/assets/43ff7369-3e9e-4a55-82a1-7f699b2b78e3)

![image](https://github.com/user-attachments/assets/84826e77-e287-4ed2-81b5-860589e84099)

![image](https://github.com/user-attachments/assets/6d5b17b5-22bd-4d18-8f60-07b81f7b2c2f)

![image](https://github.com/user-attachments/assets/6cf1b299-d60d-4b68-94b9-3ed4b37d92c1)

--- 评论 ---
https://xiaomiwiki.github.io/wiki/Flash_official_ROMs.html#flash-recovery-roms-in-miui is not relevant here.

I am looking for an open-source solution or an official tool.

So have to investigate:

- https://xiaomiwiki.github.io/wiki/Flash_official_ROMs.html#flash-recovery-roms-in-recovery-mode-using-xiaomiadb *XiaomiADB* https://xiaomiwiki.github.io/wiki/Tools_for_Xiaomi_devices.html#xiaomiadb-by-francesco-tescari https://www.xiaomitool.com/adb https://www.xiaomitool.com/adb#download https://www.xiaomitool.com/latestadb is a `.zip` of a `.exe` and `.dll`s.

> - I need to install lineageos with google services and supersu, how can I do that? You cannot do it with this tool. Only latest official xiaomi roms are allowed.

Source: https://www.xiaomitool.com/adb#faqs

> Feedback
> Help me improving this tool ;)
> Feedback section is not available for now. If you want to write something to the developer or if you want to translate this tool to your language send an email to [dev@xiaomitool.com](mailto:dev@xiaomitool.com?subject=Feedback xiaomiadb)

Source: https://www.xiaomitool.com/adb#feedback

This tool looks closed source.

- https://xiaomiwiki.github.io/wiki/Flash_official_ROMs.html#flash-fastboot-roms-in-edl-mode-using-miflash:
  - https://xiaomiwiki.github.io/wiki/Tools_for_Xiaomi_devices.html#miflash-by-xiaomi:
    > Features:
    > - Install device drivers
    > - Flash Fastboot ROM packages in Fastboot mode
    > - Flash Fastboot ROM packages in EDL mode
    > - Lock the bootloader of any Xiaomi device
  - https://xiaomiwiki.github.io/wiki/Tools_for_Xiaomi_devices.html#miflash-pro-by-xiaomi
    > Features:
    > - Download Fastboot and Recovery ROM packages
    > - Flash Recovery ROM packages in Recovery mode
    > - Flash Fastboot ROM packages in Fastboot mode
    > - Flash device in recovery mode

    So only *Flash Fastboot ROM packages in Fastboot mode* in common.

    *Download Fastboot and Recovery ROM packages* is already the purpose of https://xmfirmwareupdater.com/miui/. Let us try the Pro version if it makes sense as we can assume that it is better.

If still not working investigate:

- https://xiaomiwiki.github.io/wiki/Flash_official_ROMs.html#flash-fastboot-
