`timescale 1ps/1fs
`default_nettype none
// CLAUDE hbm-indexer 2026-10-08: hfd_idx_sel -- the die's index query quantiser + local top-k + layer-20 candidate unit
// (x1 per die, a spine slot beside hfd_vm), fed by the four hfd_idx_score stack scorers.  Design note:
// claude-takeover-20261007/review_queue/hbm-indexer.md.  NOT routed (review gate).
//
// It is ot_hbm_accel_index_path (the exact, connected-bench-qualified parent: PASS_HBM_NATIVE_CONNECTED_INDEX) cut at
// its scorer: the same children, unchanged --
//   u_index_q   ot_hbm_accel_index_query   (FP32 query blocks -> ot_hdc_actquant FP4 -> 32 head loads)
//   u_topk      ot_hdc_v41x_sel            (Q 4 x W 16, K 512: local top-512, ties to the lower ID)
//   u_cand      ot_hbm_accel_index_candidate (layer 20: block maxima, newest-block pin, K 2048)
// -- with the scorer replaced by four remote score streams (one per stack = one selector quarter, contiguous ID
// ranges in quarter order, the parent's contract), each landing in a credit-flow FIFO.  Every die input lands in a
// flop, every die output leaves a flop.
//
// Ports:
//   fs   frame start from the cmdproc {keep_en, cand_en, k10, n_die14, rank7, pos20, gen4, job32, v}
//   qb   FP32 query block from the VM {w16, data1024, blk2, head5, v} (in order head-major, 128 blocks); qbr credit
//        pulse (one block freed from the 4-deep landing FIFO; the VM starts with 4 credits)
//   kin  keep bitmap of one stack {bits342, q2, v} (layers 24..36 cand mask; from the cand_apply path)
//   qo   q bus to the 4 stacks {payload568, kind2, v} (a registered copy each; with T = 4 the stack's taps chain it
//        on through their qx ports)
//   si   score beats from the 4T hfd_idx_score blocks (block 4.. quarter q, tap t at index q*T+t; tap t holds lanes
//        t*L .. t*L+L-1 of the quarter's 16-lane beat); sc credit pulses back
//   to   top-k out (to the VM / merge collective) {idx20 x16, val16 x16, ninf16, lv16, q2, last, v}; toc credit in
//   co   candidates out (layer 20) {blk17 x2, val16 x2, lv2, q2, last, v}; coc credit in
//   ev   {fault, done} (registered pulses / level)
module hfd_idx_sel #(
  parameter integer EXPOSE_QUARTER_LAST = 0,
  parameter integer T = 1,           // scorer blocks a stack (1: one hfd_idx_score L16; 4: four column taps L4)
  parameter integer LA = 6,          // score landing FIFO address bits (depth 64 = the scorer's CRED)
  parameter integer OCRED = 8,       // output credits (the VM landing depth) on to / co
  parameter integer READLAT = 1,     // opt-in macro output capture: 2
  parameter integer MEMV = 0,        // line memories: 0 behavioural, 1 SRAM macros (hfd_idx_mem)
  parameter integer L = 16 / T,      // lanes a scorer block
  parameter integer SW = 38 * L + 2  // score beat width a scorer block
) (
  input  wire          ck,
  input  wire          rst,
  input  wire [89:0]   fs,
  input  wire [1047:0] qb,
  output reg           qbr,
  input  wire [344:0]  kin,
  output wire [4*571-1:0]   qo,      // q bus, one registered copy per stack (taps chain it on: hfd_idx_score qx)
  input  wire [4*T*SW-1:0]  si,      // score beats, quarter-major
  output reg  [4*T-1:0]     sc,      // credit pulses
  output wire [611:0]  to,
  input  wire          toc,
  output wire [71:0]   co,
  output reg           co_quarter_last, // aligned co.v; legacy co.last remains whole-frame
  input  wire          coc,
  output reg  [1:0]    ev
);
  localparam integer Q = 4, W = 16, IW = 20;
