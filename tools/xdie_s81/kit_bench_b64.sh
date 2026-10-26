#!/bin/bash
# kit_bench_b64.sh <outdir> <pass|board400|chb0>  (cwd = repo root): kit_bench.sh for the S81-COLL bank64 safe3 lane kits
# (dscoll_lane_w_b64 / dscoll_lane_e_b64): the TOKEN-XDIE-S81 vehicle with the lane tiles bound to ot_s81ph_coll_lane_safe3
# through rtl/test/xdie_s81/coll_lane_safe3_shim.sv.  Same verdicts as kit_bench.sh: pass -> PASS; board400 (tile CH_BOARD
# 400, full dense calendar) and chb0 (ch_b strap 0) -> must FAIL late.
set -u; O=$1; M=${2:-pass}; mkdir -p $O
if [ "$M" = board400 ]; then
  python3 tools/xdie_s81/gen_golden.py --out $O/gm --gap 100 --lat S=556,N=556 --per S=1.345,N=1.345 > $O/gen.txt 2>&1 \
    || { echo "GEN_FAILED"; tail -5 $O/gen.txt; exit 3; }
  A="+define+XDIE_SAFE3_CHB400 +define+XDIE_SAFE3_LANE"
else
  python3 tools/xdie_s81/gen_golden.py --out $O/gm --reps 1 --only a_allgather,stage_hop --lat S=556,N=556 --per S=1.345,N=1.345 \
    > $O/gen.txt 2>&1 || { echo "GEN_FAILED"; tail -5 $O/gen.txt; exit 3; }
  A="-GMAXCYC=40000 +define+XDIE_SAFE3_LANE"
fi
case $M in
  pass|board400) ;;
  chb0) A="$A -GCHB=0" ;;
  *) echo "usage: kit_bench_b64.sh <outdir> pass|board400|chb0"; exit 2 ;;
esac
export LANE="rtl/test/xdie_s81/coll_lane_safe3_shim.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe3.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe3.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv
 rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv
 rtl/common/ot_link_credit_rx_b64.sv rtl/common/ot_link_credit_tx_rc.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v"
J=${J:-6} bash tools/xdie_s81/run_xdie_s81.sh $O $M $O/gm ep $A; rc=$?
grep -h "^XDIE_LINK" $O/$M/run.log 2>/dev/null
exit $rc
