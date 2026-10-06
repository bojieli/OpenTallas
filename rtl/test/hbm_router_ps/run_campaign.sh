#!/bin/bash
# Exact campaign for ot_gpu_router_topk_ps: PIPESEL 1 (full rate) and 2 (half-rate fallback) against the
# reference over SEEDS, plus the four planted-error negative controls (each must FAIL).
# usage: run_campaign.sh <outdir> [NV]
set -u; O=$1; NV=${2:-2000}; mkdir -p $O; cd "$(dirname "$0")/../../.."
SRC="rtl/test/hbm_router_ps/tb_router_topk_ps.sv rtl/gpu/ot_gpu_router_topk_ps.sv rtl/gpu/ot_gpu_router_topk.sv"
run() { # tag pipesel rate neg seed nv
  iverilog -g2012 -o $O/$1.vvp -s tb_router_topk_ps -P tb_router_topk_ps.PIPESEL=$2 -P tb_router_topk_ps.RATE=$3 \
    -P tb_router_topk_ps.NEG=$4 -P tb_router_topk_ps.SEED=$5 -P tb_router_topk_ps.NV=$6 $SRC && vvp -n $O/$1.vvp > $O/$1.log 2>&1
  echo "$1 rc=$?" >> $O/rc.txt; }
: > $O/rc.txt
for s in 1 2 3 4; do run ps1_s$s 1 1 0 $s $NV & run ps2_s$s 2 2 0 $s $((NV/2)) & done
for n in 1 2 3 4; do run neg${n}_ps1 1 1 $n 7 200 & run neg${n}_ps2 2 2 $n 7 200 & done
wait
grep -h "ROUTER_PS PIPESEL" $O/*.log | sort
cat $O/rc.txt | sort
