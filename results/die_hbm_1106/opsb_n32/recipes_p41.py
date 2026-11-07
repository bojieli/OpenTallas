#!/usr/bin/env python3
"""HBM d44v part 41 recipes: ot_hgi_sfu_opsb_output -> the OT_OPSB_N32 narrow-macro bank form; the old row-macro form
is kept under ot_hgi_sfu_opsb_output__row256 (fallback, byte-identical recipe).   recipes_p41.py RECIPES_B2_JSON SRC_SHA"""
import json, sys
p, src = sys.argv[1], sys.argv[2]
raw = open(p).read(); d = json.loads(raw)
assert json.dumps(d, indent=2, ensure_ascii=False) + "\n" == raw, "recipes_b2.json does not round-trip"
k = "ot_hgi_sfu_opsb_output"; old = d[k]
if "OT_OPSB_N32" in old.get("defines", []):
    sys.exit("already applied")
d[k + "__row256"] = dict(old, source=old["source"] + "; kept as the fallback row-macro form by d44v part 41")
d[k] = dict(old, defines=["OT_OPSB_N32"],
            files=old["files"] + ["rtl/hbm_accel/cores_split/reform_1105s/opstore/ot_hgi_su_lbank_n32.sv"],
            macros=["ot_sram_1r1w_2048x32_m8_r0c0_g32"],
            source=old["source"] + "; HBM-FORM-SPLIT-13-OPSB d44v part 41: OT_OPSB_N32 narrow-macro banks (16 x "
                   "ot_sram_1r1w_2048x32_m8_r0c0_g32, 90 signal pins each, was 823), lock-step bench "
                   "results/die_hbm_1106/opsb_n32 (0 errors, 4/4 mutants FAIL), PIN CYCLES 0",
            source_commit=src)
open(p, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n"); print("recipes", k, "->", src)
