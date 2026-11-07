#!/usr/bin/env python3
"""HBM-FORM-SPLIT-13-OPSB RE-FORM recipes (opt-in variants; ot_hgi_sfu_opsb_output itself unchanged):
ot_hgi_sfu_opsb_output__rreg2 / __rreg1 = the part 41 OT_OPSB_N32 form + OT_OPSB_RREG=2/1 (bank-local read register, RREG 2
also the registered read-network output) + CTS without macro-tree delay buffers (cts_delay_buffer_derate 0).
recipes_rreg.py RECIPES_B2_JSON SRC_SHA"""
import json, sys
p, src = sys.argv[1], sys.argv[2]
raw = open(p).read(); d = json.loads(raw)
assert json.dumps(d, indent=2, ensure_ascii=False) + "\n" == raw, "recipes_b2.json does not round-trip"
base = d["ot_hgi_sfu_opsb_output"]
assert base.get("defines") == ["OT_OPSB_N32"], base.get("defines")
for r in (2, 1):
    d[f"ot_hgi_sfu_opsb_output__rreg{r}"] = dict(
        base, defines=["OT_OPSB_N32", f"OT_OPSB_RREG={r}"], cts_delay_buffer_derate=0,
        source=base["source"] + f"; HBM-FORM-SPLIT-13-OPSB RE-FORM (vB/vC TT -483/-452: SRAM rd_out -> 16:1 select -> "
               f"700 um haul in one cycle; CTS-0033 10 macro-tree delay buffers ~229 ps): OT_OPSB_RREG={r} bank-local read "
               f"register{' + registered read-network output' if r == 2 else ''}, CTS -delay_buffer_derate 0 (HBM-SFUHW2 10-18 "
               f"precedent); PIN CYCLES sr_d/sr_rv +{r}; lock-step bench results/die_hbm_1106/opsb_rreg",
        source_commit=src)
open(p, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n"); print("recipes rreg2/rreg1 ->", src)
