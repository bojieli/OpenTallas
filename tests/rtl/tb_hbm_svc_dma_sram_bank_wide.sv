`timescale 1ns/1ps
module tb_hbm_svc_dma_sram_bank_wide;
  parameter integer MUT = 0;
  parameter integer BANK_MUT = 0;
  reg clk=0; always #0.4165 clk=~clk;
  reg rst_n=0, wr_v=0, rd_v=0, out_rdy=1, wr_fault=0;
  reg [7:0] wr_addr=0, rd_addr=0;
  reg [255:0] wr_data=0;
  wire wr_rdy,rd_rdy,out_v,out_fault;
  wire [255:0] out_data;
  hbm_svc_dma_sram_bank_wide #(.ECC_MUT(MUT), .BANK_MUT(BANK_MUT)) dut(.*);
  reg [255:0] golden[0:255];
  reg [256:0] expected[0:4095];
  integer sent=0,seen=0,cyc=0, first_launch=-1, first_publish=-1;
  integer read_prev=-1, read_gap=0, write_prev=-1, write_gap=0;
  reg check_read_ii=0,check_write_ii=0,held=0;
  reg [256:0] held_word;
  function automatic [255:0] pattern(input integer n);
    pattern={64'h0123456789abcdef ^ n,64'hfedcba9876543210 ^ n,
             64'h55aa55aa3cc3c33c ^ n,64'h55aa00ff01010101 ^ n};
  endfunction
  always @(posedge clk) begin
    cyc=cyc+1;
    if(rst_n) begin
      if(wr_v && wr_rdy && check_write_ii) begin
        if(write_prev>=0 && cyc-write_prev != 2) $fatal(1,"write II != 2");
        write_prev=cyc; write_gap=write_gap+1;
      end
      if(rd_v && rd_rdy) begin
        if(first_launch<0) first_launch=cyc;
        if(check_read_ii) begin
          if(read_prev>=0 && cyc-read_prev != 2) $fatal(1,"read II != 2");
          read_prev=cyc; read_gap=read_gap+1;
        end
      end
      if(held && (!out_v || {out_fault,out_data} !== held_word))
        $fatal(1,"publication changed under backpressure");
      held=out_v && !out_rdy;
      if(held) held_word={out_fault,out_data};
      if(out_v && out_rdy) begin
        if(first_publish<0) first_publish=cyc;
        if(seen>=sent) $fatal(1,"unsolicited/duplicate output");
        if({out_fault,out_data} !== expected[seen])
          $fatal(1,"record %0d mismatch expected=%h actual=%h",seen,expected[seen],{out_fault,out_data});
        seen=seen+1;
      end
    end else held=0;
  end
  task automatic write_sector(input [7:0] a,input [255:0] d,input bit fault);
    begin
      @(negedge clk); wr_v=1;wr_addr=a;wr_data=d;wr_fault=fault;
      @(posedge clk); while(!wr_rdy) @(posedge clk);
      @(negedge clk);wr_v=0;
    end
  endtask
  task automatic read_sector(input [7:0] a,input [255:0] d,input bit fault);
    begin
      @(negedge clk);rd_v=1;rd_addr=a;
      expected[sent]={fault,d};sent=sent+1;
      @(posedge clk);while(!rd_rdy) @(posedge clk);
      @(negedge clk);rd_v=0;
    end
  endtask
  task automatic drain;
    begin wait(seen==sent);repeat(2) @(negedge clk); end
  endtask
  integer i,j,b;
  initial begin
    repeat(3) @(negedge clk);rst_n=1;
    // Macro initialization disabled by runner: every unwritten row poisons.
    for(i=0;i<256;i=i+1) read_sector(i,0,1);
    drain();
    check_write_ii=1;
    for(i=0;i<256;i=i+1) begin golden[i]=pattern(i);write_sector(i,golden[i],0);end
    check_write_ii=0;
    repeat(4) @(negedge clk);
    first_launch=-1;first_publish=-1;check_read_ii=1;
    for(i=0;i<256;i=i+1) read_sector(i,golden[i],0);
    check_read_ii=0;drain();
    // Monitor observes publication on the following acceptance edge (6),
    // while out_v becomes visible immediately after the fifth edge.
    if(first_publish-first_launch != 6) $fatal(1,"unexpected first latency %0d",first_publish-first_launch);
    $display("MEASURE read_visible_cycles=5 read_transfer_cycles=6 read_II=2 write_II=2");
    // Fill exactly four reservations, then verify admission stops and output
    // remains stable. Publication may not overwrite under indefinite stall.
    out_rdy=0;
    for(i=0;i<4;i=i+1) read_sector(i,golden[i],0);
    repeat(12) @(negedge clk);
    if(rd_rdy || dut.reserved != 4) $fatal(1,"missing finite reservation backpressure");
    out_rdy=1;drain();
    // Independent write/read ports concurrently use different groups.
    fork
      begin for(integer k=0;k<128;k=k+1) write_sector(k,pattern(k+128),0);end
      begin for(integer k=128;k<256;k=k+1) read_sector(k,golden[k],0);end
    join
    drain();repeat(4) @(negedge clk);
    for(i=0;i<128;i=i+1) golden[i]=pattern(i+128);
    // A same-group read waits for both payload and sidecar write edges.
    fork
      write_sector(31,pattern(999),0);
      begin repeat(1) @(posedge clk); read_sector(31,pattern(999),0);end
    join
    golden[31]=pattern(999);drain();
    // A continuously requested same-group read cannot starve a pending write.
    // Use identical data to make the transaction golden independent of which
    // completed version the reader observes.
    fork
      begin for(integer k=0;k<8;k=k+1) write_sector(0,golden[0],0);end
      begin for(integer k=0;k<8;k=k+1) read_sector(0,golden[0],0);end
    join
    drain();repeat(4) @(negedge clk);
    // Every payload bit and every check bit can be corrected independently.
    for(b=0;b<256;b=b+1) begin
      @(negedge clk);dut.mem0.arr[0][b*2]=~dut.mem0.arr[0][b*2];
      read_sector(0,golden[0],0);drain();
      dut.mem0.arr[0][b*2]=~dut.mem0.arr[0][b*2];
    end
    for(b=0;b<32;b=b+1) begin
      @(negedge clk);dut.mem0.arr[64][b*2]=~dut.mem0.arr[64][b*2];
      read_sector(0,golden[0],0);drain();
      dut.mem0.arr[64][b*2]=~dut.mem0.arr[64][b*2];
    end
    // Double-bit faults in each protected 64-bit word must poison everything.
    for(j=0;j<4;j=j+1) begin
      @(negedge clk);dut.mem0.arr[0][j*128]=~dut.mem0.arr[0][j*128];dut.mem0.arr[0][j*128+2]=~dut.mem0.arr[0][j*128+2];
      read_sector(0,0,1);drain();
      dut.mem0.arr[0][j*128]=~dut.mem0.arr[0][j*128];dut.mem0.arr[0][j*128+2]=~dut.mem0.arr[0][j*128+2];
    end
    for(b=32;b<52;b=b+1) begin
      @(negedge clk);dut.mem0.arr[64][b*2]=~dut.mem0.arr[64][b*2];
      read_sector(0,0,1);drain();
      dut.mem0.arr[64][b*2]=~dut.mem0.arr[64][b*2];
    end
    // Second macro + odd mux slot: logical payload127, sidecar255.
    // Full group identity must distinguish0 from128, and127 from255.
    for(b=0;b<256;b=b+1) begin
      @(negedge clk);dut.mem1.arr[63][b*2+1]=~dut.mem1.arr[63][b*2+1];
      read_sector(255,golden[255],0);drain();
      dut.mem1.arr[63][b*2+1]=~dut.mem1.arr[63][b*2+1];
    end
    for(b=0;b<32;b=b+1) begin
      @(negedge clk);dut.mem1.arr[127][b*2+1]=~dut.mem1.arr[127][b*2+1];
      read_sector(255,golden[255],0);drain();
      dut.mem1.arr[127][b*2+1]=~dut.mem1.arr[127][b*2+1];
    end
    // Corrupt paired identity to a different macro's group, preserving its
    // complement: transaction identity still must reject the sidecar.
    @(negedge clk);dut.mem1.arr[127][43*2+1]=~dut.mem1.arr[127][43*2+1];
    dut.mem1.arr[127][51*2+1]=~dut.mem1.arr[127][51*2+1];
    read_sector(255,0,1);drain();
    dut.mem1.arr[127][43*2+1]=~dut.mem1.arr[127][43*2+1];
    dut.mem1.arr[127][51*2+1]=~dut.mem1.arr[127][51*2+1];
    write_sector(3,pattern(3),1);repeat(4) @(negedge clk);
    read_sector(3,0,1);drain();
    // Locally resetting validity rejects retained physical contents.
    rst_n=0;repeat(2) @(negedge clk);rst_n=1;
    read_sector(0,0,1);drain();
    $display("PASS transactions=%0d payload_single=512 parity_single=64 double=4 metadata=20 no_init=256 concurrent_ports=128",seen);
    $finish;
  end
  initial begin repeat(30000) @(posedge clk);$fatal(1,"bench deadlock");end
endmodule
