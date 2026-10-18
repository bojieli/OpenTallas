`timescale 1ns/1ps
`default_nettype none
// HBM-B-RTL1 2026-10-17 (owner 0do, plan (b) d4g): PHY-side host configuration / status leaf, one per quadrant.
//
// d4f: host_cp_ingress (ot_hbm_host_static_ingress) broadcast its F20 configuration bundle straight to ~70 target
// instances (~194 sink pins, relay depths 27..40) and host_status (ot_hbm_status_join_fa) took ~70 ready/active and
// ~107 fault bits straight from those targets.  d4g: the ingress drives 4 of these leaves (one fat equal-age lane per
// quadrant), each leaf re-launches the bundle to its own quadrant's targets, and the same leaf brings the quadrant's
// per-target status bits back to host_status.  No arithmetic, no OR-collapse: every target keeps its own status bit,
// so host_status (participation per target id, block_ready AND over participants) is unchanged.
//
// Datapath (fixed latency, no ready / credit / arbitration -- static schedule rule 10-14):
//   configuration  pin flop (stage 1) -> NCP replicated copy registers (stage 2, one group per sink group, so no net
//                  fans out to the whole quadrant) -> output pins.  Latency CFG_LAT = 2 edges, identical for every
//                  copy and every bit (equal age).  cfg_v / desc_v / launch_v are reset flops (synced rst_n); the
//                  payload (target/addr/data/desc fields) is unreset, qualified by the valids (as the ingress).
//   status         t_ready / t_active / t_fault: pin flop (stage 1) -> output flop (stage 2) -> output pins.
//                  Latency ST_LAT = 2 edges, the same for every bit; bit order preserved (s_ready[i] = t_ready[i]).
// Pin rule (owner 10-15): every input lands in a pin flop, every output is a flop Q.  rst_n drives only an
// ot_rst_relay (2 sync + 1 tree stage per region: assert immediate, release +3 edges -- configuration latency only).
// Regions: 0 = configuration valids (pin + copies), 1 = status pin/output flops.
//
// Composition rule for host_status (documented, checked by tb_hbm_host_cfg_leaf_lockstep): the join sees the ingress
// frame (cfg_v/desc_v/launch_v/cfg_target) at the ingress edge but a target's status now returns CFG_LAT + ST_LAT
// = 4 edges later than in d4f (plus the die's lane relays to/from the leaf).  The join's readiness GUARD must cover
// that round trip: GUARD(d4g) = GUARD(d4f) + CFG_LAT + ST_LAT + (lane relay edges ingress->leaf + leaf->join).
// RRELAY of the join is unchanged (it only delays the join's own reset release).
//
// MUT (bench only): 1 copy 1 drops cfg_data bit 0; 2 copy 1 one stage short (stage-1 value straight out);
//                   3 status ready bits 0/1 swapped; 4 status fault bit 0 dropped.
module ot_hbm_host_cfg_leaf #(
    parameter integer NCP = 2,           // replicated output copies (sink groups)
    parameter integer NT  = 18,          // per-target ready / active bits carried
    parameter integer NF  = 28,          // per-target fault bits carried
    parameter integer MUT = 0
)(
    input  wire clk, rst_n,
    // from the ingress (or its lane)
    input  wire        cfg_v,
    input  wire [7:0]  cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire        desc_v,
    input  wire [11:0] desc_base,
    input  wire [12:0] desc_limit,
    input  wire [15:0] desc_loops,
    input  wire        launch_v,
    // NCP copies to the quadrant targets
    output wire [NCP-1:0]      o_cfg_v,
    output wire [NCP*8-1:0]    o_cfg_target,
    output wire [NCP*12-1:0]   o_cfg_addr,
    output wire [NCP*256-1:0]  o_cfg_data,
    output wire [NCP-1:0]      o_desc_v,
    output wire [NCP*12-1:0]   o_desc_base,
    output wire [NCP*13-1:0]   o_desc_limit,
    output wire [NCP*16-1:0]   o_desc_loops,
    output wire [NCP-1:0]      o_launch_v,
    // status fan-in from the quadrant targets, to host_status
    input  wire [NT-1:0] t_ready, t_active,
    input  wire [NF-1:0] t_fault,
    output reg  [NT-1:0] s_ready, s_active,
    output reg  [NF-1:0] s_fault
);
    localparam integer PW = 8 + 12 + 256 + 12 + 13 + 16;   // unreset payload width = 317
    wire [1:0] rr;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));

    // ---- stage 1: pin flops
    reg cv_p, dv_p, lv_p;
    reg [PW-1:0] pl_p;
    always @(posedge clk) pl_p <= {desc_loops, desc_limit, desc_base, cfg_data, cfg_addr, cfg_target};
    always @(posedge clk or negedge rr[0])
        if (!rr[0]) begin cv_p <= 1'b0; dv_p <= 1'b0; lv_p <= 1'b0; end
        else begin cv_p <= cfg_v; dv_p <= desc_v; lv_p <= launch_v; end

    // ---- stage 2: NCP replicated copy registers
    genvar g;
    generate for (g = 0; g < NCP; g = g + 1) begin : g_cp
        (* keep = "true" *) reg cv_c, dv_c, lv_c;
        (* keep = "true" *) reg [PW-1:0] pl_c;
        wire [PW-1:0] pl_m = (MUT == 1 && g == 1) ? (pl_p & ~({{(PW-21){1'b0}}, 1'b1, 20'd0})) : pl_p;
        always @(posedge clk) pl_c <= pl_m;
        always @(posedge clk or negedge rr[0])
            if (!rr[0]) begin cv_c <= 1'b0; dv_c <= 1'b0; lv_c <= 1'b0; end
            else begin cv_c <= cv_p; dv_c <= dv_p; lv_c <= lv_p; end
        wire short = (MUT == 2 && g == 1);
        wire [PW-1:0] pl_o = short ? pl_p : pl_c;
        assign o_cfg_v[g]               = short ? cv_p : cv_c;
        assign o_desc_v[g]              = short ? dv_p : dv_c;
        assign o_launch_v[g]            = short ? lv_p : lv_c;
        assign o_cfg_target[g*8 +: 8]   = pl_o[0 +: 8];
        assign o_cfg_addr[g*12 +: 12]   = pl_o[8 +: 12];
        assign o_cfg_data[g*256 +: 256] = pl_o[20 +: 256];
        assign o_desc_base[g*12 +: 12]  = pl_o[276 +: 12];
        assign o_desc_limit[g*13 +: 13] = pl_o[288 +: 13];
        assign o_desc_loops[g*16 +: 16] = pl_o[301 +: 16];
    end endgenerate

    // ---- status: pin flops -> output flops (bit order preserved)
    reg [NT-1:0] rdy_p, act_p;
    reg [NF-1:0] flt_p;
    wire [NT-1:0] rdy_m;
    generate if (MUT == 3 && NT >= 2) begin : g_m3
        assign rdy_m = {rdy_p[NT-1:2], rdy_p[0], rdy_p[1]};
    end else begin : g_m3n
        assign rdy_m = rdy_p;
    end endgenerate
    always @(posedge clk or negedge rr[1])
        if (!rr[1]) begin
            rdy_p <= {NT{1'b0}}; act_p <= {NT{1'b0}}; flt_p <= {NF{1'b0}};
            s_ready <= {NT{1'b0}}; s_active <= {NT{1'b0}}; s_fault <= {NF{1'b0}};
        end else begin
            rdy_p <= t_ready; act_p <= t_active; flt_p <= t_fault;
            s_ready <= rdy_m; s_active <= act_p;
            s_fault <= (MUT == 4) ? (flt_p & ~{{(NF-1){1'b0}}, 1'b1}) : flt_p;
        end
endmodule
`default_nettype wire
`default_nettype none
// Hardened master (hdie_host_cfg_leaf_r1): ot_hbm_host_cfg_leaf at NCP 2 with each copy group on its own ports, so the
// kit puts copy A on the W face and copy B on the E face (each to its own half of the quadrant's targets).
module ot_hbm_host_cfg_leaf2 #(parameter integer NT = 20, parameter integer NF = 32, parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [NT-1:0] t_ready, t_active, input wire [NF-1:0] t_fault,
    output wire [NT-1:0] s_ready, s_active, output wire [NF-1:0] s_fault
);
    ot_hbm_host_cfg_leaf #(.NCP(2), .NT(NT), .NF(NF), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .o_cfg_v({b_cfg_v, a_cfg_v}), .o_cfg_target({b_cfg_target, a_cfg_target}), .o_cfg_addr({b_cfg_addr, a_cfg_addr}),
        .o_cfg_data({b_cfg_data, a_cfg_data}), .o_desc_v({b_desc_v, a_desc_v}), .o_desc_base({b_desc_base, a_desc_base}),
        .o_desc_limit({b_desc_limit, a_desc_limit}), .o_desc_loops({b_desc_loops, a_desc_loops}),
        .o_launch_v({b_launch_v, a_launch_v}),
        .t_ready(t_ready), .t_active(t_active), .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
`default_nettype wire
`default_nettype none
// d4g per-quadrant hardened masters (HBM-B-RTL1b 10-17): ot_hbm_host_cfg_leaf2 at the EXACT per-quadrant status
// widths of host_cfg_leaf_map_d4g.json (SW 18/29, SE 18/26, NW 19/29, NE 14/23), so every t_ready/t_active/t_fault
// input is driven by a real target/source pin in its die and no input is tied (owner 10-14 no-stubs rule; the
// NT20/NF32 leaf2 master would leave 1..6 ready/active and 3..9 fault inputs open per quadrant).  SW+NW cannot merge
// (NT19 would leave one SW ready/active pair tied).  Every output (both copy groups, every status bit) has a sink.
module ot_hbm_host_cfg_leaf_sw #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [17:0] t_ready, t_active, input wire [28:0] t_fault,
    output wire [17:0] s_ready, s_active, output wire [28:0] s_fault
);
    ot_hbm_host_cfg_leaf2 #(.NT(18), .NF(29), .MUT(MUT)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
module ot_hbm_host_cfg_leaf_se #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [17:0] t_ready, t_active, input wire [25:0] t_fault,
    output wire [17:0] s_ready, s_active, output wire [25:0] s_fault
);
    ot_hbm_host_cfg_leaf2 #(.NT(18), .NF(26), .MUT(MUT)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
module ot_hbm_host_cfg_leaf_nw #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [18:0] t_ready, t_active, input wire [28:0] t_fault,
    output wire [18:0] s_ready, s_active, output wire [28:0] s_fault
);
    ot_hbm_host_cfg_leaf2 #(.NT(19), .NF(29), .MUT(MUT)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
module ot_hbm_host_cfg_leaf_ne #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [13:0] t_ready, t_active, input wire [22:0] t_fault,
    output wire [13:0] s_ready, s_active, output wire [22:0] s_fault
);
    ot_hbm_host_cfg_leaf2 #(.NT(14), .NF(23), .MUT(MUT)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
`default_nettype wire
