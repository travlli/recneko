---
title: 网络检索素材：手机屏幕显示 press any key to shutdown
type: web-research
retrieved: 2026-10-05
query: "press any key to shutdown" fastboot xiaomi
model: deepseek-v4.1-flash
tokens: 13534
urls:
  - "[1] Does the drm suspend/wakeup works? - https://github.com/map220v/sm8150-mainline/issues/12"
  - "[2] add blog post about setting up linageos on my xiaomi mi mix 3 - https://github.com/andreashappe/snikt.net/pull/24"
  - "[3] Trying to install without usb3 fix in Windows 10/11 - https://github.com/ubports/ubports-installer/issues/2327"
---

# 检索到的原始材料（不可变，勿改）

> 这是 `tools/research_kb.py` 联网检索后抓到的正文原文，作为 wiki 条目的依据。
> 未经人工复核，**不是官方文档**。

## 模型基于以上材料给出的整理（未经人工复核）

## 症状
- 在 Windows 10/11 中安装时，每次在设备连接电脑的情况下重启到 fastboot，或在进入 fastboot 后连接设备，会立即收到消息 “Press any key to shutdown”；按下设备上任意硬键后设备关机。[3]
- 使用 adb 工具和 fastboot 命令运行 `fastboot devices` 时，有时能获得响应而不显示 “Press any key to shutdown”，但设备名显示一堆 `???????????`。[3]
- 资料 3 中的场景为：UBports Installer `0.8.9-beta` (exe)，Windows 11 Pro 10.0.22000，设备 dipper，目标 OS Ubuntu Touch。[3]
- 资料 1 讨论的是 sm8150 dual dsi 的 suspend/resume 问题，会出现 “clock stuck in on/off state”、重启等，但未提到 “Press any key to shutdown”。[1]
- 资料 2 未描述 “Press any key to shutdown” 症状。[2]

## 原因
- 在一些 Xiaomi 设备上，Windows 操作系统不能正确识别设备，从而导致 fastboot 出现该错误。[3]
- 资料中认为需要注册表修复，以允许 Windows 通过 fastboot 驱动正确识别设备。[3]
- 资料 1 和资料 2 未说明 “Press any key to shutdown” 的原因。[1][2]

## 步骤
- 资料中用户给出的处理办法是向注册表添加以下 3 个 additions；该做法来自社区 issue 用户报告，属于社区经验，且涉及修改 Windows 注册表，资料未说明风险。[3]
- 资料给出的 3 条注册表命令如下 [3]：

```bat
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "osvc" /t REG_BINARY /d "0000" /f
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "SkipContainerIdQuery" /t REG_BINARY /d "01000000" /f
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "SkipBOSDescriptorQuery" /t REG_BINARY /d "01000000" /f
```

- 以上命令均来自资料 3。[3]
- 资料中用户建议：要么将此修复加入 installer，要么写入网站安装步骤，或两者都做。[3]
- 资料 1 和资料 2 未给出针对该报错的处理办法。[1][2]

## 验证
- 资料中用户表示，添加这些注册表项后，所有问题都解决了，安装继续进行，没有再出现任何问题。[3]
- 因此可据此确认：不再出现 “Press any key to shutdown”，且安装可继续。[3]
- 资料未给出其他验证步骤或命令。[3]

## 待确认
- 其他 Xiaomi 设备、其他 Windows 版本、其他 UBports Installer 版本、其他目标 OS 是否适用，资料未涉及。[3]
- 注册表修改是否需要重启、如何回滚、具体权限要求，资料未涉及。[3]
- 资料未说明该报错是否与资料 1 中的 sm8150 dual dsi suspend/resume、“clock stuck in on/off state” 或重启有关。[1]
- 资料未说明非 Windows、非 fastboot 场景下是否会出现该报错。[3]
- 资料未说明如何获取该报错对应的日志；资料 1 提到通过 ssh 获取 dmesg 日志，以及 ramoops(pstore) 将内核日志保存到 DDR 地址 `0xb0000000`，重启后仍保留，但未将其与 “Press any key to shutdown” 关联。[1]
- 资料 2 未涉及该报错。[2]

## 抓取到的来源正文

### [1] Does the drm suspend/wakeup works?

URL: https://github.com/map220v/sm8150-mainline/issues/12

# Does the drm suspend/wakeup works?

Does the drm/dsi suspend works, can i suspend my screen and the wakeup it without any crash and fatal for UX bugs.
One important question, does hibernate to disk works? Eg, no crashes after resuming from image

