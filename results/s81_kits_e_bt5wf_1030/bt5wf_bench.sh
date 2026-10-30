#!/bin/bash
# S81-KITS-E 10-30: lockstep bench ot_v41_bterm5_w10 FP4K=1 (new) vs the 0bf70739ce4 module with fp4 tied 1 (gold),
# P0B 0..3, random FP4/FP8 words, 64 reset edges; a mutant (bit 1 read as 0) must be caught.  usage: bt5wf_bench.sh REPO OUT
set -euo pipefail
R=$(cd "$1" && pwd); O=$2; mkdir -p "$O"
git -C "$R" show 0bf70739ce4:rtl/v41rom/ot_v41_bterm5_w10.sv | sed "s/\bot_v41_bterm5_w10\b/gold_bt5/; s/\bot_v41_kreg\b/ot_v41_kreg/" > "$O/gold.sv"
sed "s/\bot_v41_bterm5_w10\b/mut_bt5/; s/{x\[3\], x\[2\], x\[2\], x\[0\]}/{x[3], x[2], 1'b0, x[0]}/" "$R/rtl/v41rom/ot_v41_bterm5_w10.sv" > "$O/mut.sv"
grep -qF "1'b0, x[0]" "$O/mut.sv"
LIBS=""; for m in ot_v41_kreg ot_hdc_delay ot_v41_csa ot_v41_inc; do LIBS="$LIBS $(grep -rlE "^\s*module\s+$m\b" "$R/rtl" --include=*.sv --include=*.v | grep -v "_sim\|rtl/test/" | head -1)"; done
for P in 0 1 2 3; do
cat > "$O/tb$P.sv" <<TB
\`timescale 1ps/1ps
module tb;
reg clk=0,rst=0,v=0; reg [255:0] xq=0,wq=0; reg signed [9:0] xe=0,we=0; reg [7:0] tag=0;
wire ga,da,ma,gf,df,mf; wire [31:0] gy,dy,my; wire [7:0] gt,dt,mt;
gold_bt5 #(.TW(8),.P0B($P)) g(.clk(clk),.rst_n(rst),.v(v),.fp4(1'b1),.xq(xq),.xe(xe),.wq(wq),.we(we),.tag(tag),.ov(ga),.y(gy),.f(gf),.otag(gt));
ot_v41_bterm5_w10 #(.TW(8),.FP4K(1),.P0B($P)) d(.clk(clk),.rst_n(rst),.v(v),.fp4(1'b1),.xq(xq),.xe(xe),.wq(wq),.we(we),.tag(tag),.ov(da),.y(dy),.f(df),.otag(dt));
mut_bt5 #(.TW(8),.FP4K(1),.P0B($P)) m(.clk(clk),.rst_n(rst),.v(v),.fp4(1'b1),.xq(xq),.xe(xe),.wq(wq),.we(we),.tag(tag),.ov(ma),.y(my),.f(mf),.otag(mt));
integer i,j,err=0,merr=0,nv=0;
initial forever begin #500 clk=1; #500 clk=0; end
initial begin
 for(i=0;i<20000;i=i+1) begin
  @(negedge clk); rst=(i>=64); v=\$random; tag=\$random; xe=\$random; we=\$random;
  for(j=0;j<8;j=j+1) begin xq[32*j+:32]=\$random; wq[32*j+:32]=\$random; end
  @(posedge clk); #1;
  if (rst && i>100) begin if ({ga,gy,gf,gt}!=={da,dy,df,dt}) begin if(err<3) \$display("DIFF i=%0d g=%h d=%h",i,{ga,gy,gf,gt},{da,dy,df,dt}); err=err+1; end
    if ({ga,gy,gf,gt}!=={ma,my,mf,mt}) merr=merr+1; if (ga) nv=nv+1; end
 end
 if (err || !merr || nv<1000) \$fatal(1,"BT5WF_FAIL P0B=$P mism=%0d mutant=%0d ov=%0d",err,merr,nv);
 \$display("BT5WF PASS P0B=$P cycles20000 mismatch0 mutant_caught%0d ov_edges%0d",merr,nv); \$finish;
end
endmodule
TB
iverilog -g2012 -s tb -o "$O/sim$P" $LIBS "$O/gold.sv" "$O/mut.sv" "$R/rtl/v41rom/ot_v41_bterm5_w10.sv" "$O/tb$P.sv"
vvp -n "$O/sim$P" | grep -E "PASS|FAIL|DIFF"
done
