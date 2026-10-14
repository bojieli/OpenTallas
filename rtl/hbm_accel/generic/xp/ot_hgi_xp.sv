// SM.MATVEC x plane (owner 10-13 redesign): wave reader + record scheduler.  Budget and spec: el1013-hbm-redesign-smmv.log.
// ot_hgi_xp_rd   : one WAVE (8 consecutive sectors = 64 FP32) a cycle from the local 8-lane VM slice; sector s rides lane
//                  s[2:0]; x is 8-sector aligned (compiler obligation, fault otherwise) so lane i carries wave sector i.
//                  Per-lane credits == per-lane landing space; loads issue back to back with no gap cycle.
// ot_hgi_xp_sched: record window (in-order retire), verified x-slot reuse, load admission by range overlap, issue when
//                  the slot is complete.  Record N+1.. load under record N's weight stream.
// REAL JOIN (10-13, step 5): cmd_nsec 0 = a NULL wave (no lane, zero data: an x unit with no element inside K keeps its
//   place in the wave order); wave_rdy = pop hold from the pack stage (unit pacing, combinational from its tag head, T1 /
//   T2 abut); wave_pop = the pop this edge (wave_v one edge later); RQC > 0 = lane REQUEST credits (B2 lanestation queue,
//   rq_cr returns one a lane), on top of the landing credits.
module ot_hgi_xp_rd #(parameter integer CR = 16, parameter integer XQ = 4, parameter integer RQC = 0, parameter integer MUT_DROP = 0) (
    input  logic clk, input logic rst,
    input  logic cmd_v, output logic cmd_rdy, input logic [14:0] cmd_sec, input logic [10:0] cmd_nsec, input logic [3:0] cmd_id,
    output logic [7:0] rq_v, output logic [7:0][14:0] rq_sec,           // lane requests (pin flops)
    input  logic [7:0] rs_v, input logic [7:0][255:0] rs_d,             // lane responses, in order per lane
    input  logic [7:0] rq_cr, input logic wave_rdy, output logic wave_pop,
    output logic wave_v, output logic [2047:0] wave_d, output logic [3:0] wave_n, output logic wave_last,
    output logic [3:0] wave_id, output logic [7:0] wave_idx, output logic fault);
  // command queue (flops, XQ deep)
  logic [29:0] cq [XQ]; logic [$clog2(XQ):0] cq_n; logic [$clog2(XQ)-1:0] cq_r, cq_w;
  assign cmd_rdy = cq_n < XQ[$clog2(XQ):0];
  // cursor
  logic act; logic [14:0] c_sec; logic [10:0] c_rem; logic [3:0] c_id; logic [7:0] c_idx;
  logic [7:0][4:0] cr;                                                  // credits a lane
  logic [7:0] rs_vq; logic [7:0][255:0] rs_dq;                          // lane response pin flops
  logic [7:0][5:0] qc;                                                  // request credits a lane (RQC)
  // wave meta fifo (16)
  logic [16:0] mq [16]; logic [4:0] mq_n; logic [3:0] mq_r, mq_w;
  // landing fifos (16 deep storage, bounded to CR by credits)
  logic [255:0] lf [8][16]; logic [7:0][3:0] lf_r, lf_w; logic [7:0][4:0] lf_n;
  logic [3:0] n_now; logic last_now, can, take_cmd, pop;
  logic [3:0] m_n; logic m_last; logic [3:0] m_id; logic [7:0] m_idx;
  always_comb begin
    n_now = (c_rem > 11'd8) ? 4'd8 : c_rem[3:0];
    last_now = c_rem <= 11'd8;
    can = act && (mq_n < 5'd16);
    for (int l = 0; l < 8; l++) if (l < n_now && (cr[l] == 0 || (RQC != 0 && qc[l] == 0))) can = 1'b0;
    take_cmd = (cq_n != 0) && (!act || (can && last_now));
    {m_idx, m_id, m_last, m_n} = mq[mq_r];
    pop = (mq_n != 0) && wave_rdy;
    for (int l = 0; l < 8; l++) if (l < m_n && lf_n[l] == 0) pop = 1'b0;
    wave_pop = pop;
  end
  always_ff @(posedge clk) begin
    rq_v <= '0; wave_v <= 1'b0; rs_vq <= rs_v; rs_dq <= rs_d;
    if (cmd_v && cmd_rdy) begin
      cq[cq_w] <= {cmd_id, cmd_nsec, cmd_sec}; cq_w <= (cq_w == XQ-1) ? '0 : cq_w + 1'b1;
      if (cmd_sec[2:0] != 0 && cmd_nsec != 0) fault <= 1'b1;
    end
    cq_n <= cq_n + (cmd_v && cmd_rdy) - take_cmd;
    if (can) begin
      for (int l = 0; l < 8; l++) if (l < n_now) begin rq_v[l] <= 1'b1; rq_sec[l] <= c_sec + 15'(l); end
      mq[mq_w] <= {c_idx, c_id, last_now, n_now}; mq_w <= mq_w + 1'b1;
      c_sec <= c_sec + 15'd8; c_rem <= c_rem - 11'(n_now); c_idx <= c_idx + 1'b1;
      if (last_now) act <= 1'b0;
    end
    if (take_cmd) begin
      {c_id, c_rem, c_sec} <= cq[cq_r]; c_idx <= '0; act <= 1'b1; cq_r <= (cq_r == XQ-1) ? '0 : cq_r + 1'b1;
    end
    mq_n <= mq_n + can - pop;
    for (int l = 0; l < 8; l++) begin
      logic iss, lpop;
      iss = can && (l < n_now); lpop = pop && (l < m_n);
      cr[l] <= cr[l] - iss + lpop;
      qc[l] <= qc[l] - iss + rq_cr[l];
      if (rs_vq[l]) begin lf[l][lf_w[l]] <= rs_dq[l]; lf_w[l] <= lf_w[l] + 1'b1; if (lf_n[l] >= 5'(CR)) fault <= 1'b1; end
      lf_n[l] <= lf_n[l] + rs_vq[l] - lpop;
      if (lpop) lf_r[l] <= lf_r[l] + 1'b1;
      if (pop) wave_d[256*l +: 256] <= (l < m_n) ? lf[l][lf_r[l]] : '0;
    end
    if (pop) begin
      mq_r <= mq_r + 1'b1;
      wave_v <= !(MUT_DROP != 0 && m_idx == 8'd3 && m_id == 4'd2);
      wave_n <= m_n; wave_last <= m_last; wave_id <= m_id; wave_idx <= m_idx;
    end
    if (rst) begin
      cq_n <= '0; cq_r <= '0; cq_w <= '0; act <= 1'b0; mq_n <= '0; mq_r <= '0; mq_w <= '0; fault <= 1'b0;
      lf_r <= '0; lf_w <= '0; lf_n <= '0; rq_v <= '0; wave_v <= 1'b0; rs_vq <= '0;
      for (int l = 0; l < 8; l++) begin cr[l] <= 5'(CR); qc[l] <= 6'(RQC); end
    end
  end
endmodule

module ot_hgi_xp_sched #(parameter integer W = 8, parameter integer NS = 16, parameter integer MUT_RET = 0, parameter integer MUT_XRS = 0) (
    input  logic clk, input logic rst,
    input  logic rec_v, output logic rec_rdy, input logic rec_xr, input logic [6:0] rec_xb, input logic [7:0] rec_nxe,
    input  logic [14:0] rec_sec, input logic [10:0] rec_nsec,
    output logic cmd_v, input logic cmd_rdy, output logic [14:0] cmd_sec, output logic [10:0] cmd_nsec, output logic [3:0] cmd_id,
    input  logic done_v, input logic [3:0] done_id,                      // slot complete in every SM x store
    output logic iss_v, output logic [6:0] iss_xb, output logic [$clog2(W)-1:0] iss_seq,
    input  logic cdone_v,                                                // SM + publication done, in record order
    output logic ret_v, output logic [$clog2(W)-1:0] ret_seq, output logic fault);
  localparam integer PW = $clog2(W);
  typedef struct packed { logic xr; logic [6:0] xb; logic [7:0] nxe; logic [14:0] sec; logic [10:0] nsec; logic [3:0] sl; } ent_t;
  ent_t win [W]; logic [W-1:0] w_v, w_disp, w_iss, w_cd;
  logic [PW-1:0] ap, xp, ip, cp, rp;
  logic [NS-1:0] s_v, s_done; logic [6:0] s_xb [NS]; logic [7:0] s_nxe [NS];
  // dispatch decision, registered (stage 0 compares, stage 1 acts)
  logic d_v, d_ovl, d_hit, d_free_v; logic [3:0] d_hit_i, d_free_i; logic [NS-1:0] d_kill;
  logic c_ovl, c_hit, c_free_v; logic [3:0] c_hit_i, c_free_i; logic [NS-1:0] c_kill;
  ent_t e; logic [7:0] e_end;
  function automatic logic ovl(input logic [6:0] a, input logic [7:0] an, input logic [6:0] b, input logic [7:0] bn);
    return ({1'b0, a} < ({1'b0, b} + bn)) && ({1'b0, b} < ({1'b0, a} + an));
  endfunction
  always_comb begin
    e = win[xp]; c_ovl = 1'b0; c_hit = 1'b0; c_hit_i = '0; c_free_v = 1'b0; c_free_i = '0; c_kill = '0;
    for (int i = 0; i < W; i++) if (w_v[i] && w_disp[i] && ovl(e.xb, e.nxe, win[i].xb, win[i].nxe)) c_ovl = 1'b1;
    for (int i = NS-1; i >= 0; i--) begin
      if (s_v[i] && ((s_xb[i] == e.xb && s_nxe[i] == e.nxe) || MUT_XRS != 0)) begin c_hit = 1'b1; c_hit_i = 4'(i); end
      if (s_v[i] && ovl(e.xb, e.nxe, s_xb[i], s_nxe[i])) c_kill[i] = 1'b1;
      if (!s_v[i]) begin c_free_v = 1'b1; c_free_i = 4'(i); end
    end
  end
  assign rec_rdy = !w_v[ap];
  always_ff @(posedge clk) begin
    iss_v <= 1'b0; ret_v <= 1'b0;
    if (rec_v && rec_rdy) begin
      win[ap] <= '{xr: rec_xr, xb: rec_xb, nxe: rec_nxe, sec: rec_sec, nsec: rec_nsec, sl: '0};
      w_v[ap] <= 1'b1; w_disp[ap] <= 1'b0; w_iss[ap] <= 1'b0; w_cd[ap] <= 1'b0; ap <= ap + 1'b1;
      if ({1'b0, rec_xb} + rec_nxe > 9'd128 || rec_nxe == 0) fault <= 1'b1;
    end
    // x dispatch: stage 0
    d_v <= w_v[xp] && !w_disp[xp] && !d_v && !(cmd_v && !cmd_rdy);
    d_ovl <= c_ovl; d_hit <= c_hit; d_hit_i <= c_hit_i; d_free_v <= c_free_v; d_free_i <= c_free_i; d_kill <= c_kill;
    if (cmd_v && cmd_rdy) cmd_v <= 1'b0;
    // stage 1
    if (d_v) begin
      if (win[xp].xr) begin
        if (d_hit) begin win[xp].sl <= d_hit_i; win[xp].xb <= s_xb[d_hit_i]; w_disp[xp] <= 1'b1; xp <= xp + 1'b1; end
        else fault <= 1'b1;                                             // XR names no live slot: fail closed
      end else if (!d_ovl && d_free_v) begin                            // no unretired reader of the range: load
        s_v <= (s_v & ~d_kill) | (NS'(1) << d_free_i); s_done[d_free_i] <= 1'b0;
        s_xb[d_free_i] <= win[xp].xb; s_nxe[d_free_i] <= win[xp].nxe;
        win[xp].sl <= d_free_i; w_disp[xp] <= 1'b1; xp <= xp + 1'b1;
        cmd_v <= 1'b1; cmd_sec <= win[xp].sec; cmd_nsec <= win[xp].nsec; cmd_id <= d_free_i;
      end
    end
    if (done_v) s_done[done_id] <= 1'b1;
    if (w_v[ip] && w_disp[ip] && !w_iss[ip] && s_done[win[ip].sl] && !iss_v) begin
      iss_v <= 1'b1; iss_xb <= win[ip].xb; iss_seq <= ip; w_iss[ip] <= 1'b1; ip <= ip + 1'b1;
    end
    if (cdone_v) begin w_cd[cp] <= 1'b1; cp <= cp + 1'b1; if (!w_iss[cp]) fault <= 1'b1; end
    if (w_v[rp] && w_iss[rp] && (w_cd[rp] || MUT_RET != 0) && !ret_v) begin
      ret_v <= 1'b1; ret_seq <= rp; w_v[rp] <= 1'b0; w_disp[rp] <= 1'b0; rp <= rp + 1'b1;
    end
    if (rst) begin
      w_v <= '0; w_disp <= '0; w_iss <= '0; w_cd <= '0; ap <= '0; xp <= '0; ip <= '0; cp <= '0; rp <= '0;
      s_v <= '0; s_done <= '0; d_v <= 1'b0; cmd_v <= 1'b0; iss_v <= 1'b0; ret_v <= 1'b0; fault <= 1'b0;
    end
  end
endmodule
