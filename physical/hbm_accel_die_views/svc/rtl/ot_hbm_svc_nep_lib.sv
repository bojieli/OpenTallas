`timescale 1ps/1fs
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hbm-phys [svc-ep] 2026-10-10: the PS NATIVE ENDPOINT (loader memory port lq / lr on the per-PC-stream svc segments).
// Lead decision (b) 10-10: every path end to end -- the loader's kport (ot_hfd_loader_kport, CP record fetch, DMA mover,
// loader) reaches HBM through the routed PS segments, not only through the behavioural ot_hbm_svc_core_native.
//
// Protocol on the die chains (unchanged widths; ot_hfd_loader_kport field order):
//   lq 350 = {native_len 4, outer_write_pending, native_rsp_rdy, native_tag 16, native_addr 30, native_pc 5, native_v,
//             wq_d 292 = {data 256, addr 30, pc 5, wr_v}}                           (+ forwarded clock, loader -> svc)
//   lr 293 = {wq_source_fault, WR_G 8, native_fault, rsp_data 256, rsp_beat 4, rsp_tag 16, rsp_pc 5, rsp_v, native_rdy}
//   READS: native_v pulses against NQ credits (native_rdy = one credit pulse a pop); a transaction is 1..4 sectors of one
//          PC row (the kport splits at row boundaries); up to NO in flight a stack, one a PC; responses one sector a beat
//          in ACCEPTANCE order (an in-order return ring of RING sectors, reserved at issue), native_rsp_rdy ignored (the
//          kport reserves its response room).
//   WRITES: one sector a packet; WR_G = 8-bit Gray count of write packets popped from the WQ-deep write queue into
//          their PC queue (the kport holds WQ credits a stack and gets one back a WR_G step); popped = visible: a PC's
//          queue issues in arrival order and the outward chain is FIFO, so a later read of that PC sees the write.
//          A write pops only when no read is queued here (no write overtakes an older read).
// Structure: one endpoint (ot_svn_ep) in the band under the loader chain (band 3) and one station (ot_svn_st) beside
// every PC unit; the endpoint drives two OUTWARD daisy chains (west / east of it, OW bits: one request flit a cycle)
// and takes two INWARD merge chains (IW bits: one flit a cycle, a station inserts into an empty slot).  Flits:
//   outward {0, data 128, slot 7, len 3, addr 30, pc 5, op 2, v} (177) op 1 read, 2 write low half (+addr), 3 write high half
//   inward  {data 128, last, slot 7, half, pc 5, op 2, v} (145) op 1 read data half, 2 queue-entry free (credit)
// A station queue holds QD entries (credited by the endpoint per PC); a read buffers its <= 4 returning beats.
// Rate a stack: one 128-bit flit a cycle each way -> 16 B/cycle reads, 16 B/cycle writes (2 flits a sector).
// ---------------------------------------------------------------------------------------------------------------------
module ot_svn_ep #(parameter integer NO = 32, parameter integer NQ = 4, parameter integer RING = 128,
                   parameter integer WQ = 16, parameter integer QD = 4, parameter [31:0] WMASK = 32'h0000_0000,
                   parameter integer MUT = 0) (     // MUT 1: drop every 5th read-data flit; 2: return beats out of
                                                    // order (head skips); 3: write lands at the wrong PC
  input wire ck, input wire rst, input wire rn,
  input wire [350:0] lq,                            // {fclk, lq 350}
  output wire [293:0] lr,                           // {fclk, lr 293}
  output reg [176:0] ow_w, output reg [176:0] ow_e,
  input wire [144:0] iw_w, input wire [144:0] iw_e,
  output wire fault);
  // ---------------------------------------------------------------- capture (forwarded clock, falling edge)
  wire l_wck = ~lq[350];
  reg q_nv, q_wv; reg [54:0] q_n; reg [290:0] q_w;
  always @(posedge l_wck or negedge rst) if (!rst) begin q_nv <= 1'b0; q_wv <= 1'b0; end
    else begin q_nv <= lq[292]; q_wv <= lq[0]; end
  always @(posedge l_wck) begin q_n <= {lq[349:346], lq[343:328], lq[327:298], lq[297:293]}; q_w <= lq[291:1]; end
  // {len4, tag16, addr30, pc5}
  wire n_empty, n_full, w_empty, w_full; wire [2:0] n_fr, w_fr; wire [54:0] nh; wire [290:0] wh;
  wire n_pop, w_pop;
  ot_hbm_accel_cdc_fifo #(.W(55), .AW($clog2(NQ))) u_nq (.wclk(l_wck), .wrst_n(rst), .we(q_nv), .wdata(q_n),
    .full(n_full), .rd_freed(n_fr), .rclk(ck), .rrst_n(rn), .re(n_pop), .rdata(nh), .empty(n_empty));
  ot_hbm_accel_cdc_fifo #(.W(291), .AW($clog2(WQ))) u_wq (.wclk(l_wck), .wrst_n(rst), .we(q_wv), .wdata(q_w),
    .full(w_full), .rd_freed(w_fr), .rclk(ck), .rrst_n(rn), .re(w_pop), .rdata(wh), .empty(w_empty));
  reg ovf; always @(posedge l_wck or negedge rst) if (!rst) ovf <= 1'b0;
    else if ((q_nv && n_full) || (q_wv && w_full)) ovf <= 1'b1;        // the loader overran its credits: fail closed
  // ---------------------------------------------------------------- per-PC state
  localparam integer RA = $clog2(RING), FA = $clog2(NO);
  reg [2:0] pcr [0:31];                 // free station queue entries a PC
  reg [31:0] rbusy;                     // a read outstanding at the PC (one a PC)
  // owner FIFO {pc 5, tag 16, len 3, slot RA}
  reg [4:0] o_pc [0:NO-1]; reg [15:0] o_tg [0:NO-1]; reg [2:0] o_ln [0:NO-1]; reg [RA-1:0] o_sl [0:NO-1];
  reg [FA-1:0] oh, ot; reg [FA:0] on;
  reg [RA:0] rh, rt;                     // ring head / tail (sectors), free = RING - (rt - rh)
  // ---------------------------------------------------------------- issue (one new op a cycle; a write's high flit
  // owns its branch the cycle after)
  wire [4:0] n_pc = nh[4:0]; wire [29:0] n_ad = nh[34:5]; wire [15:0] n_tg = nh[50:35];
  wire [2:0] n_ln = (nh[54:51] == 4'd0) ? 3'd1 : (nh[54:51] > 4'd4) ? 3'd4 : nh[53:51];
  wire [4:0] w_pc = wh[4:0]; wire [29:0] w_ad = wh[34:5]; wire [255:0] w_dt = wh[290:35];
  wire [RA:0] used = rt - rh;
  reg hb_v, hb_e; reg [4:0] hb_pc; reg [127:0] hb_d;      // pending write high flit
  wire n_e = !WMASK[n_pc], w_e = !WMASK[w_pc];
  wire n_ok = !n_empty && on != (FA+1)'(NO) && ((RA+2)'(used) + (RA+2)'(n_ln) <= (RA+2)'(RING)) &&
              pcr[n_pc] != 3'd0 && !rbusy[n_pc] && !(hb_v && hb_e == n_e);
  // a write pops only behind every queued read (no write overtakes an older read: WAR order per PC); the kport admits
  // no read while a write is unpopped (RAW), so the stack's native ops reach each PC queue in arrival order
  wire w_ok = !w_empty && n_empty && pcr[w_pc] != 3'd0 && !hb_v;
  reg pri;                                   // round robin read / write
  assign n_pop = n_ok && (!w_ok || pri);
  assign w_pop = w_ok && !n_pop;
  wire [4:0] w_pcm = (MUT == 3) ? w_pc ^ 5'd1 : w_pc;
  reg nrdy, wr_step;
  // ---------------------------------------------------------------- inward
  wire [1:0] i_op_w = iw_w[2:1], i_op_e = iw_e[2:1];
  wire [4:0] i_pc_w = iw_w[7:3], i_pc_e = iw_e[7:3];
  wire fr_w = iw_w[0] && i_op_w == 2'd2, fr_e = iw_e[0] && i_op_e == 2'd2;
  wire dt_w = iw_w[0] && i_op_w == 2'd1, dt_e = iw_e[0] && i_op_e == 2'd1;
  reg [7:0] dcnt;
  wire drop_w = (MUT == 1) && dcnt == 8'd4;
  reg [255:0] ring [0:RING-1]; reg [RING-1:0] vlo, vhi;
  // ---------------------------------------------------------------- return (in acceptance order)
  reg [2:0] bc;
  wire [RA-1:0] hs = o_sl[oh] + RA'(bc);
  wire [RA-1:0] hsm = (MUT == 2 && bc == 3'd0 && o_ln[oh] > 3'd1) ? hs + RA'(1) : hs;
  wire h_rdy = on != 0 && vlo[hsm] && vhi[hsm];
  wire h_last = h_rdy && (bc + 3'd1 == o_ln[oh]);
  reg rv; reg [4:0] rpc; reg [15:0] rtg; reg [3:0] rbt; reg [255:0] rdt;
  reg [7:0] wcnt;
  wire [7:0] wg = wcnt ^ (wcnt >> 1);
  integer p;
  always @(posedge ck or negedge rn)
    if (!rn) begin
      for (p = 0; p < 32; p = p + 1) pcr[p] <= 3'(QD);
      rbusy <= 32'd0; oh <= 0; ot <= 0; on <= 0; rh <= 0; rt <= 0; hb_v <= 1'b0; pri <= 1'b0; nrdy <= 1'b0;
      ow_w <= 177'd0; ow_e <= 177'd0; vlo <= 0; vhi <= 0; bc <= 3'd0; rv <= 1'b0; wcnt <= 8'd0; dcnt <= 8'd0;
    end else begin
      nrdy <= n_pop; rv <= h_rdy;
      if (n_pop || w_pop) pri <= ~pri;
      // outward flits
      ow_w <= 177'd0; ow_e <= 177'd0;
      if (hb_v) begin
        if (hb_e) ow_e <= {1'b0, hb_d, 7'd0, 3'd0, 30'd0, hb_pc, 2'd3, 1'b1}; else ow_w <= {1'b0, hb_d, 7'd0, 3'd0, 30'd0, hb_pc, 2'd3, 1'b1};
        hb_v <= 1'b0;
      end
      if (n_pop) begin
        if (n_e) ow_e <= {129'd0, 7'(rt[RA-1:0]), n_ln, n_ad, n_pc, 2'd1, 1'b1}; else ow_w <= {129'd0, 7'(rt[RA-1:0]), n_ln, n_ad, n_pc, 2'd1, 1'b1};
        o_pc[ot] <= n_pc; o_tg[ot] <= n_tg; o_ln[ot] <= n_ln; o_sl[ot] <= rt[RA-1:0];
        ot <= (ot == FA'(NO - 1)) ? {FA{1'b0}} : ot + 1'b1;
        rt <= rt + (RA+1)'(n_ln); rbusy[n_pc] <= 1'b1;
      end
      if (w_pop) begin
        if (w_e) ow_e <= {1'b0, w_dt[127:0], 7'd0, 3'd1, w_ad, w_pcm, 2'd2, 1'b1}; else ow_w <= {1'b0, w_dt[127:0], 7'd0, 3'd1, w_ad, w_pcm, 2'd2, 1'b1};
        hb_v <= 1'b1; hb_e <= w_e; hb_pc <= w_pcm; hb_d <= w_dt[255:128]; wcnt <= wcnt + 8'd1;
      end
      // per-PC credits: - issue, + free flits (both chains)
      for (p = 0; p < 32; p = p + 1)
        pcr[p] <= pcr[p] - (((n_pop && n_pc == p) || (w_pop && w_pc == p)) ? 3'd1 : 3'd0)
                          + ((fr_w && i_pc_w == p) ? 3'd1 : 3'd0) + ((fr_e && i_pc_e == p) ? 3'd1 : 3'd0);
      // inward data halves
      if (dt_w) dcnt <= dcnt + 8'd1;
      if (dt_w && !drop_w) begin if (iw_w[8]) vhi[iw_w[9 +: RA]] <= 1'b1; else vlo[iw_w[9 +: RA]] <= 1'b1; end
      if (dt_e) begin if (iw_e[8]) vhi[iw_e[9 +: RA]] <= 1'b1; else vlo[iw_e[9 +: RA]] <= 1'b1; end
      if (dt_w && iw_w[16]) rbusy[i_pc_w] <= 1'b0;
      if (dt_e && iw_e[16]) rbusy[i_pc_e] <= 1'b0;
      // return
      if (h_rdy) begin
        vlo[hsm] <= 1'b0; vhi[hsm] <= 1'b0;
        bc <= h_last ? 3'd0 : bc + 3'd1;
        if (h_last) begin oh <= (oh == FA'(NO - 1)) ? {FA{1'b0}} : oh + 1'b1; rh <= rh + (RA+1)'(o_ln[oh]); end
      end
      on <= on + (n_pop ? 1'b1 : 1'b0) - (h_last ? 1'b1 : 1'b0);
    end
  always @(posedge ck) begin
    if (dt_w && !drop_w) begin if (iw_w[8]) ring[iw_w[9 +: RA]][255:128] <= iw_w[144:17]; else ring[iw_w[9 +: RA]][127:0] <= iw_w[144:17]; end
    if (dt_e) begin if (iw_e[8]) ring[iw_e[9 +: RA]][255:128] <= iw_e[144:17]; else ring[iw_e[9 +: RA]][127:0] <= iw_e[144:17]; end
    rpc <= o_pc[oh]; rtg <= o_tg[oh]; rbt <= {1'b0, bc}; rdt <= ring[hsm];
  end
  reg [7:0] wg_q; always @(posedge ck or negedge rn) if (!rn) wg_q <= 8'd0; else wg_q <= wg;
  wire fk; ot_svc_fclk_buf u_fk (.a(ck), .y(fk));
  assign fault = ovf;
  assign lr = {fk, 1'b0, wg_q, ovf, rdt, rbt, rtg, rpc, rv, nrdy};
endmodule

// station beside PC unit PCID: outward pass / capture, QD-entry queue, read beat buffer, inward merge
module ot_svn_st #(parameter integer PCID = 0, parameter integer QD = 4) (
  input wire ck, input wire rn,
  input wire [176:0] oi, output reg [176:0] oo,
  input wire [144:0] ii, output reg [144:0] io,
  // to the PC unit (ot_svs_pcsn native port)
  output wire n_v, output wire n_we, output wire [29:0] n_addr, output wire [3:0] n_len, output wire [255:0] n_wd,
  input wire n_take,
  input wire nb_v, input wire [3:0] nb_beat, input wire [255:0] nb_d,
  output reg ovf);
  wire mine = oi[0] && oi[7:3] == 5'(PCID);
  wire [1:0] op = oi[2:1];
  // write first half held until its high half follows (the next flit on this chain, same PC)
  reg wa_v; reg [29:0] wa_a; reg [127:0] wa_lo;
  // queue {we, addr30, len3, slot6, data256}
  localparam integer QA = (QD <= 2) ? 1 : $clog2(QD);
  reg qwe [0:QD-1]; reg [29:0] qa [0:QD-1]; reg [2:0] ql [0:QD-1]; reg [6:0] qs [0:QD-1]; reg [255:0] qd [0:QD-1];
  reg [QA-1:0] qh, qt; reg [QA:0] qn;
  wire push_r = mine && op == 2'd1, push_w = mine && op == 2'd3 && wa_v;
  wire push = push_r || push_w;
  assign n_v = qn != 0; assign n_we = qwe[qh]; assign n_addr = qa[qh]; assign n_len = {1'b0, ql[qh]}; assign n_wd = qd[qh];
  // read in progress: its slot / length, the buffered beats
  reg r_act; reg [6:0] r_sl; reg [2:0] r_ln; reg [255:0] rb [0:3]; reg [3:0] rbv;
  reg [2:0] snd; reg sh;                          // next beat to send and its half
  reg [2:0] frq;                                   // free flits owed
  wire own_d = r_act && rbv[snd[1:0]];
  wire own_f = frq != 3'd0;
  wire slot_free = !ii[0];
  wire send_f = slot_free && own_f;
  wire send_d = slot_free && !own_f && own_d;
  wire d_last = send_d && sh && (snd + 3'd1 == r_ln);
  always @(posedge ck or negedge rn)
    if (!rn) begin oo <= 177'd0; io <= 145'd0; wa_v <= 1'b0; qh <= 0; qt <= 0; qn <= 0; r_act <= 1'b0; rbv <= 4'd0;
                   snd <= 3'd0; sh <= 1'b0; frq <= 3'd0; ovf <= 1'b0; end
    else begin
      oo <= mine ? 177'd0 : oi;
      if (mine && op == 2'd2) begin wa_v <= 1'b1; wa_a <= oi[37:8]; wa_lo <= oi[175:48]; end
      else if (push_w) wa_v <= 1'b0;
      if (push) begin
        if (qn == (QA+1)'(QD)) ovf <= 1'b1;
        qt <= (qt == QA'(QD - 1)) ? {QA{1'b0}} : qt + 1'b1;
      end
      if (n_take) qh <= (qh == QA'(QD - 1)) ? {QA{1'b0}} : qh + 1'b1;
      qn <= qn + (push ? 1'b1 : 1'b0) - (n_take ? 1'b1 : 1'b0);
      frq <= frq + (n_take ? 3'd1 : 3'd0) - (send_f ? 3'd1 : 3'd0);
      if (n_take && !qwe[qh]) begin r_act <= 1'b1; r_sl <= qs[qh]; r_ln <= ql[qh]; snd <= 3'd0; sh <= 1'b0; end
      if (nb_v) rbv[nb_beat[1:0]] <= 1'b1;
      if (send_d) begin
        sh <= ~sh;
        if (sh) begin rbv[snd[1:0]] <= 1'b0; snd <= snd + 3'd1; end
        if (d_last) r_act <= 1'b0;
      end
      io <= !slot_free ? ii :
            send_f ? {128'd0, 1'b0, 7'd0, 1'b0, 5'(PCID), 2'd2, 1'b1} :
            send_d ? {sh ? rb[snd[1:0]][255:128] : rb[snd[1:0]][127:0], d_last, r_sl + 7'(snd), sh, 5'(PCID), 2'd1, 1'b1} :
            145'd0;
    end
  always @(posedge ck) begin
    if (push_r) begin qwe[qt] <= 1'b0; qa[qt] <= oi[37:8]; ql[qt] <= oi[40:38]; qs[qt] <= oi[47:41]; end
    if (push_w) begin qwe[qt] <= 1'b1; qa[qt] <= wa_a; ql[qt] <= 3'd1; qs[qt] <= 7'd0; qd[qt] <= {oi[175:48], wa_lo}; end
    if (nb_v) rb[nb_beat[1:0]] <= nb_d;
  end
endmodule
`default_nettype wire

