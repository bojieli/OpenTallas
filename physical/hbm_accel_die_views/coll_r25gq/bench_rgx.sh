#!/bin/bash
# [link] 2026-10-10 hfd_coll R25GQ: hgi-1010/c's RGX memory-lane bench at the VM W2 LQ the coll top uses (32).
#   bench_rgx.sh <out> [SNK_MUT=n | LF_MUT=n]   prints RGXMEM PASS / FATAL
set -u; O=$1; M=${2:-}; mkdir -p $O; R=rtl/hbm_accel/generic
sed 's/localparam integer DEL = 4, LQ = 8;/localparam integer DEL = 4, LQ = 32;/' $R/collective/rgx/tb_hgi_coll_rgx_mem.sv > $O/tb.sv
grep -q "LQ = 32;" $O/tb.sv || { echo "RGXMEM FATAL tb LQ line not found"; exit 2; }
P=""; [ -n "$M" ] && P="-Ptb_hgi_coll_rgx_mem.${M}"
iverilog -g2012 -I$R -s tb_hgi_coll_rgx_mem $P -o $O/sim $R/collective/rgx/ot_hgi_coll_rgx_hbm.sv $R/collective/rgx/ot_hgi_coll_rgx_snk.sv \
  $R/peers/ot_hgi_hbm_lane.sv $R/vm/ot_hgi_vm_lanearb.sv $O/tb.sv > $O/build.log 2>&1 || { tail -5 $O/build.log; exit 2; }
vvp -n $O/sim > $O/sim.log 2>&1; grep -h "RGXMEM\|FATAL\|Fatal" $O/sim.log | head -3
grep -q "RGXMEM PASS" $O/sim.log
