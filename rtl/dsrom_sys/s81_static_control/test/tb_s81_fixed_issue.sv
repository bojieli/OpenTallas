`timescale 1ns/1ps
module tb_s81_fixed_issue;
`ifndef ISSUER_MUT
`define ISSUER_MUT 0
`endif
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,pw_v=0,job_v=0;reg[6:0]pw_a=0;reg[27:0]pw_d=0;
`ifdef OT_S81_ISSUE_SCANPIPE
 localparam integer SCAN_EDGES=130;
`else
 localparam integer SCAN_EDGES=128;
`endif
 reg[7:0]plen=128;reg[9:0]user=0;reg[20:0]pos=0,tok=0;
 wire jr,busy,done,kdone,slot,fault;wire[20:0]ktok;wire[3:0]code;wire[1:0]phase;
 wire[12:0]cv;wire[1091:0]cd;reg[12:0]av=13'h1fff,dv=0;reg[103:0]dt=0;
 wire[31:0]nj,nc;
 ot_s81_fixed_issue #(.STAGE(7),.MUT(`ISSUER_MUT))dut(.clk(clk),.rst_n(rst_n),.pw_v(pw_v),.pw_a(pw_a),.pw_d(pw_d),.prog_len(plen),
 .job_v(job_v),.job_user(user),.job_pos(pos),.job_tok(tok),.job_rdy(jr),.busy(busy),.job_done(done),.job_kdone(kdone),.done_slot(slot),.kit_tok(ktok),
 .cmd_v(cv),.cmd_d(cd),.engine_available(av),.dn_v(dv),.dn_tag(dt),.fault(fault),.fault_code(code),.st_jobs(nj),.st_cmds(nc),.phase(phase));
 reg[34:0]pwmem[0:385];reg[12:0]due[0:1599];reg[103:0]tags[0:1599];
 integer tick=-1,mode=0,commands=0,ends=0,kits=0,i,e,op,s,expected,second,seal_tick=-1;
 reg[23:0]arg;reg[83:0]cmd;
 function[23:0]arg_for(input integer k);arg_for=24'h010203+24'(k)*24'h001523;endfunction
 initial begin
  if(!$value$plusargs("mode=%d",mode))mode=0;
  $readmemh("program.hex",pwmem);
  for(i=0;i<1600;i=i+1)begin due[i]=0;tags[i]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(i=0;i<386;i=i+1)begin
   @(negedge clk);pw_v=!(mode==4&&i==130);pw_a=pwmem[i][34:28];pw_d=pwmem[i][27:0];
   @(negedge clk);pw_v=0;
  end
 end
 always @(negedge clk)if(rst_n)begin
  dv=mode==7?0:due[tick+1];dt=tags[tick+1];if(mode==6)dt=dt^104'h01010101010101010101010101;
  job_v=0;
  if(tick==999||tick==(mode==3?1004:1003)||(mode==8&&tick==1007)||(mode==9&&tick==799))begin
   job_v=1;user=tick==999?37:38;pos=1048575;tok=tick==999?21946:128999;
  end
  if(mode==1)av=13'h1ffd;
  if(mode==5&&tick==1010)begin pw_v=1;pw_a=0;pw_d=28'd0;end
  if(mode==5&&tick==1011)pw_v=0;
 end
 always @(posedge clk)begin
  if(!rst_n)tick=-1;
  else begin
   tick=tick+1;#1;
   if(pw_v&&pw_d[27:26]==3&&pw_d[25])seal_tick=tick;
   if(seal_tick>=0&&tick==seal_tick+SCAN_EDGES-1&&dut.sealed)$fatal(1,"boot scan armed early");
   if(seal_tick>=0&&tick==seal_tick+SCAN_EDGES&&dut.sealed!==(mode!=4))$fatal(1,"boot scan fixed arm edge lost");
   for(e=0;e<13;e=e+1)if(cv[e])begin
    cmd=cd[84*e+:84];s=cmd[83];op=cmd[6:0];arg=arg_for(op);expected=1001+4*s+op;
    if(op>=126||e!=op%13||tick!=expected||cmd[30:7]!=arg||cmd[82:73]!=(s?38:37)||cmd[72:52]!=1048575||cmd[51:31]!=(s?128999:21946))begin
     $display("BAD command tick=%0d expected=%0d e=%0d op=%0d s=%0d cmd=%h",tick,expected,e,op,s,cmd);$fatal(1,"native ABI/calendar mismatch");
    end
    commands=commands+1;
    due[tick+(mode==2?4:3)][e]=1;tags[tick+(mode==2?4:3)][8*e+:8]={1'(s),7'(op)};
   end
   if(done)begin
    if(tick!=(slot?1135:1131))$fatal(1,"END moved");ends=ends+1;
   end
   if(kdone)begin
    if(tick!=1130&&tick!=1134)$fatal(1,"KIT moved");
    if(ktok!=(tick==1130?21946:128999))$fatal(1,"KIT context corrupted");kits=kits+1;
   end
   if(tick==1300)begin
    second=(mode==3||mode==4)?0:1;
    if(mode==4)begin if(commands!=0||ends!=0||!fault)$fatal(1,"incomplete PW dispatched");end
    else begin
     if(commands!=126*(1+second)||ends!=1+second||kits!=1+second)$fatal(1,"missing actual command/KIT/END events");
     if((mode==0&&fault)||(mode!=0&&!fault))$fatal(1,"fault expectation failed code=%0d mode=%0d",code,mode);
    end
    $display("S81_FIXED mode=%0d commands=%0d jobs=%0d KIT=%0d END=%0d fault=%0d code=%0d",mode,commands,nj,kits,ends,fault,code);$finish;
   end
  end
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
