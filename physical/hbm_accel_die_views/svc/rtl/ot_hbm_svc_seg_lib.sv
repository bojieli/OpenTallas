`timescale 1ps/1fs
`default_nettype none
// CLAUDE HBM-ABSTRACTS (svcidx) 2026-10-06: units of the SEGMENTED stream service (svc split into ~1 mm segment
// masters, coordinator decision).  Same function as ot_hbm_svc_core (that file supplies ot_svc_vpipe / ot_svc_fifo /
// ot_svc_asm / ot_svc_fclk_buf); the generator physical/hbm_accel_die_views/svc/gen_svc_seg.py places one unit where
// its pins / partners are and joins units only through wire-stage chains (ot_svc_vpipe portions, every segment face
// register-to-register).  Every one-cycle loop stays inside one unit:
//   * SM arbiter (ot_svs_arb): the four PC busy bits live AT the arbiter (were at the PC pins, up to 800 um and, for
//     the e-command, 2.9 mm apart in one cycle); the issue goes to the PC pin unit through a chain (+ its stages);
//   * e command (ot_svs_e): dispatched by kind at the e port into three chains (W unit, KV owner arbiter, IK owner
//     arbiter), one command outstanding per kind (was one outstanding in total); per-port order is unchanged;
//   * W lane room (w_room) reaches the W unit through a chain (was a 1.9 mm one-cycle path).
// Default-off: nothing outside physical/hbm_accel_die_views/svc instantiates these modules.

module ot_svs_rsync (input wire ck, input wire rst, output wire rn);
  reg [1:0] rst_s;      // named rst_s: the io_vclk SDC reset-release multicycle (rst_mcp2) applies
  always @(posedge ck or negedge rst) if (!rst) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
  assign rn = rst_s[1];
endmodule

// segment-local "ready after reset" (kr_rdy / wr_rdy level and the response capture enable)
module ot_svs_rdy (input wire ck, input wire rn, output wire rdy_q, output wire rdy_q2);
  reg a, b;
  always @(posedge ck or negedge rn) if (!rn) begin a <= 1'b0; b <= 1'b0; end else begin a <= 1'b1; b <= a; end
  assign rdy_q = a; assign rdy_q2 = b;
endmodule

// SM request port: capture + FIFO + one request outstanding on the request chain (token returns on tk_back)
module ot_svs_smport #(parameter integer FWD = 0) (
  input wire ck, input wire rst, input wire rn,
  input wire [41:0] q_d, input wire q_v, input wire q_fclk, output wire q_rdy,
  output wire iv, output wire [41:0] id, input wire tk_back);
  wire ine; reg pend;
  generate if (FWD) begin : fwd
    wire full_, empty_; wire [2:0] fr_;
    reg fv; reg [41:0] fd;
    wire wck = ~q_fclk;
    always @(posedge wck or negedge rst) if (!rst) fv <= 1'b0; else fv <= q_v;
    always @(posedge wck) fd <= q_d;
    ot_hbm_accel_cdc_fifo #(.W(42), .AW(2)) u_x (.wclk(wck), .wrst_n(rst), .we(fv),
      .wdata(fd), .full(full_), .rd_freed(fr_), .rclk(ck), .rrst_n(rn), .re(iv), .rdata(id), .empty(empty_));
    assign ine = !empty_;
    assign q_rdy = 1'b0;
  end else begin : loc
    reg v_q; reg [41:0] d_q; wire rdy_;
    reg v_r, rdy_d; reg [41:0] d_r;
    always @(posedge ck or negedge rn) if (!rn) begin v_r <= 1'b0; rdy_d <= 1'b0; end else begin v_r <= q_v; rdy_d <= rdy_; end
    always @(posedge ck) d_r <= q_d;
    always @(posedge ck or negedge rn) if (!rn) v_q <= 1'b0; else v_q <= v_r && rdy_d;
    always @(posedge ck) d_q <= d_r;
    ot_svc_fifo #(.W(42), .AW(3), .AF(5)) u_f (.ck(ck), .rst_n(rn), .we(v_q), .wd(d_q), .rdy(rdy_),
      .re(iv), .rd(id), .ne(ine));
    assign q_rdy = rdy_;
  end endgenerate
  assign iv = ine && !pend;
  always @(posedge ck or negedge rn) if (!rn) pend <= 1'b0; else if (iv) pend <= 1'b1; else if (tk_back) pend <= 1'b0;
