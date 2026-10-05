---
title: 网络检索素材：error: Missmatching image and device error
type: web-research
retrieved: 2026-10-05
query: "Missmatching image and device" xiaomi
model: deepseek-v4.1-flash
tokens: 11661
urls:
  - "[1] Xiaomi Mi A3 support - https://github.com/Benjamin-Loison/android/issues/25"
  - "[2] redmi note 10 5g: seems to not work - https://github.com/XiaomiFirmwareUpdater/xiaomi-flashable-firmware-creator/issues/40"
---

# 检索到的原始材料（不可变，勿改）

> 这是 `tools/research_kb.py` 联网检索后抓到的正文原文，作为 wiki 条目的依据。
> 未经人工复核，**不是官方文档**。

## 模型基于以上材料给出的整理（未经人工复核）

## 症状
在 fastboot 刷机时，执行包含如下检查的脚本会输出该错误：

```bash
fastboot $* getvar product 2>&1 | grep -E "^product: *camellia"
if [ $? -ne 0 ] ; then echo "error : Missmatching image and device"; exit 1; fi
```

即当 `fastboot getvar product` 的输出不匹配 `^product: *camellia` 时，脚本打印 `error : Missmatching image and device` 并退出。[2]

## 原因
- 脚本检查当前设备的 product 是否匹配镜像期望的设备代号 `camellia`；不匹配则报错，表示镜像与设备不匹配。[2]
- 资料中该案例的设备为 Redmi Note 10 5G，ROM 文件名包含 `CAMELLIA`，脚本期望 product 为 `camellia`。[2]
- 资料中评论指出该设备是 MTK，不能创建 non-ARB firmware；创建 non-arb fw zip 仅限 QCOM 设备；`anti: 1` 只表示存在，不代表 ARB 已启用。这些是资料中的背景信息，未直接解释该报错的修复。[2]

## 步骤
资料未涉及针对 `error : Missmatching image and device` 的具体处理办法。[2] 资料2只展示了触发该错误的脚本代码，以及关于 MTK、ARB、non-ARB firmware 的讨论，没有给出解决该报错的步骤。[2]

## 验证
资料未涉及如何验证该报错已修复。资料不足，无法确认。[2]

## 待确认
- 用户实际设备的 `fastboot getvar product` 输出是什么？[2]
- 用户刷入的 ROM/镜像对应哪个设备代号？是否与设备实际代号一致？[2]
- 用户是否在执行 `flash_all.sh` 或类似 fastboot 刷机脚本时遇到该报错？[2]
- 资料未涉及该报错与 ARB、MTK 平台之间的直接因果关系，需要用户补充完整命令与输出。[2]

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

### [2] redmi note 10 5g: seems to not work

URL: https://github.com/XiaomiFirmwareUpdater/xiaomi-flashable-firmware-creator/issues/40

# redmi note 10 5g: seems to not work

Hi,
I tried to get a 'non-arb firmware' version from the miui stock rom [redmi note 10 5g].
[miui_CAMELLIANEEAGlobal_V12.5.1.0.RKSEUXM_b68dbc127b_11.0.zip](https://xiaomifirmwareupdater.com/miui/camellian/stable/V12.5.1.0.RKSEUXM/)
But XiaomiFirmwareUpdater can't find anything to extract.

```bash
$ xiaomi_flashable_firmware_creator -N miui_CAMELLIANEEAGlobal_V12.5.1.0.RKSEUXM_b68dbc127b_11.0.zip
Unzipping MIUI ROM...
Traceback (most recent call last):
  File "/home/******/.local/bin/xiaomi_flashable_firmware_creator", line 8, in <module>
    sys.exit(main())
  File "/home/******/.local/lib/python3.8/site-packages/xiaomi_flashable_firmware_creator/xiaomi_flashable_firmware_creator.py", line 41, in main
    new_zip = firmware_creator.auto()
  File "/home/******/.local/lib/python3.8/site-packages/xiaomi_flashable_firmware_creator/firmware_creator.py", line 366, in auto
    self.extract()
  File "/home/******/.local/lib/python3.8/site-packages/xiaomi_flashable_firmware_creator/firmware_creator.py", line 339, in extract
    raise RuntimeError("Nothing found to extract!")
RuntimeError: Nothing found to extract!

```
> Maybe I'm not doing things the right way?
> Do you have any idea or information of incompatibility with the device?
> Thank you.


--- 评论 ---
First, this device is MTK, so you can't create non-ARB firmware from its rom.

Second, you don't need to, it doesn't have ARB enabled, so use the regular firmware.

--- 评论 ---
#### Thanks for the answer.
- If I understand correctly, the Mtk sockets are not compatible with your script? (I didn't see a notice about this, sorry). I didn't know that.
- You answer me that there is no ARB on my device. The fastboot command on the redmi note 10 5g gives this result:
```bash
$ fastboot getvar anti
anti: 1
```
- And by digging into the `fastboot` stock rom image, you can find in the bash script file `flash_all.sh`, the code below:
```bash
fastboot $* getvar product 2>&1 | grep -E "^product: *camellia"
if [ $? -ne 0 ] ; then echo "error : Missmatching image and device"; exit 1; fi

CURRENT_ANTI_VER=1
version=`fastboot getvar anti 2>&1 | grep "anti:" | awk -F ": " '{print $2}'`
if [  "${version}"x == ""x ] ; then version=0 ; fi
if [ ${version} -gt ${CURRENT_ANTI_VER} ] ; then  echo "error : current device antirollback #version is greater than this package" ; exit 1 ; fi
```
I don't know if this information makes sure that ARB is enabled but I would never try to flash a stock rom that has `CURRENT_ANTI_VER=0`. There is a [topic](https://c.mi.com/thread-3139231-1-1.html) where it is said that the values `anti= 0, 1, 2, 3`, allow to downgrade the version of the rom, but if you search in the comments belonging to this article, you can find some of them that give some doubts about this. In fact, I can't be sure that there is no ARB protection on my device. So, thanks for sharing your knowledge.

Regards.

--- 评论 ---
@hfmrow The tool supports MTK, but creating non-arb fw zip is limited to QCOM devices only.

Anti 1 doesn't mean it's enabled, it just means it "exists". The OEM can "increase" that value "and enable arb" to prevent rolling back to older version, in this case custom ROMs users might want to extract non-arb fw to keep the old anti value while using files from the newer firmware.

--- 评论 ---
@yshalsager Thank you for these useful clarifications, have a nice day.
Regards.