--- 评论 ---
Unfortunately it's broken on sm8150 with dual dsi since kernel 6.2, when dsi suspends or resumes it gives errors like: clock stuck in on/off state, on kernel 6.1 without this issue, there is no UX, OpenGL and Vulkan context crashes or bugs when suspending or resuming.

If linux hibernate doesn't require uefi varstore then it should work same way as on regular linux PC.

--- 评论 ---
> Unfortunately it's broken on sm8150 with dual dsi since kernel 6.2, when dsi suspends or resumes it gives errors like: clock stuck in on/off state, on kernel 6.1 without this issue, there is no UX, OpenGL and Vulkan context crashes or bugs when suspending or resuming.
> 
> If linux hibernate doesn't require uefi varstore then it should work same way as on regular linux PC.

Does it mean kernel will panic on resume/suspend? I sawed commit for drm resume/suspend fix https://github.com/maverickjb/linux-6.1.10/commit/7c923106caddb4e08e63696f29fee062ab99d107 from maverickjb, only difference is gdsc.c, i updated it in my fork, but same as you i cant test it now :(

--- 评论 ---
First dsi will give critical errors, then it will reboot because of unstable clock driver or dsi driver state.
I think gdsc.c issues were already fixed in older kernels, right now dsi issue seem to be releated to devlink and dsi cyclic dependencies.

--- 评论 ---
> First dsi will give critical errors, then it will reboot because of unstable clock driver or dsi driver state. I think gdsc.c issues were already fixed in older kernels, right now dsi issue seem to be releated to devlink and dsi cyclic dependencies.

Well, if screen is suspended it will crash on resume, any ideas of fixing this? Did you have kernel log of crash? What parts of kernel/dts is related to dsi clocks, devlink and dsi cyclic dependencies? How can i debug my tablet's kernel via usb, without dissambling it and any external hardware?

Edit: https://github.com/torvalds/linux/commit/9187ebb954ab2afe0e79e0ff7771e94d3d1d9e1c https://github.com/torvalds/linux/commit/d09ec6f9877798a2a66c9d5de524b419e2c064bb https://github.com/torvalds/linux/commits/master/drivers/gpu/drm/msm/dsi maybe this commits can be related to our problem? Or just try to downgrade dsi drivers?

--- 评论 ---
> > First dsi will give critical errors, then it will reboot because of unstable clock driver or dsi driver state. I think gdsc.c issues were already fixed in older kernels, right now dsi issue seem to be releated to devlink and dsi cyclic dependencies.
> 
> Well, if screen is suspended it will crash on resume, any ideas of fixing this? Did you have kernel log of crash? What parts of kernel/dts is related to dsi clocks, devlink and dsi cyclic dependencies? How can i debug my tablet's kernel via usb, without dissambling it and any external hardware?

