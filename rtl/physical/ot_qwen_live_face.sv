`timescale 1ns/1ps
// r5 (2026-10-14): live-clock stream queue with a REGISTERED credit face (Qwen compute-die tile, items B + C).
//
// Replaces two structures that cannot close as native faces:
//   * the one-outstanding identity mailbox (toggle/ACK; typed D2 and D8 both 381 base edges per 128 words), and
//   * the combinational credit face (ACK pin -> XNOR -> credit pin; count + pending_post -> credit pin) that the
//     coherent-family clock gate consumed in the same cycle.
// The queue runs on the LIVE (ungated) base clock of the family; the core family runs on ICG(base_clk, en) where
// en(E) is the enable effective at base edge E.  Contract:
//   * credit_q is a flop.  It reaches the family ICG through LAT-1 further live register stages (die/parent
//     aggregation), so credit_q set at edge t enables at most the core edge t+LAT.
//   * core_en is the enable that was effective at the current base edge (sampled live, including disabled edges).
//     The word/identity a core edge E produced sits in core flops after E and is captured at base edge E+1 iff the
//     edge happened (step_q) and the producer flagged it: ONCE per producing edge, never from a held level while
//     the core clock is stopped (changing-identity safe: the capture copies the tuple of that edge only).
//   * credit is granted only if every word that can still arrive fits: count_next + LAT + 1 <= DEPTH
//     (LAT words decided but not yet captured + the edge being decided).  An overflow is still a FAULT (never a
//     drop), so a broken pause loop is detected by the authoritative owner of the capacity.
//   * consumer face: ready is registered at the pin (ready latency 1); consume_v / consume_tuple come from flops
//     through the DEPTH:1 head mux only.
// Deadlock freedom under a stopped core clock: every flop that decides credit is on the live clock; pops proceed
// while the core is paused, count falls, credit_q rises, en rises.  No core-clock register is on the pause loop.
// Full rate (one word per base edge with a ready consumer) needs DEPTH >= LAT + 3.
module ot_qwen_live_credit_queue #(
  parameter integer W = 209,
  parameter integer DEPTH = 8,
  parameter integer LAT = 2,
  parameter integer MUT = 0,          // bench mutants: 1 margin LAT-1, 2 capture on held level (no step), 3 no ready reg
  parameter integer PW = (DEPTH < 2) ? 1 : $clog2(DEPTH)
) (
  input  wire          base_clk,
  input  wire          rst_n,
  input  wire          core_en,      // enable effective at this base edge (live)
  input  wire          produce_v,    // core flop: this core edge produced a word
  input  wire [W-1:0]  produce_tuple,// core flops: the word + its identity
  output reg           credit_q,     // registered credit -> family enable chain (LAT stages total)
  input  wire          consume_ready,
  output wire          consume_v,
  output wire [W-1:0]  consume_tuple,
  output reg           fault
);
  localparam integer MARGIN = (MUT == 1) ? LAT : LAT + 1;
  reg          step_q, ready_q;
  reg [PW:0]   count;
  reg [PW-1:0] head, tail;
  reg [W-1:0]  entries [0:DEPTH-1];
  wire capture = ((MUT == 2) ? 1'b1 : step_q) && produce_v;
  wire pop     = ((MUT == 3) ? consume_ready : ready_q) && consume_v;
  assign consume_v     = !fault && count != 0;
  assign consume_tuple = entries[head];
  wire [PW:0] count_next = count + {{PW{1'b0}}, capture} - {{PW{1'b0}}, pop};
  always @(posedge base_clk or negedge rst_n) begin
    if (!rst_n) begin
      step_q <= 1'b0; ready_q <= 1'b0; count <= 0; head <= 0; tail <= 0; credit_q <= 1'b0; fault <= 1'b0;
    end else begin
      step_q  <= core_en;
      ready_q <= consume_ready;
      if (capture && count == DEPTH && !pop) fault <= 1'b1;
      if (capture) tail <= (tail == DEPTH - 1) ? {PW{1'b0}} : tail + 1'b1;
      if (pop)     head <= (head == DEPTH - 1) ? {PW{1'b0}} : head + 1'b1;
      count    <= count_next;
      credit_q <= !fault && (count_next + MARGIN <= DEPTH);
    end
  end
  // Payload storage carries no reset: count / head / tail qualify it.
  always @(posedge base_clk) if (capture) entries[tail] <= produce_tuple;
endmodule

// Live family enable: registered AND of the queues' credits and the external pause, LAT-1 register stages after
// credit_q (STAGES = LAT - 1 >= 0; STAGES = 0 means credit_q drives the ICG enable directly).  The returned en is
// what the ICG latches for the next base edge; core_en_eff is its effective value at that edge, for the queues.
module ot_qwen_live_family_enable #(
  parameter integer N = 2,
  parameter integer STAGES = 1
) (
  input  wire         base_clk,
  input  wire         rst_n,
  input  wire [N-1:0] credit_q,
  input  wire         run,             // external pause (registered by the caller)
  output wire         en
);
  generate if (STAGES == 0) begin : g_direct
    assign en = (&credit_q) && run;
  end else begin : g_pipe
    reg [STAGES-1:0] p;
    always @(posedge base_clk or negedge rst_n)
      if (!rst_n) p <= {STAGES{1'b0}};
      else p <= {p[STAGES-2 >= 0 ? STAGES-2 : 0:0], (&credit_q) && run} ;
    assign en = p[STAGES-1];
  end endgenerate
endmodule
