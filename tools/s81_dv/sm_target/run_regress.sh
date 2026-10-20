#!/bin/bash
# S81-SMWIRE (10-19): regressions of the modules the SO wiring touched (repo root, Verilator 5.050 / iverilog):
#   ot_s81sl_xr     tools/s81_slice/xr_bench.sh base HB 0 / HB 1 + its mutants (hops row porder nocol bwide)
#   ot_s81sl_rstop  tools/s81_slice/rstop_sid_bench.sh none + tiercol
#   dsfd_dvland_pvrd rtl/dsrom_sys/s81_dv/land/test/pvrd_bench.sh pass / mut_cal / mut_sel
#   dsdv_svc_rs     lint (die build: no RS_OBS) of dsdv_svc_rs + dsdv_svc_rs_entry with SMT 1 (the bound wrappers)
set -u
ROOT=$(cd "$(dirname "$0")/../../.." && pwd); cd "$ROOT"
O=${1:-out_regress}; mkdir -p "$O"
VL=${OPENTALLAS_TOOLS_ROOT:-$HOME/.local/opentallas-tools}/verilator-5.050/bin/verilator
"$VL" --version > "$O/tool.txt"
r() { local n=$1; shift; "$@" > "$O/$n.log" 2>&1; local rc=$?; echo "REG $n rc=$rc | $(tail -1 "$O/$n.log")"; return $rc; }
bad=0
r xr_hb0 tools/s81_slice/xr_bench.sh "$O/xr_hb0" base 1 0 || bad=$((bad+1)) &
r xr_hb1 tools/s81_slice/xr_bench.sh "$O/xr_hb1" base 1 1 || bad=$((bad+1)) &
for m in hops row porder nocol; do r xr_$m tools/s81_slice/xr_bench.sh "$O/xr_$m" $m 1 1 & done
r xr_bwide tools/s81_slice/xr_bench.sh "$O/xr_bwide" bwide 1 1 &
r rstop_none tools/s81_slice/rstop_sid_bench.sh "$O/rstop" none &
r rstop_tiercol tools/s81_slice/rstop_sid_bench.sh "$O/rstop_t" tiercol &
r pvrd_pass rtl/dsrom_sys/s81_dv/land/test/pvrd_bench.sh pass "$O/pvrd_p" &
r pvrd_mut_cal rtl/dsrom_sys/s81_dv/land/test/pvrd_bench.sh mut_cal "$O/pvrd_c" &
r pvrd_mut_sel rtl/dsrom_sys/s81_dv/land/test/pvrd_bench.sh mut_sel "$O/pvrd_s" &
source tools/s81_dv/svc_rs/rs_files.sh
for top in dsdv_svc_rs dsdv_svc_rs_entry; do
  ( "$VL" --lint-only -Wall -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM \
      -Wno-PINCONNECTEMPTY -Wno-GENUNNAMED -Wno-VARHIDDEN -Wno-UNDRIVEN --top-module $top -I$D -DSVCQ_ENG_FG3 "${RS_DEF[@]}" \
      "${RS_SRC[@]}" "${RS_LIB[@]}" > "$O/lint_$top.log" 2>&1; \
    n=$(grep -c '%Error' "$O/lint_$top.log"); echo "REG lint_$top errors=$n | $(grep -m3 '%Error' "$O/lint_$top.log" | tr '\n' ' ')" ) &
done
wait
# verdicts from the logs (background jobs)
ok() { grep -q "$2" "$O/$1.log"; }
v=0
ok xr_hb0 '^PASS xr base' || v=$((v+1)); ok xr_hb1 '^PASS xr base' || v=$((v+1))
for m in hops row porder nocol bwide; do ok xr_$m 'NEGATIVE_CONTROL_FAILED_AS_EXPECTED' || v=$((v+1)); done
ok rstop_none 'BENCH_PASS rstop_sid' || v=$((v+1)); ok rstop_tiercol 'NEGATIVE_CONTROL_FAILED_AS_EXPECTED' || v=$((v+1))
ok pvrd_pass 'PVRD_BENCH PASS' || v=$((v+1))
ok pvrd_mut_cal 'PVRD_BENCH FAIL' || v=$((v+1)); ok pvrd_mut_sel 'PVRD_BENCH FAIL' || v=$((v+1))
for top in dsdv_svc_rs dsdv_svc_rs_entry; do grep -q '%Error' "$O/lint_$top.log" && v=$((v+1)); done
echo "REGRESS_DONE bad=$v"
[ $v = 0 ]
