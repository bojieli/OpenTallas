#!/usr/bin/env bash
# H-DIE 2026-10-15: re-run an SM-stack bench (run_sm_stack_native.sh / _steady.sh / _capacity.sh) with the controller
# split into 32 ot_hbm_svc_pc_ctrl_leaf instances (ot_hbm_svc_native_sector_pipeline_leaves) in place of the monolithic
# ot_hbm_svc_native_sector_pipeline_stack.  Same TB, same images, same pass strings and mutants; only the controller
# source differs.   run_ctrl_leaves.sh <bench script> <out> <bench args after out...>
set -euo pipefail
bench=${1:?bench script}; out=${2:?out}; shift 2
d=rtl/hbm_accel/loader/service_native
mkdir -p "$out/leaves_src"
sed 's/\bot_hbm_svc_native_sector_pipeline_stack controller\b/ot_hbm_svc_native_sector_pipeline_leaves controller/' \
  "$d/ot_hbm_svc_sm_stack_native.sv" > "$out/leaves_src/ot_hbm_svc_sm_stack_native.sv"
grep -q 'ot_hbm_svc_native_sector_pipeline_leaves controller' "$out/leaves_src/ot_hbm_svc_sm_stack_native.sv"
leaf="rtl/lib/ot_rst_relay.sv\" \"${LEAF_SRC:-$d/ot_hbm_svc_pc_ctrl_leaf.sv}"   # LEAF_SRC: a mutated leaf (bench_pc_ctrl_leaf.sh)
sed -e "s#\"\$d/ot_hbm_svc_native_sector_pipeline_stack.sv\"#\"$leaf\" \"\$d/ot_hbm_svc_native_sector_pipeline_leaves.sv\"#" \
    -e "s#\"\$d/ot_hbm_svc_sm_stack_native.sv\"#\"$out/leaves_src/ot_hbm_svc_sm_stack_native.sv\"#" "$d/$bench" > "$out/leaves_src/$bench"
grep -q ot_hbm_svc_native_sector_pipeline_leaves.sv "$out/leaves_src/$bench"
grep -q "$out/leaves_src/ot_hbm_svc_sm_stack_native.sv" "$out/leaves_src/$bench"
bash "$out/leaves_src/$bench" "$out" "$@"
echo "CTRL_LEAVES $bench PASS"
