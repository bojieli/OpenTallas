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
//                clock copies), meta = {31'd0, load tag13, idx, pcid5, smask4, 10'd0}; ONE-BIT line credits back from the consumer
//                on kq ({fclk, v}, two-clock FIFO), returned in row order: the group keeps the PC id of every credited
//                row it sent (a 4 x CRR FIFO) and hands each credit to that row's PC (credit mode: CRR rows a PC).
// Physical: rows of 4 PCs leave each group at its arbiter's x: 8 row ports a stack (8 x 1,024 b a cycle = the stack's 32
// sectors a cycle).  No protection beyond what the legacy units had (REVIEW_20261009).
// ---------------------------------------------------------------------------------------------------------------------

module ot_svs_eps #(parameter integer WEMPTY = 0, parameter integer EEMPTY = 0) (
  input wire ck, input wire rst, input wire rn, input wire [127:0] e_d, input wire e_fclk,
  output wire ow_v, output wire ok_v, output wire oi_v, output wire [39:0] o_d,
  input wire bw, input wire bk, input wire bi,
  output reg sd_v, output reg [61:0] sd_d,                 // stream descriptor to both PC daisy chains
  input wire dw_ok, input wire dw_ph, input wire de_ok, input wire de_ph,
  output wire [1:0] kd,                                    // {forwarded clock, stream done pulse}
  output reg sg_v, output reg [12:0] sg_d);                // the stream's LOAD TAG (ed[83:71], compiler-supplied
                                                           // {ld_mode, ld_bank3, ld_grp8, ld_w2v}) to every group unit
  wire [126:0] ed; wire e_empty, e_full; wire [2:0] e_fr;
  reg [127:0] e_f;
  wire e_wck = ~e_fclk;
  always @(posedge e_wck or negedge rst) if (!rst) e_f[0] <= 1'b0; else e_f[0] <= e_d[0];
  always @(posedge e_wck) e_f[127:1] <= e_d[127:1];
  wire [1:0] kind = ed[1:0];
  wire strm = ed[126] && (kind == 2'd1 || kind == 2'd2);
  reg [2:0] pend; reg spend, ph, kdv;
  // The second stream owns a separate pending slot: its wait must not block unrelated legacy commands.
  reg spq_v; reg [126:0] spq_d;
