`default_nettype none
// Opt-in successor. First DATA capture is an asynchronous synchronizer, not
// deterministic phase-qualified STA. See before-build model ce6525178 for
// mandatory startup POR recovery/removal and technology MTBF qualification.
module ot_hbm_clock_reset_data_boundary #(parameter bit ENABLE=0)(
 input wire aon_clk,clk_stream,clk_serial,clk_hbm,clk_link,
 input wire cold_por_n,pll_lock,sequence_ready,
 input wire [16:0] reset_intent_n,
 output wire [16:0] reset_n,
 output wire ready
);
 generate if(!ENABLE) begin:disabled
  assign reset_n=0;
  assign ready=0;
 end else begin:enabled
  // Clock indices: PHY[3:0] HBM; links[12:4] link;
  // collective[13] stream/[14] serial; command[15] stream/[16] serial.
  for(genvar i=0;i<17;i=i+1) begin:endpoint
   wire endpoint_clk=(i<4)?clk_hbm:(i<13)?clk_link:
      (i==13 || i==15)?clk_stream:clk_serial;
   (* async_reg="true" *) reg intent_meta,intent_sync;
   reg local_reset_n;
   always @(posedge endpoint_clk or negedge cold_por_n)
    if(!cold_por_n) begin intent_meta<=0;intent_sync<=0;end
    else begin
     intent_meta<=reset_intent_n[i] & pll_lock;
     intent_sync<=intent_meta;
    end
   // Reset release/reassertion is half a cycle from positive-edge sinks.
   // Cold POR alone asserts asynchronously; startup source must qualify its
   // release relative to this negative edge as well as the first DATA FF.
   always @(negedge endpoint_clk or negedge cold_por_n)
    if(!cold_por_n) local_reset_n<=0;
    else local_reset_n<=intent_sync;
   assign reset_n[i]=local_reset_n;
  end
  (* async_reg="true" *) reg [16:0] ready_meta,ready_sync;
  reg ready_registered;
  always @(posedge aon_clk or negedge cold_por_n)
   if(!cold_por_n) begin ready_meta<=0;ready_sync<=0;ready_registered<=0;end
   else begin
    ready_meta<=reset_n;
    ready_sync<=ready_meta;
    ready_registered<=sequence_ready & (&ready_sync);
   end
  assign ready=ready_registered;
 end endgenerate
endmodule

// The production wrapper owns no oscillator, divider, clock gate, power FSM,
// lease or boot FSM. Existing AON sequencer supplies held reset intents.
module ot_hbm_clock_reset_data_pll #(parameter bit ENABLE=0)(
 input wire aon_clk,refclk,cold_por_n,pll_reset_n,sequence_ready,
 input wire [16:0] reset_intent_n,
 output wire clk_stream,clk_serial,clk_hbm,clk_link,pll_lock,
 output wire [16:0] reset_n,output wire ready
);
 ot_hbm_pll_bb pll(.refclk(refclk),.reset_n(cold_por_n & pll_reset_n),
  .clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),
  .clk_link(clk_link),.locked(pll_lock));
 ot_hbm_clock_reset_data_boundary #(.ENABLE(ENABLE)) boundary(
  .aon_clk(aon_clk),.clk_stream(clk_stream),.clk_serial(clk_serial),
  .clk_hbm(clk_hbm),.clk_link(clk_link),.cold_por_n(cold_por_n),
  .pll_lock(pll_lock),.sequence_ready(sequence_ready),
  .reset_intent_n(reset_intent_n),.reset_n(reset_n),.ready(ready));
endmodule
`default_nettype wire
