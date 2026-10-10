`timescale 1ps/1fs
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hbm-forks 2026-10-10: svc-side DMA STREAM (hgi-takeover.log "SPEC for hbm-forks: svc-side DMA stream <-> hgi-takeover
// DMA front", agreed 03:15 PT) -- the hub unit at the family end that terminates the die nets.
//
//   request  dq  = {v, tag 4, nsec 9, addr 37}  (front -> svc; addr = die byte address of the first 32-B sector, stack
//                  bits [36:35]; the stack-local sector s = addr[34:5] lives in PC s[6:2] ^ s[11:7] ^ s[16:12]
//                  (ot_hbm_loader_kport_address), sector address s)
//   accept       the front holds dq until it sees dq_rdy; dq_rdy is this unit's register, so a request is taken when
//                the pin-flopped dq is valid and dq_rdy was high one cycle earlier (the cycle the front sampled it)
//   data     dd  = 8 lanes x {v, fault, tag 4, idx 8, data 256} (lane l = idx % 8, per lane in idx order, a request's
//                  sectors before the next request's on every lane), one beat a lane only with a credit (dd_cr pulses,
//                  CR0 initial)
//
// Structure (one stack):
//   R  request FIFO (pin-flopped dq, depth 8) -> request start: the request's sectors get a contiguous range of the
//      stack's sector SEQUENCE G (G0 = the next G with G0 % 4 = s % 4, so every HBM row of 4 sectors lands at a G
//      multiple of 4); the request queue RQ (NQ entries {tag, G0, nsec}) is the lanes' order.
//   I  issue: up to two rows a cycle in row order, each to its PC (command {gq = G / 4, row}) when the PC has a hub
//      credit (DH rows in flight a PC) and the row's G lies inside the reorder window (G < Gmin + 8 DP, Gmin = the
//      slowest lane's next G); commands leave on the command chain (two slots a cycle) to the group units.
//   A  arrivals: rows come back on two inward chains, A = even gq (banks 0-3), B = odd gq (banks 4-7): each row writes
//      its valid sectors (per-row sector mask, kept by gq) into the reorder buffer ROB = 8 banks x DP sectors (bank
//      = G % 8, address = (G / 8) % DP), one write a bank a cycle by construction; the PC's hub credit returns.
//   L  lanes: lane l walks its request's sectors idx = l, l + 8, ... (G = G0 + idx, bank = G % 8 = (G0 + l) % 8); a
//      sector leaves when it is valid, the lane holds a credit and the lane wins its bank's read port (lanes on the
//      same request use distinct banks; across requests the older request wins).  ROB read -> lane output register.
// No protection beyond the PS units' (REVIEW_20261009): fault is 0.
// ---------------------------------------------------------------------------------------------------------------------
module ot_svd_hub #(parameter integer DH = 8, parameter integer DP = 128, parameter integer NQ = 8,
                    parameter integer CR0 = 4) (
  input wire ck, input wire rn,
  input wire [50:0] dq, output wire dq_rdy,
  output wire [8*270-1:0] dd, input wire [7:0] dd_cr,
  output reg  [93:0] cmd,                              // {c1 47, c0 47}, c = {v, pc5, gq10, row28, 3'd0}
  input wire av, input wire [1038:0] ad,               // chain A arrival {gq10, pc5, data1024}
  input wire bv, input wire [1038:0] bd);              // chain B arrival
  localparam integer AW = $clog2(DP);
  localparam integer GW = 16;
  localparam integer QW = $clog2(NQ);
  localparam integer MW = AW + 1;                      // mask table index = gq % 2DP
  // ------------------------------------------------------------------ R: pin flops, request FIFO, dq_rdy
  reg [50:0] dq_q; reg [7:0] cr_q; reg rdy_q, rdy_d;
  reg [49:0] rf [0:7]; reg [2:0] rf_h, rf_t; reg [3:0] rf_n;
  wire take = dq_q[50] && rdy_d;
  wire pop;
  always @(posedge ck or negedge rn)
    if (!rn) begin dq_q <= 51'd0; cr_q <= 8'd0; rdy_q <= 1'b0; rdy_d <= 1'b0; rf_h <= 3'd0; rf_t <= 3'd0; rf_n <= 4'd0; end
    else begin
      dq_q <= dq; cr_q <= dd_cr; rdy_d <= rdy_q;
      if (take) rf_t <= rf_t + 3'd1;
      if (pop) rf_h <= rf_h + 3'd1;
      rf_n <= rf_n + (take ? 4'd1 : 4'd0) - (pop ? 4'd1 : 4'd0);
      // room for this cycle's take, the two requests the front may still send on rdy seen high, and one spare
      rdy_q <= (rf_n + (take ? 4'd1 : 4'd0) - (pop ? 4'd1 : 4'd0)) <= 4'd4;
    end
  always @(posedge ck) if (take) rf[rf_t] <= dq_q[49:0];
  assign dq_rdy = rdy_q;
  // ------------------------------------------------------------------ request queue (lanes' order)
  reg [3:0] rq_tag [0:NQ-1]; reg [GW-1:0] rq_g0 [0:NQ-1]; reg [8:0] rq_ns [0:NQ-1]; reg [NQ-1:0] rqv;
  reg [QW-1:0] rq_h, rq_t;
  // ------------------------------------------------------------------ issue engine
  reg act; reg [27:0] ir; reg [6:0] ik; reg [GW-3:0] igq; reg [1:0] ia, ilast; reg ifst;
  reg [GW-1:0] gn;                                     // next free G
  reg [GW-1:0] gmin;                                   // registered lower bound of every lane's next G
  wire [49:0] rh = rf[rf_h];
  wire [29:0] s0 = rh[34:5];
  wire [8:0] ns0 = rh[45:37];
  wire [1:0] a0 = s0[1:0];
  wire [GW-1:0] g0 = gn + GW'((a0 - gn[1:0]) & 2'd3);
  // at most NQ - 1 requests queued: a lane that finished every request waits at rq_t, which is then never valid
  wire [QW-1:0] rq_t1 = rq_t + 1'b1;
  wire rq_full = rqv[rq_t1];
  assign pop = (rf_n != 4'd0) && !act && !rq_full;
  // two candidate rows
  wire [27:0] ir1 = ir + 28'd1;
  wire [4:0] pc0 = ir[4:0] ^ ir[9:5] ^ ir[14:10];
  wire [4:0] pc1 = ir1[4:0] ^ ir1[9:5] ^ ir1[14:10];
  reg [3:0] hc [0:31];                                 // hub credits in use a PC
  wire [GW-1:0] ge0 = {igq, 2'b11};
  wire [GW-1:0] ge1 = ge0 + GW'(4);
  wire win0 = (GW'(ge0 - gmin)) < GW'(8 * DP);
  wire win1 = (GW'(ge1 - gmin)) < GW'(8 * DP);
  wire ok0 = act && win0 && (hc[pc0] != 4'(DH));
  wire ok1 = ok0 && (ik >= 7'd2) && win1 && (hc[pc1] != 4'(DH)) && (pc1 != pc0);
  function automatic [3:0] rmask(input fst, input lst, input [1:0] a, input [1:0] l);
    integer j;
    begin for (j = 0; j < 4; j = j + 1) rmask[j] = (!fst || j >= a) && (!lst || j <= l); end
  endfunction
  wire [3:0] m0 = rmask(ifst, ik == 7'd1, ia, ilast);
  wire [3:0] m1 = rmask(1'b0, ik == 7'd2, ia, ilast);
  reg [3:0] mt [0:2*DP-1];
  always @(posedge ck) begin
    if (ok0) mt[igq[MW-1:0]] <= m0;
    if (ok1) mt[MW'(igq + 1'b1)] <= m1;
  end
  // ------------------------------------------------------------------ arrivals (registered at the hub)
  reg a_v, b_v; reg [1038:0] a_d, b_d;
  always @(posedge ck or negedge rn) if (!rn) begin a_v <= 1'b0; b_v <= 1'b0; end else begin a_v <= av; b_v <= bv; end
  always @(posedge ck) begin a_d <= ad; b_d <= bd; end
  wire [9:0] a_gq = a_d[1038:1029], b_gq = b_d[1038:1029];
  wire [4:0] a_pc = a_d[1028:1024], b_pc = b_d[1028:1024];
  wire [3:0] a_m = mt[a_gq[MW-1:0]], b_m = mt[b_gq[MW-1:0]];
  wire [AW-1:0] a_ad = a_gq[AW:1], b_ad = b_gq[AW:1];
  // ------------------------------------------------------------------ ROB valid bits and banks
  reg [DP-1:0] vb [0:7];
  // ------------------------------------------------------------------ lanes
  reg [QW-1:0] lq [0:7]; reg [8:0] li [0:7]; reg [3:0] lcr [0:7];
  wire [7:0] lact, lreq; wire [2:0] lbank [0:7]; wire [AW-1:0] laddr [0:7]; wire [GW-1:0] lg [0:7];
  wire [7:0] ladv;
  genvar gl;
  generate for (gl = 0; gl < 8; gl = gl + 1) begin : lv
    wire [GW-1:0] g = rq_g0[lq[gl]] + GW'(li[gl]);
    assign lact[gl] = rqv[lq[gl]];
    assign ladv[gl] = lact[gl] && (li[gl] >= rq_ns[lq[gl]]);
    assign lbank[gl] = g[2:0];
    assign laddr[gl] = g[3 +: AW];
    assign lreq[gl] = lact[gl] && !ladv[gl] && vb[g[2:0]][g[3 +: AW]] && (lcr[gl] != 4'd0);
    // the lane's next G for the window: its position, clamped to its request's end
    assign lg[gl] = !lact[gl] ? gn : rq_g0[lq[gl]] + GW'((li[gl] < rq_ns[lq[gl]]) ? li[gl] : rq_ns[lq[gl]]);
  end endgenerate
  // bank arbitration: lanes on one request never share a bank; across requests the older request (nearer rq_h) wins
  wire [7:0] lgnt;
  generate for (gl = 0; gl < 8; gl = gl + 1) begin : la
    wire [QW-1:0] age = lq[gl] - rq_h;
    reg lose; integer o;
    always @* begin
      lose = 1'b0;
      for (o = 0; o < 8; o = o + 1)
        if (o != gl && lreq[o] && lbank[o] == lbank[gl] && QW'(lq[o] - rq_h) < age) lose = 1'b1;
    end
    assign lgnt[gl] = lreq[gl] && !lose;
  end endgenerate
  // ROB banks: one write (its chain) and one read (the granted lane) a bank a cycle
  wire [255:0] rdo [0:7];
  genvar gb;
  generate for (gb = 0; gb < 8; gb = gb + 1) begin : bk
    wire h = gb >= 4;
    wire wv = h ? b_v && b_m[gb - 4] : a_v && a_m[gb];
    wire [AW-1:0] wa = h ? b_ad : a_ad;
    wire [255:0] wd = h ? b_d[(gb - 4) * 256 +: 256] : a_d[gb * 256 +: 256];
    reg rv; reg [AW-1:0] ra; integer o;
    always @* begin
      rv = 1'b0; ra = {AW{1'b0}};
      for (o = 0; o < 8; o = o + 1) if (lgnt[o] && lbank[o] == gb[2:0]) begin rv = 1'b1; ra = laddr[o]; end
    end
    ot_svd_rob_bank #(.DP(DP)) u_b (.ck(ck), .re(rv), .ra(ra), .rd(rdo[gb]), .we(wv), .wa(wa), .wd(wd));
  end endgenerate
  // ------------------------------------------------------------------ lane output registers
  reg [7:0] p_v; reg [2:0] p_b [0:7]; reg [3:0] p_t [0:7]; reg [7:0] p_i [0:7];
  reg [7:0] o_v; reg [3:0] o_t [0:7]; reg [7:0] o_i [0:7]; reg [255:0] o_d [0:7];
  generate for (gl = 0; gl < 8; gl = gl + 1) begin : lo
    assign dd[gl*270 +: 270] = {o_v[gl], 1'b0, o_t[gl], o_i[gl], o_d[gl]};
  end endgenerate
  // ------------------------------------------------------------------ sequential
  integer l, b, p;
  always @(posedge ck or negedge rn)
    if (!rn) begin
      act <= 1'b0; gn <= {GW{1'b0}}; gmin <= {GW{1'b0}}; rqv <= {NQ{1'b0}}; rq_h <= {QW{1'b0}}; rq_t <= {QW{1'b0}};
      cmd <= 94'd0; p_v <= 8'd0; o_v <= 8'd0;
      for (p = 0; p < 32; p = p + 1) hc[p] <= 4'd0;
      for (b = 0; b < 8; b = b + 1) vb[b] <= {DP{1'b0}};
      for (l = 0; l < 8; l = l + 1) begin lq[l] <= {QW{1'b0}}; li[l] <= 9'(l); lcr[l] <= 4'(CR0); end
    end else begin : seq
      reg [GW-1:0] mn;
      // request start
      if (pop) begin
        act <= 1'b1; ir <= s0[29:2]; igq <= g0[GW-1:2]; ia <= a0; ifst <= 1'b1;
        ik <= 7'(({7'd0, a0} + {1'b0, ns0} + 9'd3) >> 2);
        ilast <= 2'(a0 + ns0[1:0] - 2'd1);
        gn <= g0 + GW'(ns0);
        rq_tag[rq_t] <= rh[49:46]; rq_g0[rq_t] <= g0; rq_ns[rq_t] <= ns0; rqv[rq_t] <= 1'b1; rq_t <= rq_t1;
      end else if (ok0) begin
        ifst <= 1'b0;
        ir <= ok1 ? ir + 28'd2 : ir1; igq <= igq + (ok1 ? 2'd2 : 2'd1);
        ik <= ik - (ok1 ? 7'd2 : 7'd1);
        if (ik == (ok1 ? 7'd2 : 7'd1)) act <= 1'b0;
      end
      cmd <= {ok1, pc1, 10'(igq + 1'b1), ir1, 3'd0, ok0, pc0, 10'(igq), ir, 3'd0};
      // hub credits: taken at issue, returned at arrival
      for (p = 0; p < 32; p = p + 1)
        hc[p] <= hc[p] + (((ok0 && pc0 == 5'(p)) || (ok1 && pc1 == 5'(p))) ? 4'd1 : 4'd0)
                       - (a_v && a_pc == 5'(p) ? 4'd1 : 4'd0) - (b_v && b_pc == 5'(p) ? 4'd1 : 4'd0);
      // ROB valid bits: set by arrivals, cleared by lane reads
      for (b = 0; b < 4; b = b + 1) if (a_v && a_m[b]) vb[b][a_ad] <= 1'b1;
      for (b = 0; b < 4; b = b + 1) if (b_v && b_m[b]) vb[b + 4][b_ad] <= 1'b1;
      for (l = 0; l < 8; l = l + 1) if (lgnt[l]) vb[lbank[l]][laddr[l]] <= 1'b0;
      // lanes
      for (l = 0; l < 8; l = l + 1) begin
        lcr[l] <= lcr[l] - (lgnt[l] ? 4'd1 : 4'd0) + (cr_q[l] ? 4'd1 : 4'd0);
        if (ladv[l]) begin lq[l] <= lq[l] + 1'b1; li[l] <= 9'(l); end
        else if (lgnt[l]) li[l] <= li[l] + 9'd8;
        p_v[l] <= lgnt[l]; p_b[l] <= lbank[l]; p_t[l] <= rq_tag[lq[l]]; p_i[l] <= li[l][7:0];
        o_v[l] <= p_v[l];
      end
      // request queue head: free once every lane has passed it
      if (rqv[rq_h] && lq[0] != rq_h && lq[1] != rq_h && lq[2] != rq_h && lq[3] != rq_h && lq[4] != rq_h &&
          lq[5] != rq_h && lq[6] != rq_h && lq[7] != rq_h) begin rqv[rq_h] <= 1'b0; rq_h <= rq_h + 1'b1; end
      // window bound: gn minus the largest lag of any lane (registered: a stale bound is a smaller, safe one)
      mn = gn;
      for (l = 0; l < 8; l = l + 1) if (GW'(gn - lg[l]) > GW'(gn - mn)) mn = lg[l];
      gmin <= mn;
    end
  // output payload reset: no X on the die net before the first beat
  always @(posedge ck or negedge rn)
    if (!rn) for (l = 0; l < 8; l = l + 1) begin o_t[l] <= 4'd0; o_i[l] <= 8'd0; o_d[l] <= 256'd0; end
    else for (l = 0; l < 8; l = l + 1) if (p_v[l]) begin o_t[l] <= p_t[l]; o_i[l] <= p_i[l]; o_d[l] <= rdo[p_b[l]]; end
endmodule

// one ROB bank: DP x 256 1R1W, read data the cycle after the read (the ASAP7 1R1W macro's registered output)
module ot_svd_rob_bank #(parameter integer DP = 128) (
  input wire ck, input wire re, input wire [$clog2(DP)-1:0] ra, output wire [255:0] rd,
  input wire we, input wire [$clog2(DP)-1:0] wa, input wire [255:0] wd);
`ifdef OT_SVD_MACRO
  generate if (DP == 128) begin : m
    ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(re), .r_addr_in(ra), .rd_out(rd), .w_ce_in(we), .w_addr_in(wa),
      .wd_in(wd), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
  end endgenerate
`else
  reg [255:0] m [0:DP-1]; reg [255:0] r;
  always @(posedge ck) begin
    if (re) r <= m[ra];
    if (we) m[wa] <= wd;
  end
  assign rd = r;
`endif
endmodule
`default_nettype wire
