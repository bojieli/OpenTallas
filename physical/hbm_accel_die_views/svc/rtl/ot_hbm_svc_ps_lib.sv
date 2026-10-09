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
//                returned beat leaves with tag[4:0] = {nocr, idx, valid, slot2} (slot = sector j[1:0]).
//   ot_svs_grp   group unit beside SM arbiter k (PCs 4k .. 4k+3): ping-pong 4-sector row buffers per PC, round-robin
//                onto the group's row port ks = {meta64, row1024, rq10, v} (the SM-line format: 1,099 b + 3 forwarded
//                clock copies), meta = {20'd0, rq / list index 11, load tag13, idx, pcid5, smask4, 10'd0}; ONE-BIT line credits back from the consumer
//                on kq ({fclk, v}, two-clock FIFO), returned in row order: the group keeps the PC id of every credited
//                row it sent (a 4 x CRR FIFO) and hands each credit to that row's PC (credit mode: CRR rows a PC).
// Physical: rows of 4 PCs leave each group at its arbiter's x: 8 row ports a stack (8 x 1,024 b a cycle = the stack's 32
// sectors a cycle).  No protection beyond what the legacy units had (REVIEW_20261009).
// ---------------------------------------------------------------------------------------------------------------------

module ot_svs_eps #(parameter integer WEMPTY = 0, parameter integer EEMPTY = 0, parameter integer IDQ = 32) (
  input wire ck, input wire rst, input wire rn, input wire [127:0] e_d, input wire e_fclk,
  output wire ow_v, output wire ok_v, output wire oi_v, output wire [39:0] o_d,
  input wire bw, input wire bk, input wire bi,
  output reg sd_v, output reg [123:0] sd_d,                // daisy word to both PC chains: {typ, payload 123}
                                                           //   typ 0 descriptor {ixm, ph, idx, nocr, row0 15, nsec/k 12, mask 32}
                                                           //   typ 1 id chunk {cnt 3, 6 x position 20}
  input wire dw_ok, input wire dw_ph, input wire de_ok, input wire de_ph,
  input wire [31:0] icw, input wire [31:0] ice,            // indexed: per-PC id-FIFO pops returned on the two credit chains
  output wire [2:0] kd,                                    // {forwarded clock, id-chunk credit, stream done pulse}
  output reg sg_v, output reg [12:0] sg_d);                // the stream's LOAD TAG (ed[83:71], compiler-supplied
                                                           // {ld_mode, ld_bank3, ld_grp8, ld_w2v}) to every group unit
  // Commands (ed = e[127:1]): legacy kinds 0-2 unchanged; STREAM = ed[126] with kind 1 (KV) / 2 (IK): ed[125] no-credit,
  // ed[124] INDEXED (DS selected rows: k = ed[28:17] ids follow), ed[83:71] load tag, ed[16:2] row0, ed[28:17] nsec / k,
  // ed[60:29] PC mask, ed[69:61] IK blocks; ID CHUNK = ed[126] with kind 3: ed[124:122] count (1..6), position i at
  // ed[2+20i +: 20], in list order (the IDX.TOPK order, sorted); the sender keeps <= 4 chunks unpopped (the e FIFO
  // depth) and gets one credit back per popped chunk on kd[1].  An indexed stream sends its chunks only while every
  // owning PC has id-FIFO room (IDQ credits a PC, returned by the PCs' pop chains), so no FIFO ever overflows.
  wire [126:0] ed; wire e_empty, e_full; wire [2:0] e_fr;
  reg [127:0] e_f;
  wire e_wck = ~e_fclk;
  always @(posedge e_wck or negedge rst) if (!rst) e_f[0] <= 1'b0; else e_f[0] <= e_d[0];
  always @(posedge e_wck) e_f[127:1] <= e_d[127:1];
  wire [1:0] kind = ed[1:0];
  wire strm = ed[126] && (kind == 2'd1 || kind == 2'd2);
  wire idch = ed[126] && (kind == 2'd3);
  reg [2:0] pend; reg spend, ph, kdv, ixa, kcv;
  // id credits (indexed): idc[p] free FIFO entries of PC p; need[p] = ids of this chunk owned by PC p
  reg [6:0] idc [0:31];
  reg [2:0] need [0:31];
  integer q, z;
  always @* begin
    for (q = 0; q < 32; q = q + 1) need[q] = 3'd0;
    for (z = 0; z < 6; z = z + 1)
      if (z < ed[124:122]) need[ed[2 + 20*z +: 5]] = need[ed[2 + 20*z +: 5]] + 3'd1;
  end
  reg room;
  always @* begin room = 1'b1; for (q = 0; q < 32; q = q + 1) if ({4'd0, need[q]} > idc[q]) room = 1'b0; end
  wire id_ok = ixa && room;
