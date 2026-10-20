#!/bin/bash
# KV-RETIRE 10-19 fleet evidence (Verilator 5.050 only).  Run from a repo-root copy:  bash results/arch/kv_retire_1019/run.sh
set -u
cd "$(dirname "$0")/../../.."
ROOT=$PWD; R=results/arch/kv_retire_1019; O=${OUT:-$R/out}; mkdir -p $O
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$V" ] || V=$(command -v verilator)
"$V" --version > $O/verilator.version; grep -q 5.050 $O/verilator.version || { echo "NEED VERILATOR 5.050"; exit 91; }
. $R/bench.env
fail=0; note(){ echo "$*" | tee -a $O/summary.log; }
bad(){ note "FAIL $*"; fail=1; }
: > $O/summary.log
# 0 planner / contract unit tests
(cd tools/qwen_kv_die && python3 -m unittest test_kv_retirement_contract test_kv_retirement -v) > $O/planner.log 2>&1 && note "PASS planner+contract unit tests" || bad planner
S=rtl/qwen_sys/split_20261014
WP="rtl/test/qwen_split/tb_kv_retire_wholepath.sv $S/qkd_native_attention_programme.sv $S/qkd_native_attention_static_ctl.sv $S/qkd_native59_descriptor_producer.sv $S/qkd_native59_command_guard.sv $S/qkd_native_attention_record.sv rtl/qwen_sys/static_kv_die_20261017/qkd_attn_fault_root.sv"
"$V" --binary --timing -Wno-fatal -j 4 --top-module tb_kv_retire_wholepath --Mdir $O/wp $WP > $O/wp_build.log 2>&1 || bad "wholepath build"
B=$O/wp/Vtb_kv_retire_wholepath; A="+TXF=$TXF +RX=$RX"
# 1 nominal / late / missing modes at the contract STATUS
for m in 0 2 3 4 5; do $B $A +STATUS=$STATUS +MODE=$m +D=$DMAX > $O/mode$m.log 2>&1 && grep -q RETIRE_WHOLEPATH_PASS $O/mode$m.log || bad "mode $m"; done
note "modes 0/2/3/4/5 done"
# 2 every one of the contract sources injected AT the functional cutoff with its own pre-AFR edges
mkdir -p $O/sources; n=0
while read i id d; do $B $A +STATUS=$STATUS +MODE=1 +INJ=$CUTOFF +D=$d > $O/sources/s$i.log 2>&1 && grep -q RETIRE_WHOLEPATH_PASS $O/sources/s$i.log || bad "source $i $id D=$d"; n=$((n+1)); done < $R/bench_sources.txt
note "sources injected at cutoff $CUTOFF: $n"
# 3 early injection
$B $A +STATUS=$STATUS +MODE=1 +INJ=100 +D=$DMAX > $O/early.log 2>&1 && grep -q RETIRE_WHOLEPATH_PASS $O/early.log || bad early
# 4 boundary: smallest STATUS that never lets a healthy STATUS escape for the worst source at the cutoff
b=-1
for s in $(seq $((CUTOFF+DMAX-30)) $STATUS); do
  if $B $A +STATUS=$s +MODE=1 +INJ=$CUTOFF +D=$DMAX > $O/sweep.log 2>&1 && grep -q RETIRE_WHOLEPATH_PASS $O/sweep.log; then b=$s; break; fi