`ifdef OT_PS_MUT_CONC
  wire e_re = !e_empty && ((kind == 2'd3) || (strm ? 1'b1 : !pend[kind]));   // NEGATIVE CONTROL: streams overlap
`else
  wire e_re = !e_empty && ((kind == 2'd3) || (strm ? !spq_v : !pend[kind]));
`endif
  ot_hbm_accel_cdc_fifo #(.W(127), .AW(2)) u_e (.wclk(e_wck), .wrst_n(rst), .we(e_f[0]), .wdata(e_f[127:1]),
    .full(e_full), .rd_freed(e_fr), .rclk(ck), .rrst_n(rn), .re(e_re), .rdata(ed), .empty(e_empty));
  assign ow_v = e_re && (kind == 2'd0);
  assign ok_v = e_re && (kind == 2'd1) && !strm;
  assign oi_v = e_re && (kind == 2'd2) && !strm;
  assign o_d = {ed[47:38], ed[31:2]};           // {tag10, addr30}
`ifdef OT_PS_MUT_CONC
  wire launch_q = 1'b0, queue_stream = 1'b0;
  wire launch = e_re && strm;
`else
  wire launch_q = spq_v && !spend;
  wire queue_stream = e_re && strm && spend;
  wire launch = launch_q || (e_re && strm && !spend && !spq_v);
`endif
  wire [126:0] stream_d = launch_q ? spq_d : ed;
  wire idx = (stream_d[1:0] == 2'd2);
  wire [11:0] nsec_i = 12'(((17 * {3'd0, stream_d[69:61]}) + 12'd31) >> 5);   // IK: ceil(17 blocks / 32) sectors a PC
  // done: both chains report every PC finished in the current phase (a side without PCs is always done)
  wire w_done = (WEMPTY != 0) || (dw_ok && dw_ph == ph);
  wire e_done = (EEMPTY != 0) || (de_ok && de_ph == ph);
  reg [3:0] hold;                                // the descriptor needs >= 1 cycle to leave before a done can count
  always @(posedge ck or negedge rn)
    if (!rn) begin pend <= 3'b000; spq_v <= 1'b0; spend <= 1'b0; ph <= 1'b0; sd_v <= 1'b0; sg_v <= 1'b0; kdv <= 1'b0; hold <= 4'd0; end
    else begin
      sd_v <= launch; sg_v <= launch; kdv <= 1'b0;
      if (queue_stream) spq_v <= 1'b1; else if (launch_q) spq_v <= 1'b0;
      if (ow_v) pend[0] <= 1'b1; else if (bw) pend[0] <= 1'b0;
      if (ok_v) pend[1] <= 1'b1; else if (bk) pend[1] <= 1'b0;
      if (oi_v) pend[2] <= 1'b1; else if (bi) pend[2] <= 1'b0;
      if (launch) begin spend <= 1'b1; ph <= ~ph; hold <= 4'd8; end
      else if (hold != 0) hold <= hold - 4'd1;
      else if (spend && w_done && e_done) begin spend <= 1'b0; kdv <= 1'b1; end
    end
  always @(posedge ck) if (queue_stream) spq_d <= ed;
  always @(posedge ck) if (launch) sg_d <= stream_d[83:71];
  always @(posedge ck) if (launch)
    sd_d <= {~ph, idx, stream_d[125], stream_d[16:2], idx ? nsec_i : stream_d[28:17], idx ? 32'hFFFF_FFFF : stream_d[60:29]};
  wire fck; ot_svc_fclk_buf u_fk (.a(ck), .y(fck));
  assign kd = {fck, kdv};
endmodule

module ot_svs_pcs #(parameter integer PCID = 0, parameter integer KNO = 15, parameter integer CRR = 16,
                    parameter integer END = 0, parameter integer DMA = 0, parameter integer CR0 = 32,
                    parameter integer QD = 16, parameter integer MF = 32) (
  input wire ck, input wire rn, input wire rdy_q2,
  input wire iss_v, input wire [50:0] iss_d,
  output wire k_v, input wire k_rdy, output wire [29:0] k_addr, output wire [3:0] k_len, output wire [16:0] k_tag,
  input wire kr_v, input wire [16:0] kr_tag, input wire [3:0] kr_beat, input wire [255:0] kr_data,
  output wire b_v, output wire [16:0] b_t, output wire [3:0] b_b, output wire [255:0] b_d,
  input wire di_v, input wire [61:0] di_d, output reg do_v, output reg [61:0] do_d,
  input wire dni_ok, input wire dni_ph, output reg dno_ok, output reg dno_ph,
  input wire cr_v,
  // ---- DMA stream v2 (hbm-phys [svc] 2026-10-10, agreed with hgi-1010/c: one 270-b lane a PC, lane = this PC, every
  // beat {v, fault, tag4, idx8, data256}, no ordering rule, per-lane credit pulses, CR0 = the front's lane buffer).
  // Requests {tag4, nsec9, s30} (s = stack-local sector) arrive on the side's request daisy chain (rq_i -> rq_o, the
  // PS descriptor chain's order); this PC keeps them in a QD-deep queue and reads ITS rows of each: in every 32-row
  // aligned block exactly one row r has r[4:0] ^ r[9:5] ^ r[14:10] = PCID (ot_hbm_loader_kport_address), so a request
  // of <= 65 rows costs <= 3 block steps; an owned row in range is read as one 4-sector K request (below SM issues and
  // PS stream reads); its {tag, idx base, sector mask} waits in an MF-deep in-flight FIFO (the PHY returns a PC's reads
  // in order, a read's beats contiguous).  A returned beat whose sector lies in the request leaves on the beat path
  // (bb[3] = 1, bt = {11, 000, tag, idx}) to the group unit, which drives it onto the lane; masked sectors are dropped.
  // Lane credits are counted here; kr_rdy_o (registered) is high only with >= 2 credits left after this edge (at most 2
  // beats are handed over before a decrement shows: the one in the capture stage and the next handshake).  The pop
  // count npop goes back on the min chain (pm_i -> pm_o: the older of this PC's and the upstream count) to the request
  // unit, which admits a request only while every PC's queue has room.  DMA = 0: none of this (kr_rdy_o = 1).
  output reg kr_rdy_o,
  input wire rq_iv, input wire [42:0] rq_i, output reg rq_ov, output reg [42:0] rq_o,
  input wire [7:0] pm_i, output reg [7:0] pm_o,
  input wire lc_v);
  localparam integer QA = $clog2(QD), MA = $clog2(MF), CW = $clog2(CR0 + 1);
  // ---- DMA request queue and block walker
  reg [42:0] rqq [0:QD-1]; reg [QA-1:0] qh, qt; reg [QA:0] qn; reg [7:0] npop;
  wire [42:0] hd = rqq[qh];
  wire [29:0] hs = hd[29:0]; wire [8:0] hn = hd[38:30]; wire [3:0] htg = hd[42:39];
  wire [29:0] hl = hs + 30'(hn) - 30'd1;
  wire [27:0] r0 = hs[29:2], r1 = hl[29:2];
  reg hact; reg [22:0] bk;
  wire [27:0] rc = {bk, 5'(PCID) ^ bk[4:0] ^ bk[9:5]};
  wire rin = rc >= r0 && rc <= r1;
  // row FIFO (owned rows waiting for the K register): {row28, tag4, base10, mask4}
  reg [45:0] rw [0:3]; reg [1:0] rwh, rwt; reg [2:0] rwn;
  wire [9:0] rbase = 10'({rc, 2'b00} - {hs[29:2], hs[1:0]});
  wire [3:0] rmsk;
  genvar gm_;
  generate for (gm_ = 0; gm_ < 4; gm_ = gm_ + 1) begin : msk
    assign rmsk[gm_] = ({rc, 2'(gm_)} >= hs) && ({rc, 2'(gm_)} <= hl);
  end endgenerate
  wire bstep = (DMA != 0) && hact && (!rin || rwn != 3'd4);
  wire bdone = bstep && (bk == r1[27:5]);
  // in-flight FIFO {tag4, base10, mask4}
  reg [17:0] mf [0:MF-1]; reg [MA-1:0] mh, mt; reg [MA:0] mn;
  reg [CW-1:0] lcr;

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
  wire go_d  = (DMA != 0) && idle && !iss_v && !smh && !sreq && rwn != 3'd0 && mn != (MA+1)'(MF);
  wire sacc  = pend && v_d && k_rdy_q && sr;
  always @(posedge ck or negedge rn)
    if (!rn) begin v <= 1'b0; pend <= 1'b0; v_d <= 1'b0; k_rdy_q <= 1'b0; sr <= 1'b0; smh <= 1'b0; end
    else begin
      k_rdy_q <= k_rdy; v_d <= v;
      if (iss_v && !idle) smh <= 1'b1; else if (go_sm) smh <= 1'b0;
      if (go_sm || go_s || go_d) begin v <= 1'b1; pend <= 1'b1; sr <= go_s; end
      else if (v) v <= 1'b0;
      else if (pend && v_d && k_rdy_q) pend <= 1'b0;
      else if (pend && !v_d) v <= 1'b1;
    end
  always @(posedge ck) begin
    if (iss_v && !idle) smd <= iss_d;
    if (go_sm) {t, ln, a} <= (iss_v && idle) ? iss_d : smd;
    else if (go_s) begin a <= {sa[29:2], 2'b00}; ln <= 4'd4; t <= {2'b11, jn[11:2], 5'd0}; end
    else if (go_d) begin a <= {rw[rwh][45:18], 2'b00}; ln <= 4'd4; t <= {2'b11, 10'd0, 1'b1, 4'd0}; end
  end
  assign k_v = v; assign k_addr = a; assign k_len = ln; assign k_tag = t;
  // ---- responses: raw capture + aligned register (ot_svs_pc); stream beats get {idx, valid, slot} in tag[4:0]
  reg kr_v_q, bv; reg [16:0] t_r, bt; reg [3:0] bb_r, bb; reg [255:0] d_r, bd;
  wire d_beat = (DMA != 0) && t_r[16:15] == 2'b11 && t_r[4];     // a DMA row beat (beat j = sector j of the row)
  wire s_beat = t_r[16:15] == 2'b11 && !d_beat;
  wire [17:0] dmh = mf[mh];
  wire dkeep = dmh[bb_r[1:0]];                                        // the sector lies in its request
  wire dcap = kr_v_q && rdy_q2 && d_beat;
  wire demit = dcap && dkeep;
  reg [1:0] dcnt;
  wire [11:0] bj4 = {t_r[14:5], 2'b00};
  wire [14:0] rr = row0 + 15'(bj4 >> 10);
  wire [1:0] slot = bb_r[1:0] ^ rr[1:0];
  wire [11:0] bj = {t_r[14:5], slot};
  wire svalid = idx || (bj < nsec);
  always @(posedge ck or negedge rn) if (!rn) begin kr_v_q <= 1'b0; bv <= 1'b0; end
    else begin kr_v_q <= kr_v && ((DMA == 0) || kr_rdy_o); bv <= kr_v_q && rdy_q2 && (!d_beat || dkeep); end
  always @(posedge ck) begin
    t_r <= kr_tag; bb_r <= kr_beat; d_r <= kr_data;
    bt <= s_beat ? {t_r[16:5], nocr, idx, svalid, slot} : d_beat ? {5'b11000, dmh[17:14], 8'(dmh[13:4] + 10'(bb_r[1:0]))} : t_r;
    bb <= d_beat ? {1'b1, bb_r[2:0]} : bb_r; bd <= d_r;
  end
  assign b_v = bv; assign b_t = bt; assign b_b = bb; assign b_d = bd;
  wire s_ret = bv && bt[16:15] == 2'b11 && !bb[3];   // a stream beat returned (counted at the aligned register)
  // ---- DMA sequential state
  wire [CW-1:0] lcr_n = lcr - (demit ? CW'(1) : CW'(0)) + (lc_v ? CW'(1) : CW'(0));
  always @(posedge ck) begin
    if (rq_iv) rqq[qt] <= rq_i;
    if (bstep && rin) rw[rwt] <= {rc, htg, rbase, rmsk};
    if (go_d) mf[mt] <= rw[rwh][17:0];
    rq_o <= rq_i;
  end
  always @(posedge ck or negedge rn)
    if (!rn) begin
      qh <= {QA{1'b0}}; qt <= {QA{1'b0}}; qn <= {(QA+1){1'b0}}; npop <= 8'd0; hact <= 1'b0; bk <= 23'd0;
      rwh <= 2'd0; rwt <= 2'd0; rwn <= 3'd0; mh <= {MA{1'b0}}; mt <= {MA{1'b0}}; mn <= {(MA+1){1'b0}};
      lcr <= CW'(CR0); kr_rdy_o <= 1'b0; dcnt <= 2'd0; rq_ov <= 1'b0; pm_o <= 8'd0;
    end else begin
      rq_ov <= rq_iv;
      if (rq_iv) qt <= qt + 1'b1;
      // block walker: start the head request at its first block, step one block a cycle, pop after the last
      if (!hact && qn != 0 && DMA != 0) begin hact <= 1'b1; bk <= r0[27:5]; end
      else if (bdone) begin hact <= 1'b0; qh <= qh + 1'b1; npop <= npop + 8'd1; end
      else if (bstep) bk <= bk + 23'd1;
      qn <= qn + (rq_iv ? 1'b1 : 1'b0) - (bdone ? 1'b1 : 1'b0);
      if (bstep && rin) rwt <= rwt + 2'd1;
      if (go_d) rwh <= rwh + 2'd1;
      rwn <= rwn + ((bstep && rin) ? 3'd1 : 3'd0) - (go_d ? 3'd1 : 3'd0);
      if (go_d) mt <= mt + 1'b1;
      if (dcap) dcnt <= dcnt + 2'd1;
      if (dcap && dcnt == 2'd3) mh <= mh + 1'b1;
      mn <= mn + (go_d ? 1'b1 : 1'b0) - ((dcap && dcnt == 2'd3) ? 1'b1 : 1'b0);
      lcr <= lcr_n;
      kr_rdy_o <= (DMA == 0) || (lcr_n >= CW'(2));
      // min chain: the older pop count (counts within a 128 window: the request unit admits <= QD - 1 ahead)
      pm_o <= (END != 0 || $signed(npop - pm_i) < 0) ? npop : pm_i;
    end
  // ---- stream engine
  always @(posedge ck or negedge rn)
    if (!rn) begin act <= 1'b0; ph <= 1'b0; idx <= 1'b0; nocr <= 1'b1; mine <= 1'b0; jn <= 0; jr <= 0; nob <= 0; cred <= 8'(CRR);
                   do_v <= 1'b0; dno_ok <= 1'b0; dno_ph <= 1'b0; end
    else begin
      do_v <= di_v;
      cred <= cred - ((sacc && !nocr) ? 8'd1 : 8'd0) + (cr_v ? 8'd1 : 8'd0);
      if (di_v) begin
        {ph, idx, nocr} <= di_d[61:59]; mine <= di_d[PCID]; act <= di_d[PCID];
        jn <= 0; jr <= 0; nob <= 0;    // cred persists: a credit returned after a stream ended still counts
      end else begin
        if (sacc) jn <= jn + 12'd4;
        if (s_ret) jr <= jr + 13'd1;
        nob <= nob + (sacc ? 7'd4 : 7'd0) - (s_ret ? 7'd1 : 7'd0);
        if (act && pdone) act <= 1'b0;
      end
      // done chain: every PC upstream finished in the same phase, and this one
      dno_ok <= ((END != 0) ? 1'b1 : (dni_ok && dni_ph == ph)) && pdone && !di_v;
      dno_ph <= ph;
    end
  always @(posedge ck) if (di_v) {row0, nsec} <= di_d[58:32];
  always @(posedge ck) if (di_v) do_d <= di_d;
endmodule

module ot_svs_grp #(parameter integer K = 0, parameter integer DMA = 0) (
  input wire ck, input wire rst, input wire rn,
  input wire [3:0] sv_i, input wire [4*277-1:0] sq_i,     // stream beats of PCs 4K .. 4K+3 (tag 11)
  input wire [1:0] kq,                                     // {fclk, v}: one line credit, in row order
  input wire sg_v, input wire [12:0] sg_d,                 // the running stream's load tag (from the e port)
  output wire [3:0] cr,                                    // credit pulse to PC 4K + j
  output wire [1101:0] ks,                                 // {fclk x3, meta64, row1024, rq10, v}
  output wire ovf,                                         // a beat found its row buffer still full / credit queue overflow (never)
  // DMA stream v2 (hbm-phys [svc] 2026-10-10): the DMA beats of PCs 4K .. 4K+3 (bb[3] = 1, bt = {11000, tag, idx}, only
  // sectors inside their request, a lane credit already spent at the PC) leave registered on their lane of the group's
  // port dd (lane j at [270j +: 270] = {v, fault 0, tag4, idx8, data256}); the front's credit pulses dc go back to
  // the PCs registered (dcr, one chain a PC).  DMA = 0: dd = 0, dcr = 0, and every beat is a PS beat as before.
  output reg [4*270-1:0] dd, input wire [3:0] dc, output reg [3:0] dcr);
  // hbm-forks 2026-10-09 (svc SE_s2 routed c_rs13_1.q -> u_gp3.b -53.9 ps: a beat's index bits fanned out to the 2 x 4
  // row-buffer write enables across the buffer array straight from the chain's last stage): the beat lands in the
  // group unit's own input register (sv / sq, at the unit) with its write enables pre-decoded one-hot (we1h), and is
  // written one edge later (+1 cycle on the stream path; the stream beats carry no backpressure)
  reg [3:0] sv; reg [4*277-1:0] sq; reg [3:0] we1h [0:3];
  wire [3:0] dm;                                           // the beat is a DMA lane beat
  genvar gd_;
  generate for (gd_ = 0; gd_ < 4; gd_ = gd_ + 1) begin : gdm assign dm[gd_] = (DMA != 0) && sq[gd_*277 + 259]; end endgenerate
  integer dl_;
  always @(posedge ck or negedge rn)
    if (!rn) begin dd <= {4*270{1'b0}}; dcr <= 4'd0; end
    else begin
      dcr <= (DMA != 0) ? dc : 4'd0;
      for (dl_ = 0; dl_ < 4; dl_ = dl_ + 1)
        if (sv[dl_] && dm[dl_]) dd[dl_*270 +: 270] <= {1'b1, 1'b0, sq[dl_*277 + 268 +: 4], sq[dl_*277 + 260 +: 8], sq[dl_*277 +: 256]};
        else dd[dl_*270 + 269] <= 1'b0;
    end
  integer pi_;
  always @(posedge ck or negedge rn)
    if (!rn) sv <= 4'd0;
    else sv <= sv_i;
  always @(posedge ck) begin
    sq <= sq_i;
    for (pi_ = 0; pi_ < 4; pi_ = pi_ + 1) we1h[pi_] <= 4'd1 << sq_i[pi_*277+260 +: 2];
  end
  reg [255:0] b [0:3][0:1][0:3];
  reg [3:0] sm [0:3][0:1];
  reg [2:0] cnt [0:3][0:1];
  reg [9:0] rq [0:3][0:1];
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
  // hbm-forks 2026-10-09 (route SW_s1 PREROUTE_MARGIN reg2reg -815 ps: rs -> rdy -> rotate / priority -> sel -> the
  // 8:1 x 1,024-b row mux and the credit-queue write): two stages -- A picks the row (sel, its slot) and frees it,
  // B reads the picked buffer into the port register one edge later (+1 row cycle; a beat landing in the freed slot
  // at B's edge is written after B samples it)
  reg av; reg [1:0] asel; reg aslot; reg anc;
  always @(posedge ck) if (sg_v) lt <= sg_d;
  always @(posedge ck or negedge rn)
    if (!rn) begin
      for (p = 0; p < 4; p = p + 1) begin full[p] <= 2'b00; ws[p] <= 1'b0; rs[p] <= 1'b0;
        for (s = 0; s < 2; s = s + 1) begin cnt[p][s] <= 3'd0; sm[p][s] <= 4'd0; end end
      rr <= 2'd0; ov <= 1'b0; ovb <= 1'b0; av <= 1'b0;
    end else begin
      av <= any; ov <= av;
      if (any) begin rr <= sel + 2'd1; full[sel][rs[sel]] <= 1'b0; rs[sel] <= ~rs[sel]; end
      for (p = 0; p < 4; p = p + 1) if (sv[p] && !dm[p]) begin
        if (full[p][ws[p]] && !(any && sel == p && rs[p] == ws[p])) ovb <= 1'b1;
        sm[p][ws[p]] <= ((cnt[p][ws[p]] == 3'd0) ? 4'd0 : sm[p][ws[p]]) |
                        (sq[p*277+260+2] ? (4'd1 << sq[p*277+260 +: 2]) : 4'd0);
        if (cnt[p][ws[p]] == 3'd3) begin
          cnt[p][ws[p]] <= 3'd0; full[p][ws[p]] <= 1'b1; ws[p] <= ~ws[p];
        end else cnt[p][ws[p]] <= cnt[p][ws[p]] + 3'd1;
      end
    end
  always @(posedge ck) begin
    for (p = 0; p < 4; p = p + 1) if (sv[p] && !dm[p]) begin
      for (s = 0; s < 4; s = s + 1) if (we1h[p][s]) b[p][ws[p]][s] <= sq[p*277 +: 256];
      rq[p][ws[p]] <= sq[p*277+265 +: 10];
      ix[p][ws[p]] <= sq[p*277+260+3];
      nc[p][ws[p]] <= sq[p*277+260+4];
    end
    if (any) begin asel <= sel; aslot <= rs[sel]; anc <= nc[sel][rs[sel]]; end
  end
  // Boundary payloads remain defined during idle after reset, before the first row.
  always @(posedge ck or negedge rn) if (!rn) begin od <= 1088'd0; ot <= 10'd0; end
  else if (av) begin
      od <= {31'd0, lt, ix[asel][aslot], 5'(4 * K + asel), sm[asel][aslot], 10'd0,
             b[asel][aslot][3], b[asel][aslot][2], b[asel][aslot][1], b[asel][aslot][0]};
      ot <= rq[asel][aslot];
  end
  wire fck; ot_svc_fclk_buf u_fk (.a(ck), .y(fck));
  assign ks = {fck, fck, fck, od, ot, ov};
  // credits: forwarded {fclk, v}, falling-edge capture + two-clock FIFO (as the e port); the PC of each credited row
  // sent is queued, and a returned credit goes to the PC at the head (the consumer returns credits in row order)
  localparam integer QD = 64;
  reg [1:0] pq [0:QD-1]; reg [5:0] qh, qt; reg [6:0] qn;
  wire push = av && !anc;
  reg cf_v; wire c_empty, c_full; wire [2:0] c_fr; wire cd;
  wire c_wck = ~kq[1];
  always @(posedge c_wck or negedge rst) if (!rst) cf_v <= 1'b0; else cf_v <= kq[0];
  ot_hbm_accel_cdc_fifo #(.W(1), .AW(3)) u_c (.wclk(c_wck), .wrst_n(rst), .we(cf_v), .wdata(1'b1), .full(c_full),
    .rd_freed(c_fr), .rclk(ck), .rrst_n(rn), .re(!c_empty && qn != 0), .rdata(cd), .empty(c_empty));
  wire pop = !c_empty && qn != 0;
  reg [3:0] crq; reg ovq;
  assign ovf = ovb | ovq;
  always @(posedge ck) if (push) pq[qt] <= asel;
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
