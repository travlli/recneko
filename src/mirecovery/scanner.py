"""Log analysis: pull platform, mode, device hints and error codes out of
pasted console output.

This module is intentionally self-contained and dependency-free so it can be
unit-tested without Toga or network access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Finding:
    """A classification result for one log blob."""

    platform: str = "unknown"
    """One of: mtk, qualcomm, fastboot, recovery, avb, unknown."""

    confidence: float = 0.0
    mode: str = ""
    device_hints: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    """Human-readable evidence lines explaining the classification."""

    @property
    def platform_label(self) -> str:
        return {
            "mtk": "MediaTek (MTK)",
            "qualcomm": "Qualcomm (骁龙)",
            "fastboot": "Fastboot / Bootloader",
            "recovery": "Recovery",
            "avb": "AVB / Verified Boot",
            "unknown": "未能判定",
        }.get(self.platform, self.platform)


# --------------------------------------------------------------------------
# Signature tables
# --------------------------------------------------------------------------

# Each signature: (regex, weight, human label)
_PLATFORM_SIGNATURES: dict[str, list[tuple[str, float, str]]] = {
    "mtk": [
        (r"\bBROM\b", 4.0, "BROM 关键字"),
        (r"\bBROM\s+ERROR\b", 6.0, "BROM ERROR 报错"),
        (r"STATUS_BROM_[A-Z_]+", 6.0, "BROM 状态码"),
        (r"STATUS_DA_[A-Z_]+", 6.0, "DA 状态码"),
        (r"SP\s*Flash\s*Tool", 6.0, "SP Flash Tool 日志"),
        (r"\bDownload\s*Agent\b|\bDA\b\s*(file|hash|download)", 3.0, "Download Agent"),
        (r"\bPreloader\b", 4.0, "Preloader"),
        (r"\bMT\d{4}\b", 3.0, "MTK 芯片型号"),
        (r"mtk[_\- ]?(usb|vcom|preloader)", 4.0, "MTK 驱动"),
        (r"\bDA_HASH_MISMATCH\b", 6.0, "DA 哈希不匹配"),
        (r"\bS_DA_[A-Z_]+", 6.0, "MTK 安全启动状态码"),
        # SP Flash Tool 的数字错误码（4032 / 2004 / 4008 / 3004 ...）。
        # 用户经常只贴一行「ERROR 4032」，此前这种输入平台判定为 unknown，
        # 报告会自相矛盾地同时说「未能判定平台」和给出 MTK 方案。
        (r"\bERROR[\s:_]*(?:[1-5]\d{3})\b", 5.0, "SP Flash Tool 数字错误码"),
        (r"\bS_(?:FT|DA|BROM|SEC|RT)_[A-Z_]{3,}", 6.0, "MTK 状态码前缀"),
    ],
    "qualcomm": [
        (r"\bSahara\b|\bsahara\b", 6.0, "Sahara 协议"),
        (r"\bFirehose\b|\bfirehose\b", 6.0, "Firehose 协议"),
        (r"\b9008\b|\b900E\b", 6.0, "Qualcomm 紧急下载模式"),
        (r"\bQDLoader\b", 6.0, "QDLoader 驱动"),
        (r"\bQFIL\b|\bQPST\b", 5.0, "高通刷机工具"),
        (r"\bMiFlash\b", 4.0, "MiFlash"),
        (r"\bEDL\b", 4.0, "EDL 模式"),
        (r"only nop and sig tag", 7.0, "Sahara 认证失败"),
        (r"\bprogrammer\b.*\b(fail|invalid|not\s*found)", 4.0, "firehose programmer"),
        (r"MSM\d{4}|\bSDM\d{3}\b|\bSM\d{4}\b", 3.0, "高通芯片型号"),
    ],
    "fastboot": [
        (r"\bfastboot\b", 6.0, "fastboot 命令"),
        (r"FAILED\s*\(remote:", 5.0, "fastboot 远程失败"),
        (r"< waiting for (any )?device >", 6.0, "等待设备"),
        (r"\bflashing unlock\b|\bfastboot oem unlock\b", 5.0, "解锁命令"),
        (r"not allowed in locked state", 6.0, "锁定状态限制"),
        (r"\bfastbootd\b", 5.0, "fastbootd 模式"),
        (r"\bvbmeta\b", 3.0, "vbmeta 分区操作"),
    ],
    "recovery": [
        (r"\bE:?\s*(Unable to mount|failed to mount|Can't mount)", 6.0, "recovery 挂载错误"),
        (r"failed to mount /data|unable to mount storage", 6.0, "data 分区挂载失败"),
        (r"\brecovery\b", 4.0, "recovery"),
        (r"Can't load Android system", 6.0, "系统无法加载"),
        (r"\bwipe data\b|factory reset", 3.0, "双清"),
        (r"\bsideload\b|\badb sideload\b", 4.0, "sideload 刷机"),
        (r"failed to read command|error:\s*closed", 4.0, "sideload 中断"),
        (r"\bTWRP\b|\bOrangeFox\b", 4.0, "第三方 recovery"),
        (r"@/cache/recovery|/sdcard/recovery\.log", 4.0, "recovery 日志路径"),
    ],
    "avb": [
        (r"dm-verity", 6.0, "dm-verity"),
        (r"\bAVB\b|\bavb\b", 5.0, "AVB"),
        (r"vbmeta verification failed", 7.0, "vbmeta 校验失败"),
        (r"device is corrupt", 6.0, "设备损坏提示"),
        (r"verified boot|\bverity\b", 5.0, "verified boot"),
        (r"disable-verity|disable-verification", 4.0, "关闭校验参数"),
    ],
}

# Mode detection runs independently of platform.
_MODE_SIGNATURES: list[tuple[str, str]] = [
    (r"\bBROM\b", "BROM 模式"),
    (r"\bPreloader\b", "Preloader 模式"),
    (r"\b(9008|900E)\b|QDLoader|EDL", "EDL / 9008 模式"),
    (r"< waiting for (any )?device >|\bfastbootd\b", "Fastboot / fastbootd"),
    (r"Can't load Android system|@/cache/recovery|recovery", "Recovery"),
]

# Common OEM / Xiaomi identifiers so the report can name the target device.
_DEVICE_PATTERNS: list[tuple[str, str]] = [
    (r"\b(2\d{3}[0-9A-Z]{2,}[0-9A-Z]*)\b", "机型代号"),
    (r"\bRedmi\s+[A-Za-z0-9 ]{1,20}", "Redmi 机型"),
    (r"\bXiaomi\s+[A-Za-z0-9 ]{1,20}", "Xiaomi 机型"),
    (r"\bMI\s?\d{1,2}\s?(Pro|Ultra|Lite|SE)?\b", "小米机型"),
    (r"\b(Poco|POCO)\s+[A-Za-z0-9 ]{1,20}", "POCO 机型"),
    (r"\b(codename|device)[\s:=]+([a-z][a-z0-9_]{2,20})", "设备代号字段"),
]

# Broad error-code sweep, used as fallback when platform rules do not fire.
_GENERIC_ERROR_PATTERNS: list[str] = [
    r"ERROR[\s:_]*\d{3,5}",
    r"STATUS_[A-Z][A-Z0-9_]{3,}",
    r"S_DA_[A-Z0-9_]{3,}",
    r"Sahara\s*Fail|Firehose\s*Fail",
    r"FAILED\s*\(remote:[^)]*\)",
    r"E:\s?[A-Za-z][^,\n]{3,60}",
    r"0x[0-9A-Fa-f]{4,}",
    # SP Flash Tool prints its code in parentheses right after a symbolic name,
    # e.g. "S_FT_ENABLE_DRAM_FAIL (4032)". Without this the most important
    # number in the log was not extracted at all.
    r"\bS_[A-Z][A-Z0-9_]{3,}\s*\(\s*\d{3,5}\s*\)",
    r"\(\s*\d{4}\s*\)",
]

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def clean_log(text: str) -> str:
    """Strip ANSI colour codes and normalise line endings."""
    text = _ANSI_RE.sub("", text or "")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def analyze(text: str) -> Finding:
    """Classify a log blob and extract actionable identifiers."""
    log = clean_log(text)
    finding = Finding()
    if not log.strip():
        return finding

    scores: dict[str, float] = {}
    for platform, signatures in _PLATFORM_SIGNATURES.items():
        total = 0.0
        for pattern, weight, label in signatures:
            if re.search(pattern, log, re.IGNORECASE):
                total += weight
                if label not in finding.signals:
                    finding.signals.append(f"{label}")
        if total:
            scores[platform] = total

    if scores:
        best = max(scores.items(), key=lambda kv: kv[1])
        finding.platform = best[0]
        # Confidence: share of evidence held by the winning platform, and how
        # much absolute evidence there was.
        total = sum(scores.values())
        share = best[1] / total if total else 0.0
        finding.confidence = round(min(1.0, 0.35 + 0.65 * share) * min(1.0, best[1] / 8.0), 2)

    # Mode
    for pattern, label in _MODE_SIGNATURES:
        if re.search(pattern, log, re.IGNORECASE):
            finding.mode = label
            break

    # Device hints
    for pattern, label in _DEVICE_PATTERNS:
        for match in re.finditer(pattern, log, re.IGNORECASE):
            value = match.group(0).strip()
            hint = f"{label}: {value}"
            if hint not in finding.device_hints:
                finding.device_hints.append(hint)
            if len(finding.device_hints) >= 5:
                break

    # Error codes (deduplicated, order preserved)
    for pattern in _GENERIC_ERROR_PATTERNS:
        for match in re.finditer(pattern, log, re.IGNORECASE):
            code = " ".join(match.group(0).split())
            if code and code not in finding.error_codes:
                finding.error_codes.append(code)
            if len(finding.error_codes) >= 12:
                break

    return finding
