`timescale 1ns/1ps
module tb;
reg clk=0; always #0.4165 clk=~clk;
reg rst_n=0,ta=0,tb=0; integer cycle=0,ca=-2,cb=0;
localparam [15:0] EP=16'h0b0b;
localparam [63:0] DG=64'h514bb0b28004c8e8, FT=64'h5850463100001046;
function [547:0] record(input integer n);
reg[547:0] r; begin r=0;
if(n==20)begin r[542:539]=14;r[538:533]=63;r[532:517]=EP;r[65]=1;r[64]=1;r[63:0]=DG;end
record=r;end endfunction
reg[547:0] r_a,r_b;reg[166:0] da=0;reg[384:0] db=0;wire[166:0] qa;wire[384:0] qb;
wire ra,rb,fa,fb;
ot_dp_clk_landing_cas #(.W(167),.DEPTH(4)) a(.fclk(clk),.t_rst_n(ta),.clk(clk),.rst_n(rst_n),.strap_k(6'd47),.d(da),.q(qa),.ready(ra),.fault(fa));
ot_dp_clk_landing_cas #(.W(385),.DEPTH(4)) b(.fclk(clk),.t_rst_n(tb),.clk(clk),.rst_n(rst_n),.strap_k(6'd47),.d(db),.q(qb),.ready(rb),.fault(fb));
reg[166:0] pa[0:9];reg[384:0] pb[0:9];integer i;
initial begin for(i=0;i<10;i=i+1)begin pa[i]=0;pb[i]=0;end end
always @(negedge clk) begin
cycle=cycle+1;if(cycle==1)rst_n=1;if(cycle==45)ta=1;if(cycle==45)tb=1;
if(ta)begin r_a=record(ca);da={ca==20,2'b00,ca==20,r_a[547:385]};ca=ca+1;end
if(tb)begin r_b=record(cb);db=r_b[384:0];cb=cb+1;end
end
always @(posedge clk)begin pa[0]<=qa;pb[0]<=qb;for(integer j=1;j<10;j=j+1)begin pa[j]<=pa[j-1];pb[j]<=pb[j-1];end end
wire bad,good,mut;wire bi,gi,mi;wire bc,gc,mc;
qkd_program_witness_rx old(.ck(clk),.rst_n(rst_n),.program_begin_v(1'b0),.receive_slot(pa[7][166]),.rx_v(pa[7][163]),.rx_record({pa[7][162:0],pb[9]}),.expected_epoch(EP),.expected_digest(DG),.authorized_footer_valid(1'b1),.authorized_footer(FT),.program_commit_v(bc),.program_installed_valid(bi),.fault(bad));
qkd_program_witness_rx fixed(.ck(clk),.rst_n(rst_n),.program_begin_v(1'b0),.receive_slot(pa[9][166]),.rx_v(pa[9][163]),.rx_record({pa[9][162:0],pb[9]}),.expected_epoch(EP),.expected_digest(DG),.authorized_footer_valid(1'b1),.authorized_footer(FT),.program_commit_v(gc),.program_installed_valid(gi),.fault(good));
qkd_program_witness_rx offby1(.ck(clk),.rst_n(rst_n),.program_begin_v(1'b0),.receive_slot(pa[8][166]),.rx_v(pa[8][163]),.rx_record({pa[8][162:0],pb[9]}),.expected_epoch(EP),.expected_digest(DG),.authorized_footer_valid(1'b1),.authorized_footer(FT),.program_commit_v(mc),.program_installed_valid(mi),.fault(mut));
always @(negedge clk) if(cycle==120)begin
$display("WITNESS_PACKET old_fault=%b old_installed=%b fixed_fault=%b fixed_installed=%b offby1_fault=%b offby1_installed=%b ring_fault=%b%b",bad,bi,good,gi,mut,mi,fa,fb);
if(!(!bad&&bi&&!good&&!gi&&!mut&&!mi&&!fa&&!fb))$fatal(1,"unexpected witness result");$finish;end
endmodule
