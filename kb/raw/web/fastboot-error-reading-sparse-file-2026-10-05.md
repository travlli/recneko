---
title: 网络检索素材：error: Sending sparse 'system' 3/5 FAILED (Error reading sparse file)
type: web-research
retrieved: 2026-10-05
query: "Error reading sparse file" fastboot
model: deepseek-v4.1-flash
tokens: 21378
urls:
  - "[1] [2.2.0] Fastboot flash failure is masked by successful service exit after USB transport failure during Secure Boot provisioning - https://github.com/raspberrypi/rpi-sb-provisioner/issues/335"
  - "[2] Unknown Error - https://github.com/ubports/ubports-installer/issues/3551"
  - "[3] ubtouch flash - https://github.com/ubports/ubports-installer/issues/3967"
  - "[4] Unknown Error - https://github.com/ubports/ubports-installer/issues/3605"
  - "[5] Unknown Error - https://github.com/ubports/ubports-installer/issues/3421"
---

# 检索到的原始材料（不可变，勿改）

> 这是 `tools/research_kb.py` 联网检索后抓到的正文原文，作为 wiki 条目的依据。
> 未经人工复核，**不是官方文档**。

## 模型基于以上材料给出的整理（未经人工复核）

## 症状

- 本次待排查报错为 `error: Sending sparse 'system' 3/5 FAILED (Error reading sparse file)`；资料中未出现完全相同的 `system` 3/5 片段。
- 资料 1 中，在 Raspberry Pi 5、Secure Boot provisioning、`sd` 场景下，通过 fastboot 刷写 root filesystem 时，前面已成功刷写多个 sparse chunks，到 `Sending sparse 'mapper/cryptroot' 20/58 (262140 KB)` 时出现 `FAILED (Error reading sparse file)`，随后 `fastboot: error: Command failed` [1]。
- 资料 1 中该失败发生在 Secure Boot enrollment 已完成之后；设备已进入 Secure Boot 模式，但操作系统镜像只写入了一部分，刷写停在 chunk 20/58 [1]。
- 资料 2、3、4、5 中，UBports Installer `0.10.0` 的 `fastboot:flash` 阶段出现 `Flashing failed`，stderr 包含 `FAILED (Error reading sparse file)` 和 `fastboot: error: Command failed` [2][3][4][5]。
- 资料 1 中，`fastboot` 报错后执行了 cleanup，最后 provisioning script 输出 `exit 0`，导致对应 systemd service 被报告为成功完成 [1]。
- 资料 3 同一日志中还出现其他 fastboot 错误，如 `FAILED (Write to device failed (Too many links))` 和 `FAILED (Write to device failed (Unknown error))` [3]。

## 原因

- 资料 1 的 fastbootd 控制台输出显示：`io_uring request failed: res = -108`、`ClientUSBTransport: read failed: Cannot send after transport endpoint shutdown`、`read expected 268431522 bytes, got 288768`、`Failed to write`、`Couldn't download data: Cannot send after transport endpoint shutdown` [1]。
- 资料 1 认为，这强烈表明 root cause 是 USB transport interruption/reset during a large bulk transfer，而不是 corrupted sparse image [1]。
- 资料 1 指出，客户端报告的是 `FAILED (Error reading sparse file)`，而 fastboot console 显示的实际原因是 USB transport shutdown，这使诊断真实问题变得困难 [1]。
- 资料 2、3、4、5 未给出该报错的原因，仅记录 `fastboot:flash` 失败和 `FAILED (Error reading sparse file)` [2][3][4][5]。

## 步骤

- 资料未给出针对该报错的具体修复或处理步骤；资料 1 列出的是期望行为和建议改进，不是已验证的修复步骤 [1]。
- 资料 1 建议：保留原始 `fastboot` 退出状态；返回非零退出码；明确报告 provisioning failed；保留诊断信息，或提供选项保留诊断信息；区分 Secure Boot enrollment completed、flashing incomplete、provisioning incomplete [1]。
- 资料 1 建议：不要用 `exit 0` 替换失败；报告 `FLASH_FAILED` 或 `FLASH_INTERRUPTED`；区分 USB transport failures 与 sparse image parsing failures [1]。
- 资料 1 中失败后实际执行了 cleanup：`rm -rf temporary directories`、`Deleting customised intermediates`，最后 `exit 0`；资料 1 明确指出这会使服务看起来成功并掩盖失败，不应视为修复 [1]。
- 资料 1 提到板子本身可恢复，但未给出具体恢复步骤 [1]。
- 资料 2、3、4、5 未给出处理办法 [2][3][4][5]。

