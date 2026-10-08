#!/bin/bash
# run_sr_bench.sh [none|m1..m6] (run from the repo root): transaction-level exactness of ot_hbm_accel_tu_endpoint_sr
# (the SRAM-FIFO / SRAM-delay hfd_coll endpoint, stream hbm-coll-rtl 2026-10-08) on the collective bench
# rtl/hbm_accel/tu/tb_hbm_accel_tu_endpoint.sv (golden fixtures of tools/dshbm_1m_coll.py: all-reduce from the
# hdc_golden tree + to_bf16, gathers): every delivered word checked, all words delivered, no fault.
#   builds: ar / ga  (campaign shape PFMAX 384, async PHY clock T_PHY 1.0 ns)
#           arblk_a  (die-view shape PFMAX 64, pclk = clk, CDC FIFOs kept)
#           arblk_s / gablk_s (die-view shape, pclk = clk, SYNCPHY = 1)
#   plus: the die wrapper rtl_sr/hfd_coll.sv == rtl/hfd_coll.sv but for the endpoint instance line.
# m1..m6 run the same on a mutated copy and must FAIL:
#   m1 SRAM delay read offset +1, m2 SRAM FIFO bank select one edge early, m3 operand-column write data from port 0,
#   m4 slice compare >= -> >, m5 SRAM FIFO head credit K+1, m6 wrapper rank binding shifted.
set -u
R=$(pwd); MUT=${1:-none}
T=$(mktemp -d /tmp/hcoll_sr.XXXXXX)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p $T/src
cp rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_sr.sv \
   physical/hbm_accel_die_views/coll/rtl_sr/hfd_coll.sv physical/hbm_accel_die_views/coll/rtl_sr/hfd_coll_cdc.sv $T/src/
P=$T/src/ot_hcoll_sram_prims.sv; E=$T/src/ot_hbm_accel_tu_endpoint_sr.sv; WR=$T/src/hfd_coll.sv
case $MUT in
  none) ;;
  m1) sed -i "s/cnt - 7'(D - 3)/cnt - 7'(D - 2)/" $P ;;
  m2) sed -i "s/rawb\[(NBK > 1) ? bs2/rawb[(NBK > 1) ? bs1/" $P ;;
  m3) sed -i "s/cw_d\[x\] = cw_d\[x\] | rb_head\[p\]\[FW-1:0\]/cw_d[x] = cw_d[x] | rb_head[0][FW-1:0]/" $E ;;
  m4) sed -i "s/if (f >= mOF\[m\])/if (f > mOF[m])/" $E ;;
  m5) sed -i "s/ocr <= 3'(K);/ocr <= 3'(K + 1);/" $P ;;
  m6) sed -i "s/u_ep (.clk(w_ep_clk), .rst_n(w_ep_rst_n), .pclk(w_ep_pclk)/u_ep (.clk(w_ep_clk), .rst_n(w_ep_rst_n), .pclk(w_ep_clk)/; s/assign w_ep_rank = {i_f_cmdproc\[7:0\]}/assign w_ep_rank = {i_f_cmdproc[8:1]}/" $WR ;;
  *) echo "unknown mutant $MUT"; exit 2 ;;
esac
for f in $P $E $WR; do b=$(basename $f); d=rtl/hbm_accel/tu/$b; [ $b = hfd_coll.sv ] && d=physical/hbm_accel_die_views/coll/rtl_sr/$b
  cmp -s $f $d || echo "mutant $MUT applied to $b"; done
# wrapper: identical to the benched flop-endpoint wrapper except the endpoint instance line
python3 - $WR $T/src/hfd_coll_cdc.sv physical/hbm_accel_die_views/coll/rtl/hfd_coll.sv > $T/wrap.log <<'PY'
import sys
def body(f):
    L = open(f).read().splitlines()
    while L and L[0].startswith('//'): L.pop(0)
    return L
