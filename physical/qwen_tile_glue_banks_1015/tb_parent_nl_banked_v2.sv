// NL banked (53 CLOSED banks, 13 children) vs the independent staged qfd_tile_nl reference: full 514-bit t_out word
// every cycle. ALLB=1: instruction wbase spans all 5 rpair ROM banks + 16-edge boot (as tb_parent_banked_allbanks).
// FAULT=1: every third instruction has split 5 < SMIN 7 -> the tile split fault must reach t_out[513] at the
// reference's age (NK's tb never raises a tile fault).
`timescale 1ns/1ps
module tb_parent_nl_banked_v2;
 parameter integer MUT=0, ALLB=0, FAULT=0;
 reg ck=0,rst_n=0;always #5 ck=~ck;
 reg [507:0] tap=0;
 wire [513:0] ct,rt;
 qfd_tile_nl_banked_v2 #(.ROM_TILE(0),.MUT(MUT)) dut(.ck(ck),.ck_bank({53{ck}}),.ck_reset({11{ck}}),.ck_child({13{ck}}),.rst_n(rst_n),.tile_id(16'b0),.tap(tap),.t_out(ct),.tie_hi(),.tie_lo());
 qfd_tile_nl_staged_reference #(.ROM_TILE(0)) ref_parent(.ck(ck),.ck_rp0(ck),.ck_rp1(ck),.ck_rp2(ck),.ck_rp3(ck),.ck_rp4(ck),.ck_lsl0(ck),.ck_lsl1(ck),.ck_lsl2(ck),.ck_lsl3(ck),.ck_lsl4(ck),.ck_lsl5(ck),.ck_lsl6(ck),.ck_lsl7(ck),.rst_n(rst_n),.tile_id(16'b0),.tap(tap),.t_out(rt),.tie_hi(),.tie_lo());
 reg [378:0] ib=0;
 reg [17:0] nout,tiles,k;
 reg [3:0] split;
 reg round;
 integer c,j,checks=0,outputs=0,nonzero=0,faults=0,start,ncyc;
 integer reads[0:4];
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[0].g_hd.u_rp.ce_d)reads[0]=reads[0]+1;
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[1].g_hd.u_rp.ce_d)reads[1]=reads[1]+1;
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[2].g_hd.u_rp.ce_d)reads[2]=reads[2]+1;
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[3].g_hd.u_rp.ce_d)reads[3]=reads[3]+1;
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[4].g_hd.u_rp.ce_d)reads[4]=reads[4]+1;
 task instruction(input integer num);
 begin
  nout=256+(num%3)*16;tiles=1+(num%2);k=1+(num%4);split=(FAULT && num%3==2) ? 4'd5 : 4'(7+(num%4));round=num%2;
  ib={nout,tiles,k,1'b0,24'((ALLB ? (num%5)*4096 : 0)+num*17),24'd7,24'd3,24'd1,24'd0,24'd1,24'd1,24'd1,3'd0,split,24'd0,round,24'd0,24'd1,24'd1,1'b0,1'b0,1'b0,1'b0,24'd0};
 end endtask
 always @(negedge ck)if(rst_n && c>(ALLB ? 40 : 100))begin
  if(ct[513:512]!==rt[513:512])$fatal(1,"FAIL parent valid/fault age c%0d ct%h rt%h",c,ct[513:512],rt[513:512]);
  if(ct!==rt)$fatal(1,"FAIL parent tile complete word c%0d got%h want%h",c,ct,rt);
  checks=checks+1;if(ct[512])begin outputs=outputs+1;if(|ct[511:0])nonzero=nonzero+1;end
  if(ct[513])faults=faults+1;
 end
 initial begin
  for(j=0;j<5;j=j+1)reads[j]=0;
  start=ALLB ? 16 : 20; ncyc=ALLB ? 6000 : 3600;
  repeat(start)@(negedge ck);rst_n=1;
  for(c=0;c<ncyc;c=c+1)begin
   @(posedge ck);#1;
   tap[0]=0;
   if(c%400==(ALLB ? 16 : 80))begin instruction(c/400);tap[379:1]=ib;tap[0]=1;end
   for(j=0;j<4;j=j+1)tap[380+32*j+:32]={1'(c+j),8'(124+j),23'((c*11237+j*3319)^32'h007fffff)};
  end
  if(checks<3400||outputs<20||nonzero<20)$fatal(1,"FAIL parent coverage checks%0d output%0d nonzero%0d",checks,outputs,nonzero);
  if(FAULT && faults<10)$fatal(1,"FAIL fault coverage faults%0d",faults);
  if(ALLB)begin for(j=0;j<5;j=j+1)if(reads[j]<8)$fatal(1,"FAIL bank coverage bank%0d reads%0d",j,reads[j]);
   $display("ACTUAL_BANK_READS %0d %0d %0d %0d %0d",reads[0],reads[1],reads[2],reads[3],reads[4]);end
  $display("PASS actual full old-NL staged-reference v2-vs53bank TX198 ALLB%0d FAULT%0d checks%0d output%0d nonzero%0d faults%0d",ALLB,FAULT,checks,outputs,nonzero,faults);$finish;
 end
endmodule
