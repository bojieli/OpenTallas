`timescale 1ns/1ps
// Actual full-shape controller consumer. p_am is declared external stimulus,
// delayed four edges to model the separately-proved APIPE15 port boundary.
// This proves tag/clear/reduction alignment, not port arithmetic or a head join.
module tb_spctl_port_age;
parameter integer EXTRA=4, AMI=1, RMAX=0;
reg clk=0; always #5 clk=~clk;
reg rst_n=0, go=0;
localparam NP=6, CW=51;
reg[NP*CW-1:0] pa;
reg[NP*CW-1:0] delayed[0:3];
integer cycle=0;
always @(negedge clk) begin
 cycle=cycle+1;
 for(integer p=0;p<NP;p=p+1)
  pa[CW*p+:CW]={1'b1,32'hbf800000+32'(cycle*NP+p),18'(cycle*NP+p)};
end
always @(posedge clk) begin
 delayed[0]<=pa;
 for(integer k=1;k<4;k=k+1) delayed[k]<=delayed[k-1];
end
wire[1:0] any_, mxwe, fault,ready;
wire[17:0] idx[0:1];wire[31:0] val[0:1];
wire[23:0] mxa[0:1];wire[15:0] mxm[0:1];wire[511:0] mxd[0:1];
genvar d; generate for(d=0;d<2;d=d+1)begin:g
 ot_qwen_me_spctl_w12 #(.W(16),.IL(8),.NW(18),.GT(3072),.SMIN(7),.SMAX(11),.TCUT(7),
  .XD(105),.XVM(15),.ORD(7),.ACC_LAT(7),.TREE_LAT(7),.MUL_LAT(6),.SCALE_LAT(8),
  .FAST_ISSUE(1),.KV_PREP(3),.BANDF(1),.SPRE(2),.XADDR(0),.PQ(4),.AMR(1),.AMI(AMI),.PK(1),
  .PORT_AM_EXTRA_EDGES(d?EXTRA:0)) u(
  .clk(clk),.rst_n(rst_n),.go(go),.ready(ready[d]),.land_cnt(16'd0),
  .i_nout(18'd6144),.i_tiles(18'd8),.i_k(18'd8),.i_wsrc(1'b0),.i_wbase(24'd0),
  .i_ts(24'd64),.i_ks(24'd8),.i_js(24'd1),.i_xbase(24'd8192),.i_xks(24'd1),
  .i_xjs(24'd0),.i_xcs(24'd8),.i_jsh(3'd0),.i_split(4'd9),.i_wcs(24'd0),
  .i_round(1'b1),.i_obase(24'd0),.i_ots(24'd8),.i_ojs(24'd1),.i_mmode(1'b0),
  .i_oen(1'b0),.i_amax(!RMAX),.i_rmax(1'(RMAX)),.i_mbase(24'd128),
  .x_q('0),.tr_fault('0),.p_fault('0),.fab_fault(1'b0),
  .p_am(d?delayed[3]:pa),.am_any(any_[d]),.am_idx(idx[d]),.am_val(val[d]),
  .mx_we(mxwe[d]),.mx_addr(mxa[d]),.mx_mask(mxm[d]),.mx_data(mxd[d]),.fault(fault[d]));
end endgenerate
reg[50:0] history[0:3];
reg[552:0] mxhistory[0:3];
integer errors=0, updates=0, writes=0;
reg[17:0] previous_idx=0;
always @(posedge clk)begin
 history[0]<={any_[0],idx[0],val[0]};
 mxhistory[0]<={mxwe[0],mxa[0],mxm[0],mxd[0]};
 for(integer k=1;k<4;k=k+1)begin history[k]<=history[k-1];mxhistory[k]<=mxhistory[k-1];end
end
always @(negedge clk)if(rst_n&&cycle>40)begin
 if({any_[1],idx[1],val[1]}!==history[3]) errors=errors+1;
 if(mxwe[1]!==mxhistory[3][552])errors=errors+1;
 if(mxwe[1]&&{mxa[1],mxm[1],mxd[1]}!==mxhistory[3][551:0])errors=errors+1;
 if(any_[0]&&idx[0]!=previous_idx) updates=updates+1;
 previous_idx=idx[0];
 if(mxwe[0])writes=writes+1;
 if(fault!=0)errors=errors+1;
end
initial begin
 repeat(6)@(negedge clk);rst_n=1;
 repeat(20)@(negedge clk);go=1;@(negedge clk);go=0;
 repeat(1800)@(negedge clk);
 if((!RMAX&&updates<64)||(RMAX&&writes!=1))errors=errors+1;
 $display("SPCTL_PORT_AGE extra=%0d ami=%0d rmax=%0d updates=%0d writes=%0d errors=%0d",EXTRA,AMI,RMAX,updates,writes,errors);
 if(errors)$fatal(1,"SPCTL_PORT_AGE FAIL");
 $display("SPCTL_PORT_AGE PASS");$finish;
end
endmodule
