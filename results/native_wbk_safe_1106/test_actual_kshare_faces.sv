`timescale 1ns/1ps
module test_out_protocol;
 parameter integer READY_NEGEDGE=1,MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst=0; integer cyc=0;
 reg [15:0] iv[0:1];wire [15:0] ir[0:1];reg [479:0] ia[0:1];reg[4095:0] id[0:1];
 wire [15:0] ov[0:1];reg [15:0] ore[0:1];wire[479:0] oa[0:1];wire[4095:0] od[0:1];
 wire[15:0]rdy_src[0:1],rx_v[0:1];wire[479:0]rx_a[0:1];wire[4095:0]rx_d[0:1];integer linked[0:1];
 ot_wbq_sw_split_out__fcore ref_raw(.hbm_clk(clk),.hbm_rst_n(rst),.in_v(iv[0]),.in_ready(ir[0]),.in_addr(ia[0]),.in_data(id[0]),.w_k_v(ov[0]),.w_k_rdy(rdy_src[0]),.w_k_addr(oa[0]),.w_k_wdata(od[0]));
 ot_wbq_sw_split_out__elastic_native #(.READY_NEGEDGE(READY_NEGEDGE),.MUT(MUT)) dut_real(.hbm_clk(clk),.hbm_rst_n(rst),.in_v(iv[1]),.in_ready(ir[1]),.in_addr(ia[1]),.in_data(id[1]),.w_k_v(ov[1]),.w_k_rdy(rdy_src[1]),.w_k_addr(oa[1]),.w_k_wdata(od[1]));
 genvar pp;
 generate for(pp=0;pp<16;pp=pp+1)begin:ref_receive
 ot_hbm_svc_pin_skid2 #(.WIDTH(286)) u_e(.clk(clk),.rst_n(rst),.in_v(ov[0][pp]),.in_r(rdy_src[0][pp]),
 .in_data({oa[0][30*pp+:30],od[0][256*pp+:256]}),.out_v(rx_v[0][pp]),.out_r(ore[0][pp]),.out_data({rx_a[0][30*pp+:30],rx_d[0][256*pp+:256]}));
 end endgenerate
 captured_kshare_wb_faces real_receiver(.hbm_clk(clk),.hbm_rst_n(rst),.w_k_v(ov[1][3:0]),.w_k_rdy(rdy_src[1][3:0]),
 .w_k_addr(oa[1][119:0]),.w_k_wdata(od[1][1023:0]),.rx_v(rx_v[1][3:0]),.rx_rdy(ore[1][3:0]),.rx_addr(rx_a[1][119:0]),.rx_data(rx_d[1][1023:0]));
 assign rdy_src[1][15:4]=0;assign rx_v[1][15:4]=0;assign rx_a[1][479:120]=0;assign rx_d[1][4095:1024]=0;
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
    if(ov[u][0]&&rdy_src[u][0])linked[u]<=linked[u]+1;
    if(rx_v[u][0]&&ore[u][0])begin
     if(rx_a[u][0+:30]!==30'(got[u])||rx_d[u][0+:256]!==256'(got[u]))begin
      bad[u]<=bad[u]+1;
      if(bad[u]<5)$display("OUT_PROTOCOL_MISMATCH variant=%0d cycle=%0d expected=%0d addr=%0d data=%0d",u,cyc,got[u],rx_a[u][0+:30],rx_d[u][0+:256]);
     end
     got[u]<=got[u]+1;
    end
    // READY is a real consumer register, sampled literally on the external interface.
    ore[u]<=((cyc%13>=4)&&(cyc%13<10))?16'hffff:16'h0;
   end
  end
 end
 initial begin
  for(u=0;u<2;u=u+1)begin iv[u]=0;ia[u]=0;id[u]=0;ore[u]=0;sent[u]=0;got[u]=0;bad[u]=0;linked[u]=0;end
  repeat(8)@(negedge clk);rst=1;repeat(16)@(negedge clk);
  for(u=0;u<2;u=u+1)iv[u]=1;
  repeat(250)@(negedge clk);
  $display("NATIVE_LINK_TAKES raw=%0d physical_partner=%0d",linked[0],linked[1]);
  $display("KSHARE_FACE_PROTOCOL_RESULT raw sent=%0d got=%0d bad=%0d real sent=%0d got=%0d bad=%0d",sent[0],got[0],bad[0],sent[1],got[1],bad[1]);
  if(sent[0]!=32||got[0]!=32||bad[0]!=0)$fatal(1,"REFERENCE_VEHICLE_FAIL");
  if(sent[1]!=32||got[1]!=32||bad[1]!=0)$fatal(1,"REAL_OUT_PROTOCOL_FAIL");
  $display("OUT_PROTOCOL_PASS");$finish;
 end
endmodule
