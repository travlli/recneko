---
title: 网络检索素材：error: FAILED (data transfer failure (Too many links))
type: web-research
retrieved: 2026-10-05
query: "Too many links" fastboot
model: deepseek-v4.1-flash
tokens: 25723
urls:
  - "[1] fastboot boot command is bugged on Xiaomi MTK devices - https://github.com/MiCode/Xiaomi_Kernel_OpenSource/issues/2356"
  - "[2] Bootloop with Xiaomi Poco M3 Pro 5G (device needs `fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img`) - https://github.com/topjohnwu/Magisk/issues/4421"
  - "[3] 能否出一个仅使用wifi接入内网当作服务器的固件版本，减少预留内存 - https://github.com/OpenStick/OpenStick/issues/7"
  - "[4] lineage 16 (20190720) broke twrp 3.3.0-0 on sailfish mounting encrypted data, twrp 3.3.1 fixed it, but build is missing for sailfish - https://github.com/TeamWin/android_device_google_sailfish/issues/4"
  - "[5] MDZ-27-AA stuck in DNL: fastboot reboot bootloader accepted but never reaches 2nd stage - https://github.com/RodrigoDeveloperX/xiaomi-mi-tv-stick-4k-mdz-27-aa-recovery/issues/4"
  - "[6] twrp too many links - https://github.com/TeamWin/android_bootable_recovery/issues/409"
---

# 检索到的原始材料（不可变，勿改）

> 这是 `tools/research_kb.py` 联网检索后抓到的正文原文，作为 wiki 条目的依据。
> 未经人工复核，**不是官方文档**。

## 模型基于以上材料给出的整理（未经人工复核）

## 症状

- 资料中出现的报错原文包括：`Booting FAILED (Status read failed (Too many links))` [2][3][6]、`randomly throws error: Too many links even with using usb 2 hub` [1]、`Status read failed (Too many links)` [5]。
- 该报错出现在执行 `fastboot boot` 命令时 [1][2][3][6]；资料5中执行 `fastboot getvar product` 时也出现 `Status read failed (Too many links)` [5]。
- 出现场景涉及：Xiaomi MTK 设备上 `fastboot boot twrp.img` [1]；Xiaomi Poco M3 Pro 5G 上 `fastboot boot magisk_patched-23001_1VHSg.img` [2]；OpenStick 设备上 `fastboot.exe boot fixed_boot.img`，报错后进入 9006 端口模式 [3]；TWRP 官方构建上 `fastboot boot recovery.img` [6]；MDZ-27-AA 处于 DNL 模式时 [5]。
- 资料中没有出现完整的 `error: FAILED (data transfer failure (Too many links))` 原文，只有相近的 `FAILED (Status read failed (Too many links))` [2][3][6]。

## 原因

- 资料1认为这是 MTK bootloader failure (lk.img)，`boot` 命令不工作 [1]。
- 资料1评论认为 Mediatek 不想加入 `fastboot boot` [1]。
- 资料2评论提到 `initial vbmeta disable command is expected and required`，暗示需要先禁用 vbmeta 验证 [2]。
- 资料4中出现的 `Too many symbolic links encountered` 是 linker 读取文件时的符号链接问题，与 fastboot 的 `Too many links` 不同 [4]。
- 资料3、5、6未明确给出该报错的原因 [3][5][6]。

## 步骤

- 资料1评论（社区经验）：`just do fastboot flash boot then reboot to twrp -> restore stock boot.img and do ramdisk patching` [1]。风险：社区经验，未说明是否通用。
- 资料1评论（社区经验）：尝试 `fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img`、`fastboot flash boot "arquivo twrp"`、`fastboot reboot recovery`；如果不行，下载当前设备的 fastboot ROM，提取 `boot.img` 和 `vbmeta.img`，然后执行 `fastboot flash boot boot.img` [1]。但随后有评论表示 `nothing changed, sad :(` [1]。风险：社区经验，有失败报告。
- 资料2评论（社区经验）：先刷 `vbmeta.img`（评论者称上传的是 empty one），执行 `fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img`，然后 `fastboot flash boot boot.img` [2]。评论者称 `this time will work !!!!!! it worked for me` [2]。但另一评论表示对 poco x3 pro 不工作 [2]。风险：社区经验，依赖第三方提供的 `vbmeta.img`，且并非所有设备有效。
- 资料2评论（社区经验）：`Looks like initial vbmeta disable command is expected and required.` [2]。
- 资料3、5、6未给出针对 `Too many links` 的处理步骤 [3][5][6]。
- 资料4的 `Too many symbolic links encountered` 处理方式与 fastboot 无关，未涉及 [4]。

