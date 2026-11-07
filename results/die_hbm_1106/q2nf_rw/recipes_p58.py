#!/usr/bin/env python3
"""HBM d44v part 58 recipes: ot_q2nf_rest -> OT_Q2NF_RW masters; old form kept as ot_q2nf_rest__r2c2.  recipes_p58.py RECIPES_B2_JSON SRC_SHA"""
import json, sys
p, src = sys.argv[1], sys.argv[2]
raw = open(p).read(); d = json.loads(raw)
assert json.dumps(d, indent=2, ensure_ascii=False) + "\n" == raw, "recipes_b2.json does not round-trip"
k = "ot_q2nf_rest"; old = d[k]
if "OT_Q2NF_RW" in old.get("defines", []): sys.exit("already applied")
d[k + "__r2c2"] = dict(old, source=old["source"] + "; kept as the fallback r2c2 form by d44v part 58")
d[k] = dict(old, defines=old["defines"] + ["OT_Q2NF_RW"],
            macros=["ot_sram_1r1w_256x256_m2_r0c0_g256", "ot_sram_1r1w_64x141_m1_r0c0_g141", "ot_sram_1rw_256x64_m4_r2c2"],
            source=old["source"] + "; DIE-HBM-83-Q2R d44v part 58: OT_Q2NF_RW right-width masters, bench results/die_hbm_1106/q2nf_rw, PIN CYCLES 0",
            source_commit=src)
open(p, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n"); print("recipes", k, "->", src)
