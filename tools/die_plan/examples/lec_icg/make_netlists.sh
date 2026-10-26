#!/bin/bash
# regenerate the gate netlists of the LEC clock-gate fixture inside the ORFS image (docker, 2 GB):
#   tools/die_plan/examples/lec_icg/make_netlists.sh
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
docker run --rm -m 2g -u "$(id -u):$(id -g)" -v "$D:/fx" -w /fx openroad/orfs:asap7lock bash -lc '
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
zcat $L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz > /tmp/simple.lib
zcat $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz > /tmp/invbuf.lib
for v in ok MUT_INV_EN MUT_WRONG_GATE MUT_UNGATED REF_CASCADE REF_CLK_IN_EN REF_NEGEDGE REF_GCLK_LOGIC; do
  def=""; [ $v = ok ] || def="-D$v"
  $Y -q -p "read_verilog -sv /fx/icg_bb.v; read_verilog -sv /fx/lec_bbx.v; read_verilog -sv -DSYNTHESIS $def /fx/lec_icg_t.sv;
    hierarchy -top lec_icg_t; synth -flatten -top lec_icg_t; rename -wire t:\$_*DFF*_;
    dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty /tmp/simple.lib -liberty /tmp/invbuf.lib;
    hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean;
    write_verilog -noattr -noexpr /fx/netlist_$v.v"
done'
