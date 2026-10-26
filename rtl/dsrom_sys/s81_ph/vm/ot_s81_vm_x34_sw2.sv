`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_vm_x34_sw2 (S-VM-X34 2026-10-16): the 1026-b serial -> stream 3:4 fixed-epoch transfer of aSW (VM parent u_xsw)
// as TWO ot_s81_vm_x34 #(.W(514)) halves h0 / h1 -- the closed native-PASS W514 s/t masters already used by u_xsel /
// u_xcol (ot_s81_vm_x34_s_w514_1015_f4 / ot_s81_vm_x34_t_w514_1015_f4).  The W1026 serial master failed the strict
// native launch audit on both closed views (n1 234.5 / n3 233.9 ps > 220); the split removes that tile variant.
//   * half k carries data bits s_d[513k+512 : 513k] in its s_d[512:0] plus the same s_v; its s_d[513] is a
//     QUANTIZATION PAD (constant 0 in, o_d[513] unused): 1026 data bits = 2 x 513 on the 514-wide master.  Not a
//     functional tie: no function is removed, the bit carries no information in either form.
//   * both halves hang off the same s / t clock and reset roots as the W1026 instance (die ABI unchanged);
//   * o_v from h0 (h1's o_v is the same flop function of the same s_v / clocks / resets; simulation check below);
//   * fault = OR of both halves' sticky epoch-parity / phase-marker faults (each tile asserts its own alignment).
// Zero cycles: every o_v / o_d / fault edge is that of ot_s81_vm_x34 #(.W(1026)) (tb_ot_s81_vm_x34_sw2_diff).
// Static fixed-cycle: no handshake, no credit, no ready.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_vm_x34_sw2 (
    input  wire          s_ck, s_rst_n,
    input  wire          s_v, input wire [1025:0] s_d,
    input  wire          t_ck, t_rst_n,
    output wire          o_v, output wire [1025:0] o_d,
    output wire          fault,
    output wire [1:0]    fault_parts
);
    wire [1:0] hv, hf; wire [513:0] d0, d1;
`ifdef OT_VM_X34SPLIT_MUT_SWAP
    wire [513:0] i0 = {1'b0, s_d[1025:513]}, i1 = {1'b0, s_d[512:0]};          // MUTANT: halves swapped
`elsif OT_VM_X34SPLIT_MUT_DROP
    wire [513:0] i0 = {1'b0, s_d[512:0]}, i1 = {1'b0, s_d[1025:514], 1'b0};    // MUTANT: data bit 513 dropped
`else
    wire [513:0] i0 = {1'b0, s_d[512:0]}, i1 = {1'b0, s_d[1025:513]};
`endif
    ot_s81_vm_x34 #(.W(514)) h0 (.s_ck(s_ck), .s_rst_n(s_rst_n), .s_v(s_v), .s_d(i0),
        .t_ck(t_ck), .t_rst_n(t_rst_n), .o_v(hv[0]), .o_d(d0), .fault(hf[0]));
    ot_s81_vm_x34 #(.W(514)) h1 (.s_ck(s_ck), .s_rst_n(s_rst_n), .s_v(s_v), .s_d(i1),
        .t_ck(t_ck), .t_rst_n(t_rst_n), .o_v(hv[1]), .o_d(d1), .fault(hf[1]));
    assign o_v = hv[0];
    assign o_d = {d1[512:0], d0[512:0]};
    assign fault = |hf;
    assign fault_parts = hf;
`ifndef SYNTHESIS
    always @(posedge t_ck)
        if (hv[1] !== hv[0]) $error("X34SW2 o_v half mismatch h0=%b h1=%b", hv[0], hv[1]);
`endif
endmodule
`default_nettype wire
