`timescale 1ps/1fs
module wrap;
reg clk=0; always #416.5 clk=~clk;
reg rst=0, grant=1, push=0; reg [4:0] bank=4,col=0;
wire [1:0] ready,rv,cv,cwe,fault; wire[2:0]rop[0:1];wire[4:0]rb[0:1],cb[0:1],cc[0:1];
integer edge_n=0, writes=0, pushes=0, acts=0;
`define PARAM .ENABLE(1),.REF_MODE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),.PHYS_WACT(2),.WP_REG(1),.TIMING_833(1),.T_CCDS(2),.COL_TDM(1),.ROW_CADENCE(2),.T_RCD(24),.T_RP(20),.T_RAS(34),.T_RTP(7),.T_CCDL(4),.T_RRDS(4),.T_RRDL(4),.T_FAW(19),.T_RFC(421),.T_RFCPB(241),.T_REFI(4681),.T_REFIPB(144),.T_RREFD(10),.T_RTW(12),.T_WTR(17),.T_WRR(34),.T_RCDW(12)
`define PORT(N) .clk(clk),.rst_n(rst),.reset_regions({8{rst}}),.slot_parity(1'b1),.refresh_reload(8'd150),.desc_v(1'b0),.desc_r(),.desc_row(19'd0),.desc_n(11'd0),.go(1'b1),.next_posted(1'b0),.row_v(rv[N]),.row_prio(),.row_gnt(grant),.row_op(rop[N]),.row_bank(rb[N]),.row_row(),.col_v(cv[N]),.col_bank(cb[N]),.col_col(cc[N]),.cred_ret(3'd0),.busy(),.ref_fault(fault[N]),.wr_v(push),.wr_bank(bank),.wr_col(col),.wr_r(ready[N]),.col_we(cwe[N]),.wr_rd(1'b0),.col_aq()
ot_hbm_r14_stream_pc_strap_h9_off #(`PARAM) a(`PORT(0));
ot_hbm_r14_stream_pc_strap_h9_on #(`PARAM) b(`PORT(1));
`undef PORT
`undef PARAM
always @(posedge clk) begin
 if(!rst)begin edge_n=0;writes=0;pushes=0;acts=0;end else begin
  edge_n=edge_n+1;
  if(push&&ready[0]) pushes=pushes+1;
  if(cv[0]&&cwe[0])writes=writes+1;
  if(rv[0]&&grant&&rop[0]==3'd1)acts=acts+1;
 end
end
always @(negedge clk) if(rst) begin
 if(fault!==0)$fatal(1,"WRAP_FAULT edge%0d",edge_n);
 if(ready[0]!==ready[1] || rv[0]!==rv[1] || cv[0]!==cv[1] || (rv[0]&&{rop[0],rb[0]}!=={rop[1],rb[1]}) || (cv[0]&&{cwe[0],cb[0],cc[0]}!=={cwe[1],cb[1],cc[1]}))
  $fatal(1,"WQDIAG_WRAP_DIFF edge%0d goldrow%0d maskrow%0d pwin%h/%h",edge_n,rb[0],rb[1],a.on.pwin,b.on.pwin);
end
task put(input[4:0]b,input[4:0]c);begin
 @(negedge clk);#1;bank=b;col=c;push=1;
 while(ready!==2'b11)begin @(negedge clk);#1;if(edge_n>120)$fatal(1,"WRAP_READY_TIMEOUT");end
 @(negedge clk);#1;push=0;
end endtask
integer i;
initial begin
 repeat(64)@(negedge clk);#1;rst=1;
 put(4,0);
 wait(writes==1);@(negedge clk);#1;grant=0;
 put(1,1);
 for(i=2;i<32;i=i+1)put(4,5'(i));
 put(2,0);
 repeat(3)@(negedge clk);
 if(a.on.wq_rp!=1 || a.on.wq_pv!==32'hffffffff || a.on.wq_act_physical!==32'h00000003 || a.on.pwin!==32'h00000002)
  $fatal(1,"WRAP_NOT_TARGET rp%0d pv%h elig%h pwin%h edge%0d",a.on.wq_rp,a.on.wq_pv,a.on.wq_act_physical,a.on.pwin,edge_n);
 $display("WQDIAG_WRAP_TARGET edge%0d pushes%0d eligible%h winner%h",edge_n,pushes,a.on.wq_act_physical,a.on.pwin);$fflush();
 #1;grant=1;repeat(12)@(negedge clk);
 if(pushes!=33 || acts<2)$fatal(1,"WRAP_VACUOUS pushes%0d acts%0d",pushes,acts);
 $display("WQDIAG_WRAP_PASS edges%0d pushes%0d writes%0d acts%0d",edge_n,pushes,writes,acts);$finish;
end
initial begin repeat(180)@(posedge clk);if(rst&&edge_n>140)$fatal(1,"WRAP_BOUND");end
endmodule
