#!/bin/bash
# QXF-SEAMC 10-18: slice bench of the Qwen compute die record-bundle seams (rtl/test/qwen_split/tb_qxf_record_seam.sv),
# Verilator 5.050, on the fleet (ot-run).  usage (repository root): bench_record_seam.sh OUTDIR [CONFIG ...]
# Each config builds the seam slice with tools/qwen_split/record_bundles.py (real forwarded lanes + landings through the
# GEN's relay wrappers, tools/qwen_split/gen_relay_rtl.py), elaborates it with the REAL consumers and runs it:
#   fixed_bn    PASS  dv2f14bn lanes + the GEN fix (record_bundles.fix_lanes: zero-stage members landed with their bundle,
#                     frame pads past the ring window, one E per bundle) in the GEN's emitted form
#   fixed_lp    PASS  dv2f14bhd lanes + the dv2f14bg land plan (what the next GEN takes) + the GEN fix
#   asbuilt_bn  FAIL  dv2f14bn AS BUILT: the GEN netlist's own lane cells and K straps, verbatim (F5 + G-C2 witness)
#   collcal_lp  FAIL  dv2f14bhd + land plan + Q-COLLCAL's bus-name equalize only (04f8b56c6): C.rx_record K 2 vs 1
#   mut_k_auth  FAIL  fixed_bn with ONE strap moved: sf_prog_auth_slot K + 1
#   mut_k_rxv   FAIL  fixed_lp with ONE strap moved: lnk_native_rx_v K + 1
# One line per config: <name> expect=<PASS|FAIL> got=<PASS|FAIL> -> OK | UNEXPECTED.  Exit 0 only when all met it.
# Fail regex (mutants / as-built): ^QXF_SEAM FAIL
set -u
OUT=$1; shift
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
RB=tools/qwen_split/record_bundles.py
FX=results/rtl/qxf_seamc_1018/fixtures/dv2f14bn_seam_die.v
CC=results/rtl/q_collcal_1018
mkdir -p "$OUT/in"
python3 $RB fix-die $FX --out "$OUT/in/bn_fix.json" > "$OUT/in/bn_fix.log" 2>&1 || { echo "fix-die failed"; cat "$OUT/in/bn_fix.log"; exit 2; }
python3 $RB audit-lanes $CC/gen_bhd_asbuilt/fwd_lanes.json --land-plan $CC/gen_bhd_lp/land_plan_dv2f14bg.json --fix \
  --lanes-out "$OUT/in/lp_fix.json" --out "$OUT/in/lp_fix_audit.json" > "$OUT/in/lp_fix.log" 2>&1 || { cat "$OUT/in/lp_fix.log"; exit 2; }
python3 $RB audit-lanes $CC/gen_bhd_asbuilt/fwd_lanes.json --land-plan $CC/gen_bhd_lp/land_plan_dv2f14bg.json --equalize-only \
  --lanes-out "$OUT/in/lp_collcal.json" --out "$OUT/in/lp_collcal_audit.json" > "$OUT/in/lp_collcal.log" 2>&1
SRC=(rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv rtl/qwen_split/qfd_native59_record_endpoint.sv
     rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv rtl/qwen_split/qfd_sys_face_record_port.sv
     rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv
     rtl/test/qwen_split/tb_qxf_record_seam.sv)
sha256sum "${SRC[@]}" $RB tools/qwen_split/lane_groups.py tools/qwen_split/gen_relay_rtl.py $FX \
  $CC/gen_bhd_asbuilt/fwd_lanes.json $CC/gen_bhd_lp/land_plan_dv2f14bg.json "$0" > "$OUT/source.sha256"
# name | expect | slice args
CONFIGS=(
 "fixed_bn|PASS|--lanes $OUT/in/bn_fix.json"
 "fixed_lp|PASS|--lanes $OUT/in/lp_fix.json"
 "asbuilt_bn|FAIL|$FX"
 "collcal_lp|FAIL|--lanes $OUT/in/lp_collcal.json"
 "mut_k_auth|FAIL|--lanes $OUT/in/bn_fix.json --mut-k sf_prog_auth_slot:+1"
 "mut_k_rxv|FAIL|--lanes $OUT/in/lp_fix.json --mut-k lnk_native_rx_v:+1"
)
want=("$@")
one() {
  local name=$1 exp=$2 args=$3 o=$OUT/$1
  mkdir -p "$o"
  python3 $RB slice $args --out "$o/seam.v" > "$o/slice.json" 2> "$o/slice.err" || { echo "$name expect=$exp got=SLICE_FAIL -> UNEXPECTED"; tail -3 "$o/slice.err"; return; }
  python3 tools/qwen_split/gen_relay_rtl.py "$o/seam.v" "$o/wrappers.sv" > "$o/wrappers.json" || { echo "$name got=GEN_FAIL -> UNEXPECTED"; return; }
  read -r ec es < <(python3 -c "import json,sys; m=json.load(open(sys.argv[1]))['members']; print(m['lnk_native_rx_v']['lane_cycles'], m['sf_prog_rx_v']['lane_cycles'])" "$o/slice.json")
  $V --binary --timing -j "${JOBS:-4}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY \
     -Wno-LATCH -Wno-INITIALDLY -Wno-TIMESCALEMOD --top-module tb -GEXP_C=$ec -GEXP_SF=$es --Mdir "$o/obj" -o tb \
     "$o/seam.v" "$o/wrappers.sv" "${SRC[@]}" > "$o/build.log" 2>&1 || { echo "$name expect=$exp got=BUILD_FAIL -> UNEXPECTED"; grep -m6 '%Error' "$o/build.log"; return; }
  "$o/obj/tb" > "$o/run.log" 2>&1
  rm -rf "$o/obj"
  local got=FAIL; grep -q '^QXF_SEAM PASS' "$o/run.log" && got=PASS
  echo "$name expect=$exp got=$got -> $([ $got = $exp ] && echo OK || echo UNEXPECTED)  (slice C.rx_record valid age $ec, SF.rx_record valid age $es)"
  grep -E '^QXF_(CFG|SEAM)' "$o/run.log" | sed 's/^/    /'
  grep -m3 '^QXF_ERR' "$o/run.log" | sed 's/^/    /'
}
pids=()
for c in "${CONFIGS[@]}"; do
  IFS='|' read -r name exp args <<< "$c"
  if [ ${#want[@]} -gt 0 ] && ! printf '%s\n' "${want[@]}" | grep -qx "$name"; then continue; fi
  one "$name" "$exp" "$args" > "$OUT/$name.summary" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait $p; done
cat "$OUT"/*.summary | tee "$OUT/SUMMARY.txt"
! grep -q 'UNEXPECTED\|BUILD_FAIL\|SLICE_FAIL' "$OUT/SUMMARY.txt"
