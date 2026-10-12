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
  input wire dw_ok, input wire [1:0] dw_ph, input wire de_ok, input wire [1:0] de_ph,   // drained-stream count mod 4
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
  reg [2:0] pend; reg ph, kdv;
  // tputx-svc 2026-10-11 (descriptor overlap): up to TWO streams in flight (the PCs hold two descriptor slots, indexed by
  // the descriptor's phase bit): stream N+1 launches as soon as stream N-1 is done, so the PCs issue N+1's reads while
  // they drain N (no drain bubble at a descriptor boundary).  Completion: each PC reports how many streams it has fully
  // drained (mod 4) on the done chains; a stream is done when every PC's count has passed it (an AND over equal counts).
  reg [1:0] lc, dc;                              // streams launched / streams completed (kd), mod 4
  wire [1:0] nout = lc - dc;                     // streams in flight (0..2)
  wire spend = (nout == 2'd2);                   // both PC descriptor slots busy
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
  // done: both chains agree on the drained count (a side without PCs agrees with any count)
  wire [1:0] cnt = (WEMPTY != 0) ? de_ph : dw_ph;
  wire w_ok = (WEMPTY != 0) || dw_ok;
  wire e_ok = (EEMPTY != 0) || (de_ok && (WEMPTY != 0 || de_ph == dw_ph));
  wire [1:0] cpass = cnt - dc;                   // streams the PCs have drained beyond the last kd (1..nout -> done)
  wire sdone = (nout != 2'd0) && w_ok && e_ok && (cpass != 2'd0) && (cpass <= nout);
  always @(posedge ck or negedge rn)
    if (!rn) begin pend <= 3'b000; spq_v <= 1'b0; lc <= 2'd0; dc <= 2'd0; ph <= 1'b0; sd_v <= 1'b0; sg_v <= 1'b0; kdv <= 1'b0; end
    else begin
      sd_v <= launch; sg_v <= launch; kdv <= 1'b0;
      if (queue_stream) spq_v <= 1'b1; else if (launch_q) spq_v <= 1'b0;
      if (ow_v) pend[0] <= 1'b1; else if (bw) pend[0] <= 1'b0;
      if (ok_v) pend[1] <= 1'b1; else if (bk) pend[1] <= 1'b0;
      if (oi_v) pend[2] <= 1'b1; else if (bi) pend[2] <= 1'b0;
      if (launch) begin lc <= lc + 2'd1; ph <= ~ph; end
      if (sdone) begin dc <= dc + 2'd1; kdv <= 1'b1; end        // one kd a cycle; a second completed stream follows
    end
  always @(posedge ck) if (queue_stream) spq_d <= ed;
  always @(posedge ck) if (launch) sg_d <= stream_d[83:71];
  always @(posedge ck) if (launch)
    sd_d <= {~ph, idx, stream_d[125], stream_d[16:2], idx ? nsec_i : stream_d[28:17], idx ? 32'hFFFF_FFFF : stream_d[60:29]};
  wire fck; ot_svc_fclk_buf u_fk (.a(ck), .y(fck));
  assign kd = {fck, kdv};
endmodule

module ot_svs_pcs #(parameter integer PCID = 0, parameter integer KNO = 31, parameter integer CRR = 16,
                    parameter integer END = 0) (
  input wire ck, input wire rn, input wire rdy_q2,
  input wire iss_v, input wire [50:0] iss_d,
  output wire k_v, input wire k_rdy, output wire [29:0] k_addr, output wire [3:0] k_len, output wire [16:0] k_tag,
  input wire kr_v, input wire [16:0] kr_tag, input wire [3:0] kr_beat, input wire [255:0] kr_data,
  output wire b_v, output wire [16:0] b_t, output wire [3:0] b_b, output wire [255:0] b_d,
  input wire di_v, input wire [61:0] di_d, output reg do_v, output reg [61:0] do_d,
  input wire dni_ok, input wire [1:0] dni_ph, output reg dno_ok, output reg [1:0] dno_ph,
  input wire cr_v);
  // tputx-svc 2026-10-11 (SVC.STREAM throughput):
  //  * PER-PC READ REORDER BUFFER: stream beats are written into a 128-sector 1R1W SRAM at their position in the PC's
  //    sector sequence (mod 128) and drained in that order, so a PC's stream beats leave in order whatever order the
  //    controller returns them in (FR-FCFS reorder window): ot_svs_grp's in-order row assembly is exact by construction.
  //    The ROB is the outstanding window: KNO reads x 4 sectors <= 124 (KNO 15 -> 31 = BW x latency).
  //  * Credits are consumed when a row's first sector is drained (not at read issue), so the CRR window spans only the
  //    pcs -> group -> consumer -> pcs loop, not HBM latency.
  //  * TWO DESCRIPTOR SLOTS (indexed by the descriptor's phase bit): the next stream's reads issue while the current one
  //    drains; the ROB sequence runs on across the boundary (slot base = running sum of nsec4).  The read tag carries the
  //    slot (tag[0]) so a returned beat finds its stream's row0; a drained beat carries it in beat[2] (the group's load
  //    tag select).  Done chain: the number of streams this PC has fully drained, mod 4.
  //  SM / KV / IK beats keep their one-stage path (cycle-identical).
  localparam integer ROBD = 128;
  initial if (4 * KNO + 4 > ROBD) $fatal(1, "ot_svs_pcs: KNO %0d exceeds the %0d-sector ROB", KNO, ROBD);
  // ---- descriptor slots ({ph, idx, nocr, row0 15, nsec 12, mask 32}); slot = ph
  reg sidx [0:1]; reg snocr [0:1]; reg [14:0] srow0 [0:1]; reg [11:0] snsec [0:1]; reg [6:0] sbase [0:1];
  reg [1:0] icnt, dcnt; reg ih, dh;              // issue / drain queues: count and head slot
  reg [6:0] nb;                                  // ROB sequence position of the next descriptor's first sector
  reg [1:0] dsc;                                 // streams fully drained, mod 4 (done chain)
  wire [11:0] di_nsec = di_d[PCID] ? di_d[43:32] : 12'd0;      // a PC outside the mask takes no sectors
  wire [11:0] di_nsec4 = (di_nsec + 12'd3) & ~12'd3;
  reg [11:0] jn; reg [12:0] jd; reg [7:0] nob; reg [7:0] cred; reg [6:0] gd;
  // tputx-svc 2026-10-12 (routes SE_s6 TT -3.6 / SW_s4 TT -60.7: dh -> snsec[dh] -> +3 -> compare -> dr, gd -> rv[gd]
  // 128:1 -> dr, and the segment-wide rdy_q2 net -> m_in -> out_d -> dr each fed dr's ~300-flop fanout in one cycle):
  // the drain decision now reads only registers -- dlim (the drain head's nsec4), rvh (rv[gd] as of this cycle, computed
  // one cycle ahead from rv / gd / gd1 / the ROB write) and m_in / s_in, registered from the raw response inputs
  // (kr_v, kr_tag[16:15]) and rl1 (= rdy_q: reset 0, 1 from the first edge; one cycle later it is rdy_q2).  Cycle-identical.
  reg [11:0] dlim; reg rvh; reg [6:0] gd1;
  reg rl1, m_in, s_in;
  always @(posedge ck or negedge rn) if (!rn) begin rl1 <= 1'b0; m_in <= 1'b0; s_in <= 1'b0; end
    else begin rl1 <= 1'b1; m_in <= kr_v && rl1 && (kr_tag[16:15] != 2'b11); s_in <= kr_v && rl1 && (kr_tag[16:15] == 2'b11); end
  wire [11:0] insec = snsec[ih];
  wire [11:0] dnsec = snsec[dh];
  wire [11:0] osnsec4 = (snsec[~dh] + 12'd3) & ~12'd3;     // the other slot's nsec4 (the next drain head)
  wire [11:0] jq = {jn[11:2], 2'b00};
  wire [29:0] sa; wire sf;
  ot_hbm_kport_map u_m (.pc(5'(PCID)), .bank({jq[9:7], jq[1:0]}), .row({4'd0, srow0[ih]} + 19'(jq >> 10)), .col(jq[6:2]),
    .s(sa), .fault(sf));
  wire sreq = (icnt != 2'd0) && (jn < insec) && (nob <= 8'(4 * KNO - 4));
  wire idone = (icnt != 2'd0) && (jn >= insec) && !(pend && sr);    // the issue head's reads all accepted
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
    else if (go_s) begin a <= {sa[29:2], 2'b00}; ln <= 4'd4; t <= {2'b11, jn[11:2], 4'd0, ih}; end
  end
  assign k_v = v; assign k_addr = a; assign k_len = ln; assign k_tag = t;
  // ---- responses: raw capture (pin flops); SM beats -> aligned register; stream beats -> ROB write register
  reg kr_v_q, bv; reg [16:0] t_r, bt; reg [3:0] bb_r, bb; reg [255:0] d_r, bd;
  wire s_beat = t_r[16:15] == 2'b11;
  wire tsl = t_r[0];                              // the beat's descriptor slot
  wire [11:0] bj4 = {t_r[14:5], 2'b00};
  wire [14:0] row0 = srow0[tsl];
  wire [14:0] rr = row0 + 15'(bj4 >> 10);
  wire [1:0] slot = bb_r[1:0] ^ rr[1:0];
  wire [11:0] bj = {t_r[14:5], slot};
  // m_in == kr_v_q && rdy_q2 && !s_beat (SM / KV / IK beat -> output register), registered above
  // s_in == kr_v_q && rdy_q2 && s_beat (stream beat -> ROB at its sequence position), registered above
  reg wv; reg [6:0] wa; reg [255:0] wd;
  always @(posedge ck or negedge rn) if (!rn) begin kr_v_q <= 1'b0; wv <= 1'b0; end
                                     else begin kr_v_q <= kr_v; wv <= s_in; end
  always @(posedge ck) begin
    t_r <= kr_tag; bb_r <= kr_beat; d_r <= kr_data;
    wa <= sbase[tsl] + bj[6:0]; wd <= d_r;
  end
  // ---- ROB: valid bitmap + 1R1W SRAM; drain in sequence order (R0 issue -> R1 capture -> output / hold)
  reg [ROBD-1:0] rv;
  reg rp_v, cap_v, h_v; reg [15:0] rp_j, cap_j, h_j; reg [255:0] cap_d, h_d;   // {nocr, idx, valid, desc slot, sector j 12}
  wire [255:0] rob_q;
  wire out_d = !m_in && (h_v || cap_v);           // a drained beat leaves this cycle (SM beats have priority)
  wire [1:0] nfl = 2'(rp_v) + 2'(cap_v) + 2'(h_v);
  wire row1 = (jd[1:0] == 2'd0);                  // the row's first sector takes the row's credit
  wire dlt = jd < {1'b0, dlim};
  wire dact = (dcnt != 2'd0) && dlt;
  wire dr = dact && rvh && ((nfl - 2'(out_d)) <= 2'd1) && (!row1 || snocr[dh] || cred != 0);
  wire ddone = (dcnt != 2'd0) && !dlt;                               // the drain head's sectors all read out
  wire rob_ovf = wv && rv[wa];                    // a sector landing on an undrained slot (never: nob <= 124)
  ot_sram_1r1w_128x256_m1_r2c2 u_rob (.clk(ck), .r_ce_in(dr), .r_addr_in(gd), .rd_out(rob_q),
    .w_ce_in(wv), .w_addr_in(wa), .wd_in(wd), .w_mask_in({256{1'b1}}),
    .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(16'd0));
`ifndef SYNTHESIS
  always @(posedge ck) if (rn && rob_ovf) $display("ERROR ot_svs_pcs PC %0d: ROB slot %0d overwritten", PCID, wa);
`endif
  always @(posedge ck or negedge rn)
    if (!rn) begin rv <= {ROBD{1'b0}}; rp_v <= 1'b0; cap_v <= 1'b0; h_v <= 1'b0; rvh <= 1'b0; end
    else begin
      rvh <= dr ? (rv[gd1] || (wv && wa == gd1)) : (rv[gd] || (wv && wa == gd));   // rv[gd] after this edge
      if (wv) rv[wa] <= 1'b1;
      if (dr) rv[gd] <= 1'b0;
      rp_v <= dr;
      h_v <= h_v ? (!out_d || cap_v) : (cap_v && !out_d);
      cap_v <= rp_v || (cap_v && h_v && !out_d);
    end
  always @(posedge ck) begin
    if (dr) rp_j <= {snocr[dh], sidx[dh], sidx[dh] || (jd[11:0] < dnsec), dh, jd[11:0]};
    if (rp_v) begin cap_d <= rob_q; cap_j <= rp_j; end            // capture flops: the macro's read data only
    if (h_v ? (out_d && cap_v) : (cap_v && !out_d)) begin h_d <= cap_d; h_j <= cap_j; end
  end
  wire [15:0] oj = h_v ? h_j : cap_j;
  wire [255:0] od = h_v ? h_d : cap_d;
  always @(posedge ck or negedge rn) if (!rn) bv <= 1'b0; else bv <= m_in || out_d;
  always @(posedge ck) begin
    bt <= m_in ? t_r : {2'b11, oj[11:2], oj[15:13], oj[1:0]};
    bb <= m_in ? bb_r : {1'b0, oj[12], oj[1:0]};
    bd <= m_in ? d_r : od;
  end
  assign b_v = bv; assign b_t = bt; assign b_b = bb; assign b_d = bd;
  // ---- stream engine: descriptor slots, issue head, drain head, done count
  always @(posedge ck or negedge rn)
    if (!rn) begin icnt <= 2'd0; dcnt <= 2'd0; ih <= 1'b0; dh <= 1'b0; nb <= 7'd0; dsc <= 2'd0; jn <= 0; jd <= 0; gd <= 7'd0; gd1 <= 7'd1; dlim <= 12'd0;
                   nob <= 0; cred <= 8'(CRR); do_v <= 1'b0; dno_ok <= 1'b0; dno_ph <= 2'd0; end
    else begin
      do_v <= di_v;
      cred <= cred - ((dr && row1 && !snocr[dh]) ? 8'd1 : 8'd0) + (cr_v ? 8'd1 : 8'd0);  // cred persists across streams
      nob <= nob + (sacc ? 8'd4 : 8'd0) - (dr ? 8'd1 : 8'd0);
      if (sacc) jn <= jn + 12'd4;
      if (dr) begin jd <= jd + 13'd1; gd <= gd + 7'd1; gd1 <= gd1 + 7'd1; end
      if (di_v) nb <= nb + di_nsec4[6:0];
      // issue queue: a new descriptor joins; the head retires when all its reads are accepted
      icnt <= icnt + (di_v ? 2'd1 : 2'd0) - (idone ? 2'd1 : 2'd0);
      if (idone) begin ih <= ~ih; jn <= 0; end
      else if (di_v && icnt == 2'd0) ih <= di_d[61];
      // drain queue: the head retires when all its sectors are read out of the ROB and the output pipe is empty
      dcnt <= dcnt + (di_v ? 2'd1 : 2'd0) - ((ddone && nfl == 2'd0) ? 2'd1 : 2'd0);
      if (ddone && nfl == 2'd0) begin dh <= ~dh; jd <= 0; dsc <= dsc + 2'd1;
        dlim <= (di_v && di_d[61] != dh) ? di_nsec4 : osnsec4; end
      else if (di_v && dcnt == 2'd0) begin dh <= di_d[61]; dlim <= di_nsec4; end
      // done chain: every PC upstream has drained as many streams as this one
      dno_ok <= (END != 0) ? 1'b1 : (dni_ok && dni_ph == dsc);
      dno_ph <= dsc;
    end
  always @(posedge ck) if (di_v) begin
    sidx[di_d[61]] <= di_d[60]; snocr[di_d[61]] <= di_d[59]; srow0[di_d[61]] <= di_d[58:44];
    snsec[di_d[61]] <= di_nsec; sbase[di_d[61]] <= nb;
  end
  always @(posedge ck) if (di_v) do_d <= di_d;
endmodule

module ot_svs_grp #(parameter integer K = 0) (
  input wire ck, input wire rst, input wire rn,
  input wire [3:0] sv_i, input wire [4*277-1:0] sq_i,     // stream beats of PCs 4K .. 4K+3 (tag 11)
  input wire [1:0] kq,                                     // {fclk, v}: one line credit, in row order
  input wire sg_v, input wire [12:0] sg_d,                 // the running stream's load tag (from the e port)
  output wire [3:0] cr,                                    // credit pulse to PC 4K + j
  output wire [1101:0] ks,                                 // {fclk x3, meta64, row1024, rq10, v}
  output wire ovf);                                        // a beat found its row buffer still full / credit queue overflow (never)
  // hbm-forks 2026-10-09 (svc SE_s2 routed c_rs13_1.q -> u_gp3.b -53.9 ps: a beat's index bits fanned out to the 2 x 4
  // row-buffer write enables across the buffer array straight from the chain's last stage): the beat lands in the
  // group unit's own input register (sv / sq, at the unit) with its write enables pre-decoded one-hot (we1h), and is
  // written one edge later (+1 cycle on the stream path; the stream beats carry no backpressure)
  reg [3:0] sv; reg [4*277-1:0] sq; reg [3:0] we1h [0:3];
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
  reg rph [0:3][0:1];                                      // the row's descriptor slot (beat[2]): its stream's load tag
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
  reg ov, ovb; reg [1087:0] od; reg [9:0] ot; reg [12:0] lt [0:1]; reg gph;
  // hbm-forks 2026-10-09 (route SW_s1 PREROUTE_MARGIN reg2reg -815 ps: rs -> rdy -> rotate / priority -> sel -> the
  // 8:1 x 1,024-b row mux and the credit-queue write): two stages -- A picks the row (sel, its slot) and frees it,
  // B reads the picked buffer into the port register one edge later (+1 row cycle; a beat landing in the freed slot
  // at B's edge is written after B samples it)
  reg av; reg [1:0] asel; reg aslot; reg anc;
  // tputx-svc 2026-10-11: two streams may be in flight (descriptor overlap): one load tag per descriptor slot; the e port
  // sends a stream's tag at its launch and launches alternate slots, so the slot of the k-th launch is k mod 2 (gph)
  always @(posedge ck or negedge rn) if (!rn) gph <= 1'b0; else if (sg_v) gph <= ~gph;
  always @(posedge ck) if (sg_v) lt[~gph] <= sg_d;
  always @(posedge ck or negedge rn)
    if (!rn) begin
      for (p = 0; p < 4; p = p + 1) begin full[p] <= 2'b00; ws[p] <= 1'b0; rs[p] <= 1'b0;
        for (s = 0; s < 2; s = s + 1) begin cnt[p][s] <= 3'd0; sm[p][s] <= 4'd0; end end
      rr <= 2'd0; ov <= 1'b0; ovb <= 1'b0; av <= 1'b0;
    end else begin
      av <= any; ov <= av;
      if (any) begin rr <= sel + 2'd1; full[sel][rs[sel]] <= 1'b0; rs[sel] <= ~rs[sel]; end
      for (p = 0; p < 4; p = p + 1) if (sv[p]) begin
        if (full[p][ws[p]] && !(any && sel == p && rs[p] == ws[p])) ovb <= 1'b1;
        sm[p][ws[p]] <= ((cnt[p][ws[p]] == 3'd0) ? 4'd0 : sm[p][ws[p]]) |
                        (sq[p*277+260+2] ? (4'd1 << sq[p*277+260 +: 2]) : 4'd0);
        if (cnt[p][ws[p]] == 3'd3) begin
          cnt[p][ws[p]] <= 3'd0; full[p][ws[p]] <= 1'b1; ws[p] <= ~ws[p];
        end else cnt[p][ws[p]] <= cnt[p][ws[p]] + 3'd1;
      end
    end
  always @(posedge ck) begin
    for (p = 0; p < 4; p = p + 1) if (sv[p]) begin
      for (s = 0; s < 4; s = s + 1) if (we1h[p][s]) b[p][ws[p]][s] <= sq[p*277 +: 256];
      rq[p][ws[p]] <= sq[p*277+265 +: 10];
      ix[p][ws[p]] <= sq[p*277+260+3];
      nc[p][ws[p]] <= sq[p*277+260+4];
      rph[p][ws[p]] <= sq[p*277+256+2];
    end
    if (any) begin asel <= sel; aslot <= rs[sel]; anc <= nc[sel][rs[sel]]; end
  end
  // Boundary payloads remain defined during idle after reset, before the first row.
  always @(posedge ck or negedge rn) if (!rn) begin od <= 1088'd0; ot <= 10'd0; end
  else if (av) begin
      od <= {31'd0, lt[rph[asel][aslot]], ix[asel][aslot], 5'(4 * K + asel), sm[asel][aslot], 10'd0,
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