`ifdef OT_PS_MUT_CONC
  wire e_re = !e_empty && (idch ? id_ok : (kind == 2'd3) || (strm ? 1'b1 : !pend[kind]));   // NEGATIVE CONTROL: streams overlap
`else
  wire e_re = !e_empty && (idch ? id_ok : (kind == 2'd3) || (strm ? !spend : !pend[kind]));
`endif
  ot_hbm_accel_cdc_fifo #(.W(127), .AW(2)) u_e (.wclk(e_wck), .wrst_n(rst), .we(e_f[0]), .wdata(e_f[127:1]),
    .full(e_full), .rd_freed(e_fr), .rclk(ck), .rrst_n(rn), .re(e_re), .rdata(ed), .empty(e_empty));
  assign ow_v = e_re && (kind == 2'd0);
  assign ok_v = e_re && (kind == 2'd1) && !strm;
  assign oi_v = e_re && (kind == 2'd2) && !strm;
  assign o_d = {ed[47:38], ed[31:2]};           // {tag10, addr30}
  wire launch = e_re && strm;
  wire sendid = e_re && idch;
  wire idx = (kind == 2'd2);
  wire ixm = ed[124] && !idx;
  wire [11:0] nsec_i = 12'(((17 * {3'd0, ed[69:61]}) + 12'd31) >> 5);   // IK: ceil(17 blocks / 32) sectors a PC
  // done: both chains report every PC finished in the current phase (a side without PCs is always done)
  wire w_done = (WEMPTY != 0) || (dw_ok && dw_ph == ph);
  wire e_done = (EEMPTY != 0) || (de_ok && de_ph == ph);
  reg [3:0] hold;                                // the descriptor needs >= 1 cycle to leave before a done can count
  always @(posedge ck or negedge rn)
    if (!rn) begin pend <= 3'b000; spend <= 1'b0; ph <= 1'b0; sd_v <= 1'b0; sg_v <= 1'b0; kdv <= 1'b0; hold <= 4'd0; kcv <= 1'b0;
                   ixa <= 1'b0; for (q = 0; q < 32; q = q + 1) idc[q] <= 7'(IDQ); end
    else begin
      sd_v <= launch || sendid; sg_v <= launch; kdv <= 1'b0; kcv <= e_re;     // kcv: one e-FIFO credit back (any popped command)
      for (q = 0; q < 32; q = q + 1)
        idc[q] <= idc[q] - (sendid ? {4'd0, need[q]} : 7'd0) + {6'd0, icw[q]} + {6'd0, ice[q]};
      if (ow_v) pend[0] <= 1'b1; else if (bw) pend[0] <= 1'b0;
      if (ok_v) pend[1] <= 1'b1; else if (bk) pend[1] <= 1'b0;
      if (oi_v) pend[2] <= 1'b1; else if (bi) pend[2] <= 1'b0;
      if (launch) begin spend <= 1'b1; ph <= ~ph; hold <= 4'd8; ixa <= ixm; end
      else if (hold != 0) hold <= hold - 4'd1;
      else if (spend && w_done && e_done) begin spend <= 1'b0; kdv <= 1'b1; ixa <= 1'b0; end
    end
  always @(posedge ck) if (launch) sg_d <= ed[83:71];
  always @(posedge ck)
    if (launch) sd_d <= {1'b0, 60'd0, ixm, ~ph, idx, ed[125], ed[16:2], idx ? nsec_i : ed[28:17],
                         (idx || ixm) ? 32'hFFFF_FFFF : ed[60:29]};
    else if (sendid) sd_d <= {1'b1, ed[124:122], ed[121:2]};
  wire fck; ot_svc_fclk_buf u_fk (.a(ck), .y(fck));
  assign kd = {fck, kcv, kdv};
endmodule

module ot_svs_pcs #(parameter integer PCID = 0, parameter integer KNO = 15, parameter integer CRR = 16,
                    parameter integer END = 0, parameter integer IDQ = 32) (
  input wire ck, input wire rn, input wire rdy_q2,
  input wire iss_v, input wire [50:0] iss_d,
  output wire k_v, input wire k_rdy, output wire [29:0] k_addr, output wire [3:0] k_len, output wire [16:0] k_tag,
  input wire kr_v, input wire [16:0] kr_tag, input wire [3:0] kr_beat, input wire [255:0] kr_data,
  output wire b_v, output wire [16:0] b_t, output wire [3:0] b_b, output wire [255:0] b_d,
  input wire di_v, input wire [123:0] di_d, output reg do_v, output reg [123:0] do_d,
  input wire dni_ok, input wire dni_ph, output reg dno_ok, output reg dno_ph,
  input wire [31:0] ici, output reg [31:0] ico,            // indexed: id-FIFO pop credits toward the e port (OR chain)
  input wire cr_v);
  // ---- stream state (descriptor {ixm, ph, idx, nocr, row0 15, nsec/k 12, mask 32})
  reg act, ph, idx, nocr, mine, ixm; reg [14:0] row0; reg [11:0] nsec;
  reg [11:0] jn; reg [12:0] jr; reg [6:0] nob; reg [7:0] cred;
  // indexed: the ids this PC owns, in list order {li 11, position 20}; lic = ids seen (list index of the next id)
  reg [30:0] idf [0:IDQ-1]; reg [5:0] ih, it_; reg [6:0] icnt; reg [11:0] lic; reg [12:0] iss4;
  wire d_desc = di_v && !di_d[123], d_ids = di_v && di_d[123];
  wire [11:0] nsec4 = (nsec + 12'd3) & ~12'd3;
  wire pdone = ixm ? (lic >= nsec && icnt == 0 && jr >= iss4) : (!mine || (jr >= {1'b0, nsec4}));
  wire [11:0] jq = {jn[11:2], 2'b00};
  wire [30:0] ih_e = idf[ih[4:0]];
  wire [19:0] ipos = ih_e[19:0];
  wire [16:0] ijq = {ipos[19:5], 2'b00};                   // indexed row: sector j = 4 * (position div 32)
  wire [29:0] sa, sai; wire sf, sfi;
  ot_hbm_kport_map u_m (.pc(5'(PCID)), .bank({jq[9:7], jq[1:0]}), .row({4'd0, row0} + 19'(jq >> 10)), .col(jq[6:2]),
    .s(sa), .fault(sf));
  wire [18:0] irow = {4'd0, row0} + 19'(ijq >> 10);
  ot_hbm_kport_map u_mi (.pc(5'(PCID)), .bank({ijq[9:7], ijq[1:0]}), .row(irow), .col(ijq[6:2]), .s(sai), .fault(sfi));
  wire sreq = act && mine && (ixm ? (icnt != 0) : (jn < nsec)) && (nob <= 7'(4 * KNO - 4)) && (nocr || cred != 0);
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
  // stream read tag: {11, rq10 / li11, rr2, 00}: contiguous rq in [14:5] (li[10] = 0), indexed li in [14:4]; the row's
  // bank-XOR bits rr[1:0] ride in [3:2] (indexed) so the returned beat finds its sector slot without a table
  always @(posedge ck) begin
    if (iss_v && !idle) smd <= iss_d;
    if (go_sm) {t, ln, a} <= (iss_v && idle) ? iss_d : smd;
    else if (go_s && ixm) begin a <= {sai[29:2], 2'b00}; ln <= 4'd4; t <= {2'b11, ih_e[30:20], irow[1:0], 2'b00}; end
    else if (go_s) begin a <= {sa[29:2], 2'b00}; ln <= 4'd4; t <= {2'b11, 1'b0, jn[11:2], 4'd0}; end
  end
  assign k_v = v; assign k_addr = a; assign k_len = ln; assign k_tag = t;
  // ---- responses: raw capture + aligned register (ot_svs_pc).  A stream beat leaves as
  //      tag {11, rq / li 11, slot 2, valid, idx}, beat {ixm, nocr, 2'b00} (the group unit's format)
  reg kr_v_q, bv; reg [16:0] t_r, bt; reg [3:0] bb_r, bb; reg [255:0] d_r, bd;
  wire s_beat = t_r[16:15] == 2'b11;
  wire [11:0] bj4 = {t_r[13:4], 2'b00};
  wire [14:0] rr = row0 + 15'(bj4 >> 10);
`ifdef OT_PS_MUT_ISLOT
  wire [1:0] slot = bb_r[1:0] ^ (ixm ? 2'b00 : rr[1:0]);                    // NEGATIVE CONTROL: indexed rows unpermuted
`else
  wire [1:0] slot = bb_r[1:0] ^ (ixm ? t_r[3:2] : rr[1:0]);
`endif
  wire [11:0] bj = {t_r[13:4], slot};
  wire svalid = idx || ixm || (bj < nsec);
  always @(posedge ck or negedge rn) if (!rn) begin kr_v_q <= 1'b0; bv <= 1'b0; end else begin kr_v_q <= kr_v; bv <= kr_v_q && rdy_q2; end
  always @(posedge ck) begin
    t_r <= kr_tag; bb_r <= kr_beat; d_r <= kr_data;
    bt <= s_beat ? {t_r[16:4], slot, svalid, idx} : t_r;
    bb <= s_beat ? {ixm, nocr, 2'b00} : bb_r;
    bd <= d_r;
  end
  assign b_v = bv; assign b_t = bt; assign b_b = bb; assign b_d = bd;
  wire s_ret = bv && bt[16:15] == 2'b11;          // a stream beat returned (counted at the aligned register)
  // ---- the id FIFO (indexed): push every id of a chunk this PC owns (<= 6 a cycle; the e port's credits keep it from
  //      overflowing), pop one per issued read, in list order
  reg [2:0] npush; reg [30:0] pv [0:5];
  integer z;
  always @* begin
    npush = 3'd0;
    for (z = 0; z < 6; z = z + 1) pv[z] = 31'd0;
    for (z = 0; z < 6; z = z + 1)
      if (d_ids && z < di_d[122:120] && di_d[20*z +: 5] == 5'(PCID)) begin
        pv[npush] = {11'(lic + 12'(z)), di_d[20*z +: 20]};
        npush = npush + 3'd1;
      end
  end
  wire ipop = sacc && ixm;
  always @(posedge ck) for (z = 0; z < 6; z = z + 1) if (z < npush) idf[(it_ + 6'(z)) % IDQ] <= pv[z];
`ifdef OT_PS_MUT_IORDER
  wire [5:0] ih_n = ipop ? ((icnt > 1 && ih[0]) ? ih + 6'd2 : ih + 6'd1) : ih;   // NEGATIVE CONTROL: list order broken
`else
  wire [5:0] ih_n = ipop ? ih + 6'd1 : ih;
`endif
  // ---- stream engine
  always @(posedge ck or negedge rn)
    if (!rn) begin act <= 1'b0; ph <= 1'b0; idx <= 1'b0; nocr <= 1'b1; mine <= 1'b0; ixm <= 1'b0; jn <= 0; jr <= 0;
                   nob <= 0; cred <= 8'(CRR); do_v <= 1'b0; dno_ok <= 1'b0; dno_ph <= 1'b0; ih <= 0; it_ <= 0;
                   icnt <= 0; lic <= 0; iss4 <= 0; ico <= 32'd0; end
    else begin
      do_v <= di_v;
      cred <= cred - ((sacc && !nocr) ? 8'd1 : 8'd0) + (cr_v ? 8'd1 : 8'd0);
      ico <= ici | (ipop ? (32'd1 << PCID) : 32'd0);
      if (d_desc) begin
        {ixm, ph, idx, nocr} <= di_d[62:59]; mine <= di_d[PCID]; act <= di_d[PCID];
        jn <= 0; jr <= 0; nob <= 0; lic <= 0; iss4 <= 0;   // cred persists: a credit returned after a stream ended counts
      end else begin
        if (d_ids) lic <= lic + {9'd0, di_d[122:120]};
        if (sacc && !ixm) jn <= jn + 12'd4;
        if (sacc) iss4 <= iss4 + 13'd4;
        if (s_ret) jr <= jr + 13'd1;
        nob <= nob + (sacc ? 7'd4 : 7'd0) - (s_ret ? 7'd1 : 7'd0);
        if (act && pdone) act <= 1'b0;
      end
      it_ <= (it_ + {3'd0, npush}) % IDQ;
      ih <= ih_n % IDQ;
      icnt <= icnt + {4'd0, npush} - (ipop ? 7'd1 : 7'd0);
      // done chain: every PC upstream finished in the same phase, and this one
      dno_ok <= ((END != 0) ? 1'b1 : (dni_ok && dni_ph == ph)) && pdone && !di_v;
      dno_ph <= ph;
    end
  always @(posedge ck) if (d_desc) {row0, nsec} <= di_d[58:32];
  always @(posedge ck) if (di_v) do_d <= di_d;
endmodule

module ot_svs_grp #(parameter integer K = 0) (
  input wire ck, input wire rst, input wire rn,
  input wire [3:0] sv, input wire [4*277-1:0] sq,         // stream beats of PCs 4K .. 4K+3 (tag 11)
  input wire [1:0] kq,                                     // {fclk, v}: one line credit, in row order
  input wire sg_v, input wire [12:0] sg_d,                 // the running stream's load tag (from the e port)
  output wire [3:0] cr,                                    // credit pulse to PC 4K + j
  output wire [1101:0] ks,                                 // {fclk x3, meta64, row1024, rq10, v}
  output wire ovf);                                        // a beat found its row buffer still full / credit queue overflow (never)
  reg [255:0] b [0:3][0:1][0:3];
  reg [3:0] sm [0:3][0:1];
  reg [2:0] cnt [0:3][0:1];
  reg [10:0] rq [0:3][0:1];
  reg ix [0:3][0:1];
  reg nc [0:3][0:1];
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
  reg ov, ovb; reg [1087:0] od; reg [9:0] ot; reg [12:0] lt;
  always @(posedge ck) if (sg_v) lt <= sg_d;
  always @(posedge ck or negedge rn)
    if (!rn) begin
      for (p = 0; p < 4; p = p + 1) begin full[p] <= 2'b00; ws[p] <= 1'b0; rs[p] <= 1'b0;
        for (s = 0; s < 2; s = s + 1) begin cnt[p][s] <= 3'd0; sm[p][s] <= 4'd0; end end
      rr <= 2'd0; ov <= 1'b0; ovb <= 1'b0;
    end else begin
      ov <= any;
      if (any) begin rr <= sel + 2'd1; full[sel][rs[sel]] <= 1'b0; rs[sel] <= ~rs[sel]; end
      for (p = 0; p < 4; p = p + 1) if (sv[p]) begin
        if (full[p][ws[p]] && !(any && sel == p && rs[p] == ws[p])) ovb <= 1'b1;
        sm[p][ws[p]] <= ((cnt[p][ws[p]] == 3'd0) ? 4'd0 : sm[p][ws[p]]) |
                        (sq[p*277+261] ? (4'd1 << sq[p*277+262 +: 2]) : 4'd0);
        if (cnt[p][ws[p]] == 3'd3) begin
          cnt[p][ws[p]] <= 3'd0; full[p][ws[p]] <= 1'b1; ws[p] <= ~ws[p];
        end else cnt[p][ws[p]] <= cnt[p][ws[p]] + 3'd1;
      end
    end
  always @(posedge ck) begin
    for (p = 0; p < 4; p = p + 1) if (sv[p]) begin
      b[p][ws[p]][sq[p*277+262 +: 2]] <= sq[p*277 +: 256];
      rq[p][ws[p]] <= sq[p*277+264 +: 11];
      ix[p][ws[p]] <= sq[p*277+260];
      nc[p][ws[p]] <= sq[p*277+258];
    end
    if (any) begin
      od <= {20'd0, rq[sel][rs[sel]], lt, ix[sel][rs[sel]], 5'(4 * K + sel), sm[sel][rs[sel]], 10'd0,
             b[sel][rs[sel]][3], b[sel][rs[sel]][2], b[sel][rs[sel]][1], b[sel][rs[sel]][0]};
      ot <= rq[sel][rs[sel]][9:0];
    end
  end
  wire fck; ot_svc_fclk_buf u_fk (.a(ck), .y(fck));
  assign ks = {fck, fck, fck, od, ot, ov};
  // credits: forwarded {fclk, v}, falling-edge capture + two-clock FIFO (as the e port); the PC of each credited row
  // sent is queued, and a returned credit goes to the PC at the head (the consumer returns credits in row order)
  localparam integer QD = 64;
  reg [1:0] pq [0:QD-1]; reg [5:0] qh, qt; reg [6:0] qn;
  wire push = any && !nc[sel][rs[sel]];
  reg cf_v; wire c_empty, c_full; wire [2:0] c_fr; wire cd;
  wire c_wck = ~kq[1];
  always @(posedge c_wck or negedge rst) if (!rst) cf_v <= 1'b0; else cf_v <= kq[0];
  ot_hbm_accel_cdc_fifo #(.W(1), .AW(3)) u_c (.wclk(c_wck), .wrst_n(rst), .we(cf_v), .wdata(1'b1), .full(c_full),
    .rd_freed(c_fr), .rclk(ck), .rrst_n(rn), .re(!c_empty && qn != 0), .rdata(cd), .empty(c_empty));
  wire pop = !c_empty && qn != 0;
  reg [3:0] crq; reg ovq;
  assign ovf = ovb | ovq;
  always @(posedge ck) if (push) pq[qt] <= sel;
  always @(posedge ck or negedge rn)
    if (!rn) begin qh <= 0; qt <= 0; qn <= 0; crq <= 4'd0; ovq <= 1'b0; end
    else begin
      if (push) qt <= qt + 6'd1;
      if (pop) qh <= qh + 6'd1;
      qn <= qn + (push ? 7'd1 : 7'd0) - (pop ? 7'd1 : 7'd0);
      crq <= pop ? (4'd1 << pq[qh]) : 4'd0;
      if (push && qn == QD) ovq <= 1'b1;
    end
  assign cr = crq;
endmodule
`default_nettype wire
