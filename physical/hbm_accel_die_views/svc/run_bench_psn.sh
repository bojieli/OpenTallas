#!/bin/bash
# [svc-ep] 2026-10-10: the PS segments WITH the native endpoint (gen_svc_seg.py --nep, rtl/seg_psn) as the DUT.
#   run_bench_psn.sh <out dir>        (from the source snapshot root; SVC_SIM=verilator)
#   lint_<master>       yosys check -assert of every --nep segment master
#   pos_SW_x<N> / pos_NE_x<N>   legacy SM / W / KV / IK traffic + 12 PS streams (KV credited on kq, IK on kc: N8) + the
#                       native driver (tb_svn_drv.svh: random reads / bursts / writes with RAW, then read rate, write rate,
#                       read-back) at NXL N extra PHY cycles: SVC_BENCH PASS + NEP_RATE / NEP_WRATE lines
#   neg_drop            endpoint mutant: a read-data flit dropped                 -> must FAIL
#   neg_order           endpoint mutant: a burst's beats returned out of order    -> must FAIL
#   neg_land            endpoint mutant: a write lands on the neighbouring PC     -> must FAIL
#   neg_wcons           N8: index-key credits returned by the idle consumer (kq)  -> must FAIL (stray credit fault)
#   neg_conc            N8: a second stream launched while one runs (overlap)     -> must FAIL
#   neg_wrg             WR_G sent as a binary count (not Gray)                    -> must FAIL
set -u
O=$1; mkdir -p $O; V=physical/hbm_accel_die_views/svc; T=$V/tb
rm -f $O/summary.txt
mkdir -p $O/ps
for f in $V/rtl/seg_psn/*.sv; do
  sed -E 's/\b(hfd_svc_(SW|SE)_s[0-9]+)\b/\1_ps/g; s/\b(hfd_svc_(SW|SE|NW|NE)_seg)\b/\1_ps/g' $f > $O/ps/$(basename $f .sv)_ps.sv
done
LIB="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv $V/rtl/ot_hbm_svc_core.sv $V/rtl/ot_hbm_svc_seg_lib.sv $V/rtl/ot_hbm_svc_ps_lib.sv"
NEPLIB=$V/rtl/ot_hbm_svc_nep_lib.sv
rc=0
if command -v yosys >/dev/null; then
  for f in $V/rtl/seg_psn/hfd_svc_S[WE]_s[0-9].sv; do
    m=$(basename $f .sv)
    ( yosys -q -p "read_verilog -sv $LIB $NEPLIB $f; hierarchy -check -top $m; proc; flatten; opt_clean; check -assert" > $O/lint_$m.log 2>&1
      echo "lint_$m rc=$?" > $O/lint_$m.rc ) &
  done
fi
for m in 1 2 3 4; do sed "s/parameter integer MUT = 0) (/parameter integer MUT = $m) (/" $NEPLIB > $O/nep_mut$m.sv
  cmp -s $O/nep_mut$m.sv $NEPLIB && { echo "endpoint mutant $m not applied" >> $O/summary.txt; rc=1; }; done
sim() {   # sim <label> <st> <fam> <nep lib> <args...>
  local L=$1 S=$2 F=$3 NL=$4; shift 4
  local SFILES="$LIB $NL $O/ps/hfd_svc_${F}_s[0-9]_ps.sv $O/ps/hfd_svc_${S}_seg_ps.sv $T/tb_svc_physide.sv $T/tb_svn_ps_$S.sv"
  local X=(); [[ $L == neg_* ]] && X=(-DOT_SVC_EARLY_FAIL)
  verilator --binary --timing -j ${VJ:-16} -Wno-fatal "$@" "${X[@]}" -DOT_SVC_VLT --top-module tb_svn_ps_$S -I$T --Mdir "$O/vlt_$L" $SFILES > "$O/build_$L.log" 2>&1 || { echo "$L build FAIL" >> "$O/summary.txt"; return 3; }
  "$O/vlt_$L/Vtb_svn_ps_$S" > "$O/$L.log" 2>&1
}
POS=${POS:-"SW:0 SW:30 SW:60 SW:90 NE:30"}
for c in $POS; do s=${c%%:*}; x=${c##*:}; f=SW; [ $s = NE ] && f=SE
  sim pos_${s}_x$x $s $f $NEPLIB -DPS_STREAMS -GNXL=$x & done
sim neg_drop SW SW $O/nep_mut1.sv -DPS_STREAMS & sim neg_order SW SW $O/nep_mut2.sv -DPS_STREAMS &
sim neg_land SW SW $O/nep_mut3.sv -DPS_STREAMS & sim neg_wcons SW SW $NEPLIB -DPS_STREAMS -DNEP_MUT_WCONS &
sim neg_conc SW SW $NEPLIB -DPS_STREAMS -DOT_PS_MUT_CONC & sim neg_wrg SW SW $O/nep_mut4.sv -DPS_STREAMS &
wait
cat $O/lint_*.rc 2>/dev/null >> $O/summary.txt; grep -q "rc=[1-9]" $O/lint_*.rc 2>/dev/null && rc=1
for c in $POS; do s=${c%%:*}; x=${c##*:}; L=pos_${s}_x$x
  grep -q "^SVC_BENCH PASS" $O/$L.log; r=$?
  echo "$L rc=$r $(grep -h 'SVC_BENCH lines\|NEP_BENCH\|NEP_RATE\|NEP_WRATE' $O/$L.log | tr '\n' ' ')" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
done
for L in neg_drop neg_order neg_land neg_wcons neg_conc neg_wrg; do
  grep -q "^SVC_BENCH PASS" $O/$L.log && r=0 || r=1
  echo "$L rc=$r (must be nonzero) $(grep -m2 'ERR\|SVC_MUTANT' $O/$L.log | tr '\n' ' ')" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
done
echo "overall rc=$rc" >> $O/summary.txt; cat $O/summary.txt; exit $rc
