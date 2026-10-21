#!/usr/bin/env bash
set -euo pipefail
mkdir -p cxbits_area_atomic
cd cxbits_area_atomic
cp ../ot_link_afifo.sv .
cp ../cxbits_atomic_r2/qkc_afifo_bits_1021.sv .
ln -sfn ../libs libs
cat > tops.sv <<'SV'
module area_gold(input wclk,rclk,wrst_n,rrst_n,wr,rd,input[63:0]wdata,output wfull,ovf,rempty,output[4:0]wfreed,rcount,output[63:0]rdata);
  ot_link_afifo #(.W(64),.AW(4)) u(.wclk(wclk),.rclk(rclk),.wrst_n(wrst_n),.rrst_n(rrst_n),.wr(wr),.rd(rd),.wdata(wdata),.wfull(wfull),.ovf(ovf),.rempty(rempty),.wfreed(wfreed),.rcount(rcount),.rdata(rdata));
endmodule
module area_bits(input wclk,rclk,wrst_n,rrst_n,wr,rd,input[63:0]wdata,output wfull,ovf,rempty,output[4:0]wfreed,rcount,output[63:0]rdata);
  qkc_afifo_bits_1021 #(.W(64),.AW(4)) u(.wclk(wclk),.rclk(rclk),.wrst_n(wrst_n),.rrst_n(rrst_n),.wr(wr),.rd(rd),.wdata(wdata),.wfull(wfull),.ovf(ovf),.rempty(rempty),.wfreed(wfreed),.rcount(rcount),.rdata(rdata));
endmodule
SV
L=''; S='';for f in libs/*.lib;do L="$L read_liberty -lib $f;";S="$S -liberty $f";done
for mode in gold bits;do
 yosys -l "$mode.log" -p "$L read_verilog -sv -DSYNTHESIS ot_link_afifo.sv qkc_afifo_bits_1021.sv tops.sv; synth -flatten -top area_$mode; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean; tee -o $mode.json stat -json $S; write_verilog -noattr $mode.v" > "$mode.stdout.log" 2>&1
 done