`ifndef SYNTHESIS
  reg mut_sval, mut_qord;
  initial begin mut_sval = $test$plusargs("MUT_SVAL"); mut_qord = $test$plusargs("MUT_QORD"); end
`else
  localparam mut_sval = 1'b0, mut_qord = 1'b0;
`endif
  reg rs1, rs2;
  always @(posedge ck or negedge rst) if (!rst) {rs2, rs1} <= 2'b00; else {rs2, rs1} <= {rs1, 1'b1};
  wire rn = rs2;
  // ------------------------------------------------------------------ pin registers
  integer gi;
  reg fsv; reg [88:0] fsd;
  reg kv_; reg [343:0] kd_;
  reg qbv; reg [1046:0] qbd;
  reg [Q*T-1:0] siv; reg [SW-2:0] sid [0:Q*T-1];
  reg tocv, cocv;
  always @(posedge ck or negedge rn)
    if (!rn) begin fsv <= 1'b0; kv_ <= 1'b0; qbv <= 1'b0; siv <= '0; tocv <= 1'b0; cocv <= 1'b0; end
    else begin
      fsv <= fs[0]; kv_ <= kin[0]; qbv <= qb[0];
      for (gi = 0; gi < Q*T; gi = gi + 1) siv[gi] <= si[gi*SW];
      tocv <= toc; cocv <= coc;
    end
  always @(posedge ck) begin
    fsd <= fs[89:1]; kd_ <= kin[344:1]; qbd <= qb[1047:1];
    for (gi = 0; gi < Q*T; gi = gi + 1) sid[gi] <= si[gi*SW+1 +: SW-1];
  end
  // ------------------------------------------------------------------ frame
  reg active, fault, cand_en, keep_en;
  reg [31:0] job; reg [3:0] gen; reg [19:0] pos; reg [6:0] rank; reg [9:0] kk; reg [13:0] ndie;
  wire begin_frame = fsv && !active;
  // per-quarter key counts of the contiguous ranges (2,736 keys = 342 blocks a quarter)
  function automatic [11:0] nq_of(input [13:0] n, input integer qq);
    integer lo; begin lo = 2736 * qq;
      nq_of = (n <= lo) ? 12'd0 : ((n - lo >= 2736) ? 12'd2736 : 12'(n - lo)); end
  endfunction
  // ------------------------------------------------------------------ query: VM blocks -> quantiser -> q bus
  wire qfifo_ne; wire [1046:0] qfifo_rd; wire [2:0] qfifo_cnt;
  wire qblock_r;
  hfd_idx_fifo #(.W(1047), .AW(2)) u_qf (.ck(ck), .rst_n(rn), .we(qbv), .wd(qbd), .re(qblock_r && qfifo_ne),
    .rd(qfifo_rd), .ne(qfifo_ne), .cnt(qfifo_cnt));
  // qbr is a CREDIT pulse (one block freed); the VM holds 4 credits (the landing depth)
  always @(posedge ck or negedge rn) if (!rn) qbr <= 1'b0; else qbr <= qblock_r && qfifo_ne;
  wire qs_ready, qs_done, qs_fault, ql_v;
  wire [7:0] ql_head; wire [511:0] ql_codes; wire [31:0] ql_sc; wire [15:0] ql_w;
  reg cfg_pend, keep_pend; reg [1:0] keep_q; reg [341:0] keep_bits;
  wire ql_r = !cfg_pend && !keep_pend;
  ot_hbm_accel_index_query #(.ENABLE(1)) u_index_q (
    .clk(ck), .por_n(rn), .start(begin_frame), .start_ready(qs_ready),
    .block_v(qfifo_ne && active && !fault), .block_r(qblock_r), .block_head(qfifo_rd[4:0]), .block_number(qfifo_rd[6:5]),
    .block_data(qfifo_rd[1030:7]), .head_weight(qfifo_rd[1046:1031]),
    .ql_v(ql_v), .ql_r(ql_r), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w),
    .done(qs_done), .fault(qs_fault));
  // q bus: config (frame start) > keep bitmap > query heads; one registered beat a cycle per quarter
  reg [Q-1:0] qov; reg [1:0] qok [0:Q-1]; reg [567:0] qop [0:Q-1];
  integer g;
  always @(posedge ck or negedge rn) begin
    if (!rn) begin qov <= 4'd0; cfg_pend <= 1'b0; keep_pend <= 1'b0; end
    else begin
      qov <= 4'd0;
      if (kv_) begin keep_pend <= 1'b1; keep_q <= kd_[1:0]; keep_bits <= kd_[343:2]; end
      if (cfg_pend) begin
        cfg_pend <= 1'b0;
        for (g = 0; g < Q; g = g + 1) begin
          qov[g] <= 1'b1; qok[g] <= 2'd1;
          qop[g] <= {537'd0, keep_en, nq_of(ndie, g), 11'(342 * g), rank};
        end
      end else if (keep_pend) begin
        keep_pend <= 1'b0;
        qov[keep_q] <= 1'b1; qok[keep_q] <= 2'd2; qop[keep_q] <= {226'd0, keep_bits};
      end else if (ql_v) begin
        for (g = 0; g < Q; g = g + 1) begin
          qov[g] <= 1'b1; qok[g] <= 2'd0; qop[g] <= {ql_head, ql_codes, ql_sc, ql_w};
        end
      end
      if (begin_frame) cfg_pend <= 1'b1;
    end
  end
  generate for (genvar gb = 0; gb < Q; gb = gb + 1) begin : gqo
    assign qo[gb*571 +: 571] = {qop[gb], qok[gb], qov[gb]};
  end endgenerate
  // ------------------------------------------------------------------ score landing (credit flow) and issue
  // one FIFO per scorer block; a quarter's beat issues when all T taps hold it (the taps' beats of one quarter are
  // the same 16 consecutive keys, lanes t*L.. of tap t): the atomic beat handshake of ot_hdc_v41x_idx_array, across
  // the die
  wire [Q*T-1:0] lne; wire [SW-2:0] lrd [0:Q*T-1];
  wire [Q-1:0] sel_ready, cand_ready;
  wire [Q-1:0] fire;
  wire [Q-1:0] f_last; wire [Q*W-1:0] f_lv, f_fault; wire [Q*W*16-1:0] f_val; wire [Q*W*IW-1:0] f_idx;
  wire [Q*T-1:0] pop;
  genvar gq, gt;
  generate for (gq = 0; gq < Q; gq = gq + 1) begin : gl
    wire [T-1:0] ne_q;
    for (gt = 0; gt < T; gt = gt + 1) begin : gt_
      localparam integer B = gq * T + gt;
      wire [LA:0] cnt_;
      hfd_idx_fifo #(.W(SW-1), .AW(LA)) u_l (.ck(ck), .rst_n(rn), .we(siv[B]), .wd(sid[B]), .re(pop[B]),
        .rd(lrd[B]), .ne(lne[B]), .cnt(cnt_));
      assign ne_q[gt] = lne[B];
      assign pop[B] = fire[gq];
      // tap beat {idx20 x L, score16 x L, kv L, fault L, last}
      assign f_fault[W*gq + L*gt +: L] = lrd[B][L:1];
      assign f_lv[W*gq + L*gt +: L] = lrd[B][2*L:L+1];
      assign f_val[W*16*gq + 16*L*gt +: 16*L] = lrd[B][18*L:2*L+1] ^
        ((mut_sval && gq == 1) ? {L{16'h0001}} : {16*L{1'b0}});
      assign f_idx[W*IW*gq + IW*L*gt +: IW*L] = lrd[B][38*L:18*L+1];
    end
    assign f_last[gq] = lrd[gq*T][0];
    assign fire[gq] = (&ne_q) && active && !fault && sel_ready[gq] && (!cand_en || cand_ready[gq]);
  end endgenerate
  always @(posedge ck or negedge rn) if (!rn) sc <= '0; else sc <= pop;
  // ------------------------------------------------------------------ local top-k (unchanged ot_hdc_v41x_sel)
  wire [Q-1:0] o_v, o_last, o_r; wire [Q*W-1:0] o_lv, o_ninf; wire [Q*W*16-1:0] o_val; wire [Q*W*IW-1:0] o_idx;
  wire [Q-1:0] m_we, m_re; wire [Q*8-1:0] m_wa, m_ra; wire [Q*W*(17+IW)-1:0] m_wd, m_rd;
  wire rep, ovf, sel_busy; wire [Q*3*9-1:0] sel_stats;
  ot_hdc_v41x_sel #(.Q(Q), .W(W), .IW(IW), .K(512), .AW(8), .READLAT(READLAT)) u_topk (
    .clk(ck), .rst_n(rn), .in_valid(fire), .in_ready(sel_ready), .in_last(f_last), .in_lv(f_lv), .in_val(f_val),
    .in_idx(f_idx), .in_k(kk),
    .out_valid(o_v), .out_ready(o_r), .out_last(o_last), .out_lv(o_lv), .out_val(o_val), .out_idx(o_idx),
    .out_ninf(o_ninf),
    .mem_we(m_we), .mem_waddr(m_wa), .mem_wdata(m_wd), .mem_re(m_re), .mem_raddr(m_ra), .mem_rdata(m_rd),
    .rep_req(rep), .ovf(ovf), .busy(sel_busy), .stats(sel_stats));
  generate for (gq = 0; gq < Q; gq = gq + 1) begin : gm
    hfd_idx_mem #(.W(W*(17+IW)), .AW(8), .MEMV(MEMV), .READLAT(READLAT)) u_m (.ck(ck), .we(m_we[gq]), .wa(m_wa[8*gq +: 8]),
      .wd(m_wd[W*(17+IW)*gq +: W*(17+IW)]), .re(m_re[gq]), .ra(m_ra[8*gq +: 8]), .rd(m_rd[W*(17+IW)*gq +: W*(17+IW)]));
  end endgenerate
  // ------------------------------------------------------------------ layer-20 candidates (unchanged wrapper)
  wire [Q-1:0] c_v, c_last, c_r; wire [Q*2-1:0] c_lv; wire [Q*2*16-1:0] c_val; wire [Q*2*17-1:0] c_blk;
  wire [Q-1:0] cm_we, cm_re; wire [Q*10-1:0] cm_wa, cm_ra; wire [Q*2*34-1:0] cm_wd, cm_rd;
  wire crep, covf, cand_busy; wire [Q*3*11-1:0] cand_stats;
  ot_hbm_accel_index_candidate #(.ENABLE(1), .READLAT(READLAT)) u_cand (
    .clk(ck), .rst_n(rn), .held_valid(active && !fault && cand_en),
    .held_job(job), .held_gen(gen), .held_pos(pos), .held_rank(rank),
    .out_job(), .out_gen(), .out_pos(), .out_rank(),
    .in_valid(fire & {Q{cand_en}}), .in_ready(cand_ready), .in_last(f_last), .in_lv(f_lv), .in_val(f_val),
    .in_idx(f_idx), .in_k(12'd2048),
    .out_valid(c_v), .out_ready(c_r), .out_last(c_last), .out_lv(c_lv), .out_val(c_val), .out_blk(c_blk),
    .mem_we(cm_we), .mem_waddr(cm_wa), .mem_wdata(cm_wd), .mem_re(cm_re), .mem_raddr(cm_ra), .mem_rdata(cm_rd),
    .rep_req(crep), .ovf(covf), .busy(cand_busy), .stats(cand_stats));
  generate for (gq = 0; gq < Q; gq = gq + 1) begin : gc
    hfd_idx_mem #(.W(68), .AW(10), .MEMV(MEMV), .READLAT(READLAT)) u_m (.ck(ck), .we(cm_we[gq]), .wa(cm_wa[10*gq +: 10]), .wd(cm_wd[68*gq +: 68]),
      .re(cm_re[gq]), .ra(cm_ra[10*gq +: 10]), .rd(cm_rd[68*gq +: 68]));
  end endgenerate
  // ------------------------------------------------------------------ output serialisers (quarter order), credits
  reg [1:0] oq, cq; reg odone, cdone;
  reg [3:0] ocr, ccr;
  wire o_go = active && !odone && (ocr != 4'd0);
  wire c_go = active && cand_en && !cdone && (ccr != 4'd0);
  assign o_r = {3'd0, o_go} << oq;
  assign c_r = {3'd0, c_go} << cq;
  wire o_take = o_go && o_v[oq];
  wire c_take = c_go && c_v[cq];
  reg tv; reg [610:0] td;
  reg cv_; reg [70:0] cd_;
  always @(posedge ck or negedge rn) if (!rn) begin tv <= 1'b0; cv_ <= 1'b0; end else begin tv <= o_take; cv_ <= c_take; end
  always @(posedge ck or negedge rn)
    if (!rn) co_quarter_last <= 1'b0;
    else co_quarter_last <= EXPOSE_QUARTER_LAST && c_take && c_last[cq];
  always @(posedge ck) begin
    if (o_take) td <= {o_idx[W*IW*oq +: W*IW], o_val[W*16*oq +: W*16], o_ninf[W*oq +: W], o_lv[W*oq +: W], oq,
                       o_last[oq] && oq == 2'd3};
    if (c_take) cd_ <= {c_blk[34*cq +: 34], c_val[32*cq +: 32], c_lv[2*cq +: 2], cq, c_last[cq] && cq == 2'd3};
  end
  assign to = {td, tv};
  assign co = {cd_, cv_};
  // ------------------------------------------------------------------ frame control
  always @(posedge ck or negedge rn) begin
    if (!rn) begin
      active <= 1'b0; fault <= 1'b0; ev <= 2'd0; oq <= 2'd0; cq <= 2'd0; odone <= 1'b0; cdone <= 1'b0;
      ocr <= 4'(OCRED); ccr <= 4'(OCRED); cand_en <= 1'b0; keep_en <= 1'b0;
    end else begin
      ev[0] <= 1'b0;
      ocr <= ocr - {3'd0, o_take} + {3'd0, tocv};
      ccr <= ccr - {3'd0, c_take} + {3'd0, cocv};
      if (begin_frame) begin
        active <= 1'b1; oq <= mut_qord ? 2'd1 : 2'd0; cq <= 2'd0; odone <= 1'b0; cdone <= 1'b0;
        job <= fsd[31:0]; gen <= fsd[35:32]; pos <= fsd[55:36]; rank <= fsd[62:56]; ndie <= fsd[76:63];
        kk <= fsd[86:77]; cand_en <= fsd[87]; keep_en <= fsd[88];
        if (!qs_ready || fsd[62:56] >= 7'd96) fault <= 1'b1;
      end
      if (o_take && o_last[oq]) begin
        if (oq == 2'd3) odone <= 1'b1;
        else if (mut_qord) oq <= (oq == 2'd1) ? 2'd0 : (oq == 2'd0) ? 2'd2 : oq + 2'd1;
        else oq <= oq + 2'd1;
      end
      if (c_take && c_last[cq]) begin if (cq == 2'd3) cdone <= 1'b1; else cq <= cq + 2'd1; end
      if (qs_fault || rep || ovf || crep || covf) fault <= 1'b1;
      for (g = 0; g < Q; g = g + 1) if (fire[g] && |(f_fault[W*g +: W] & f_lv[W*g +: W])) fault <= 1'b1;
      for (g = 0; g < Q*T; g = g + 1) if (fire[g / T] && lrd[g][0] != lrd[(g / T) * T][0]) fault <= 1'b1;  // taps in step
      if (active && odone && (cdone || !cand_en) && !sel_busy && !cand_busy) begin active <= 1'b0; ev[0] <= 1'b1; end
      ev[1] <= fault;
    end
  end
endmodule
`default_nettype wire
