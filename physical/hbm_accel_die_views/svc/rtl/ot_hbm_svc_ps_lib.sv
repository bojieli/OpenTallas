`timescale 1ps/1fs
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hbm-forks 2026-10-09 (coordinator: FIRST fork; HGI-1 section 2 "svc segments: kind-1 KV and kind-2 index-key reads
// striped over all 32 PCs"; CF-SVC): units of the PER-PC STREAM (PS) successor of the segmented stream service.
// The same function as ot_hbm_svc_core KVS / IKS (every PC of the stack streams its sectors j = 0 .. nsec-1 of the
// region in the dskv_wb / stream-PC j order through ot_hbm_kport_map, up to KNO 4-sector reads outstanding a PC), built
// for the segment masters (gen_svc_seg.py --ps): every one-cycle loop stays inside one unit, units talk only through
// wire-stage chains.
//   ot_svs_eps   e port: the legacy ot_svs_e dispatch (kind 0 W, kind 1 KV / kind 2 IK on one owner PC) plus STREAM
//                commands (ed[126] = 1, kind 1 or 2; ed[125] = no-credit: the consumer takes a row a cycle): one stream at
//                a time, the descriptor broadcast down the two PC daisy chains (west / east of the e port), completion by
//                the two done chains (an AND over every PC, phase-matched), a done pulse on port kd.
//   ot_svs_pcs   PC pin unit = ot_svs_pc (SM request present-and-drop, response capture) + the PC's stream engine.  An
//                SM issue is never delayed when the PC is idle (DS cycle-identical without streams); while a stream read
//                is being presented an SM issue waits in a one-entry hold (the arbiter keeps one SM read a PC).
//                Stream reads carry tag {2'b11, rq10, 5'd0} (legacy SM 00 / KV 01 / IK 10 filters ignore them); the
//                returned beat leaves with tag[4:0] = {1'b0, idx, valid, slot2} (slot = sector j[1:0]).
//   ot_svs_grp   group unit beside SM arbiter k (PCs 4k .. 4k+3): ping-pong 4-sector row buffers per PC, round-robin
//                onto the group's row port ks = {meta64, row1024, rq10, v} (the SM-line format: 1,099 b + 3 forwarded
//                clock copies), meta = {44'd0, idx, pcid5, smask4, 10'd0}; line credits back from the consumer on kq
//                ({fclk, pc2, v}, two-clock FIFO) to the owning PC (credit mode: CRR rows outstanding a PC).
// Physical: rows of 4 PCs leave each group at its arbiter's x: 8 row ports a stack (8 x 1,024 b a cycle = the stack's 32
// sectors a cycle).  No protection beyond what the legacy units had (REVIEW_20261009).
// ---------------------------------------------------------------------------------------------------------------------

module ot_svs_eps #(parameter integer WEMPTY = 0, parameter integer EEMPTY = 0) (
  input wire ck, input wire rst, input wire rn, input wire [127:0] e_d, input wire e_fclk,
  output wire ow_v, output wire ok_v, output wire oi_v, output wire [39:0] o_d,
  input wire bw, input wire bk, input wire bi,
  output reg sd_v, output reg [61:0] sd_d,                 // stream descriptor to both PC daisy chains
  input wire dw_ok, input wire dw_ph, input wire de_ok, input wire de_ph,
  output wire [1:0] kd);                                   // {forwarded clock, stream done pulse}
  wire [126:0] ed; wire e_empty, e_full; wire [2:0] e_fr;
  reg [127:0] e_f;
  wire e_wck = ~e_fclk;
  always @(posedge e_wck or negedge rst) if (!rst) e_f[0] <= 1'b0; else e_f[0] <= e_d[0];
  always @(posedge e_wck) e_f[127:1] <= e_d[127:1];
  wire [1:0] kind = ed[1:0];
  wire strm = ed[126] && (kind == 2'd1 || kind == 2'd2);
  reg [2:0] pend; reg spend, ph, kdv;
  wire e_re = !e_empty && ((kind == 2'd3) || (strm ? !spend : !pend[kind]));
  ot_hbm_accel_cdc_fifo #(.W(127), .AW(2)) u_e (.wclk(e_wck), .wrst_n(rst), .we(e_f[0]), .wdata(e_f[127:1]),
    .full(e_full), .rd_freed(e_fr), .rclk(ck), .rrst_n(rn), .re(e_re), .rdata(ed), .empty(e_empty));
  assign ow_v = e_re && (kind == 2'd0);
  assign ok_v = e_re && (kind == 2'd1) && !strm;
  assign oi_v = e_re && (kind == 2'd2) && !strm;
  assign o_d = {ed[47:38], ed[31:2]};           // {tag10, addr30}
  wire launch = e_re && strm;
  wire idx = (kind == 2'd2);
  wire [11:0] nsec_i = 12'(((17 * {3'd0, ed[69:61]}) + 12'd31) >> 5);   // IK: ceil(17 blocks / 32) sectors a PC
  // done: both chains report every PC finished in the current phase (a side without PCs is always done)
  wire w_done = (WEMPTY != 0) || (dw_ok && dw_ph == ph);
  wire e_done = (EEMPTY != 0) || (de_ok && de_ph == ph);
  reg [3:0] hold;                                // the descriptor needs >= 1 cycle to leave before a done can count
  always @(posedge ck or negedge rn)
    if (!rn) begin pend <= 3'b000; spend <= 1'b0; ph <= 1'b0; sd_v <= 1'b0; kdv <= 1'b0; hold <= 4'd0; end
    else begin
      sd_v <= launch; kdv <= 1'b0;
      if (ow_v) pend[0] <= 1'b1; else if (bw) pend[0] <= 1'b0;
      if (ok_v) pend[1] <= 1'b1; else if (bk) pend[1] <= 1'b0;
      if (oi_v) pend[2] <= 1'b1; else if (bi) pend[2] <= 1'b0;
      if (launch) begin spend <= 1'b1; ph <= ~ph; hold <= 4'd8; end
      else if (hold != 0) hold <= hold - 4'd1;
      else if (spend && w_done && e_done) begin spend <= 1'b0; kdv <= 1'b1; end
    end
  always @(posedge ck) if (launch)
    sd_d <= {~ph, idx, ed[125], ed[16:2], idx ? nsec_i : ed[28:17], idx ? 32'hFFFF_FFFF : ed[60:29]};
  wire fck; ot_svc_fclk_buf u_fk (.a(ck), .y(fck));
  assign kd = {fck, kdv};
endmodule

module ot_svs_pcs #(parameter integer PCID = 0, parameter integer KNO = 15, parameter integer CRR = 16,
                    parameter integer END = 0) (
  input wire ck, input wire rn, input wire rdy_q2,
  input wire iss_v, input wire [50:0] iss_d,
  output wire k_v, input wire k_rdy, output wire [29:0] k_addr, output wire [3:0] k_len, output wire [16:0] k_tag,
  input wire kr_v, input wire [16:0] kr_tag, input wire [3:0] kr_beat, input wire [255:0] kr_data,
  output wire b_v, output wire [16:0] b_t, output wire [3:0] b_b, output wire [255:0] b_d,
  input wire di_v, input wire [61:0] di_d, output reg do_v, output reg [61:0] do_d,
  input wire dni_ok, input wire dni_ph, output reg dno_ok, output reg dno_ph,
  input wire cr_v);
  // ---- stream state (descriptor {ph, idx, nocr, row0 15, nsec 12, mask 32})
  reg act, ph, idx, nocr, mine; reg [14:0] row0; reg [11:0] nsec;
  reg [11:0] jn; reg [12:0] jr; reg [6:0] nob; reg [7:0] cred;
  wire [11:0] nsec4 = (nsec + 12'd3) & ~12'd3;
  wire pdone = !mine || (jr >= {1'b0, nsec4});
  wire [11:0] jq = {jn[11:2], 2'b00};
  wire [29:0] sa; wire sf;
  ot_hbm_kport_map u_m (.pc(5'(PCID)), .bank({jq[9:7], jq[1:0]}), .row({4'd0, row0} + 19'(jq >> 10)), .col(jq[6:2]),
    .s(sa), .fault(sf));
  wire sreq = act && mine && (jn < nsec) && (nob <= 7'(4 * KNO - 4)) && (nocr || cred != 0);
  // ---- K request register: SM issue (never delayed when idle) or a stream read
  reg v, pend, v_d, k_rdy_q, sr, smh; reg [29:0] a; reg [3:0] ln; reg [16:0] t; reg [50:0] smd;
  wire idle = !pend && !v;
  wire go_sm = (iss_v && idle) || (smh && idle);
  wire go_s  = idle && !iss_v && !smh && sreq;
  wire sacc  = pend && v_d && k_rdy_q && sr;
  always @(posedge ck or negedge rn)
    if (!rn) begin v <= 1'b0; pend <= 1'b0; v_d <= 1'b0; k_rdy_q <= 1'b0; sr <= 1'b0; smh <= 1'b0; end
    else begin
      k_rdy_q <= k_rdy; v_d <= v;
      if (iss_v && !idle) smh <= 1'b1; else if (go_sm) smh <= 1'b0;
      if (go_sm || go_s) begin v <= 1'b1; pend <= 1'b1; sr <= go_s; end
      else if (v) v <= 1'b0;
      else if (pend && v_d && k_rdy_q) pend <= 1'b0;
      else if (pend && !v_d) v <= 1'b1;
    end
  always @(posedge ck) begin
    if (iss_v && !idle) smd <= iss_d;
    if (go_sm) {t, ln, a} <= (iss_v && idle) ? iss_d : smd;
    else if (go_s) begin a <= {sa[29:2], 2'b00}; ln <= 4'd4; t <= {2'b11, jn[11:2], 5'd0}; end
  end
  assign k_v = v; assign k_addr = a; assign k_len = ln; assign k_tag = t;
  // ---- responses: raw capture + aligned register (ot_svs_pc); stream beats get {idx, valid, slot} in tag[4:0]
  reg kr_v_q, bv; reg [16:0] t_r, bt; reg [3:0] bb_r, bb; reg [255:0] d_r, bd;
  wire s_beat = t_r[16:15] == 2'b11;
  wire [11:0] bj4 = {t_r[14:5], 2'b00};
  wire [14:0] rr = row0 + 15'(bj4 >> 10);
  wire [1:0] slot = bb_r[1:0] ^ rr[1:0];
  wire [11:0] bj = {t_r[14:5], slot};
  wire svalid = idx || (bj < nsec);
  always @(posedge ck or negedge rn) if (!rn) begin kr_v_q <= 1'b0; bv <= 1'b0; end else begin kr_v_q <= kr_v; bv <= kr_v_q && rdy_q2; end
  always @(posedge ck) begin
    t_r <= kr_tag; bb_r <= kr_beat; d_r <= kr_data;
    bt <= s_beat ? {t_r[16:5], 1'b0, idx, svalid, slot} : t_r;
    bb <= bb_r; bd <= d_r;
  end
  assign b_v = bv; assign b_t = bt; assign b_b = bb; assign b_d = bd;
  wire s_ret = bv && bt[16:15] == 2'b11;          // a stream beat returned (counted at the aligned register)
  // ---- stream engine
  always @(posedge ck or negedge rn)
    if (!rn) begin act <= 1'b0; ph <= 1'b0; idx <= 1'b0; nocr <= 1'b1; mine <= 1'b0; jn <= 0; jr <= 0; nob <= 0; cred <= 8'd0;
                   do_v <= 1'b0; dno_ok <= 1'b0; dno_ph <= 1'b0; end
    else begin
      do_v <= di_v;
      if (di_v) begin
        {ph, idx, nocr} <= di_d[61:59]; mine <= di_d[PCID]; act <= di_d[PCID];
        jn <= 0; jr <= 0; nob <= 0; cred <= 8'(CRR);
      end else begin
        if (sacc) jn <= jn + 12'd4;
        if (s_ret) jr <= jr + 13'd1;
        nob <= nob + (sacc ? 7'd4 : 7'd0) - (s_ret ? 7'd1 : 7'd0);
        cred <= cred - ((sacc && !nocr) ? 8'd1 : 8'd0) + ((cr_v && !nocr) ? 8'd1 : 8'd0);
        if (act && pdone) act <= 1'b0;
      end
      // done chain: every PC upstream finished in the same phase, and this one
      dno_ok <= ((END != 0) ? 1'b1 : (dni_ok && dni_ph == ph)) && pdone && !di_v;
      dno_ph <= ph;
    end
  always @(posedge ck) if (di_v) {row0, nsec} <= di_d[58:32];
  always @(posedge ck) if (di_v) do_d <= di_d;
endmodule

module ot_svs_grp #(parameter integer K = 0) (
  input wire ck, input wire rst, input wire rn,
  input wire [3:0] sv, input wire [4*277-1:0] sq,         // stream beats of PCs 4K .. 4K+3 (tag 11)
  input wire [3:0] kq,                                     // {fclk, pc2, v}: one line credit back to a PC
  output wire [3:0] cr,                                    // credit pulse to PC 4K + j
  output wire [1101:0] ks,                                 // {fclk x3, meta64, row1024, rq10, v}
  output reg ovf);                                         // a beat found its row buffer still full (never: schedule)
  reg [255:0] b [0:3][0:1][0:3];
  reg [3:0] sm [0:3][0:1];
  reg [2:0] cnt [0:3][0:1];
  reg [9:0] rq [0:3][0:1];
  reg ix [0:3][0:1];
  reg [1:0] full [0:3];
  reg ws [0:3], rs [0:3];
  integer p, s;
  // the row a PC hands next (its older buffer), round robin over the PCs with a ready row
  wire [3:0] rdy;
  genvar g;
  generate for (g = 0; g < 4; g = g + 1) begin : gr assign rdy[g] = full[g][rs[g]]; end endgenerate
  reg [1:0] rr;
  wire [7:0] r2 = {rdy, rdy};
  wire [3:0] rot = r2 >> rr;
  wire [1:0] off = rot[0] ? 2'd0 : rot[1] ? 2'd1 : rot[2] ? 2'd2 : 2'd3;
  wire [1:0] sel = rr + off;
  wire any = |rdy;
  reg ov; reg [1087:0] od; reg [9:0] ot;
  always @(posedge ck or negedge rn)
    if (!rn) begin
      for (p = 0; p < 4; p = p + 1) begin full[p] <= 2'b00; ws[p] <= 1'b0; rs[p] <= 1'b0;
        for (s = 0; s < 2; s = s + 1) begin cnt[p][s] <= 3'd0; sm[p][s] <= 4'd0; end end
      rr <= 2'd0; ov <= 1'b0; ovf <= 1'b0;
    end else begin
      ov <= any;
      if (any) begin rr <= sel + 2'd1; full[sel][rs[sel]] <= 1'b0; rs[sel] <= ~rs[sel]; end
      for (p = 0; p < 4; p = p + 1) if (sv[p]) begin
        if (full[p][ws[p]] && !(any && sel == p && rs[p] == ws[p])) ovf <= 1'b1;
        sm[p][ws[p]] <= ((cnt[p][ws[p]] == 3'd0) ? 4'd0 : sm[p][ws[p]]) |
                        (sq[p*277+260+2] ? (4'd1 << sq[p*277+260 +: 2]) : 4'd0);
        if (cnt[p][ws[p]] == 3'd3) begin
          cnt[p][ws[p]] <= 3'd0; full[p][ws[p]] <= 1'b1; ws[p] <= ~ws[p];
        end else cnt[p][ws[p]] <= cnt[p][ws[p]] + 3'd1;
      end
    end
  always @(posedge ck) begin
    for (p = 0; p < 4; p = p + 1) if (sv[p]) begin
      b[p][ws[p]][sq[p*277+260 +: 2]] <= sq[p*277 +: 256];
      rq[p][ws[p]] <= sq[p*277+265 +: 10];
      ix[p][ws[p]] <= sq[p*277+260+3];
    end
    if (any) begin
      od <= {44'd0, ix[sel][rs[sel]], 5'(4 * K + sel), sm[sel][rs[sel]], 10'd0,
             b[sel][rs[sel]][3], b[sel][rs[sel]][2], b[sel][rs[sel]][1], b[sel][rs[sel]][0]};
      ot <= rq[sel][rs[sel]];
    end
  end
  wire fck; ot_svc_fclk_buf u_fk (.a(ck), .y(fck));
  assign ks = {fck, fck, fck, od, ot, ov};
  // credits: forwarded {pc2, v} with its clock, falling-edge capture + two-clock FIFO (as the e port)
  reg cf_v; reg [1:0] cf_d; wire c_empty, c_full; wire [2:0] c_fr; wire [1:0] cd;
  wire c_wck = ~kq[3];
  always @(posedge c_wck or negedge rst) if (!rst) cf_v <= 1'b0; else cf_v <= kq[0];
  always @(posedge c_wck) cf_d <= kq[2:1];
  ot_hbm_accel_cdc_fifo #(.W(2), .AW(3)) u_c (.wclk(c_wck), .wrst_n(rst), .we(cf_v), .wdata(cf_d), .full(c_full),
    .rd_freed(c_fr), .rclk(ck), .rrst_n(rn), .re(!c_empty), .rdata(cd), .empty(c_empty));
  reg [3:0] crq;
  always @(posedge ck or negedge rn) if (!rn) crq <= 4'd0; else crq <= c_empty ? 4'd0 : (4'd1 << cd);
  assign cr = crq;
endmodule
`default_nettype wire
