`timescale 1ps/1fs
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hbm-phys [svc] 2026-10-10: svc-side DMA STREAM v2 (agreed with hgi-1010/c, hgi-1010.log "AGREED svc DMA stream v2").
//
//   request  dq  = {v, tag 4, nsec 9, addr 37}  (front -> svc; addr = die byte address of the first 32-B sector, stack
//                  bits [36:35]; the stack-local sector s = addr[34:5] lives in PC r[4:0] ^ r[9:5] ^ r[14:10], r = s >> 2
//                  (ot_hbm_loader_kport_address)); nsec 1..256
//   accept       the front holds dq until it sees dq_rdy; dq_rdy is this unit's register, so a request is taken when
//                the pin-flopped dq is valid and dq_rdy was high one cycle earlier (the cycle the front sampled it)
//   data         32 lanes a stack, lane p = PC p, each {v, fault, tag 4, idx 8, data 256}: every sector of a request
//                leaves exactly once, on the lane of the PC that stores it; no ordering rule (the front places a beat by
//                tag + idx).  The lanes leave per GROUP: group k's port carries lanes 4k .. 4k+3 on the svc N face at
//                the group's x (die nets t_hgi_dsd<k> 1,080 b / f_hgi_dsc<k> 4 b), so nothing converges along the strip.
//   credit       per-lane pulses from the front, CR0 initial (= the front's lane buffer LD); never a beat without one.
//
// v1 (one 8-lane hub per stack with a reorder buffer, d8fc11d34) is retired: the 259-um strip cannot carry the
// convergence (cut capacity ~2.67 kb, 1.9-2.5 kb used on SW cuts 0-3) and it delivered 256 B/cycle a stack, not the
// 792 B/cycle of 3.80 TB/s a die.
//
// ot_svd_req: the request unit beside the e port.  Pin flops, an 8-deep request FIFO, registered dq_rdy; a request
// is broadcast on both sides' request daisy chains (rqw / rqe -> the PCs, ot_svs_pcs DMA = 1) when every PC's request
// queue has room: issued - min(pop counts) < QD - 1, the pop counts coming back on each side's min chain (a stale
// minimum is a smaller one: safe).
// ---------------------------------------------------------------------------------------------------------------------
module ot_svd_req #(parameter integer QD = 16, parameter integer WEMPTY = 0, parameter integer EEMPTY = 0) (
  input wire ck, input wire rn,
  input wire [50:0] dq, output wire dq_rdy,
  output reg rqw_v, output reg [42:0] rqw, output reg rqe_v, output reg [42:0] rqe,   // {tag4, nsec9, s30}
  input wire [7:0] pmw, input wire [7:0] pme);
  reg [50:0] dq_q; reg rdy_q, rdy_d;
  reg [49:0] rf [0:7]; reg [2:0] rf_h, rf_t; reg [3:0] rf_n;
  reg [7:0] iss, pmw_q, pme_q;
  wire take = dq_q[50] && rdy_d;
  wire [7:0] pmin = (WEMPTY != 0) ? pme_q : (EEMPTY != 0) ? pmw_q : ($signed(pmw_q - pme_q) < 0) ? pmw_q : pme_q;
  wire room = $signed(8'(iss - pmin)) < $signed(8'(QD - 1));
  wire pop = (rf_n != 4'd0) && room;
  wire [49:0] rh = rf[rf_h];
  always @(posedge ck or negedge rn)
    if (!rn) begin
      dq_q <= 51'd0; rdy_q <= 1'b0; rdy_d <= 1'b0; rf_h <= 3'd0; rf_t <= 3'd0; rf_n <= 4'd0; iss <= 8'd0;
      pmw_q <= 8'd0; pme_q <= 8'd0; rqw_v <= 1'b0; rqe_v <= 1'b0; rqw <= 43'd0; rqe <= 43'd0;
    end else begin
      dq_q <= dq; rdy_d <= rdy_q; pmw_q <= pmw; pme_q <= pme;
      if (take) rf_t <= rf_t + 3'd1;
      if (pop) rf_h <= rf_h + 3'd1;
      rf_n <= rf_n + (take ? 4'd1 : 4'd0) - (pop ? 4'd1 : 4'd0);
      // room for this cycle's take, the two requests the front may still send on rdy seen high, and one spare
      rdy_q <= (rf_n + (take ? 4'd1 : 4'd0) - (pop ? 4'd1 : 4'd0)) <= 4'd4;
      if (pop) iss <= iss + 8'd1;
      rqw_v <= pop && WEMPTY == 0; rqe_v <= pop && EEMPTY == 0;
      if (pop) begin rqw <= {rh[49:46], rh[45:37], rh[34:5]}; rqe <= {rh[49:46], rh[45:37], rh[34:5]}; end
    end
  always @(posedge ck) if (take) rf[rf_t] <= dq_q[49:0];
  assign dq_rdy = rdy_q;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_svd_stack: one stack's DMA stream for benches (the front's tb and tb_svd2_stack): the request unit, 32 PC units
// (ot_svs_pcs DMA = 1; PCs 0-15 west, 16-31 east of the request unit, each side one daisy chain, RH stages a link),
// 8 group units (ot_svs_grp DMA = 1, PC k -> group k / 4, PH stages each way between a PC and its group, like the c_rs
// / c_cr chains of the segments).  The PHY side of the 32 PCs is a port bundle (tb_svd_phy is the bench model).
// No SM / PS traffic here (iss_v / PS descriptors tied off): the DMA path alone.
// ---------------------------------------------------------------------------------------------------------------------
module ot_svd_stack #(parameter integer CR0 = 32, parameter integer QD = 16, parameter integer MF = 32,
                      parameter integer RH = 1, parameter integer PH = 3) (
  input wire ck, input wire rn,
  input wire [50:0] dq, output wire dq_rdy,
  output wire [32*270-1:0] dd, input wire [31:0] dd_cr,
  output wire [31:0] k_v, input wire [31:0] k_rdy, output wire [32*30-1:0] k_addr, output wire [32*4-1:0] k_len,
  output wire [32*17-1:0] k_tag,
  input wire [31:0] kr_v, output wire [31:0] kr_rdy, input wire [32*17-1:0] kr_tag, input wire [32*4-1:0] kr_beat,
  input wire [32*256-1:0] kr_data,
  output wire [7:0] ovf);
  wire rqw_v, rqe_v; wire [42:0] rqw, rqe; wire [7:0] pmw, pme;
  ot_svd_req #(.QD(QD)) u_rq (.ck(ck), .rn(rn), .dq(dq), .dq_rdy(dq_rdy), .rqw_v(rqw_v), .rqw(rqw), .rqe_v(rqe_v),
    .rqe(rqe), .pmw(pmw), .pme(pme));
  // chain wiring: position i on a side = distance from the request unit (west: PC 15 - i, east: PC 16 + i)
  wire [31:0] ri_v, ro_v; wire [42:0] ri [0:31]; wire [42:0] ro [0:31]; wire [7:0] po [0:31];
  wire [31:0] bv, sv; wire [276:0] bq [0:31]; wire [276:0] sq [0:31];
  wire [31:0] lc_g, lc_p;
  genvar p;
  generate for (p = 0; p < 32; p = p + 1) begin : pc
    localparam integer E = p >= 16;
    localparam integer POS = E ? p - 16 : 15 - p;
    localparam integer UP = E ? p - 1 : p + 1;          // nearer the request unit
    localparam integer DN = E ? p + 1 : p - 1;          // farther
    localparam integer LAST = POS == 15;
    wire [7:0] pmo_;
    if (POS == 0) begin : h
      ot_svc_vpipe #(.W(43), .N(RH)) u_r (.ck(ck), .rst_n(rn), .v(E ? rqe_v : rqw_v), .d(E ? rqe : rqw), .qv(ri_v[p]), .q(ri[p]));
      if (E) begin : e_ assign pme = pmo_; end else begin : w_ assign pmw = pmo_; end
    end else begin : n
      ot_svc_vpipe #(.W(43), .N(RH)) u_r (.ck(ck), .rst_n(rn), .v(ro_v[UP]), .d(ro[UP]), .qv(ri_v[p]), .q(ri[p]));
    end
    // min chain: each PC's registered pm_o (reset) feeds the PC nearer the request unit (one register a link)
    wire bvp; wire [16:0] bt; wire [3:0] bb; wire [255:0] bd; wire dov, dnook, dnoph; wire [61:0] dod;
    ot_svs_pcs #(.PCID(p), .END(LAST), .DMA(1), .CR0(CR0), .QD(QD), .MF(MF)) u_p (.ck(ck), .rn(rn), .rdy_q2(1'b1),
      .iss_v(1'b0), .iss_d(51'd0), .k_v(k_v[p]), .k_rdy(k_rdy[p]), .k_addr(k_addr[p*30 +: 30]), .k_len(k_len[p*4 +: 4]),
      .k_tag(k_tag[p*17 +: 17]), .kr_v(kr_v[p]), .kr_tag(kr_tag[p*17 +: 17]), .kr_beat(kr_beat[p*4 +: 4]),
      .kr_data(kr_data[p*256 +: 256]), .b_v(bvp), .b_t(bt), .b_b(bb), .b_d(bd), .di_v(1'b0), .di_d(62'd0), .do_v(dov),
      .do_d(dod), .dni_ok(1'b1), .dni_ph(1'b0), .dno_ok(dnook), .dno_ph(dnoph), .cr_v(1'b0), .kr_rdy_o(kr_rdy[p]),
      .rq_iv(ri_v[p]), .rq_i(ri[p]), .rq_ov(ro_v[p]), .rq_o(ro[p]), .pm_i(LAST ? 8'd0 : po[DN]), .pm_o(pmo_),
      .lc_v(lc_p[p]));
    assign po[p] = pmo_;
    ot_svc_vpipe #(.W(277), .N(PH)) u_s (.ck(ck), .rst_n(rn), .v(bvp), .d({bt, bb, bd}), .qv(sv[p]), .q(sq[p]));
    wire lq_; ot_svc_vpipe #(.W(1), .N(PH)) u_c (.ck(ck), .rst_n(rn), .v(lc_g[p]), .d(1'b0), .qv(lc_p[p]), .q(lq_));
  end endgenerate
  genvar g;
  generate for (g = 0; g < 8; g = g + 1) begin : gp
    wire [1101:0] ks; wire [3:0] cr;
    ot_svs_grp #(.K(g), .DMA(1)) u_g (.ck(ck), .rst(rn), .rn(rn), .sv_i(sv[4*g +: 4]),
      .sq_i({sq[4*g+3], sq[4*g+2], sq[4*g+1], sq[4*g]}), .kq(2'b00), .sg_v(1'b0), .sg_d(13'd0), .cr(cr), .ks(ks),
      .ovf(ovf[g]), .dd(dd[g*1080 +: 1080]), .dc(dd_cr[4*g +: 4]), .dcr(lc_g[4*g +: 4]));
  end endgenerate
endmodule
`default_nettype wire
