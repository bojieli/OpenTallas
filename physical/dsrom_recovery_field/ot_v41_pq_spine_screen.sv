`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_pq_spine_screen: physical-screen top of the PQ spine (DS-ROM recovery lever "field", 2026-10-04):
// ot_v41_spine_pq_w17w10 (built with OT_PQ_ROM_PORTS) with every port registered here, as its neighbours are in the
// die (vector-memory read port and write ports, region roots, the broadcast's first wire stage, the op issuer), and
// its phase and stream ROMs as register files read combinationally, as the spine reads them (written through a
// screen port so they are not constants; the die holds them in ROM macros).  The pinned quantisers inside the spine
// are a register-bounded stub (ot_hdc_actquant_screen_stub.sv): not new hardware, not screened here.
// ---------------------------------------------------------------------------
module ot_v41_pq_spine_screen #(
    parameter integer PHW = 6,
    parameter integer SAW = 8,
    parameter integer R = 16,
    parameter integer VAW = 19,
    parameter integer VRD = 64,
    parameter integer KMAX = 256,
    parameter integer BST = 2,
    parameter integer PQ = 1,
    parameter integer BW = 1 + PHW + 3 + 1 + 1 + 2 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024
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
    input  wire [1:0]        i_fmt,
    input  wire [VRD*32-1:0] x_q,
    input  wire [R-1:0]      r_v,
    input  wire [16*R-1:0]   r_row,
    input  wire [3*R-1:0]    r_pos,
    input  wire [32*R-1:0]   r_fp32,
    input  wire [16*R-1:0]   r_bf16,
    input  wire [R-1:0]      r_e,
    input  wire              f_fault,
    input  wire              rw_ph,
    input  wire              rw_st,
    input  wire [SAW-1:0]    rw_a,
    input  wire [63:0]       rw_d,
    output reg               o_ready,
    output reg               o_idle,
    output reg               o_x_re,
    output reg  [VAW-1:0]    o_x_addr,
    output reg  [R-1:0]      o_w_we,
    output reg  [R*VAW-1:0]  o_w_addr,
    output reg  [R*32-1:0]   o_w_data,
    output reg  [BW-1:0]     o_bus,
    output reg               o_fault,
    output reg               o_ev
);
    reg              q_go, q_ff;
    reg [PHW-1:0]    q_ph;
    reg [2:0]        q_np;
    reg [VAW-1:0]    q_xb, q_xps, q_ob, q_ops;
    reg [1:0]        q_fm;
    reg [VRD*32-1:0] q_x;
    reg [R-1:0]      q_rv, q_re;
    reg [16*R-1:0]   q_row, q_bf;
    reg [3*R-1:0]    q_pos;
    reg [32*R-1:0]   q_f32;
    always @(posedge clk) begin
        q_go <= go; q_ph <= i_ph; q_np <= i_np; q_xb <= i_xbase; q_xps <= i_xps; q_ob <= i_obase; q_ops <= i_ops;
        q_fm <= i_fmt; q_x <= x_q; q_rv <= r_v; q_row <= r_row; q_pos <= r_pos; q_f32 <= r_fp32; q_bf <= r_bf16;
        q_re <= r_e; q_ff <= f_fault;
    end
    reg [63:0] phrom [0:(2 << PHW)-1];
    reg [47:0] strom [0:(1 << SAW)-1];
    always @(posedge clk) begin
        if (rw_ph) phrom[rw_a[PHW:0]] <= rw_d;
        if (rw_st) strom[rw_a] <= rw_d[47:0];
    end
    wire [PHW:0] pa0, pa1;
    wire [SAW-1:0] sa;
    wire ready, idle, x_re, fault, ev_go, ev_end;
    wire [VAW-1:0] x_addr;
    wire [R-1:0] w_we;
    wire [R*VAW-1:0] w_addr;
    wire [R*32-1:0] w_data;
    wire [BW-1:0] bus;
    wire [1:0] ev_tag;
    ot_v41_spine_pq_w17w10 #(.PHW(PHW), .SAW(SAW), .R(R), .VAW(VAW), .VRD(VRD), .KMAX(KMAX), .BST(BST), .PQ(PQ)) u_sp (
        .clk(clk), .rst_n(rst_n), .go(q_go), .i_ph(q_ph), .i_np(q_np), .i_xbase(q_xb), .i_xps(q_xps),
        .i_obase(q_ob), .i_ops(q_ops), .i_fmt(q_fm), .ready(ready), .idle(idle), .x_re(x_re), .x_addr(x_addr),
        .x_q(q_x), .w_we(w_we), .w_addr(w_addr), .w_data(w_data),
        .f_cfg_go(), .f_cfg_ph(), .f_cfg_np(), .f_go(), .f_go_bf(), .f_go_tag(), .f_xs_v(), .f_xs_p(), .f_xs_b(),
        .f_xs_sv(), .f_xs_q0(), .f_xs_e0(), .f_xs_q1(), .f_xs_e1(), .f_xs_pos(), .f_xb_pos(), .f_xb_v(), .f_xb_b(),
        .f_xb_sv(), .f_xb_u(), .f_xb_d(), .f_bus(bus),
        .r_v(q_rv), .r_row(q_row), .r_pos(q_pos), .r_fp32(q_f32), .r_bf16(q_bf), .r_e(q_re), .f_fault(q_ff),
        .fault(fault), .phase_cycles(), .ev_go(ev_go), .ev_end(ev_end), .ev_tag(ev_tag),
        .rom_pa0(pa0), .rom_pa1(pa1), .rom_pq0(phrom[pa0]), .rom_pq1(phrom[pa1]), .rom_sa(sa), .rom_sq(strom[sa]));
    always @(posedge clk) begin
        o_ready <= ready; o_idle <= idle; o_x_re <= x_re; o_x_addr <= x_addr; o_w_we <= w_we; o_w_addr <= w_addr;
        o_w_data <= w_data; o_bus <= bus; o_fault <= fault; o_ev <= ev_go ^ ev_end ^ ^ev_tag;
    end
endmodule
