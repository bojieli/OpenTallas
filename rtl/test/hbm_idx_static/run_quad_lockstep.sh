#!/bin/bash
# HBM-B-RTL2 (2026-10-17): lockstep of the d4g per-quadrant IDX client (ot_hbm_idx_client_static_quad) against
# today's N_Q=2 TP=192 stack-scorer client (ot_hbm_idx_scheduled_static, OT_IDX_SCORE_CLUSTER: the die's chained
# 16-leaf cluster, --score-chain 8), same programme source, VM image and keys.
# PASS: pos (new programme --score-chain 14) bit-identical every edge with the documented shifts (beats +2, scores +4,
# TX +8, done +2). Must FAIL: chain13 (programme compiled for a 1-edge-short tree), qswap (quadrant halves swapped on the straps),
# keybit (one key bit flipped on the new design's key lines only).
# Usage: run_quad_lockstep.sh OUT
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-quad-lockstep}"); mkdir -p "$out"
rank=191; keys=5456
OPENBLAS_NUM_THREADS=1 PYTHONPATH=tools python3 tools/hbm_idx_static_parent_vectors.py "$out/vec" 2 192 $rank > "$out/vectors.log"
for c in 8 13 14; do python3 tools/hbm_idx_static_calendar.py "$out/cal_c$c" --score-chain $c > "$out/cal_c$c.log"; done
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
Q=rtl/hbm_accel/index/quad_1017
src=(rtl/hbm_accel/index/ot_hbm_idx_scheduled_static.sv rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_parent_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv
 rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/hbm_accel/index/ot_hbm_idx_score_static.sv rtl/hbm_accel/index/ot_hbm_idx_engine_static.sv
 rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv
 rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv
 rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv
 $Q/ot_hbm_idx_score_quarter_static.sv $Q/ot_hbm_idx_xq_node_static.sv $Q/ot_hbm_idx_qctl_static.sv $Q/ot_hbm_idx_rootctl_static.sv $Q/ot_hbm_idx_client_static_quad.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
 rtl/hdc/v41x/ot_hbm_idx_chunk_rt.sv rtl/hbm_accel/index/ot_hbm_idx_score_cluster.sv
 rtl/test/hbm_idx_static/tb_idx_quad_lockstep.sv rtl/test/hbm_idx_static/quad.vlt)
sha256sum "${src[@]}" tools/hbm_idx_static_calendar.py tools/hbm_idx_static_parent_vectors.py rtl/test/hbm_idx_static/run_quad_lockstep.sh > "$out/sources.sha256"
build(){ # tag qswap
 "$vl" -DOT_IDX_SCORE_CLUSTER --hierarchical --binary --timing --verilate-jobs "${IDX_VERILATE_JOBS:-8}" --build-jobs "${IDX_BUILD_JOBS:-16}" -O1 -Wno-fatal -Wno-lint -Wno-style \
  -GTP=192 -GRANK=$rank -GNKEYS=5472 -GCHAIN=6 -GQSWAP=$2 --top-module tb_idx_quad_lockstep --Mdir "$out/obj_$1" "${src[@]}" > "$out/build_$1.log" 2>&1
}
# IDX_SERIAL=1: one build at a time (~53 GB RSS each; ot-run --mem 64), else both in parallel (~110 GB)
if [ "${IDX_SERIAL:-0}" = 1 ]; then build pos 0; build qswap 1; else build pos 0 & build qswap 1 & wait; fi
echo BUILDS_DONE
len(){ python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["length"])' "$1/calendar.json"; }
rc=0
run(){ # tag obj newcal mut want
 local d=$out/run_$1; mkdir -p "$d"; cp "$out"/vec/*.hex "$d/"
 cp "$out/cal_c8/calendar_instructions.hex" "$d/cal_old.hex"; cp "$out/cal_c$3/calendar_instructions.hex" "$d/cal_new.hex"
 set +e; (cd "$d" && "$out/obj_$2/Vtb_idx_quad_lockstep" +NO=$(len "$out/cal_c8") +NN=$(len "$out/cal_c$3") +MUT=$4 +KEYS=$keys) > "$d.log" 2>&1; local r=$?; set -e
 grep -E "IDX_QUAD_LOCKSTEP|BAD|disagree|fatal|Error" "$d.log" | head -6 | sed "s/^/[$1] /"
 if [ "$5" = pass ]; then [ $r = 0 ] && grep -q "IDX_QUAD_LOCKSTEP PASS" "$d.log" || { echo "[$1] FAILED (expected PASS)"; rc=1; }
 else [ $r != 0 ] && grep -q "IDX_QUAD_LOCKSTEP chain" "$d.log" && echo "[$1] mutant rejected" || { echo "[$1] MUTANT SURVIVED"; rc=1; }; fi
}
run pos pos 14 0 pass
run chain13 pos 13 0 fail
run keybit pos 14 2 fail
run qswap qswap 14 0 fail
[ $rc = 0 ] && echo IDX_QUAD_LOCKSTEP_GATE_PASS || echo IDX_QUAD_LOCKSTEP_GATE_FAIL
exit $rc
