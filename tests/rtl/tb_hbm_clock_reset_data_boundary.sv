`timescale 1ns/1ps
module tb;
 reg aon_clk=0,clk_stream=0,clk_serial=0,clk_hbm=0,clk_link=0;
 reg start_clocks=0,cold_por_n=1,pll_lock=0,sequence_ready=0;
 reg [16:0] reset_intent_n=0;
 wire [16:0] reset_n,off_reset;
 wire ready,off_ready;
 ot_hbm_clock_reset_data_boundary #(.ENABLE(1)) dut(.*);
 ot_hbm_clock_reset_data_boundary off_dut(.aon_clk(aon_clk),.clk_stream(clk_stream),
  .clk_serial(clk_serial),.clk_hbm(clk_hbm),.clk_link(clk_link),
  .cold_por_n(cold_por_n),.pll_lock(pll_lock),.sequence_ready(sequence_ready),
  .reset_intent_n(reset_intent_n),.reset_n(off_reset),.ready(off_ready));
 // Startup-only quiet source contract; no runtime clock gating exercised.
 always #1.37 if(start_clocks) aon_clk=~aon_clk;
 always #0.416667 if(start_clocks) clk_stream=~clk_stream;
 initial begin #0.071;forever #0.555556 if(start_clocks) clk_serial=~clk_serial;end
 initial begin #0.137;forever #0.512 if(start_clocks) clk_hbm=~clk_hbm;end
 initial begin #0.191;forever #0.416667 if(start_clocks) clk_link=~clk_link;end
 reg [16:0] expected=0;
 for(genvar i=0;i<17;i=i+1) begin:oracle
  wire c=(i<4)?clk_hbm:(i<13)?clk_link:(i==13 || i==15)?clk_stream:clk_serial;
  reg meta=0,sync=0,oldmeta;
  always @(posedge c or negedge cold_por_n) begin
   if(!cold_por_n) begin meta=0;sync=0;end
   else begin oldmeta=meta;meta=reset_intent_n[i] & pll_lock;sync=oldmeta;end
  end
  always @(negedge c or negedge cold_por_n) begin
   expected[i]=cold_por_n ? sync : 0;
   #0.002;
   if(reset_n[i]!==expected[i]) $fatal(1,"endpoint oracle %0d got %b expected %b",i,reset_n[i],expected[i]);
  end
  // No DATA intent or lock transition may directly change reset output.
  always @(reset_n[i]) begin
   #0.002;
   if(cold_por_n && reset_n[i]!==expected[i]) $fatal(1,"raw intent bypass endpoint %0d",i);
  end
 end
 reg [16:0] return_meta=0,return_sync=0,old_return_meta;
 reg expected_ready=0;
 always @(posedge aon_clk or negedge cold_por_n) begin
  if(!cold_por_n) begin return_meta=0;return_sync=0;expected_ready=0;end
  else begin
   expected_ready=sequence_ready & (&return_sync);
   old_return_meta=return_meta;return_meta=expected;return_sync=old_return_meta;
  end
  #0.003;
  if(ready!==expected_ready) $fatal(1,"ready oracle got %b expected %b",ready,expected_ready);
 end
 always @(ready) begin
  #0.003;
  if(cold_por_n && ready!==expected_ready) $fatal(1,"direct ready bypass");
 end
 integer phase;
 initial begin
  #0.01;cold_por_n=0;
  #0.10;cold_por_n=1;
  // First PLL AND AON edges follow cold POR release by at least 300 ps.
  #0.30;start_clocks=1;
  #0.029;pll_lock=1;reset_intent_n=17'h1ffff;sequence_ready=1;
  #15;if(reset_n!==17'h1ffff || !ready) $fatal(1,"boot failed");
  for(phase=0;phase<6;phase=phase+1) begin
   // Relative-phase changes held far longer than synchronizer latency.
   #(0.019+phase*0.037);reset_intent_n[phase+4]=0;
   #12;if(reset_n[phase+4]!==0 || ready!==0) $fatal(1,"held intent loss failed");
   reset_intent_n[phase+4]=1;
   #12;if(reset_n!==17'h1ffff || !ready) $fatal(1,"held intent recovery failed");
  end
  #0.173;pll_lock=0;
  // Permitted PLL-loss contract: clocks remain valid until sampled reset.
  #3;if(reset_n!==0) $fatal(1,"PLL-loss bounded assertion failed");
  #10;if(ready!==0) $fatal(1,"PLL-loss returned ready failed");
  pll_lock=1;#15;if(!ready) $fatal(1,"PLL reacquisition failed");
  sequence_ready=0;#3;if(ready!==0) $fatal(1,"AON held ready clear failed");
  #0.013;cold_por_n=0;#0.005;
  if(reset_n!==0 || ready!==0) $fatal(1,"cold assertion failed");
  if(off_reset!==0 || off_ready!==0) $fatal(1,"default enable failed");
  $display("PASS DATA boundary: 17 endpoints, phase variation, held intents, valid-clock PLL loss, three-AON registered ready, default off");
  $finish;
 end
 initial begin #250;$fatal(1,"bench failed to complete");end
endmodule
