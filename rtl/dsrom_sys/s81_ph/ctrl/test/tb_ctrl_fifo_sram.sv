`timescale 1ps/1ps
module tb_ctrl_fifo_sram;
parameter integer W=340, PHASE=0;
reg wc=0,rc=0,rst=0,wv=0,pop=0;
reg [W-1:0] wd=0;
wire ov,nv,orv,nrv,oc,nc,oo,no;
wire [W-1:0] od,nd;
localparam integer NG=(W+31)/32;
integer nw=0,nr=0,checks=0,reads=0,errors=0,j;
always #416 wc=~wc;
initial begin #(PHASE); forever #450 rc=~rc; end
ot_s81ph_afifo_g #(.W(W),.DEPTH(8),.AF(1)) oldq(
.wclk(wc),.wrst_n(rst),.w_v(wv),.w_d(wd),.w_rdy(ov),.w_credit(oc),.w_ovf(oo),
.rclk(rc),.rrst_n(rst),.r_v(orv),.r_pop(pop),.r_pop_g({NG{pop}}),.r_d(od));
ot_s81ph_afifo_g_sram #(.W(W),.DEPTH(8),.AF(1)) newq(
.wclk(wc),.wrst_n(rst),.w_v(wv),.w_d(wd),.w_rdy(nv),.w_credit(nc),.w_ovf(no),
.rclk(rc),.rrst_n(rst),.r_v(nrv),.r_pop(pop),.r_pop_g({NG{pop}}),.r_d(nd));
always @(negedge wc) begin
 nw=nw+1;
 wv=rst&&ov&&(nw%7!=0);
 for(j=0;j<W;j=j+1) wd[j]=1'((nw*29+j*17)^(nw>>(j%8)));
end
always @(negedge rc) begin nr=nr+1;pop=rst&&(nr%113<85)&&(nr%5!=0);end
always @(posedge wc) if(rst) begin
 #2;checks=checks+1;
 if({ov,oc,oo}!=={nv,nc,no}) begin errors=errors+1;$display("CTRL_FIFO_DIFF writeflags at%0t",$time);end
end
always @(posedge rc) if(rst) begin
 #2;checks=checks+1;
 if(orv!==nrv) begin errors=errors+1;$display("CTRL_FIFO_DIFF valid at%0t",$time);end
 if(orv) begin reads=reads+1;if(od!==nd) begin errors=errors+1;$display("CTRL_FIFO_DIFF data at%0t old=%h new=%h",$time,od,nd);end end
end
initial begin
 repeat(10) @(negedge wc);rst=1;
 repeat(3000) @(negedge wc);rst=0;
 repeat(12) @(negedge wc);rst=1;
 repeat(3000) @(negedge wc);#10;
 if(errors==0&&reads>1000) begin $display("CTRL_FIFO_EXACT PASS W%0d PHASE%0d checks%0d reads%0d",W,PHASE,checks,reads);$finish;end
 else begin $display("CTRL_FIFO_EXACT FAIL errors%0d reads%0d",errors,reads);$fatal;end
end
endmodule
