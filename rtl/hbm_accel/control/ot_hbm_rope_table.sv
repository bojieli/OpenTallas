`timescale 1ps/1fs
`default_nettype none
// hbm-system 2026-10-08 (T3 gap 6): the RoPE cos/sin PRODUCER of the DS-V4.1 HBM die.
//
// Before: the SU norm / RoPE chains (ot_dsrom_su_norm cos_t / sin_t, "RoPE table (constants of the position)") took
// the tables as top-level inputs and every bench tied them off; nothing on the die made them.
// The golden (tools/hdc_golden_v41.py rope_cs) is cos / sin of the FP32 angle F(pos) * freqs evaluated in binary64
// and rounded to FP32 -- a correctly rounded transcendental of an arbitrary angle, so the exact, cheap producer is a
// TABLE: an HBM-resident image [set][pos][32 pairs] of {cos, sin} FP32 (set 0 plain theta 1e4, set 1 YaRN theta 1.6e5),
// written once at boot by the loader (8 sectors = 256 B an entry, 2 x 2^20 entries = 512 MiB a die), read here one
// step AHEAD: positions are known (AR: pos + 1; the compressed-row group position pos + 1 - r), so the fetch of the
// next step's three entries (plain @ p, YaRN @ p, YaRN @ p - 1) overlaps the current step and the chains see a
// registered table at step start.
//
// Read client of one stream-service stack (a K-port style request channel; the service routes by the address's
// pseudo-channel): rq_v/rq_rdy {addr30 (4-aligned), len 4, tag 8}, responses rs_v {tag8, beat2, data256}.
// Entry e = (set, pos): sectors TBASE[set] + 8 pos .. + 7 = two 4-sector reads.
// adv: the step at cur_pos starts (cur becomes valid only if its fetch completed: stall_cyc counts the wait), the
// unit then fetches cur_pos + 1.  Outputs: plain / yarn / yarn_m1 cos and sin, 32 x FP32 each, of cur_pos.
module ot_hbm_rope_table #(
  parameter [29:0] TBASE0 = 30'h0000000, parameter [29:0] TBASE1 = 30'h0800000,   // 2^23 sectors a set
  parameter integer MUT = 0                       // bench negative control: 1 = YaRN entry read from set 0
)(
  input  wire          clk, rst_n,
  input  wire          start, input wire [19:0] start_pos,     // job start: fetch start_pos, then follow adv
  input  wire          adv,                                    // step advances to cur_pos + 1
  output reg           cur_v, output reg [19:0] cur_pos, output reg [31:0] stall_cyc,   // stall: cycles a step (adv) waited
  output wire [1023:0] cos_plain, output wire [1023:0] sin_plain,
  output wire [1023:0] cos_yarn,  output wire [1023:0] sin_yarn,
  output wire [1023:0] cos_yarn1, output wire [1023:0] sin_yarn1,      // YaRN at pos - 1 (ratio-2 group position)
  output reg           rq_v, input wire rq_rdy, output reg [29:0] rq_addr, output wire [3:0] rq_len, output reg [7:0] rq_tag,
  input  wire          rs_v, input wire [7:0] rs_tag, input wire [1:0] rs_beat, input wire [255:0] rs_data
);
  assign rq_len = 4'd4;
  // two banks (A/B) x 3 entries x 8 sectors; bank `cb` is the current one
  reg [255:0] tb [0:1][0:2][0:7];
  reg cb;                                  // current bank
  reg [5:0] got;                           // sectors landed in the fetch bank (24 = complete)
  reg [2:0] ri;                            // reads issued for the fetch (6)
  reg fetching, fetched; reg [19:0] fpos;
  wire fb = ~cb;
  reg adv_pend;
  // read i (0..5): entry i >> 1, half i & 1
  wire [1:0] ent = ri[2:1];
  wire [19:0] epos = (ent == 2'd2) ? fpos - 20'd1 : fpos;
  wire [29:0] ebase = ((ent == 2'd0) || (MUT == 1)) ? TBASE0 : TBASE1;
  wire [29:0] eaddr = ebase + {epos, 3'b000} + {27'd0, ri[0], 2'b00};
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      cb <= 1'b0; got <= 0; ri <= 0; fetching <= 1'b0; fetched <= 1'b0; cur_v <= 1'b0; cur_pos <= 0;
      rq_v <= 1'b0; stall_cyc <= 0; fpos <= 0;
    end else begin
      // issue the fetch reads one at a time (registered request, held until accepted)
      if (rq_v && rq_rdy) rq_v <= 1'b0;
      else if (fetching && !rq_v && ri < 3'd6) begin
        rq_v <= 1'b1; rq_addr <= eaddr; rq_tag <= {fb, 4'd0, ri}; ri <= ri + 3'd1;
      end
      if (rs_v && rs_tag[7] == fb) begin
        tb[fb][rs_tag[2:1]][{rs_tag[0], rs_beat}] <= rs_data;
        got <= got + 6'd1;
      end
      if (fetching && got == 6'd24) begin fetching <= 1'b0; fetched <= 1'b1; end
      // control
      if (start) begin
        fpos <= start_pos; fetching <= 1'b1; fetched <= 1'b0; got <= 0; ri <= 0; cur_v <= 1'b0; cur_pos <= start_pos;
      end else if ((adv || !cur_v) && fetched) begin             // the fetch bank becomes current (same cycle as adv)
        cb <= fb; cur_v <= 1'b1; cur_pos <= fpos; fetched <= 1'b0;
        fpos <= fpos + 20'd1; fetching <= 1'b1; got <= 0; ri <= 0;
      end else if (adv) cur_v <= 1'b0;                            // step done before the prefetch landed: wait
      if (adv_pend && !cur_v) stall_cyc <= stall_cyc + 32'd1;
    end
  // a step is waiting for the table when the consumer advanced and the next entry has not landed
  always @(posedge clk or negedge rst_n)
    if (!rst_n) adv_pend <= 1'b0; else if (adv && !fetched) adv_pend <= 1'b1; else if (cur_v) adv_pend <= 1'b0;
  genvar k;
  generate for (k = 0; k < 32; k = k + 1) begin : go_
    // sector q of an entry holds pairs 4q .. 4q + 3 as {cos, sin} words: pair k at sector k >> 2, word 2 (k & 3)
    assign cos_plain[32*k +: 32] = tb[cb][0][k >> 2][64*(k & 3) +: 32];
    assign sin_plain[32*k +: 32] = tb[cb][0][k >> 2][64*(k & 3) + 32 +: 32];
    assign cos_yarn[32*k +: 32]  = tb[cb][1][k >> 2][64*(k & 3) +: 32];
    assign sin_yarn[32*k +: 32]  = tb[cb][1][k >> 2][64*(k & 3) + 32 +: 32];
    assign cos_yarn1[32*k +: 32] = tb[cb][2][k >> 2][64*(k & 3) +: 32];
    assign sin_yarn1[32*k +: 32] = tb[cb][2][k >> 2][64*(k & 3) + 32 +: 32];
  end endgenerate
endmodule
`default_nettype wire
