---
title: 网络检索素材：error:Not catch checkpoint ($fastboot -s .*lock), flash is not done
type: web-research
retrieved: 2026-10-05
query: "Not catch checkpoint" miflash
model: deepseek-v4.1-flash
tokens: 4401
urls:
  - "[1] Android 手机 / 电视折腾 - https://github.com/hegya/blog/issues/1"
---

# 检索到的原始材料（不可变，勿改）

> 这是 `tools/research_kb.py` 联网检索后抓到的正文原文，作为 wiki 条目的依据。
> 未经人工复核，**不是官方文档**。

## 模型基于以上材料给出的整理（未经人工复核）

## 症状
题目给出的报错为 `error:Not catch checkpoint ($fastboot -s .*lock), flash is not done`。[1]  
资料中对应提到的是“MiFlash 错误 Not catch checkpoint”，并列出“MiFlash 错误 Not catch checkpoint 解决方法”的链接标题。[1]  
资料未说明该报错具体出现的刷机场景、设备型号、MiFlash 版本或操作步骤。[1]

## 原因
资料未给出该报错的原因。[1]  
资料不足，无法确认。[1]

## 步骤
资料未给出具体处理办法，仅出现“MiFlash 错误 Not catch checkpoint 解决方法”这一链接标题。[1]  
因此无法根据本资料写出可执行的处理步骤。[1]  
资料不足，无法确认。[1]

## 验证
资料未涉及如何验证该报错已修复。[1]  
资料不足，无法确认。[1]

## 待确认
- 该报错出现的具体场景、设备、MiFlash 版本、刷机包等信息：资料未涉及。[1]
- 报错原因：资料未涉及。[1]
- “MiFlash 错误 Not catch checkpoint 解决方法”链接中的具体步骤、命令及风险：资料未涉及。[1]
- 修复后的验证方式：资料未涉及。[1]

## 抓取到的来源正文

### [1] Android 手机 / 电视折腾

URL: https://github.com/hegya/blog/issues/1

# Android 手机 / 电视折腾

--- 评论 ---
- [状态栏隐藏图标方法](https://brain.best33.com/android-icon-blacklist)
`adb shell settings get secure icon_blacklist #获取隐藏列表`
`adb shell settings put secure icon_blacklist vpn`

--- 评论 ---
- [MiFlash 错误 Not catch checkpoint 解决方法](https://miuiver.com/miflash-error-not-catch-checkpoint/)

--- 评论 ---
- 折腾 Termux
  - 切换镜像 `termux-change-repo`
  - 设置本地存储 `termux-setup-storage`
  - 配置 SSH
  `pkg install openssh`
  `ssh-keygen -A //生成 ssh 密钥`
  `whoami //查看用户名`
  `passwd //设置密码，远程访问端口为 8022`
  - [安装 nginx 和 php](https://www.zhihuclub.com/152736.shtml)

--- 评论 ---
- 折腾 ADB
  - [下载](https://developer.android.com/tools/releases/platform-tools?hl=zh-cn)
  - 重启进 bootloader ` adb -d reboot bootloader `
  - 列出已连接的设备 ` fastboot devices `
  - fastboot 刷入 recovery.img ` fastboot flash recovery recovery.img `
  - fastboot 重启进 recovery ` fastboot boot recovery.img `
  - 侧载刷机包 ` adb -d sideload filename.zip `
  - 停用 bloatware
  ` adb shell pm uninstall --user 0 com.vivo.nps `
  ` adb shell pm disable-user com.android.quicksearchbox `
  ` adb shell pm uninstall --user 0 com.vivo.ai.base.copilot `
  ` adb shell pm uninstall --user 0 com.vivo.screenagent `
  ` adb shell pm uninstall --user 0 com.vivo.smartanswer `
  - 去除信号感叹号
  ` adb shell "settings put global captive_portal_https_url https://connect.rom.miui.com/generate_204" `
  ` adb shell "settings put global captive_portal_http_url http://connect.rom.miui.com/generate_204" `
  - 连接局域网设备 ` adb connect 192.168.0.15 `
  - 列出所有「已卸载但保留安装包」的应用 ` adb shell pm list packages -u `
  - 恢复应用 ` adb shell cmd package install-existing --user 0 <应用包名> `

--- 评论 ---
- 常用 APP
  - [`[Fcitx5]`](https://github.com/fcitx5-android/fcitx5-android)
  - [Via 浏览器](https://res.viayoo.com/v1/via-release-cn.apk)
  - [米家](https://app.market.xiaomi.com/hd/apm-h5-cdn/cdn-applinking.html?id=com.xiaomi.smarthome)
  - [阅读]()
