"""The packed window DMA record must pin the current RTL and bench."""

import json

from tools.rtl_chip_v41x_window_kv_prefetch import OUTPUT, sources


def test_record_is_current():
    record = json.loads(OUTPUT.read_text())
    assert record["status"] == "pass"
    assert record["sources"] == sources()
    assert record["checks"]["errors"] == 0
    assert record["checks"]["stale_fault"] == 1
