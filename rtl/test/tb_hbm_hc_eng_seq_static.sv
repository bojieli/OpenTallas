`timescale 1ns/1ps
// Small mapped-memory component gate; does not qualify HC arithmetic or die integration.
module tb_hbm_hc_eng_seq_static;
  reg clk=0; always #1 clk=~clk;
  reg rst_n=0, cfg_we=0, start_v=0;
  reg [9:0] cfg_addr=0;
  reg [255:0] cfg_data=0;
  reg [10:0] start_limit=16;
  wire [123:0] event_word;
  wire event_v,active,done,fault;
  wire [19:0] t;
  integer seen=0, cycles=0, mutation=0;
  ot_hbm_hc_eng_seq_static dut(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
    .start_v(start_v),.start_base(10'd0),.start_limit(start_limit),.start_loops(16'd1),
    .event_word(event_word),.event_v(event_v),.t(t),.active(active),.done(done),.fault(fault));
  always @(negedge clk) begin
    cycles=cycles+1;
    if(event_v) begin
      if(event_word[19:0] !== 20'(16+seen) || event_word[51:20] !== 32'(seen+100) || t !== 20'(17+seen))
        $fatal(1,"event data/time seen=%0d t=%0d word=%h",seen,t,event_word);
      seen=seen+1;
    end
    if(cycles>200) $fatal(1,"watchdog");
  end
  initial begin
    if($value$plusargs("MUT=%d",mutation)) begin end
    repeat(3) @(negedge clk); rst_n=1;
    for(integer i=0;i<16;i=i+1) begin
      @(negedge clk); cfg_we=1;cfg_addr=10'(i);cfg_data=0;
      cfg_data[255:240]=(mutation==1 && i==7) ? 16'hc7a3 : 16'hc7a2;
      cfg_data[233:224]=10'(i);cfg_data[51:20]=32'(i+100);cfg_data[19:0]=20'(16+i);
    end
    @(negedge clk);cfg_we=0;
    repeat(4) @(negedge clk);start_v=1;
    @(negedge clk);start_v=0;
    wait(done); repeat(2) @(negedge clk);
    if(fault || seen!=16) $fatal(1,"SEQ FAIL fault=%0d seen=%0d",fault,seen);
    $display("HC_ENG_SEQ PASS events=%0d exact consecutive cycles, mapped SRAM",seen);$finish;
  end
endmodule