## 验证

- 资料未说明如何确认该报错已修复，也未给出成功标准或验证命令 [1][2][3][4][5]。
- 资料 1 只说明期望行为：失败时应返回非零并明确报告失败、保留诊断信息、区分状态 [1]，但这不是验证修复的方法。
- 因此：资料不足，无法确认。

## 待确认

- 用户报错为 `Sending sparse 'system' 3/5`，资料 1 为 `Sending sparse 'mapper/cryptroot' 20/58` [1]，资料 2、3、4、5 未给出具体分区名和分块编号 [2][3][4][5]；资料未涉及 `system` 3/5 这一具体场景。
- 资料 2、3、4、5 没有 fastbootd 控制台输出；资料 1 有 [1][2][3][4][5]。需要用户补充完整 fastboot 输出和 fastbootd 控制台输出，以判断是否也是 `Cannot send after transport endpoint shutdown` 类 USB transport 问题 [1]。
- 资料未说明该错误是否与设备、安装器版本、目标系统、USB 端口/线缆/集线器、镜像文件可读性有关，需要用户补充这些信息 [1][2][3][4][5]。
- 资料未给出具体修复步骤和验证方法 [1][2][3][4][5]。
- 资料 1 提到需要区分 Secure Boot enrollment completed、flashing incomplete、provisioning incomplete [1]，但未说明用户当前处于哪个阶段；需要用户补充。

## 抓取到的来源正文

### [1] [2.2.0] Fastboot flash failure is masked by successful service exit after USB transport failure during Secure Boot provisioning

URL: https://github.com/raspberrypi/rpi-sb-provisioner/issues/335

# [2.2.0] Fastboot flash failure is masked by successful service exit after USB transport failure during Secure Boot provisioning

# Fastboot flash failure is masked by successful service exit after USB transport failure during Secure Boot provisioning

## Environment

- Project: `rpi-sb-provisioner`
- Version: 2.2.0
- Target: Raspberry Pi 5
- Provisioning style: `secure-boot`
- Storage type: `sd`
- Bootloader firmware:
  `/usr/lib/firmware/raspberrypi/bootloader-2712/default/pieeprom-2026-05-11.bin`
- Gold master image:
  `<redacted>.img`

Configuration:

```text
CUSTOMER_KEY_FILE_PEM=/etc/rpi-sb-provisioner/keys/customer-key-<redacted>.pem
PROVISIONING_STYLE=secure-boot
RPI_DEVICE_STORAGE_TYPE=sd
RPI_DEVICE_FIRMWARE_FILE=/usr/lib/firmware/raspberrypi/bootloader-2712/default/pieeprom-2026-05-11.bin
```

---

## Summary

While provisioning a Raspberry Pi 5 in **Secure Boot** mode, a transient USB transport failure occurs during flashing of the root filesystem through fastboot.

`fastboot` correctly reports a failure.

However, after cleanup the provisioning service exits successfully (`exit 0`), making the provisioning attempt appear successful even though flashing stopped halfway.

This is especially problematic because the failure happens **after Secure Boot enrollment has already completed**.

The board itself is recoverable, but the successful service exit makes diagnostics difficult and may mislead automation into assuming provisioning completed successfully.

---

## Secure Boot enrollment completed successfully

The bootstrap stage completed successfully and programmed the Secure Boot configuration.

Bootstrap log:

```text
Keywriting completed. Silently rebooting for next phase.
```

After reboot, the board successfully entered the signed fastboot environment.

---

## Flashing started normally

The provisioning process successfully flashed multiple sparse chunks:

```text
Writing 'mapper/cryptroot'                         OKAY [  5.472s]

Sending sparse 'mapper/cryptroot' 15/58 (249172 KB) OKAY [25.244s]
Writing 'mapper/cryptroot'                          OKAY [ 5.343s]

Sending sparse 'mapper/cryptroot' 16/58 (256388 KB) OKAY [26.075s]
Writing 'mapper/cryptroot'                          OKAY [ 5.527s]

Sending sparse 'mapper/cryptroot' 17/58 (262140 KB) OKAY [26.747s]
Writing 'mapper/cryptroot'                          OKAY [ 5.763s]

Sending sparse 'mapper/cryptroot' 18/58 (233460 KB) OKAY [23.807s]
Writing 'mapper/cryptroot'                          OKAY [ 4.968s]

Sending sparse 'mapper/cryptroot' 19/58 (262140 KB) OKAY [26.721s]
Writing 'mapper/cryptroot'                          OKAY [ 5.387s]
```

