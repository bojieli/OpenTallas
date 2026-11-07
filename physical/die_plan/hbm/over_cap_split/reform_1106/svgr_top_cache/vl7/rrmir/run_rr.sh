#!/bin/bash
# run_rr.sh: DIE-HBM-88 RRMIR lock-step matrix (iverilog 12, host tools, prlimit 6 GB each).
# usage: run_rr.sh [NCYC] ; env MUTS=1 runs the mutant set instead.
set -u
B=$(cd "$(dirname "$0")" && pwd); cd /
N=${1:-200000}; L=$B/logs; mkdir -p $L $B/bin
K=$B/rtl; # issuer / calendar / static feed / reset sync / face reg: vL6 kit copies; cache: vL7 branch
sed -e 's/\bot_svgr_top_cachecut\b/ot_svgr_top_cachecut_ref/g;s/\bot_svgr_feed_cachecut\b/ot_svgr_feed_cachecut_ref/g;s/\bot_svgr_prod_s_cachecut\b/ot_svgr_prod_s_cachecut_ref/g;s/\bot_svgr_k_out\b/ot_svgr_k_out_ref/g;s/\bot_svgr_kr_in\b/ot_svgr_kr_in_ref/g' $B/ref/ot_svgr_top_cachecut.sv > $B/ref_cachecut.sv
COMMON="$B/ref_cachecut.sv $K/ot_hbm_svc_sm_issuer_rel.sv $K/ot_smh_calendar_static_x.sv $K/ot_smh_static_feed.sv $K/ot_reset_sync.sv $B/ref/ot_svgr_cache136_native.sv $B/sram_beh_all.sv"
run(){ tag=$1; dut=$2; shift 2; prlimit --as=6000000000 nice -n 10 iverilog -g2012 "$@" -DNCYC=$N -o $B/bin/$tag $B/tb_rr.sv $dut $COMMON >$L/$tag.comp 2>&1 && prlimit --as=6000000000 nice -n 10 vvp -n $B/bin/$tag >$L/$tag.log 2>&1; echo "$tag rc $? $(grep -h '^RESULT' $L/$tag.log)" >> $L/summary.txt; rm -f $B/bin/$tag; }
if [ "${MUTS:-0}" = 1 ]; then
 for m in $B/mut/*.sv; do t=$(basename $m .sv)
  run mut_$t $m -DRRM=1 -DRRM1 -DSEED=7 -DSTOP1=1 ${MUTX:-} &
  run mut_oil0_$t $m -DRRM=1 -DRRM1 -DSEED=8 -DOIL=0 -DSTOP1=1 ${MUTX:-} &
 done; wait; exit 0
fi
for s in ${SEEDS:-1 2 3}; do
 # name:RRM:P1:OIL:IDC:XS:LBK:WDEC:GS:GR
 for c in kit_on:1:1:1:1:1:4:1:1:2 kit_off:0:1:1:1:1:4:1:1:2 p0_on:1:0:0:1:1:4:0:0:1 oil0_on:1:1:0:1:1:4:1:1:2 idc0_on:1:1:1:0:0:4:1:1:2 lb2_on:1:1:1:1:1:2:1:1:2 v6cache_on:1:1:1:1:1:4:0:0:1; do
  IFS=: read n r p o i x l w g gr <<<"$c"
  D=""; [ $r = 1 ] && D="-DRRM1"
  run ${n}${TAGX:-}_s$s $B/dut/ot_svgr_top_cachecut.sv ${MAINX:-} -DRRM=$r $D -DP1V=$p -DOIL=$o -DIDC=$i -DXS=$x -DLBK=$l -DWDEC=$w -DGS=$g -DGR=$gr -DSEED=$s &
 done
done
wait
echo "ALLDONE $(date)" >> $L/summary.txt
