`timescale 1ns/1ps
// Single full controller, no array simulation. Software map and byte merge are independent of DUT.
module tb_hbm_accel_dskv_wb_sram;
  parameter integer MUT_MERGE=0;
  reg clk=0,rst_n=0;
  always #.4165 clk=~clk;
  reg [6:0] die=31;
  reg [19:0] pos=1048575;
  reg row_v=0,row_r2=0,sh_v=0,wq_r=0;
  reg [1:0] row_kind=0;
  reg [5:0] row_slot=0;
  reg [2:0] sh_slot=0;
  reg [4351:0] row_data=0,sh_data=0;
  reg [5:0] ack_n=0;
  wire row_r,sh_r,fault,wq_v,fence_ok;
  wire [1:0] wq_stk;
  wire [4:0] wq_pc,wq_bank,wq_col;
  wire [18:0] wq_row;
  wire [255:0] wq_data;
  wire [15:0] issued,acked;
  ot_hbm_accel_dskv_wb_sram #(.ENABLE(1),.ALL_STACKS(1),.MUT_MERGE(MUT_MERGE)) dut(.*);
  typedef struct packed {bit[1:0] stk; bit[4:0] pc,bank; bit[18:0] rw; bit[4:0] col; bit[255:0] data;} sector_t;
  sector_t expected[$], got, want, held;
  bit held_v=0;
  reg [4351:0] golden[0:7];
  integer bad=0,posts=0,cycles=0,stall_cycles=0,key2=0,key3=0;
  integer row_start, max_row_cycles=0,preload_start,max_preload_cycles=0;
  task automatic fail(input string why);
    bad++; $display("WB_SRAM_ERROR %s cycle=%0d",why,cycles);
  endtask
  function automatic [4351:0] pattern(input integer seed);
    for(int b=0;b<544;b++) pattern[b*8+:8]=8'((b*29) ^ (b>>3) ^ (seed*41));
  endfunction
  task automatic append(input integer kind,slot,S,j,input bit[255:0]data);
    sector_t x;
    x.stk=2'((S>>5)&3); x.pc=5'(S&31);
    x.bank=5'((((j>>7)&7)<<2)|(j&3)); x.col=5'((j>>2)&31);
    x.rw=19'((kind==0?2000:kind==1?3000:4000)+slot*2+(j>>10)); x.data=data;
    expected.push_back(x);
  endtask
  always @(posedge clk) if(rst_n) begin
    cycles++;
    got.stk=wq_stk; got.pc=wq_pc; got.bank=wq_bank; got.rw=wq_row; got.col=wq_col; got.data=wq_data;
    if(held_v && (!wq_v || got!==held)) fail("posted write changed under stall");
    held_v=wq_v&&!wq_r; held=got;
    if(held_v) stall_cycles++;
    ack_n<=0;
    if(wq_v && wq_r) begin
      posts++;
      if(expected.size()==0) fail("unexpected write");
      else begin
        want=expected.pop_front();
        if(got!==want) fail("posted address/data mismatch");
      end
      ack_n<=1;
    end
    if(fault) fail("unexpected controller fault");
    if(fence_ok && issued!=acked) fail("premature fence");
  end
  always @(negedge clk) if(rst_n) wq_r=(cycles%7)>=3;
  task automatic finish_row;
    integer elapsed;
    elapsed=0;
    while(!fence_ok) begin
      @(negedge clk); elapsed++;
      if(elapsed>512) $fatal(1,"finite controller row failed to complete");
    end
    if(expected.size()!=0) fail("missing write at fence");
    if(cycles-row_start>max_row_cycles) max_row_cycles=cycles-row_start;
  endtask
  task automatic send_row(input integer kind,slot,position,input bit[4351:0]data);
    @(negedge clk);
    while(!row_r) @(negedge clk);
    row_start=cycles; row_kind=2'(kind); row_slot=6'(slot);pos=20'(position);row_data=data;row_v=1;
    @(posedge clk);
    @(negedge clk);row_v=0;
    finish_row();
  endtask
  initial begin
    reg [4351:0] value;
    integer k,first,last,S,j;
    repeat(4) @(negedge clk);rst_n=1;
    // All eight real544B sectors are staged through the17write handshake.
    for(int slot=0;slot<8;slot++) begin
      golden[slot]=pattern(slot+1);
      @(negedge clk);while(!sh_r) @(negedge clk);
      preload_start=cycles;sh_v=1;sh_slot=3'(slot);sh_data=golden[slot];
      @(posedge clk);@(negedge clk);sh_v=0;
      while(!sh_r) @(negedge clk);
      if(cycles-preload_start>max_preload_cycles)max_preload_cycles=cycles-preload_start;
    end
    // Window row and complete compressed row preserve the same real address map.
    value=pattern(19);
    for(int t=0;t<17;t++) append(0,39,127,t,value[256*t+:256]);
    send_row(0,39,1048575,value);
    value=pattern(23); k=1365*8+7;
    for(int t=0;t<9;t++) begin S=k*9+t;j=S>>7;append(1,7,S,j,value[256*t+:256]);end
    send_row(1,7,1048575,value);
    //1M final owner block: all keys and slots, including2and3sector partial merges.
    for(int ki=0;ki<8;ki++) for(int slot=0;slot<8;slot++) begin
      value=pattern(100+ki*8+slot);
      for(int b=0;b<68;b++)golden[slot][8*(68*ki+b)+:8]=value[8*b+:8];
      first=(68*ki)/32;last=(68*ki+67)/32;
      if(last-first+1==2)key2++;else if(last-first+1==3)key3++;else fail("bad golden sector count");
      for(int t=first;t<=last;t++)begin
        S=1365*17+t;j=S>>7;append(2,slot,S,j,golden[slot][256*t+:256]);
      end
      send_row(2,slot,1048568+ki,value);
    end
    if(issued!=posts || acked!=posts)fail("posted/acknowledged count mismatch");
    $display("WB_SRAM_METRICS posts=%0d issued=%0d acked=%0d key2=%0d key3=%0d stall_cycles=%0d max_row_cycles=%0d max_preload_cycles=%0d bad=%0d mutant=%0d",posts,issued,acked,key2,key3,stall_cycles,max_row_cycles,max_preload_cycles,bad,MUT_MERGE);
    $display("WB_SRAM_VERDICT %s",bad==0 ? "PASS":"FAIL");
    if(bad)$fatal(1,"controller exactness failed");
    $finish;
  end
endmodule
