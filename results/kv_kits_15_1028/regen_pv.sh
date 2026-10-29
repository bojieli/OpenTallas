#!/bin/bash
# KV-KITS-15 (2026-10-28) item 4: regenerate the kv3_pv_pair kits (R0 + fMX) from the DIE-KV-14b (b1) SRAM macro-leaf
# plan view (COORD ruling f823f65a0 16:54; RM230 core_infra stage_basis='total'), on current main.
# Base = the KV-KITS-10 kits (QK-CORES-11 plan tree + KV-KITS-8 macro channel + KV-KITS-10 on-grid macro sites; routed,
# DRT-0418 0, not signed: SRAM clk at depth 2 vs register leaves depth 4-6 -> related-pair skew 182/212 ps TT).
# Changes, nothing else:
#   (1) plan macro leaves: results/die_kv_14_1028/pv_pair/pv_macro_leaves.py install KIT (pv_tree_slice.json ->
#       br_j -> (S+1) x BUFx24 chain -> 2 SRAM clk, S = TritonCTS register stages; core_infra_* regenerated on main);
#   (2) --cts-setup-only (gen_core_kit_kv.cts_setup_only on main: SKIP_CTS_REPAIR_TIMING + setup-only POST_CTS repair
#       chained after leaf_affinity.tcl; FF hold only in the FF-only GRT step), as the other current KV kits;
#   (3) the pure tool copies refreshed from main (what gen_core_kit_kv on main copies): face_guard lec rtl_lint
#       sdc_lint signoff straps vclk_corner; freeze.json kit_hash/source_commit + PROVENANCE.json rewritten.
# usage (intel2, from a CLEAN checkout of this branch): regen_pv.sh OUTDIR
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
OLD=/srv/opentallas-scratch2/claude/kv-kits-10-1028/kits_pv
O=${1:?OUTDIR}
mkdir -p "$O"
for T in kv3_pv_pair__380.16x190.08 kv3_pv_pair__380.16x190.08_fMX; do
  K=$OLD/$T; N=$O/$T
  rm -rf "$N"; mkdir -p "$N"
  # generator-time kit inputs only (run outputs of the KV-KITS-10 runs are not carried)
  rsync -a --exclude run --exclude signoff --exclude views --exclude lec --exclude __pycache__ \
    --exclude 'autopilot_chain_*' --exclude 'preflight_autopilot_*' --exclude preflight.json \
    --exclude 1_synth_odb.v --exclude 'synth_odb_v.*' --exclude 'face_guard*.json' --exclude 'face_guard*.log' \
    --exclude 'rtl_lint.json' --exclude rtl_lint.log --exclude rtl_lint.ys --exclude 'selrange.*' \
    --exclude dont_use_check.json --exclude adder_map_dontuse.json --exclude sdc_lint.log --exclude lec_run.log \
    --exclude run_place.log --exclude run_route.log --exclude signoff.log --exclude pin_audit.json \
    --exclude ft_interface.json "$K/" "$N/"
  for f in face_guard.py lec.py rtl_lint.py sdc_lint.py signoff.py straps.py vclk_corner.tcl; do
    cp "$REPO/tools/die_plan/$f" "$N/$f"
  done
  python3 "$REPO/results/die_kv_14_1028/pv_pair/pv_macro_leaves.py" install "$N"
  python3 - "$REPO" "$N" <<'EOF'
import json, sys
from pathlib import Path
repo, kd = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(repo / "physical/die_plan/qwen_kvsys/cores/harden"), str(repo / "tools/die_plan")]
import gen_core_kit_kv as GK
import lec as LEC
cfg = (kd / "config.mk").read_text().splitlines()
if any("post_cts_setup.tcl" in l for l in cfg):
    raise SystemExit("already cts-setup-only")
r = GK.cts_setup_only(kd, cfg)
import ft_ports as FT   # gen-time ft interface model skeleton (signoff fills the delays), as ft_ports.install writes it
(kd / "ft_interface.json").write_text(json.dumps(FT.model_skeleton(json.loads((kd / "ft_ports.json").read_text())), indent=1) + "\n")
(kd / "config.mk").write_text("\n".join(cfg) + "\n")
fz = json.loads((kd / "freeze.json").read_text())
prov = LEC._repo_provenance(repo)
fz.update(kit_hash=GK.kit_hash(kd), source_commit=prov.get("commit"),
          cts_setup_only=r,
          regen=dict(lane="KV-KITS-15", base_kit=f"kv-kits-10-1028/kits_pv/{kd.name}",
                     base_source_commit=fz.get("source_commit"),
                     plan_delta="DIE-KV-14b (b1) SRAM macro leaves, pv_macro_leaves.py install (core_infra stage_basis=total)",
                     tools_refreshed=["face_guard.py", "lec.py", "rtl_lint.py", "sdc_lint.py", "signoff.py",
                                      "straps.py", "vclk_corner.tcl"]))
(kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
LEC.write_kit_provenance(kd, repo, provenance=prov)
print("REGEN", kd.name, "kit_hash", fz["kit_hash"], "src", prov.get("commit"))
EOF
done
