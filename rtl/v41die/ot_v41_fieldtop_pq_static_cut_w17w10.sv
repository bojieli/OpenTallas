// Additive source-selected PQ cut: real c_tag -> fb_go_tag; packed fr_row[15:14] returns actual bank tag.
// Additive default-off full-parent provider hook, exact existing field/VM body.
// Additive source hook; same field and VM, only the default-off issuer address repair.
// Experimental companion: PQ default off; no adoption or clock claim beyond its own screen.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_fieldtop_pq_w17w10: SUCCESSOR of ot_v41_fieldtop_w17w10 (DS-ROM recovery lever "field", 2026-10-04): the
// pipelined-phase spine ot_v41_spine_pq_w17w10, the vector-memory model and the PQ field ot_v41_field_pq_w17w10.
// Flat build only (no RT_CUT).  Debug outputs ev_go / ev_end / ev_tag (the spine's op events) for the bench.
//
// ot_v41_fieldtop_w17w10: the spine, a vector-memory model and the ROM field -- the unit of the W17 runtime-
// composition equivalence gate (tools/w17_w10_field_rt_gate.py).
//
// Flat (default): everything in one model.  RT_CUT defined: the field is NOT instantiated; its broadcast
// inputs become outputs (fb_*) and its root outputs become inputs (fr_*), so the runtime host composes
// the field from separately compiled ot_v41_pair_w17w10 / ot_v41_retn_w17w10 / ot_v41_ret_root models.  Nothing else
// differs between the two builds.
//
// Vector memory model: 2^VAW 32-bit words, a VRD-wide read port (registered, one cycle), R write ports
// (increasing port order on a same-address collision).  Contents: +OT_ROM_DIR=<dir>/vm.hex, or public.
// ---------------------------------------------------------------------------
module ot_v41_fieldtop_pq_static_cut_w17w10 #(
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer BP = 0,
    parameter integer NP = 8,
    parameter integer R = 2,
    parameter integer NBF = 2,
    parameter integer PHW = 10,
    parameter integer SAW = 14,
    parameter integer VAW = 14,
    parameter integer VRD = 64,
    parameter integer KMAX = 6144,
    parameter integer BST = 2,
    parameter integer RST = 1,
    parameter integer PQ = 0,
    parameter integer ADDR_LOOKAHEAD = 0,
    parameter integer STATIC_CONTROLS = 0,
    parameter integer CONTROL_STAGE = 37,
    parameter integer GAP = 12,
    parameter integer GUARD = 180,
    parameter integer GSLACK = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [PHW-1:0]    i_ph,
    input  wire [2:0]        i_np,
    input  wire [VAW-1:0]    i_xbase,
    input  wire [VAW-1:0]    i_xps,
    input  wire [VAW-1:0]    i_obase,
    input  wire [VAW-1:0]    i_ops,
    output wire              ready,
    output wire              idle,
    output wire [R-1:0]      o_we,
    output wire [R*VAW-1:0]  o_addr,
    output wire [R*32-1:0]   o_data,
    output wire              fault,
    output wire [31:0]       phase_cycles,
    output wire              ev_go,
    output wire              ev_end,
    output wire [1:0]        ev_tag
