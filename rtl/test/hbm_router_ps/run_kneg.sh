#!/bin/bash
# run_kneg.sh <outdir> <pos|neg> [NV]: ot_gpu_router_topk_ps PIPESEL 1 with OT_ROUTER_KNEG (negedge key3 -> key4
# copy) against the reference ot_gpu_router_topk, 4 seeds; neg = + OT_NEG_ROUTER_KNEG (key3n fed from key2), must FAIL.
set -u; O=$1; M=$2; NV=${3:-1500}; mkdir -p $O
D="-DOT_ROUTER_KNEG"; [ "$M" = neg ] && D="$D -DOT_NEG_ROUTER_KNEG"
SRC="rtl/test/hbm_router_ps/tb_router_topk_ps.sv rtl/gpu/ot_gpu_router_topk_ps.sv rtl/gpu/ot_gpu_router_topk.sv"
: > $O/rc_$M.txt
for s in 1 2 3 4; do
  ( iverilog -g2012 $D -o $O/${M}_s$s.vvp -s tb_router_topk_ps -P tb_router_topk_ps.PIPESEL=1 -P tb_router_topk_ps.RATE=1 \
      -P tb_router_topk_ps.NEG=0 -P tb_router_topk_ps.SEED=$s -P tb_router_topk_ps.NV=$NV $SRC && vvp -n $O/${M}_s$s.vvp > $O/${M}_s$s.log 2>&1
    echo "s$s rc=$?" >> $O/rc_$M.txt ) &
done; wait
grep -h "ROUTER_PS PIPESEL" $O/${M}_s*.log | sort
if grep -q "rc=[1-9]" $O/rc_$M.txt || grep -qh "FAIL" $O/${M}_s*.log; then echo "KNEG_BENCH FAIL"; exit 1; fi
echo "KNEG_BENCH PASS"
