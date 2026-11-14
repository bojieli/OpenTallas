#!/bin/bash
# S81 svc_lo kit-RTL post step: IRG pin-register defines (SVC-BAND-3 2026-11-13).
# Runs after `bind.py kit-rtl` (kit_wave.py kit_rtl_post_cmd inlines every tools/autopilot/kit_rtl_post.d/*.sh),
# cwd = wave source checkout; env TYPE, OUT (kit RTL dir with kit_rtl.json), PLAN (unused).
# Class: the S81 plan record binds the svc_lo IRG as dsdv_idx_rg3 #(.EL(140), .PR(1)) (S81-SVCRS-3 11-10: PR = IRG
# pin-register stages in the dsdv_idx_rg2_chunk slices, EL = 124 + 16 PR). Those stages exist only in the S81 svc
# fastpad slice copy, selected by OT_IDX_HSLICE_FASTPAD + OT_IDX_HSLICE_FP_CS (rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv
# 1072-1160); with PR != 0 and without them the chunk elaborates `$fatal` on purpose. The as-built define set of the
# wave bind lacks both, so every svc_lo kit (rs t1..t7, rs_w t1) failed GEN_LINT rtl_check
# ("dsdv_idx_rg2.sv:1096: Can't resolve task name `$fatal'"), before and after the memory closure.
# The step adds the two defines to kit_rtl.json "defines" (gen_phys.kit_rtl_defines carries them into the kit
# VERILOG_DEFINES / lint / LEC gold) only when the bound instantiates dsdv_idx_rg3[_fit] with PR != 0; any other kit
# is left byte-identical (exit 0). It fails if the fastpad slice sources are missing from kit_rtl.f.
set -euo pipefail
: "${TYPE:?TYPE must be a plan type}" "${OUT:?OUT must be the kit RTL directory}"
[ -f "$OUT/kit_rtl.json" ] || { echo "S81_IRG_PR: no $OUT/kit_rtl.json" >&2; exit 1; }
python3 -I - "$OUT" <<'PY'
import json, re, sys
from pathlib import Path
out = Path(sys.argv[1])
kj = out / "kit_rtl.json"
k = json.loads(kj.read_text())
bm = k.get("bound_module") or ""
if not bm.startswith("s81p_svc_"):
    sys.exit(0)
b = out / (bm + ".sv")
txt = b.read_text() if b.is_file() else ""
prs = [int(x) for x in re.findall(r"\bdsdv_idx_rg3(?:_fit)?\s*#\([^;]*?\.PR\((\d+)\)", txt, re.S)]
if not any(prs):
    print("S81_IRG_PR NOT_APPLICABLE", bm)
    sys.exit(0)
need = ["OT_IDX_HSLICE_FASTPAD", "OT_IDX_HSLICE_FP_CS"]
fl = (out / "kit_rtl.f").read_text() if (out / "kit_rtl.f").is_file() else ""
for src in ("ot_s81_svc_idx_hslice_fp.sv", "ot_hdc_v41x_idx_hslice_fp.sv", "dsdv_idx_rg2.sv"):
    assert src in fl, "S81_IRG_PR: PR %s needs %s in kit_rtl.f" % (prs, src)
d = k.get("defines") or []
add = [x for x in need if x not in d]
if add:
    k["defines"] = d + add
    k.setdefault("post_steps", []).append({"step": "s81_svc_irg_pr", "added_defines": add, "pr": prs})
    kj.write_text(json.dumps(k, indent=1) + "\n")
print("S81_IRG_PR APPLIED", bm, "PR", prs, "added", add)
PY