---

## Failure

Chunk 20 failed:

```text
Sending sparse 'mapper/cryptroot' 20/58 (262140 KB)
FAILED (Error reading sparse file)

fastboot: error: Command failed
```

---

## fastbootd output

The fastboot console on the Raspberry Pi reported:

```text
io_uring request failed:
res = -108

ClientUSBTransport:
read failed:
Cannot send after transport endpoint shutdown

read expected 268431522 bytes, got 288768

Failed to write
Couldn't download data:
Cannot send after transport endpoint shutdown
```

Immediately afterwards fastbootd restarted its USB FunctionFS interface:

```text
Using io_uring for usb ffs

initializing functions

opening control endpoint
/dev/usb-ffs/fastboot/ep0

read descriptors
read strings
```

This strongly suggests that the root cause is a USB transport interruption/reset during a large bulk transfer rather than a corrupted sparse image.

---

## Cleanup

After `fastboot` reported an error, cleanup was executed:

```text
fastboot: error: Command failed

cleanup()

...
rm -rf temporary directories
...
Deleting customised intermediates
```

Finally the provisioning script finished with:

```text
exit 0
```

As a result, the corresponding systemd service is reported as having completed successfully.

---

## Expected behaviour

A failed flash operation should never be reported as a successful provisioning run.

The provisioning service should:

- preserve the original `fastboot` exit status;
- return a non-zero exit code;
- clearly report that provisioning failed;
- preserve diagnostics (or provide an option to preserve them);
- distinguish between:
  - Secure Boot enrollment completed;
  - flashing incomplete;
  - provisioning incomplete.

---

## Actual behaviour

After a USB transport failure:

- Secure Boot enrollment has already completed successfully;
- flashing stops during chunk 20/58;
- `fastboot` reports an error;
- cleanup removes temporary artifacts;
- the provisioning script exits with `exit 0`;
- the systemd service therefore appears successful despite the failed provisioning.

---

## Why this is problematic

This failure occurs **after Secure Boot enrollment**.

At this point the device has already transitioned into Secure Boot mode, while the operating system image has only been partially written.

The board itself is recoverable, but the successful service exit makes it unnecessarily difficult to determine what actually happened and may mislead higher-level automation into assuming provisioning completed successfully.

---

## Suggested improvements

1. Preserve the original `fastboot` exit code after cleanup.

2. Never replace a failed provisioning attempt with `exit 0`.

3. Preserve diagnostic artifacts (or provide an option to preserve them) after failed flashing.

4. Report an explicit provisioning state such as:

```text
FLASH_FAILED
```

or

```text
FLASH_INTERRUPTED
```

instead of reporting success.

5. If possible, distinguish USB transport failures from sparse image parsing failures. In this case the client reports:

```text
FAILED (Error reading sparse file)
```

while the fastboot console indicates that the actual reason was a USB transport shutdown:

```text
Cannot send after transport endpoint shutdown
```

which makes diagnosing the real problem significantly harder.

--- 评论 ---
Same masking class, one stage earlier — worth f

### [2] Unknown Error

URL: https://github.com/ubports/ubports-installer/issues/3551

# Unknown Error

**UBports Installer `0.10.0` (AppImage)**
Environment: `LinuxMint 21.2 Victoria linux 5.15.0-88-generic x64 NodeJS v18.12.1`
Device: [`lavender`](https://github.com/ubports/installer-configs/blob/120be2cd71613ca217f71a60a909597cd4064c82/v2/devices/lavender.yml) ([Xiaomi Redmi Note 7](https://devices.ubuntu-touch.io/device/lavender/))
Target OS: Ubuntu Touch
Settings: `{"bootstrap":true,"wipe":true,"channel":"20.04/arm64/android9plus/stable"}`
OPEN-CUTS run: *N/A* <!-- Uploading logs failed. Please add them manually: https://github.com/ubports/ubports-installer#logs -->
Pastebin: https://snip.hxrsh.in/ubi-1699792599843

**Previous Errors:**
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)fastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)fastboot: error: Command failed"}
    at /tmp/.mount_ubportVdXiRh/resources/app.asar.unpacked/node_modules/promise-android-tools/lib/module.cjs:1121:15
    at /tmp/.mount_ubportVdXiRh/resources/app.asar.unpacked/node_modules/promise-android-tools/node_modules/cancelable-promise/dist/CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"Warning: skip copying boot image avb footer (boot partition size: 0, boot image size: 36286464).fastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"Warning: skip copying boot image avb footer (boot partition size: 0, boot image size: 36286464).fastboot: error: Command failed"}
    at /tmp/.mount_ubportVdXiRh/resources/app.asar.unpacked/node_modules/promise-android-tools/lib/module.cjs:1121:15
    at /tmp/.mount_ubportVdXiRh/resources/app.asar.unpacked/node_modules/promise-android-tools/node_modules/cancelable-promise/dist/CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
