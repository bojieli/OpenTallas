#!/usr/bin/env python3
"""S81 iq_C / kv512_C: drop the 6 ot_sram_1r1w2c_128x64_m1 sites (DIE-S81-60 11-05).

Their u_xg master is ot_s81sl_xg -> ot_s81sl_xs, which holds block exponents in flops and has no g_ex SRAM.  Only
ot_s81sl_xgt_xo -> ot_s81sl_xs4 has them, the other 14 C types.  The netlists hold 7 ROM + 24 SRAM + 0 u_em, so
delta_c_macro_sites_1105.py's rows stop these two types at MPL-0020.  Other sites do not move.

usage: delta_c_em_drop_1105.py PLAN_IN PLAN_OUT INSTANCES_JSON
"""
import json
import sys
from pathlib import Path

TYPES = ("dsdv_slice_iq_C__t1", "dsdv_slice_kv512_C__t1")
MOD = "ot_sram_1r1w2c_128x64_m1"


def main():
    src, dst, ins = sys.argv[1:4]
    txt = Path(src).read_text()
    plan = json.loads(txt)
    for tn in TYPES:
        a = txt.index(f'\n  "{tn}": {{\n')
        b = txt.index('\n  },', a)
        block = txt[a:b]
        lines = block.split("\n")
        keep = [ln for ln in lines if f'"module":"{MOD}"' not in ln]
        assert len(lines) - len(keep) == 6, (tn, len(lines) - len(keep))
        block2 = "\n".join(keep)
        c = block2.index('"contents": [')
        e = block2.index("\n   ],\n", c)
        if block2[e - 1] == ",":
            block2 = block2[:e - 1] + block2[e:]
        txt = txt[:a] + block2 + txt[b:]
    after = json.loads(txt)
    assert set(after) == set(plan)
    for tn, t in plan["partition_types"].items():
        if tn not in TYPES:
            assert after["partition_types"][tn] == t, tn
            continue
        new = after["partition_types"][tn]
        assert new["contents"] == [c for c in t["contents"] if c.get("module") != MOD], tn
        assert {k: v for k, v in new.items() if k != "contents"} == {k: v for k, v in t.items() if k != "contents"}, tn
    Path(dst).write_text(txt)
    ev = json.loads(Path(ins).read_text())
    for tn in TYPES:
        del ev[tn][MOD]
    Path(ins).write_text(json.dumps(ev, indent=0) + "\n")
    print("dropped 6 x 2")


main()