// ot_svs_pcs + the native port (generated from ot_hbm_svc_ps_lib.sv ot_svs_pcs; [svc-ep] 2026-10-10)
`default_nettype none
module ot_svs_pcsn #(parameter integer PCID = 0, parameter integer KNO = 15, parameter integer CRR = 16,
                    parameter integer END = 0) (
  input wire ck, input wire rn, input wire rdy_q2,
  input wire iss_v, input wire [50:0] iss_d,
  output wire k_v, input wire k_rdy, output wire [29:0] k_addr, output wire [3:0] k_len, output wire [16:0] k_tag,
  input wire kr_v, input wire [16:0] kr_tag, input wire [3:0] kr_beat, input wire [255:0] kr_data,
  output wire b_v, output wire [16:0] b_t, output wire [3:0] b_b, output wire [255:0] b_d,
  input wire di_v, input wire [61:0] di_d, output reg do_v, output reg [61:0] do_d,
  input wire dni_ok, input wire dni_ph, output reg dno_ok, output reg dno_ph,
  input wire cr_v,
  // [svc-ep] native port (ot_svn_st): one queued native op, taken when the K register accepts it
  input wire n_v, input wire n_we, input wire [29:0] n_addr, input wire [3:0] n_len, input wire [255:0] n_wd,
  output wire n_take, output wire k_we, output wire [255:0] k_wdata, output wire [31:0] k_wstrb,
  output reg nb_v, output reg [3:0] nb_beat, output reg [255:0] nb_d);
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
  reg v, pend, v_d, k_rdy_q, sr, smh, nr, we; reg [29:0] a; reg [3:0] ln; reg [16:0] t; reg [50:0] smd;
  wire idle = !pend && !v;
  wire go_sm = (iss_v && idle) || (smh && idle);
  wire go_n  = idle && !iss_v && !smh && n_v;              // native before the stream engine, after SM
  wire go_s  = idle && !iss_v && !smh && !n_v && sreq;
  wire sacc  = pend && v_d && k_rdy_q && sr;
  always @(posedge ck or negedge rn)
    if (!rn) begin v <= 1'b0; pend <= 1'b0; v_d <= 1'b0; k_rdy_q <= 1'b0; sr <= 1'b0; smh <= 1'b0; nr <= 1'b0; we <= 1'b0; end
    else begin
      k_rdy_q <= k_rdy; v_d <= v;
      if (iss_v && !idle) smh <= 1'b1; else if (go_sm) smh <= 1'b0;
      if (go_sm || go_s || go_n) begin v <= 1'b1; pend <= 1'b1; sr <= go_s; nr <= go_n; we <= go_n && n_we; end
      else if (v) v <= 1'b0;
      else if (pend && v_d && k_rdy_q) pend <= 1'b0;
      else if (pend && !v_d) v <= 1'b1;
    end
  always @(posedge ck) begin
    if (iss_v && !idle) smd <= iss_d;
    if (go_sm) {t, ln, a} <= (iss_v && idle) ? iss_d : smd;
    else if (go_n) begin a <= n_addr; ln <= n_we ? 4'd1 : n_len; t <= {2'b11, 10'd0, 5'b10000}; end
    else if (go_s) begin a <= {sa[29:2], 2'b00}; ln <= 4'd4; t <= {2'b11, jn[11:2], 5'd0}; end
  end
  assign k_v = v; assign k_addr = a; assign k_len = ln; assign k_tag = t;
  assign n_take = pend && v_d && k_rdy_q && nr;
  assign k_we = we; assign k_wdata = n_wd; assign k_wstrb = {32{we}};   // n_wd is the station's queue head, held to the take
  // ---- responses: raw capture + aligned register (ot_svs_pc); stream beats get {idx, valid, slot} in tag[4:0]
  reg kr_v_q, bv; reg [16:0] t_r, bt; reg [3:0] bb_r, bb; reg [255:0] d_r, bd;
  wire s_beat = t_r[16:15] == 2'b11;
  wire [11:0] bj4 = {t_r[14:5], 2'b00};
  wire [14:0] rr = row0 + 15'(bj4 >> 10);
  wire [1:0] slot = bb_r[1:0] ^ rr[1:0];
  wire [11:0] bj = {t_r[14:5], slot};
  wire svalid = idx || (bj < nsec);
  wire n_beat = s_beat && t_r[4];
  always @(posedge ck or negedge rn) if (!rn) begin kr_v_q <= 1'b0; bv <= 1'b0; nb_v <= 1'b0; end
    else begin kr_v_q <= kr_v; bv <= kr_v_q && rdy_q2 && !n_beat; nb_v <= kr_v_q && rdy_q2 && n_beat; end
  always @(posedge ck) begin nb_beat <= bb_r; nb_d <= d_r; end
  always @(posedge ck) begin
    t_r <= kr_tag; bb_r <= kr_beat; d_r <= kr_data;
    bt <= s_beat ? {t_r[16:5], nocr, idx, svalid, slot} : t_r;
    bb <= bb_r; bd <= d_r;
  end
  assign b_v = bv; assign b_t = bt; assign b_b = bb; assign b_d = bd;
  wire s_ret = bv && bt[16:15] == 2'b11;          // a stream beat returned (counted at the aligned register)
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
`default_nettype wire

