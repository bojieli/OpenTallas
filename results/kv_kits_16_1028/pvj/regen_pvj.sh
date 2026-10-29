#!/bin/bash
# KV-KITS-16 (2026-10-28): ot_qwen_tp8_pv_join_t R0 + fR180 kits with the one-hot operand-select RTL fix
# (rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv, this branch; old-vs-new random bench + MUT mutant:
# results/kv_kits_16_1028/pvj/pvj_onehot_eq.sh). Base = the KV-KITS-7 kits (routed, NOT signed: 4ea738599325 R0 TT setup
# -57.34 / 49aa312a473a fR180 -41.61, js decode fanout 46/17/28 loads, slew 218 ps into the adder s1 cone).
# Changes, nothing else (regen_pv.sh form):
#   (1) kit rtl ot_qwen_tp8_pv_wide_pair__leaf.sv: the same g_join select patch as the release file (pvj_patch.py),
#       module text == release module text except the __leaf name (checked below, fail closed);
#   (2) entry-trunk census: + the 176 new kept select flops (g_join[0..15].sa[1..6] / sb[1..5], $_DFF_PN0_ like js),
#       PREDICTED names; core_infra re-installed from pv_trunk_slice.json with that census (CI.install, main). The census
#       MUST be re-derived from the kit's own 1_synth_odb.v (census_from_synth form) before CTS / enqueue;
#   (3) --cts-setup-only + --two-mode-grt (gen_core_kit_kv.cts_setup_only / timing_modes_stage) and main tool copies
#       (face_guard lec rtl_lint sdc_lint straps vclk_corner run_kit_kv.sh + signoff bundle); freeze/PROVENANCE rewritten.
# usage (intel2, clean checkout of this branch): regen_pvj.sh OUTDIR
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
OLD=/srv/opentallas-scratch2/claude/kv-kits-7-1028/pvj
O=${1:?OUTDIR}
D=$REPO/results/kv_kits_16_1028/pvj
for V in r0/ot_qwen_tp8_pv_join_t__172.8x172.8 fr180/ot_qwen_tp8_pv_join_t__172.8x172.8_fR180; do
  K=$OLD/$V; N=$O/$(basename $V)
  rm -rf "$N"; mkdir -p "$N"
  rsync -a --exclude run --exclude signoff --exclude views --exclude lec --exclude __pycache__ \
    --exclude 'autopilot_chain_*' --exclude 'preflight_autopilot_*' --exclude preflight.json \
    --exclude 1_synth_odb.v --exclude 'synth_odb_v.*' --exclude 'face_guard*.json' --exclude 'face_guard*.log' \
    --exclude 'rtl_lint.json' --exclude rtl_lint.log --exclude rtl_lint.ys --exclude 'selrange.*' \
    --exclude dont_use_check.json --exclude adder_map_dontuse.json --exclude sdc_lint.log \
    --exclude lec_run.log --exclude run_place.log --exclude run_route.log --exclude run_finish.log --exclude signoff.log \
    --exclude pin_audit.json "$K/" "$N/"
  python3 "$D/pvj_patch.py" "$N/rtl/ot_qwen_tp8_pv_wide_pair__leaf.sv"
  cmp <(sed -n "/^module ot_qwen_tp8_pv_join_t #/,/^endmodule/p" "$REPO/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv") \
      <(sed -n "/^module ot_qwen_tp8_pv_join_t__leaf #/,/^endmodule/p" "$N/rtl/ot_qwen_tp8_pv_wide_pair__leaf.sv" | sed "s/module ot_qwen_tp8_pv_join_t__leaf/module ot_qwen_tp8_pv_join_t/")
  for f in face_guard.py lec.py rtl_lint.py sdc_lint.py straps.py vclk_corner.tcl; do cp "$REPO/tools/die_plan/$f" "$N/$f"; done
  cp "$REPO/physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh" "$N/run_kit_kv.sh"
  python3 -I "$REPO/tools/die_plan/signoff.py" bundle "$N"
  python3 - "$REPO" "$N" <<'EOF'
import json, sys
from pathlib import Path
repo, kd = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(repo / "physical/die_plan/qwen_kvsys/cores/harden"), str(repo / "tools/die_plan")]
import gen_core_kit_kv as GK
import core_infra as CI
import lec as LEC
cen = json.loads((kd / "pv_clock_census.json").read_text())
old_n = len(cen["sinks"])
add = [f"u_leaf.g_join\\[{g}\\].{r}\\[{k}\\]$_DFF_PN0_/CLK" for g in range(16) for r, n in (("sa", 6), ("sb", 5)) for k in range(1, n + 1)]
assert not set(add) & set(cen["sinks"])
cen["sinks"] = cen["sinks"] + add
cen["kv_kits_16"] = dict(added_predicted=len(add), rule="one-hot select copies sa[1..6]/sb[1..5] per lane, async reset like js; "
                         "PREDICTED names: re-derive from 1_synth_odb.v before CTS")
(kd / "pv_clock_census.json").write_text(json.dumps(cen, indent=1) + "\n")
sl = json.loads((kd / "pv_trunk_slice.json").read_text())
lf = sl["core_tree"]["leaves"][0]
lf["sinks"], lf["domain_sinks"] = cen["sinks"], len(cen["sinks"])
CI.install(kd, sl)
(kd / "pv_trunk_slice.json").write_text(json.dumps(sl, indent=1) + "\n")
t = (kd / "pv_trunk_install.tcl").read_text().replace(f"sinks{old_n}", f"sinks{len(cen['sinks'])}")
(kd / "pv_trunk_install.tcl").write_text(t)
cfg = (kd / "config.mk").read_text().splitlines()
if any("post_cts_setup.tcl" in l or "OT_HOLD_MM" in l for l in cfg):
    raise SystemExit("base kit already cts-setup-only / two-mode")
r = GK.cts_setup_only(kd, cfg)
(kd / "config.mk").write_text("\n".join(cfg) + "\n")
tm = GK.timing_modes_stage(kd)
fz = json.loads((kd / "freeze.json").read_text())
prov = LEC._repo_provenance(repo)
fz.update(kit_hash=GK.kit_hash(kd), source_commit=prov.get("commit"), cts_setup_only=r, timing_modes=tm,
          regen=dict(lane="KV-KITS-16", base_kit=f"kv-kits-7-1028/pvj/{kd.name}", base_source_commit=fz.get("source_commit"),
                     rtl_delta="pv_join g_join one-hot operand selects sa/sb (0 cycles)", census_added_predicted=len(add),
                     options=["--cts-setup-only", "--two-mode-grt"]))
(kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
LEC.write_kit_provenance(kd, repo, provenance=prov)
print("REGEN", kd.name, "kit_hash", fz["kit_hash"], "sinks", len(cen["sinks"]), "src", prov.get("commit"), tm)
EOF
done
