#!/usr/bin/env python3
"""DIE-HBM/KITS 10-27 (UNCOMMITTED PROPOSAL): generate a kit for a pgslice canon type (type-reduction family) with
gen_core_kit_hbm.py unchanged.  The canon module has no recipe key in the views table; its RTL is exactly the family's
canonical top (member recipe: same files/top), wired by the canon wrapper from mk_canon_wrappers.py.
  run_canon_kit.py WT FIXES <gen args...>          (gen args as mk_c18.py passes them: --views --view --out --master-slice --trial --tag)
Adds: --recipe-key <canon> (recipe = member recipe, + synth_memory_max_bits 256*61 for the exp family as the generator
does for lane_exp<n>), --wrapper FIXES/canon_wrappers/<canon>.sv, and for lane_exp canon the family macro placement
FIXES/B2n_inputs/exp_lane.json (= git physical/die_plan/hbm_arch/B2n_inputs/exp_lane.json) at u_core.u_bank.u_data.g_read[k].u_m."""
import json, re, sys
from pathlib import Path
WT, FIX = Path(sys.argv[1]), Path(sys.argv[2])
args = sys.argv[3:]
HERE = WT / "physical/die_plan/hbm_arch_cores"
sys.path.insert(0, str(HERE))
import gen_core_kit_hbm as G  # noqa: E402

MEMBER = {  # canon -> member recipe key (same functional_type/top/files; members listed in C19 type_reduce_report.json)
    "ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691": "ot_hbm_su_static_pgslice_lg__lane_exp2__440.64x457.92",
    "ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77": "ot_hbm_su_static_pgslice_lg__lanes0_3__587.52x933.12",
    "ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526": "ot_hbm_su_static_pgslice_lg__lanes_plain0_3__440.64x457.92",
}
view = args[args.index("--view") + 1]
module = view.split("@")[0]
if module not in MEMBER:
    raise SystemExit(f"not a canon pgslice view: {view}")
R = G.load_recipes()
rec = dict(R[MEMBER[module]])
# every member of the family must carry the same files/top/params (else the alias is not exact)
fam = [k for k, v in R.items() if v.get("functional_type") == rec.get("functional_type")]
for k in fam:
    for f in ("files", "top", "params", "defines", "macros"):
        if R[k].get(f) != rec.get(f):
            raise SystemExit(f"ALIAS_NOT_EXACT {module}: {k}.{f} differs from {MEMBER[module]}")
rec["alias_of"] = MEMBER[module]
rec["alias_note"] = "DIE-HBM/KITS 10-27: canon type-reduction family; RTL = member recipe, wiring = canon wrapper"
extra = ["--recipe-key", module, "--wrapper", str(FIX / "canon_wrappers" / f"{module}.sv")]
if "__lane_exp__" in module:
    rec["synth_memory_max_bits"] = max(256 * 61, rec.get("synth_memory_max_bits", 0))
    extra += ["--macro-placement", str(FIX / "B2n_inputs" / "exp_lane.json"),
              "--macro-inst-fmt", "u_core.u_bank.u_data.g_read[{k}].u_m"]
sys.argv = ["gen_core_kit_hbm.py"] + args + extra
G.main(recipe_overrides={module: rec})
