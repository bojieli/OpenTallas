`timescale 1ns/1ps
module tb_station_cfg #(parameter integer MUT=0);
 reg ck=0,rst=0,cfg=0;always #5 ck=~ck;
 reg[1:0] mode=0;reg ws=0;reg[7:0] nw=0,k=0;reg[8:0] base=0;
 reg[1027:0] rs=0;wire fault;
 qfd_dv_redstn2 u(.ck(ck),.rst_n(rst),.cfg_v(cfg),.cfg_mode(mode),.cfg_wsrc(ws),
 .cfg_nwords(nw),.cfg_sbase(base),.cfg_kcm1(k),.rs_s(rs),.rs_n(1028'd0),.nb_i(514'd0),
 .nb_o(),.bt_re(),.bt_word(),.bt_q(256'd0),.r_v(),.r_idx(),.r_last(),.r_d(),.fault(fault));
 reg[27:0] expect_q[0:127];reg due[0:127];integer cycle=0,seen=0;
 initial for(integer i=0;i<128;i=i+1) due[i]=0;
 always @(posedge ck) begin
  if(cfg) begin due[cycle+2]=1;expect_q[cycle+2]={mode,ws,nw,base,k};end
  #1;
  if(due[cycle]) begin
   if({u.mode,u.wsrc,u.nwords,u.sbase,u.kcm1}!==expect_q[cycle])
    $fatal(1,"STATION_CFG_LOSS cycle%0d",cycle);
   for(integer j=0;j<32;j=j+1)
    if(u.local_mode[j] !== (4'b0001<<expect_q[cycle][27:26])) $fatal(1,"STATION_MODE_COPY_ALIGNMENT");
   seen=seen+1;
  end
  cycle=cycle+1;
 end
 initial begin
  repeat(8) @(negedge ck);rst=1;repeat(18) @(negedge ck);
  for(integer j=0;j<4;j=j+1) begin
   cfg=1;mode=2'(j);ws=1'(j);nw=8'(19+j);base=9'(113+j);k=8'(7+j);
   if(MUT!=0&&j==1) rs[512]=1;
   @(negedge ck);
  end
  cfg=0;rs=0;repeat(8) @(negedge ck);
  if(seen!=4) $fatal(1,"STATION_CFG_COUNT");
  if(fault) $fatal(1,"STATION_CFG_SCHEDULE_FAULT MUT%0d",MUT);
  $display("STATION_CFG PASS four consecutive configurations II1 acceptance+2 aligned32modecopies");$finish;
 end
endmodule
