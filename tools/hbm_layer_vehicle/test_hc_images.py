#!/usr/bin/env python3
"""VEH-FMT-COLL2/HC: self-test of hc_images.py (qhub word layout vs the RTL field slices, calendar grants validated by
hbm_vm_static_calendar, fixture data reconstruction, replay event ordering).  Run: PYTHONPATH=tools python3 -m
hbm_layer_vehicle.test_hc_images"""
import re

import numpy as np

from hbm_layer_vehicle import hc_images as H

RTL = H.ROOT / "rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_q_static.sv"


def test_fields():
    txt = RTL.read_text()
    got = {}
    for m in re.finditer(r"(?:wire\s*(?:\[\d+:\d+\])?\s*)?(\w+)=c\[(\d+)(?::(\d+))?\]", txt):
        hi, lo = int(m.group(2)), int(m.group(3) or m.group(2))
        got[m.group(1)] = (lo, hi - lo + 1)
    for m in re.finditer(r",(\w+)=c\[(\d+):(\d+)\]", txt):
        got[m.group(1)] = (int(m.group(3)), int(m.group(2)) - int(m.group(3)) + 1)
    assert got == H.FIELDS, (got, H.FIELDS)
    assert "ot_vms_calendar_static #(.W(79))" in txt
    w = H.qhub_word(store_slot=1, result_base=0x48, store_position=5)
    assert (w >> 59) & 1 and (w >> 60) & 0xffff == 0x48 and (w >> 76) == 5


def test_record():
    rng = np.random.default_rng(1)
    A = rng.integers(0, 1 << 32, 24, dtype=np.uint64).astype(np.uint32)
    O = rng.integers(0, 1 << 32, 24, dtype=np.uint64).astype(np.uint32)
    g = H.mix_post_record(A, O, 30)
    data = {e["cyc"]: int(e["val"], 16) for e in g["chk"] if e["port"] == "hc_SW__gathered_mix_data"}
    assert [data[c] for c in sorted(data)] == [int(x) for x in A]
    vm = {int(e["port"][3:], 16): int(e["val"], 16) for e in g["chk"] if e["port"].startswith("vm:")}
    got = [(vm[g["o_sector"] + j // 8] >> (32 * (j % 8))) & 0xffffffff for j in range(24)]
    assert got == [int(x) for x in O]
    res = [e for e in g["events"] if e.get("port") == "hc_eng__result"][0]
    assert res["cyc"] == g["result_pins_after"] == g["gather_row0_at"] - 1 + H.EMIT_AFTER_ROW0
    # store word s sampled at word0_edge[1] + s; result pinned one edge before
    assert g["word0_edge"][1] + g["store_word"] - 2 == res["cyc"]
    for kw in (dict(res_shift=1), dict(grant_shift=1), dict(flip=3)):
        H.mix_post_record(A, O, 30, **kw)


if __name__ == "__main__":
    test_fields()
    test_record()
    print("test_hc_images PASS")
