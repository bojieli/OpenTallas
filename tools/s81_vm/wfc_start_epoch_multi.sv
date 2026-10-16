`timescale 1ns/1ps
// OFF DEFAULT component. Declared common ideal reset, no physical epoch claim.
module dsfd_hstnh_53(input wire[0:0]ck,input wire[52:0]di,output wire[52:0]dq);
 reg[52:0]q;always@(posedge ck[0])q<=di;assign dq=q;
endmodule
module tb_wfc_epoch_multi;
 reg ck=0,sk=0,rn=0;always #6 ck=~ck;always #8 sk=~sk;
 reg[527:0]vw=0;reg[52:0]cs=0;wire[52:0]ks;wire[526:0]swd;wire swv;wire[3:0]ft;
 wire[53:0]kd;wire[5:0]st;wire[84:0]cmd;reg[8:0]dn=0;
 dsfd_wfc_vmx_w #(.POSTED(1),.VM_LINK(1),.EPOCH_START_ENABLE(1),.EPOCH_COMMON_RESET_CONTRACT(1),.FIRST_SLOT_S(148),.PERIOD_S(60),.SLOT_COUNT(3))producer(.ck(ck),.ckv(sk),.rst(rn),.rsv(rn),.f_vw(vw),.f_cs(cs),.t_vc(),.t_swv(swv),.t_swd(swd),.f_swr(1'b1),.f_swa(1'b0),.f_kdv(kd[53]),.t_ks(ks),.t_hks(),.f_pf(1'b0),.f_lf(1'b0),.f_rf(1'b0),.t_ft(ft));
 wire[52:0]link[0:40];assign link[0]=ks;
 genvar h;generate for(h=0;h<40;h=h+1)begin:stations
 dsfd_hstnh_53 u(.ck(ck),.di(link[h]),.dq(link[h+1]));end endgenerate
 reg[35:0]pw=0;reg[34:0]image[0:7];
 dsfd_stage_seq_static_c8 #(.NOPS(2))consumer(.ck(ck),.ckv(sk),.rst(rn),.rsv(rn),.f_ks(link[40]),.t_kd(kd),.f_pw(pw),.f_plen(8'd2),.t_st(st),.c0(cmd),.c1(),.c2(),.c3(),.c4(),.c5(),.c6(),.c7(),.c12(),.d0(dn),.d1(9'd0),.d2(9'd0),.d3(9'd0),.d4(9'd0),.d5(9'd0),.d6(9'd0),.d7(9'd0),.d12(9'd0),.s0(2'd2),.s1(2'd2),.s2(2'd2),.s3(2'd2),.s4(2'd2),.s5(2'd2),.s6(2'd2),.s7(2'd2),.s12(2'd2));
 function automatic[51:0]meta(input integer j);
  meta={10'(10'h2d3+j),21'(21'h17a953+17*j),21'(21'h0ad365+9*j)};
 endfunction
 function automatic[51:0]expected(input integer j,input integer mode);
  expected=(j==1&&mode!=0)?52'd0:meta(j);
 endfunction
 integer tc=0,sc=0,phase=0,mode=0,pulses=0,captures=0,commands=0,kits=0,doors=0,errors=0,due=-1,firstfault=-1,j;
 reg[7:0]due_tag;reg[75:0]row;reg[51:0]e;
 initial begin
  if($value$plusargs("PHASE=%d",phase))begin end
  if($value$plusargs("MODE=%d",mode))begin end
  image[0]=(3<<26)|(2<<9)|(3<<7);
  row=(76'd3<<52)|24'h102938;
  image[1]=row[25:0];image[2]=(1<<26)|row[51:26];image[3]=(2<<26)|row[75:52];
  row=(76'd7<<28)|(76'd15<<24);
  image[4]=(1<<28)|row[25:0];image[5]=(1<<28)|(1<<26)|row[51:26];image[6]=(1<<28)|(2<<26)|row[75:52];
  image[7]=(3<<26)|(1<<25)|(2<<9)|(3<<7);
  #190.5;rn=1;
 end
 always@(negedge ck)begin
  vw=0;cs=0;dn=0;
  for(integer n=0;n<3;n=n+1)begin
   if(tc==200+80*n+phase)vw={1'b1,15'(1024+n),{16{32'heca86420}}};
   if(tc==200+80*n+phase&&!(n==1&&mode!=0))cs={1'b1,meta(n)};
  end
  // The late middle job arrives AFTER its reservation; no ready wait.
  if(mode==2&&tc==320+phase)cs={1'b1,meta(1)};
  if(tc==due)dn={1'b1,due_tag};
 end
 always@(negedge sk)begin pw=0;if(sc>=25&&sc<33)pw={1'b1,image[sc-25]};end
 always@(posedge sk)begin
  if(rn)begin
   if(swv&&(&swd[526:512]))begin
    j=(mode==1&&doors==1)?2:doors;
    if(swd[51:0]!==meta(j))errors=errors+1;
    $display("EPOCH_DOOR phase=%0d mode=%0d j=%0d serial=%0d",phase,mode,j,sc);
    doors=doors+1;
   end
   if(ks[52])begin
    if(sc!=163+60*pulses||ks[51:0]!==expected(pulses,mode))errors=errors+1;
    $display("EPOCH_LAUNCH j=%0d serial=%0d payload=%h",pulses,sc,ks[51:0]);pulses=pulses+1;
   end
   if(link[40][52])begin if(sc!=192+60*captures)errors=errors+1;captures=captures+1;end
   #1;
   if(kd[53])begin
    e=expected(kits,mode);
    if(sc!=204+60*kits||kd[52:32]!==e[41:21])errors=errors+1;
    $display("EPOCH_KIT j=%0d serial=%0d token=%h",kits,sc,kd[52:32]);kits=kits+1;
   end
   if(sc==390)begin
    $display("EPOCH_MULTI_RESULT phase=%0d mode=%0d doors=%0d pulses=%0d captures=%0d commands=%0d kits=%0d errors=%0d status=%h ft=%h firstfault=%0d",phase,mode,doors,pulses,captures,commands,kits,errors,st,ft,firstfault);
    if(pulses!=3||captures!=3||commands!=3||kits!=3||errors||st[5]||doors!=(mode==1?2:3))$fatal(1,"fixed3slot schedule/context mismatch");
    if((mode==0&&ft)||(mode!=0&&!ft[0]))$fatal(1,"multislot fault mismatch");
    if(mode!=0&&(firstfault<0||firstfault>=341))$fatal(1,"missing middle fault deadline");
    $finish;
   end
  end
  sc=sc+1;
 end
 always@(posedge ck)begin
  if(rn&&ft[0]&&firstfault<0)firstfault=tc;
  #1;
  if(cmd[84])begin
   e=expected(commands,mode);
   if(tc!=261+80*commands||cmd[83]!==1'(commands%2)||cmd[82:73]!==e[51:42]||cmd[72:52]!==e[20:0]||cmd[51:31]!==e[41:21]||cmd[30:7]!==24'h102938||cmd[6:0]!==0)errors=errors+1;
   due=tc+3;due_tag={cmd[83],7'd0};
   $display("EPOCH_COMMAND j=%0d core=%0d context=%0d payload=%h",commands,tc,cmd[83],cmd[83:0]);commands=commands+1;
  end
  tc=tc+1;
 end
endmodule
