`default_nettype none
// Reset release is a boot transaction while all actual domain clocks are low.
// No destination-clock asynchronous-reset FF is introduced by this controller.
module ot_hbm_quiescent_reset_commit #(
 parameter bit ENABLE=0, parameter integer GUARD=2
)(
 input wire aon_clk,raw_qualified_n,sequence_ready,
 input wire [16:0] desired_reset_n,
 input wire [3:0] actual_quiet_ack,
 output wire [16:0] reset_n,
 output wire [3:0] clock_enable_req,
 output wire ready,
 output wire fault,
 output wire [1:0] phase
);
 initial if(GUARD<2) $error("reset restart guard requires at least two AON edges");
 generate if(!ENABLE) begin:off
  assign reset_n=0;assign clock_enable_req=0;assign ready=0;assign fault=0;assign phase=0;
 end else begin:on
  localparam WAIT_QUIET=0,HOLD_GUARD=1,RUN=2;
  localparam CW=$clog2(GUARD+1);
  (* async_reg="true" *) reg [3:0] quiet_meta,quiet_sync;
  reg [16:0] pending,committed;
  reg [1:0] state;
  reg [CW-1:0] guard_count;
  reg permit,bad;
  always @(posedge aon_clk or negedge raw_qualified_n) begin
   if(!raw_qualified_n) begin
    quiet_meta<=0;quiet_sync<=0;pending<=0;committed<=0;
    state<=WAIT_QUIET;guard_count<=0;permit<=0;bad<=0;
   end else begin
    quiet_meta<=actual_quiet_ack;quiet_sync<=quiet_meta;
    // Assertions never wait for a stopped clock. Source intents are AON state
    // outputs held until sampled; a desired1 cannot undo an uncommitted0.
    committed<=committed & desired_reset_n;
    case(state)
     WAIT_QUIET: begin
      permit<=0;
      pending<=desired_reset_n;
      if((&quiet_sync) && (&actual_quiet_ack) && desired_reset_n==pending && !bad) begin
       committed<=pending;guard_count<=GUARD;state<=HOLD_GUARD;
      end
     end
     HOLD_GUARD: begin
      if(desired_reset_n!=pending) begin permit<=0;state<=WAIT_QUIET;end
      else if(!(&actual_quiet_ack)) begin
       // A source that violates its acknowledged hold cannot release resets.
       bad<=1;committed<=0;permit<=0;state<=WAIT_QUIET;
      end else if(guard_count==1) begin
       guard_count<=0;permit<=1;state<=RUN;
      end else guard_count<=guard_count-1'b1;
     end
     RUN: if(desired_reset_n!=committed) begin
      permit<=0;pending<=desired_reset_n;state<=WAIT_QUIET;
     end
     default: begin bad<=1;permit<=0;committed<=0;state<=WAIT_QUIET;end
    endcase
   end
  end
  assign reset_n={17{raw_qualified_n}} & committed & desired_reset_n;
  assign clock_enable_req={4{raw_qualified_n && permit && !bad}};
  // Each quiet bit is a held level, returned only by the actual gate. During
  // RUN its synchronized complement proves all four gates have really started.
  assign ready=raw_qualified_n && sequence_ready && permit && !bad &&
    state==RUN && (&committed) && !(|quiet_sync);
  assign fault=bad;
  assign phase=state;
 end endgenerate
endmodule

// Literal safe-edge clock producer. No divider, invented oscillator, refclk
// inversion, resettable release FF or asynchronous clock cut. During power-up
// endpoints remain reset until this producer has genuinely acknowledged quiet.
// The first request FF is an explicit CDC synchronizer requiring technology
// metastability characterization, not a synchronous AON timing claim.
module ot_hbm_boot_clock_gate #(parameter bit ENABLE=0)(
 input wire root_clk,enable_req,
 output wire domain_clk,quiet_ack
);
 generate if(!ENABLE) begin:off
  assign domain_clk=0;assign quiet_ack=1;
 end else begin:on
  (* async_reg="true" *) reg en_meta,en_sync;
  reg en_gate;
  always @(negedge root_clk) begin
   en_meta<=enable_req;en_sync<=en_meta;en_gate<=en_sync;
  end
  assign domain_clk=root_clk & en_gate;
  assign quiet_ack=!en_gate;
 end endgenerate
endmodule
`default_nettype wire
