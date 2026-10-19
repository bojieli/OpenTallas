`timescale 1ns/1ps
module tb_a0_reset_cut;
reg [16:0] ck=0;
reg [16:0] run=0;
reg rs=0; wire [18:0] leaf; integer MUT=0; initial if($value$plusargs("MUT=%d",MUT))begin end
a0_actual_reset_cut dut (.rst_n(rs),.ck(ck[0]),.ck_fa2(ck[1]),.ck_fa3(ck[2]),.ck_fa4(ck[3]),.ck_node(ck[4]),.ck_rn(ck[5]),.ck_rnw(ck[6]),.ck_rs(ck[7]),.ck_rsw(ck[8]),.ck_tx0(ck[9]),.ck_tx1(ck[10]),.ck_tx2(ck[11]),.ck_tx3(ck[12]),.ck_tx4(ck[13]),.ck_tx5(ck[14]),.ck_tx6(ck[15]),.ck_tx7(ck[16]),.leaf(leaf));
reg [2:0] face=0;
always @(posedge ck[3] or negedge rs) if(!rs) face<=0; else face<={face[1:0],1'b1};
integer checks=0;
reg expect_0=0; always @(posedge ck[0] or negedge face[2]) if(!face[2])expect_0<=0;else expect_0<=1;
always @(negedge ck[0]) begin checks=checks+1;if(leaf[0]!==expect_0) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf0 MUT%0d",MUT);end
reg expect_1=0; always @(posedge ck[0] or negedge face[2]) if(!face[2])expect_1<=0;else expect_1<=1;
always @(negedge ck[0]) begin checks=checks+1;if(leaf[1]!==expect_1) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf1 MUT%0d",MUT);end
reg expect_2=0; always @(posedge ck[0] or negedge face[2]) if(!face[2])expect_2<=0;else expect_2<=1;
always @(negedge ck[0]) begin checks=checks+1;if(leaf[2]!==expect_2) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf2 MUT%0d",MUT);end
reg expect_3=0; always @(posedge ck[0] or negedge face[2]) if(!face[2])expect_3<=0;else expect_3<=1;
always @(negedge ck[0]) begin checks=checks+1;if(leaf[3]!==expect_3) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf3 MUT%0d",MUT);end
reg expect_4=0; always @(posedge ck[1] or negedge face[2]) if(!face[2])expect_4<=0;else expect_4<=1;
always @(negedge ck[1]) begin checks=checks+1;if(leaf[4]!==expect_4) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf4 MUT%0d",MUT);end
reg expect_5=0; always @(posedge ck[2] or negedge face[2]) if(!face[2])expect_5<=0;else expect_5<=1;
always @(negedge ck[2]) begin checks=checks+1;if(leaf[5]!==expect_5) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf5 MUT%0d",MUT);end
reg expect_6=0; always @(posedge ck[4] or negedge face[2]) if(!face[2])expect_6<=0;else expect_6<=1;
always @(negedge ck[4]) begin checks=checks+1;if(leaf[6]!==expect_6) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf6 MUT%0d",MUT);end
reg expect_7=0; always @(posedge ck[5] or negedge face[2]) if(!face[2])expect_7<=0;else expect_7<=1;
always @(negedge ck[5]) begin checks=checks+1;if(leaf[7]!==expect_7) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf7 MUT%0d",MUT);end
reg expect_8=0; always @(posedge ck[6] or negedge face[2]) if(!face[2])expect_8<=0;else expect_8<=1;
always @(negedge ck[6]) begin checks=checks+1;if(leaf[8]!==expect_8) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf8 MUT%0d",MUT);end
reg expect_9=0; always @(posedge ck[7] or negedge face[2]) if(!face[2])expect_9<=0;else expect_9<=1;
always @(negedge ck[7]) begin checks=checks+1;if(leaf[9]!==expect_9) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf9 MUT%0d",MUT);end
reg expect_10=0; always @(posedge ck[8] or negedge face[2]) if(!face[2])expect_10<=0;else expect_10<=1;
always @(negedge ck[8]) begin checks=checks+1;if(leaf[10]!==expect_10) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf10 MUT%0d",MUT);end
reg expect_11=0; always @(posedge ck[9] or negedge face[2]) if(!face[2])expect_11<=0;else expect_11<=1;
always @(negedge ck[9]) begin checks=checks+1;if(leaf[11]!==expect_11) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf11 MUT%0d",MUT);end
reg expect_12=0; always @(posedge ck[10] or negedge face[2]) if(!face[2])expect_12<=0;else expect_12<=1;
always @(negedge ck[10]) begin checks=checks+1;if(leaf[12]!==expect_12) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf12 MUT%0d",MUT);end
reg expect_13=0; always @(posedge ck[11] or negedge face[2]) if(!face[2])expect_13<=0;else expect_13<=1;
always @(negedge ck[11]) begin checks=checks+1;if(leaf[13]!==expect_13) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf13 MUT%0d",MUT);end
reg expect_14=0; always @(posedge ck[12] or negedge face[2]) if(!face[2])expect_14<=0;else expect_14<=1;
always @(negedge ck[12]) begin checks=checks+1;if(leaf[14]!==expect_14) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf14 MUT%0d",MUT);end
reg expect_15=0; always @(posedge ck[13] or negedge face[2]) if(!face[2])expect_15<=0;else expect_15<=1;
always @(negedge ck[13]) begin checks=checks+1;if(leaf[15]!==expect_15) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf15 MUT%0d",MUT);end
reg expect_16=0; always @(posedge ck[14] or negedge face[2]) if(!face[2])expect_16<=0;else expect_16<=1;
always @(negedge ck[14]) begin checks=checks+1;if(leaf[16]!==expect_16) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf16 MUT%0d",MUT);end
reg expect_17=0; always @(posedge ck[15] or negedge face[2]) if(!face[2])expect_17<=0;else expect_17<=1;
always @(negedge ck[15]) begin checks=checks+1;if(leaf[17]!==expect_17) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf17 MUT%0d",MUT);end
reg expect_18=0; always @(posedge ck[16] or negedge face[2]) if(!face[2])expect_18<=0;else expect_18<=1;
always @(negedge ck[16]) begin checks=checks+1;if(leaf[18]!==expect_18) $fatal(1,"A0_RESET_CUT_TRACE_FAIL leaf18 MUT%0d",MUT);end
initial begin #0.01;if(MUT==42)force dut.\a0_reset_face1_q = rs; if(MUT==41)force dut.\a0_reset_leaf_11_q = 1'b0; if(MUT==43)force dut.\a0_reset_face1_q = 1'b1; if(MUT==44)force dut.\a0_reset_branch_q = dut.\a0_reset_face2_q ;end
integer scenario,step,i;integer latest_ready;initial begin
#0.1;rs=0;#0.1;rs=1;
for(scenario=0;scenario<32;scenario++)begin
 run=0;ck=0;#0.1;rs=0;#0.1;
 if(leaf!==0)$fatal(1,"A0_RESET_STOPPED_ASSERT_FAIL scenario%0d leaf%h",scenario,leaf);
#0.1;rs=1;#0.1;if(leaf!==0)$fatal(1,"A0_RESET_STOPPED_RELEASE_FAIL");
 latest_ready=-1;
 for(step=0;step<160;step++)begin
  for(i=0;i<17;i++)begin
   if(step>=((i+scenario)%17)*2)run[i]=1;
   if(run[i] && ((step+i+scenario)%2==0))ck[i]=~ck[i];
  end
  #0.1;if(leaf===19'h7ffff && latest_ready<0)latest_ready=step;
 end
 if(latest_ready<0)$fatal(1,"A0_RESET_RESUME_FAIL");
 $display("A0_RESET_EPOCH scenario%0d ready_step%0d",scenario,latest_ready);
end
$display("A0_RESET_CUT_PASS scenarios32 independent_clocks%d checks%0d",17,checks);$finish;end endmodule