I don't have kernel logs from mainline, you can check [this code](https://github.com/map220v/sm8150-mainline/blob/nabu-6.7/drivers/gpu/drm/msm/dsi/phy/dsi_phy_7nm.c) it controls dsi clocks. For devlink and it's cyclic dependecies handling check latest [nabu-6.0-rc1](https://github.com/map220v/sm8150-mainline/commits/nabu-6.0-rc1) commits.
Idk if linux has support for usb debugging, dwc3 driver on linux probably doesn't support that.

> Edit: [torvalds/linux@9187ebb](https://github.com/torvalds/linux/commit/9187ebb954ab2afe0e79e0ff7771e94d3d1d9e1c) [torvalds/linux@d09ec6f](https://github.com/torvalds/linux/commit/d09ec6f9877798a2a66c9d5de524b419e2c064bb) https://github.com/torvalds/linux/commits/master/drivers/gpu/drm/msm/dsi maybe this commits can be related to our problem? Or just try to downgrade dsi drivers?

These commits doesn't seem to be releated to this issue. Downgrading dsi most likely won't help, because issue seem to be somewhere else, this error "clock stuck in on/off state" is also happens for UFS on boot, I fixed it temporarly by adding sleep functions in clock enable/disable, but it seems that ufs driver still has chance to crash at boot.

--- 评论 ---
Now only left two annoing parts, waiting for bootloader unlock and debugging. I wont close this issue until, i/you/we found a solution for this, if you can give me more info about this it may be very helpful

--- 评论 ---
How to get kernel crash log for debugging if screen is black(or it isnt?), does it save logs or dump files, if it does, where are they?

--- 评论 ---
> How to get kernel crash log for debugging if screen is black(or it isnt?), does it save logs or dump files, if it does, where are they?

I use ssh to get logs from dmesg, there is also [ramoops(pstore)](https://github.com/map220v/sm8150-mainline/blob/9894da172d3f6433475489d2d3332dd7b437c105/arch/arm64/boot/dts/qcom/sm8150-xiaomi-nabu.dts#L128) it saves kernel logs to ddr region at address 0xb0000000 that is persistent between reboots.

--- 评论 ---
> > How to get kernel crash log for debugging if screen is black(or it isnt?), does it save logs or dump files, if it does, where are they?
> 
> I use ssh to get logs from dmesg, there is also [ramoops(pstore)](https://github.com/map220v/sm8150-mainline/blob/9894da172d3f6433475489d2d3332dd7b437c105/arch/arm64/boot/dts/qcom/sm8150-xiaomi-nabu.dts#L128) it saves kernel logs to ddr region at address 0xb0000000 that is persistent between reboots.

But how to get thoose logs from there?

--- 评论 ---
> > > How to get kernel crash log for debugging if screen is black(or it isnt?), does it save logs or dump files, if it does, where are they?
> > 
> > 
> > I use ssh to get logs from dmesg, there is also [ramoops(pstore)](https://github.com/map220v/sm8150-mainline/blob/9894da172d3f6433475489d2d3332dd7b437c105/arch/arm64/boot/dts/qcom/sm8150-xiaomi-nabu.dts#L128) it saves kernel logs to ddr region at address 0xb0000000 that is

### [2] add blog post about setting up linageos on my xiaomi mi mix 3

URL: https://github.com/andreashappe/snikt.net/pull/24

# add blog post about setting up linageos on my xiaomi mi mix 3

--- 评论 ---
## Deploying snikt-net with &nbsp;<a href="https://pages.dev"><img alt="Cloudflare Pages" src="https://user-images.githubusercontent.com/23264/106598434-9e719e00-654f-11eb-9e59-6167043cfa01.png" width="16"></a> &nbsp;Cloudflare Pages

<table><tr><td><strong>Latest commit:</strong> </td><td>
<code>211533d</code>
</td></tr>
<tr><td><strong>Status:</strong></td><td>⚡️&nbsp; Build in progress...</td></tr>
</table>

[View logs](https://dash.cloudflare.com/?to=/f92da3477e5f5ead5ba6d57200669633/pages/view/snikt-net/df127448-333b-4117-9fe9-d8608c639606)

### [3] Trying to install without usb3 fix in Windows 10/11

URL: https://github.com/ubports/ubports-installer/issues/2327

# Trying to install without usb3 fix in Windows 10/11

**UBports Installer `0.8.9-beta` (exe)**
Environment: `Microsoft Windows 11 Pro 10.0.22000 win32 10.0.22000 x64 22000 0.0 NodeJS v12.18.3`
Device: dipper
Target OS: Ubuntu Touch
Settings: `undefined`
OPEN-CUTS run: *N/A*
Log: *N/A*


Trying to install in Windows 10/11 I would get an error. After trying many times many things, I figured out that you need a registry fix to allow windows to properly recognize the device through the fastboot driver. Every time I would reboot to fastboot while having it connected to the computer or connect it after I entered fastboot I would get immediately the message "Press any key to shutdown" and after pressing any hard key on the device it would shutdown. I used the adb tools and the fastboot command to run fastboot devices and the times that I managed to get an answer without showing the message "Press any key to shutdown", it showed a bunch of ??????????? as the device name. After searching the internet for what could cause this behavior, I found out that in some Xiaomi devices, the windows operating system wouldn't properly recognize the device and cause this error to the fastboot. After some more searching the internet, I found the solution to this problem. Turns out you need to add the following 3 additions to the registry.

reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "osvc" /t REG_BINARY /d "0000" /f
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "SkipContainerIdQuery" /t REG_BINARY /d "01000000" /f
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\usbflags\18D1D00D0100" /v "SkipBOSDescriptorQuery" /t REG_BINARY /d "01000000" /f

After doing this, all the issues got resolved and the installation proceeded without any further issues.

My suggestion is to either add this fix to the installer or write it down in the installation steps on the website. Or both!
Thank you for your time!

<!-- thank you for reporting! -->
