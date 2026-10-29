"""lec.py relayout never reverses a PACKED vector (DIE-KV-32-LEC 10-29: KV-014 q0 u_b `reg [1:0] lmax_any_i` was
reversed on a downstream simulation gain and left 4 false NOT EQUIVALENT points).  slang drives a packed vector from
one `$driver$x` cell and an unpacked array from one `$driver$x[i]` cell per element.
    python3 -m pytest -q tools/die_plan/test_lec_relayout_packed.py"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402


def _aliases(tmp_path):
    j = {"modules": {"lec_top": {
        "netnames": {"u_dut.u.p": {"hide_name": 0, "bits": [30, 31]},
                     "u_dut.u.one": {"hide_name": 0, "bits": [40]},
                     "u_dut.q": {"hide_name": 0, "bits": [20, 21, 22, 23, 10, 11, 12, 13]},
                     "$flatten\\u_dut.$p$3": {"hide_name": 1, "bits": [30, 31]}},
        "cells": {"$flatten\\u_dut.\\u.$driver$p": {"type": "$aldff", "connections": {"Q": [30, 31]}},
                  "$flatten\\u_dut.\\u.$driver$one": {"type": "$dff", "connections": {"Q": [40]}},
                  "$flatten\\u_dut.$driver$q[0]": {"type": "$aldff", "connections": {"Q": [10, 11, 12, 13]}},
                  "$flatten\\u_dut.$driver$q[1]": {"type": "$aldff", "connections": {"Q": [20, 21, 22, 23]}}}}}}
    f = tmp_path / "gold.aliases.json"
    f.write_text(json.dumps(j))
    return f


def test_packed_vectors_from_unindexed_driver_cells(tmp_path):
    p = lec.slang_packed_vectors(_aliases(tmp_path))
    assert p == {"ff:u_dut.u.p"}                     # unpacked q and 1-bit one are not listed
    assert lec.slang_packed_vectors(tmp_path / "missing.json") == frozenset()


def test_relayout_skips_packed_bases():
    class FakeL:                                     # relayout must not even simulate a flip of a packed base
        matched = {"ff:u.p[0]", "ff:u.p[1]"}
        tp = {"ff:u.p[0]": 2, "ff:u.p[1]": 4}
        tc = {}
        dlit = {("gold", "ff:u.p[0]"): 0, ("gate", "ff:u.p[0]"): 1, ("gold", "ff:u.p[1]"): 0,
                ("gate", "ff:u.p[1]"): 1}

        def build(self, with_compare, with_hyp):
            class M:
                def simulate(self, words, seed):
                    return [0, 0, 0, 0], 0xFF
            return M(), {}
    L = FakeL()
    calls = []
    orig = lec.lit_val
    lec.lit_val = lambda val, mask, lit: lit
    try:
        log = []
        lec.relayout(L, log, packed={"ff:u.p"})
        assert not any("relayout" in x for x in log) and L.tp == {"ff:u.p[0]": 2, "ff:u.p[1]": 4}
    finally:
        lec.lit_val = orig
