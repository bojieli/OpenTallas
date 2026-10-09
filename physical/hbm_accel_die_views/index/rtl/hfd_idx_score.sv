`timescale 1ps/1fs
`default_nettype none
// CLAUDE hbm-indexer 2026-10-08: hfd_idx_score -- the REAL index scorer of one HBM stack (x4 per die, one per stack),
// replacing the interim hfd_index_q shell's placeholder t_vm (key[511:0] ^ key[1023:512]).  Design, budget and fit:
// claude-takeover-20261007/review_queue/hbm-indexer.md.  NOT routed (review gate).
//
// Function (tools/hdc_golden_v41.py Model.indexer, the score lines): for every index key of this stack's contiguous
// block range (quarter q = stack q: die block ordinals 342q .. 342q+341, the ot_hbm_accel_index_path contract),
//   s = to_bf16(sum_h chunk8 to_bf16(relu(to_bf16(dots_q4(q_h, k))) * w_h)), masked -inf when keep = 0,
// with the unchanged exact arithmetic of ot_hdc_v41x_idx_array_l (4 slices x NK 4 = 16 keys / cycle, FPL 7 / FML 5 /
// QL 5, the 1.2 GHz streaming build).  16 keys/cycle = 8,704 b/cycle > the stack's ~6.5 kb/cycle HBM key rate, so the
// scan is HBM-bound (top-down sizing: the slice count is the smallest multiple of the 8-key block that covers the
// stack rate; 12 keys/cycle would break the selector's 16-lane block-aligned beat).
//
// Ports (every input lands in a flop, every output leaves a flop):
//   ik   NP x {data1088, tag10, v}: index-key LINES from the stack's stream service (svc kind-2 read striped over all 32
//        pseudo-channels; port p carries lines p, p+8, p+16, ... of the stack's key region in order; a line = 2 keys
//        of 544 b {scale bytes[543:512], FP4 codes[511:0]}; tag = line number mod 1024; the last beat is padded to 8
//        lines).  FWD=1: port p is launched on forwarded clock ikf[p] and lands through ot_hbm_accel_cdc_fifo
//        (capture on the forwarded clock's falling edge, as the shell did); FWD=0: common clock.
//   ikc  NP credit pulses back to the svc (one line freed; the svc holds 2^FA credits per port).
//   q    {payload568, kind2, v} from hfd_idx_sel (one-way): kind 0 query head {head8, codes512, sc32, w16} (as the
//        ot_hdc_v41x_idx_array_l ql port), kind 1 frame config {.., keep_en, n_q12, first_ord11, rank7}, kind 2 the
//        stack's keep bitmap (342 block bits, cand mask of layers 24..36).
//   s    score beat {idx20 x16, score16 x16, kv16, fault16, last, v} to hfd_idx_sel (credit flow: sc returns one credit
//        per beat popped from hfd_idx_sel's landing FIFO; CRED = that FIFO's depth).
//   st   {fault, busy, qloaded, 1'b0} status (registered).
module hfd_idx_score #(
  parameter integer L = 16,          // score lanes of this block (16: one block a stack; 4: one column tap of four)
  parameter integer LANE0 = 0,       // first lane of the stack's 16-key beat scored here (tap c: 4c)
  parameter integer FWD = 0,         // 1: forwarded-clock line ports through two-clock FIFOs
  parameter integer FA = 4,          // line FIFO address bits (depth 16 per port)
  parameter integer CRED = 64,       // output credits (hfd_idx_sel landing FIFO depth)
  parameter integer SAFE_QUERY_GATE = 0,
  parameter integer NK = 4, IW = 20, MD = 64, FPL = 7, FML = 5, QL = 5,
  parameter integer NP = L / 2,      // line ports (a line = 2 keys)
  parameter integer NS = L / NK,     // score slices
  parameter integer SW = 38 * L + 2  // score beat width
) (
  input  wire                ck,
  input  wire                rst,
  input  wire [NP*1099-1:0]  ik,
  input  wire [NP-1:0]       ikf,
  output reg  [NP-1:0]       ikc,
  input  wire [570:0]        q,
  output wire [570:0]        qx,      // the q bus, registered on to the next column tap of the stack (T = 4)
  output wire [SW-1:0]       s,
  input  wire                sc,
  output reg  [3:0]          st
);
  localparam integer KB = 544;                                // a line = 2 keys; the stack beat = 16 keys = 8 lines
  // negative mutants for the exact bench (simulation only; tools/hbm_idx_die_bench.py runs each and requires FAIL)
`ifndef SYNTHESIS
  reg mut_lane, mut_gid, mut_keep;
  initial begin
    mut_lane = $test$plusargs("MUT_LANE"); mut_gid = $test$plusargs("MUT_GID"); mut_keep = $test$plusargs("MUT_KEEP");
  end
`else
  localparam mut_lane = 1'b0, mut_gid = 1'b0, mut_keep = 1'b0;
