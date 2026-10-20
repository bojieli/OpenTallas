`timescale 1ns/1ps
// Named opt-in LANDW native32 successors; original masters unchanged.
module qfd_landh0d8f_107_EW_44x44 (input wire ck_s, input wire en, input wire [106:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [106:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8_fan32 #(.W(107), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8fn_107_EW_44x44 (input wire ck_s, input wire en, input wire [106:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [106:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8_fan32 #(.W(107), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8f_116_EW_46x46 (input wire ck_s, input wire en, input wire [115:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [115:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8_fan32 #(.W(116), .ICG(1)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
module qfd_landh0d8fn_116_EW_46x46 (input wire ck_s, input wire en, input wire [115:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, output wire [115:0] b, output wire fault);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
    ot_qfd_land8_fan32 #(.W(116), .ICG(0)) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), .k({k3, k2, k1, k0}), .o(b), .fault(fault));
endmodule