done
[ $b -gt $((CUTOFF+DMAX-30)) ] || bad "no safe STATUS up to the contract age, or sweep started inside the safe range (b=$b)"
note "kv-side boundary STATUS=$b contract STATUS=$STATUS margin=$((STATUS-b)) (contract suffix $SUFFIX)"
# 5 negative controls (fail witnesses): one edge before the boundary, and the legacy un-delayed STATUS
$B $A +STATUS=$((b-1)) +MODE=1 +INJ=$CUTOFF +D=$DMAX +EXPECT_ESCAPE=1 > $O/witness_boundary_minus1.log 2>&1 && grep -q RETIRE_ESCAPE_WITNESS $O/witness_boundary_minus1.log || bad "boundary-1 did not escape"
$B $A +STATUS=$LEGACY +MODE=1 +INJ=$CUTOFF +D=$DMAX +EXPECT_ESCAPE=1 > $O/witness_legacy_status.log 2>&1 && grep -q RETIRE_ESCAPE_WITNESS $O/witness_legacy_status.log || bad "legacy STATUS did not escape"
# and the bench's own checker fails (fatal) when asked to certify that early STATUS
$B $A +STATUS=$((b-1)) +MODE=1 +INJ=$CUTOFF +D=$DMAX > $O/fail_boundary_minus1.log 2>&1; rc=$?
[ $rc -ne 0 ] && grep -q "healthy STATUS escaped functional fault path" $O/fail_boundary_minus1.log || bad "early STATUS not refused by checker"
note "negative controls done"
# 6 reset root counter widths
RR="$S/qkd_rst_region.sv"
for t in tb_qkd_rst_region tb_qkd_rst_region_pr; do
  "$V" --binary --timing -Wno-fatal -j 4 --top-module $t --Mdir $O/$t rtl/test/qwen_split/$t.sv $RR $S/qkd_rst_region_pr.sv > $O/${t}_build.log 2>&1 || bad "$t build"
  $O/$t/V$t > $O/$t.log 2>&1 && grep -q "PASS" $O/$t.log || bad "$t regression"
done
for m in 0 4; do
  "$V" --binary --timing -Wno-fatal -j 4 --top-module tb_qkd_rst_region_wide -GMUT=$m --Mdir $O/wide$m rtl/test/qwen_split/tb_qkd_rst_region_wide.sv $RR > $O/wide${m}_build.log 2>&1 || bad "wide build $m"
  $O/wide$m/Vtb_qkd_rst_region_wide > $O/wide$m.log 2>&1; rc=$?
  if [ $m = 0 ]; then [ $rc = 0 ] && grep -q RST_REGION_WIDE_PASS $O/wide0.log || bad "wide pass"; else [ $rc -ne 0 ] && grep -q RST_REGION_WIDE_FAIL $O/wide4.log || bad "wide legacy mutant"; fi
done
note "reset root widths done"
# 7 host guard warm-reset history
H=rtl/qwen_sys/host_20261013
"$V" --binary --timing -Wno-fatal -j 4 --top-module tb_qkd_host_service_guard --Mdir $O/guard rtl/test/qwen_host/tb_qkd_host_service_guard.sv $H/qkd_host_service_guard.sv $H/qkd_host_guard_fifo.sv > $O/guard_build.log 2>&1 || bad "guard build"
$O/guard/Vtb_qkd_host_service_guard > $O/guard.log 2>&1 || bad "guard regression"
declare -A RX_=( [1]="WARM_CERTIFIED_CLEAN" [2]="WARM_VETO_NOT_LIVE_IN_RESET|RETAINED_CERTIFIED_CLEAN" [3]="RECOVERY_WITH_RETAINED" )
for m in 0 1 2 3; do
  "$V" --binary --timing -Wno-fatal -j 4 --top-module tb_qkd_host_service_guard_wh -GWH_MUT=$m --Mdir $O/wh$m rtl/test/qwen_host/tb_qkd_host_service_guard_wh.sv $H/qkd_host_service_guard_wh.sv $H/qkd_host_service_guard.sv $H/qkd_host_guard_fifo.sv > $O/wh${m}_build.log 2>&1 || bad "wh build $m"
  $O/wh$m/Vtb_qkd_host_service_guard_wh > $O/wh$m.log 2>&1; rc=$?
  if [ $m = 0 ]; then [ $rc = 0 ] && grep -q GUARD_WH_PASS $O/wh0.log || bad "wh pass"; else [ $rc -ne 0 ] && grep -Eq "${RX_[$m]}" $O/wh$m.log || bad "wh mutant $m"; fi
done
note "guard warm history done"
[ $fail = 0 ] && note "KV_RETIRE_ALL_PASS" || note "KV_RETIRE_FAILURES"
exit $fail
