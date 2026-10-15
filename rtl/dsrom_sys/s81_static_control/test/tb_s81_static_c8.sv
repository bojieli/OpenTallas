`timescale 1ns/1ps
// S-BIND: layer-die static sequencer dsfd_stage_seq_static_c8, VM engine 12 face. Ideal 3:4 clocks only.
// mode 0 exact; mode 1 latent VM status fault; mode 2 VM done one stream cycle late (must fault).
module tb_s81_static_c8;
 reg ck=0,cvk=0;always #3 ck=~ck;always #4 cvk=~cvk;
 reg rn=0;reg[52:0]ks=0;reg[35:0]pw=0;reg[7:0]plen=4;
 wire[53:0]kd;wire[5:0]st;wire[84:0]c[0:12];reg[8:0]d[0:12];reg[1:0]s[0:12];
 dsfd_stage_seq_static_c8 #(.NOPS(4),.STAGE(7))dut(
 .ck(ck),.rst(rn),.ckv(cvk),.rsv(rn),.f_ks(ks),.t_kd(kd),.f_pw(pw),.f_plen(plen),.t_st(st),
 .c0(c[0]),.c1(c[1]),.c2(c[2]),.c3(c[3]),.c4(c[4]),.c5(c[5]),.c6(c[6]),.c7(c[7]),.c12(c[12]),
 .d0(d[0]),.d1(d[1]),.d2(d[2]),.d3(d[3]),.d4(d[4]),.d5(d[5]),.d6(d[6]),.d7(d[7]),.d12(d[12]),
 .s0(s[0]),.s1(s[1]),.s2(s[2]),.s3(s[3]),.s4(s[4]),.s5(s[5]),.s6(s[6]),.s7(s[7]),.s12(s[12]));
 reg[34:0]image[0:13];reg[116:0]due[0:399];
 integer serial=-1,fast=-1,i,e,op,slot,origin,commands=0,kits=0,mode=0;
 initial begin
  if(!$value$plusargs("mode=%d",mode))mode=0;
  $readmemh("c8.hex",image);
  for(i=0;i<13;i=i+1)begin d[i]=0;s[i]=2;end
  for(i=0;i<400;i=i+1)due[i]=0;
  #30;rn=1;
 end
 // Consecutive serial PW words exercise every mailbox crossing without gaps.
 always @(negedge cvk)begin
  pw=0;ks=0;
  if(serial>=10&&serial<24)pw={1'b1,image[serial-10]};
  if(serial==199||serial==202)ks={1'b1,10'(serial==199?37:38),21'(serial==199?21946:128799),21'd1048575};
  if(mode==1&&serial==230)s[12]=3; // latent engine fault outside any issue
 end
 always @(posedge cvk)begin
  serial=serial+1;#0.1;
  if(kd[53])begin
   if(serial!=(kits==0?211:214))begin $display("KIT serial=%0d expected=%0d",serial,kits==0?211:214);$fatal(1,"wrapper fixed KIT return moved");end
   if(kd[52:32]!=(kits==0?21946:128799)||kd[31:0]!=0)$fatal(1,"KIT wrapper context corrupt");
   kits=kits+1;
  end
  if(serial==250)begin
   if(commands!=4||kits!=2)$fatal(1,"wrapper lost command or return commands=%0d kits=%0d",commands,kits);
   if((mode==0&&st[5])||(mode==1&&(!st[5]||st[4:1]!=11))||(mode==2&&(!st[5]||(st[4:1]!=8&&st[4:1]!=6))))$fatal(1,"wrapper status corrupt %h",st);
   $display("S81_STATIC_C8 mode=%0d 3:4 PW14 consecutive commands=%0d KIT=%0d status=%h",mode,commands,kits,st);$finish;
  end
 end
 always @(negedge ck)if(fast<399)for(e=0;e<13;e=e+1)d[e]=due[fast+1][9*e+:9];
 always @(posedge ck)begin
  fast=fast+1;#0.1;
  for(e=0;e<13;e=e+1)if(c[e][84])begin
   op=c[e][6:0];slot=c[e][83];origin=271+4*slot;
   if((op==0&&e!=0)||(op==1&&e!=12)||op>1||fast!=origin+op||c[e][82:73]!=(slot?38:37)||c[e][72:52]!=1048575||c[e][51:31]!=(slot?128799:21946)||c[e][30:7]!=(op?24'hfa0312:24'h102938))begin
    $display("wrapper bad fast=%0d expected=%0d e=%0d payload=%h",fast,origin+op,e,c[e]);$fatal(1,"wrapper pin cycle/context mismatch");
   end
   commands=commands+1;due[fast+3+((mode==2&&e==12)?1:0)][9*e+:9]={1'b1,1'(slot),7'(op)};
  end
 end
 initial begin #2500;$fatal(1,"wrapper timeout");end
endmodule