endmodule

// SM arbiter: request hold, round robin over its four PCs, PC busy bits, KV / IK command holds (owner of KV_PC /
// IK_PC only), issue registers {t17, ln4, a30} per PC (+ valid) into the issue chains
module ot_svs_arb #(parameter integer S = 0, parameter integer KVI = -1, parameter integer IKI = -1) (
  input wire ck, input wire rn,
  input wire sv, input wire [41:0] sd, output wire rq_take,
  input wire kvc_v, input wire [39:0] kvc_d, output wire kv_take,
  input wire ikc_v, input wire [39:0] ikc_d, output wire ik_take,
  input wire [3:0] done,
  output wire [3:0] iss_v, output wire [4*51-1:0] iss_d);
  reg hv; reg [41:0] hd;
  always @(posedge ck or negedge rn) if (!rn) hv <= 1'b0; else if (sv) hv <= 1'b1; else if (rq_take) hv <= 1'b0;
  always @(posedge ck) if (sv) hd <= sd;
  reg kh, ih; reg [39:0] kd, idd;
  reg [3:0] busy; reg [1:0] rr;
  wire kvt = (KVI >= 0) && kh && !busy[KVI < 0 ? 0 : KVI];
  wire ikt = (IKI >= 0) && ih && !busy[IKI < 0 ? 0 : IKI];
  assign kv_take = kvt; assign ik_take = ikt;
  always @(posedge ck or negedge rn)
    if (!rn) begin kh <= 1'b0; ih <= 1'b0; end
    else begin
      if (kvc_v) kh <= 1'b1; else if (kvt) kh <= 1'b0;
      if (ikc_v) ih <= 1'b1; else if (ikt) ih <= 1'b0;
    end
  always @(posedge ck) begin if (kvc_v) kd <= kvc_d; if (ikc_v) idd <= ikc_d; end
  wire [3:0] fr;
  genvar p;
  generate for (p = 0; p < 4; p = p + 1) begin : gf
    assign fr[p] = !busy[p] && !((p == KVI) && kvt) && !((p == IKI) && ikt);
  end endgenerate
  wire [7:0] f2 = {fr, fr};
  wire [3:0] rot = f2 >> rr;
  wire [1:0] off = rot[0] ? 2'd0 : rot[1] ? 2'd1 : rot[2] ? 2'd2 : 2'd3;
  wire [1:0] sel = rr + off;
  assign rq_take = hv && (|fr);
  reg [3:0] iv_r; reg [50:0] id_r [0:3];
  generate for (p = 0; p < 4; p = p + 1) begin : gi
    wire smi = rq_take && (sel == p);
    wire ckv = (p == KVI) && kvt, cik = (p == IKI) && ikt;
    wire any = ckv || cik || smi;
    always @(posedge ck or negedge rn)
      if (!rn) begin iv_r[p] <= 1'b0; busy[p] <= 1'b0; end
      else begin
        iv_r[p] <= any;
        if (any) busy[p] <= 1'b1; else if (done[p]) busy[p] <= 1'b0;
      end
    always @(posedge ck)
      if (ckv) id_r[p] <= {2'b01, 5'd0, kd[39:30], 4'd4, kd[29:0]};
      else if (cik) id_r[p] <= {2'b10, 5'd0, idd[39:30], 4'd4, idd[29:0]};
      else if (smi) id_r[p] <= {2'b00, 3'(S), 2'b00, hd[41:32], 4'd5, hd[29:0]};
    assign iss_v[p] = iv_r[p]; assign iss_d[p*51 +: 51] = id_r[p];
  end endgenerate
  always @(posedge ck or negedge rn) if (!rn) rr <= 2'd0; else if (rq_take) rr <= sel + 2'd1;
endmodule

// PC pin unit: K request present-and-drop against the registered k_rdy, response raw capture + aligned register
module ot_svs_pc (
  input wire ck, input wire rn, input wire rdy_q2,
  input wire iss_v, input wire [50:0] iss_d,
  output wire k_v, input wire k_rdy, output wire [29:0] k_addr, output wire [3:0] k_len, output wire [16:0] k_tag,
  input wire kr_v, input wire [16:0] kr_tag, input wire [3:0] kr_beat, input wire [255:0] kr_data,
  output wire b_v, output wire [16:0] b_t, output wire [3:0] b_b, output wire [255:0] b_d);
  reg v, pend, v_d, k_rdy_q; reg [29:0] a; reg [3:0] ln; reg [16:0] t;
  always @(posedge ck or negedge rn)
    if (!rn) begin v <= 1'b0; pend <= 1'b0; v_d <= 1'b0; k_rdy_q <= 1'b0; end
    else begin
      k_rdy_q <= k_rdy; v_d <= v;
      if (iss_v) begin v <= 1'b1; pend <= 1'b1; end
      else if (v) v <= 1'b0;
      else if (pend && v_d && k_rdy_q) pend <= 1'b0;
      else if (pend && !v_d) v <= 1'b1;
    end
  always @(posedge ck) if (iss_v) {t, ln, a} <= iss_d;
  assign k_v = v; assign k_addr = a; assign k_len = ln; assign k_tag = t;
  reg kr_v_q, bv; reg [16:0] t_r, bt; reg [3:0] bb_r, bb; reg [255:0] d_r, bd;
  always @(posedge ck or negedge rn) if (!rn) begin kr_v_q <= 1'b0; bv <= 1'b0; end else begin kr_v_q <= kr_v; bv <= kr_v_q && rdy_q2; end
  always @(posedge ck) begin t_r <= kr_tag; bb_r <= kr_beat; d_r <= kr_data; bt <= t_r; bb <= bb_r; bd <= d_r; end
  assign b_v = bv; assign b_t = bt; assign b_b = bb; assign b_d = bd;
endmodule

// SM line assembler: four PC response chains + the W lane chain -> one line {data1088, tag10, v}
// SLOT = 1 (coordinator 2026-10-06 18:55, margin rule on v2 routes: full -> round-robin select -> 5:1 x 1088 mux -> ld
// at -296..-488 ps @833 over a ~1 mm segment): each assembler hands its line to its own slot register when the slot is
// empty (take = full & ~slot valid; an assembler needs >= 5 beats per line, so the refill bubble is never exposed); the
// round-robin merge then selects among slot valids only (all merge logic local, slots registered).  +1 cycle on every
// K / W line.  SLOT = 0 is the original single-cycle merge.
module ot_svs_asm #(parameter integer SLOT = 0) (
  input wire ck, input wire rn,
  input wire [3:0] sv, input wire [4*277-1:0] sq, input wire wsv, input wire [270:0] wsq,
  output wire [3:0] k_take, output wire w_take, output wire [1098:0] line);
  wire [4:0] full; wire [9:0] tg [0:4]; wire [1279:0] dt [0:4];
  genvar p;
  generate for (p = 0; p < 4; p = p + 1) begin : ga
    wire [12:0] t13;
    if (SLOT >= 4) begin : gr
    ot_svs_asm_r #(.NB(5), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv[p]), .btag(sq[p*277+260 +: 13]),
      .bbeat({1'b0, sq[p*277+256 +: 4]}), .bdata(sq[p*277 +: 256]), .full(full[p]), .tag(t13), .data(dt[p]),
      .take(k_take[p]));
    end else begin : gp
    ot_svc_asm #(.NB(5), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv[p]), .btag(sq[p*277+260 +: 13]),
      .bbeat({1'b0, sq[p*277+256 +: 4]}), .bdata(sq[p*277 +: 256]), .full(full[p]), .tag(t13), .data(dt[p]),
      .take(k_take[p]));
    end
    assign tg[p] = t13[9:0];
  end endgenerate
  wire [9:0] t10;
  generate if (SLOT >= 4) begin : gwr
  ot_svs_asm_r #(.NB(5), .TW(10)) u_wa (.ck(ck), .rst_n(rn), .bv(wsv), .btag(wsq[270:261]), .bbeat(wsq[260:256]),
    .bdata(wsq[255:0]), .full(full[4]), .tag(t10), .data(dt[4]), .take(w_take));
  end else begin : gwp
  ot_svc_asm #(.NB(5), .TW(10)) u_wa (.ck(ck), .rst_n(rn), .bv(wsv), .btag(wsq[270:261]), .bbeat(wsq[260:256]),
    .bdata(wsq[255:0]), .full(full[4]), .tag(t10), .data(dt[4]), .take(w_take));
  end endgenerate
  assign tg[4] = t10;
  reg [2:0] lr;
  reg lv, lv2; reg [9:0] lt; reg [1087:0] ld;
  wire [4:0] cand;                        // merge candidates: assembler full flags (SLOT 0) or slot valids (SLOT 1)
  wire [9:0] fx = {cand, cand};
  wire [4:0] rot = fx >> lr;
  wire [3:0] off = rot[0] ? 4'd0 : rot[1] ? 4'd1 : rot[2] ? 4'd2 : rot[3] ? 4'd3 : 4'd4;
  wire [3:0] s0 = {1'b0, lr} + off;
  wire [2:0] sel = (s0 >= 4'd5) ? 3'(s0 - 4'd5) : s0[2:0];
  wire any = |cand;
  always @(posedge ck or negedge rn)
    if (!rn) begin lv <= 1'b0; lr <= 3'd0; end
    else begin lv <= any; if (any) lr <= (sel == 3'd4) ? 3'd0 : sel + 3'd1; end
  generate if (SLOT == 4) begin : gs4
    // views agent 2026-10-07 (SE_s7 d6f9d25a1 SLOT 2 route -45 ps, owner: stage EVERY failing class): assembler inputs
    // registered with a pre-decoded one-hot beat enable in kept copies (ot_svs_asm_r, +1 cycle; chain -> b[beat] -45),
    // slot write enables from 8 kept sv_q copies (sv_q -> sd 1,088 x 5 loads, -43), one-hot grant in 8 kept copies with
    // per-chunk line enables (gq -> ld -34), one more line register before the port (SLOT 3).  +3 cycles per K/W line vs
    // SLOT 1 (+2 vs SLOT 2), same order.
    reg [4:0] sv_q, gq; (* keep *) reg [4:0] svr [0:7]; (* keep *) reg [4:0] gqr [0:7];
    reg [9:0] st [0:4]; reg [1087:0] sd [0:4];
    wire [4:0] fill = full & ~sv_q;
    wire [4:0] drain = any ? (5'd1 << sel) : 5'd0;
    assign cand = sv_q;
    assign k_take = fill[3:0];
    assign w_take = fill[4];
    integer r;
    always @(posedge ck or negedge rn)
      if (!rn) begin sv_q <= 5'd0; gq <= 5'd0; for (r = 0; r < 8; r = r + 1) begin svr[r] <= 5'd0; gqr[r] <= 5'd0; end end
      else begin
        sv_q <= (sv_q & ~drain) | fill; gq <= drain;
        for (r = 0; r < 8; r = r + 1) begin svr[r] <= (sv_q & ~drain) | fill; gqr[r] <= drain; end
      end
    for (p = 0; p < 5; p = p + 1) begin : gsl
      always @(posedge ck) if (fill[p]) st[p] <= tg[p];
      for (genvar c = 0; c < 8; c = c + 1) begin : gc
        always @(posedge ck) if (full[p] & ~svr[c][p]) sd[p][c*136 +: 136] <= dt[p][c*136 +: 136];
      end
    end
    reg [1087:0] dsel; reg [9:0] tsel; integer q;
    always @* begin
      dsel = 1088'd0; tsel = 10'd0;
      for (q = 0; q < 5; q = q + 1) begin
        for (r = 0; r < 8; r = r + 1) dsel[r*136 +: 136] = dsel[r*136 +: 136] | ({136{gqr[r][q]}} & sd[q][r*136 +: 136]);
        tsel = tsel | ({10{gq[q]}} & st[q]);
      end
    end
    reg lv2a; reg [9:0] lta; reg [1087:0] lda;
    always @(posedge ck or negedge rn) if (!rn) begin lv2a <= 1'b0; lv2 <= 1'b0; end else begin lv2a <= |gq; lv2 <= lv2a; end
    always @(posedge ck) if (|gq) lta <= tsel;
    for (genvar c = 0; c < 8; c = c + 1) begin : gl
      always @(posedge ck) if (|gqr[c]) lda[c*136 +: 136] <= dsel[c*136 +: 136];
    end
    always @(posedge ck) begin lt <= lta; ld <= lda; end
  end else if (SLOT == 3) begin : gs3
    // views agent 2026-10-07 (SE_s7 aggressive variant, owner LAUNCH IMMEDIATELY: stages on every class within 100 ps):
    // SLOT 2 + the one-hot grant held in 8 KEPT copies (each drives 136 of the 1,088 data bits: no 1,088-load net on the
    // grant) + the line re-registered once more before the port (ld -> l7 was +83.5 ps over 7 levels).  +2 cycles per
    // K/W line vs SLOT 1 (+1 vs SLOT 2), same order.
    reg [4:0] sv_q; (* keep *) reg [4:0] gqr [0:7]; reg [4:0] gq; reg [9:0] st [0:4]; reg [1087:0] sd [0:4];
    wire [4:0] fill = full & ~sv_q;
    wire [4:0] drain = any ? (5'd1 << sel) : 5'd0;
    assign cand = sv_q;
    assign k_take = fill[3:0];
    assign w_take = fill[4];
    integer r;
    always @(posedge ck or negedge rn)
      if (!rn) begin sv_q <= 5'd0; gq <= 5'd0; for (r = 0; r < 8; r = r + 1) gqr[r] <= 5'd0; end
      else begin sv_q <= (sv_q & ~drain) | fill; gq <= drain; for (r = 0; r < 8; r = r + 1) gqr[r] <= drain; end
    for (p = 0; p < 5; p = p + 1) begin : gsl
      always @(posedge ck) if (fill[p]) begin st[p] <= tg[p]; sd[p] <= dt[p][1087:0]; end
    end
    reg [1087:0] dsel; reg [9:0] tsel; integer q;
    always @* begin
      dsel = 1088'd0; tsel = 10'd0;
      for (q = 0; q < 5; q = q + 1) begin
        for (r = 0; r < 8; r = r + 1) dsel[r*136 +: 136] = dsel[r*136 +: 136] | ({136{gqr[r][q]}} & sd[q][r*136 +: 136]);
        tsel = tsel | ({10{gq[q]}} & st[q]);
      end
    end
    reg lv2a; reg [9:0] lta; reg [1087:0] lda;
    always @(posedge ck or negedge rn) if (!rn) begin lv2a <= 1'b0; lv2 <= 1'b0; end else begin lv2a <= |gq; lv2 <= lv2a; end
    always @(posedge ck) if (|gq) begin lta <= tsel; lda <= dsel; end
    always @(posedge ck) begin lt <= lta; ld <= lda; end
  end else if (SLOT == 2) begin : gs2
    // views agent (SE_s7 70a27c406: lr -> rot -> off -> mod-5 sel -> 5:1 x 1088 mux -> ld, 25 levels, -267.6 ps over
    // 400 endpoints): SLOT 1 plus a REGISTERED one-hot grant: the arbitration (5-bit) lands in gq, the slot data are
    // read one cycle later by an AND-OR over gq (a drained slot is refilled no earlier than the edge that reads it, so
    // the read sees the granted line).  +1 cycle per K/W line, same order (round robin over slot valids).
    reg [4:0] sv_q, gq; reg [9:0] st [0:4]; reg [1087:0] sd [0:4];
    wire [4:0] fill = full & ~sv_q;
    wire [4:0] drain = any ? (5'd1 << sel) : 5'd0;
    assign cand = sv_q;
    assign k_take = fill[3:0];
    assign w_take = fill[4];
    always @(posedge ck or negedge rn)
      if (!rn) begin sv_q <= 5'd0; gq <= 5'd0; end
      else begin sv_q <= (sv_q & ~drain) | fill; gq <= drain; end
    for (p = 0; p < 5; p = p + 1) begin : gsl
      always @(posedge ck) if (fill[p]) begin st[p] <= tg[p]; sd[p] <= dt[p][1087:0]; end
    end
    reg [1087:0] dsel; reg [9:0] tsel; integer q;
    always @* begin
      dsel = 1088'd0; tsel = 10'd0;
      for (q = 0; q < 5; q = q + 1) begin dsel = dsel | ({1088{gq[q]}} & sd[q]); tsel = tsel | ({10{gq[q]}} & st[q]); end
    end
    always @(posedge ck or negedge rn) if (!rn) lv2 <= 1'b0; else lv2 <= |gq;
    always @(posedge ck) if (|gq) begin lt <= tsel; ld <= dsel; end
  end else if (SLOT) begin : gs
    reg [4:0] sv_q; reg [9:0] st [0:4]; reg [1087:0] sd [0:4];
    wire [4:0] fill = full & ~sv_q;
    wire [4:0] drain = any ? (5'd1 << sel) : 5'd0;
    assign cand = sv_q;
    assign k_take = fill[3:0];
    assign w_take = fill[4];
    always @(posedge ck or negedge rn)
      if (!rn) sv_q <= 5'd0;
      else sv_q <= (sv_q & ~drain) | fill;
    for (p = 0; p < 5; p = p + 1) begin : gsl
      always @(posedge ck) if (fill[p]) begin st[p] <= tg[p]; sd[p] <= dt[p][1087:0]; end
    end
    always @(posedge ck) if (any) begin lt <= st[sel]; ld <= sd[sel]; end
  end else begin : g0
    assign cand = full;
    for (p = 0; p < 4; p = p + 1) begin : gt
      assign k_take[p] = any && (sel == p);
    end
    assign w_take = any && (sel == 3'd4);
    always @(posedge ck) if (any) begin lt <= tg[sel]; ld <= dt[sel][1087:0]; end
  end endgenerate
  assign line = {ld, lt, (SLOT >= 2) ? lv2 : lv};
endmodule

// KV (KV = 1) / index-key (KV = 0) assembler at its port
module ot_svs_kvasm #(parameter integer KV = 1) (
  input wire ck, input wire rn, input wire sv, input wire [276:0] sq,
  output wire dn, output wire [1037:0] kv, output wire [1023:0] ik);
  wire full_; wire [12:0] t13; wire [1023:0] dd;
  ot_svc_asm #(.NB(4), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv), .btag(sq[272:260]), .bbeat({1'b0, sq[259:256]}),
    .bdata(sq[255:0]), .full(full_), .tag(t13), .data(dd), .take(1'b1));
  reg v; reg [12:0] t; reg [1023:0] d;
  always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= full_;
  always @(posedge ck) if (full_) begin t <= t13; d <= dd; end
  assign kv = KV ? {d, t, v} : 1038'd0;
  assign ik = d;
  assign dn = full_;
endmodule

// e command port: falling-edge capture + two-clock FIFO, dispatch by kind (0 W, 1 KV, 2 IK, 3 dropped), one command
// outstanding per kind (pend cleared by that kind's return token)
module ot_svs_e (
  input wire ck, input wire rst, input wire rn, input wire [127:0] e_d, input wire e_fclk,
  output wire ow_v, output wire ok_v, output wire oi_v, output wire [39:0] o_d,
  input wire bw, input wire bk, input wire bi);
  wire [126:0] ed; wire e_empty, e_full; wire [2:0] e_fr;
  reg [127:0] e_f;
  wire e_wck = ~e_fclk;
  always @(posedge e_wck or negedge rst) if (!rst) e_f[0] <= 1'b0; else e_f[0] <= e_d[0];
  always @(posedge e_wck) e_f[127:1] <= e_d[127:1];
  wire [1:0] kind = ed[1:0];
  reg [2:0] pend;
  wire e_re = !e_empty && ((kind == 2'd3) || !pend[kind]);
  ot_hbm_accel_cdc_fifo #(.W(127), .AW(2)) u_e (.wclk(e_wck), .wrst_n(rst), .we(e_f[0]), .wdata(e_f[127:1]),
    .full(e_full), .rd_freed(e_fr), .rclk(ck), .rrst_n(rn), .re(e_re), .rdata(ed), .empty(e_empty));
  assign ow_v = e_re && (kind == 2'd0);
  assign ok_v = e_re && (kind == 2'd1);
  assign oi_v = e_re && (kind == 2'd2);
  assign o_d = {ed[47:38], ed[31:2]};           // {tag10, addr30}
  always @(posedge ck or negedge rn)
    if (!rn) pend <= 3'b000;
    else begin
      if (ow_v) pend[0] <= 1'b1; else if (bw) pend[0] <= 1'b0;
      if (ok_v) pend[1] <= 1'b1; else if (bk) pend[1] <= 1'b0;
      if (oi_v) pend[2] <= 1'b1; else if (bi) pend[2] <= 1'b0;
    end
endmodule

// W unit at the PHY W port: command hold, lane busy, present-and-drop against the registered w_rdy
module ot_svs_w (
  input wire ck, input wire rn,
  input wire cv, input wire [39:0] cd, output wire c_take,
  input wire [7:0] room, input wire [7:0] lane_done,
  output wire w_v, input wire w_rdy, output wire [23:0] w_addr, output wire [5:0] w_len, output wire [9:0] w_tag);
  reg hv; reg [39:0] hd;
  wire [9:0] c_tag = hd[39:30]; wire [29:0] c_addr = hd[29:0];
  reg [7:0] lane_busy; reg wv_q, wp_pend, wv_d, w_rdy_q; reg [23:0] wa_q; reg [9:0] wt_q;
  wire w_issue = hv && !wp_pend && !lane_busy[c_tag[2:0]] && room[c_tag[2:0]];
  assign c_take = w_issue;
  always @(posedge ck or negedge rn) if (!rn) hv <= 1'b0; else if (cv) hv <= 1'b1; else if (w_issue) hv <= 1'b0;
  always @(posedge ck) if (cv) hd <= cd;
  always @(posedge ck or negedge rn)
    if (!rn) begin wv_q <= 1'b0; lane_busy <= 8'h00; wp_pend <= 1'b0; wv_d <= 1'b0; w_rdy_q <= 1'b0; end
    else begin
      w_rdy_q <= w_rdy; wv_d <= wv_q;
      if (w_issue) begin wv_q <= 1'b1; wp_pend <= 1'b1; end
      else if (wv_q) wv_q <= 1'b0;
      else if (wp_pend && wv_d && w_rdy_q) wp_pend <= 1'b0;
      else if (wp_pend && !wv_d) wv_q <= 1'b1;
      lane_busy <= (lane_busy | (w_issue ? (8'h01 << c_tag[2:0]) : 8'h00)) & ~lane_done;
    end
  always @(posedge ck) if (w_issue) begin wa_q <= c_addr[23:0]; wt_q <= c_tag; end
  assign w_v = wv_q; assign w_addr = wa_q; assign w_len = 6'd5; assign w_tag = wt_q;
endmodule

// W lane pin unit: response raw capture + aligned register, lane room capture
module ot_svs_lane (
  input wire ck, input wire rn, input wire rdy_q2,
  input wire wr_v, input wire [9:0] wr_tag, input wire [4:0] wr_beat, input wire [255:0] wr_data, input wire w_room,
  output wire o_v, output wire [270:0] o_d, output wire room_q);
  reg vq, v, rq; reg [9:0] tr, t; reg [4:0] br, b; reg [255:0] dr, d;
  always @(posedge ck or negedge rn) if (!rn) begin vq <= 1'b0; v <= 1'b0; rq <= 1'b0; end
    else begin vq <= wr_v; v <= vq && rdy_q2; rq <= w_room; end
  always @(posedge ck) begin tr <= wr_tag; br <= wr_beat; dr <= wr_data; t <= tr; b <= br; d <= dr; end
  assign o_v = v; assign o_d = {t, b, d}; assign room_q = rq;
endmodule
`default_nettype wire

// views agent 2026-10-07: ot_svc_asm with its beat input registered (+1 cycle).  The one-hot write enable is decoded
// BEFORE the register and held in 4 kept copies (64-bit data chunks each), so no beat-decode cone or 1,280-load enable
// net follows the wire-stage chain.  Same function as ot_svc_asm one cycle later (a beat arriving with take on a full
// assembler is written but not marked, as there).
module ot_svs_asm_r #(parameter integer NB = 5, parameter integer TW = 13) (
  input wire ck, input wire rst_n,
  input wire bv, input wire [TW-1:0] btag, input wire [4:0] bbeat, input wire [255:0] bdata,
  output wire full, output wire [TW-1:0] tag, output wire [NB*256-1:0] data, input wire take);
  reg [NB-1:0] have, oh_q; (* keep *) reg [NB-1:0] we_q [0:3]; reg bv_q;
  reg [TW-1:0] t, t_q; reg [255:0] d_q;
  reg [255:0] b [0:NB-1];
  wire [NB-1:0] oh = bv ? NB'(1 << bbeat) : {NB{1'b0}};
  integer k;
  assign full = &have;
  assign tag = t;
  genvar g, c;
  generate for (g = 0; g < NB; g = g + 1) begin : gd
    assign data[g*256 +: 256] = b[g];
    for (c = 0; c < 4; c = c + 1) begin : gc
      always @(posedge ck) if (we_q[c][g]) b[g][c*64 +: 64] <= d_q[c*64 +: 64];
    end
  end endgenerate
  always @(posedge ck) begin d_q <= bdata; t_q <= btag; if (bv_q) t <= t_q; end
  always @(posedge ck or negedge rst_n)
    if (!rst_n) begin bv_q <= 1'b0; oh_q <= {NB{1'b0}}; for (k = 0; k < 4; k = k + 1) we_q[k] <= {NB{1'b0}}; have <= {NB{1'b0}}; end
    else begin
      bv_q <= bv; oh_q <= oh; for (k = 0; k < 4; k = k + 1) we_q[k] <= oh;
      if (full && take) have <= {NB{1'b0}};
      else have <= have | oh_q;
    end
endmodule