<!-- thank you for reporting! -->

### [3] ubtouch flash

URL: https://github.com/ubports/ubports-installer/issues/3967

# ubtouch flash

**UBports Installer `0.10.0` (exe)**
Environment: `Microsoft Windows 10 Professionnel 10.0.19045 Windows 10.0.19045 x64 19045 0.0 NodeJS v18.12.1`
Device: [`algiz`](https://github.com/ubports/installer-configs/blob/758eb4d41da10f628fa0bd51a9361beb302c2b2f/v2/devices/algiz.yml) ([Volla Phone Quintus](https://devices.ubuntu-touch.io/device/algiz/))
Target OS: Ubuntu Touch
Settings: `{"bootstrap":true,"wipe":true,"channel":"20.04/arm64/android9plus/stable"}`
OPEN-CUTS run: *N/A* <!-- Uploading logs failed. Please add them manually: https://github.com/ubports/ubports-installer#logs -->
Pastebin: *N/A* <!-- Uploading logs failed. Please add them manually: https://github.com/ubports/ubports-installer#logs -->

try to flash ubtouch coming from volla os and cant boot ubtouch and flash doesnt work well


**Previous Errors:**
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)\rfastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)\rfastboot: error: Command failed"}
    at C:\Users\hikag\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\hikag\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: fastboot:format: Error: formatting failed: Error: {"error":{"code":1,"cmd":"C:\\Users\\hikag\\AppData\\Local\\Temp\\2OtAFsnV2Em3s1DrbrINBarrFLV\\resources\\app.asar.unpacked\\node_modules\\android-tools-bin\\dist\\win32\\x86\\fastboot.exe format:ext4 userdata"},"stderr":"FAILED (Write to device failed (Too many links))\r\nfastboot: error: Command failed"}
stack trace: Error: formatting failed: Error: {"error":{"code":1,"cmd":"C:\\Users\\hikag\\AppData\\Local\\Temp\\2OtAFsnV2Em3s1DrbrINBarrFLV\\resources\\app.asar.unpacked\\node_modules\\android-tools-bin\\dist\\win32\\x86\\fastboot.exe format:ext4 userdata"},"stderr":"FAILED (Write to device failed (Too many links))\r\nfastboot: error: Command failed"}
    at C:\Users\hikag\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1250:15
    at C:\Users\hikag\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)\rfastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)\rfastboot: error: Command failed"}
    at C:\Users\hikag\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\hikag\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Write to device failed (Unknown error))\rfastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Write to device failed (Unknown error))\rfastboot: error: Command failed"}
    at C:\Users\hikag\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\hikag\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
<!-- thank you for reporting! -->

### [4] Unknown Error

URL: https://github.com/ubports/ubports-installer/issues/3605

# Unknown Error

**UBports Installer `0.10.0` (exe)**
Environment: `Майкрософт Windows 10 Домашняя для одного языка 10.0.19045 Windows 10.0.19045 x64 19045 0.0 NodeJS v18.12.1`
Device: `lavender`
Target OS: undefined
Settings: `{}`
OPEN-CUTS run: *N/A* <!-- Uploading logs failed. Please add them manually: https://github.com/ubports/ubports-installer#logs -->
Pastebin: *N/A* <!-- Uploading logs failed. Please add them manually: https://github.com/ubports/ubports-installer#logs -->

**Previous Errors:**
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"fastboot: error: cannot load 'C:\\Users\\Slava\\AppData\\Roaming\\ubports\\lavender\\firmware\\unpacked_droidian\\data\\vendor.img': No such file or directory"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"fastboot: error: cannot load 'C:\\Users\\Slava\\AppData\\Roaming\\ubports\\lavender\\firmware\\unpacked_droidian\\data\\vendor.img': No such file or directory"}
    at C:\Users\Slava\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\Slava\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)\rfastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)\rfastboot: error: Command failed"}
    at C:\Users\Slava\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\Slava\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"nt))\rfastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"nt))\rfastboot: error: Command failed"}
    at C:\Users\Slava\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\Slava\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
