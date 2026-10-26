`timescale 1ns/1ps
// KDIE5-RTL 2026-10-22: pin-registered successors qkd_kvs_grp_r2 / qkd_kvs_grp_h_r2 of the release KV die landing-group
// tiles (qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj.sv modules qkd_kvs_grp / qkd_kvs_grp_h; that file is NOT modified:
// each successor instantiates the unchanged release module as u_core).  Opt-in: the die binds these masters only under
// OT_KV_GRP_R2=1 (tools/qwen_kv_die/kv_static_die.py); every other design point is unchanged.
//
// Why: the release group tiles carry 432 (grp) / 306 (grp_h) combinational input -> output bits (i_ctl -> o_dn 271,
// i_up -> o_ctl 126, x -> y 35), the i_up -> o_ctl word spans the 1188-um tile unregistered, and the cf1 fault cone of
// grp_h sits >= 631 um from its pins (daemon FLOORPLAN_MARGIN, claude/kdie5-tv-1022@38f92570d).
//
// Structure (no combinational input -> output path is left; every pass word is registered at both pins and relayed
// at 1/3 and 2/3 of the 1188-um N <-> S span, legs <= ~400 um):
//   fan chain   i_ctl (N) -> q0 entry face flop -> r1 -> r2 -> o_dn exit face flop (S)     = 4 core edges per group hop
//   local view  u_core.i_ctl = q0 delayed by HOP * (7 - depth) more edges, so EVERY group of a stack sees the root's
//               fan word at the same age E = 1 + HOP * 7 = 29 edges (depth = chain position from the stack root,
//               slg index n -> depth via kv_static_die ORDER (4,5,0,1,2,3,6,7) chain slots 7..0: n 7,6,3,2,1,0,5,4 ->
//               depth 0..7); the chain end (grp_h, n 4) is depth 7 = delay 0.  The 194 locally used bits [193:0] are
//               delayed together (cfg + per-group strobes + landing / phase words), so u_core sees exactly the release
//               tile's i_ctl stream 29 edges later in every group: ONE uniform compiler delta (groups += 29).
//   gather      i_up (S) -> u0 -> u1 -> u2 -> o_ctl[143:18] exit flop (N)                   = 4 core edges per hop
//               own status u_core.o_ctl[17:0] -> o1 -> o2 -> o_ctl[17:0] exit flop (N)        = 3 core edges
//   cf1 fault   i_pc<q>[290] -> f0 entry flop (at the i_pc<q> face) -> f1 -> u_core cf1       = 2 core edges
//   EST / tok   x__est[0] / x__tok / x__tep -> entry flop -> y exit flop (W, beside)           = 2 core edges
// Pass / delay flops have no reset (as the die relays qkd_rly_*): the regional reset hold (OT_KV_RST_HOLD 273 edges,
// clock running) flushes them with the reset root's zeros (fan chain + local delay <= 29, gather <= 32 edges).
// Every other port (kreq / vreq / rsp / krsp / i_pc / o_pc / af* / straps / clocks / resets) is u_core's, unchanged.
// Bench: tools/qwen_kv_die/kvs_grp_r2_bench.sh (lockstep vs the release module on delayed inputs, mutants must FAIL).

module qkd_kvs_grp_r2 (
    input wire ck,
    input wire rst_n,
    input wire [0:0] afk,
    input wire [0:0] afv,
    input wire [0:0] afu,
    input wire hck,
    input wire hrst_n,
    input wire [1:0] slg__cfg_stack,
    input wire [2:0] slg__cfg_group,
    input wire [37:0] kreq,
    input wire [14:0] vreq,
    input wire [12:0] x__est,
    input wire [17:0] x__tok,
    input wire [15:0] x__tep,
    output wire [1055:0] rsp,
    output wire [1061:0] krsp,
    output wire [0:0] af__fault,
    output wire [0:0] y__est__0_1,
    output wire [17:0] y__tok,
    output wire [15:0] y__tep,
    input wire [270:0] i_ctl,
    input wire [304:0] i_pc0,
    input wire [304:0] i_pc1,
    input wire [304:0] i_pc2,
    input wire [304:0] i_pc3,
    output wire [127:0] o_pc0,
    output wire [127:0] o_pc1,
    output wire [127:0] o_pc2,
    output wire [127:0] o_pc3,
    output wire [270:0] o_dn,
    input wire [143:0] i_up,
    output wire [143:0] o_ctl
);
    localparam LW = 194;                 // locally used i_ctl bits [193:0]
    localparam NT = 8;                   // taps: delay 4 * t, t = 7 - depth (0..7)
    localparam DL = 4 * (NT - 1);        // 28 delay stages
    localparam NC = 8;                   // tap-select replicas (<= 25 mux loads each)
    // ---- fan chain: entry face flop, two relays, rotated exit face flop
    reg [270:0] q0, r1, r2, dn_q;
    always @(posedge ck) begin
        q0 <= i_ctl;
        r1 <= q0;
        r2 <= r1;
`ifdef KVS_GRP_R2_MUT1
        dn_q <= {r1[193:183], r1[270:194], r1[182:0]};              // MUT 1: one relay skipped (3-edge hop)
