#!/usr/bin/env bash
# H-NETLIST 2026-10-16 (die alias reduction): strap-identity service group ot_hbm_svc_sm_group_id vs the parameterised
# ot_hbm_svc_sm_group on the same hardware-issued stack bench.
#   run_sm_groups_issued_id.sh <out> <images> [stack] [rows] [epochs]
# PASS = both positives pass AND their PASS/epoch reports are identical (same packets, consumer lines, sector counts and
# done times to the ps); every strap mutant (SM xor 1, SM xor 4, STACK xor 1) must FAIL with an SM_STACK fatal.
set -euo pipefail
ulimit -c 0
out=${1:?out}; images=${2:?images}; stack=${3:-0}; rows=${4:-40}; epochs=${5:-8}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
common=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_sm8_landing_bank.sv" "$d/ot_hbm_svc_static_sm_packed136.sv" "$d/ot_hbm_svc_sm_issuer.sv" rtl/hbm_accel/sm/static/ot_smh_static_feed.sv rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv" rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv "$d/ot_hbm_svc_native_sector_pipeline_leaves.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv")
par=("$d/ot_hbm_svc_prefetch_mapped4_owner.sv" "$d/ot_hbm_svc_prefetch_overlap_owner.sv" "$d/ot_hbm_svc_sm4pc_cdc.sv" "$d/ot_hbm_svc_sm_feed_programmed.sv" "$d/ot_hbm_svc_sm_group.sv" "$d/tb_hbm_svc_sm_groups_issued.sv")
gid=("$d/ot_hbm_svc_prefetch_overlap_owner_id.sv" "$d/ot_hbm_svc_sm4pc_cdc_id.sv" "$d/ot_hbm_svc_sm_feed_programmed_id.sv" "$d/ot_hbm_svc_sm_group_id.sv" "$d/tb_hbm_svc_sm_groups_issued_id.sv")
sha256sum "${common[@]}" "${par[@]}" "${gid[@]}" > "$out/sources.sha256"
build(){ # name top defines... (sources picked by top)
 local n=$1 top=$2; shift 2; local s=("${common[@]}" "${par[@]}"); [ "$top" = tb_hbm_svc_sm_groups_issued_id ] && s=("${common[@]}" "${gid[@]}")
 verilator --binary --timing -j 4 -Wno-fatal "$@" --top-module "$top" -GSTACK="$stack" -GROWS="$rows" -GEPOCHS="$epochs" \
  --Mdir "$out/$n" -o sim "${s[@]}" > "$out/$n.build.log" 2>&1 || { tail -20 "$out/$n.build.log"; echo "SVG_ID BUILD_FAIL $n"; exit 2; }
}
build obj_par tb_hbm_svc_sm_groups_issued &
build obj_id tb_hbm_svc_sm_groups_issued_id &
build obj_msm1 tb_hbm_svc_sm_groups_issued_id -DOT_SVG_ID_MUT_SM=1 &
build obj_msm4 tb_hbm_svc_sm_groups_issued_id -DOT_SVG_ID_MUT_SM=4 &
build obj_mst tb_hbm_svc_sm_groups_issued_id -DOT_SVG_ID_MUT_STACK=1 &
wait
fail=0
"$out/obj_par/sim" +IMAGES="$images" > "$out/par.log" 2>&1 || true
"$out/obj_id/sim" +IMAGES="$images" > "$out/id.log" 2>&1 || true
grep -q '^SM_GROUPS_ISSUED PASS' "$out/par.log" || { echo "SVG_ID parameterised positive FAILED"; tail -3 "$out/par.log"; fail=1; }
grep -q '^SM_GROUPS_ISSUED PASS' "$out/id.log" || { echo "SVG_ID strap positive FAILED"; tail -3 "$out/id.log"; fail=1; }
grep '^SM_GROUPS_ISSUED' "$out/par.log" > "$out/par.report"; grep '^SM_GROUPS_ISSUED' "$out/id.log" > "$out/id.report"
if cmp -s "$out/par.report" "$out/id.report"; then echo "SVG_ID REPORT_IDENTICAL lines=$(wc -l < "$out/id.report")"; else echo "SVG_ID REPORT_DIFFERS"; diff "$out/par.report" "$out/id.report" | head; fail=1; fi
head -1 "$out/id.report"
for m in msm1 msm4 mst; do
 if "$out/obj_$m/sim" +IMAGES="$images" > "$out/$m.log" 2>&1 && grep -q '^SM_GROUPS_ISSUED PASS' "$out/$m.log"; then echo "SVG_ID MUTANT_SURVIVED $m"; fail=1
 elif grep -q 'SM_STACK' "$out/$m.log"; then echo "SVG_ID MUTANT_REJECTED $m: $(grep -m1 -o 'SM_STACK[^"]*' "$out/$m.log")"
 else echo "SVG_ID MUTANT_NO_WITNESS $m"; tail -3 "$out/$m.log"; fail=1; fi
done
rm -rf "$out"/obj_*/*.o "$out"/obj_*/*.cpp
[ $fail = 0 ] && echo "SVG_ID_GATE PASS stack=$stack" || { echo "SVG_ID_GATE FAIL stack=$stack"; exit 1; }
