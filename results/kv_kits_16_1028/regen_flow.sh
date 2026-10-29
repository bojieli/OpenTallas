#!/bin/bash
# KV-KITS-16 (2026-10-28): generic regen_pv.sh-form re-kit of a carried KV core kit on current main.
# Carried: rtl/, pins.json, io.tcl, constraint.sdc, pdn, face_flops*, island_ft*, hooks (byte-identical to BASE).
# Changes ONLY: (1) --cts-setup-only (gen_core_kit_kv.cts_setup_only), (2) --two-mode-grt (gen_core_kit_kv.timing_modes_stage,
# COORD 19:44: all new KV kits), (3) main tool copies (face_guard lec rtl_lint sdc_lint straps vclk_corner run_kit_kv.sh +
# signoff bundle), (4) optional config.mk knob edits KEY=VALUE (existing 'export KEY = ' lines only; e.g. the COORD-accepted
# e2/e6 near-miss knobs HOLD_SLACK_MARGIN / OT_HOLD_FF_MARGIN 10, SLEW_MARGIN 40). freeze.json + PROVENANCE.json rewritten.
# usage (intel2, CLEAN checkout of this branch): regen_flow.sh BASE_KIT OUTDIR [KEY=VALUE ...]
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
K=${1:?BASE_KIT}; O=${2:?OUTDIR}; shift 2
T=$(basename "$K"); N=$O/$T
mkdir -p "$O"; rm -rf "$N"; mkdir -p "$N"
rsync -a --exclude run --exclude signoff --exclude views --exclude lec --exclude __pycache__ \
  --exclude 'autopilot_chain_*' --exclude 'preflight_autopilot_*' --exclude preflight.json \
  --exclude 1_synth_odb.v --exclude 'synth_odb_v.*' --exclude 'face_guard*.json' --exclude 'face_guard*.log' \
  --exclude 'rtl_lint.json' --exclude rtl_lint.log --exclude rtl_lint.ys --exclude 'selrange.*' \
  --exclude dont_use_check.json --exclude adder_map_dontuse.json --exclude sdc_lint.log \
  --exclude lec_run.log --exclude run_place.log --exclude run_route.log --exclude run_finish.log --exclude signoff.log \
  --exclude pin_audit.json --exclude 'replica_check_odb.json' --exclude ft_interface.json "$K/" "$N/"
for f in face_guard.py lec.py rtl_lint.py sdc_lint.py straps.py vclk_corner.tcl; do cp "$REPO/tools/die_plan/$f" "$N/$f"; done
cp "$REPO/physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh" "$N/run_kit_kv.sh"
python3 -I "$REPO/tools/die_plan/signoff.py" bundle "$N"
python3 - "$REPO" "$N" "$K" "$@" <<'EOF'
import json, sys
from pathlib import Path
repo, kd, base, knobs = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4:]
sys.path[:0] = [str(repo / "physical/die_plan/qwen_kvsys/cores/harden"), str(repo / "tools/die_plan")]
import gen_core_kit_kv as GK
import lec as LEC
cfg = (kd / "config.mk").read_text().splitlines()
if any("post_cts_setup.tcl" in l for l in cfg) or any("OT_HOLD_MM" in l for l in cfg):
    raise SystemExit("base kit already cts-setup-only / two-mode")
edits = {}
for kv in knobs:
    k, v = kv.split("=", 1)
    hits = [i for i, l in enumerate(cfg) if l.startswith(f"export {k} = ")]
    if len(hits) != 1:
        raise SystemExit(f"knob {k}: {len(hits)} 'export {k} = ' lines")
    edits[k] = [cfg[hits[0]].split(" = ", 1)[1], v]
    cfg[hits[0]] = f"export {k} = {v}"
r = GK.cts_setup_only(kd, cfg)
GK._ms().plan_tree_cts(kd, cfg)
if (kd / "ft_ports.json").is_file():
    import ft_ports as FT
    (kd / "ft_interface.json").write_text(json.dumps(FT.model_skeleton(json.loads((kd / "ft_ports.json").read_text())), indent=1) + "\n")
(kd / "config.mk").write_text("\n".join(cfg) + "\n")
tm = GK.timing_modes_stage(kd)
fz = json.loads((kd / "freeze.json").read_text())
prov = LEC._repo_provenance(repo)
fz.update(kit_hash=GK.kit_hash(kd), source_commit=prov.get("commit"), cts_setup_only=r, timing_modes=tm,
          regen=dict(lane="KV-KITS-16", base_kit=base, base_source_commit=fz.get("source_commit"),
                     options=["--cts-setup-only", "--two-mode-grt"], knobs=edits,
                     tools_refreshed=["face_guard.py", "lec.py", "rtl_lint.py", "sdc_lint.py", "straps.py",
                                      "vclk_corner.tcl", "run_kit_kv.sh", "signoff bundle"]))
(kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
LEC.write_kit_provenance(kd, repo, provenance=prov)
print("REGEN", kd.name, "kit_hash", fz["kit_hash"], "src", prov.get("commit"), "knobs", edits, "modes", tm)
EOF
