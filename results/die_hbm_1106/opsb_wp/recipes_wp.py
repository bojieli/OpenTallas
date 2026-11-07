#!/usr/bin/env python3
"""HBM-FORM-SPLIT-14-OPSB RE-FORM recipes (opt-in variants; ot_hgi_sfu_opsb_output itself unchanged):
ot_hgi_sfu_opsb_output__wp1 / __wp2 = the part 41 OT_OPSB_N32 form + OT_OPSB_WP=1/2 (ot_hgi_su_lgroup2_wp.sv: per-column
kept write-record copies, bank-local regs, sr_d-face read copy; WP 2 also the registered decoded write record).
recipes_wp.py RECIPES_B2_JSON SRC_SHA"""
import json, sys
p, src = sys.argv[1], sys.argv[2]
raw = open(p).read(); d = json.loads(raw)
assert json.dumps(d, indent=2, ensure_ascii=False) + "\n" == raw, "recipes_b2.json does not round-trip"
base = d["ot_hgi_sfu_opsb_output"]
assert base.get("defines") == ["OT_OPSB_N32"], base.get("defines")
f = "rtl/hbm_accel/cores_split/reform_1105s/opstore/ot_hgi_su_lgroup2_wp.sv"
for w in (1, 2):
    d[f"ot_hgi_sfu_opsb_output__wp{w}"] = dict(
        base, defines=["OT_OPSB_N32", f"OT_OPSB_WP={w}"], files=list(base["files"]) + [f], cts_delay_buffer_derate=0,
        source=base["source"] + f"; HBM-FORM-SPLIT-14-OPSB RE-FORM (vD/vE routed TT -310/-308: lane-write decode + broadcast "
               f"in one cycle across 760 um, bank read regs placed at the sr_d face): OT_OPSB_WP={w} ot_hgi_su_lgroup2_wp "
               f"({'registered decoded write record + ' if w == 2 else ''}4 kept per-column copies, bank-local regs, sr_d-face read "
               f"copy); PIN CYCLES sr_d/sr_rv +{2 + w}, flt +{w}; lock-step bench results/die_hbm_1106/opsb_wp",
        source_commit=src)
open(p, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n"); print("recipes wp1/wp2 ->", src)
