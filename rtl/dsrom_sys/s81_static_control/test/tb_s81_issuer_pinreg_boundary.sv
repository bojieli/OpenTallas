`timescale 1ns/1ps
module tb_s81_issuer_pinreg_boundary;
`ifdef S81_STATUS_C8
 localparam integer PORT_FAULT_EDGE=211,ACCEPT_EDGE=212;
`else
 localparam integer PORT_FAULT_EDGE=212,ACCEPT_EDGE=213;
`endif
 reg kit_seen=0,success=0,rejected=0;integer consumer_serial=-1;
 integer fault_fast=-1,fault_serial=-1,end_fast=-1;

 reg ck=0,cvk=0;always #3 ck=~ck;always #4 cvk=~cvk;
`ifdef OT_S81_ISSUER_SPLIT_PW
 integer root_mut=0;
 initial begin if($value$plusargs("root_mut=%d",root_mut))begin end end
 wire actual_ck=(root_mut==1&&fast>=260)?1'b0:ck;
 wire actual_ckv=(root_mut==2&&serial>=10&&serial<24)?1'b0:cvk;
 wire actual_ck_pw=(root_mut==3&&fast>=20&&fast<120)?1'b0:ck;
`else
 wire actual_ck=ck,actual_ckv=cvk;
`endif
 reg rn=0;reg[52:0]ks=0;reg[35:0]pw=0;reg[7:0]plen=4;
 wire[53:0]kd;wire[5:0]st;wire[84:0]c[0:13];reg[8:0]d[0:13];reg[1:0]s[0:13];
 wire[35:0]pq_desc;wire cal_prime,cal_start;wire[11:0]cal_base;wire[12:0]cal_len;
 assign c[8]=0;assign c[9]=0;assign c[11]=0;
 reg[35:0]pqw=0;reg primed=0;
 always @(posedge ck)if(cal_prime)primed<=1;else if(cal_start)primed<=0;
`ifdef S81_STATUS_C8
 dsfd_stage_seq_static_c8 dut(
 .ck(actual_ck),.rst(rn),.ckv(actual_ckv),.rsv(rn),.f_ks(ks),.t_kd(kd),.f_pw(pw),.f_plen(plen),.t_st(st),
 .c0(c[0]),.c1(c[1]),.c2(c[2]),.c3(c[3]),.c4(c[4]),.c5(c[5]),.c6(c[6]),.c7(c[7]),.c12(c[12]),
 .d0(d[0]),.d1(d[1]),.d2(d[2]),.d3(d[3]),.d4(d[4]),.d5(d[5]),.d6(d[6]),.d7(d[7]),.d12(d[12]),
 .s0(s[0]),.s1(s[1]),.s2(s[2]),.s3(s[3]),.s4(s[4]),.s5(s[5]),.s6(s[6]),.s7(s[7]),.s12(s[12]));
`else
 dsfd_stage_seq_static_c10 dut(
`ifdef OT_S81_ISSUER_SPLIT_PW
 .ck_pw(actual_ck_pw),
