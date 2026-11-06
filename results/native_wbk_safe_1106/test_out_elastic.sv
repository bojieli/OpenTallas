`timescale 1ns/1ps
module test_out_protocol;
 parameter integer READY_NEGEDGE=1,MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst=0; integer cyc=0;
 reg [15:0] iv[0:1];wire [15:0] ir[0:1];reg [479:0] ia[0:1];reg[4095:0] id[0:1];
 wire [15:0] ov[0:1];reg [15:0] ore[0:1];wire[479:0] oa[0:1];wire[4095:0] od[0:1];
 ot_wbq_sw_split_out__fcore ref_raw(.hbm_clk(clk),.hbm_rst_n(rst),.in_v(iv[0]),.in_ready(ir[0]),.in_addr(ia[0]),.in_data(id[0]),.w_k_v(ov[0]),.w_k_rdy(ore[0]),.w_k_addr(oa[0]),.w_k_wdata(od[0]));
 ot_wbq_sw_split_out__elastic_native #(.READY_NEGEDGE(READY_NEGEDGE),.MUT(MUT)) dut_real(.hbm_clk(clk),.hbm_rst_n(rst),.in_v(iv[1]),.in_ready(ir[1]),.in_addr(ia[1]),.in_data(id[1]),.w_k_v(ov[1]),.w_k_rdy(ore[1]),.w_k_addr(oa[1]),.w_k_wdata(od[1]));
 integer sent[0:1],got[0:1],bad[0:1];integer u;
 always @(posedge clk)begin
  cyc<=cyc+1;
  for(u=0;u<2;u=u+1)begin
   if(rst&&cyc>20)begin
    if(iv[u][0]&&ir[u][0])begin
     sent[u]<=sent[u]+1;
     if(sent[u]==31)iv[u]<=0;
     else begin ia[u][0+:30]<=30'(sent[u]+1);id[u][0+:256]<=256'(sent[u]+1);end
    end
    if(ov[u][0]&&ore[u][0])begin
     if(oa[u][0+:30]!==30'(got[u])||od[u][0+:256]!==256'(got[u]))begin
      bad[u]<=bad[u]+1;
      if(bad[u]<5)$display("OUT_PROTOCOL_MISMATCH variant=%0d cycle=%0d expected=%0d addr=%0d data=%0d",u,cyc,got[u],oa[u][0+:30],od[u][0+:256]);
     end
     got[u]<=got[u]+1;
    end
    // READY is a real consumer register, sampled literally on the external interface.
    ore[u]<=((cyc%13>=4)&&(cyc%13<10))?16'hffff:16'h0;
   end
  end
 end
 initial begin
  for(u=0;u<2;u=u+1)begin iv[u]=0;ia[u]=0;id[u]=0;ore[u]=0;sent[u]=0;got[u]=0;bad[u]=0;end
  repeat(8)@(negedge clk);rst=1;repeat(16)@(negedge clk);
  for(u=0;u<2;u=u+1)iv[u]=1;
  repeat(250)@(negedge clk);
  $display("OUT_PROTOCOL_RESULT raw sent=%0d got=%0d bad=%0d real sent=%0d got=%0d bad=%0d",sent[0],got[0],bad[0],sent[1],got[1],bad[1]);
  if(sent[0]!=32||got[0]!=32||bad[0]!=0)$fatal(1,"REFERENCE_VEHICLE_FAIL");
  if(sent[1]!=32||got[1]!=32||bad[1]!=0)$fatal(1,"REAL_OUT_PROTOCOL_FAIL");
  $display("OUT_PROTOCOL_PASS");$finish;
 end
endmodule
