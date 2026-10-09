`timescale 1ns/1ps
// Minimum component gate: 8 slots x 17 sectors, real provider SRAM model.
// Macro memory path supplied by the DUT owner; no fallback behavioral storage.
`ifndef SHADOW_MEM0
`define SHADOW_MEM0 dut.on.bank0.arr
`endif
module tb_hbm_accel_dskv_shadow_sram;
  reg clk=0, rst_n=0;
  always #0.4165 clk=~clk;
  reg req_v=0, req_write=0, rsp_r=0;
  reg [2:0] req_slot=0;
  reg [4:0] req_sector=0;
  reg [255:0] req_data=0;
  wire req_r, rsp_v, rsp_poison, fault;
  wire [255:0] rsp_data;
  ot_hbm_accel_dskv_shadow_sram #(.ENABLE(1)) dut(.*);
  integer bad=0, transactions=0, stalls=0, reads=0, writes=0, mut=0;
  integer max_latency=0, full_reads=0;
  reg [255:0] golden[0:135];
  function automatic [255:0] pattern(input integer slot, sector, epoch);
    for (int word=0; word<8; word++)
      pattern[word*32+:32] = 32'h9e3779b9*(slot+1) ^ 32'h85ebca6b*(sector+1) ^
                            32'hc2b2ae35*(word+1) ^ 32'h27d4eb2f*(epoch+1);
  endfunction
  task automatic fail(input string reason);
    bad++;
    $display("SHADOW_ERROR %s transaction=%0d", reason, transactions);
  endtask
  // The cycle limits below prove the finite one-credit interface, not a build/job deadline.
  task automatic transact(input bit wr, input integer slot, sector,
                           input reg [255:0] data, input bit poisoned,
                           input reg [255:0] expected, input integer stall_cycles,
                           input bit check_data);
    integer elapsed;
    reg [255:0] held_data;
    reg held_poison;
    @(negedge clk);
    req_v=1; req_write=wr; req_slot=3'(slot); req_sector=5'(sector); req_data=data; rsp_r=0;
    elapsed=0;
    do begin
      @(posedge clk); elapsed++;
      if (elapsed>32) $fatal(1,"request admission did not progress");
    end while (!req_r);
    @(negedge clk); req_v=0;
    elapsed=0;
    while (!rsp_v) begin
      @(negedge clk); elapsed++;
      if (elapsed>32) $fatal(1,"response did not progress");
    end
    if (elapsed>max_latency) max_latency=elapsed;
    held_data=rsp_data; held_poison=rsp_poison;
    if (rsp_poison !== poisoned) fail("response poison mismatch");
    if (check_data && !poisoned && rsp_data !== expected) fail("response data mismatch");
    // Present a real second request while the sole response credit is occupied.
    req_v=1; req_write=0; req_slot=3'(slot); req_sector=5'(sector);
    repeat(stall_cycles) begin
      @(posedge clk);
      if (req_r !== 1'b0) fail("accepted second request while response stalled");
      @(negedge clk);
      if (rsp_v !== 1'b1 || rsp_data !== held_data || rsp_poison !== held_poison)
        fail("response changed under backpressure");
      stalls++;
    end
    req_v=0; rsp_r=1;
    @(posedge clk);
    @(negedge clk); rsp_r=0;
    if (rsp_v) fail("response repeated after consumption");
    transactions++;
    if (wr) writes++; else reads++;
  endtask
  task automatic reset_service;
    @(negedge clk); rst_n=0; req_v=0; rsp_r=0;
    repeat(3) @(negedge clk); rst_n=1;
    if (fault) fail("reset did not clear sticky fault");
  endtask
  task automatic check_failed;
    if (!fault) fail("poison did not set sticky fault");
    repeat(3) begin
      @(negedge clk);
      if (!fault || req_r) fail("failed service admitted a new request");
    end
  endtask
  initial begin
    void'($value$plusargs("mut=%d",mut));
    repeat(4) @(negedge clk); rst_n=1;
    // Every legal address must poison until first write, including the second macro.
    for(int slot=0;slot<8;slot++) for(int sector=0;sector<17;sector++)
      begin
        reset_service();
        transact(0,slot,sector,'0,1,'0,(slot+sector)%5,0);
        check_failed();
      end
    reset_service();
    for(int epoch=0;epoch<2;epoch++) begin
      for(int sector=0;sector<17;sector++) for(int slot=0;slot<8;slot++) begin
        golden[slot*17+sector]=pattern(slot,sector,epoch);
        transact(1,slot,sector,golden[slot*17+sector],0,golden[slot*17+sector],(slot+sector)%3,1);
      end
      // Reverse order catches aliasing and the 127/128 macro boundary.
      for(int slot=7;slot>=0;slot--) for(int sector=16;sector>=0;sector--) begin
        transact(0,slot,sector,'0,0,
          golden[slot*17+sector] ^ ((mut==1 && slot==7 && sector==16) ? 256'd1 : 256'd0),
          (slot+sector)%7,1);
        full_reads++;
      end
    end
    // SECDED correction is exercised on stored payload, never on a mocked response.
    `SHADOW_MEM0[0] = `SHADOW_MEM0[0] ^ 256'd1;
    transact(0,0,0,'0,0,golden[0],9,1);
    // Reset the word through the service before injecting a two-bit uncorrectable error.
    transact(1,0,0,golden[0],0,'0,2,0);
    `SHADOW_MEM0[0] = `SHADOW_MEM0[0] ^ 256'd3;
    transact(0,0,0,'0,(mut==2 ? 0 : 1),golden[0],11,1);
    check_failed();
    reset_service();
    transact(1,1,0,golden[17],0,golden[17],3,1);
    // Sector 17 is illegal; fail-stop rejection may not corrupt slot 1.
    transact(1,0,17,'1,1,'0,4,0);
    check_failed();
    if (`SHADOW_MEM0[17] !== golden[17]) fail("illegal write aliased slot 1");
    reset_service();
    transact(0,0,17,'0,1,'0,4,0);
    check_failed();
    reset_service();
    transact(1,0,0,golden[0],0,golden[0],3,1);
    dut.on.valid_n[0]=1; // metadata dualrail corruption must fail closed
    transact(0,0,0,'0,1,'0,4,0);
    check_failed();
    reset_service();
    transact(1,7,16,golden[135],0,golden[135],2,1);
    dut.on.bank1.arr[7] = dut.on.bank1.arr[7] ^ 256'd1;
    transact(0,7,16,'0,0,golden[135],9,1);
    dut.on.bank1.arr[7] = dut.on.bank1.arr[7] ^ 256'd2;
    transact(0,7,16,'0,1,'0,11,0);
    check_failed();
    reset_service();
    transact(1,0,0,golden[0],0,golden[0],2,1);
    dut.on.checkbits[0] = dut.on.checkbits[0] ^ 10'd1;
    transact(0,0,0,'0,0,golden[0],6,1);
    if (fault) fail("correctable sidecar error set fatal fault");
    $display("SHADOW_METRICS transactions=%0d reads=%0d writes=%0d full_reads=%0d stall_cycles=%0d max_response_cycles=%0d bad=%0d mut=%0d",transactions,reads,writes,full_reads,stalls,max_latency,bad,mut);
    $display("SHADOW_VERDICT %s",bad==0 ? "PASS" : "FAIL");
    if (bad) $fatal(1,"shadow exactness gate failed");
    $finish;
  end
endmodule
