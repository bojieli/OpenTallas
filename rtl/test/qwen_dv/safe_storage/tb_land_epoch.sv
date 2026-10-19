`timescale 1ns/1ps
module tb_land_epoch #(parameter integer MUT=0);
reg ck=0,rsi=0;always #5 ck=~ck;
integer cycle=0;
always @(negedge ck) begin cycle=cycle+1;rsi=(cycle>=8 && !(cycle>=701&&cycle<711));end
for(genvar t=0;t<4;t=t+1) begin:g_width
 localparam integer W=(t==0)?1:(t==1)?32:(t==2)?97:1073;
 reg[W-1:0] d=0;
 always @(negedge ck) for(integer b=0;b<W;b=b+1) d[b]=$random;
 for(genvar k=1;k<=3;k=k+1) begin:g_k
  wire[4*W-1:0] ba,bb,ca,cb;wire[11:0] ea,eb,fa,fb;wire[3:0] va,vb;
  localparam integer C=(W+23)/24;
  wire[4*C-1:0] xa,xb;wire[W-1:0] oa,ob,pa,pb;
  ot_pl_land_w #(.W(W),.D(4)) a(.ck(ck),.rsi(rsi),.i(d),.bank(ba),.epo(ea),.vld(va));
  ref_ot_pl_land_w #(.W(W),.D(4)) b(.ck(ck),.rsi(rsi),.i(d),.bank(bb),.epo(eb),.vld(vb));
  ot_pl_land_r #(.W(W),.D(4),.K((MUT!=0&&k==2)?3:k)) ar(.ck(ck),.rsi(rsi),.bank(ba),.epo(ea),.vld(va),.o(oa));
  ref_ot_pl_land_r #(.W(W),.D(4),.K(k)) br(.ck(ck),.rsi(rsi),.bank(bb),.epo(eb),.vld(vb),.o(ob));
  ot_pl_land_chunk_w #(.W(W),.D(4),.CHUNK_BITS(24)) c(.ck(ck),.rsi(rsi),.i(d),.bank(ca),.epo(fa),.vld(xa));
  ref_ot_pl_land_chunk_w #(.W(W),.D(4),.CHUNK_BITS(24)) e(.ck(ck),.rsi(rsi),.i(d),.bank(cb),.epo(fb),.vld(xb));
  ot_pl_land_chunk_r #(.W(W),.D(4),.K(k),.CHUNK_BITS(24)) cr(.ck(ck),.rsi(rsi),.bank(ca),.epo(fa),.vld(xa),.o(pa));
  ref_ot_pl_land_chunk_r #(.W(W),.D(4),.K(k),.CHUNK_BITS(24)) er(.ck(ck),.rsi(rsi),.bank(cb),.epo(fb),.vld(xb),.o(pb));
  always @(posedge ck) begin #1;
   if({ba,va,ca,xa,oa,pa}!=={bb,vb,cb,xb,ob,pb})$fatal(1,"LAND_EPOCH_FUNCTIONAL_MISMATCH W%0d K%0d edge%0d",W,k,cycle);
`ifndef SYNTHESIS
   if({ea,fa}!=={eb,fb})$fatal(1,"LAND_EPOCH_ASSERTION_STATE_MISMATCH");
`else
   if({ea,fa}!==24'd0)$fatal(1,"LAND_EPOCH_SYNTH_DIAGNOSTICS_NOT_ZERO");
`endif
  end
 end
end
initial begin repeat(1600)@(negedge ck);$display("LAND_EPOCH_EQ PASS widths1/32/97/1073 K1/2/3 legacy+chunk24 1600edges tworesets");$finish;end
endmodule