## 验证

- 资料未提供针对本报错的统一验证方法。
- 资料2中评论者称按 vbmeta 方法后 `this time will work !!!!!! it worked for me` [2]，但另一评论称对其设备不工作 [2]。
- 资料3中评论者称 `全部在linux上修改后启动不报错了`，但这是针对修改 dtb 后的启动，不是针对 `Too many links` 的验证，且保留内存未生效 [3]。
- 资料4中 TWRP 3.3.1 的验证是 `decrypted datastorage using password`、`adb sideload nanodroid` 等 [4]，与 `Too many links` 无关。
- 因此，针对本报错的验证方法：资料不足，无法确认。

## 待确认

- 完整报错 `error: FAILED (data transfer failure (Too many links))` 未在资料中一致出现；资料中多为 `FAILED (Status read failed (Too many links))` [2][3][6] 或 `Too many links` [1][5]。需确认是否同一问题。
- 不同设备（Xiaomi MTK、Poco M3 Pro 5G、OpenStick、MDZ-27-AA、TWRP 官方构建设备）上该报错的原因是否相同，资料未说明 [1][2][3][5][6]。
- 资料2的 vbmeta 方法是否普遍有效，资料未确认，且有失败报告 [2]。
- 资料未涉及 fastboot 版本、USB 端口/线缆、主机操作系统等环境信息。
- 资料5中从 DNL 模式进入 2nd stage 的其他方法，资料未给出 [5]。
- 资料6中 TWRP 官方构建下该错误的修复方法，资料未涉及 [6]。

## 抓取到的来源正文

### [1] fastboot boot command is bugged on Xiaomi MTK devices

URL: https://github.com/MiCode/Xiaomi_Kernel_OpenSource/issues/2356

# fastboot boot command is bugged on Xiaomi MTK devices

The best practice for installing TWRP seems to be to inject ramdisk after using fastboot boot twrp.img command. But when this command is broken on the firmware side, I have to make new TWRP build everytime you push OTA cos the wifi/BT/etc kernel modules wont load if the TWRP kernel (latest stock kernel at the time of building) does not match cos devices nowadays use recovery as boot.

It sometimes says "successful" but ends up booting into system rather than TWRP even when twrpfastboot=1 cmdline (forces to boot twrp) is on and randomly throws error: Too many links even with using usb 2 hub.


It would make life a lot easier if you could fix this on your MTK lineup devices. If you cant fix it, release devices with dedicated recovery partition, Thanks.

--- 评论 ---
> The best practice for installing TWRP seems to be to inject ramdisk after using fastboot boot twrp.img command. But when this command is broken on the firmware side, I have to make new TWRP build everytime you push OTA cos the wifi/BT/etc kernel modules wont load if the TWRP kernel (latest stock kernel at the time of building) does not match cos devices nowadays use recovery as boot.
> 
> It sometimes says "successful" but ends up booting into system rather than TWRP even when twrpfastboot=1 cmdline (forces to boot twrp) is on and randomly throws error: Too many links even with using usb 2 hub.
> 
> It would make life a lot easier if you could fix this on your MTK lineup devices. If you cant fix it, release devices with dedicated recovery partition, Thanks.

Hello, i agree with you this is MTK bootloader failure (lk.img) the boot command doesn't seem to work and it's return an error 

$fastboot boot (name of file).img
Sending (name of file).img -> OKAY
Booting... -> FAILED : (Status read failed (No such device) ) and ofc @mi-code you're From Xiaomi Team pls make it work by patching lk.img because only you can build and sign the lk.img Thanks :)

