`timescale 1ns/1ps
// QW-LANDW 10-19: wide D8 hop-0 landing class masters.  Written by tools/qwen_split/gen_land8w_masters.py.
// qfd_landh0d8_* / d8n_*  : D8 flop ring (rtl/qwen_split/qfd_land8.sv ot_qfd_land8), ICG main / no-ICG fallback.
// qfd_landh0d8s_* / d8sn_*: D8 SRAM record slice (rtl/qwen_split/qfd_land8s.sv ot_qfd_land8s), ICG / no ICG.
// Ports = qfd_landh0d8 (ck_s en a ck rs k0..k3 tie_hi tie_lo b fault).
module qfd_landh0d8_107_EW_44x44 (input wire ck_s, input wire en, input wire [106:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [106:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(107), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8n_107_EW_44x44 (input wire ck_s, input wire en, input wire [106:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [106:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(107), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8_116_EW_46x46 (input wire ck_s, input wire en, input wire [115:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [115:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(116), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8n_116_EW_46x46 (input wire ck_s, input wire en, input wire [115:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [115:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8 #(.W(116), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8s_151_EW_98x171 (input wire ck_s, input wire en, input wire [150:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [150:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(151), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8sn_151_EW_98x171 (input wire ck_s, input wire en, input wire [150:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [150:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(151), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8s_173_EW_98x171 (input wire ck_s, input wire en, input wire [172:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [172:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(173), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8sn_173_EW_98x171 (input wire ck_s, input wire en, input wire [172:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [172:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(173), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8s_174_EW_98x171 (input wire ck_s, input wire en, input wire [173:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [173:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(174), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8sn_174_EW_98x171 (input wire ck_s, input wire en, input wire [173:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [173:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(174), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8s_182_EW_98x171 (input wire ck_s, input wire en, input wire [181:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [181:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(182), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8sn_182_EW_98x171 (input wire ck_s, input wire en, input wire [181:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [181:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(182), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8s_183_EW_98x171 (input wire ck_s, input wire en, input wire [182:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [182:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(183), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8sn_183_EW_98x171 (input wire ck_s, input wire en, input wire [182:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [182:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8s #(.W(183), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