ref = body(sys.argv[3])
old = 'ot_hbm_accel_tu_endpoint #(.ENABLE(1), .RXAW(4), .QAW(4), .TXAW(4)) u_ep ('
ok = True
for f, par in ((sys.argv[1], '.SYNCPHY(1)'), (sys.argv[2], '.SYNCPHY(0)')):
    new = 'ot_hbm_accel_tu_endpoint_sr #(.ENABLE(1), %s) u_ep (' % par
    a = body(f)
    nd = [i for i, (x, y) in enumerate(zip(a, ref)) if x != y]
    ok &= len(a) == len(ref) and len(nd) == 1 and a[nd[0]] == ref[nd[0]].replace(old, new)
print('WRAP_OK' if ok else 'WRAP_BAD')
PY
grep -q WRAP_OK $T/wrap.log || { echo "HCOLL_SR MISMATCH wrapper"; rm -rf $T; exit 1; }
python3 tools/dshbm_1m_coll.py fixtures $T > $T/fx.log 2>&1 || { echo "HCOLL_SR ERROR fixtures"; cat $T/fx.log; exit 3; }
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRC="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $M $P $E rtl/hbm_accel/tu/tb_hbm_accel_tu_endpoint.sv"
D="+define+TU_DUT=ot_hbm_accel_tu_endpoint_sr"
AR="+define+TU_NC=8 +define+TU_NOG=8 +define+TU_BF16=1"; GA="+define+TU_NC=1 +define+TU_NOG=96 +define+TU_BF16=0"
BLK="+define+TU_PFMAX=64 +define+TU_PCLK_IS_CLK -GT_PHY=0.833333"
build() { n=$1; shift; mkdir -p $T/b; $V --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast \
  --top-module tb_hbm_accel_tu_endpoint --Mdir $T/b/$n $D "$@" $SRC > $T/build_$n.log 2>&1 || echo "BUILD_FAIL $n"; }
build ar $AR +define+TU_PFMAX=384 & build ga $GA +define+TU_PFMAX=384 & build arblk_a $AR $BLK &
build arblk_s $AR $BLK +define+TU_SYNCPHY & build gablk_s $GA $BLK +define+TU_SYNCPHY & wait
for n in ar ga arblk_a arblk_s gablk_s; do [ -x $T/b/$n/Vtb_hbm_accel_tu_endpoint ] || { echo "HCOLL_SR ERROR build $n"; tail -5 $T/build_$n.log; exit 3; }; done
J=$T/jobs.txt; : > $J
for r in 0 13 63; do for s in 1 2; do echo "ar +VEC=fx/ar_p1 +PF=64 +RANK=$r +SEED=$s" >> $J; done; done
for r in 3 62; do echo "ar +VEC=fx/ar_p6 +PF=384 +RANK=$r +SEED=1" >> $J; done
for pf in 1 5 64 384; do for r in 0 95; do echo "ga +VEC=fx/gather_pf$pf +PF=$pf +RANK=$r +SEED=1" >> $J; done; done
for b in arblk_a arblk_s; do for r in 0 13 62; do echo "$b +VEC=fx/ar_p1 +PF=64 +RANK=$r +SEED=1" >> $J; done; done
for pf in 2 10 64; do for r in 0 47; do echo "gablk_s +VEC=fx/gather_pf$pf +PF=$pf +RANK=$r +SEED=1" >> $J; done; done
i=0; while read b args; do i=$((i+1)); echo "cd $T && timeout 600 b/$b/Vtb_hbm_accel_tu_endpoint $args > run_$i.log 2>&1; echo \"$b $args\" >> run_$i.log"; done < $J > $T/cmds.txt
xargs -P ${PAR:-8} -I{} bash -c '{}' < $T/cmds.txt
n=0; bad=0
for f in $T/run_*.log; do n=$((n+1))
  if ! grep -q "TUDONE .* mismatches=0 faults=0 " $f; then bad=$((bad+1)); echo "FAILED: $(tail -1 $f): $(grep -h 'TUDONE\|TUTIMEOUT\|TUMISMATCH' $f | head -2)"; fi
done
grep -h TUDONE $T/run_*.log | sed 's/^/  /' | cut -c1-200 > $T/summary.txt
if [ $bad -eq 0 ] && [ $n -eq $(wc -l < $J) ]; then echo "HCOLL_SR PASS runs=$n mutant=$MUT"; rc=0
else echo "HCOLL_SR MISMATCH bad=$bad of $n mutant=$MUT"; rc=1; fi
rm -rf $T; exit $rc