`ifdef RT_CUT
    ,
    output wire              fb_cfg_go,
    output wire [PHW-1:0]    fb_cfg_ph,
    output wire [2:0]        fb_cfg_np,
    output wire              fb_go,
    output wire              fb_go_bf,
    output wire [1:0]        fb_go_tag,
    output wire              fb_xs_v,
    output wire [7:0]        fb_xs_p,
    output wire [2:0]        fb_xs_b,
    output wire [1:0]        fb_xs_sv,
    output wire [255:0]      fb_xs_q0,
    output wire [9:0]        fb_xs_e0,
    output wire [255:0]      fb_xs_q1,
    output wire [9:0]        fb_xs_e1,
    output wire [2:0]        fb_xs_pos,
    output wire [2:0]        fb_xb_pos,
    output wire              fb_xb_v,
    output wire [2:0]        fb_xb_b,
    output wire [3:0]        fb_xb_sv,
    output wire [31:0]       fb_xb_u,
    output wire [1023:0]     fb_xb_d,
    input  wire [R-1:0]      fr_v,
    input  wire [16*R-1:0]   fr_row,
    input  wire [3*R-1:0]    fr_pos,
    input  wire [32*R-1:0]   fr_fp32,
    input  wire [16*R-1:0]   fr_bf16,
    input  wire [R-1:0]      fr_e,
    input  wire              fr_fault
`endif
);
    // vector memory
    reg [31:0] vm [0:(1 << VAW)-1] /*verilator public_flat_rw*/;
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial begin
        for (ii = 0; ii < (1 << VAW); ii = ii + 1) vm[ii] = 32'd0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir)) $readmemh({rom_dir, "/vm.hex"}, vm);
    end
    wire              x_re;
    wire [VAW-1:0]    x_addr;
    reg  [VRD*32-1:0] x_q;
    wire [R-1:0]      w_we;
    wire [R*VAW-1:0]  w_addr;
    wire [R*32-1:0]   w_data;
    integer k;
    always @(posedge clk) begin
        if (x_re) for (k = 0; k < VRD; k = k + 1) x_q[32*k +: 32] <= vm[x_addr + VAW'(k)];
        for (k = 0; k < R; k = k + 1) if (w_we[k]) vm[w_addr[VAW*k +: VAW]] <= w_data[32*k +: 32];
    end
    assign o_we = w_we; assign o_addr = w_addr; assign o_data = w_data;

    wire              c_go, c_gobf, c_cfg, c_xs_v, c_xb_v;
    wire [1:0]        c_tag;
    wire [PHW-1:0]    c_ph;
    wire [2:0]        c_np, c_xs_b, c_xs_pos, c_xb_pos, c_xb_b;
    wire [7:0]        c_xs_p;
    wire [1:0]        c_xs_sv;
    wire [255:0]      c_xs_q0, c_xs_q1;
    wire [9:0]        c_xs_e0, c_xs_e1;
    wire [3:0]        c_xb_sv;
    wire [31:0]       c_xb_u;
    wire [1023:0]     c_xb_d;
    wire [R-1:0]      r_v, r_e;
    wire [16*R-1:0]   r_row, r_bf16;
    wire [3*R-1:0]    r_pos;
    wire [32*R-1:0]   r_fp32;
    wire              f_fault;
    ot_v41_spine_pq_static_w17w10 #(.PHW(PHW), .SAW(SAW), .R(R), .VAW(VAW), .VRD(VRD), .KMAX(KMAX), .BST(BST), .PQ(PQ),
                             .GAP(GAP), .GUARD(GUARD), .GSLACK(GSLACK), .ADDR_LOOKAHEAD(ADDR_LOOKAHEAD), .STATIC_CONTROLS(STATIC_CONTROLS), .CONTROL_STAGE(CONTROL_STAGE)) u_sp (
        .clk(clk), .rst_n(rst_n), .go(go), .i_ph(i_ph), .i_np(i_np), .i_xbase(i_xbase), .i_xps(i_xps),
        .i_obase(i_obase), .i_ops(i_ops), .i_fmt(2'd0), .ready(ready), .idle(idle), .x_re(x_re), .x_addr(x_addr), .x_q(x_q),
        .w_we(w_we), .w_addr(w_addr), .w_data(w_data),
        .f_cfg_go(c_cfg), .f_cfg_ph(c_ph), .f_cfg_np(c_np), .f_go(c_go), .f_go_bf(c_gobf), .f_go_tag(c_tag), .f_xs_v(c_xs_v),
        .f_xs_p(c_xs_p), .f_xs_b(c_xs_b), .f_xs_sv(c_xs_sv), .f_xs_q0(c_xs_q0), .f_xs_e0(c_xs_e0),
        .f_xs_q1(c_xs_q1), .f_xs_e1(c_xs_e1), .f_xs_pos(c_xs_pos), .f_xb_pos(c_xb_pos), .f_xb_v(c_xb_v),
        .f_xb_b(c_xb_b), .f_xb_sv(c_xb_sv), .f_xb_u(c_xb_u), .f_xb_d(c_xb_d), .f_bus(),
        .r_v(r_v), .r_row(r_row), .r_pos(r_pos), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e),
        .f_fault(f_fault), .fault(fault), .phase_cycles(phase_cycles),
        .ev_go(ev_go), .ev_end(ev_end), .ev_tag(ev_tag));
`ifdef RT_CUT
    assign fb_cfg_go = c_cfg; assign fb_cfg_ph = c_ph; assign fb_cfg_np = c_np; assign fb_go = c_go;
    assign fb_go_tag = c_tag; assign fb_go_bf = c_gobf; assign fb_xs_v = c_xs_v; assign fb_xs_p = c_xs_p; assign fb_xs_b = c_xs_b;
    assign fb_xs_sv = c_xs_sv; assign fb_xs_q0 = c_xs_q0; assign fb_xs_e0 = c_xs_e0; assign fb_xs_q1 = c_xs_q1;
    assign fb_xs_e1 = c_xs_e1; assign fb_xs_pos = c_xs_pos; assign fb_xb_pos = c_xb_pos; assign fb_xb_v = c_xb_v;
    assign fb_xb_b = c_xb_b; assign fb_xb_sv = c_xb_sv; assign fb_xb_u = c_xb_u; assign fb_xb_d = c_xb_d;
    assign r_v = fr_v; assign r_row = fr_row; assign r_pos = fr_pos; assign r_fp32 = fr_fp32;
    assign r_bf16 = fr_bf16; assign r_e = fr_e; assign f_fault = fr_fault;
`else
    wire f_busy;
    ot_v41_field_pq_w17w10 #(.FAST(FAST), .PP(PP), .BP(BP), .NP(NP), .R(R), .NBF(NBF), .PHW(PHW), .RST(RST), .PQ(PQ)) u_f (
        .clk(clk), .rst_n(rst_n), .cfg_go(c_cfg), .cfg_ph(c_ph), .cfg_np(c_np), .go(c_go), .go_bf(c_gobf), .go_tag(c_tag),
        .xs_v(c_xs_v), .xs_p(c_xs_p), .xs_b(c_xs_b), .xs_sv(c_xs_sv), .xs_q0(c_xs_q0), .xs_e0(c_xs_e0),
        .xs_q1(c_xs_q1), .xs_e1(c_xs_e1), .xs_pos(c_xs_pos), .xb_pos(c_xb_pos), .xb_v(c_xb_v), .xb_b(c_xb_b),
        .xb_sv(c_xb_sv), .xb_u(c_xb_u), .xb_d(c_xb_d), .r_v(r_v), .r_row(r_row), .r_pos(r_pos),
        .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .busy(f_busy), .fault(f_fault));
`endif
endmodule
