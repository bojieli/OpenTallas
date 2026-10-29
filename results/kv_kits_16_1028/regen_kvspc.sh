#!/bin/bash
# KV-KITS-16 (2026-10-28): qkd_kvs_pc (124 instances, one GDS) release kit on current main.
# Base = the KV-KITS-10 kit kvspc_land7 (QK-CORES-7 q5c39 kit 52abcc31 + the RM195 land_d[7] literal-0 line; kit LEC
# EQUIVALENT 90970/90970, kept_registers 6149 missing 0, KV-KITS-13 CHECKED). Plan check: hm_r26q15d kv3_pc type differs
# from q5c39 only by clock.core_taps="early" (kvs_pc has no macros/early taps), pins file cores/qkd_kvs_pc_pins_r25.json
# sha 1331ffaa = kit pins_sha256 (CHECKED). The original generator inputs (kv-cores-1025r core json sources,
# wt/kv-kits-7-1027) are deleted, so this is the regen_pv.sh form: the kit files are carried and ONLY these change:
#   (1) --cts-setup-only (gen_core_kit_kv.cts_setup_only): SKIP_CTS_REPAIR_TIMING + setup-only POST_CTS repair, FF hold
#       only in the GRT step;
#   (2) --two-mode-grt (gen_core_kit_kv.timing_modes_stage = tools/die_plan/kit_modes.py stage, COORD 19:44 "all NEW KV
#       kits"): GRT hold repair in one two-mode session (scene tc TT setup vclk 250 / scene BC FF hold vclk 202.5);
#   (3) tool copies refreshed from main as gen_core_kit_kv copies them: run_kit_kv.sh (two-mode branch), lec.py, straps.py,
#       rtl_lint/sdc_lint/vclk_corner, signoff bundle (signoff.py bundle, incl. data_droop.py / kit_modes.py);
#       freeze.json kit_hash / source_commit / regen record + PROVENANCE.json rewritten.
# rtl/, pins.json, io.tcl, constraint.sdc, pdn, face_flops*, island_ft*, kvr2_reserve.tcl: byte-identical to the base.
# usage (intel2, from a CLEAN checkout of this branch): regen_kvspc.sh BASE_KIT OUTDIR
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
K=${1:?BASE_KIT}
O=${2:?OUTDIR}
T=qkd_kvs_pc__397.44x362.88
N=$O/$T
mkdir -p "$O"; rm -rf "$N"; mkdir -p "$N"
rsync -a --exclude run --exclude signoff --exclude views --exclude lec --exclude __pycache__ \
  --exclude 'autopilot_chain_*' --exclude 'preflight_autopilot_*' --exclude preflight.json \
  --exclude 1_synth_odb.v --exclude 'synth_odb_v.*' --exclude 'face_guard*.json' --exclude 'face_guard*.log' \
  --exclude 'rtl_lint.json' --exclude rtl_lint.log --exclude rtl_lint.ys --exclude 'selrange.*' \
  --exclude dont_use_check.json --exclude adder_map_dontuse.json --exclude sdc_lint.log \
  --exclude lec_run.log --exclude run_place.log --exclude run_route.log --exclude signoff.log --exclude pin_audit.json \
  --exclude ft_interface.json "$K/" "$N/"
for f in face_guard.py lec.py rtl_lint.py sdc_lint.py straps.py vclk_corner.tcl; do
  cp "$REPO/tools/die_plan/$f" "$N/$f"
done
cp "$REPO/physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh" "$N/run_kit_kv.sh"
python3 -I "$REPO/tools/die_plan/signoff.py" bundle "$N"
python3 - "$REPO" "$N" <<'EOF'
import json, sys
from pathlib import Path
repo, kd = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(repo / "physical/die_plan/qwen_kvsys/cores/harden"), str(repo / "tools/die_plan")]
import gen_core_kit_kv as GK
import lec as LEC
cfg = (kd / "config.mk").read_text().splitlines()
if any("post_cts_setup.tcl" in l for l in cfg) or any("OT_HOLD_MM" in l for l in cfg):
    raise SystemExit("base kit already cts-setup-only / two-mode")
r = GK.cts_setup_only(kd, cfg)
GK._ms().plan_tree_cts(kd, cfg)   # as the generator: no plan tree in this kit -> unchanged
import ft_ports as FT
(kd / "ft_interface.json").write_text(json.dumps(FT.model_skeleton(json.loads((kd / "ft_ports.json").read_text())), indent=1) + "\n")
(kd / "config.mk").write_text("\n".join(cfg) + "\n")
tm = GK.timing_modes_stage(kd)
fz = json.loads((kd / "freeze.json").read_text())
prov = LEC._repo_provenance(repo)
fz.update(kit_hash=GK.kit_hash(kd), source_commit=prov.get("commit"), cts_setup_only=r, timing_modes=tm,
          regen=dict(lane="KV-KITS-16", base_kit="kv-kits-10-1028/kvspc_land7/kit (intel1)",
                     base_source_commit=fz.get("source_commit"), plan_check="hm_r26q15d 2c3a183d: kv3_pc type == q5c39 except clock.core_taps; pins_r25 sha 1331ffaa",
                     options=["--cts-setup-only", "--two-mode-grt"],
                     tools_refreshed=["face_guard.py", "lec.py", "rtl_lint.py", "sdc_lint.py", "straps.py",
                                      "vclk_corner.tcl", "run_kit_kv.sh", "signoff bundle"]))
(kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
LEC.write_kit_provenance(kd, repo, provenance=prov)
print("REGEN", kd.name, "kit_hash", fz["kit_hash"], "src", prov.get("commit"), "modes", tm)
EOF