--- 评论 ---
They will never do that tho.
Its happpen in all mediatek devices not only Xiaomi, but other also.
The solution is simple just do fastboot flash boot then reboot to twrp -> restore stock boot.img and do ramdisk patching.
No offense.

--- 评论 ---
On my Poco M3:
```

fastboot boot Image
creating boot image...
creating boot image - 35883008 bytes
Sending 'boot.img' (35042 KB)                      OKAY [  0.837s]
Booting                                            FAILED (remote: 'unknown command')
fastboot: error: Command failed
```

--- 评论 ---
please fix it asap
it's really annoying

--- 评论 ---
+1

--- 评论 ---
It seems that Mediatek does not want to add `fastboot boot`

--- 评论 ---
Here i thought i was the only with the same problem 😭
Mediatek is just trashy sometimes

--- 评论 ---
tente esses comandos :
fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img
fastboot flash boot "arquivo twrp"
fastboot reboot recovery
E se não funcionar é só baixar uma ROM fastboot atual do seu dispositivo e extrair o arquivo boot. img e fazer esse comando: fastboot flash boot boot.img 
O arquivo vbmeta.img também é encontrado quando extrai a ROM fastboot, por favor avise se funcionar..

--- 评论 ---
> On my Poco M3:
> 
> ```
> 
> fastboot boot Image
> creating boot image...
> creating boot image - 35883008 bytes
> Sending 'boot.img' (35042 KB)                      OKAY [  0.837s]
> Booting                                            FAILED (remote: 'unknown command')
> fastboot: error: Command failed
> ```

Same on xaga

--- 评论 ---
> tente esses comandos : fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img fastboot flash boot "arquivo twrp" fastboot reboot recovery E se não funcionar é só baixar uma ROM fastboot atual do seu dispositivo e extrair o arquivo boot. img e fazer esse comando: fastboot flash boot boot.img O arquivo vbmeta.img também é encontrado quando extrai a ROM fastboot, por favor avise se funcionar..

