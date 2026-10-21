#!/usr/bin/env bash
set -euo pipefail
mkdir -p fifo1_probe
cd fifo1_probe
cp ../ot_link_afifo.sv .
cp ../native_census.py .
ln -sfn ../libs libs
cat > top.sv <<'SV'
module fifo1(input wclk,rclk,wrst_n,rrst_n,wr,rd,wdata,output wfull,wfreed,ovf,rempty,rdata,output [4:0] rcount);
wire[4:0] wf;assign wfreed=|wf;
ot_link_afifo #(.W(1),.AW(4)) u_fifo (.wclk(wclk),.wrst_n(wrst_n),.wr(wr),.wdata(wdata),.wfull(wfull),.wfreed(wf),.ovf(ovf),.rclk(rclk),.rrst_n(rrst_n),.rd(rd),.rempty(rempty),.rdata(rdata),.rcount(rcount));
endmodule
SV
L=''; for f in libs/*.lib; do L="$L read_liberty -lib $f;"; done
yosys -l synth.log -p "$L read_verilog -sv -DSYNTHESIS ot_link_afifo.sv top.sv; synth -flatten -top fifo1; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean; write_verilog -noattr mapped.v" > synth_stdout.log 2>&1
args=(python3 native_census.py --netlist mapped.v --top fifo1 --out native.json);for f in libs/*.lib;do args+=(--liberty "$f");done
"${args[@]}" > native.log 2>&1
