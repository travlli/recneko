"""Platform / mode / error-code detection tests.

Includes regression tests for a real defect: a bare SP Flash Tool error code
(``ERROR 4032``) produced ``platform=unknown`` while retrieval correctly found
the MTK page, so the report contradicted itself - "未能判定平台" immediately
followed by an MTK solution.
"""

from __future__ import annotations

import pytest

from mirecovery.scanner import analyze

# (log text, expected platform)
CASES = [
    (
        "SP Flash Tool v5.2044\nBROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)\n"
        "[EMI] Enable DRAM failed!\n",
        "mtk",
    ),
    ("ERROR: Sahara Fail\nFailed to get sahara mode!!\nInvalid Firehose programmer\n",
     "qualcomm"),
    (
        "$ fastboot flash boot boot.img\nSending 'boot' (65536 KB)  OKAY\n"
        "Writing 'boot'  FAILED (remote: 'not allowed in locked state')\n",
        "fastboot",
    ),
    (
        "E:failed to mount /data (Invalid argument)\nE:Unable to mount storage\n"
        "Can't load Android system. Your data may be corrupt.\n",
        "recovery",
    ),
    (
        "dm-verity corruption\nYour device is corrupt. It can't be trusted\n"
        "AVB: vbmeta verification failed\n",
        "avb",
    ),
    ("$ fastboot devices\n< waiting for any device >\n", "fastboot"),
    ("Only nop and sig tag can be received before authentication\n", "qualcomm"),
    ("BROM ERROR : STATUS_BROM_CMD_SEND_DA_FAIL\n", "mtk"),
]

# Bare numeric error codes: the regression case.
BARE_ERROR_CODES = [
    ("ERROR 4032", "mtk"),
    ("ERROR 4004", "mtk"),
    ("ERROR 4008", "mtk"),
    ("ERROR 2004", "mtk"),
    ("ERROR 2005", "mtk"),
    ("ERROR 3004", "mtk"),
    ("ERROR: 4032", "mtk"),
]


@pytest.mark.parametrize("log,expected", CASES, ids=[c[1] for c in CASES])
def test_platform_detection(log, expected):
    assert analyze(log).platform == expected


@pytest.mark.parametrize("log,expected", BARE_ERROR_CODES, ids=[c[0] for c in BARE_ERROR_CODES])
def test_bare_error_code_still_identifies_platform(log, expected):
    """Regression: 'ERROR 4032' alone used to yield platform=unknown."""
    assert analyze(log).platform == expected


def test_unknown_for_unrelated_text():
    assert analyze("hello world 你好，今天天气不错").platform == "unknown"


def test_empty_input_is_safe():
    finding = analyze("")
    assert finding.platform == "unknown"
    assert finding.confidence == 0.0


def test_mode_detection():
    assert "EDL" in analyze("QDLoader 9008").mode or analyze("QDLoader 9008").mode
    assert analyze("BROM ERROR").mode == "BROM 模式"


def test_error_codes_extracted():
    finding = analyze("BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)\nERROR 4008")
    joined = " ".join(finding.error_codes)
    assert "4032" in joined
    assert "4008" in joined


def test_confidence_is_bounded():
    finding = analyze("SP Flash Tool BROM ERROR STATUS_BROM_CMD_SEND_DA_FAIL ERROR 4032")
    assert 0.0 <= finding.confidence <= 1.0
