`timescale 1ns/1ps
// Preparation only. qwen_optin_capture_logic must come from the later,
// Maxwell-priced default-off source variant; this file defines no candidate.
module tb_qwen_rom_hold_capture_equivalence;
  reg clk=0, rst_n=0, wrom_re=0;
  reg [23:0] wrom_addr=0;
  reg [2659:0] rom_rd; // 10 actual266-bit macro output interfaces, no reset
  wire [511:0] original_q, default_q, enabled_q;
  wire [4:0] original_ce, default_ce, enabled_ce;
  wire [11:0] original_addr, default_addr, enabled_addr;
  integer edge_number=0, checks=0, unknown_selected_checks=0, p,b;
  always #5 clk=~clk;
  qwen_current_capture_logic original(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),
    .rom_rd(rom_rd),.wrom_q(original_q),.rom_ce(original_ce),.rom_addr(original_addr));
  // Default must remain off, without supplying the opt-in parameter.
  qwen_optin_capture_logic default_variant(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),
    .rom_rd(rom_rd),.wrom_q(default_q),.rom_ce(default_ce),.rom_addr(default_addr));
  qwen_optin_capture_logic #(.ROM_HOLD_DIRECT_CAPTURE(1)) enabled_variant(
    .clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),
    .wrom_q(enabled_q),.rom_ce(enabled_ce),.rom_addr(enabled_addr));
  function automatic [265:0] response(input integer n, col, bank);
    reg [265:0] v; integer bit_number;
    begin
      for (bit_number=0;bit_number<266;bit_number=bit_number+1)
        v[bit_number]=((n*73+col*19+bank*31+bit_number*7) >> (bit_number%5)) & 1;
      // Deliberate four-state payloads, including the consumed low256 bits.
      // No X is converted tozero or declared an exact numeric word.
      if (n%7==0) v[13:6]=8'bx1z00xz1;
      if (n%11==0) v[265:256]=10'bxz01xz1010;
      response=v;
    end
  endfunction
  // Same pre-edge/NBA CE-hold relation as the pinned ROM model. This is a
  // response fixture, not the ROM array, trained weights or macro timing.
  always @(posedge clk) begin
    for (p=0;p<2;p=p+1)
      for (b=0;b<5;b=b+1)
        if (original_ce[b]) rom_rd[(p*5+b)*266 +: 266] <= response(edge_number,p,b);
    edge_number=edge_number+1;
  end
  task automatic step(input bit reset_released,read_enable,input integer bank,row);
    begin
      @(negedge clk);rst_n=reset_released;wrom_re=read_enable;wrom_addr=(bank<<12)|row;
      #1;
      if (default_ce !== original_ce || enabled_ce !== original_ce ||
          default_addr !== original_addr || enabled_addr !== original_addr)
        $fatal(1,"ROM request interface mismatch edge=%0d",edge_number);
      @(posedge clk);#1;
      // Case comparison retains X/Z. Compare only the bank-masked consumer
      // interface; never demand equal raw unselected capture registers.
      if (default_q !== original_q || enabled_q !== original_q)
        $fatal(1,"four-state selected output mismatch edge=%0d bank=%0d",edge_number,bank);
      if (!reset_released && original_q !== 512'd0)
        $fatal(1,"reset selected output notzero");
      if ((^original_q) === 1'bx) unknown_selected_checks=unknown_selected_checks+1;
      checks=checks+1;
    end
  endtask
  integer n;
  initial begin
    // rd/cap intentionally start unknown. Establish asynchronous metadata
    // reset via an actual falling edge before the first observed read.
    rst_n=1;#1;rst_n=0;
    step(0,0,0,0);step(1,0,0,0);
    for (n=0;n<5;n=n+1) begin
      step(1,1,n,n*11); // each bank's first read
      step(1,0,n,0);step(1,0,n,0);
    end
    for (n=0;n<20;n=n+1) step(1,1,n%5,n*17); // consecutive bank switches
    for (n=0;n<8;n=n+1) step(1,1,3,n*23); // consecutive same bank
    step(1,0,3,0);step(1,0,3,0);
    step(1,1,2,7);step(0,1,4,9); // reset while a read is pending; ROM may still read
    step(0,0,4,9);step(1,0,4,9);step(1,1,1,13);step(1,0,1,13);
    step(1,1,5,0);step(1,0,5,0); // out-of-range: no bank CE; delayed mask becomeszero
    for (n=0;n<20;n=n+1) step(1,(n%3)!=0,(n*3)%5,n*29);
    step(1,0,0,0);step(1,0,0,0);
    if (unknown_selected_checks==0) $fatal(1,"four-state selected payload coverage absent");
    $display("PASS QWEN_ROM_HOLD_CAPTURE_LITERAL_FOURSTATE checks=%0d unknown_selected=%0d",checks,unknown_selected_checks);
    $finish;
  end
endmodule
