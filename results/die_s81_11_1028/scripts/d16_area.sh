#!/bin/bash
# area (yosys + abc, ASAP7 RVT TT NLDM, 64-bit, LAPX 3) of ot_dp_clk_landing_ca at DEPTH 4/8/16 (as results/meso_count_1027 area.txt)
set -u; repo=$1; out=$2; mkdir -p $out; cd $out
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
mkdir -p lib; for f in $L/*RVT_TT*; do case $f in *.gz) zcat $f > lib/$(basename $f .gz);; *) cp $f lib/;; esac; done
LIBS=$(ls lib/*.lib | grep -v FAKE)
cat lib/asap7sc7p5t_{AO,INVBUF,OA,SIMPLE}_RVT_TT*.lib > /dev/null
for D in 4 8 16; do
  LA=""; for l in $LIBS; do LA="$LA -liberty $l"; done
  yosys -q -p "read_verilog -sv -DSYNTHESIS $repo/rtl/common/ot_meso_fifo.sv $repo/rtl/common/ot_dp_clk_landing.sv $repo/rtl/common/ot_dp_clk_landing_ca.sv; chparam -set W 64 -set DEPTH $D -set K 2 ot_dp_clk_landing_ca; synth -flatten -top ot_dp_clk_landing_ca; dfflibmap -liberty lib/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc $LA; opt_clean; tee -o area_d$D.txt stat $LA" > y_d$D.log 2>&1
  echo "D$D $(grep -E 'Chip area|Number of cells' area_d$D.txt | tr -s ' ' | tr '\n' ' ')"
done