`endif
  // ------------------------------------------------------------------ reset synchroniser
  reg rs1, rs2;
  always @(posedge ck or negedge rst) if (!rst) {rs2, rs1} <= 2'b00; else {rs2, rs1} <= {rs1, 1'b1};
  wire rn = rs2;
  // ------------------------------------------------------------------ q bus pin register
  reg qv; reg [1:0] qk; reg [567:0] qp;
  always @(posedge ck or negedge rn) if (!rn) qv <= 1'b0; else qv <= q[0];
  always @(posedge ck) begin qk <= q[2:1]; qp <= q[570:3]; end
  assign qx = {qp, qk, qv};
  // frame config / keep bitmap / query load
  reg [6:0] rank; reg [10:0] ford; reg [11:0] nq; reg keep_en;
  reg [341:0] keepbm;
  reg active, qloaded, fault;
  reg [5:0] heads; reg [2:0] settle;
  reg [8:0] beat, nbeats;               // beats of this frame (<= 171)
  reg ql_v; reg [7:0] ql_head; reg [511:0] ql_codes; reg [31:0] ql_sc; reg [15:0] ql_w;
  wire ql_ready;
  always @(posedge ck) begin
    ql_head <= qp[567:560]; ql_codes <= qp[559:48]; ql_sc <= qp[47:16]; ql_w <= qp[15:0];
  end
  // ------------------------------------------------------------------ line landing (one FIFO per port)
  wire [NP-1:0] lne;
  wire [NP*1098-1:0] lrd;
  wire pop;
  genvar p;
  generate for (p = 0; p < NP; p = p + 1) begin : gp
    if (FWD) begin : fw
      wire wck = ~ikf[p];
      reg cv; reg [1097:0] cd;                        // capture flop at the pin (falling edge of the forwarded clock)
      always @(posedge wck or negedge rst) if (!rst) cv <= 1'b0; else cv <= ik[p*1099];
      always @(posedge wck) cd <= ik[p*1099+1 +: 1098];
      wire full_; wire [2:0] fr_; wire em;
      ot_hbm_accel_cdc_fifo #(.W(1098), .AW(FA)) u_x (.wclk(wck), .wrst_n(rst), .we(cv), .wdata(cd), .full(full_),
        .rd_freed(fr_), .rclk(ck), .rrst_n(rn), .re(pop), .rdata(lrd[p*1098 +: 1098]), .empty(em));
      assign lne[p] = !em;
    end else begin : cc
      reg cv; reg [1097:0] cd;
      always @(posedge ck or negedge rn) if (!rn) cv <= 1'b0; else cv <= ik[p*1099];
      always @(posedge ck) cd <= ik[p*1099+1 +: 1098];
      wire [FA:0] cnt_;
      hfd_idx_fifo #(.W(1098), .AW(FA)) u_f (.ck(ck), .rst_n(rn), .we(cv), .wd(cd), .re(pop),
        .rd(lrd[p*1098 +: 1098]), .ne(lne[p]), .cnt(cnt_));
    end
  end endgenerate
  // ------------------------------------------------------------------ beat assembly -> scorer array
  reg bv;                                       // beat register valid
  reg [L-1:0] bkv, bref, bkeep; reg [NS-1:0] blast;
  reg [NS*IW-1:0] bfirst;                        // first index of each slice's NK keys
  reg [L*KB-1:0] bkey;
  wire a_ready;
  wire take = bv && a_ready;
  wire last_beat = (beat + 9'd1 == nbeats);
  wire empty_frame = (nq == 12'd0);
  wire beat_go = active && qloaded && (settle == 3'd0) && (beat < nbeats) && (!bv || take);
  assign pop = beat_go && !empty_frame && (&lne);
  wire beat_load = beat_go && (empty_frame || (&lne));
  // global ID of key 16b + l: 8 * (96 * (ford + 2b + l/8) + rank) + l%8 (ot_hbm_accel_index_path ID rule)
  reg [IW-1:0] g0;                               // ID base of the beat being loaded: 768 * (ford + 2 beat) + 8 rank
  integer l, j;
  reg tag_bad;
  always @* begin
    tag_bad = 1'b0;
    for (j = 0; j < NP; j = j + 1)
      if (lrd[j*1098 +: 10] != 10'({beat, 3'b000} + 12'(LANE0 / 2 + j))) tag_bad = 1'b1;
  end
  always @(posedge ck) if (beat_load) begin
    for (l = 0; l < L; l = l + 1) begin
      bkey[l*KB +: KB] <= empty_frame ? {KB{1'b0}} : lrd[(l/2)*1098 + 10 + (((l < 2) && mut_lane) ? 1 - (l%2) : (l%2))*KB +: KB];
      bkv[l] <= ({beat, 4'(LANE0 + l)} < {1'b0, nq});
      bref[l] <= !empty_frame && (lrd[(l/2)*1098 + 10 + (l%2)*KB + 512 +: 8] >= 8'd253 ||
                                  lrd[(l/2)*1098 + 10 + (l%2)*KB + 520 +: 8] >= 8'd253 ||
                                  lrd[(l/2)*1098 + 10 + (l%2)*KB + 528 +: 8] >= 8'd253 ||
                                  lrd[(l/2)*1098 + 10 + (l%2)*KB + 536 +: 8] >= 8'd253);
      bkeep[l] <= !keep_en || mut_keep || (({1'b0, beat, 1'b0} + 11'((LANE0 + l) / 8)) < 11'd342 &&
                                                keepbm[{1'b0, beat, 1'b0} + 11'((LANE0 + l) / 8)]);
    end
    for (l = 0; l < NS; l = l + 1)
      bfirst[l*IW +: IW] <= g0 + IW'(((LANE0 + l * NK) / 8) * 768 + (LANE0 + l * NK) % 8);
    blast <= {NS{last_beat}};
  end
  // ------------------------------------------------------------------ frame control
  reg [7:0] cred;
  wire o_v, o_last_any; wire [NS-1:0] o_last; wire [L-1:0] o_kv, o_fault; wire [L*16-1:0] o_score;
  wire [L*IW-1:0] o_index; wire pfault;
  reg scv;
  always @(posedge ck or negedge rn) if (!rn) scv <= 1'b0; else scv <= sc;
  wire o_take = o_v && (cred != 8'd0);
  always @(posedge ck or negedge rn) begin
    if (!rn) begin
      active <= 1'b0; qloaded <= 1'b0; fault <= 1'b0; heads <= 6'd0; settle <= 3'd0; beat <= 9'd0; nbeats <= 9'd0;
      bv <= 1'b0; ql_v <= 1'b0; cred <= 8'(CRED); ikc <= {NP{1'b0}}; keep_en <= 1'b0; nq <= 12'd0;
      st <= 4'd0;
    end else begin
      ql_v <= qv && qk == 2'd0;
      ikc <= {NP{pop}};
      cred <= cred - {7'd0, o_take} + {7'd0, scv};
      if (qv && qk == 2'd1) begin                 // frame config: a new frame
        rank <= qp[6:0]; ford <= qp[17:7]; nq <= qp[29:18]; keep_en <= qp[30];
        g0 <= IW'(768) * IW'(qp[17:7]) + IW'(8) * IW'(qp[6:0]) + (mut_gid ? IW'(8) : IW'(0));
        nbeats <= (qp[29:18] == 12'd0) ? 9'd1 : 9'((qp[29:18] + 12'd15) >> 4);
        beat <= 9'd0; heads <= 6'd0; qloaded <= 1'b0; settle <= 3'd0; active <= 1'b1;
        if (active) fault <= 1'b1;                // previous frame not drained
      end
      if (qv && qk == 2'd2) keepbm <= qp[341:0];
      if (ql_v) begin
        if (!ql_ready || !active || qloaded) fault <= 1'b1;
        heads <= heads + 6'd1;
        if (heads == 6'd31) begin qloaded <= 1'b1; settle <= 3'd4; end
      end
      if (settle != 3'd0) settle <= settle - 3'd1;
      if (beat_load) begin
        bv <= 1'b1; beat <= beat + 9'd1;
        g0 <= g0 + IW'(1536);
        if (pop && tag_bad) fault <= 1'b1;
      end else if (take) bv <= 1'b0;
      if (o_take && o_last[0]) active <= 1'b0;
      if (pfault) fault <= 1'b1;
      st <= {fault, active, qloaded, 1'b0};
    end
  end
  ot_hdc_v41x_idx_array_l #(.NS(NS), .NK(NK), .NB(4), .IH(32), .IW(IW), .MD(MD), .FPL(FPL), .FML(FML), .QL(QL), .SAFE_QUERY_GATE(SAFE_QUERY_GATE)) u_arr (
    .clk(ck), .rst_n(rn),
    .ql_v(ql_v), .ql_ready(ql_ready), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w),
    .i_valid(bv), .i_ready(a_ready), .i_last(blast), .i_kv(bkv), .i_ref(bref), .i_keep(bkeep), .i_index(bfirst),
    .i_key(bkey),
    .o_valid(o_v), .o_ready(o_take), .o_last(o_last), .o_kv(o_kv), .o_fault(o_fault), .o_score(o_score),
    .o_index(o_index), .protocol_fault(pfault));
  // ------------------------------------------------------------------ output pin register
  reg sv_; reg [SW-2:0] sd_;
  always @(posedge ck or negedge rn) if (!rn) sv_ <= 1'b0; else sv_ <= o_take;
  always @(posedge ck) if (o_take) sd_ <= {o_index, o_score, o_kv, o_fault, o_last[0]};
  assign s = {sd_, sv_};
endmodule
`default_nettype wire