<!-- thank you for reporting! -->

### [5] Unknown Error

URL: https://github.com/ubports/ubports-installer/issues/3421

# Unknown Error

**UBports Installer `0.10.0` (exe)**
Environment: `Microsoft Windows 10 Education 10.0.19045 Windows 10.0.19045 x64 19045 0.0 NodeJS v18.12.1`
Device: [`surya`](https://github.com/ubports/installer-configs/blob/b750ffb887886c7cf6e9757a4426409c316fe29c/v2/devices/surya.yml) ([Xiaomi Poco X3 NFC](https://devices.ubuntu-touch.io/device/surya/))
Target OS: Ubuntu Touch
Settings: `{"bootstrap":true,"wipe":true,"channel":"16.04/arm64/android9/stable"}`
OPEN-CUTS run: *N/A* <!-- Uploading logs failed. Please add them manually: https://github.com/ubports/ubports-installer#logs -->
Pastebin: https://snip.hxrsh.in/ubi-1691354479668

**Previous Errors:**
```
Error: plugin wait(): Error: {"message":"{\"error\":{\"code\":3221225781,\"cmd\":\"C:\\\\Users\\\\Maddog\\\\AppData\\\\Local\\\\Temp\\\\2OtAFsnV2Em3s1DrbrINBarrFLV\\\\resources\\\\app.asar.unpacked\\\\node_modules\\\\android-tools-bin\\\\dist\\\\win32\\\\x86\\\\heimdall.exe detect\"}}","name":"heimdall"}
stack trace: Error: {"message":"{\"error\":{\"code\":3221225781,\"cmd\":\"C:\\\\Users\\\\Maddog\\\\AppData\\\\Local\\\\Temp\\\\2OtAFsnV2Em3s1DrbrINBarrFLV\\\\resources\\\\app.asar.unpacked\\\\node_modules\\\\android-tools-bin\\\\dist\\\\win32\\\\x86\\\\heimdall.exe detect\"}}","name":"heimdall"}
    at C:\Users\Maddog\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:117:20
    at ChildProcess.exithandler (node:child_process:430:5)
    at ChildProcess.emit (node:events:513:28)
    at maybeClose (node:internal/child_process:1091:16)
    at Socket.<anonymous> (node:internal/child_process:449:11)
    at Socket.emit (node:events:513:28)
    at Pipe.<anonymous> (node:net:313:12)
```
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)\rfastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"FAILED (Error reading sparse file)\rfastboot: error: Command failed"}
    at C:\Users\Maddog\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\Maddog\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"fastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"fastboot: error: Command failed"}
    at C:\Users\Maddog\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\Maddog\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: fastboot:flash: Error: Flashing failed: {"error":{"code":1},"stderr":"fastboot: error: Command failed"}
stack trace: Error: Flashing failed: {"error":{"code":1},"stderr":"fastboot: error: Command failed"}
    at C:\Users\Maddog\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:1121:15
    at C:\Users\Maddog\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\node_modules\cancelable-promise\dist\CancelablePromise.js:27:18
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
```
```
Error: plugin wait(): Error: {"message":"{\"error\":{\"code\":3221225781,\"cmd\":\"C:\\\\Users\\\\Maddog\\\\AppData\\\\Local\\\\Temp\\\\2OtAFsnV2Em3s1DrbrINBarrFLV\\\\resources\\\\app.asar.unpacked\\\\node_modules\\\\android-tools-bin\\\\dist\\\\win32\\\\x86\\\\heimdall.exe detect\"}}","name":"heimdall"}
stack trace: Error: {"message":"{\"error\":{\"code\":3221225781,\"cmd\":\"C:\\\\Users\\\\Maddog\\\\AppData\\\\Local\\\\Temp\\\\2OtAFsnV2Em3s1DrbrINBarrFLV\\\\resources\\\\app.asar.unpacked\\\\node_modules\\\\android-tools-bin\\\\dist\\\\win32\\\\x86\\\\heimdall.exe detect\"}}","name":"heimdall"}
    at C:\Users\Maddog\AppData\Local\Temp\2OtAFsnV2Em3s1DrbrINBarrFLV\resources\app.asar.unpacked\node_modules\promise-android-tools\lib\module.cjs:117:20
    at ChildProcess.exithandler (node:child_process:430:5)
    at ChildProcess.emit (node:events:513:28)
    at maybeClose (node:internal/child_process:1091:16)
    at ChildProcess._handle.onexit (node:internal/child_process:302:5)
```
<!-- thank you for reporting! -->