nothing changed, sad :(

### [2] Bootloop with Xiaomi Poco M3 Pro 5G (device needs `fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img`)

URL: https://github.com/topjohnwu/Magisk/issues/4421

# Bootloop with Xiaomi Poco M3 Pro 5G (device needs `fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img`)

<!--

## READ BEFORE OPENING ISSUES

All bug reports require you to **USE CANARY BUILDS**. Please include the version name and version code in the bug report.

If you experience a bootloop, attach a `dmesg` (kernel logs) when the device refuse to boot. This may very likely require a custom kernel on some devices as `last_kmsg` or `pstore ramoops` are usually not enabled by default. In addition, please also upload the result of `cat /proc/mounts` when your device is working correctly **WITHOUT ROOT**.

If you experience issues during installation, in recovery, upload the recovery logs, or in Magisk, upload the install logs. Please also upload the `boot.img` or `recovery.img` that you are using for patching.



If you experience a crash of Magisk app, dump the full `logcat` **when the crash happens**.

If you experience other issues related to Magisk, upload `magisk.log`, and preferably also include a boot `logcat` (start dumping `logcat` when the device boots up)

**DO NOT** open issues regarding root detection.

**DO NOT** ask for instructions.

**DO NOT** report issues if you have any modules installed.

Without following the rules above, your issue will be closed without explanation.

-->

Device: Xiaomi Poco M3 Pro 5G (camellian)
Android version: camellian_eea_global_images_V12.0.8.0.RKSEUXM_20210519.0000.00_11.0_eea_fc5972c36a.tgz
Magisk version name: f822ca5b
Magisk version code: 23001

Patching the Magisk-patched boot.img causes a bootloop on my new Poco M3 Pro 5G / Redmi Note 10 5G (same device, camellian).

> fastboot flash boot boot.img
> Sending 'boot_b' (65536 KB)                        OKAY [  1.441s]
> Writing 'boot_b'                                   OKAY [  0.218s]
> Finished. Total time: 2.276s

Just booting the patched boot.img gives the following error:

> fastboot boot magisk_patched-23001_1VHSg.img
> Sending 'boot.img' (65536 KB)                      OKAY [  1.525s]
> Booting                                            FAILED (Status read failed (Too many links))
> fastboot: error: Command failed

Here is the Magisk install log and the boot.img used for patching:

[magisk_install_log_2021-06-08T14_55_47Z.log](https://github.com/topjohnwu/Magisk/files/6616248/magisk_install_log_2021-06-08T14_55_47Z.log)

[boot.img](https://send.vis.ee/download/461d9facd7afda57/#aeQJtUXrc-1JL-R6lo1VKQ)

Unfortunately I don't believe there exists a custom recovery for the device yet, so my hands are a bit tied, but I figured it's better to get a report in quickly.

--- 评论 ---
oh.. nice to read your report.. i did post a report but was removed not sure if i did something wrong in reporting it though!
i could flash patched boot  but than it goes in bootloop and i need to boot boot.img regular again !

--- 评论 ---
I've got ROOT !! solution
i've uploaded a vbmeta.img on xda ... you need that !! in order to get root i did this
i used magisk 22.1 ( probably it works on v23 as well but .. well mine was tested on that )
ptach your boot.img on magisk as you normally do 
you need to flash vbmeta.img first : 
fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img  ( the one i uploaded is an empty one )
than you just fastboot flash boot boot.img
this time will work !!!!!! it worked for me 
check my post on xda : 
https://forum.xda-developers.com/t/root-gained.4290689/

--- 评论 ---
> I've got ROOT !! solution
> i've uploaded a vbmeta.img on xda ... you need that !! in order to get root i did this
> i used magisk 22.1 ( probably it works on v23 as well but .. well mine was tested on that )
> ptach your boot.img on magisk as you normally do
> you need to flash vbmeta.img first :
> fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img ( the one i uploaded is an empty one )
> than you just fastboot flash boot boot.img
> this time will work !!!!!! it worked for me
> check my post on xda :
> [https://forum.xda-developers.com/t/root-gained.4290689/](url)

Unfortunately, for my device, poco x3 pro, this method is not working.

--- 评论 ---
@bucefalo2 thanks for your solution, it worked for me too with a Wiko View 3.

BTW, I also want to thank Magisk developpers/contributors for their work and inform Wiko View 3 users for who Magisk tells that there is NO RAMDISK, that the "normal" procedure works fine, not the "recovery" one. I've tried both, recovery doesn't work but boot does work.

Cheers

--- 评论 ---
https://twitter.com/Hikari_Calyx/status/1368542481692856322

Looks like initial vbmeta disable command is expected and required. Magisk could maybe just document it better, but it's otherwise a non-issue. 👍

### [3] 能否出一个仅使用wifi接入内网当作服务器的固件版本，减少预留内存

URL: https://github.com/OpenStick/OpenStick/issues/7

# 能否出一个仅使用wifi接入内网当作服务器的固件版本，减少预留内存

当前v1版本，预留了约170MB内存给驱动，系统无法使用。

`Memory: 350280K/524288K available (9664K kernel code, 1212K rwdata, 3644K rodata, 1728K init, 358K bss, 141240K reserved, 32768K cma-reserved)`

如果不需要使用4G功能以及相关驱动，是否可以不预留这些内存，谢谢。

--- 评论 ---
目前没有相关计划，需要更多内存请自行调整设备树关掉modem和视频编解码器（venus）的保留内存，或者更换容量更大的emcp芯片。

--- 评论 ---
已解决。

另外后来用了酷安上“emm没有c”所作的带cifs模块的debian包，有需要的可以试下。

修改各位大侠所作随身wifi刷机包的device tree，减少reversed memory所占内存的方法

Reversed memory不是浪费，是保证4G、5G等通信所需的。所以如果不是刷debian且只当作服务器来用，不建议修改。

修改前内存占用情况
[    0.000000] Memory: 346584K/524288K available (10048K kernel code, 1246K rwdata, 3572K rodata, 1728K init, 365K bss, 144936K reserved, 32768K cma-reserved)

修改后内存占用情况
[    0.000000] Memory: 465196K/524288K available (10048K kernel code, 1246K rwda
ta, 3572K rodata, 1728K init, 365K bss, 54996K reserved, 4096K cma-reserved)

需要准备如下几个工具
android_system_tools_mkbootimg-lineage-19.1，github项目，需要python3，可以用其他类似工具代替
extract-dtb-master，github项目，需要python3
dtc，这个在openstick debian刷机包里有，但无法直接运行，可能因为是在x86架构上编译的。可以装一个alpine linux虚拟机，然后apk add dtc，从其仓库中安装。

步骤如下：

1、确认原刷机包可用
按照openstick debian刷机说明刷入debian，确认可以正常启动。

2、unpack boot.img
从刷机包中找到boot.img，用android_system_tools_mkbootimg-lineage-19.1中的unpackimg命令工具解出kernel和ramdisk两个文件。这个kernel是含dtb，即二进制device tree文件的。注意解包时带上--format mkbootimg参数，输出的命令行参数可以作为后续重新打包的命令参数。

3、从kernel中解出不含dtb的kernel和独立的dtb文件
使用extract-dtb，从kernel中解出不含dtb的kernel和独立的dtb文件。dtb文件是针对具体板子型号的，不过如果不用4g，大部分板子的基本结构都差不多，所以也能直接用。

4、使用dtc将dtb转换为dts
使用可运行的dtc将dtb转为dts，会有些warning报错，不过没关系，主要修改的是两处节点，第一个是reserved-memory，里面每一项的结构如下：

		mpss@86800000 {
			reg = <0x00 0x86800000 0x00 0x5500000>;
			no-map;
			phandle = <0x16>;
		};

mpss@后面的是开始地址，reg里0x00不用管，其他第一个0x是开始地址和前面那个开始地址相同，后面那个是占用地址，这里0x5500000转为十进制，/1024/1024等于85兆。为防万一，没有删除任何节点，包括mpss（4g modem）、venus（视频部分）都只是缩小了占用空间，然后重新计算各项开始地址并修改。

下面还有一个gps，在memshare节点中，我删除了gps@0的整个节点，其他没动。

将修改后的dts用dtc重新转为dtb文件。

5、合并之前extract-dtb生成的不含dtb的kernel和新dtb文件
使用copy /b kernel + dtb kernel.new命令生成新kerenl文件

6、生成修改后的新boot.img
使用mkbootimg结合之前unpackimg给出的参数，生成新boot.img。此时在参数里加上cma=4MB，可以将cma从原来的32兆减少到4兆。

7、无损测试新boot.img
进入fastboot模式，fastboot boot bootimg文件名，不刷机即可测试新boot.img文件是否可用。

8、测试无误，刷入新boot.img

修改后的dts文件见附件
[output1.zip](https://github.com/OpenStick/OpenStick/files/9379208/output1.zip)
：

--- 评论 ---
> 7、无损测试新boot.img
> 进入fastboot模式，fastboot boot bootimg文件名，不刷机即可测试新boot.img文件是否可用。
  
@sulisu 我按照上面的方法操作，一直到这一步的时候出错了  
```
>fastboot.exe boot fixed_boot.img
Sending 'boot.img' (10496 KB)                      OKAY [  0.334s]
Booting                                            FAILED (Status read failed (Too many links))
fastboot: error: Command failed
```
然后就进入了9006端口模式

--- 评论 ---
> 已解决。
> 
> 另外后来用了酷安上“emm没有c”所作的带cifs模块的debian包，有需要的可以试下。
> 
> 修改各位大侠所作随身wifi刷机包的device tree，减少reversed memory所占内存的方法
> 
> Reversed memory不是浪费，是保证4G、5G等通信所需的。所以如果不是刷debian且只当作服务器来用，不建议修改。
> 
> 修改前内存占用情况 [ 0.000000] Memory: 346584K/524288K available (10048K kernel code, 1246K rwdata, 3572K rodata, 1728K init, 365K bss, 144936K reserved, 32768K cma-reserved)
> 
> 修改后内存占用情况 [ 0.000000] Memory: 465196K/524288K available (10048K kernel code, 1246K rwda ta, 3572K rodata, 1728K init, 365K bss, 54996K reserved, 4096K cma-reserved)
> 
> 需要准备如下几个工具 android_system_tools_mkbootimg-lineage-19.1，github项目，需要python3，可以用其他类似工具代替 extract-dtb-master，github项目，需要python3 dtc，这个在openstick debian刷机包里有，但无法直接运行，可能因为是在x86架构上编译的。可以装一个alpine linux虚拟机，然后apk add dtc，从其仓库中安装。
> 
> 步骤如下：
> 
> 1、确认原刷机包可用 按照openstick debian刷机说明刷入debian，确认可以正常启动。
> 
> 2、unpack boot.img 从刷机包中找到boot.img，用android_system_tools_mkbootimg-lineage-19.1中的unpackimg命令工具解出kernel和ramdisk两个文件。这个kernel是含dtb，即二进制device tree文件的。注意解包时带上--format mkbootimg参数，输出的命令行参数可以作为后续重新打包的命令参数。
> 
> 3、从kernel中解出不含dtb的kernel和独立的dtb文件 使用extract-dtb，从kernel中解出不含dtb的kernel和独立的dtb文件。dtb文件是针对具体板子型号的，不过如果不用4g，大部分板子的基本结构都差不多，所以也能直接用。
> 
> 4、使用dtc将dtb转换为dts 使用可运行的dtc将dtb转为dts，会有些warning报错，不过没关系，主要修改的是两处节点，第一个是reserved-memory，里面每一项的结构如下：
> 
> ```
> 	mpss@86800000 {
> 		reg = <0x00 0x86800000 0x00 0x5500000>;
> 		no-map;
> 		phandle = <0x16>;
> 	};
> ```
> 
> mpss@后面的是开始地址，reg里0x00不用管，其他第一个0x是开始地址和前面那个开始地址相同，后面那个是占用地址，这里0x5500000转为十进制，/1024/1024等于85兆。为防万一，没有删除任何节点，包括mpss（4g modem）、venus（视频部分）都只是缩小了占用空间，然后重新计算各项开始地址并修改。
> 
> 下面还有一个gps，在memshare节点中，我删除了gps@0的整个节点，其他没动。
> 
> 将修改后的dts用dtc重新转为dtb文件。
> 
> 5、合并之前extract-dtb生成的不含dtb的kernel和新dtb文件 使用copy /b kernel + dtb kernel.new命令生成新kerenl文件
> 
> 6、生成修改后的新boot.img 使用mkbootimg结合之前unpackimg给出的参数，生成新boot.img。此时在参数里加上cma=4MB，可以将cma从原来的32兆减少到4兆。
> 
> 7、无损测试新boot.img 进入fastboot模式，fastboot boot bootimg文件名，不刷机即可测试新boot.img文件是否可用。
> 
> 8、测试无误，刷入新boot.img
> 
> 修改后的dts文件见附件 [output1.zip](https://github.com/OpenStick/OpenStick/files/9379208/output1.zip) ：

大佬能不能详细的说一下呀？比如说用的什么插件，然后用的什么命令我是小白呀，找不到啊这些东西，

--- 评论 ---
> > 7、无损测试新boot.img
> > 进入fastboot模式，fastboot boot bootimg文件名，不刷机即可测试新boot.img文件是否可用。
> 
> @sulisu 我按照上面的方法操作，一直到这一步的时候出错了
> 
> ```
> >fastboot.exe boot fixed_boot.img
> Sending 'boot.img' (10496 KB)                      OKAY [  0.334s]
> Booting                                            FAILED (Status read failed (Too many links))
> fastboot: error: Command failed
> ```
> 
> 然后就进入了9006端口模式

全部在linux上修改后启动不报错了，但是保留内存还是原来的大小，没生效
```
[    0.000000] Memory: 377980K/524288K available (11264K kernel code, 1310K rwdata, 3960K rodata, 576K init, 381K bss, 142212K reserved, 4096K cma-reserved)
```
这是我修改后的dts：[fixed_001C.zip](https://github.com/OpenStick/OpenStick/files/9962615/fixed_001C.zip)，转换回dtb的时候报了一大堆错误
```
~# dtc -I dts -O dtb -o kernel+dtb/output.dtb kernel+dtb/output.dts
kernel+dtb/output.dts:2072.14-2076.7: Warning (unit_address_vs_reg): /soc@0/spmi@200f000/pmic@1/pwm@bc00: node has a unit name, but no reg property
kernel+dtb/output.dts:1778.17-1795.5: Warning (simple_bus_reg): /soc@0/camss@1b00000: simple-bus unit address format error, expected "1b0ac00"
kernel+dtb/output.dt

### [4] lineage 16 (20190720) broke twrp 3.3.0-0 on sailfish mounting encrypted data, twrp 3.3.1 fixed it, but build is missing for sailfish

URL: https://github.com/TeamWin/android_device_google_sailfish/issues/4

# lineage 16 (20190720) broke twrp 3.3.0-0 on sailfish mounting encrypted data, twrp 3.3.1 fixed it, but build is missing for sailfish

repoduction:
+ update sailfish device to lineage 16 (20190720) 
+ twrp 3.3.0 can not mount encrypted data, and fails to flash nanodroid (microg, fdroid and friends)

additional:
+ i tried to download a newer version (3.3.1*) from jenkins.twrp.me, but there is no build for sailfish
+ i looked up marlin (pixel XL) which has a build job, and from what i looked up, 
https://github.com/TeamWin/android_device_google_marlin has support for both marlin and sailfish.

question:
+ How can i help to get twrp 3.3.1 build for sailfish ?
+ how can i build twrp 3.3.1 for sailfish myself, should i use the marlin repo and if so, how can i use the marlin repo but build sailfish twrp ?

Thank you for your work, 
best regards,
   Felix


--- 评论 ---
echoing @wuxxin about the source of`twrp-3.3.0-0-sailfish.img` - is it built from this repo or from TeamWin/android_device_google_marlin, where there is a sailfish target: https://github.com/TeamWin/android_device_google_marlin/blob/lineage-16.0/aosp_sailfish.mk

--- 评论 ---
previous version `twrp-3.2.3-1-sailfish.img`  doesn't decrypt the latest lineage (July 5 2019 patch level) as well

--- 评论 ---
@bigbiff if there is anything where i can help,
or if you know how to build sailfish twrp 3.3.1,
please tell us :-)

--- 评论 ---
Can you see if http://build.twrp.me/twrp-3.3.1-0-sailfish.img is horribly broken?

--- 评论 ---
i think its working, i was able to
+ boot the build using 'fastboot boot twrp-3.3.1-0-sailfish.img`
+ decrypted datastorage using password
+ adb sideload nanodroid 
and on the next boot the system looks like it should :smile: , thanks

--- 评论 ---
same here - thank you!
decrypt worked, i tested delete of backup - worked. i think there is a circular loop `/system/etc -> /system/etc` that doesn't seem to affect basic functionality, ie these are the messages upon booting and successful decrypting:
```
e4crypt_prepare_user_storage for volume null, user 0, serial 0, flags 1
Preparing: /data/system/users/0
Preparing: /data/misc/profiles/cur/0
Preparing: /data/system_de/0
Preparing: /data/misc_de/0
Preparing: /data/vendor_de/0
Preparing: /data/user_de/0
contents mode 'ice' filenames 'aes-256-cts'
not actually forking for vold_prepare_subdirs
Decrypted Successfully!
Data successfully decrypted
Updating partition details...
WARNING: linker: Warning: couldn't read "/system/etc/ld.config.txt" for "/sbin/sh" (using default configuration instead): error reading file "/system/etc/ld.config.txt": Too many symbolic links encountered
WARNING: linker: Warning: couldn't read "/system/etc/ld.config.txt" for "/sbin/toybox" (using default configuration instead): error reading file "/system/etc/ld.config.txt": Too many symbolic links encountered
I:mount -o bind '/data/media/0' '/sdcard' process ended with RC=0
```

btw aosp_sailfish.mk i mentioned is not in use and can be deleted

--- 评论 ---
since this is open, another issue with 3.3.1 on sailfish regarding /system:

Advanced Wipe > System doesn't work on 3.3.1, works on 3.2.3.

3.3.1 wipe produces a message:
```
mke2fs -t ext4 -b 4096 /dev/block/bootdevice/by-name/system_b 524288 process ended with ERROR:1
Unable to wipe System
Unable to wipe /system
```
The problem seems to be that /system is mounted in 3.3.1 as `/s` even after explicitly unmounting it in the interface.
```
sailfish:/ # mount | grep sda34
/dev/block/sda34 on /s type ext4 (ro,seclabel,relatime,data=ordered)
sailfish:/ # ls -la /dev/block/bootdevice/by-name/system*
lrwxrwxrwx 1 root root 38 1970-01-29 07:01 /dev/block/bootdevice/by-name/system -> /dev/block/bootdevice/by-name/system_b
lrwxrwxrwx 1 root root 16 1970-01-29 07:00 /dev/block/bootdevice/by-name/system_a -> /dev/block/sda33
lrwxrwxrwx 1 root root 16 1970-01-29 07:00 /dev/block/bootdevice/by-name/system_b -> /dev/block/sda34
```

If i explicitly `umount /s` via adb shell in twrp, wiping /system succeeds.

--- 评论 ---
this also means that installing lineage os on sailfish with latest twrp will fail for most people, as it calls for wiping /system: https://wiki.lineageos.org/devices/sailfish/install

--- 评论 ---
Tried testing 3.3.1-0 on SAILFISH just running stock OS.  The passcode now works to decrypt the partition.  Tried to run the Magisk uninstaller and it threw two errors;
```
Updating partition details...
Failed to mount '/system' (Device or resource busy)
Failed to mount '/vendor' (Device or resource busy)
...done
```
Tried the same on 3.3.0-0, working with no errors.

--- 评论 ---
@tarvcode while booted to twrp, try: `adb shell` and then:
`umount /s; umount /v; umount /system`
zip installs should now work . i tried opengapps

### [5] MDZ-27-AA stuck in DNL: fastboot reboot bootloader accepted but never reaches 2nd stage

URL: https://github.com/RodrigoDeveloperX/xiaomi-mi-tv-stick-4k-mdz-27-aa-recovery/issues/4

# MDZ-27-AA stuck in DNL: fastboot reboot bootloader accepted but never reaches 2nd stage

Device: Xiaomi Mi TV Stick 4K (MDZ-27-AA). Stuck on Mi logo, likely after an OTA (history not fully known).

What I did:
- Windows 11, Zadig 2.9 -> WinUSB on DNL (1B8E:C004), fix-adnl-guid.ps1 applied (2 instances updated), Google USB Driver r13 installed via pnputil.
- A14 package mi-tv-stick-4k_14_26.6.10_91, SHA-256 verified.

Symptoms:
- check-usb-mode.ps1 always returns DNL. The device does NOT cycle on the bus by itself; it stays present.
- `fastboot devices` shows "???????????? fastboot".
- With fastboot waiting first and the stick plugged in after: `fastboot reboot bootloader` prints "Rebooting into bootloader" and then hangs (no OKAY). A 1-second poll of check-usb-mode.ps1 for 90 s shows DNL the whole time, never absent, never FASTBOOT.
- `fastboot getvar product` fails with "Write to device failed (no link)" or "Status read failed (Too many links)".
- On one USB port, after reboot bootloader, Windows showed "Unknown USB Device (Device Descriptor Request Failed)" instead.

Is there another way to reach the 2nd stage from here, or should I use the DNL route (and which package, A11 1440 or A14 250303_01)?

### [6] twrp too many links

URL: https://github.com/TeamWin/android_bootable_recovery/issues/409

# twrp too many links

- i am running an official build TWRP, downloaded from https://twrp.me/Devices/
- i am running the latest version of TWRP 
- i have read the FAQ  https://twrp.me/FAQ/
- i have search this issues and still find the solution 

STEP WILL REPRODUCE THE PROBLEM

1. open cmd and fastboot flash boot recovery.img and this step is success
2. and i type fastboot  boot recovery.img 
3. and (failed (( status read failed( too many links))
