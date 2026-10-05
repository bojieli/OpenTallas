`timescale 1ps/1fs
// Source-only adapter test, NOT a leaf/joint/ME qualification replay.
// The response driver follows the already measured two-edge leaf contract.
module tb_code_read_align;
  reg clk=0; always #416.666 clk=~clk;
  reg por_n=0, consumer_enable=1, leaf_fault=0;
  reg [1:0] rd_fire=0, rsp_ready=0;
  reg [5:0] virtual_bank=0;
  reg [1:0] leaf_rd_rsp_v=0, stage1=0;
  reg [511:0] leaf_rd_data=0, stage_data=0;
  wire [1:0] ready, rsp;
  wire [2659:0] rom;
  wire fault;
  parameter integer MEM_EXTRA=0;
  ot_qwen_hbm_code_read_align #(.ENABLE(1),.MEM_EXTRA(MEM_EXTRA)) dut(
    .clk(clk),.por_n(por_n),.consumer_enable(consumer_enable),
    .rd_fire(rd_fire),.virtual_bank(virtual_bank),
    .leaf_rd_rsp_v(leaf_rd_rsp_v),.leaf_rd_data(leaf_rd_data),.leaf_fault(leaf_fault),
    .consumer_ready(ready),.rsp_v(rsp),.rsp_ready(rsp_ready),.rom_rd(rom),.fault(fault));
  always @(posedge clk) begin
    if(!por_n) begin stage1<=0;leaf_rd_rsp_v<=0;end
    else begin
      stage1<=rd_fire; leaf_rd_rsp_v<=stage1;
      if(|rd_fire) stage_data<={256'hfedcba9876543210,256'h123456789abcdef0};
      if(|stage1) leaf_rd_data<=stage_data;
    end
  end
  task tick;
    begin @(posedge clk);#1;end
  endtask
  initial begin
    tick(); @(negedge clk);por_n=1;
    // Uninstalled physical spans are refused by the enclosing mapper, not
    // inferred from virtual tags here. Out-of-range tags5..7 still refuse.
    for(integer b=5;b<8;b=b+1) begin
      virtual_bank={3'(b),3'(b)};#1;
      if(ready!==0 || rsp!==0) $fatal(1,"out-of-range virtual bank accepted");
    end
    for(integer b=0;b<5;b=b+1) begin
      @(negedge clk);virtual_bank={3'(4-b),3'(b)};rsp_ready=0;#1;
      if(ready!==3) $fatal(1,"valid virtual tags not ready");
      rd_fire=3; tick();
      if(rsp!==0 || ready!==0) $fatal(1,"early response or repeated acceptance");
      @(negedge clk);rd_fire=0;
      tick();
      if(MEM_EXTRA==0 && rsp!==3) $fatal(1,"missing second-edge response");
      if(MEM_EXTRA==1 && rsp!==0) $fatal(1,"MEM_EXTRA capture bypassed");
      tick();
      if(rsp!==3 || rom[b*266+:256]!==256'h123456789abcdef0 ||
         rom[(5+4-b)*266+:256]!==256'hfedcba9876543210)
        $fatal(1,"response data/bank alignment");
      for(integer slot=0;slot<5;slot=slot+1) begin
        if(slot!=b && rom[slot*266+:266]!==0) $fatal(1,"wrong column0 bank driven");
        if(slot!=4-b && rom[(5+slot)*266+:266]!==0) $fatal(1,"wrong column1 bank driven");
      end
      if(rom[b*266+256+:10]!==0) $fatal(1,"unused upper bits not zero");
      // Changing proposed tag/data while stalled must not relabel the response.
      @(negedge clk);virtual_bank={3'd5,3'd5};leaf_rd_data='1;
      tick();tick();
      if(rsp!==3 || ready!==0 || rom[b*266+:256]!==256'h123456789abcdef0 || fault)
        $fatal(1,"held response changed");
      @(negedge clk);rsp_ready=3;
      tick();
      if(rsp!==0 || ready!==0 || fault) $fatal(1,"retirement/invalid next tag");
    end
    // A real leaf fault never becomes valid zero data or positive readiness.
    @(negedge clk);leaf_fault=1;#1;
    if(rsp!==0 || ready!==0 || !fault) $fatal(1,"fault not refused");
    $display("PASS_READ_ALIGN_ADAPTER_ONLY MEM_EXTRA=%0d",MEM_EXTRA);
    $finish;
  end
endmodule
