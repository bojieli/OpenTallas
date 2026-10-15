`timescale 1ns/1ps
module tb_hbm_host_static_ingress;
 parameter MUT=0, READY_MUT=0, ROWS=1024, LOOPS=2;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,av=0,wv=0,br=1,arv=0,rr=1;
 reg [11:0] aa=0,ra=0;reg [31:0]wd=0;reg[3:0]ws=15;
 wire awr,wr,bv,arr,rv;wire[1:0]bres;wire[31:0]rd;
 wire cv,dv,lv,hf;wire[7:0]target;wire[11:0]addr,base;wire[12:0]limit;wire[15:0]loops;wire[255:0]data;
 wire twe,ts,configured,tf,ready_validated,ready_fault;wire[9:0]ta,tbase;wire[10:0]tlim;wire[15:0]tloops;wire[255:0]td;
 wire[15:0]calendar;wire calendar_v,active,done,pf;wire[31:0]ordinal;
 integer seen=0,launches=0,cy=0,lastcy=-1;reg measure=0;reg[31:0] expect_resp=0;
 ot_hbm_host_static_ingress #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),
 .s_awvalid(av),.s_awready(awr),.s_awaddr(aa),.s_wvalid(wv),.s_wready(wr),.s_wdata(wd),.s_wstrb(ws),
 .s_bvalid(bv),.s_bready(br),.s_bresp(bres),.s_arvalid(arv),.s_arready(arr),.s_araddr(ra),
 .s_rvalid(rv),.s_rready(rr),.s_rdata(rd),.block_ready(ready_validated),.program_active(active),.program_fault(tf|pf|ready_fault),
 .cfg_v(cv),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),.desc_v(dv),.desc_base(base),.desc_limit(limit),.desc_loops(loops),.launch_v(lv),.fault(hf));
 ot_static_program_target #(.TARGET(48),.PCW(10)) target_dut(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),
 .desc_v(dv),.desc_base(base),.desc_limit(limit),.desc_loops(loops),.launch_v(lv),.program_active(active),
 .program_cfg_we(twe),.program_cfg_addr(ta),.program_cfg_data(td),.program_start_v(ts),.program_start_base(tbase),.program_start_limit(tlim),.program_start_loops(tloops),.configured(configured),.fault(tf));
 ot_hbm_program_block_ready #(.TARGET(48),.PCW(10),.MUT(READY_MUT)) readiness(.clk(clk),.rst_n(rst_n),.cfg_we(twe),.cfg_addr(ta),
 .desc_v(dv),.desc_target(target),.desc_base(base),.desc_limit(limit),.desc_loops(loops),.program_active(active),.launch_v(lv),.block_ready(ready_validated),.fault(ready_fault));
 ot_vms_calendar_static #(.W(16)) programme(.clk(clk),.rst_n(rst_n),.cfg_we(twe),.cfg_addr(ta),.cfg_data(td),.start_v(ts),.start_base(tbase),.start_limit(tlim),.start_loops(tloops),
 .calendar(calendar),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(pf));
 always @(negedge clk)begin
  cy=cy+1;
  if(lv)launches=launches+1;
  if(measure&&calendar_v)begin
   if(calendar!==16'(16'h9000+(seen%ROWS)) || ordinal!==seen)$fatal(1,"HOST_STATIC data/ordinal mismatch n=%0d got=%h ord=%d",seen,calendar,ordinal);
   if(lastcy>=0&&cy!=lastcy+1)$fatal(1,"HOST_STATIC runtime calendar gap");
   lastcy=cy;seen=seen+1;
  end
 end
 task reset_dut;begin
  @(negedge clk);rst_n=0;av=0;wv=0;arv=0;ws=15;measure=0;
  repeat(4)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
 end endtask
 // Independent address/data ordering exercises the actual external boundary.
 task write32(input[11:0] a,input[31:0] d,input integer order,input integer bad);
 begin
  @(negedge clk);aa=a;wd=d;
  if(order==0)begin
   av=1;do @(posedge clk);while(!awr);@(negedge clk);av=0;
   repeat(3)@(negedge clk);wv=1;do @(posedge clk);while(!wr);@(negedge clk);wv=0;
  end else if(order==1)begin
   wv=1;do @(posedge clk);while(!wr);@(negedge clk);wv=0;
   repeat(2)@(negedge clk);av=1;do @(posedge clk);while(!awr);@(negedge clk);av=0;
  end else begin
   fork
    begin av=1;do @(posedge clk);while(!awr);@(negedge clk);av=0;end
    begin wv=1;do @(posedge clk);while(!wr);@(negedge clk);wv=0;end
   join
  end
  while(!bv)@(negedge clk);
  if(bres!==(bad?2'b10:2'b00))$fatal(1,"HOST_STATIC wrong AXI response %h a=%h",bres,a);
  @(negedge clk);
 end endtask
 reg[255:0]word;
 initial begin
  reset_dut();
  // Unconfigured launch must never emit even transiently. MUT2 fails here.
  write32(12'hf30,1,0,1);repeat(6)@(negedge clk);
  if(!hf||launches!=0)$fatal(1,"HOST_STATIC premature launch escaped");
  reset_dut();
  write32(12'hf20,48,0,0);
  for(integer row=0;row<ROWS;row=row+1)begin
   word=0;word[255:240]=16'hc7a1;word[233:224]=10'(row);word[15:0]=16'(16'h9000+row);
   for(integer k=0;k<8;k=k+1)write32(12'hf24,word[k*32+:32],k%3,0);
  end
  write32(12'hf28,ROWS<<12,1,0);write32(12'hf2c,LOOPS,0,0);
  repeat(ROWS+8)@(negedge clk);
  if(!configured||!ready_validated||hf||tf||pf||ready_fault)$fatal(1,"HOST_STATIC genuine target not configured");
  measure=1;write32(12'hf30,1,1,0);
  wait(done);repeat(3)@(negedge clk);
  if(seen!=ROWS*LOOPS||launches!=1||hf||tf||pf||ready_fault)$fatal(1,"HOST_STATIC composition failed seen=%0d",seen);
  // A host service response can wait without changing or replaying a write.
  br=0;write32(12'hf28,ROWS<<12,2,0);
  repeat(4)begin @(negedge clk);if(!bv||bres!=0)$fatal(1,"HOST_STATIC unstable held response");end
  // New AW/W are already asserted on the edge accepting the old B response.
  // Registered ready must retain them until each channel actually handshakes.
  aa=12'hf28;wd=ROWS<<12;br=1;
  fork
   begin av=1;do @(posedge clk);while(!awr);@(negedge clk);av=0;end
   begin wv=1;do @(posedge clk);while(!wr);@(negedge clk);wv=0;end
  join
  while(!bv)@(negedge clk);
  if(bres!=0)$fatal(1,"HOST_STATIC response-turnover request dropped");
  @(negedge clk);
  // Partial assembly and bad strobe are refused independently of target ready.
  measure=0;
  write32(12'hf24,32'h12345678,2,0);write32(12'hf30,1,2,1);
  if(!hf||launches!=1)$fatal(1,"HOST_STATIC partial-frame launch escaped");
  reset_dut();ws=3;write32(12'hf20,48,2,1);
  if(!hf)$fatal(1,"HOST_STATIC bad strobe escaped");
  reset_dut();write32(12'hf20,49,2,1);if(!hf)$fatal(1,"HOST_STATIC unbound target escaped");
  reset_dut();write32(12'hf24,1,2,1);if(!hf)$fatal(1,"HOST_STATIC unselected frame escaped");
  reset_dut();write32(12'hf20,48,2,0);write32(12'hf28,0,2,1);if(!hf)$fatal(1,"HOST_STATIC empty range escaped");
  reset_dut();write32(12'hf20,48,2,0);write32(12'hf28,2<<12,2,0);write32(12'hf2c,1,2,0);
  repeat(10)@(negedge clk);if(ready_validated||!ready_fault)$fatal(1,"HOST_STATIC unloaded range falsely ready");
  $display("HBM_HOST_STATIC_PASS real_macro=1024x256 target=48 gapless=1 AXI_orderings=3 held_response=1 response_turnover=1 negatives=7 rows=%0d loops=%0d exact_calendar_beats=%0d",ROWS,LOOPS,seen);$finish;
 end
 initial begin #2000000;$fatal(1,"HOST_STATIC watchdog");end
endmodule
