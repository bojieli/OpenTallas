`timescale 1ns/1ps
// Functional copy of exact --hstn-posedge generator master, no station reset.
module dsfd_hstnh_53(input wire[0:0]ck,input wire[52:0]di,output wire[52:0]dq);
 reg[52:0]q;always@(posedge ck[0])q<=di;assign dq=q;
endmodule
module tb_wfc_start;
 reg ck=0,sk=0,rn=0;always #6 ck=~ck;always #8 sk=~sk;
 reg[527:0]vw=0;reg[52:0]cs=0;wire[52:0]ks;wire[526:0]swd;wire swv;wire[3:0]ft;
 reg ready=1;wire[53:0]kd;wire[5:0]st;wire[84:0]cmd;reg[8:0]dn=0;
 dsfd_wfc_vmx_w #(.POSTED(1),.VM_LINK(1),.START_DELAY_S(1))producer(.ck(ck),.ckv(sk),.rst(rn),.rsv(rn),.f_vw(vw),.f_cs(cs),.t_vc(),.t_swv(swv),.t_swd(swd),.f_swr(ready),.f_swa(1'b0),.f_kdv(kd[53]),.t_ks(ks),.t_hks(),.f_pf(1'b0),.f_lf(1'b0),.f_rf(1'b0),.t_ft(ft));
 wire[52:0]link[0:40];assign link[0]=ks;
 genvar h;generate for(h=0;h<40;h=h+1)begin:stations
 dsfd_hstnh_53 u(.ck(ck),.di(link[h]),.dq(link[h+1]));end endgenerate
 reg[35:0]pw=0;reg[34:0]image[0:7];
 dsfd_stage_seq_static_c8 #(.NOPS(2))consumer(.ck(ck),.ckv(sk),.rst(rn),.rsv(rn),.f_ks(link[40]),.t_kd(kd),.f_pw(pw),.f_plen(8'd2),.t_st(st),.c0(cmd),.c1(),.c2(),.c3(),.c4(),.c5(),.c6(),.c7(),.c12(),.d0(dn),.d1(9'd0),.d2(9'd0),.d3(9'd0),.d4(9'd0),.d5(9'd0),.d6(9'd0),.d7(9'd0),.d12(9'd0),.s0(2'd2),.s1(2'd2),.s2(2'd2),.s3(2'd2),.s4(2'd2),.s5(2'd2),.s6(2'd2),.s7(2'd2),.s12(2'd2));
 localparam[51:0]META={10'h2d3,21'h17a953,21'h0ad365};
 integer tc=0,sc=0,phase=0,cal=0,sp=0,mut=0,faultcase=0,expected_door=0,door=-1,launch=-1,capture=-1,commands=0,kits=0,pulses=0,doors=0,errors=0,due=-1;
 reg[75:0]row;
 initial begin
  if($value$plusargs("PHASE=%d",phase))begin end
  if($value$plusargs("SP=%d",sp))begin end
  if($value$plusargs("CAL=%d",cal))begin end
  if($value$plusargs("MUT=%d",mut))begin end
  if($value$plusargs("FAULT=%d",faultcase))begin end
  case(phase)
   0:expected_door=155;1,2:expected_door=156;3:expected_door=157;4:expected_door=158;5,6:expected_door=159;7:expected_door=160;
  endcase
  image[0]=(3<<26)|(2<<9)|(sp<<7);
  row=(76'd3<<52)|24'h102938;
  image[1]=row[25:0];image[2]=(1<<26)|row[51:26];image[3]=(2<<26)|row[75:52];
  row=(76'd7<<28)|(76'd15<<24);
  image[4]=(1<<28)|row[25:0];image[5]=(1<<28)|(1<<26)|row[51:26];image[6]=(1<<28)|(2<<26)|row[75:52];
  image[7]=(3<<26)|(1<<25)|(2<<9)|(sp<<7);
  #190.5;rn=1;
 end
 always@(negedge ck)begin
  vw=0;cs=0;dn=0;
  if(tc==198+phase)vw={1'b1,15'd1024,{16{32'heca86420}}};
  if(tc==200+phase)cs={1'b1,META};
  if(tc==due)dn=9'h100;
 end
 always@(negedge sk)begin
  if(faultcase&&sc==expected_door)ready=0;
  pw=0;if(sc>=25&&sc<33)pw={1'b1,image[sc-25]};end
 always@(posedge sk)begin
  if(rn)begin
   if(swv&&(&swd[526:512]))begin door=sc;doors=doors+1;if(swd[51:0]!==META)errors=errors+1;end
   if(ks[52])begin launch=sc;pulses=pulses+1;if(sc!=door+1||ks[51:0]!==META)errors=errors+1;end
   if(link[40][52])capture=sc;
   #1;
   if(kd[53])begin kits=kits+1;if(kd[52:32]!==META[41:21])errors=errors+1;end
   if(sc==250)begin
    $display("START_RESULT phase=%0d sp=%0d door=%0d tks=%0d fks=%0d doors=%0d pulses=%0d commands=%0d kits=%0d errors=%0d status=%h ft=%h",phase,sp,door,launch,capture,doors,pulses,commands,kits,errors,st,ft);
    if(!cal&&(doors!=1||pulses!=1||commands!=1||kits!=1||errors||st[5]||(faultcase ? !ft[0] : |ft)))$fatal(1,"START actual producer/consumer failed");
    $finish;
   end
  end
  sc=sc+1;
 end
 always@(posedge ck)begin
  if(rn&&consumer.u_s.kv)$display("START_CAL phase=%0d sp=%0d tc=%0d",phase,(consumer.u_s.u_issue.phase_q+1)&3,tc);
  #1;
  if(cmd[84])begin
   commands=commands+1;due=tc+3;
   if(cmd[82:73]!==META[51:42]||cmd[72:52]!==META[20:0]||cmd[51:31]!==META[41:21]||cmd[30:7]!==24'h102938||cmd[6:0]!==0)errors=errors+1;
  end
  tc=tc+1;
 end
endmodule
