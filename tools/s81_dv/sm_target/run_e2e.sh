#!/bin/bash
# S81-SMWIRE (10-19): end-to-end SO wiring bench tb_smwire_e2e (tools/s81_dv/sm_target/make_bench_e2e.py), Verilator 5.050.
#   usage (repo root): tools/s81_dv/sm_target/run_e2e.sh OUT [DEFINE]     DEFINE = an RTL mutant define (one build), or empty
#   base build: route 1 (tier line) + route 2 (V) must PASS; bench mutants SMW_MUT 1..5 must FAIL ("SMWIRE FAIL");
#   TARGET_MUT 1..5 must give "TARGET CAUGHT" with SMS PASS (the original causal target mutants).
#   RTL mutant build (DEFINE given): route 1 must FAIL.
set -u
ROOT=$(cd "$(dirname "$0")/../../.." && pwd); cd "$ROOT"
O=${1:-out_e2e}; DEFN=${2:-}; mkdir -p "$O"
VL=${OPENTALLAS_TOOLS_ROOT:-$HOME/.local/opentallas-tools}/verilator-5.050/bin/verilator
"$VL" --version > "$O/tool.txt"
python3 tools/s81_dv/sm_target/make_bench_e2e.py > /dev/null
S=rtl
"$VL" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
 --top-module tb_smwire_e2e -Mdir "$O/obj" -j 16 --unroll-count 4 -fno-dfg \
 -GMUT=0 -GTI=5 -GNJOB=12 -CFLAGS -O1 ${DEFN:+-D$DEFN} \
 "$S/dsrom_sys/s81_dv/sm_target/test/tb_smwire_e2e.sv" \
 "$S/dsrom_sys/s81_dv/sm_target/dsdv_sm_so_target.sv" "$S/dsrom_sys/s81_dv/sm_target/dsdv_sm_wire.sv" \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v \
 "$S/dsrom_sys/s81_dv/land/dsfd_dvland_pvrd.sv" "$S/dsrom_sys/s81_dv/land/ot_s81_land.sv" \
 "$S/lib/ot_rst_relay.sv" "$S/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv" "$S/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv" \
 "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_sms.sv" \
 "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv" \
 "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_smh.sv" \
 "$S/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv" \
 "$S/hdc/ot_hdc_delay.sv" "$S/hdc/ot_hdc_fastfp_lat_f12.sv" \
 "$S/hdc/ot_hdc_fastfp.sv" "$S/hdc/ot_hdc_fp32_add_lat.sv" \
 "$S/hdc/ot_hdc_fp32_f12.sv" "$S/hdc/ot_hdc_fp32_mul_lat.sv" \
 "$S/hdc/ot_hdc_prefix.sv" "$S/hdc/ot_hdc_sfu.sv" \
 "$S/hdc/v41x/ot_dsrom_fp32_add_l6.sv" "$S/hdc/v41x/ot_dsrom_su_add6.sv" \
 "$S/hdc/v41x/ot_dsrom_su_f12.sv" "$S/hdc/v41x/ot_dsrom_su_fdiv_f12.sv" \
 "$S/hdc/v41x/ot_dsrom_su_softmax_add6.sv" "$S/hdc/v41x/ot_dsrom_su_softmax_add.sv" \
 "$S/hdc/v41x/ot_dsrom_su_softmax_f12r.sv" "$S/hdc/v41x/ot_dsrom_su_softmax_m9.sv" \
 "$S/hdc/v41x/ot_hdc_v41x_sfu.sv" > "$O/build.log" 2>&1 || { echo "E2E BUILD_FAILED"; tail -20 "$O/build.log"; exit 3; }
B="$O/obj/Vtb_smwire_e2e"
bad=0
run() {  # name, args, expect (pass | fail | caught)
  local n=$1 a=$2 e=$3
  $B $a > "$O/run_$n.log" 2>&1
  local v=FAIL; grep -q '^SMWIRE PASS' "$O/run_$n.log" && v=PASS
  local c=NO; grep -q '^TARGET CAUGHT' "$O/run_$n.log" && grep -q '^SMS PASS' "$O/run_$n.log" && c=YES
  local ok=0
  case $e in pass) [ $v = PASS ] && ok=1;; fail) [ $v = FAIL ] && ok=1;; caught) [ $c = YES ] && ok=1;; esac
  echo "E2E $n expect=$e smwire=$v caught=$c -> $([ $ok = 1 ] && echo OK || echo BAD) | $(grep -h '^SMWIRE stats' "$O/run_$n.log" | head -1)"
  [ $ok = 1 ] || bad=$((bad + 1))
}
if [ -z "$DEFN" ]; then
  run base_r1 "+SMW_ROUTE=1" pass &
  run base_r2 "+SMW_ROUTE=2" pass &
  for m in 1 2 3 4 5; do run smw_mut$m "+SMW_ROUTE=1 +SMW_MUT=$m" fail & done
  wait
  for m in 1 2 3 4 5; do run target_mut$m "+SMW_ROUTE=1 +TARGET_MUT=$m" caught & done
  wait
  # (background subshells cannot update bad: recount from the logs)
  bad=$(cat "$O"/run_*.log >/dev/null; for f in "$O"/run_base_r*.log; do grep -q '^SMWIRE PASS' $f || echo x; done; \
        for f in "$O"/run_smw_mut*.log; do grep -q '^SMWIRE PASS' $f && echo x; done; \
        for f in "$O"/run_target_mut*.log; do (grep -q '^TARGET CAUGHT' $f && grep -q '^SMS PASS' $f) || echo x; done)
  bad=$(echo -n "$bad" | grep -c x)
else
  run "rtlmut_$DEFN" "+SMW_ROUTE=1" fail
fi
echo "E2E_DONE bad=$bad define=${DEFN:-none}"
[ "$bad" = 0 ]
