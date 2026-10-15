`timescale 1ns/1ps
// Canonical compute-die SU -> central VM packing. No timing or storage here:
// both masters register these signals at their assigned native face pins.
// Operand descriptor o (A=0,B=1,C=2), at va[50*o +: 50]:
//   a0[23:0], a1[47:24], re0[48], re1[49].
// The write image and scalar reducer follow the three descriptors. This is
// shared by the real SU wrapper and the production central-VM composition.
module qfd_su_vm_pack (
    input wire [2:0] s_re0, s_re1,
    input wire [71:0] s_a0, s_a1,
    input wire [63:0] sw_mask,
    input wire [23:0] sw_a0, sw_a1,
    input wire [2047:0] sw_data,
    input wire red_we,
    input wire [23:0] red_addr,
    input wire [31:0] red_data,
    output wire [2366:0] va
);
    genvar o;
    generate for (o=0; o<3; o=o+1) begin: g_operand
        assign va[50*o +: 50] = {s_re1[o], s_re0[o], s_a1[24*o +: 24], s_a0[24*o +: 24]};
    end endgenerate
    assign va[2197:150] = sw_data;
    assign va[2221:2198] = sw_a0;
    assign va[2245:2222] = sw_a1;
    assign va[2309:2246] = sw_mask;
    assign va[2341:2310] = red_data;
    assign va[2365:2342] = red_addr;
    assign va[2366] = red_we;
endmodule
