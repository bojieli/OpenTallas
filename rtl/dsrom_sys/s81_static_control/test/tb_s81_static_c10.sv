`timescale 1ns/1ps
// S-DIE-NETLIST: layer-die static sequencer dsfd_stage_seq_static_c10 (engines 0..7 + Engram MIX4 10 + VM 12 + PQ 13).
// Same fixture as tb_s81_static_c8 (ideal 3:4 clocks, PW14 consecutive, two KIT edges); the program's two command rows
// go to engines E0 / E1 (+e0= / +e1=, image from run_static_c10.sh), so the engine-10 and engine-13 faces are proven on
// the same fixed edges as engines 0 / 12.  mode 0 exact; mode 1 latent E1 status fault; mode 2 E1 done one stream cycle
// late (must fault).  Every job launch of a c9 / c10 sequencer checks the PQ boot state (ot_s81_pq_boot_control): the
// bench boots it through the real f_pq_pw mailbox (page 6 addr 0 {length-1, base}, page 6 addr 1 reprime edges 1, page 5
// prime) with image_sealed = 1 and a calendar model that is primed by calendar_prime and consumed by stage_start; the
// PQ boot path itself is qualified by the PQ producer gates (tools/s81/pq_canonical_pins_gate.py --sequenced).
module tb_s81_static_c10;
 reg ck=0,cvk=0;always #3 ck=~ck;always #4 cvk=~cvk;
 reg rn=0;reg[52:0]ks=0;reg[35:0]pw=0;reg[7:0]plen=4;
 wire[53:0]kd;wire[5:0]st;wire[84:0]c[0:13];reg[8:0]d[0:13];reg[1:0]s[0:13];
 wire[35:0]pq_desc;wire cal_prime,cal_start;wire[11:0]cal_base;wire[12:0]cal_len;
 assign c[8]=0;assign c[9]=0;assign c[11]=0;
 reg[35:0]pqw=0;reg primed=0;
 always @(posedge ck)if(cal_prime)primed<=1;else if(cal_start)primed<=0;
 dsfd_stage_seq_static_c10 #(.NOPS(4),.STAGE(7))dut(
 .ck(ck),.rst(rn),.ckv(cvk),.rsv(rn),.f_ks(ks),.t_kd(kd),.f_pw(pw),.f_plen(plen),.t_st(st),
 .f_pq_pw(pqw),.t_pq_desc_pw(pq_desc),.calendar_prime(cal_prime),.stage_start(cal_start),.calendar_base(cal_base),
 .calendar_length(cal_len),.pq_image_sealed(1'b1),.pq_calendar_primed(primed),.pq_calendar_fault(1'b0),
 .c0(c[0]),.c1(c[1]),.c2(c[2]),.c3(c[3]),.c4(c[4]),.c5(c[5]),.c6(c[6]),.c7(c[7]),.c10(c[10]),.c12(c[12]),.c13(c[13]),
 .d0(d[0]),.d1(d[1]),.d2(d[2]),.d3(d[3]),.d4(d[4]),.d5(d[5]),.d6(d[6]),.d7(d[7]),.d10(d[10]),.d12(d[12]),.d13(d[13]),
 .s0(s[0]),.s1(s[1]),.s2(s[2]),.s3(s[3]),.s4(s[4]),.s5(s[5]),.s6(s[6]),.s7(s[7]),.s10(s[10]),.s12(s[12]),.s13(s[13]));
 reg[34:0]image[0:13];reg[125:0]due[0:399];
 integer serial=-1,fast=-1,i,e,op,slot,origin,commands=0,kits=0,mode=0,e0=0,e1=12;
 initial begin
  if(!$value$plusargs("mode=%d",mode))mode=0;
  if(!$value$plusargs("e0=%d",e0))e0=0;
  if(!$value$plusargs("e1=%d",e1))e1=12;
  $readmemh("c10.hex",image);
  for(i=0;i<14;i=i+1)begin d[i]=0;s[i]=2;end
  for(i=0;i<400;i=i+1)due[i]=0;
  #30;rn=1;
 end
 always @(negedge cvk)begin
  pw=0;ks=0;pqw=0;
  if(serial==30)pqw={1'b1,7'd0,3'd6,1'b0,12'd3,12'd0};  // calendar base 0, length 4
  if(serial==31)pqw={1'b1,7'd1,3'd6,1'b0,24'd1};        // reprime 1 edge after each job launch
  if(serial==32)pqw={1'b1,7'd0,3'd5,1'b0,24'd0};        // initial prime
  if(serial>=10&&serial<24)pw={1'b1,image[serial-10]};
  if(serial==199||serial==202)ks={1'b1,10'(serial==199?37:38),21'(serial==199?21946:128799),21'd1048575};
  if(mode==1&&serial==230)s[e1]=3; // latent engine fault outside any issue
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
   $display("S81_STATIC_C10 mode=%0d engines=%0d,%0d 3:4 PW14 consecutive commands=%0d KIT=%0d status=%h",mode,e0,e1,commands,kits,st);$finish;
  end
 end
 always @(negedge ck)if(fast<399)for(e=0;e<14;e=e+1)d[e]=due[fast+1][9*e+:9];
 always @(posedge ck)begin
  fast=fast+1;#0.1;
  for(e=0;e<14;e=e+1)if(c[e][84])begin
   op=c[e][6:0];slot=c[e][83];origin=271+4*slot;
   if((op==0&&e!=e0)||(op==1&&e!=e1)||op>1||fast!=origin+op||c[e][82:73]!=(slot?38:37)||c[e][72:52]!=1048575||c[e][51:31]!=(slot?128799:21946)||c[e][30:7]!=(op?24'hfa0312:24'h102938))begin
    $display("wrapper bad fast=%0d expected=%0d e=%0d payload=%h",fast,origin+op,e,c[e]);$fatal(1,"wrapper pin cycle/context mismatch");
   end
   commands=commands+1;due[fast+3+((mode==2&&e==e1)?1:0)][9*e+:9]={1'b1,1'(slot),7'(op)};
  end
 end
 initial begin #2500;$fatal(1,"wrapper timeout");end
endmodule