// [svc-ep] the PS PC unit with its native station (the generator's pc<p> unit in --nep segments): ot_svs_pcsn + ot_svn_st
`default_nettype none
module ot_svs_pcse #(parameter integer PCID = 0, parameter integer KNO = 15, parameter integer CRR = 16,
                     parameter integer END = 0, parameter integer QD = 4) (
  input wire ck, input wire rn, input wire rdy_q2,
  input wire iss_v, input wire [50:0] iss_d,
  output wire k_v, input wire k_rdy, output wire [29:0] k_addr, output wire [3:0] k_len, output wire [16:0] k_tag,
  output wire k_we, output wire [255:0] k_wdata, output wire [31:0] k_wstrb,
  input wire kr_v, input wire [16:0] kr_tag, input wire [3:0] kr_beat, input wire [255:0] kr_data,
  output wire b_v, output wire [16:0] b_t, output wire [3:0] b_b, output wire [255:0] b_d,
  input wire di_v, input wire [61:0] di_d, output wire do_v, output wire [61:0] do_d,
  input wire dni_ok, input wire dni_ph, output wire dno_ok, output wire dno_ph,
  input wire cr_v,
  input wire [176:0] oi, output wire [176:0] oo, input wire [144:0] ii, output wire [144:0] io, output wire n_ovf);
  wire n_v, n_we, n_take, nb_v; wire [29:0] n_addr; wire [3:0] n_len, nb_beat; wire [255:0] n_wd, nb_d;
  ot_svn_st #(.PCID(PCID), .QD(QD)) u_st (.ck(ck), .rn(rn), .oi(oi), .oo(oo), .ii(ii), .io(io), .n_v(n_v), .n_we(n_we),
    .n_addr(n_addr), .n_len(n_len), .n_wd(n_wd), .n_take(n_take), .nb_v(nb_v), .nb_beat(nb_beat), .nb_d(nb_d), .ovf(n_ovf));
  ot_svs_pcsn #(.PCID(PCID), .KNO(KNO), .CRR(CRR), .END(END)) u_pc (.ck(ck), .rn(rn), .rdy_q2(rdy_q2), .iss_v(iss_v),
    .iss_d(iss_d), .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .kr_v(kr_v), .kr_tag(kr_tag),
    .kr_beat(kr_beat), .kr_data(kr_data), .b_v(b_v), .b_t(b_t), .b_b(b_b), .b_d(b_d), .di_v(di_v), .di_d(di_d),
    .do_v(do_v), .do_d(do_d), .dni_ok(dni_ok), .dni_ph(dni_ph), .dno_ok(dno_ok), .dno_ph(dno_ph), .cr_v(cr_v),
    .n_v(n_v), .n_we(n_we), .n_addr(n_addr), .n_len(n_len), .n_wd(n_wd), .n_take(n_take), .k_we(k_we),
    .k_wdata(k_wdata), .k_wstrb(k_wstrb), .nb_v(nb_v), .nb_beat(nb_beat), .nb_d(nb_d));
endmodule
`default_nettype wire
