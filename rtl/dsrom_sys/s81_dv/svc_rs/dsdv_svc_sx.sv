`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SVC (2026-10-17, S81-DV p4h regional service slice dsdv_svc_rs x16): dsdv_svc_sx, the SCORE EXCHANGE leaf of one
// slice.  One master for all 16 slices; the slice-id strap sid selects its row of the generated role ROM
// (dsdv_svc_sx_roles.svh, tools/s81_dv/svc_rs/svc_rs_embed.py).
//
// Golden (dsfd_svc_c): the q.k score of a row is the BALANCED tree over the 16 TD = 32 head-dim tiles, in dim order
// (D = 128 engine heap tree per quadrant, then ot_s81_svch_comb ((Q0 + Q1) + (Q2 + Q3))).  FP32 adds do not associate,
// so the slices carry that tree, not a running chain sum: every slice injects its tile partial (its engine share's score
// beat) and hosts at most ONE tree node (one bank of 64 ot_hdc_v41x_qaddf, the engine's lane-tree adder, flags =
// delay(fa | fb) | adder fault exactly as ot_s81_svch_comb / the engine g_node).  Operands travel neighbour-only over
// the N / E / S / W faces; each directed link carries at most one score lane (embedding: max load 1, 25 link hops).
// The complete score beat appears at the root slice (rt_*) and is SCATTERED back down the same tree: a node of n heads
// sends heads lo .. lo + n/2 - 1 to its left child and the rest to its right child; the leaf of tile t taps head t
// (t_*: 4 rows x FP32 + flags of the slice's SM head) -- no star, no central hub.
//
// Static schedule (owner rule, no credit / ready): every stage is a fixed-latency register.  The compiler starts each
// slice's engine share at its role offset (sx_role_off, chosen so both operands of every node meet in the same cycle);
// a node that sees one operand without the other, operands with different {row, mask} tags, or a valid on a face its
// role does not use, raises a sticky fault (checks only; they never re-time anything).
// Latency: face in pin flop + NR relays to the centre; centre crossbar register + NR relays + out pin flop; add FX.
// Every input lands in a flop and every output leaves a flop.
// MUT (bench negative controls): bit 0 = the right operand's flags are not ORed in; bit 1 = right scatter split off by
// one head slot.  DSDV_SX_MUT_ORDER (define) = role ROM of a tree whose tiles 0..3 sum as a chain (((t0+t1)+t2)+t3).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_sx #(
    parameter integer MUT = 0,
    parameter integer NR = 1,              // relay stages face <-> centre (each side)
    parameter integer FX = 5,              // qaddf latency (the D = 128 engine / svch_comb default build: F12 LAT 5)
    parameter integer F12 = 1
) (
    input  wire              ck,
    input  wire              rst,          // async die reset, active low (synchronised here)
    input  wire [3:0]        sid,          // slice-id strap (2 column + row)
    // the slice's tile partial score beat {row 16, mask 4, y 4 x 16 x FP32, flags 64} (engine share)
    input  wire              l_v,
    input  wire [2131:0]     l_d,
    // gather lanes, faces {W, S, E, N} = [3:0]
    input  wire [3:0]        gi_v,
    input  wire [4*2132-1:0] gi_d,
    output wire [3:0]        go_v,
    output wire [4*2132-1:0] go_d,
    // scatter lanes {tag 20, 8 head slots x {flags 4, y 4 x FP32}}
    input  wire [3:0]        si_v,
    input  wire [4*1076-1:0] si_d,
    output wire [3:0]        so_v,
    output wire [4*1076-1:0] so_d,
    // complete score beat (root slice only)
    output reg               rt_v,
    output reg  [2131:0]     rt_d,
    // this slice's SM head: 4 rows of scores
    output reg               t_v,
    output reg  [19:0]       t_tag,
    output reg  [127:0]      t_y,
    output reg  [3:0]        t_f,
    output reg               fault
);
`ifdef DSDV_SX_MUT_ORDER
`include "dsdv_svc_sx_roles_mut_order.svh"
`else
`include "dsdv_svc_sx_roles.svh"
`endif
    localparam integer W = 2132, N = 64, SW = 1076, SL = 132;
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    // role (static: the strap is constant after reset; registered once)
    reg [43:0] role;
    always @(posedge ck or negedge rn) if (!rn) role <= '0; else role <= sx_role(sid);
    wire [2:0] r_ga = role[2:0], r_gb = role[5:3];
    wire [2:0] r_go [0:3];
    assign r_go[0] = role[8:6]; assign r_go[1] = role[11:9]; assign r_go[2] = role[14:12]; assign r_go[3] = role[17:15];
    wire r_rt = role[18]; wire [2:0] r_ss = role[21:19]; wire [1:0] r_sh = role[23:22];
    wire [2:0] r_so [0:3];
    assign r_so[0] = role[26:24]; assign r_so[1] = role[29:27]; assign r_so[2] = role[32:30]; assign r_so[3] = role[35:33];
    wire [2:0] r_ts = role[38:36];
    genvar f, k, h;

    // ---------------- faces in: pin flop + NR relays -> centre ----------------
    wire [3:0] gc_v, sc_v; wire [W-1:0] gc_d [0:3]; wire [SW-1:0] sc_d [0:3];
    generate for (f = 0; f < 4; f = f + 1) begin : g_in
        reg [NR:0] gv, sv; reg [W-1:0] gd [0:NR]; reg [SW-1:0] sd [0:NR];
        always @(posedge ck or negedge rn)
            if (!rn) begin gv <= '0; sv <= '0; end
            else begin gv <= {gv[NR-1:0], gi_v[f]}; sv <= {sv[NR-1:0], si_v[f]}; end
        always @(posedge ck) begin
            gd[0] <= gi_d[W*f +: W]; sd[0] <= si_d[SW*f +: SW];
            for (int i = 1; i <= NR; i++) begin gd[i] <= gd[i-1]; sd[i] <= sd[i-1]; end
        end
        assign gc_v[f] = gv[NR]; assign gc_d[f] = gd[NR]; assign sc_v[f] = sv[NR]; assign sc_d[f] = sd[NR];
    end endgenerate
    reg lc_v; reg [W-1:0] lc_d;
    always @(posedge ck or negedge rn) if (!rn) lc_v <= 1'b0; else lc_v <= l_v;
    always @(posedge ck) lc_d <= l_d;

    // ---------------- gather sources: 1 leaf, 2..5 face N/E/S/W, 6 adder ----------------
    wire ad_v; wire [W-1:0] ad_d;
    function automatic [W:0] gsrc(input [2:0] s, input lv, input [W-1:0] ld, input [3:0] cv,
                                   input [W-1:0] c0, c1, c2, c3, input av, input [W-1:0] a);
        case (s)
            3'd1: gsrc = {lv, ld};
            3'd2: gsrc = {cv[0], c0};
            3'd3: gsrc = {cv[1], c1};
            3'd4: gsrc = {cv[2], c2};
            3'd5: gsrc = {cv[3], c3};
            3'd6: gsrc = {av, a};
            default: gsrc = '0;
        endcase
    endfunction
    wire [W:0] opa = gsrc(r_ga, lc_v, lc_d, gc_v, gc_d[0], gc_d[1], gc_d[2], gc_d[3], 1'b0, '0);
    wire [W:0] opb = gsrc(r_gb, lc_v, lc_d, gc_v, gc_d[0], gc_d[1], gc_d[2], gc_d[3], 1'b0, '0);
    wire a_v = opa[W], b_v = opb[W]; wire [W-1:0] a_d = opa[W-1:0], b_d = opb[W-1:0];

    // ---------------- the node: 64 x qaddf (engine lane-tree adder) ----------------
    wire [N-1:0] fa = a_d[N-1:0], fb = (MUT[0]) ? '0 : b_d[N-1:0];
    wire [N*32-1:0] y; wire [N-1:0] af, fd; wire [19:0] fd_tag; wire ov;
    generate for (k = 0; k < N; k = k + 1) begin : g_a
        ot_hdc_v41x_qaddf #(.LAT(FX), .F12(F12)) u_a (.clk(ck), .rst_n(rn), .v(1'b1), .a(a_d[N + 32*k +: 32]),
            .b(b_d[N + 32*k +: 32]), .y(y[32*k +: 32]), .fault(af[k]));
    end endgenerate
    ot_hdc_v41x_dly #(.W(N + 20), .D(FX)) u_fd (.clk(ck), .d({a_d[W-1 -: 20], fa | fb}), .q({fd_tag, fd}));
    ot_hdc_v41x_vdly #(.D(FX)) u_v (.clk(ck), .rst_n(rn), .d(a_v && r_ga != 3'd0), .q(ov));
    assign ad_v = ov; assign ad_d = {fd_tag, y, fd | af};

    // ---------------- gather out: centre register + NR relays + out pin flop ----------------
    generate for (f = 0; f < 4; f = f + 1) begin : g_go
        wire [W:0] s = gsrc(r_go[f], lc_v, lc_d, gc_v, gc_d[0], gc_d[1], gc_d[2], gc_d[3], ad_v, ad_d);
        reg [NR+1:0] v; reg [W-1:0] d [0:NR+1];
        always @(posedge ck or negedge rn) if (!rn) v <= '0; else v <= {v[NR:0], s[W]};
        always @(posedge ck) begin d[0] <= s[W-1:0]; for (int i = 1; i <= NR + 1; i++) d[i] <= d[i-1]; end
        assign go_v[f] = v[NR+1]; assign go_d[W*f +: W] = d[NR+1];
    end endgenerate
    always @(posedge ck or negedge rn) if (!rn) rt_v <= 1'b0; else rt_v <= r_rt && ad_v;
    always @(posedge ck) rt_d <= ad_d;

    // ---------------- scatter ----------------
    // head slot h of a score beat: {flags of rows 3..0, y of rows 3..0}
    function automatic [SL-1:0] slot(input [W-1:0] b, input integer hh);
        for (int r = 0; r < 4; r++) begin
            slot[128 + r] = b[r*16 + hh];
            slot[32*r +: 32] = b[N + (r*16 + hh)*32 +: 32];
        end
    endfunction
    // node input as 16 slots: from a face (8 slots, upper 8 zero) or the root's own complete beat
    reg [19:0] sn_tag; reg sn_v; reg [16*SL-1:0] sn;
    always @(*) begin
        sn_v = 1'b0; sn_tag = '0; sn = '0;
        case (r_ss)
            3'd1, 3'd2, 3'd3, 3'd4: begin
                sn_v = sc_v[r_ss - 3'd1]; sn_tag = sc_d[r_ss - 3'd1][SW-1 -: 20];
                sn[0 +: 8*SL] = sc_d[r_ss - 3'd1][8*SL-1:0];
            end
            3'd7: begin
                sn_v = r_rt && ad_v; sn_tag = ad_d[W-1 -: 20];
                for (int hh = 0; hh < 16; hh++) sn[SL*hh +: SL] = slot(ad_d, hh);
            end
            default: ;
        endcase
    end
    wire [4:0] hsh = (5'd1 << r_sh) + ((MUT[1]) ? 5'd1 : 5'd0);
    wire [8*SL-1:0] sp_l = sn[0 +: 8*SL];
    wire [16*SL-1:0] sp_rr = sn >> (SL * hsh);
    wire [8*SL-1:0] sp_r = sp_rr[0 +: 8*SL];
    function automatic [SW:0] ssrc(input [2:0] s, input [3:0] cv, input [SW-1:0] c0, c1, c2, c3,
                                    input nv, input [19:0] nt, input [8*SL-1:0] l, r);
        case (s)
            3'd1: ssrc = {cv[0], c0};
            3'd2: ssrc = {cv[1], c1};
            3'd3: ssrc = {cv[2], c2};
            3'd4: ssrc = {cv[3], c3};
            3'd5: ssrc = {nv, nt, l};
            3'd6: ssrc = {nv, nt, r};
            default: ssrc = '0;
        endcase
    endfunction
    generate for (f = 0; f < 4; f = f + 1) begin : g_so
        wire [SW:0] s = ssrc(r_so[f], sc_v, sc_d[0], sc_d[1], sc_d[2], sc_d[3], sn_v, sn_tag, sp_l, sp_r);
        reg [NR+1:0] v; reg [SW-1:0] d [0:NR+1];
        always @(posedge ck or negedge rn) if (!rn) v <= '0; else v <= {v[NR:0], s[SW]};
        always @(posedge ck) begin d[0] <= s[SW-1:0]; for (int i = 1; i <= NR + 1; i++) d[i] <= d[i-1]; end
        assign so_v[f] = v[NR+1]; assign so_d[SW*f +: SW] = d[NR+1];
    end endgenerate
    wire [SW:0] ts = ssrc(r_ts, sc_v, sc_d[0], sc_d[1], sc_d[2], sc_d[3], sn_v, sn_tag, sp_l, sp_r);
    always @(posedge ck or negedge rn) if (!rn) t_v <= 1'b0; else t_v <= ts[SW];
    always @(posedge ck) begin t_tag <= ts[SW-1 -: 20]; t_f <= ts[128 +: 4]; t_y <= ts[127:0]; end

    // ---------------- static-schedule checks (sticky; never re-time anything) ----------------
    reg [3:0] g_used, s_used;
    always @(*) begin
        g_used = '0; s_used = '0;
        for (int i = 0; i < 4; i++) begin
            if (r_ga == 3'(2 + i) || r_gb == 3'(2 + i)) g_used[i] = 1'b1;
            for (int j = 0; j < 4; j++) begin
                if (r_go[j] == 3'(2 + i)) g_used[i] = 1'b1;
                if (r_so[j] == 3'(1 + i)) s_used[i] = 1'b1;
            end
            if (r_ss == 3'(1 + i) || r_ts == 3'(1 + i)) s_used[i] = 1'b1;
        end
    end
    wire node = r_ga != 3'd0;
    wire mis = node && (a_v != b_v || (a_v && a_d[W-1 -: 20] != b_d[W-1 -: 20]));
    wire stray = |(gc_v & ~g_used) || |(sc_v & ~s_used);
    always @(posedge ck or negedge rn) if (!rn) fault <= 1'b0; else if (mis || stray) fault <= 1'b1;
endmodule
