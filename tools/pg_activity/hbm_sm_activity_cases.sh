#!/usr/bin/env bash
# PG-ACTIVITY-4 (10-27): per-case measured HBM SM activity. Same bench/sources/defines as hbm_sm_activity_sim.sh
# (tb_hgi_sm_e2e --ds, 2 real ot_hbm_accel_smh hard-master SMs, real VM, golden check), but the VCD of g_sm[0].u_sm is
# switched on per case by plusargs (hbm_tb_dump_patch.py): one build, then
#   run_full.log : all cases, no dump -> HGI_SM_E2E PASS/FAIL (exactness of the same binary)
#   caseK/       : +C0=K +C1=K+1 +DUMP, window = record issue .. min(retire, DUMPMAX) cycles -> act_SM.txt, VCD deleted
#   act/         : act_SM_mean.txt (cycle-weighted all cases), act_SM_peak.txt (largest summed rate case), cases.json
#   hbm_sm_activity_cases.sh OUTDIR   (cwd = repo root, Verilator 5.050)   env: DUMPMAX (4000) P (parallel cases, 14)
set -eu
O=$(realpath -m "${1:?outdir}"); mkdir -p "$O"; T=$(dirname "$(realpath "$0")")
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/hgi_adapters/sm_e2e_bench.py --ds --out "$O/vec" > "$O/gen.log"; cat "$O/gen.log"
N=$(sed -n 's/^\([0-9]*\) cases.*/\1/p' "$O/gen.log")
python3 "$T/hbm_tb_dump_patch.py" rtl/hbm_accel/generic/adapters/tb/tb_hgi_sm_e2e.sv "$O/tb_hgi_sm_e2e_dump.sv"
SRC="rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/hbm_accel/generic/vm/ot_hgi_vm_lanearb.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/generic/adapters/ot_hgi_sm_record.sv rtl/hbm_accel/generic/ot_hgi_sm_leaf.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv $(python3 -c "import sys; sys.path.insert(0,\"tools\"); import dshbm_sm_pq_seq as Q; print(\" \".join(s for s in Q.SRC + Q.SMH_SRC if \"rtl/test/\" not in s))")"
D="${XDEF:--DOT_SMH_CG_ENREG -DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_RSTPIN -DOT_SMH_HIER -DOT_SMH_PTW_OHDLY -DOT_SMH_PINREG -DOT_SMH_XREL -DOT_SMH_PRODUCTION_SHAPE -DOT_SMH_COMPACT_PT -DOT_SMH_GROUP_TRANSPORT -DOT_SMH_WEST_SPLIT -DOT_SMH_TRANSPORT_KEEP -DOT_SMH_RP4_SRST}"
$VL --version
if [ ! -x "$O/obj/Vtb_hgi_sm_e2e" ]; then
$VL --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN --trace --trace-max-width 2048 \
  --top-module tb_hgi_sm_e2e -I"$O/vec" $D -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" -Mdir "$O/obj" $SRC "$O/tb_hgi_sm_e2e_dump.sv" -j ${J:-16} > "$O/build.log" 2>&1 || { grep -m10 %Error "$O/build.log"; echo BUILD_FAILED; exit 3; }
fi
echo "BUILD_DONE $(date -Is)"
B="$O/obj/Vtb_hgi_sm_e2e"
( "$B" +DIR="$O/vec" > "$O/run_full.log" 2>&1; echo "EXIT $? $(date -Is)" >> "$O/run_full.log" ) &
FULL=$!
run_case() {
  c=$1; d="$O/case$c"; mkdir -p "$d"
  "$B" +DIR="$O/vec" +C0=$c +C1=$((c+1)) +DUMP +DUMPMAX=${DUMPMAX:-4000} +VCD="$d/sm.vcd" > "$d/run.log" 2>&1 || echo "SIM_EXIT $?" >> "$d/run.log"
  grep -q DUMP_OFF "$d/run.log" || { echo "case $c NO DUMP_OFF"; return 1; }
  python3 "$T/vcd_activity.py" "$d/sm.vcd" "$d" --clk 'tb_hgi_sm_e2e.g_sm[0].u_sm.clk' --root 'SM=tb_hgi_sm_e2e.g_sm[0].u_sm' > "$d/act.log" 2>&1
  ls -la "$d/sm.vcd" >> "$d/act.log"; rm -f "$d/sm.vcd"; echo "case $c $(grep DUMP_OFF "$d/run.log") $(grep -m1 '^SM ' "$d/act.log")"
}
pids=(); for c in $(seq 0 $((N-1))); do
  while [ "$(jobs -rp | wc -l)" -gt "${P:-14}" ]; do sleep 20; done
  run_case $c & pids+=($!)
done
rc=0; for p in "${pids[@]}"; do wait $p || rc=1; done
wait $FULL; command tail -n 3 "$O/run_full.log"
python3 "$T/act_merge.py" "$O/act" $(for c in $(seq 0 $((N-1))); do echo "$O/case$c"; done)
grep -a -q "HGI_SM_E2E PASS" "$O/run_full.log" || { echo "FULL BENCH NOT PASS"; rc=2; }
echo "ALL_DONE rc=$rc $(date -Is)"; exit $rc
