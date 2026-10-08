`timescale 1ns/1ps
// Additive production candidate; not selected by the current die generator.
// Native R128 PQ core and 128 ROOTD128 actual final reduction owners. Inputs
// are complete66-bit raw tree packets; no invented69-bit cast or hidden fields.
// ROM macro/VM/field transport remain explicit. See source-bound inventory and
// parent contract for clock, actual widths, finite occupancy and adoption gates.
module ot_s81_pq_parent_connector (
    input wire clk,
    input wire rst_n,
    input wire go,
    input wire [8:0] i_ph,
    input wire [2:0] i_np,
    input wire [18:0] i_xbase,
    input wire [18:0] i_xps,
    input wire [18:0] i_obase,
    input wire [18:0] i_ops,
    input wire [1:0] i_fmt,
    output wire ready,
    output wire idle,
    output wire x_re,
    output wire [18:0] x_addr,
    input wire [2047:0] x_q,
    output wire [127:0] w_we,
    output wire [2431:0] w_addr,
    output wire [4095:0] w_data,
    output wire [1632:0] f_bus,
    input wire f_fault,
    output wire fault,
    output wire [31:0] phase_cycles,
    output wire ev_go,
    output wire ev_end,
    output wire [1:0] ev_tag,
    output wire [9:0] rom_pa0,
    output wire [9:0] rom_pa1,
    input wire [63:0] rom_pq0,
    input wire [63:0] rom_pq1,
    output wire [10:0] rom_sa,
    input wire [47:0] rom_sq,
    input wire [8447:0] tree_return,
    input wire [127:0] upstream_fault,
    output wire [127:0] root_fault
);
    wire [127:0] r_v;
    wire [2047:0] r_row;
    wire [383:0] r_pos;
    wire [4095:0] r_fp32;
    wire [2047:0] r_bf16;
    wire [127:0] r_e;
    wire native_field_fault = f_fault | (|root_fault);
    ot_s81_pq_root_adapter #(.R(128),.ROOTD(128)) u_roots (
        .clk(clk),
        .rst_n(rst_n),
        .tree_return(tree_return),
        .upstream_fault(upstream_fault),
        .r_v(r_v),
        .r_row(r_row),
        .r_pos(r_pos),
        .r_fp32(r_fp32),
        .r_bf16(r_bf16),
        .r_e(r_e),
        .root_fault(root_fault)
    );
    ot_s81_pq_native_partition u_pqc (
        .clk(clk),
        .rst_n(rst_n),
        .go(go),
        .i_ph(i_ph),
        .i_np(i_np),
        .i_xbase(i_xbase),
        .i_xps(i_xps),
        .i_obase(i_obase),
        .i_ops(i_ops),
        .i_fmt(i_fmt),
        .ready(ready),
        .idle(idle),
        .x_re(x_re),
        .x_addr(x_addr),
        .x_q(x_q),
        .w_we(w_we),
        .w_addr(w_addr),
        .w_data(w_data),
        .r_v(r_v),
        .r_row(r_row),
        .r_pos(r_pos),
        .r_fp32(r_fp32),
        .r_bf16(r_bf16),
        .r_e(r_e),
        .f_bus(f_bus),
        .f_fault(native_field_fault),
        .fault(fault),
        .phase_cycles(phase_cycles),
        .ev_go(ev_go),
        .ev_end(ev_end),
        .ev_tag(ev_tag),
        .rom_pa0(rom_pa0),
        .rom_pa1(rom_pa1),
        .rom_pq0(rom_pq0),
        .rom_pq1(rom_pq1),
        .rom_sa(rom_sa),
        .rom_sq(rom_sq)
    );
endmodule
