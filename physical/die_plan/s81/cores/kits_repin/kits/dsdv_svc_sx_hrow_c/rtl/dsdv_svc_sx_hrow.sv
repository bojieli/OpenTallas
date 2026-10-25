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
    reg [3:0] sid_q; reg hb_q;
    always @(posedge ck) begin sid_q <= sid; hb_q <= hb; end
    reg [43:0] role;
    always @(posedge ck or negedge rn) if (!rn) role <= '0; else role <= sx_role(sid_q);
    wire [2:0] r_ga = role[2:0], r_gb = role[5:3];
    wire [2:0] r_go [0:3];
    assign r_go[0] = role[8:6]; assign r_go[1] = role[11:9]; assign r_go[2] = role[14:12]; assign r_go[3] = role[17:15];
    wire r_rt = role[18]; wire [2:0] r_ss = role[21:19]; wire [1:0] r_sh = role[23:22];
    wire [2:0] r_so [0:3];
    assign r_so[0] = role[26:24]; assign r_so[1] = role[29:27]; assign r_so[2] = role[32:30]; assign r_so[3] = role[35:33];
    wire [2:0] r_ts = role[38:36];
    wire own = role[39] == hb_q;                  // this half holds the tapped head (head bit 0)
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

    // ---------------- the node row: 8 x qaddf (this half's heads) ----------------
    wire [N-1:0] fa = a_d[N-1:0], fb = (MUT[0]) ? '0 : b_d[N-1:0];
    wire [N*32-1:0] y; wire [N-1:0] af, fd; wire [TW-1:0] fd_tag; wire ov;
    generate for (k = 0; k < N; k = k + 1) begin : g_a
        ot_hdc_v41x_qaddf #(.LAT(FX), .F12(F12)) u_a (.clk(ck), .rst_n(rn), .v(1'b1), .a(a_d[N + 32*k +: 32]),
            .b(b_d[N + 32*k +: 32]), .y(y[32*k +: 32]), .fault(af[k]));
    end endgenerate
    ot_hdc_v41x_dly #(.W(N + TW), .D(FX)) u_fd (.clk(ck), .d({a_d[W-1 -: TW], fa | fb}), .q({fd_tag, fd}));
    ot_hdc_v41x_vdly #(.D(FX)) u_v (.clk(ck), .rst_n(rn), .d(a_v && r_ga != 3'd0), .q(ov));
    assign ad_v = ov; assign ad_d = {fd_tag, y, fd | af};

    // ---------------- gather out: the centre register (the slice's stations follow) ----------------
    generate for (f = 0; f < 4; f = f + 1) begin : g_go
        wire [W:0] s = gsrc(r_go[f], lc_v, lc_d, gc_v, gc_d[0], gc_d[1], gc_d[2], gc_d[3], ad_v, ad_d);
        reg v; reg [W-1:0] d;
        always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= s[W];
        always @(posedge ck) d <= s[W-1:0];
        assign go_v[f] = v; assign go_d[W*f +: W] = d;
    end endgenerate
    always @(posedge ck or negedge rn) if (!rn) rt_v <= 1'b0; else rt_v <= r_rt && ad_v;
    always @(posedge ck) rt_d <= ad_d;

    // ---------------- scatter (head slots, this row) ----------------
    reg [TW-1:0] sn_tag; reg sn_v; reg [2*NS*SL-1:0] sn;
    always @(*) begin
        sn_v = 1'b0; sn_tag = '0; sn = '0;
        case (r_ss)
            3'd1, 3'd2, 3'd3, 3'd4: begin
                sn_v = sc_v[r_ss - 3'd1]; sn_tag = sc_d[r_ss - 3'd1][SW-1 -: TW];
                sn[0 +: NS*SL] = sc_d[r_ss - 3'd1][NS*SL-1:0];
            end
            3'd7: begin
                sn_v = r_rt && ad_v; sn_tag = ad_d[W-1 -: TW];
                for (int hh = 0; hh < N; hh++) sn[SL*hh +: SL] = {ad_d[hh], ad_d[N + 32*hh +: 32]};
            end
            default: ;
        endcase
    end
    // absolute shift 1 << r_sh (8, 4, 2, 1 heads) = local shift 4, 2, 1 inside a parity half; the pair node (r_sh 0)
    // does not shift (see the header)
    wire [3:0] hsh = ((r_sh == 2'd0) ? 4'd0 : (4'd1 << (r_sh - 2'd1))) + ((MUT[1]) ? 4'd1 : 4'd0);
    wire [NS*SL-1:0] sp_l = sn[0 +: NS*SL];
    wire [2*NS*SL-1:0] sp_rr = sn >> (SL * hsh);
    wire [NS*SL-1:0] sp_r = sp_rr[0 +: NS*SL];
    function automatic [SW:0] ssrc(input [2:0] s, input [3:0] cv, input [SW-1:0] c0, c1, c2, c3,
                                    input nv, input [TW-1:0] nt, input [NS*SL-1:0] l, r);
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
        reg v; reg [SW-1:0] d;
        always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= s[SW];
        always @(posedge ck) d <= s[SW-1:0];
        assign so_v[f] = v; assign so_d[SW*f +: SW] = d;
    end endgenerate
    wire [SW:0] ts = ssrc(r_ts, sc_v, sc_d[0], sc_d[1], sc_d[2], sc_d[3], sn_v, sn_tag, sp_l, sp_r);
    always @(posedge ck or negedge rn) if (!rn) t_v <= 1'b0; else t_v <= own && ts[SW];
    always @(posedge ck) begin
        t_tag <= own ? ts[SW-1 -: TW] : '0; t_f <= own && ts[32]; t_y <= own ? ts[31:0] : '0;
    end

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
    wire mis = node && (a_v != b_v || (a_v && a_d[W-1 -: TW] != b_d[W-1 -: TW]));
    wire stray = |(gc_v & ~g_used) || |(sc_v & ~s_used);
    // S81U-SVCX3: the check is registered once beside the node (gate 2: face pin flop -> 5:1 operand mux -> tag compare
    // -> the S-face fault pin flop was the worst reg->reg path, -64.7 ps); the sticky fault reports one cycle later.
    reg chk;
    always @(posedge ck or negedge rn) if (!rn) chk <= 1'b0; else chk <= mis || stray;
    (* keep *) reg fault_q;   // kits_repin: sticky state (internal); fault = the port copy
    always @(posedge ck or negedge rn) if (!rn) fault_q <= 1'b0; else if (chk) fault_q <= 1'b1;
    always @(posedge ck or negedge rn) if (!rn) fault <= 1'b0; else fault <= fault_q | chk;
endmodule
