#!/bin/bash
# REDESIGN-S81 2026-10-08: hub end pin-register exactness bench (iverilog). run.sh <outdir>: gold seeds 1..3 + MUT (must FAIL)
set -u
O=$(readlink -f ${1:-.}); mkdir -p $O; D=$(cd $(dirname $0) && pwd); R=$(cd $D/../../../../.. && pwd)
( cd $R && git show c206a1ac1:physical/s81_die_views/hend/m221pq/dsfd_glue.sv ) | sed -E 's/^module (dsfd_)/module old_\1/' > $O/old_glue.sv
# only the two masters under test (the glue file holds 124 masters with other primitives)
pick() { awk -v m="$2" '$0 ~ "^module "m" " {p=1} p {print} p && /^endmodule/ {p=0}' $1; }
{ pick $R/physical/s81_die_views/hend/m221pq/dsfd_glue.sv dsfd_r2l_vr_512x1__hcol; pick $R/physical/s81_die_views/hend/m221pq/dsfd_glue.sv dsfd_l2r_vr_564x1__hx_W;
  pick $O/old_glue.sv old_dsfd_r2l_vr_512x1__hcol; pick $O/old_glue.sv old_dsfd_l2r_vr_564x1__hx_W; } > $O/dut.sv
SRCS="$D/tb_hend_pinreg.sv $O/dut.sv $R/rtl/common/ot_ratio_cdc_fifo.sv"
iverilog -g2012 -o $O/g.vvp -s tb $SRCS 2> $O/build_g.log; echo "build g rc=$?"
iverilog -g2012 -DMUT -o $O/m.vvp -s tb $SRCS 2> $O/build_m.log; echo "build m rc=$?"
for s in 1 2 3; do vvp -n $O/g.vvp +SEED=$s > $O/run_g_$s.log 2>&1; done
vvp -n $O/m.vvp +SEED=1 > $O/run_m1.log 2>&1
for f in $O/run_*.log; do echo "$(basename $f): $(grep -h SUMMARY $f) $(grep -h RESULT $f)"; done > $O/summary.txt
cat $O/summary.txt