`else
        dn_q <= {r2[193:183], r2[270:194], r2[182:0]};
`endif
    end
    assign o_dn = dn_q;
    // ---- local view: uniform age, delay 4 * (7 - depth)
    reg [LW-1:0] dl [0:DL-1];
    integer k;
    always @(posedge ck) begin
        dl[0] <= q0[LW-1:0];
        for (k = 1; k < DL; k = k + 1) dl[k] <= dl[k-1];
    end
    function [2:0] tap_of;               // slg index n -> t = 7 - depth
        input [2:0] n;
        case (n)
            3'd7: tap_of = 3'd7;  3'd6: tap_of = 3'd6;  3'd3: tap_of = 3'd5;  3'd2: tap_of = 3'd4;
            3'd1: tap_of = 3'd3;  3'd0: tap_of = 3'd2;  3'd5: tap_of = 3'd1;  default: tap_of = 3'd0;
        endcase
    endfunction
    wire [2:0] tap_w = tap_of(slg__cfg_group);
    (* keep *) reg [NT-1:0] sel_q [0:NC-1];   // kept one-hot copies of the (static) strap decode
    integer c;
    always @(posedge ck)
        for (c = 0; c < NC; c = c + 1)
`ifdef KVS_GRP_R2_MUT2
            sel_q[c] <= {{(NT-1){1'b0}}, 1'b1} << ((tap_w == 3'd7) ? 3'd6 : tap_w + 3'd1);   // MUT 2: tap one hop (4 edges) late
`else
            sel_q[c] <= {{(NT-1){1'b0}}, 1'b1} << tap_w;
`endif
    wire [LW-1:0] tap [0:NT-1];
    assign tap[0] = q0[LW-1:0];
    genvar t, b;
    generate
        for (t = 1; t < NT; t = t + 1) begin : g_tap
            assign tap[t] = dl[4 * t - 1];
        end
    endgenerate
    wire [LW-1:0] lv;
    generate
        for (b = 0; b < LW; b = b + 1) begin : g_lv
            wire [NT-1:0] s = sel_q[b % NC];
            wire [NT-1:0] v;
            for (t = 0; t < NT; t = t + 1) begin : g_v
                assign v[t] = tap[t][b];
            end
            assign lv[b] = |(s & v);
        end
    endgenerate
    // ---- cf1 fault inputs: entry flop at the i_pc<q> face + one relay
    reg [3:0] f0, f1;
    always @(posedge ck) begin
        f0 <= {i_pc3[290], i_pc2[290], i_pc1[290], i_pc0[290]};
`ifdef KVS_GRP_R2_MUT3
        f1 <= {i_pc3[290], i_pc2[290], i_pc1[290], i_pc0[290]};     // MUT 3: cf1 fault entry flop bypassed
`else
        f1 <= f0;
`endif
    end
    wire [304:0] c_pc0 = {i_pc0[304:291], f1[0], i_pc0[289:0]};
    wire [304:0] c_pc1 = {i_pc1[304:291], f1[1], i_pc1[289:0]};
    wire [304:0] c_pc2 = {i_pc2[304:291], f1[2], i_pc2[289:0]};
    wire [304:0] c_pc3 = {i_pc3[304:291], f1[3], i_pc3[289:0]};
    // ---- the release tile, unchanged
    wire [270:0] c_dn;
    wire [143:0] c_ctl;
    wire [0:0] c_yest;
    wire [17:0] c_ytok;
    wire [15:0] c_ytep;
    qkd_kvs_grp u_core (.ck(ck), .rst_n(rst_n), .afk(afk), .afv(afv), .afu(afu), .hck(hck), .hrst_n(hrst_n),
        .slg__cfg_stack(slg__cfg_stack), .slg__cfg_group(slg__cfg_group), .kreq(kreq), .vreq(vreq),
        .x__est(x__est), .x__tok(x__tok), .x__tep(x__tep), .rsp(rsp), .krsp(krsp), .af__fault(af__fault),
        .y__est__0_1(c_yest), .y__tok(c_ytok), .y__tep(c_ytep), .i_ctl({q0[270:LW], lv}),
        .i_pc0(c_pc0), .i_pc1(c_pc1), .i_pc2(c_pc2), .i_pc3(c_pc3), .o_pc0(o_pc0), .o_pc1(o_pc1), .o_pc2(o_pc2),
        .o_pc3(o_pc3), .o_dn(c_dn), .i_up(144'd0), .o_ctl(c_ctl));
    // ---- gather: pass word 4 edges per hop, own status 3 edges
    reg [125:0] u0, u1, u2, up_q;
    reg [17:0] o1, o2, own_q;
    always @(posedge ck) begin
        u0 <= i_up[125:0];
        u1 <= u0;
        u2 <= u1;
`ifdef KVS_GRP_R2_MUT4
        up_q <= {u2[125:2], u2[0], u2[1]};                            // MUT 4: gather pass bits 0 / 1 swapped
`else
        up_q <= u2;
`endif
        o1 <= c_ctl[17:0];
        o2 <= o1;
        own_q <= o2;
    end
    assign o_ctl = {up_q, own_q};
    // ---- EST / token pass words: entry + exit flop (W face, beside each other)
    reg [34:0] xe0, xe1;
    always @(posedge ck) begin
        xe0 <= {x__tep, x__tok, x__est[0]};
        xe1 <= xe0;
    end
    assign {y__tep, y__tok, y__est__0_1} = xe1;
endmodule

// grp_h: the chain-end group (depth 7: no local delay; o_dn is unread by the die and leaves beside i_ctl)
module qkd_kvs_grp_h_r2 (
    input wire ck,
    input wire rst_n,
    input wire [0:0] afk,
    input wire [0:0] afv,
    input wire hck,
    input wire hrst_n,
    input wire [1:0] slg__cfg_stack,
    input wire [2:0] slg__cfg_group,
    input wire [37:0] kreq,
    input wire [14:0] vreq,
    input wire [12:0] x__est,
    input wire [17:0] x__tok,
    input wire [15:0] x__tep,
    output wire [1055:0] rsp,
    output wire [1061:0] krsp,
    output wire [0:0] af__fault,
    output wire [0:0] y__est__0_1,
    output wire [17:0] y__tok,
    output wire [15:0] y__tep,
    input wire [270:0] i_ctl,
    input wire [304:0] i_pc0,
    input wire [304:0] i_pc1,
    input wire [304:0] i_pc2,
    input wire [304:0] i_pc3,
    output wire [127:0] o_pc0,
    output wire [127:0] o_pc1,
    output wire [127:0] o_pc2,
    output wire [127:0] o_pc3,
    output wire [270:0] o_dn,
    output wire [143:0] o_ctl
);
    reg [270:0] q0, dn_q;
    always @(posedge ck) begin
        q0 <= i_ctl;
`ifdef KVS_GRP_R2_MUT1
        dn_q <= {i_ctl[193:183], i_ctl[270:194], i_ctl[182:0]};       // MUT 1: o_dn entry flop bypassed
`else
        dn_q <= {q0[193:183], q0[270:194], q0[182:0]};
`endif
    end
    assign o_dn = dn_q;
    reg [3:0] f0, f1;
    always @(posedge ck) begin
        f0 <= {i_pc3[290], i_pc2[290], i_pc1[290], i_pc0[290]};
`ifdef KVS_GRP_R2_MUT3
        f1 <= {i_pc3[290], i_pc2[290], i_pc1[290], i_pc0[290]};
`else
        f1 <= f0;
`endif
    end
    wire [304:0] c_pc0 = {i_pc0[304:291], f1[0], i_pc0[289:0]};
    wire [304:0] c_pc1 = {i_pc1[304:291], f1[1], i_pc1[289:0]};
    wire [304:0] c_pc2 = {i_pc2[304:291], f1[2], i_pc2[289:0]};
    wire [304:0] c_pc3 = {i_pc3[304:291], f1[3], i_pc3[289:0]};
    wire [270:0] c_dn;
    wire [143:0] c_ctl;
    wire [0:0] c_yest;
    wire [17:0] c_ytok;
    wire [15:0] c_ytep;
    qkd_kvs_grp_h u_core (.ck(ck), .rst_n(rst_n), .afk(afk), .afv(afv), .hck(hck), .hrst_n(hrst_n),
        .slg__cfg_stack(slg__cfg_stack), .slg__cfg_group(slg__cfg_group), .kreq(kreq), .vreq(vreq),
        .x__est(x__est), .x__tok(x__tok), .x__tep(x__tep), .rsp(rsp), .krsp(krsp), .af__fault(af__fault),
        .y__est__0_1(c_yest), .y__tok(c_ytok), .y__tep(c_ytep),
`ifdef KVS_GRP_R2_MUT2
        .i_ctl(i_ctl),                                                  // MUT 2: local view one edge early
`else
        .i_ctl(q0),
`endif
        .i_pc0(c_pc0), .i_pc1(c_pc1), .i_pc2(c_pc2), .i_pc3(c_pc3), .o_pc0(o_pc0), .o_pc1(o_pc1), .o_pc2(o_pc2),
        .o_pc3(o_pc3), .o_dn(c_dn), .o_ctl(c_ctl));
    // own status (the release tile repeats it 8 times): 3 edges, one kept chain, 8 exit copies at the N face
    reg [17:0] o1, o2;
    reg [143:0] own_q;
    always @(posedge ck) begin
        o1 <= c_ctl[17:0];
        o2 <= o1;
`ifdef KVS_GRP_R2_MUT4
        own_q <= {8{o1}};                                               // MUT 4: own status one edge early
`else
        own_q <= {8{o2}};
`endif
    end
    assign o_ctl = own_q;
    reg [34:0] xe0, xe1;
    always @(posedge ck) begin
        xe0 <= {x__tep, x__tok, x__est[0]};
        xe1 <= xe0;
    end
    assign {y__tep, y__tok, y__est__0_1} = xe1;
endmodule
