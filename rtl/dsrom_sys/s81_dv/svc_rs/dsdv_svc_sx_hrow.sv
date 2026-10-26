`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SVCX4 (2026-10-17): dsdv_svc_sx_hrow, the CENTRE LEAF of the split score exchange = HALF a score row.  The slice
// (dsdv_svc_sx) instantiates it 8x (4 rows x 2 halves), hardened once; the strap hb picks the half.
//
// Why: the full-row leaf (S81U-SVCX, 14.4k sinks on a 389 um pin ring) measured TT 326..415 ps insertion / 89 ps spread
// at its best CTS setting (gate 3), over the 300 / 80 clock rule.  Halving it gives ~7.3k sinks on a ~238 um ring.
//
// The halves are HEAD PARITY classes: half hb owns heads h = 2 i + hb (i = 0..7) of its row.  A score beat never mixes
// heads in the gather (the node adds lane (r, h) of a to lane (r, h) of b), so the gather splits with no crossing.  The
// scatter moves head SLOTS: a node over heads lo..hi sends lo..mid to the left child and mid + 1..hi to the right child
// shifted down by the left half's size (8, 4, 2, 1).  Shifts by 8, 4 and 2 keep slot parity (local shift 4, 2, 1 inside
// a half); only the pair nodes' shift by 1 would cross halves.  So the pair node does NOT shift: its right child gets
// the lane as is, head 2k + 1 at slot 1 = local slot 0 of half 1, and the leaf of head t taps local slot 0 of half t[0]
// (role head bit 0).  The other half's tap register holds 0 (valid low), so the slice ORs the two halves' 39-b tap
// (the same kind of output glue as its row valid AND / fault OR).  Nothing crosses halves; zero added cycles; the 5-cycle
// hop and the role ROM offsets are unchanged (the scatter lane's slot encoding below a pair node is internal to the
// exchange: only the gather beat at the root and the taps leave it).
// Lanes (per half): gather {v, tag part 5, y 8 x FP32, flags 8} = 270 b = ONE dsfd_dvrly_276 station; scatter
// {v, tag part 5, 4 slots x {flag, y}} = 138 b, the two halves of a row share one 276-b station.  Every pin registered.
// Static schedule (no ready / credit); sticky fault on operand misalignment, tag-part mismatch or a stray valid.
// MUT: bit 0 = right operand's flags not ORed; bit 1 = right scatter split off by one (local) head slot.
// S81-KITS-HROW (2026-10-24): every role-driven mux select is a registered, replicated one-hot (see below); 0 cycles.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_sx_hrow #(
    parameter integer MUT = 0,
    parameter integer FX = 5,
    parameter integer F12 = 1
) (
    input  wire              ck,
    input  wire              rst,          // async die reset, active low (synchronised here)
    input  wire [3:0]        sid,          // slice-id strap
    input  wire              hb,           // half strap: 0 = even heads, 1 = odd heads of the row
    // this half row of the tile partial: {v, tag part 5, y 8 x FP32, flags 8}
    input  wire [269:0]      l_i,
    // gather lanes {v, tag part 5, y 8 x FP32, flags 8}, one port per face (each = 1 dsfd_dvrly_276 station)
    input  wire [269:0]      gi_n, gi_e, gi_s, gi_w,
    output wire [269:0]      go_n, go_e, go_s, go_w,
    // scatter lanes {v, tag part 5, 4 head slots x {flag 1, y FP32}} (2 halves = 1 dsfd_dvrly_276 station)
    input  wire [137:0]      si_n, si_e, si_s, si_w,
    output wire [137:0]      so_n, so_e, so_s, so_w,
    // this half row of the complete score beat (root slice only) {v, 269 b}
    output wire [269:0]      rt_o,
    // this row of this slice's SM head {v, tag part 5, flag, y FP32}; 0 unless this half owns the head
    output wire [38:0]       t_o,
    output reg               fault
);
`ifdef DSDV_SX_MUT_ORDER
`ifdef OT_SVC_GROUP72
`include "dsdv_svc_sx_roles_mut_order_group72.svh"
`else
`include "dsdv_svc_sx_roles_mut_order.svh"
`endif
`else
`ifdef OT_SVC_GROUP72
`include "dsdv_svc_sx_roles_group72.svh"
`else
`include "dsdv_svc_sx_roles.svh"
`endif
`endif
    localparam integer W = 269, N = 8, TW = 5, SW = 137, SL = 33, NS = 4;
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    // S81U-SVCX3: the sid strap lands in a pin flop first (gate 2: sid -> role ROM was 4 levels from the port); the
    // strap is static and sid_q settles during the 2-cycle reset synchroniser, so role is unchanged from rn release.
    // S81-KITS-HROW: keep -- with the decode in front of the select registers, yosys memory_dff otherwise folds sid_q into
    // the sx_role ROM as its registered address (sid port -> ROM logic -> 650 select flops; face_guard 'shared' sid[*]).
    (* keep *) reg [3:0] sid_q; (* keep *) reg hb_q;
    always @(posedge ck) begin sid_q <= sid; hb_q <= hb; end
    // S81-KITS-HROW (2026-10-24): REGISTERED DECODED SELECTS.  r13 / r14 kit routes failed TT setup (-50.1 / -47.9 ps)
    // on role[8] -> 3-bit select decode (OR3) -> two 21..24-load fanout trees (120..180 ps slew) -> the 6:1 go_n mux:
    // the role field was decoded combinationally in front of every one of ~1,900 mux bits.  role is a STATIC strap
    // decode, so the decode moves in front of the register: every mux select is a one-hot register loaded from
    // sx_role(sid_q) (and hb_q for the tap), replicated per group of <= GG / GS mux bits (each copy drives one bounded
    // local fanout; (* keep *) + the kit's ot_keep_regs hook keep the copies from being merged).  Each select register
    // has the old role register's exact form (async reset on rn to the decode of role = 0, load sx_role(sid_q) on every
    // edge), so it equals decode(role) on every cycle: from reset, through the first edge after rn release, onwards.
    // The tap's own = (role head bit 0 == hb_q) folds into the tap selects (own & (r_ts == k)); old own used hb_q of the
    // current cycle, the fold uses hb_q one edge earlier: identical because hb (like sid) is a static strap that hb_q
    // captures on every edge, also during reset, >= 2 edges before rn releases.  0 added cycles, 0 boot cycles.
    localparam integer GG = 24, NGG = (W + 1 + GG - 1) / GG;   // gather-width muxes ({v, 269 b}): 12 groups of <= 24
    localparam integer GS = 23, NGS = (SW + 1 + GS - 1) / GS;  // scatter-width muxes ({v, 137 b}): 6 groups of <= 23
    localparam integer GN = 24, NGN = (W + GN - 1) / GN;       // scatter node lane sn {tag, 264 b}: 12 groups
    localparam integer GP = 22, NGP = (NS*SL + GP - 1) / GP;    // right-split shift (132 b): 6 groups of 22
    localparam integer GT = 20, NGT = 2;                        // tap {v, tag, f, y} = 39 b: 2 groups
    // rw = sx_role(sid_q), what the old role register loaded every edge, written as a sid one-hot AND-OR over the 16
    // constant role words: a case / indexed lookup becomes a yosys ROM whose memory_dff absorbs the sid_q pin flops as
    // its registered address (r15 synth: sid ports fanned straight into the decode, face_guard 'shared' sid[*]).
    wire [15:0] sid_oh = 16'(16'd1 << sid_q);
    wire [43:0] rw_t [0:15];
    genvar rr;
    generate for (rr = 0; rr < 16; rr = rr + 1) begin : g_rw
        localparam [43:0] RW = sx_role(4'(rr));
        assign rw_t[rr] = {44{sid_oh[rr]}} & RW;
    end endgenerate
    reg [43:0] rw;
    always @(*) begin rw = '0; for (int i = 0; i < 16; i++) rw = rw | rw_t[i]; end
    wire [2:0] w_ga = rw[2:0], w_gb = rw[5:3], w_ss = rw[21:19], w_ts = rw[38:36];
    wire [1:0] w_sh = rw[23:22]; wire w_rt = rw[18];
    wire [2:0] w_go [0:3]; wire [2:0] w_so [0:3];
    assign w_go[0] = rw[8:6]; assign w_go[1] = rw[11:9]; assign w_go[2] = rw[14:12]; assign w_go[3] = rw[17:15];
    assign w_so[0] = rw[26:24]; assign w_so[1] = rw[29:27]; assign w_so[2] = rw[32:30]; assign w_so[3] = rw[35:33];
    wire w_own = rw[39] == hb_q;
    // one-hot decodes: bit (code - 1) of a code 1..n (code 0 and unused codes = no source = 0, as the case defaults)
    function automatic [5:0] oh6(input [2:0] c);
        oh6 = (c >= 3'd1 && c <= 3'd6) ? 6'(6'd1 << (c - 3'd1)) : 6'd0;
    endfunction
    // decode of role = 0 (the old role register's reset value): no source anywhere, the shift select at r_sh = 0
    localparam [3:0] SH0 = 4'b0001;
`ifdef OT_HROW_SEL_MUT
    // negative control (bench only): one replicated copy (go face 0, group 2) decodes source code 3 as code 2
    function automatic [5:0] oh6m(input [2:0] c); oh6m = oh6((c == 3'd3) ? 3'd2 : c); endfunction
`endif
    genvar f, k;
    // per-face ports <-> face-indexed buses, faces {W, S, E, N} = [3:0] (the role ROM's face order)
    wire [3:0] gi_v = {gi_w[W], gi_s[W], gi_e[W], gi_n[W]}, si_v = {si_w[SW], si_s[SW], si_e[SW], si_n[SW]};
    wire [4*W-1:0] gi_d = {gi_w[W-1:0], gi_s[W-1:0], gi_e[W-1:0], gi_n[W-1:0]};
    wire [4*SW-1:0] si_d = {si_w[SW-1:0], si_s[SW-1:0], si_e[SW-1:0], si_n[SW-1:0]};
    wire [3:0] go_v, so_v; wire [4*W-1:0] go_d; wire [4*SW-1:0] so_d;
    assign go_n = {go_v[0], go_d[0 +: W]}; assign go_e = {go_v[1], go_d[W +: W]};
    assign go_s = {go_v[2], go_d[2*W +: W]}; assign go_w = {go_v[3], go_d[3*W +: W]};
    assign so_n = {so_v[0], so_d[0 +: SW]}; assign so_e = {so_v[1], so_d[SW +: SW]};
    assign so_s = {so_v[2], so_d[2*SW +: SW]}; assign so_w = {so_v[3], so_d[3*SW +: SW]};
    wire l_v = l_i[W]; wire [W-1:0] l_d = l_i[W-1:0];
    reg rt_v; reg [W-1:0] rt_d; reg t_v; reg [TW-1:0] t_tag; reg [31:0] t_y; reg t_f;
    assign rt_o = {rt_v, rt_d}; assign t_o = {t_v, t_tag, t_f, t_y};

    // ---------------- faces in: the last input register (pin flop) ----------------
    reg [3:0] gc_v, sc_v; reg [W-1:0] gc_d [0:3]; reg [SW-1:0] sc_d [0:3];
    always @(posedge ck or negedge rn) if (!rn) begin gc_v <= '0; sc_v <= '0; end else begin gc_v <= gi_v; sc_v <= si_v; end
    generate for (f = 0; f < 4; f = f + 1) begin : g_in
        always @(posedge ck) begin gc_d[f] <= gi_d[W*f +: W]; sc_d[f] <= si_d[SW*f +: SW]; end
    end endgenerate
    reg lc_v; reg [W-1:0] lc_d;
    always @(posedge ck or negedge rn) if (!rn) lc_v <= 1'b0; else lc_v <= l_v;
    always @(posedge ck) lc_d <= l_d;

    // ---------------- gather sources: 1 leaf, 2..5 face N/E/S/W, 6 adder (one-hot AND-OR on registered selects) ----------
    wire [W:0] src_l = {lc_v, lc_d};
    wire [W:0] src_c [0:3];
    assign src_c[0] = {gc_v[0], gc_d[0]}; assign src_c[1] = {gc_v[1], gc_d[1]};
    assign src_c[2] = {gc_v[2], gc_d[2]}; assign src_c[3] = {gc_v[3], gc_d[3]};
    wire ad_v; wire [W-1:0] ad_d; wire [W:0] src_a = {ad_v, ad_d};
    wire [W:0] opa, opb;
    wire [5:0] oh_ga = oh6(w_ga), oh_gb = oh6(w_gb);
    genvar j;
    generate for (j = 0; j < NGG; j = j + 1) begin : g_op
        localparam integer LO = j * GG, NB = (LO + GG > W + 1) ? W + 1 - LO : GG;
        (* keep *) reg [4:0] sa;   // operand a: leaf, faces 0..3 (code 6 = the adder never feeds an operand)
        (* keep *) reg [4:0] sb;
        always @(posedge ck or negedge rn)
            if (!rn) begin sa <= '0; sb <= '0; end else begin sa <= oh_ga[4:0]; sb <= oh_gb[4:0]; end
        assign opa[LO +: NB] = ({NB{sa[0]}} & src_l[LO +: NB]) | ({NB{sa[1]}} & src_c[0][LO +: NB]) |
                               ({NB{sa[2]}} & src_c[1][LO +: NB]) | ({NB{sa[3]}} & src_c[2][LO +: NB]) |
                               ({NB{sa[4]}} & src_c[3][LO +: NB]);
        assign opb[LO +: NB] = ({NB{sb[0]}} & src_l[LO +: NB]) | ({NB{sb[1]}} & src_c[0][LO +: NB]) |
                               ({NB{sb[2]}} & src_c[1][LO +: NB]) | ({NB{sb[3]}} & src_c[2][LO +: NB]) |
                               ({NB{sb[4]}} & src_c[3][LO +: NB]);
    end endgenerate
    wire a_v = opa[W], b_v = opb[W]; wire [W-1:0] a_d = opa[W-1:0], b_d = opb[W-1:0];

    // ---------------- static decodes used once (registered, same form) ----------------
    reg node, r_rt;                 // node: r_ga != 0; r_rt: this slice is the gather root
    reg [3:0] g_used, s_used;       // faces whose gather / scatter input the role reads (stray-valid check)
    always @(posedge ck or negedge rn)
        if (!rn) begin node <= 1'b0; r_rt <= 1'b0; g_used <= '0; s_used <= '0; end
        else begin
            node <= w_ga != 3'd0; r_rt <= w_rt;
            for (int i = 0; i < 4; i++) begin
                g_used[i] <= w_ga == 3'(2 + i) || w_gb == 3'(2 + i) || w_go[0] == 3'(2 + i) || w_go[1] == 3'(2 + i) ||
                             w_go[2] == 3'(2 + i) || w_go[3] == 3'(2 + i);
                s_used[i] <= w_ss == 3'(1 + i) || w_ts == 3'(1 + i) || w_so[0] == 3'(1 + i) || w_so[1] == 3'(1 + i) ||
                             w_so[2] == 3'(1 + i) || w_so[3] == 3'(1 + i);
            end
        end

    // ---------------- the node row: 8 x qaddf (this half's heads) ----------------
    wire [N-1:0] fa = a_d[N-1:0], fb = (MUT[0]) ? '0 : b_d[N-1:0];
    wire [N*32-1:0] y; wire [N-1:0] af, fd; wire [TW-1:0] fd_tag; wire ov;
    generate for (k = 0; k < N; k = k + 1) begin : g_a
        ot_hdc_v41x_qaddf #(.LAT(FX), .F12(F12)) u_a (.clk(ck), .rst_n(rn), .v(1'b1), .a(a_d[N + 32*k +: 32]),
            .b(b_d[N + 32*k +: 32]), .y(y[32*k +: 32]), .fault(af[k]));
    end endgenerate
    ot_hdc_v41x_dly #(.W(N + TW), .D(FX)) u_fd (.clk(ck), .d({a_d[W-1 -: TW], fa | fb}), .q({fd_tag, fd}));
    ot_hdc_v41x_vdly #(.D(FX)) u_v (.clk(ck), .rst_n(rn), .d(a_v && node), .q(ov));
    assign ad_v = ov; assign ad_d = {fd_tag, y, fd | af};

    // ---------------- gather out: the centre register (the slice's stations follow) ----------------
    generate for (f = 0; f < 4; f = f + 1) begin : g_go
        wire [W:0] s;
        for (j = 0; j < NGG; j = j + 1) begin : g_g
            localparam integer LO = j * GG, NB = (LO + GG > W + 1) ? W + 1 - LO : GG;
            (* keep *) reg [5:0] q;
            always @(posedge ck or negedge rn)
                if (!rn) q <= '0;
`ifdef OT_HROW_SEL_MUT
                else q <= (f == 0 && j == 2) ? oh6m(w_go[f]) : oh6(w_go[f]);
`else
                else q <= oh6(w_go[f]);
`endif
            assign s[LO +: NB] = ({NB{q[0]}} & src_l[LO +: NB]) | ({NB{q[1]}} & src_c[0][LO +: NB]) |
                                 ({NB{q[2]}} & src_c[1][LO +: NB]) | ({NB{q[3]}} & src_c[2][LO +: NB]) |
                                 ({NB{q[4]}} & src_c[3][LO +: NB]) | ({NB{q[5]}} & src_a[LO +: NB]);
        end
        reg v; reg [W-1:0] d;
        always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= s[W];
        always @(posedge ck) d <= s[W-1:0];
        assign go_v[f] = v; assign go_d[W*f +: W] = d;
    end endgenerate
    always @(posedge ck or negedge rn) if (!rn) rt_v <= 1'b0; else rt_v <= r_rt && ad_v;
    always @(posedge ck) rt_d <= ad_d;

    // ---------------- scatter (head slots, this row) ----------------
    // node lane sn {tag 5, 2 x 4 slots x {flag, y}}: r_ss 1..4 = scatter face 0..3 (low 4 slots), 7 = the adder (8 slots,
    // valid only at the root); one-hot ss = {r_ss == 7, faces 3..0}
    wire [W-1:0] snf [0:3]; wire [W-1:0] sna;
    generate for (f = 0; f < 4; f = f + 1) begin : g_snf
        assign snf[f] = {sc_d[f][SW-1 -: TW], {(NS*SL){1'b0}}, sc_d[f][NS*SL-1:0]};
    end endgenerate
    generate for (k = 0; k < N; k = k + 1) begin : g_sna
        assign sna[SL*k +: SL] = {ad_d[k], ad_d[N + 32*k +: 32]};
    end endgenerate
    assign sna[W-1 -: TW] = ad_d[W-1 -: TW];
    function automatic [4:0] ohss(input [2:0] c);
        ohss = (c >= 3'd1 && c <= 3'd4) ? 5'(5'd1 << (c - 3'd1)) : (c == 3'd7) ? 5'b10000 : 5'd0;
    endfunction
    wire [4:0] oh_ss = ohss(w_ss);
    wire [W-1:0] snl;   // {sn_tag, sn}
    generate for (j = 0; j < NGN; j = j + 1) begin : g_sn
        localparam integer LO = j * GN, NB = (LO + GN > W) ? W - LO : GN;
        (* keep *) reg [4:0] q;
        always @(posedge ck or negedge rn) if (!rn) q <= '0; else q <= oh_ss;
        assign snl[LO +: NB] = ({NB{q[0]}} & snf[0][LO +: NB]) | ({NB{q[1]}} & snf[1][LO +: NB]) |
                               ({NB{q[2]}} & snf[2][LO +: NB]) | ({NB{q[3]}} & snf[3][LO +: NB]) |
                               ({NB{q[4]}} & sna[LO +: NB]);
    end endgenerate
    reg [4:0] ssv;      // the valid's selects: faces 3..0, and (r_ss == 7 && r_rt) for the adder
    always @(posedge ck or negedge rn)
        if (!rn) ssv <= '0; else ssv <= {oh_ss[4] & w_rt, oh_ss[3:0]};
    wire sn_v = |(ssv[3:0] & sc_v) | (ssv[4] & ad_v);
    wire [TW-1:0] sn_tag = snl[W-1 -: TW];
    wire [2*NS*SL-1:0] sn = snl[2*NS*SL-1:0];
    // absolute shift 1 << r_sh (8, 4, 2, 1 heads) = local shift 4, 2, 1 inside a parity half; the pair node (r_sh 0)
    // does not shift (see the header).  One-hot over r_sh; shift amount of code c = hs(c) (+1 slot under MUT[1]).
    function automatic integer hs(input integer c);
        hs = ((c == 0) ? 0 : (1 << (c - 1))) + ((MUT[1]) ? 1 : 0);
    endfunction
    wire [NS*SL-1:0] sp_l = sn[0 +: NS*SL];
    wire [2*NS*SL-1:0] sr0 = sn >> (SL * hs(0)), sr1 = sn >> (SL * hs(1)), sr2 = sn >> (SL * hs(2)),
                       sr3 = sn >> (SL * hs(3));
    wire [NS*SL-1:0] sp_r;
    generate for (j = 0; j < NGP; j = j + 1) begin : g_sp
        localparam integer LO = j * GP, NB = (LO + GP > NS*SL) ? NS*SL - LO : GP;
        (* keep *) reg [3:0] q;
        always @(posedge ck or negedge rn) if (!rn) q <= SH0; else q <= 4'(4'd1 << w_sh);
        assign sp_r[LO +: NB] = ({NB{q[0]}} & sr0[LO +: NB]) | ({NB{q[1]}} & sr1[LO +: NB]) |
                                ({NB{q[2]}} & sr2[LO +: NB]) | ({NB{q[3]}} & sr3[LO +: NB]);
    end endgenerate
    // scatter sources: 1..4 = scatter face 0..3, 5 = node lane left half, 6 = node lane right half
    wire [SW:0] ss_c [0:3];
    assign ss_c[0] = {sc_v[0], sc_d[0]}; assign ss_c[1] = {sc_v[1], sc_d[1]};
    assign ss_c[2] = {sc_v[2], sc_d[2]}; assign ss_c[3] = {sc_v[3], sc_d[3]};
    wire [SW:0] ss_l = {sn_v, sn_tag, sp_l}, ss_r = {sn_v, sn_tag, sp_r};
    generate for (f = 0; f < 4; f = f + 1) begin : g_so
        wire [SW:0] s;
        for (j = 0; j < NGS; j = j + 1) begin : g_g
            localparam integer LO = j * GS, NB = (LO + GS > SW + 1) ? SW + 1 - LO : GS;
            (* keep *) reg [5:0] q;
            always @(posedge ck or negedge rn) if (!rn) q <= '0; else q <= oh6(w_so[f]);
            assign s[LO +: NB] = ({NB{q[0]}} & ss_c[0][LO +: NB]) | ({NB{q[1]}} & ss_c[1][LO +: NB]) |
                                 ({NB{q[2]}} & ss_c[2][LO +: NB]) | ({NB{q[3]}} & ss_c[3][LO +: NB]) |
                                 ({NB{q[4]}} & ss_l[LO +: NB]) | ({NB{q[5]}} & ss_r[LO +: NB]);
        end
        reg v; reg [SW-1:0] d;
        always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= s[SW];
        always @(posedge ck) d <= s[SW-1:0];
        assign so_v[f] = v; assign so_d[SW*f +: SW] = d;
    end endgenerate
    // the SM tap: {v, tag, flag (slot 0), y (slot 0)} of source r_ts, only if this half owns the head (own folded in)
    function automatic [38:0] tsx(input [SW:0] x); tsx = {x[SW], x[SW-1 -: TW], x[32], x[31:0]}; endfunction
    wire [38:0] ts;
    wire [38:0] tx0 = tsx(ss_c[0]), tx1 = tsx(ss_c[1]), tx2 = tsx(ss_c[2]), tx3 = tsx(ss_c[3]), txl = tsx(ss_l),
                txr = tsx(ss_r);
    wire [5:0] oh_ts = oh6(w_ts) & {6{w_own}};
    generate for (j = 0; j < NGT; j = j + 1) begin : g_ts
        localparam integer LO = j * GT, NB = (LO + GT > 39) ? 39 - LO : GT;
        (* keep *) reg [5:0] q;
        always @(posedge ck or negedge rn) if (!rn) q <= '0; else q <= oh_ts;
        assign ts[LO +: NB] = ({NB{q[0]}} & tx0[LO +: NB]) | ({NB{q[1]}} & tx1[LO +: NB]) |
                              ({NB{q[2]}} & tx2[LO +: NB]) | ({NB{q[3]}} & tx3[LO +: NB]) |
                              ({NB{q[4]}} & txl[LO +: NB]) | ({NB{q[5]}} & txr[LO +: NB]);
    end endgenerate
    always @(posedge ck or negedge rn) if (!rn) t_v <= 1'b0; else t_v <= ts[38];
    always @(posedge ck) begin
        t_tag <= ts[37 -: TW]; t_f <= ts[32]; t_y <= ts[31:0];
    end

    // ---------------- static-schedule checks (sticky; never re-time anything) ----------------
    wire mis = node && (a_v != b_v || (a_v && a_d[W-1 -: TW] != b_d[W-1 -: TW]));
    wire stray = |(gc_v & ~g_used) || |(sc_v & ~s_used);
    // S81U-SVCX3: the check is registered once beside the node (gate 2: face pin flop -> 5:1 operand mux -> tag compare
    // -> the S-face fault pin flop was the worst reg->reg path, -64.7 ps); the sticky fault reports one cycle later.
    reg chk;
    always @(posedge ck or negedge rn) if (!rn) chk <= 1'b0; else chk <= mis || stray;
    always @(posedge ck or negedge rn) if (!rn) fault <= 1'b0; else if (chk) fault <= 1'b1;
endmodule