`endif
 .ck(actual_ck),.rst(rn),.ckv(actual_ckv),.rsv(rn),.f_ks(ks),.t_kd(kd),.f_pw(pw),.f_plen(plen),.t_st(st),
 .f_pq_pw(pqw),.t_pq_desc_pw(pq_desc),.calendar_prime(cal_prime),.stage_start(cal_start),.calendar_base(cal_base),
 .calendar_length(cal_len),.pq_image_sealed(1'b1),.pq_calendar_primed(primed),.pq_calendar_fault(1'b0),
 .c0(c[0]),.c1(c[1]),.c2(c[2]),.c3(c[3]),.c4(c[4]),.c5(c[5]),.c6(c[6]),.c7(c[7]),.c10(c[10]),.c12(c[12]),.c13(c[13]),
 .d0(d[0]),.d1(d[1]),.d2(d[2]),.d3(d[3]),.d4(d[4]),.d5(d[5]),.d6(d[6]),.d7(d[7]),.d10(d[10]),.d12(d[12]),.d13(d[13]),
 .s0(s[0]),.s1(s[1]),.s2(s[2]),.s3(s[3]),.s4(s[4]),.s5(s[5]),.s6(s[6]),.s7(s[7]),.s10(s[10]),.s12(s[12]),.s13(s[13]));
`endif
 reg[34:0]image[0:13];reg[125:0]due[0:399];
 integer serial=-1,fast=-1,i,e,op,slot,origin,commands=0,kits=0,mode=0,e0=0,e1=12;
 initial begin
  if(!$value$plusargs("mode=%d",mode))mode=0;
  if(!$value$plusargs("e0=%d",e0))e0=0;
  if(!$value$plusargs("e1=%d",e1))e1=12;
  $readmemh("status.hex",image);
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
  if(serial==199)ks={1'b1,10'(serial==199?37:38),21'(serial==199?21946:128799),21'd1048575};

 end
 always @(posedge cvk)begin
  serial=serial+1;#0.1;
  if(st[5]&&fault_serial<0)begin fault_serial=serial;
   if(mode==0||serial!=PORT_FAULT_EDGE)$fatal(1,"status fault edge %0d expected %0d",serial,PORT_FAULT_EDGE);
  end
  if(kd[53])begin
   if(serial!=211||kd[52:32]!=21946||kd[31:0]!=0)$fatal(1,"KIT raw fixed edge changed");
   kits=kits+1;
  end
  if(serial==220)begin
   if(commands!=2||kits!=1||end_fast!=278)$fatal(1,"minimum END/KIT/command schedule changed");
   if(mode==1&&(fault_fast!=279||fault_serial!=PORT_FAULT_EDGE||success||!rejected))$fatal(1,"fault escaped fixed consumer edge");
   if(mode==0&&(!success||rejected||st[5]))$fatal(1,"valid fixed consumer completion lost");
   $display("PINREG_BOUNDARY mode%0d PASS ENDfast%0d faultfast%0d faultserial%0d KITserial211 consumeredge%0d success%0d reject%0d",mode,end_fast,fault_fast,fault_serial,ACCEPT_EDGE,success,rejected);$finish;
  end
 end
 always @(negedge ck)if(fast<399)for(e=0;e<14;e=e+1)d[e]=due[fast+1][9*e+:9];
 always @(posedge ck)begin
  fast=fast+1;#0.1;
  if(dut.u_ot_pr_core.u_s.u_issue.job_done)begin end_fast=fast;if(fast!=278)$fatal(1,"minimum END edge moved");end
  if(dut.u_ot_pr_core.u_s.u_issue.fault&&fault_fast<0)fault_fast=fast;
  for(e=0;e<14;e=e+1)if(c[e][84])begin
   op=c[e][6:0];slot=c[e][83];origin=272+4*slot;
   if((op==0&&e!=e0)||(op==1&&e!=e1)||op>1||fast!=origin+op||c[e][82:73]!=(slot?38:37)||c[e][72:52]!=1048575||c[e][51:31]!=(slot?128799:21946)||c[e][30:7]!=(op?24'hfa0312:24'h102938))begin
    $display("wrapper bad fast=%0d expected=%0d e=%0d payload=%h",fast,origin+op,e,c[e]);$fatal(1,"wrapper pin cycle/context mismatch");
   end
   commands=commands+1;if(!(mode==1&&e==e1))due[fast+3][9*e+:9]={1'b1,1'(slot),7'(op)};
  end
 end
 // Registered external consumer model: one fixed compiler-assigned edge,
 // never wait for status/ready. KIT alone is a token event, not success.
 always @(posedge cvk)begin
  consumer_serial=consumer_serial+1;
  if(rn)begin
  if(kd[53])kit_seen<=1;
`ifdef S81_STATUS_EARLY_MUTANT
  if(kd[53])begin success<=!st[5];rejected<=st[5];end
`else
  if(consumer_serial==ACCEPT_EDGE)begin
   if(!(kit_seen||kd[53]))$fatal(1,"fixed consumer edge lacks KIT token");
   success<=!st[5]&&!st[0];rejected<=st[5];
  end
`endif
 end
 end
 // Clock and asynchronous reset are not data pins. The actual generated
 // wrapper must preserve every serial edge and reset level, including the
 // original declared two-edge local reset release synchronizers.
 integer external_serial_edges=0,core_serial_edges=0;
 always @(posedge cvk)external_serial_edges=external_serial_edges+1;
 always @(posedge dut.u_ot_pr_core.ckv)core_serial_edges=core_serial_edges+1;
 always @(cvk or rn or dut.u_ot_pr_core.ckv or dut.u_ot_pr_core.rsv)begin
  #0.01;
  if(dut.u_ot_pr_core.ckv!==cvk||dut.u_ot_pr_core.rsv!==rn)$fatal(1,"serial clock/reset was data registered");
 end
 always @(posedge ck)begin
  #0.2;
  if(fast==5&&dut.u_ot_pr_core.u_s.rr!==2'b01)$fatal(1,"first core reset release edge changed");
  if(fast==6&&dut.u_ot_pr_core.u_s.rr!==2'b11)$fatal(1,"second core reset release edge changed");
 end
 always @(posedge cvk)begin
  #0.2;
  if(serial==4&&dut.u_ot_pr_core.u_s.rv!==2'b01)$fatal(1,"first serial reset release edge changed");
  if(serial==5&&dut.u_ot_pr_core.u_s.rv!==2'b11)$fatal(1,"second serial reset release edge changed");
  if(serial==219&&external_serial_edges!=core_serial_edges)$fatal(1,"serial clock edge count changed");
 end
 initial begin #2500;$fatal(1,"wrapper timeout");end
endmodule
