`timescale 1ns/1ps
// qfd_sp_res_ser (TP8 slot cell, the assembled cluster: 8 slot tiles + head + pin / relay stages) through its DIE PORTS.
// Stimulus and scoreboard of rtl/test/res_tiles/tb_res_tiles.sv (the closed tile's bench): 360 bursts with every we
// pattern class, the 42-edge engine stopping debt after rok falls, held-valid-while-disabled, credit stalls; every beat
// {end, nul, row, mask, data} exact against the queue, the conveyor latency exact (19), no fault.
// Coverage floors: the bench REFUSES to pass (FAIL coverage) unless the run reached them (BURSTS = 40 is the
// refusal control: every beat exact, but the store never fills and rok never falls).
module tb_sp_res_ser #(parameter integer MUT=0, USE_MACRO=1, PROFILE=0, BURSTS=360);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,me_en=0,i_ov=0;reg [7:0] i_we=0;reg [191:0] i_addr=0;reg [127:0] i_mask=0;reg [4095:0] i_data=0;
 wire [4424:0] i_bus={i_data,i_mask,i_addr,i_we,i_ov};
 wire [550:0] o_bus;wire rok,fault;reg cr=0;
 wire ov=o_bus[550],oe=o_bus[549],onul=o_bus[548];wire [19:0] row=o_bus[547:528];wire [15:0] mask=o_bus[527:512];
 wire [511:0] data=o_bus[511:0];
 qfd_sp_res_ser #(.MUT(MUT),.USE_MACRO(USE_MACRO)) dut(.ck(clk),.rst_n(rst_n),.me_en(me_en),.i(i_bus),.o(o_bus),
  .ok(rok),.cr(cr),.fault(fault));
 reg [550:0] expq[0:40000];integer ew=0,er=0,pending=0,burst=0,c=0,k,j,last,stopdebt=0;
 integer rq_cycle[0:40000];integer qw=0,qr=0,peak_n=0,first_accept=-1,first_output=-1,last_output=-1;
 // coverage
 integer cov_slot[0:7];integer cov_nul=0,cov_all8=0,cov_rokfall=0,cov_held=0,cov_crstall=0,cov_debt=0,cov_end=0;
 reg rok_d=0;integer covfail=0;
 reg [7:0] wen;integer x;reg [511:0] word;
 task tick;
 begin
 @(negedge clk);
 if(me_en&&i_ov&&first_accept<0) first_accept=c;
 if(dut.u_ctl.n>peak_n) peak_n=dut.u_ctl.n;
 if(dut.u_ctl.rq_v) begin rq_cycle[qw]=c;qw=qw+1;end
 if(dut.u_ctl.rv) begin
  if(qr==qw || c-rq_cycle[qr]!=19) $fatal(1,"CONVEYOR latency=%0d",c-rq_cycle[qr]);
  qr=qr+1;
 end
 if(fault) $fatal(1,"FAULT cycle=%0d n=%0d cr=%0d",c,dut.u_ctl.n,dut.u_ctl.cr);
 if(rok_d&&!rok) cov_rokfall=cov_rokfall+1;
 rok_d=rok;
 if(ov) begin
  if(first_output<0) first_output=c;last_output=c;
  if(er==ew) $fatal(1,"unexpected beat");
  if({1'b1,oe,onul,row,mask,(onul?512'd0:data)}!==expq[er])
   $fatal(1,"MISMATCH beat=%0d cycle=%0d got row=%0d end=%0d nul=%0d want row=%0d end=%0d nul=%0d",er,c,row,oe,onul,expq[er][547:528],expq[er][549],expq[er][548]);
  if(onul) cov_nul=cov_nul+1;else cov_slot[row[2:0]]=cov_slot[row[2:0]]+1;
  if(oe) cov_end=cov_end+1;
  er=er+1;pending=pending+1;
 end
 if(pending>0 && !(PROFILE!=0 || c%251>95)) cov_crstall=cov_crstall+1;
 cr=0;if(pending>0 && (PROFILE!=0 || c%251>95)) begin cr=1;pending=pending-1;end
 c=c+1;
 end endtask
 initial begin
 for(k=0;k<8;k=k+1) cov_slot[k]=0;
 repeat(5) @(negedge clk);rst_n=1;
 for(x=0;x<12000;x=x+1) begin
  tick();
  // A falling ready permits a realistic 42-edge engine stopping debt.
  if(rok) stopdebt=42;else if(stopdebt>0) stopdebt=stopdebt-1;
  me_en=(rok||stopdebt>0)&&x%7!=0;
  i_ov=me_en && (x<2000 || x%11==0) && burst<BURSTS;
  if(i_ov && !rok) cov_debt=cov_debt+1;
  if(i_ov) begin
   wen=8'((burst*53)^ (burst>>2));if(burst%13==0) wen=0;if(burst%17==0) wen=255;
   if(PROFILE==1) wen=255;else if(PROFILE==2) wen=0;
   if(wen==8'hff) cov_all8=cov_all8+1;
   i_we=wen;last=-1;for(k=0;k<8;k=k+1) if(wen[k]) last=k;
   for(k=0;k<8;k=k+1) begin
    i_addr[k*24+:24]=burst*8+k;i_mask[k*16+:16]=16'((burst*31+k)^16'hac95);
    for(j=0;j<16;j=j+1) word[j*32+:32]=32'((burst*131+k*17+j)^32'hd3915827);
    i_data[k*512+:512]=word;
    if(wen[k]) begin expq[ew]={1'b1,1'(k==last),1'b0,20'(burst*8+k),i_mask[k*16+:16],word};ew=ew+1;end
   end
   if(wen==0) begin expq[ew]={1'b1,1'b1,1'b1,20'(burst*8+7),16'd0,512'd0};ew=ew+1;end
   burst=burst+1;
  end
  // Held valid while clock-disabled must never be captured a second time.
  if(x%7==0) begin me_en=0;i_ov=1;cov_held=cov_held+1;end
 end
 me_en=0;i_ov=0;
 while(er<ew && c<30000) tick();
 if(er!=ew||burst!=BURSTS||qw!=qr) $fatal(1,"DRAIN er=%0d ew=%0d bursts=%0d",er,ew,burst);
 // coverage refusal (PROFILE 0 only: the directed profiles are single-class by construction)
 covfail=0;
 if(PROFILE==0) begin
  for(k=0;k<8;k=k+1) if(cov_slot[k]<100) covfail=1;
  if(cov_nul<20||cov_all8<15||cov_end!=BURSTS||cov_rokfall<1||cov_debt<20||peak_n<50||cov_held<1000||cov_crstall<500||er<1400) covfail=1;
 end
 if(covfail) $display("FAIL res_ser coverage nul=%0d all8=%0d end=%0d rokfall=%0d debt_bursts=%0d peak=%0d held=%0d crstall=%0d beats=%0d slot_beats=%0d/%0d/%0d/%0d/%0d/%0d/%0d/%0d (floors: slot >= 100, nul >= 20, all8 >= 15, rokfall >= 1, debt >= 20, peak >= 50, held >= 1000, crstall >= 500, beats >= 1400)",
   cov_nul,cov_all8,cov_end,cov_rokfall,cov_debt,peak_n,cov_held,cov_crstall,er,
   cov_slot[0],cov_slot[1],cov_slot[2],cov_slot[3],cov_slot[4],cov_slot[5],cov_slot[6],cov_slot[7]);
 else
 $display("PASS res_ser bursts=%0d beats=%0d cycles=%0d request_to_chain=19 peak_bursts=%0d first_accept_to_output=%0d profile=%0d first_output=%0d last_output=%0d nul=%0d all8=%0d rokfall=%0d debt_bursts=%0d crstall=%0d slot_beats=%0d/%0d/%0d/%0d/%0d/%0d/%0d/%0d",
  burst,er,c,peak_n,first_output-first_accept,PROFILE,first_output,last_output,cov_nul,cov_all8,cov_rokfall,cov_debt,cov_crstall,
  cov_slot[0],cov_slot[1],cov_slot[2],cov_slot[3],cov_slot[4],cov_slot[5],cov_slot[6],cov_slot[7]);$finish;
 end
endmodule
