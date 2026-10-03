---
title: MiFlash 常见报错：couldn't find flash script / 发送配置参数失败 / 系统找不到指定的文件
tags: [qualcomm, xiaomi, miflash, flashing, windows]
keywords: [couldn't find flash script, 发送配置参数失败, 系统找不到指定的文件, The device is not in EDL mode, MiFlash 报错, 无法刷机]
author: deepseek-agent
created: 2026-10-02
updated: 2026-10-02
sources: []
platform: qualcomm
---

# MiFlash 常见报错：couldn't find flash script / 发送配置参数失败 / 系统找不到指定的文件

## 症状

MiFlash 能打开、也能看到端口，但点刷机立刻弹出下列任一错误（示例）：

```text
couldn't find flash script
```

```text
发送配置参数失败
```

```text
系统找不到指定的文件。
```

```text
The device is not in EDL mode
```

多数情况下进度条根本不启动，或者走到「正在发送配置参数」附近就中断，设备仍停在 9008。

## 原因

- `couldn't find flash script`：MiFlash 里选的目录不是 ROM 的刷机脚本层。工具需要在所选目录下找到 `flash_all.bat` 一类的脚本（以及 `images` 等子目录）；常见错误是多选/少选了一层目录，或下载到的 tgz/zip 根本没解压。
- `系统找不到指定的文件`：脚本引用的某个镜像/工具在包内不存在——解压不完整、被杀软删掉、路径含中文或空格、磁盘空间不足都会造成这种情况。
- `发送配置参数失败`：与设备通信在配置/firehose 阶段中断，通常是 USB 链路、驱动、programmer 不匹配，或 COM 口被其他软件占用（协议侧细节见 [[qualcomm-sahara-firehose-error]]）。
- `The device is not in EDL mode`：设备当前不是 9008 状态，或端口是 900E 之类的诊断口，MiFlash 无法识别（见 [[qualcomm-edl-9008-enter]]）。

## 步骤

1. **先做通用准备**：把 ROM 解压到纯英文、无空格、层级很浅的路径（如 `D:\rom\`），关闭杀软实时防护后重新解压一次，确保包完整；刷机时不要开其他刷机工具或串口软件。
2. **处理 `couldn't find flash script`**：在 MiFlash 里把路径精确指到含 `flash_all.bat`（或对应刷机脚本）和 `images\` 的那一层。注意既不要选进 `images` 子目录，也不要选到解开后多套一层的父目录。确认拿到的是 fastboot 线刷包（带脚本），而不是未解压的卡刷包。
3. **处理 `系统找不到指定的文件`**：打开所选目录下的 `flash_all.bat`，看它引用了哪些文件名，逐个确认这些文件真实存在。缺失就重新下载/解压完整包；若 ROM 路径含中文或空格，改到纯英文短路径后重试。
4. **处理 `发送配置参数失败`**：换原装数据线和主板后置 USB 2.0 口、去掉 Hub；按 [[qualcomm-edl-9008-enter]] 重新进 9008；使用官方 ROM 包内自带的 firehose programmer；仍失败则改用 QFIL 刷同一套镜像做交叉验证，判断是包的问题还是 MiFlash/端口的问题。
5. **处理 `The device is not in EDL mode`**：打开设备管理器「端口 (COM 和 LPT)」，确认存在 `Qualcomm HS-USB QDLoader 9008 (COMx)`。没有就重新 `adb reboot edl` 或短接测试点；是 900E 就说明没进 EDL，不能继续刷。
6. **换工具交叉验证**：MiFlash 反复失败时，用 QFIL 以 Flat Build 方式刷同一 ROM 的镜像（`rawprogram*.xml` + `patch*.xml`）。QFIL 能成功就说明包本身没问题，问题在 MiFlash 侧或目录/脚本层。
7. **保留日志**：失败后不要立刻关窗口，先截图错误弹窗；MiFlash 会在 ROM 目录或临时目录留下日志（具体位置随版本不同），保留完整日志便于定位。

## 验证

- MiFlash 进度条正常推进到 100%，状态显示刷机成功；
- 设备自动重启并进入系统；设备管理器里 9008 端口消失，出现正常的 Android / MTP 设备；
- 若进度走完但设备不开机或反复重启，见 [[qualcomm-qdl-mode-stuck-bootloop]]；若在写分区阶段报写入失败，见 [[qualcomm-emmc-ufs-flash-write-failure]]。

## 待确认

- 各 MiFlash 版本日志文件的确切存放路径；
- 特定版本 `发送配置参数失败` 是否附带更具体的子错误码；
- 各版本 MiFlash 对目录层级（能否直接选含 `flash_all.bat` 的目录）的具体要求是否有差异。
