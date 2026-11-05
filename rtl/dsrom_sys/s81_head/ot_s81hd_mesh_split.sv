`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// DH58-RFRTL 2026-11-03 (HEAD RE-FORM batch l48rf, OWNER TWO-STRIKES; CLOSURE-LIST HEAD-027): hd_mesh measured 191,052
// std cells (ORFS synth of the l48x kit) > the 150k RE-FORM aim, so ot_s81hd_mesh_ep_core is split on its natural lane
// boundary into two abutted plan types (same form as the DH56-HSPLIT hd_host split):
//   hd_mesh_a = ot_s81hd_mesh_a_core: lane a (u_la) + own BEST decode (u_own) + RX copy FIFOs + word port (m_tx_i /
//               m_rx_o to hd_ctl, coll_ia / coll_oa SerDes pair a)
//   hd_mesh_b = ot_s81hd_mesh_b_core: lane b (u_lb) + its own copy of the BEST decode (u_own, same m_tx_i beats)
//               (coll_ib / coll_ob SerDes pair b)
// Seam (two plan buses; every partition output registered at its face, every input landed on a register):
//   b_tx  a->b  64 b  m_tx_i beats (the 64-wire BEST lane, not the 553-b frame: b decodes its own copy)
//   b_rx  b->a  103 b {fl_b[3:0], rv_b, can_b, rd_b[96:0]} (can_b = the canonical-BEST test, computed in b on the same
//               edge; the copy logic reads nothing else of rd_b)
// BALANCED latency (exact by construction): lane a's TX and RX paths get the same 2 edges as lane b's seam paths, and
// own_f / the copy-logic reset release are delayed by 2 too, so for every input sequence
//   coll_oa / coll_ob (t) = ot_s81hd_mesh_ep_core with m_tx_i delayed 2 edges (t),  m_rx_o (t) = that core's m_rx_o (t-2)
// i.e. +2 cycles on m_tx_i -> lanes and +2 on lanes -> m_rx_o (HEAD crossing latency table, hd_mesh rows).  Lane
// protocols, coll pins, credits and replay are untouched (the lanes are the unchanged ot_s81hd_mesh_lane).  Only
// valid / fault / beat bits are reset; record data holds are unreset.
// SPLIT_MUT (bench negative controls; 0 = production): 1 lane a TX balance stage dropped, 2 a-side landing register of
// b_rx dropped, 3 own_f (m_tx decode fault) not delayed, 4 lane b fault not carried, 5 (b core) can_b ignores rd_b[552].
// The copy-logic reset delay (rx_dl) has no mutant: its inputs (pa / pb pipes, reset by rst_n; lanes not yet trained)
// are held at 0 for many more than 2 edges after the release, so a 2-edge earlier release is not observable; it is kept
// so that the copy logic is the unsplit one shifted by exactly 2 edges in every input including reset.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_mesh_a_core #(
    parameter [1:0]   CH_B = 2'b11,          // board-lane straps of lanes a / b (as ot_s81hd_lep0N_core CH_B)
    parameter integer BQ   = 7,              // per-copy burst FIFO depth (HEAD-RTL-4 bound, see the RX section)
    parameter integer MUT  = 0,
    parameter integer SPLIT_MUT = 0          // bench negative controls only (0 = production), see the file header
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [513:0]  coll_ia,
    output wire [511:0]  coll_oa,
    output wire [63:0]   b_tx_o,             // seam W->E: m_tx_i registered at the E face (+1; +1 landing in b)
    input  wire [102:0]  b_rx_i,             // seam E->W: {fl_b 4, rv_b, can_b, rd_b[96:0]}, registered in b (+1)
    input  wire [63:0]   m_tx_i,
    output wire [63:0]   m_rx_o
);
    localparam integer WW = 110;
    wire [1:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(2)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    wire r_tx = rr[0], r_rx0 = rr[1];
    // copy-logic / word-port reset released 2 edges after the unsplit core's (its inputs are 2 edges later)
    reg [1:0] rx_dl;
    always @(posedge ck or negedge r_rx0) if (!r_rx0) rx_dl <= 2'b00; else rx_dl <= {rx_dl[0], 1'b1};
    wire r_rx = rx_dl[1];
    // ------------------------------------------------------------------ TX: own BEST -> both lanes
    // SPLIT seam (balanced, exact by construction): every lane-facing path of this endpoint is 2 edges later than in
    // the unsplit core -- m_tx_i -> lane a through 2 registers here, -> lane b through the W face register (b_tx_o) and
    // the E landing register in ot_s81hd_mesh_b_core; lane a / lane b RX -> copy logic through 2 registers (a: both
    // here; b: E face register + the landing register here); own_f and the copy-logic reset release are delayed by the
    // same 2 edges.  => coll_oa/coll_ob(t) == unsplit(m_tx_i delayed 2)(t), m_rx_o(t) == that unsplit m_rx_o(t - 2).
    reg [63:0] mt1, mt2, mtb;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin mt1 <= 64'd0; mt2 <= 64'd0; mtb <= 64'd0; end
        else begin mt1 <= m_tx_i; mt2 <= (SPLIT_MUT == 1) ? m_tx_i : mt1; mtb <= m_tx_i; end
    assign b_tx_o = mtb;
    wire        own_v, own_f0, own_f;
    wire [552:0] own_frame;
    ot_s81hd_best64_rx u_own (.ck(ck), .rn(r_tx), .lane(mt2), .v(own_v), .frame(own_frame), .fault(own_f0));
    // ------------------------------------------------------------------ lane a (lane b is in ot_s81hd_mesh_b_core)
    wire        rv_a0;
    wire [552:0] rd_a0;
    wire [3:0]  fl_a0;
    ot_s81hd_mesh_lane u_la (.ck(ck), .rst_n(rst_n), .chb(CH_B[0]), .rx(coll_ia), .tx(coll_oa),
        .tx_v(own_v), .tx_d(own_frame), .rx_v(rv_a0), .rx_d(rd_a0), .flt(fl_a0));
    wire can_a0 = rd_a0[552] && rd_a0[3:0] == 4'd1 && !(|rd_a0[551:97]);
    // 2-edge RX pipes: lane a (both stages here), lane b (landing stage here; its first stage is the E face register)
    (* keep = "true" *) reg [6:0] pa1, pa2, pb1;           // {fl 4, rv, can, own_f} -- reset
    (* keep = "true" *) reg [96:0] da1, da2, db1;          // record bodies -- unreset
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin pa1 <= 7'd0; pa2 <= 7'd0; pb1 <= 7'd0; end
        else begin
            pa1 <= {fl_a0, rv_a0, can_a0, own_f0}; pa2 <= pa1;
            pb1 <= (SPLIT_MUT == 2) ? 7'd0 : {(SPLIT_MUT == 4) ? 4'd0 : b_rx_i[102:99], b_rx_i[98:97], 1'b0};
        end
    always @(posedge ck) begin da1 <= rd_a0[96:0]; da2 <= da1; db1 <= b_rx_i[96:0]; end
    wire        rv_a = pa2[2], can_a = pa2[1];
    wire [3:0]  fl_a = pa2[6:3];
    wire        rv_b = (SPLIT_MUT == 2) ? b_rx_i[98] : pb1[2], can_b = (SPLIT_MUT == 2) ? b_rx_i[97] : pb1[1];
    wire [3:0]  fl_b = (SPLIT_MUT == 2) ? b_rx_i[102:99] : pb1[6:3];
    assign own_f = (SPLIT_MUT == 3) ? own_f0 : pa2[0];
    wire [96:0] rd_a = da2, rd_b = (SPLIT_MUT == 2) ? b_rx_i[96:0] : db1;
    // ------------------------------------------------------------------ RX: canonical BEST -> copy slots
    wire en_a = rv_a && can_a, en_b = rv_b && can_b;
    // HEAD-RTL-4 (RULING HEAD-RTL-3 ASK2): per-copy BURST FIFO of BQ records (was a 1-entry hold slot).  After a lane
    // replay the link delivers the replayed backlog back to back (lsc_r0m li_r = li_v registered, gearbox 3 flits / 4
    // edges) while the shared word port drains one word per 2 edges, A first; BQ = the worst replay backlog of
    // results/arch/head_rtl4_1026/README.md (tools/s81_head/mesh_bq_bound.py: replay window N = floor(S / T) + 1 records
    // at stall S and record spacing T, delivered 3 per 4 edges against the copy-B drain gap; S 79 / T 7 -> 7; the
    // production position period T >= 8,357 > any NAK or ACK-timeout stall gives N = 1).  Static storage: flops, one-hot write / read
    // pointers, no flow control towards the lane (the closed lsc_r0m child is unchanged).  A landing into a full FIFO
    // is DROPPED (order kept) and sets the sticky ep_fault[10].  Same edges as the slot: landing register (edge 1),
    // FIFO write + count (edge 2), decision -> word register (edge 3).  MUT 7 = BQ - 1 (bench negative control).
    localparam integer BQE = (MUT == 7) ? BQ - 1 : BQ;
    localparam integer BCW = $clog2(BQE + 1);
    reg  la, lb;                              // landed enables (aligned with the landing registers)
    reg  [96:0] ld_a, ld_b;                   // landing registers (data, unreset)
    always @(posedge ck) begin ld_a <= rd_a[96:0]; ld_b <= rd_b[96:0]; end
    reg  [96:0] fq_a [0:BQE-1];
    reg  [96:0] fq_b [0:BQE-1];
    reg  [BQE-1:0] wp_a, wp_b, rp_a, rp_b;    // one-hot pointers
    reg  [BCW-1:0] na, nb;                    // records held
    reg  iss_q;                               // a word was issued on the previous decision edge
    (* keep = "true" *) reg [3:0] selb;       // kept copies of "this word is copy B"
    wire pa = (na != 0), pb = (nb != 0);
    wire dec  = !iss_q && (pa || pb);
    wire tk_a = dec && pa;
    wire tk_b = dec && !pa;
    wire wa = la && ((na - (tk_a ? 1'b1 : 1'b0)) < BQE);   // room after this edge's read
    wire wb = lb && ((nb - (tk_b ? 1'b1 : 1'b0)) < BQE);
    reg  [11:0] fv;
    reg  ovw_q, ncan_q;
    function automatic [BQE-1:0] rot(input [BQE-1:0] p);
        rot = (BQE == 1) ? p : {p[BQE-2:0], p[BQE-1]};
    endfunction
    function automatic [96:0] pick(input [97*BQE-1:0] m, input [BQE-1:0] p);
        integer j; begin pick = 97'd0; for (j = 0; j < BQE; j = j + 1) pick = pick | (m[97*j +: 97] & {97{p[j]}}); end
    endfunction
    wire [97*BQE-1:0] fa_flat, fb_flat;
    genvar g;
    generate for (g = 0; g < BQE; g = g + 1) begin : g_fq
        assign fa_flat[97*g +: 97] = fq_a[g];
        assign fb_flat[97*g +: 97] = fq_b[g];
        always @(posedge ck) begin
            if (wa && wp_a[g]) fq_a[g] <= ld_a;
            if (wb && wp_b[g]) fq_b[g] <= ld_b;
        end
    end endgenerate
    reg  [96:0] ow;                           // the word being sent (copy A or B head)
    always @(posedge ck) if (dec) ow <= tk_a ? pick(fa_flat, rp_a) : pick(fb_flat, rp_b);
    always @(posedge ck or negedge r_rx)
        if (!r_rx) begin
            la <= 1'b0; lb <= 1'b0; na <= 0; nb <= 0; iss_q <= 1'b0; selb <= 4'd0; ovw_q <= 1'b0; ncan_q <= 1'b0;
            wp_a <= 1; wp_b <= 1; rp_a <= 1; rp_b <= 1;
        end else begin
            la <= en_a; lb <= en_b;
            na <= na + (wa ? 1'b1 : 1'b0) - (tk_a ? 1'b1 : 1'b0);
            nb <= nb + (wb ? 1'b1 : 1'b0) - (tk_b ? 1'b1 : 1'b0);
            if (wa) wp_a <= rot(wp_a);
            if (wb) wp_b <= rot(wp_b);
            if (tk_a) rp_a <= rot(rp_a);
            if (tk_b) rp_b <= rot(rp_b);
            iss_q <= dec;
            if (dec) selb <= {4{tk_b}};
            ovw_q  <= (la && !wa) || (lb && !wb);
            ncan_q <= (rv_a && !can_a) || (rv_b && !can_b);
        end
    // ------------------------------------------------------------------ word to hd_ctl
    wire [96:0] body = {ow[96:84] ^ ((MUT == 2 && selb[3]) ? 13'h1000 : 13'h0), ow[83:0]};
    wire copy = (MUT == 1) ? 1'b0 : selb[0];
    wire wf;
    wire [11:0] fv_word = (MUT == 4) ? 12'd0 : fv;
    ot_s81hd_beat_tx #(.W(WW), .N(2), .P(62), .IDLE_ZERO(1)) u_wtx (.ck(ck), .rn(r_rx), .v(iss_q), .d({fv_word, copy, body}),
        .o(m_rx_o), .fault(wf));
    always @(posedge ck or negedge r_rx)
        if (!r_rx) fv <= 12'd0;
        else fv <= fv | {wf, ovw_q, ncan_q, own_f, fl_b, fl_a};
endmodule
module ot_s81hd_mesh_b_core #(
    parameter [1:0]   CH_B = 2'b11,
    parameter integer MUT  = 0,
    parameter integer SPLIT_MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [513:0]  coll_ib,
    output wire [511:0]  coll_ob,
    input  wire [63:0]   b_tx_i,             // seam a->b, landed here (+1, the 2nd of the 2 TX edges)
    output wire [102:0]  b_rx_o              // seam b->a, registered here (+1, the 1st of the 2 RX edges)
);
    wire [1:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(2)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    wire r_tx = rr[0];
    reg [63:0] mtl;
    always @(posedge ck or negedge rst_n) if (!rst_n) mtl <= 64'd0; else mtl <= b_tx_i;
    wire        own_v, own_f_unused;
    wire [552:0] own_frame;
    ot_s81hd_best64_rx u_own (.ck(ck), .rn(r_tx), .lane(mtl), .v(own_v), .frame(own_frame), .fault(own_f_unused));
    wire        tv_b = (MUT == 3) ? 1'b0 : own_v;
    wire        rv_b;
    wire [552:0] rd_b;
    wire [3:0]  fl_b;
    ot_s81hd_mesh_lane u_lb (.ck(ck), .rst_n(rst_n), .chb(CH_B[1]), .rx(coll_ib), .tx(coll_ob),
        .tx_v(tv_b), .tx_d(own_frame), .rx_v(rv_b), .rx_d(rd_b), .flt(fl_b));
    wire can_b = ((SPLIT_MUT == 5) ? 1'b1 : rd_b[552]) && rd_b[3:0] == 4'd1 && !(|rd_b[551:97]);
    (* keep = "true" *) reg [5:0] pq;                       // {fl_b, rv_b, can_b} -- reset
    (* keep = "true" *) reg [96:0] dq;                      // record body -- unreset
    always @(posedge ck or negedge rst_n) if (!rst_n) pq <= 6'd0; else pq <= {fl_b, rv_b, can_b};
    always @(posedge ck) dq <= rd_b[96:0];
    assign b_rx_o = {pq, dq};
endmodule

// Bench / LEC reference composition of the two halves (the die abuts them; this is NOT a plan type).
module ot_s81hd_mesh_split_ref #(
    parameter [1:0]   CH_B = 2'b11,
    parameter integer BQ   = 7,
    parameter integer MUT  = 0,
    parameter integer SPLIT_MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [513:0]  coll_ia,
    output wire [511:0]  coll_oa,
    input  wire [513:0]  coll_ib,
    output wire [511:0]  coll_ob,
    input  wire [63:0]   m_tx_i,
    output wire [63:0]   m_rx_o
);
    wire [63:0] b_tx; wire [102:0] b_rx;
    ot_s81hd_mesh_a_core #(.CH_B(CH_B), .BQ(BQ), .MUT(MUT), .SPLIT_MUT(SPLIT_MUT)) u_a (.ck(ck), .rst_n(rst_n),
        .coll_ia(coll_ia), .coll_oa(coll_oa), .b_tx_o(b_tx), .b_rx_i(b_rx), .m_tx_i(m_tx_i), .m_rx_o(m_rx_o));
    ot_s81hd_mesh_b_core #(.CH_B(CH_B), .MUT(MUT), .SPLIT_MUT(SPLIT_MUT)) u_b (.ck(ck), .rst_n(rst_n),
        .coll_ib(coll_ib), .coll_ob(coll_ob), .b_tx_i(b_tx), .b_rx_o(b_rx));
endmodule
`default_nettype wire
