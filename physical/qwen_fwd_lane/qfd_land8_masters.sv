`timescale 1ns/1ps
// QW-LAND8 10-19: D8 hop-0 landing class masters (rtl/qwen_split/qfd_land8.sv ot_qfd_land8).  Written by
// tools/qwen_split/gen_land8_masters.py; ports = qfd_landh0 + the fourth K strap pin k3.
// qfd_landh0d8_*  : hop-0 ICG on ck_s with the REGISTERED enable (main);  qfd_landh0d8n_*: no clock gate (fallback).
module qfd_landh0d8_1_EW_16x16 (input wire ck_s, input wire en, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [0:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(1), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8n_1_EW_16x16 (input wire ck_s, input wire en, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [0:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(1), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8_3_EW_17x17 (input wire ck_s, input wire en, input wire [2:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [2:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(3), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8n_3_EW_17x17 (input wire ck_s, input wire en, input wire [2:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [2:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(3), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8_10_EW_19x19 (input wire ck_s, input wire en, input wire [9:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [9:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(10), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8n_10_EW_19x19 (input wire ck_s, input wire en, input wire [9:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [9:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(10), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8_32_EW_28x26 (input wire ck_s, input wire en, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [31:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(32), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8n_32_EW_28x26 (input wire ck_s, input wire en, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [31:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(32), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
