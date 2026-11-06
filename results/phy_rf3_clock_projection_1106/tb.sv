`timescale 1ns/1ps
module tb;
parameter integer MUT=0;
reg ck=0; always #5 ck=~ck;
reg rn=0,hn=0;reg [297:0] x=0;reg [33:0] ig=0;reg [31:0] unused_clocks=32'h01234567;
reg epoch=0;always #1 unused_clocks={unused_clocks[30:0],~unused_clocks[31]};
wire [296:0] a,b,raw_b;wire [31:0] removed_q;wire ea;reg eb;
ot_dp_st #(.W(32)) actual_old_clock_transport(.clk(ck),.rst_n(rn),.d(unused_clocks),.ea(epoch),.q(removed_q),.eq(ea));
// Exact remaining epoch behavior from the canonical ot_dp_st; no clock tie or extra edge.
always @(posedge ck or negedge rn) if(!rn) eb<=0;else eb<=epoch;
// These are the actual fixed RF3 provider and its exact live interface on both sides.
qkd_kvs_pcf old_provider(.ck(ck),.rst_n(rn),.hrst_n(hn),.pcf_x(x),.i_grp_f(ig),.o_grp_f(a));
qkd_kvs_pcf projected_provider(.ck(ck),.rst_n(rn),.hrst_n(hn),.pcf_x(x),.i_grp_f(ig),.o_grp_f(raw_b));
assign b = raw_b ^ ((MUT==1) ? (297'b1<<296) : 297'b0);
integer c,k,known=0,changes=0;reg [296:0] last=0;reg [296:0] observed=0;
initial begin
 for(c=0;c<260;c=c+1) begin
  @(negedge ck);
  rn=(c>=20 && !(c>=120&&c<132));hn=rn;
  epoch=~epoch;
  for(k=0;k<298;k=k+1)x[k]=$random;
  for(k=0;k<34;k=k+1)ig[k]=$random;
  // Exercise finite legal go pulses rather than an always-ready placeholder.
  ig[0]=((c%32)==0);
  @(posedge ck);#1;
  if(c>2) begin
   if(ea!==eb)begin $display("RF3_EPOCH_FAIL %0d",c);$finish_and_return(1);end
   if(a!==b)begin $display("RF3_LIVE_FAIL cycle %0d a296=%b b296=%b",c,a[296],b[296]);$finish_and_return(1);end
   for(k=0;k<297;k=k+1)if(a[k]===1'b0||a[k]===1'b1)begin
    known=known+1;observed[k]=1;if(a[k]!==last[k])changes=changes+1;
   end
   last=a;
  end
 end
 $display("RF3_LIVE_PASS cycles260 known_comparisons=%0d changes=%0d observed_bits=%0d",known,changes,$countones(observed));
 if(known<2048||changes<100||$countones(observed)<32)$finish_and_return(2);
 $finish_and_return(0);
end
endmodule
