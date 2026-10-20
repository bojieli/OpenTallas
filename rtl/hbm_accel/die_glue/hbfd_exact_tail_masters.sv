`timescale 1ns/1ps
`default_nettype none
module hbfd_land0_136_NS_tail5 (input wire ck_s, input wire en, input wire [4:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [4:0] b, output wire fault);
    ot_qfd_land #(.W(5), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_136_NS_tail12 (input wire ck_s, input wire en, input wire [11:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [11:0] b, output wire fault);
    ot_qfd_land #(.W(12), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_136_NS_tail110 (input wire ck_s, input wire en, input wire [109:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [109:0] b, output wire fault);
    ot_qfd_land #(.W(110), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_136_SN_tail5 (input wire ck_s, input wire en, input wire [4:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [4:0] b, output wire fault);
    ot_qfd_land #(.W(5), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_136_SN_tail12 (input wire ck_s, input wire en, input wire [11:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [11:0] b, output wire fault);
    ot_qfd_land #(.W(12), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_136_SN_tail110 (input wire ck_s, input wire en, input wire [109:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [109:0] b, output wire fault);
    ot_qfd_land #(.W(110), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_136_WE_tail1 (input wire ck_s, input wire en, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_48_NS_tail9 (input wire ck_s, input wire en, input wire [8:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [8:0] b, output wire fault);
    ot_qfd_land #(.W(9), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail1 (input wire ckf, input wire ea, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail2 (input wire ckf, input wire ea, input wire [1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [1:0] b, output wire fault);
    ot_qfd_land #(.W(2), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail5 (input wire ckf, input wire ea, input wire [4:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [4:0] b, output wire fault);
    ot_qfd_land #(.W(5), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail7 (input wire ckf, input wire ea, input wire [6:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [6:0] b, output wire fault);
    ot_qfd_land #(.W(7), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail8 (input wire ckf, input wire ea, input wire [7:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [7:0] b, output wire fault);
    ot_qfd_land #(.W(8), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail11 (input wire ckf, input wire ea, input wire [10:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [10:0] b, output wire fault);
    ot_qfd_land #(.W(11), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail12 (input wire ckf, input wire ea, input wire [11:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [11:0] b, output wire fault);
    ot_qfd_land #(.W(12), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail32 (input wire ckf, input wire ea, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [31:0] b, output wire fault);
    ot_qfd_land #(.W(32), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail37 (input wire ckf, input wire ea, input wire [36:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [36:0] b, output wire fault);
    ot_qfd_land #(.W(37), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail41 (input wire ckf, input wire ea, input wire [40:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [40:0] b, output wire fault);
    ot_qfd_land #(.W(41), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail43 (input wire ckf, input wire ea, input wire [42:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [42:0] b, output wire fault);
    ot_qfd_land #(.W(43), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail48 (input wire ckf, input wire ea, input wire [47:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [47:0] b, output wire fault);
    ot_qfd_land #(.W(48), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail66 (input wire ckf, input wire ea, input wire [65:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [65:0] b, output wire fault);
    ot_qfd_land #(.W(66), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail79 (input wire ckf, input wire ea, input wire [78:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [78:0] b, output wire fault);
    ot_qfd_land #(.W(79), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail108 (input wire ckf, input wire ea, input wire [107:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [107:0] b, output wire fault);
    ot_qfd_land #(.W(108), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail110 (input wire ckf, input wire ea, input wire [109:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [109:0] b, output wire fault);
    ot_qfd_land #(.W(110), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tail130 (input wire ckf, input wire ea, input wire [129:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [129:0] b, output wire fault);
    ot_qfd_land #(.W(130), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail1 (input wire ckf, input wire ea, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail2 (input wire ckf, input wire ea, input wire [1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [1:0] b, output wire fault);
    ot_qfd_land #(.W(2), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail3 (input wire ckf, input wire ea, input wire [2:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [2:0] b, output wire fault);
    ot_qfd_land #(.W(3), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail5 (input wire ckf, input wire ea, input wire [4:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [4:0] b, output wire fault);
    ot_qfd_land #(.W(5), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail7 (input wire ckf, input wire ea, input wire [6:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [6:0] b, output wire fault);
    ot_qfd_land #(.W(7), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail8 (input wire ckf, input wire ea, input wire [7:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [7:0] b, output wire fault);
    ot_qfd_land #(.W(8), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail11 (input wire ckf, input wire ea, input wire [10:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [10:0] b, output wire fault);
    ot_qfd_land #(.W(11), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail12 (input wire ckf, input wire ea, input wire [11:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [11:0] b, output wire fault);
    ot_qfd_land #(.W(12), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail32 (input wire ckf, input wire ea, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [31:0] b, output wire fault);
    ot_qfd_land #(.W(32), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail37 (input wire ckf, input wire ea, input wire [36:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [36:0] b, output wire fault);
    ot_qfd_land #(.W(37), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail41 (input wire ckf, input wire ea, input wire [40:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [40:0] b, output wire fault);
    ot_qfd_land #(.W(41), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail43 (input wire ckf, input wire ea, input wire [42:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [42:0] b, output wire fault);
    ot_qfd_land #(.W(43), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail48 (input wire ckf, input wire ea, input wire [47:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [47:0] b, output wire fault);
    ot_qfd_land #(.W(48), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail66 (input wire ckf, input wire ea, input wire [65:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [65:0] b, output wire fault);
    ot_qfd_land #(.W(66), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail108 (input wire ckf, input wire ea, input wire [107:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [107:0] b, output wire fault);
    ot_qfd_land #(.W(108), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail110 (input wire ckf, input wire ea, input wire [109:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [109:0] b, output wire fault);
    ot_qfd_land #(.W(110), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tail130 (input wire ckf, input wire ea, input wire [129:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [129:0] b, output wire fault);
    ot_qfd_land #(.W(130), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail1 (input wire ckf, input wire ea, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail2 (input wire ckf, input wire ea, input wire [1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [1:0] b, output wire fault);
    ot_qfd_land #(.W(2), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail5 (input wire ckf, input wire ea, input wire [4:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [4:0] b, output wire fault);
    ot_qfd_land #(.W(5), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail7 (input wire ckf, input wire ea, input wire [6:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [6:0] b, output wire fault);
    ot_qfd_land #(.W(7), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail8 (input wire ckf, input wire ea, input wire [7:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [7:0] b, output wire fault);
    ot_qfd_land #(.W(8), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail11 (input wire ckf, input wire ea, input wire [10:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [10:0] b, output wire fault);
    ot_qfd_land #(.W(11), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail12 (input wire ckf, input wire ea, input wire [11:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [11:0] b, output wire fault);
    ot_qfd_land #(.W(12), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail37 (input wire ckf, input wire ea, input wire [36:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [36:0] b, output wire fault);
    ot_qfd_land #(.W(37), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail41 (input wire ckf, input wire ea, input wire [40:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [40:0] b, output wire fault);
    ot_qfd_land #(.W(41), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail43 (input wire ckf, input wire ea, input wire [42:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [42:0] b, output wire fault);
    ot_qfd_land #(.W(43), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail48 (input wire ckf, input wire ea, input wire [47:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [47:0] b, output wire fault);
    ot_qfd_land #(.W(48), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail108 (input wire ckf, input wire ea, input wire [107:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [107:0] b, output wire fault);
    ot_qfd_land #(.W(108), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail110 (input wire ckf, input wire ea, input wire [109:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [109:0] b, output wire fault);
    ot_qfd_land #(.W(110), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tail130 (input wire ckf, input wire ea, input wire [129:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [129:0] b, output wire fault);
    ot_qfd_land #(.W(130), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail1 (input wire ckf, input wire ea, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail2 (input wire ckf, input wire ea, input wire [1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [1:0] b, output wire fault);
    ot_qfd_land #(.W(2), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail5 (input wire ckf, input wire ea, input wire [4:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [4:0] b, output wire fault);
    ot_qfd_land #(.W(5), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail7 (input wire ckf, input wire ea, input wire [6:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [6:0] b, output wire fault);
    ot_qfd_land #(.W(7), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail8 (input wire ckf, input wire ea, input wire [7:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [7:0] b, output wire fault);
    ot_qfd_land #(.W(8), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail11 (input wire ckf, input wire ea, input wire [10:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [10:0] b, output wire fault);
    ot_qfd_land #(.W(11), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail12 (input wire ckf, input wire ea, input wire [11:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [11:0] b, output wire fault);
    ot_qfd_land #(.W(12), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail32 (input wire ckf, input wire ea, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [31:0] b, output wire fault);
    ot_qfd_land #(.W(32), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail37 (input wire ckf, input wire ea, input wire [36:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [36:0] b, output wire fault);
    ot_qfd_land #(.W(37), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail41 (input wire ckf, input wire ea, input wire [40:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [40:0] b, output wire fault);
    ot_qfd_land #(.W(41), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail43 (input wire ckf, input wire ea, input wire [42:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [42:0] b, output wire fault);
    ot_qfd_land #(.W(43), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail48 (input wire ckf, input wire ea, input wire [47:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [47:0] b, output wire fault);
    ot_qfd_land #(.W(48), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail79 (input wire ckf, input wire ea, input wire [78:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [78:0] b, output wire fault);
    ot_qfd_land #(.W(79), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tail110 (input wire ckf, input wire ea, input wire [109:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [109:0] b, output wire fault);
    ot_qfd_land #(.W(110), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail1 (input wire ckf, input wire ea, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail3 (input wire ckf, input wire ea, input wire [2:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [2:0] b, output wire fault);
    ot_qfd_land #(.W(3), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail4 (input wire ckf, input wire ea, input wire [3:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [3:0] b, output wire fault);
    ot_qfd_land #(.W(4), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail5 (input wire ckf, input wire ea, input wire [4:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [4:0] b, output wire fault);
    ot_qfd_land #(.W(5), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail7 (input wire ckf, input wire ea, input wire [6:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [6:0] b, output wire fault);
    ot_qfd_land #(.W(7), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail8 (input wire ckf, input wire ea, input wire [7:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [7:0] b, output wire fault);
    ot_qfd_land #(.W(8), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail17 (input wire ckf, input wire ea, input wire [16:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [16:0] b, output wire fault);
    ot_qfd_land #(.W(17), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail19 (input wire ckf, input wire ea, input wire [18:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [18:0] b, output wire fault);
    ot_qfd_land #(.W(19), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail21 (input wire ckf, input wire ea, input wire [20:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [20:0] b, output wire fault);
    ot_qfd_land #(.W(21), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail32 (input wire ckf, input wire ea, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [31:0] b, output wire fault);
    ot_qfd_land #(.W(32), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tail41 (input wire ckf, input wire ea, input wire [40:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [40:0] b, output wire fault);
    ot_qfd_land #(.W(41), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail1 (input wire ckf, input wire ea, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail2 (input wire ckf, input wire ea, input wire [1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [1:0] b, output wire fault);
    ot_qfd_land #(.W(2), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail3 (input wire ckf, input wire ea, input wire [2:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [2:0] b, output wire fault);
    ot_qfd_land #(.W(3), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail4 (input wire ckf, input wire ea, input wire [3:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [3:0] b, output wire fault);
    ot_qfd_land #(.W(4), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail5 (input wire ckf, input wire ea, input wire [4:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [4:0] b, output wire fault);
    ot_qfd_land #(.W(5), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail8 (input wire ckf, input wire ea, input wire [7:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [7:0] b, output wire fault);
    ot_qfd_land #(.W(8), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail9 (input wire ckf, input wire ea, input wire [8:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [8:0] b, output wire fault);
    ot_qfd_land #(.W(9), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail13 (input wire ckf, input wire ea, input wire [12:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [12:0] b, output wire fault);
    ot_qfd_land #(.W(13), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail16 (input wire ckf, input wire ea, input wire [15:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [15:0] b, output wire fault);
    ot_qfd_land #(.W(16), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail17 (input wire ckf, input wire ea, input wire [16:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [16:0] b, output wire fault);
    ot_qfd_land #(.W(17), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail19 (input wire ckf, input wire ea, input wire [18:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [18:0] b, output wire fault);
    ot_qfd_land #(.W(19), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail21 (input wire ckf, input wire ea, input wire [20:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [20:0] b, output wire fault);
    ot_qfd_land #(.W(21), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail28 (input wire ckf, input wire ea, input wire [27:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [27:0] b, output wire fault);
    ot_qfd_land #(.W(28), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tail32 (input wire ckf, input wire ea, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [31:0] b, output wire fault);
    ot_qfd_land #(.W(32), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail1 (input wire ckf, input wire ea, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail2 (input wire ckf, input wire ea, input wire [1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [1:0] b, output wire fault);
    ot_qfd_land #(.W(2), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail3 (input wire ckf, input wire ea, input wire [2:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [2:0] b, output wire fault);
    ot_qfd_land #(.W(3), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail4 (input wire ckf, input wire ea, input wire [3:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [3:0] b, output wire fault);
    ot_qfd_land #(.W(4), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail9 (input wire ckf, input wire ea, input wire [8:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [8:0] b, output wire fault);
    ot_qfd_land #(.W(9), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail13 (input wire ckf, input wire ea, input wire [12:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [12:0] b, output wire fault);
    ot_qfd_land #(.W(13), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail17 (input wire ckf, input wire ea, input wire [16:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [16:0] b, output wire fault);
    ot_qfd_land #(.W(17), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail19 (input wire ckf, input wire ea, input wire [18:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [18:0] b, output wire fault);
    ot_qfd_land #(.W(19), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail21 (input wire ckf, input wire ea, input wire [20:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [20:0] b, output wire fault);
    ot_qfd_land #(.W(21), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail32 (input wire ckf, input wire ea, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [31:0] b, output wire fault);
    ot_qfd_land #(.W(32), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail41 (input wire ckf, input wire ea, input wire [40:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [40:0] b, output wire fault);
    ot_qfd_land #(.W(41), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tail43 (input wire ckf, input wire ea, input wire [42:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [42:0] b, output wire fault);
    ot_qfd_land #(.W(43), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail1 (input wire ckf, input wire ea, input wire [0:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [0:0] b, output wire fault);
    ot_qfd_land #(.W(1), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail2 (input wire ckf, input wire ea, input wire [1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [1:0] b, output wire fault);
    ot_qfd_land #(.W(2), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail3 (input wire ckf, input wire ea, input wire [2:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [2:0] b, output wire fault);
    ot_qfd_land #(.W(3), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail4 (input wire ckf, input wire ea, input wire [3:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [3:0] b, output wire fault);
    ot_qfd_land #(.W(4), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail7 (input wire ckf, input wire ea, input wire [6:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [6:0] b, output wire fault);
    ot_qfd_land #(.W(7), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail8 (input wire ckf, input wire ea, input wire [7:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [7:0] b, output wire fault);
    ot_qfd_land #(.W(8), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail9 (input wire ckf, input wire ea, input wire [8:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [8:0] b, output wire fault);
    ot_qfd_land #(.W(9), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail17 (input wire ckf, input wire ea, input wire [16:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [16:0] b, output wire fault);
    ot_qfd_land #(.W(17), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail19 (input wire ckf, input wire ea, input wire [18:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [18:0] b, output wire fault);
    ot_qfd_land #(.W(19), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tail32 (input wire ckf, input wire ea, input wire [31:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [31:0] b, output wire fault);
    ot_qfd_land #(.W(32), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail72 (input wire ckf, input wire ea, input wire [71:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [71:0] b, output wire fault);
    ot_qfd_land #(.W(72), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail76 (input wire ckf, input wire ea, input wire [75:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [75:0] b, output wire fault);
    ot_qfd_land #(.W(76), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail116 (input wire ckf, input wire ea, input wire [115:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [115:0] b, output wire fault);
    ot_qfd_land #(.W(116), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail136 (input wire ckf, input wire ea, input wire [135:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [135:0] b, output wire fault);
    ot_qfd_land #(.W(136), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail138 (input wire ckf, input wire ea, input wire [137:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [137:0] b, output wire fault);
    ot_qfd_land #(.W(138), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail171 (input wire ckf, input wire ea, input wire [170:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [170:0] b, output wire fault);
    ot_qfd_land #(.W(171), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail213 (input wire ckf, input wire ea, input wire [212:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [212:0] b, output wire fault);
    ot_qfd_land #(.W(213), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail257 (input wire ckf, input wire ea, input wire [256:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [256:0] b, output wire fault);
    ot_qfd_land #(.W(257), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail273 (input wire ckf, input wire ea, input wire [272:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [272:0] b, output wire fault);
    ot_qfd_land #(.W(273), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail280 (input wire ckf, input wire ea, input wire [279:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [279:0] b, output wire fault);
    ot_qfd_land #(.W(280), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail281 (input wire ckf, input wire ea, input wire [280:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [280:0] b, output wire fault);
    ot_qfd_land #(.W(281), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail296 (input wire ckf, input wire ea, input wire [295:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [295:0] b, output wire fault);
    ot_qfd_land #(.W(296), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail338 (input wire ckf, input wire ea, input wire [337:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [337:0] b, output wire fault);
    ot_qfd_land #(.W(338), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail352 (input wire ckf, input wire ea, input wire [351:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [351:0] b, output wire fault);
    ot_qfd_land #(.W(352), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail512 (input wire ckf, input wire ea, input wire [511:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [511:0] b, output wire fault);
    ot_qfd_land #(.W(512), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail516 (input wire ckf, input wire ea, input wire [515:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [515:0] b, output wire fault);
    ot_qfd_land #(.W(516), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail524 (input wire ckf, input wire ea, input wire [523:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [523:0] b, output wire fault);
    ot_qfd_land #(.W(524), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail562 (input wire ckf, input wire ea, input wire [561:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [561:0] b, output wire fault);
    ot_qfd_land #(.W(562), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail572 (input wire ckf, input wire ea, input wire [571:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [571:0] b, output wire fault);
    ot_qfd_land #(.W(572), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail596 (input wire ckf, input wire ea, input wire [595:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [595:0] b, output wire fault);
    ot_qfd_land #(.W(596), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tail613 (input wire ckf, input wire ea, input wire [612:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [612:0] b, output wire fault);
    ot_qfd_land #(.W(613), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail83 (input wire ckf, input wire ea, input wire [82:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [82:0] b, output wire fault);
    ot_qfd_land #(.W(83), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail136 (input wire ckf, input wire ea, input wire [135:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [135:0] b, output wire fault);
    ot_qfd_land #(.W(136), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail138 (input wire ckf, input wire ea, input wire [137:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [137:0] b, output wire fault);
    ot_qfd_land #(.W(138), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail173 (input wire ckf, input wire ea, input wire [172:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [172:0] b, output wire fault);
    ot_qfd_land #(.W(173), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail184 (input wire ckf, input wire ea, input wire [183:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [183:0] b, output wire fault);
    ot_qfd_land #(.W(184), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail213 (input wire ckf, input wire ea, input wire [212:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [212:0] b, output wire fault);
    ot_qfd_land #(.W(213), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail257 (input wire ckf, input wire ea, input wire [256:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [256:0] b, output wire fault);
    ot_qfd_land #(.W(257), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail271 (input wire ckf, input wire ea, input wire [270:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [270:0] b, output wire fault);
    ot_qfd_land #(.W(271), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail280 (input wire ckf, input wire ea, input wire [279:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [279:0] b, output wire fault);
    ot_qfd_land #(.W(280), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail281 (input wire ckf, input wire ea, input wire [280:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [280:0] b, output wire fault);
    ot_qfd_land #(.W(281), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail296 (input wire ckf, input wire ea, input wire [295:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [295:0] b, output wire fault);
    ot_qfd_land #(.W(296), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail297 (input wire ckf, input wire ea, input wire [296:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [296:0] b, output wire fault);
    ot_qfd_land #(.W(297), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail314 (input wire ckf, input wire ea, input wire [313:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [313:0] b, output wire fault);
    ot_qfd_land #(.W(314), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail352 (input wire ckf, input wire ea, input wire [351:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [351:0] b, output wire fault);
    ot_qfd_land #(.W(352), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail376 (input wire ckf, input wire ea, input wire [375:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [375:0] b, output wire fault);
    ot_qfd_land #(.W(376), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail512 (input wire ckf, input wire ea, input wire [511:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [511:0] b, output wire fault);
    ot_qfd_land #(.W(512), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail516 (input wire ckf, input wire ea, input wire [515:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [515:0] b, output wire fault);
    ot_qfd_land #(.W(516), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail520 (input wire ckf, input wire ea, input wire [519:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [519:0] b, output wire fault);
    ot_qfd_land #(.W(520), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail562 (input wire ckf, input wire ea, input wire [561:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [561:0] b, output wire fault);
    ot_qfd_land #(.W(562), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail586 (input wire ckf, input wire ea, input wire [585:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [585:0] b, output wire fault);
    ot_qfd_land #(.W(586), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail613 (input wire ckf, input wire ea, input wire [612:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [612:0] b, output wire fault);
    ot_qfd_land #(.W(613), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tail614 (input wire ckf, input wire ea, input wire [613:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [613:0] b, output wire fault);
    ot_qfd_land #(.W(614), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail65 (input wire ckf, input wire ea, input wire [64:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [64:0] b, output wire fault);
    ot_qfd_land #(.W(65), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail76 (input wire ckf, input wire ea, input wire [75:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [75:0] b, output wire fault);
    ot_qfd_land #(.W(76), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail83 (input wire ckf, input wire ea, input wire [82:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [82:0] b, output wire fault);
    ot_qfd_land #(.W(83), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail136 (input wire ckf, input wire ea, input wire [135:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [135:0] b, output wire fault);
    ot_qfd_land #(.W(136), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail138 (input wire ckf, input wire ea, input wire [137:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [137:0] b, output wire fault);
    ot_qfd_land #(.W(138), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail173 (input wire ckf, input wire ea, input wire [172:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [172:0] b, output wire fault);
    ot_qfd_land #(.W(173), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail213 (input wire ckf, input wire ea, input wire [212:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [212:0] b, output wire fault);
    ot_qfd_land #(.W(213), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail257 (input wire ckf, input wire ea, input wire [256:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [256:0] b, output wire fault);
    ot_qfd_land #(.W(257), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail271 (input wire ckf, input wire ea, input wire [270:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [270:0] b, output wire fault);
    ot_qfd_land #(.W(271), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail274 (input wire ckf, input wire ea, input wire [273:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [273:0] b, output wire fault);
    ot_qfd_land #(.W(274), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail280 (input wire ckf, input wire ea, input wire [279:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [279:0] b, output wire fault);
    ot_qfd_land #(.W(280), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail281 (input wire ckf, input wire ea, input wire [280:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [280:0] b, output wire fault);
    ot_qfd_land #(.W(281), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail297 (input wire ckf, input wire ea, input wire [296:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [296:0] b, output wire fault);
    ot_qfd_land #(.W(297), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail319 (input wire ckf, input wire ea, input wire [318:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [318:0] b, output wire fault);
    ot_qfd_land #(.W(319), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail516 (input wire ckf, input wire ea, input wire [515:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [515:0] b, output wire fault);
    ot_qfd_land #(.W(516), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail520 (input wire ckf, input wire ea, input wire [519:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [519:0] b, output wire fault);
    ot_qfd_land #(.W(520), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail524 (input wire ckf, input wire ea, input wire [523:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [523:0] b, output wire fault);
    ot_qfd_land #(.W(524), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail562 (input wire ckf, input wire ea, input wire [561:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [561:0] b, output wire fault);
    ot_qfd_land #(.W(562), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail594 (input wire ckf, input wire ea, input wire [593:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [593:0] b, output wire fault);
    ot_qfd_land #(.W(594), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail596 (input wire ckf, input wire ea, input wire [595:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [595:0] b, output wire fault);
    ot_qfd_land #(.W(596), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tail614 (input wire ckf, input wire ea, input wire [613:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [613:0] b, output wire fault);
    ot_qfd_land #(.W(614), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail61 (input wire ckf, input wire ea, input wire [60:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [60:0] b, output wire fault);
    ot_qfd_land #(.W(61), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail67 (input wire ckf, input wire ea, input wire [66:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [66:0] b, output wire fault);
    ot_qfd_land #(.W(67), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail76 (input wire ckf, input wire ea, input wire [75:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [75:0] b, output wire fault);
    ot_qfd_land #(.W(76), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail116 (input wire ckf, input wire ea, input wire [115:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [115:0] b, output wire fault);
    ot_qfd_land #(.W(116), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail136 (input wire ckf, input wire ea, input wire [135:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [135:0] b, output wire fault);
    ot_qfd_land #(.W(136), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail138 (input wire ckf, input wire ea, input wire [137:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [137:0] b, output wire fault);
    ot_qfd_land #(.W(138), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail171 (input wire ckf, input wire ea, input wire [170:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [170:0] b, output wire fault);
    ot_qfd_land #(.W(171), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail173 (input wire ckf, input wire ea, input wire [172:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [172:0] b, output wire fault);
    ot_qfd_land #(.W(173), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail184 (input wire ckf, input wire ea, input wire [183:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [183:0] b, output wire fault);
    ot_qfd_land #(.W(184), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail206 (input wire ckf, input wire ea, input wire [205:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [205:0] b, output wire fault);
    ot_qfd_land #(.W(206), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail207 (input wire ckf, input wire ea, input wire [206:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [206:0] b, output wire fault);
    ot_qfd_land #(.W(207), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail213 (input wire ckf, input wire ea, input wire [212:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [212:0] b, output wire fault);
    ot_qfd_land #(.W(213), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail257 (input wire ckf, input wire ea, input wire [256:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [256:0] b, output wire fault);
    ot_qfd_land #(.W(257), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail280 (input wire ckf, input wire ea, input wire [279:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [279:0] b, output wire fault);
    ot_qfd_land #(.W(280), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail281 (input wire ckf, input wire ea, input wire [280:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [280:0] b, output wire fault);
    ot_qfd_land #(.W(281), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail297 (input wire ckf, input wire ea, input wire [296:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [296:0] b, output wire fault);
    ot_qfd_land #(.W(297), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail319 (input wire ckf, input wire ea, input wire [318:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [318:0] b, output wire fault);
    ot_qfd_land #(.W(319), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail352 (input wire ckf, input wire ea, input wire [351:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [351:0] b, output wire fault);
    ot_qfd_land #(.W(352), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail376 (input wire ckf, input wire ea, input wire [375:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [375:0] b, output wire fault);
    ot_qfd_land #(.W(376), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail469 (input wire ckf, input wire ea, input wire [468:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [468:0] b, output wire fault);
    ot_qfd_land #(.W(469), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail524 (input wire ckf, input wire ea, input wire [523:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [523:0] b, output wire fault);
    ot_qfd_land #(.W(524), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail562 (input wire ckf, input wire ea, input wire [561:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [561:0] b, output wire fault);
    ot_qfd_land #(.W(562), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail596 (input wire ckf, input wire ea, input wire [595:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [595:0] b, output wire fault);
    ot_qfd_land #(.W(596), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail613 (input wire ckf, input wire ea, input wire [612:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [612:0] b, output wire fault);
    ot_qfd_land #(.W(613), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tail614 (input wire ckf, input wire ea, input wire [613:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [613:0] b, output wire fault);
    ot_qfd_land #(.W(614), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_lh0_136_EW_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(1), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_tail2 (input wire ck, input wire en, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(2), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_tail3 (input wire ck, input wire en, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(3), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_tail8 (input wire ck, input wire en, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(8), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_tail11 (input wire ck, input wire en, input wire [10:0] a, output wire [10:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(11), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_tail12 (input wire ck, input wire en, input wire [11:0] a, output wire [11:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(12), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_tail37 (input wire ck, input wire en, input wire [36:0] a, output wire [36:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(37), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_tail66 (input wire ck, input wire en, input wire [65:0] a, output wire [65:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(66), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_tail110 (input wire ck, input wire en, input wire [109:0] a, output wire [109:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(110), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_f2_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(1), .N(2), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_f3_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [2:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(1), .N(3), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(1), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail2 (input wire ck, input wire en, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(2), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail5 (input wire ck, input wire en, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(5), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail7 (input wire ck, input wire en, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(7), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail8 (input wire ck, input wire en, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(8), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail12 (input wire ck, input wire en, input wire [11:0] a, output wire [11:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(12), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail32 (input wire ck, input wire en, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(32), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail37 (input wire ck, input wire en, input wire [36:0] a, output wire [36:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(37), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail41 (input wire ck, input wire en, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(41), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail43 (input wire ck, input wire en, input wire [42:0] a, output wire [42:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(43), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail48 (input wire ck, input wire en, input wire [47:0] a, output wire [47:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(48), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail79 (input wire ck, input wire en, input wire [78:0] a, output wire [78:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(79), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail108 (input wire ck, input wire en, input wire [107:0] a, output wire [107:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(108), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail110 (input wire ck, input wire en, input wire [109:0] a, output wire [109:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(110), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tail130 (input wire ck, input wire en, input wire [129:0] a, output wire [129:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(130), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_f3_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [2:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(1), .N(3), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_f3_tail7 (input wire ck, input wire en, input wire [6:0] a, output wire [20:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(7), .N(3), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_f3_tail41 (input wire ck, input wire en, input wire [40:0] a, output wire [122:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(41), .N(3), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(1), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail2 (input wire ck, input wire en, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(2), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail5 (input wire ck, input wire en, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(5), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail7 (input wire ck, input wire en, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(7), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail8 (input wire ck, input wire en, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(8), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail12 (input wire ck, input wire en, input wire [11:0] a, output wire [11:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(12), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail37 (input wire ck, input wire en, input wire [36:0] a, output wire [36:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(37), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail41 (input wire ck, input wire en, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(41), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail43 (input wire ck, input wire en, input wire [42:0] a, output wire [42:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(43), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail48 (input wire ck, input wire en, input wire [47:0] a, output wire [47:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(48), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail79 (input wire ck, input wire en, input wire [78:0] a, output wire [78:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(79), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail108 (input wire ck, input wire en, input wire [107:0] a, output wire [107:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(108), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tail130 (input wire ck, input wire en, input wire [129:0] a, output wire [129:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(130), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_f3_tail11 (input wire ck, input wire en, input wire [10:0] a, output wire [32:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(11), .N(3), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_WE_tail8 (input wire ck, input wire en, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(8), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_WE_tail11 (input wire ck, input wire en, input wire [10:0] a, output wire [10:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(11), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_WE_tail12 (input wire ck, input wire en, input wire [11:0] a, output wire [11:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(12), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_WE_tail32 (input wire ck, input wire en, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(32), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_WE_tail37 (input wire ck, input wire en, input wire [36:0] a, output wire [36:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(37), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_WE_tail110 (input wire ck, input wire en, input wire [109:0] a, output wire [109:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(110), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(1), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail2 (input wire ck, input wire en, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(2), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail3 (input wire ck, input wire en, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(3), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail4 (input wire ck, input wire en, input wire [3:0] a, output wire [3:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(4), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail5 (input wire ck, input wire en, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(5), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail7 (input wire ck, input wire en, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(7), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail8 (input wire ck, input wire en, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(8), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail9 (input wire ck, input wire en, input wire [8:0] a, output wire [8:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(9), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail17 (input wire ck, input wire en, input wire [16:0] a, output wire [16:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(17), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail19 (input wire ck, input wire en, input wire [18:0] a, output wire [18:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(19), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tail32 (input wire ck, input wire en, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(32), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(1), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail2 (input wire ck, input wire en, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(2), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail3 (input wire ck, input wire en, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(3), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail4 (input wire ck, input wire en, input wire [3:0] a, output wire [3:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(4), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail5 (input wire ck, input wire en, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(5), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail8 (input wire ck, input wire en, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(8), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail13 (input wire ck, input wire en, input wire [12:0] a, output wire [12:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(13), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail17 (input wire ck, input wire en, input wire [16:0] a, output wire [16:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(17), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail19 (input wire ck, input wire en, input wire [18:0] a, output wire [18:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(19), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail21 (input wire ck, input wire en, input wire [20:0] a, output wire [20:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(21), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail28 (input wire ck, input wire en, input wire [27:0] a, output wire [27:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(28), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tail41 (input wire ck, input wire en, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(41), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(1), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail2 (input wire ck, input wire en, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(2), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail3 (input wire ck, input wire en, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(3), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail4 (input wire ck, input wire en, input wire [3:0] a, output wire [3:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(4), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail5 (input wire ck, input wire en, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(5), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail7 (input wire ck, input wire en, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(7), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail8 (input wire ck, input wire en, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(8), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail9 (input wire ck, input wire en, input wire [8:0] a, output wire [8:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(9), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail13 (input wire ck, input wire en, input wire [12:0] a, output wire [12:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(13), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail17 (input wire ck, input wire en, input wire [16:0] a, output wire [16:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(17), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail19 (input wire ck, input wire en, input wire [18:0] a, output wire [18:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(19), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail21 (input wire ck, input wire en, input wire [20:0] a, output wire [20:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(21), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail41 (input wire ck, input wire en, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(41), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tail43 (input wire ck, input wire en, input wire [42:0] a, output wire [42:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(43), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail1 (input wire ck, input wire en, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(1), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail3 (input wire ck, input wire en, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(3), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail4 (input wire ck, input wire en, input wire [3:0] a, output wire [3:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(4), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail7 (input wire ck, input wire en, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(7), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail8 (input wire ck, input wire en, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(8), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail9 (input wire ck, input wire en, input wire [8:0] a, output wire [8:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(9), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail16 (input wire ck, input wire en, input wire [15:0] a, output wire [15:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(16), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail17 (input wire ck, input wire en, input wire [16:0] a, output wire [16:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(17), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail21 (input wire ck, input wire en, input wire [20:0] a, output wire [20:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(21), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tail32 (input wire ck, input wire en, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(32), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail83 (input wire ck, input wire en, input wire [82:0] a, output wire [82:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(83), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail116 (input wire ck, input wire en, input wire [115:0] a, output wire [115:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(116), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail136 (input wire ck, input wire en, input wire [135:0] a, output wire [135:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(136), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail138 (input wire ck, input wire en, input wire [137:0] a, output wire [137:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(138), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail171 (input wire ck, input wire en, input wire [170:0] a, output wire [170:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(171), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail207 (input wire ck, input wire en, input wire [206:0] a, output wire [206:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(207), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail213 (input wire ck, input wire en, input wire [212:0] a, output wire [212:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(213), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail257 (input wire ck, input wire en, input wire [256:0] a, output wire [256:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(257), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail280 (input wire ck, input wire en, input wire [279:0] a, output wire [279:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(280), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail281 (input wire ck, input wire en, input wire [280:0] a, output wire [280:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(281), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail297 (input wire ck, input wire en, input wire [296:0] a, output wire [296:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(297), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail352 (input wire ck, input wire en, input wire [351:0] a, output wire [351:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(352), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail516 (input wire ck, input wire en, input wire [515:0] a, output wire [515:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(516), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail524 (input wire ck, input wire en, input wire [523:0] a, output wire [523:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(524), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail562 (input wire ck, input wire en, input wire [561:0] a, output wire [561:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(562), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail572 (input wire ck, input wire en, input wire [571:0] a, output wire [571:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(572), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail613 (input wire ck, input wire en, input wire [612:0] a, output wire [612:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(613), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tail614 (input wire ck, input wire en, input wire [613:0] a, output wire [613:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(614), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail61 (input wire ck, input wire en, input wire [60:0] a, output wire [60:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(61), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail67 (input wire ck, input wire en, input wire [66:0] a, output wire [66:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(67), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail76 (input wire ck, input wire en, input wire [75:0] a, output wire [75:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(76), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail136 (input wire ck, input wire en, input wire [135:0] a, output wire [135:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(136), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail138 (input wire ck, input wire en, input wire [137:0] a, output wire [137:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(138), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail171 (input wire ck, input wire en, input wire [170:0] a, output wire [170:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(171), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail173 (input wire ck, input wire en, input wire [172:0] a, output wire [172:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(173), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail184 (input wire ck, input wire en, input wire [183:0] a, output wire [183:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(184), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail213 (input wire ck, input wire en, input wire [212:0] a, output wire [212:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(213), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail257 (input wire ck, input wire en, input wire [256:0] a, output wire [256:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(257), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail271 (input wire ck, input wire en, input wire [270:0] a, output wire [270:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(271), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail280 (input wire ck, input wire en, input wire [279:0] a, output wire [279:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(280), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail281 (input wire ck, input wire en, input wire [280:0] a, output wire [280:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(281), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail296 (input wire ck, input wire en, input wire [295:0] a, output wire [295:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(296), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail297 (input wire ck, input wire en, input wire [296:0] a, output wire [296:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(297), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail314 (input wire ck, input wire en, input wire [313:0] a, output wire [313:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(314), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail338 (input wire ck, input wire en, input wire [337:0] a, output wire [337:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(338), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail352 (input wire ck, input wire en, input wire [351:0] a, output wire [351:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(352), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail376 (input wire ck, input wire en, input wire [375:0] a, output wire [375:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(376), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail512 (input wire ck, input wire en, input wire [511:0] a, output wire [511:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(512), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail516 (input wire ck, input wire en, input wire [515:0] a, output wire [515:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(516), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail520 (input wire ck, input wire en, input wire [519:0] a, output wire [519:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(520), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tail562 (input wire ck, input wire en, input wire [561:0] a, output wire [561:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(562), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail65 (input wire ck, input wire en, input wire [64:0] a, output wire [64:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(65), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail72 (input wire ck, input wire en, input wire [71:0] a, output wire [71:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(72), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail136 (input wire ck, input wire en, input wire [135:0] a, output wire [135:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(136), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail173 (input wire ck, input wire en, input wire [172:0] a, output wire [172:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(173), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail257 (input wire ck, input wire en, input wire [256:0] a, output wire [256:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(257), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail271 (input wire ck, input wire en, input wire [270:0] a, output wire [270:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(271), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail273 (input wire ck, input wire en, input wire [272:0] a, output wire [272:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(273), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail280 (input wire ck, input wire en, input wire [279:0] a, output wire [279:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(280), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail281 (input wire ck, input wire en, input wire [280:0] a, output wire [280:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(281), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail296 (input wire ck, input wire en, input wire [295:0] a, output wire [295:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(296), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail297 (input wire ck, input wire en, input wire [296:0] a, output wire [296:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(297), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail319 (input wire ck, input wire en, input wire [318:0] a, output wire [318:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(319), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail512 (input wire ck, input wire en, input wire [511:0] a, output wire [511:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(512), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail516 (input wire ck, input wire en, input wire [515:0] a, output wire [515:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(516), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail520 (input wire ck, input wire en, input wire [519:0] a, output wire [519:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(520), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail524 (input wire ck, input wire en, input wire [523:0] a, output wire [523:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(524), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail562 (input wire ck, input wire en, input wire [561:0] a, output wire [561:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(562), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail586 (input wire ck, input wire en, input wire [585:0] a, output wire [585:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(586), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail594 (input wire ck, input wire en, input wire [593:0] a, output wire [593:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(594), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tail613 (input wire ck, input wire en, input wire [612:0] a, output wire [612:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(613), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail83 (input wire ck, input wire en, input wire [82:0] a, output wire [82:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(83), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail116 (input wire ck, input wire en, input wire [115:0] a, output wire [115:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(116), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail136 (input wire ck, input wire en, input wire [135:0] a, output wire [135:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(136), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail138 (input wire ck, input wire en, input wire [137:0] a, output wire [137:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(138), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail171 (input wire ck, input wire en, input wire [170:0] a, output wire [170:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(171), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail184 (input wire ck, input wire en, input wire [183:0] a, output wire [183:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(184), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail206 (input wire ck, input wire en, input wire [205:0] a, output wire [205:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(206), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail213 (input wire ck, input wire en, input wire [212:0] a, output wire [212:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(213), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail257 (input wire ck, input wire en, input wire [256:0] a, output wire [256:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(257), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail274 (input wire ck, input wire en, input wire [273:0] a, output wire [273:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(274), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail280 (input wire ck, input wire en, input wire [279:0] a, output wire [279:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(280), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail281 (input wire ck, input wire en, input wire [280:0] a, output wire [280:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(281), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail319 (input wire ck, input wire en, input wire [318:0] a, output wire [318:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(319), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail352 (input wire ck, input wire en, input wire [351:0] a, output wire [351:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(352), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail376 (input wire ck, input wire en, input wire [375:0] a, output wire [375:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(376), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail469 (input wire ck, input wire en, input wire [468:0] a, output wire [468:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(469), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail512 (input wire ck, input wire en, input wire [511:0] a, output wire [511:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(512), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail562 (input wire ck, input wire en, input wire [561:0] a, output wire [561:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(562), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail596 (input wire ck, input wire en, input wire [595:0] a, output wire [595:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(596), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail613 (input wire ck, input wire en, input wire [612:0] a, output wire [612:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(613), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tail614 (input wire ck, input wire en, input wire [613:0] a, output wire [613:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(614), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(1), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail3 (input wire ckf, input wire ea, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(5), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(7), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(8), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail11 (input wire ckf, input wire ea, input wire [10:0] a, output wire [10:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(11), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [11:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(12), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(32), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [36:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(37), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(41), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [42:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(43), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail48 (input wire ckf, input wire ea, input wire [47:0] a, output wire [47:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(48), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail66 (input wire ckf, input wire ea, input wire [65:0] a, output wire [65:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(66), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail79 (input wire ckf, input wire ea, input wire [78:0] a, output wire [78:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(79), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail108 (input wire ckf, input wire ea, input wire [107:0] a, output wire [107:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(108), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail110 (input wire ckf, input wire ea, input wire [109:0] a, output wire [109:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(110), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tail130 (input wire ckf, input wire ea, input wire [129:0] a, output wire [129:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(130), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(1), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [3:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(2), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [9:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(5), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [13:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(7), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [15:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(8), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail11 (input wire ckf, input wire ea, input wire [10:0] a, output wire [21:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(11), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [23:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(12), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [73:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(37), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [81:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(41), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [85:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(43), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail66 (input wire ckf, input wire ea, input wire [65:0] a, output wire [131:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(66), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail79 (input wire ckf, input wire ea, input wire [78:0] a, output wire [157:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(79), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tail110 (input wire ckf, input wire ea, input wire [109:0] a, output wire [219:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(110), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f3_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [5:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(2), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f3_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [14:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(5), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f3_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [110:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(37), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f3_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [122:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(41), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f3_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [128:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(43), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(1), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail3 (input wire ckf, input wire ea, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(5), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(7), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(8), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail11 (input wire ckf, input wire ea, input wire [10:0] a, output wire [10:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(11), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [11:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(12), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(32), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [36:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(37), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(41), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [42:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(43), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail48 (input wire ckf, input wire ea, input wire [47:0] a, output wire [47:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(48), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail66 (input wire ckf, input wire ea, input wire [65:0] a, output wire [65:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(66), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail79 (input wire ckf, input wire ea, input wire [78:0] a, output wire [78:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(79), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail108 (input wire ckf, input wire ea, input wire [107:0] a, output wire [107:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(108), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail110 (input wire ckf, input wire ea, input wire [109:0] a, output wire [109:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(110), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tail130 (input wire ckf, input wire ea, input wire [129:0] a, output wire [129:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(130), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(1), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail3 (input wire ckf, input wire ea, input wire [2:0] a, output wire [5:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(3), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [9:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(5), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [15:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(8), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail11 (input wire ckf, input wire ea, input wire [10:0] a, output wire [21:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(11), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [23:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(12), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [73:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(37), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [81:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(41), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [85:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(43), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail108 (input wire ckf, input wire ea, input wire [107:0] a, output wire [215:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(108), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail110 (input wire ckf, input wire ea, input wire [109:0] a, output wire [219:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(110), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tail130 (input wire ckf, input wire ea, input wire [129:0] a, output wire [259:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(130), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f3_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [2:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(1), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f3_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [14:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(5), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f3_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [20:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(7), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f3_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [35:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(12), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f3_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [122:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(41), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f3_tail48 (input wire ckf, input wire ea, input wire [47:0] a, output wire [143:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(48), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(1), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(5), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(7), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(8), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail11 (input wire ckf, input wire ea, input wire [10:0] a, output wire [10:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(11), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [11:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(12), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(32), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [36:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(37), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(41), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [42:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(43), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail48 (input wire ckf, input wire ea, input wire [47:0] a, output wire [47:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(48), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail79 (input wire ckf, input wire ea, input wire [78:0] a, output wire [78:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(79), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail108 (input wire ckf, input wire ea, input wire [107:0] a, output wire [107:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(108), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail110 (input wire ckf, input wire ea, input wire [109:0] a, output wire [109:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(110), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tail130 (input wire ckf, input wire ea, input wire [129:0] a, output wire [129:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(130), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(1), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [9:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(5), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [13:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(7), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [15:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(8), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail11 (input wire ckf, input wire ea, input wire [10:0] a, output wire [21:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(11), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [23:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(12), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [73:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(37), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [81:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(41), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [85:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(43), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail48 (input wire ckf, input wire ea, input wire [47:0] a, output wire [95:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(48), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail108 (input wire ckf, input wire ea, input wire [107:0] a, output wire [215:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(108), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tail130 (input wire ckf, input wire ea, input wire [129:0] a, output wire [259:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(130), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f3_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [2:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(1), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f3_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [20:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(7), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f3_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [35:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(12), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f3_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [110:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(37), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f3_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [122:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(41), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f3_tail48 (input wire ckf, input wire ea, input wire [47:0] a, output wire [143:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(48), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f3_tail110 (input wire ckf, input wire ea, input wire [109:0] a, output wire [329:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(110), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(1), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail3 (input wire ckf, input wire ea, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(5), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(7), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(8), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail11 (input wire ckf, input wire ea, input wire [10:0] a, output wire [10:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(11), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [11:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(12), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(32), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [36:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(37), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(41), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [42:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(43), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail48 (input wire ckf, input wire ea, input wire [47:0] a, output wire [47:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(48), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail79 (input wire ckf, input wire ea, input wire [78:0] a, output wire [78:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(79), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tail110 (input wire ckf, input wire ea, input wire [109:0] a, output wire [109:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(110), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [3:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(2), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [9:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(5), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [13:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(7), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [15:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(8), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [23:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(12), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [63:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(32), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [73:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(37), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [81:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(41), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [85:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(43), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail48 (input wire ckf, input wire ea, input wire [47:0] a, output wire [95:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(48), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail79 (input wire ckf, input wire ea, input wire [78:0] a, output wire [157:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(79), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tail110 (input wire ckf, input wire ea, input wire [109:0] a, output wire [219:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(110), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f3_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [5:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(2), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f3_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [14:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(5), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f3_tail11 (input wire ckf, input wire ea, input wire [10:0] a, output wire [32:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(11), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f3_tail12 (input wire ckf, input wire ea, input wire [11:0] a, output wire [35:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(12), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f3_tail37 (input wire ckf, input wire ea, input wire [36:0] a, output wire [110:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(37), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f3_tail43 (input wire ckf, input wire ea, input wire [42:0] a, output wire [128:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(43), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f3_tail79 (input wire ckf, input wire ea, input wire [78:0] a, output wire [236:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(79), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(1), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail3 (input wire ckf, input wire ea, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail4 (input wire ckf, input wire ea, input wire [3:0] a, output wire [3:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(4), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(5), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(7), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(8), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail9 (input wire ckf, input wire ea, input wire [8:0] a, output wire [8:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(9), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail16 (input wire ckf, input wire ea, input wire [15:0] a, output wire [15:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(16), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail17 (input wire ckf, input wire ea, input wire [16:0] a, output wire [16:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(17), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail19 (input wire ckf, input wire ea, input wire [18:0] a, output wire [18:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(19), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail21 (input wire ckf, input wire ea, input wire [20:0] a, output wire [20:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(21), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(32), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(41), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(1), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail3 (input wire ckf, input wire ea, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail4 (input wire ckf, input wire ea, input wire [3:0] a, output wire [3:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(4), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(5), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(7), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(8), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail9 (input wire ckf, input wire ea, input wire [8:0] a, output wire [8:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(9), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail13 (input wire ckf, input wire ea, input wire [12:0] a, output wire [12:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(13), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail16 (input wire ckf, input wire ea, input wire [15:0] a, output wire [15:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(16), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail17 (input wire ckf, input wire ea, input wire [16:0] a, output wire [16:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(17), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail19 (input wire ckf, input wire ea, input wire [18:0] a, output wire [18:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(19), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail21 (input wire ckf, input wire ea, input wire [20:0] a, output wire [20:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(21), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(32), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(1), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail3 (input wire ckf, input wire ea, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail4 (input wire ckf, input wire ea, input wire [3:0] a, output wire [3:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(4), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(5), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(7), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(8), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail9 (input wire ckf, input wire ea, input wire [8:0] a, output wire [8:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(9), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail13 (input wire ckf, input wire ea, input wire [12:0] a, output wire [12:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(13), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail17 (input wire ckf, input wire ea, input wire [16:0] a, output wire [16:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(17), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail19 (input wire ckf, input wire ea, input wire [18:0] a, output wire [18:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(19), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail21 (input wire ckf, input wire ea, input wire [20:0] a, output wire [20:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(21), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(32), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tail41 (input wire ckf, input wire ea, input wire [40:0] a, output wire [40:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(41), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail1 (input wire ckf, input wire ea, input wire [0:0] a, output wire [0:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(1), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail2 (input wire ckf, input wire ea, input wire [1:0] a, output wire [1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail3 (input wire ckf, input wire ea, input wire [2:0] a, output wire [2:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail4 (input wire ckf, input wire ea, input wire [3:0] a, output wire [3:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(4), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail5 (input wire ckf, input wire ea, input wire [4:0] a, output wire [4:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(5), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail7 (input wire ckf, input wire ea, input wire [6:0] a, output wire [6:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(7), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail8 (input wire ckf, input wire ea, input wire [7:0] a, output wire [7:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(8), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail9 (input wire ckf, input wire ea, input wire [8:0] a, output wire [8:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(9), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail16 (input wire ckf, input wire ea, input wire [15:0] a, output wire [15:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(16), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail17 (input wire ckf, input wire ea, input wire [16:0] a, output wire [16:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(17), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail19 (input wire ckf, input wire ea, input wire [18:0] a, output wire [18:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(19), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail21 (input wire ckf, input wire ea, input wire [20:0] a, output wire [20:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(21), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tail32 (input wire ckf, input wire ea, input wire [31:0] a, output wire [31:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(32), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail61 (input wire ckf, input wire ea, input wire [60:0] a, output wire [60:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(61), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail67 (input wire ckf, input wire ea, input wire [66:0] a, output wire [66:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(67), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail72 (input wire ckf, input wire ea, input wire [71:0] a, output wire [71:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(72), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail76 (input wire ckf, input wire ea, input wire [75:0] a, output wire [75:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(76), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail83 (input wire ckf, input wire ea, input wire [82:0] a, output wire [82:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(83), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail116 (input wire ckf, input wire ea, input wire [115:0] a, output wire [115:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(116), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail136 (input wire ckf, input wire ea, input wire [135:0] a, output wire [135:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(136), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail138 (input wire ckf, input wire ea, input wire [137:0] a, output wire [137:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(138), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail171 (input wire ckf, input wire ea, input wire [170:0] a, output wire [170:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(171), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail173 (input wire ckf, input wire ea, input wire [172:0] a, output wire [172:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(173), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail213 (input wire ckf, input wire ea, input wire [212:0] a, output wire [212:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(213), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail257 (input wire ckf, input wire ea, input wire [256:0] a, output wire [256:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(257), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail271 (input wire ckf, input wire ea, input wire [270:0] a, output wire [270:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(271), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail273 (input wire ckf, input wire ea, input wire [272:0] a, output wire [272:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(273), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail280 (input wire ckf, input wire ea, input wire [279:0] a, output wire [279:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(280), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail281 (input wire ckf, input wire ea, input wire [280:0] a, output wire [280:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(281), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail296 (input wire ckf, input wire ea, input wire [295:0] a, output wire [295:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(296), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail297 (input wire ckf, input wire ea, input wire [296:0] a, output wire [296:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(297), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail338 (input wire ckf, input wire ea, input wire [337:0] a, output wire [337:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(338), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail352 (input wire ckf, input wire ea, input wire [351:0] a, output wire [351:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(352), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail512 (input wire ckf, input wire ea, input wire [511:0] a, output wire [511:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(512), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail516 (input wire ckf, input wire ea, input wire [515:0] a, output wire [515:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(516), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail524 (input wire ckf, input wire ea, input wire [523:0] a, output wire [523:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(524), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail562 (input wire ckf, input wire ea, input wire [561:0] a, output wire [561:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(562), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail572 (input wire ckf, input wire ea, input wire [571:0] a, output wire [571:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(572), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail586 (input wire ckf, input wire ea, input wire [585:0] a, output wire [585:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(586), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail594 (input wire ckf, input wire ea, input wire [593:0] a, output wire [593:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(594), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail596 (input wire ckf, input wire ea, input wire [595:0] a, output wire [595:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(596), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail613 (input wire ckf, input wire ea, input wire [612:0] a, output wire [612:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(613), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tail614 (input wire ckf, input wire ea, input wire [613:0] a, output wire [613:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(614), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail61 (input wire ckf, input wire ea, input wire [60:0] a, output wire [60:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(61), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail67 (input wire ckf, input wire ea, input wire [66:0] a, output wire [66:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(67), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail76 (input wire ckf, input wire ea, input wire [75:0] a, output wire [75:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(76), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail83 (input wire ckf, input wire ea, input wire [82:0] a, output wire [82:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(83), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail116 (input wire ckf, input wire ea, input wire [115:0] a, output wire [115:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(116), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail136 (input wire ckf, input wire ea, input wire [135:0] a, output wire [135:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(136), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail138 (input wire ckf, input wire ea, input wire [137:0] a, output wire [137:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(138), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail171 (input wire ckf, input wire ea, input wire [170:0] a, output wire [170:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(171), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail173 (input wire ckf, input wire ea, input wire [172:0] a, output wire [172:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(173), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail213 (input wire ckf, input wire ea, input wire [212:0] a, output wire [212:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(213), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail257 (input wire ckf, input wire ea, input wire [256:0] a, output wire [256:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(257), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail271 (input wire ckf, input wire ea, input wire [270:0] a, output wire [270:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(271), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail280 (input wire ckf, input wire ea, input wire [279:0] a, output wire [279:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(280), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail281 (input wire ckf, input wire ea, input wire [280:0] a, output wire [280:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(281), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail296 (input wire ckf, input wire ea, input wire [295:0] a, output wire [295:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(296), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail297 (input wire ckf, input wire ea, input wire [296:0] a, output wire [296:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(297), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail338 (input wire ckf, input wire ea, input wire [337:0] a, output wire [337:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(338), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail352 (input wire ckf, input wire ea, input wire [351:0] a, output wire [351:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(352), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail376 (input wire ckf, input wire ea, input wire [375:0] a, output wire [375:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(376), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail512 (input wire ckf, input wire ea, input wire [511:0] a, output wire [511:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(512), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail516 (input wire ckf, input wire ea, input wire [515:0] a, output wire [515:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(516), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail520 (input wire ckf, input wire ea, input wire [519:0] a, output wire [519:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(520), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail562 (input wire ckf, input wire ea, input wire [561:0] a, output wire [561:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(562), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail586 (input wire ckf, input wire ea, input wire [585:0] a, output wire [585:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(586), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail596 (input wire ckf, input wire ea, input wire [595:0] a, output wire [595:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(596), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail613 (input wire ckf, input wire ea, input wire [612:0] a, output wire [612:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(613), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tail614 (input wire ckf, input wire ea, input wire [613:0] a, output wire [613:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(614), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail65 (input wire ckf, input wire ea, input wire [64:0] a, output wire [64:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(65), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail72 (input wire ckf, input wire ea, input wire [71:0] a, output wire [71:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(72), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail76 (input wire ckf, input wire ea, input wire [75:0] a, output wire [75:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(76), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail83 (input wire ckf, input wire ea, input wire [82:0] a, output wire [82:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(83), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail116 (input wire ckf, input wire ea, input wire [115:0] a, output wire [115:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(116), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail136 (input wire ckf, input wire ea, input wire [135:0] a, output wire [135:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(136), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail138 (input wire ckf, input wire ea, input wire [137:0] a, output wire [137:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(138), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail171 (input wire ckf, input wire ea, input wire [170:0] a, output wire [170:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(171), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail173 (input wire ckf, input wire ea, input wire [172:0] a, output wire [172:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(173), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail207 (input wire ckf, input wire ea, input wire [206:0] a, output wire [206:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(207), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail213 (input wire ckf, input wire ea, input wire [212:0] a, output wire [212:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(213), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail257 (input wire ckf, input wire ea, input wire [256:0] a, output wire [256:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(257), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail271 (input wire ckf, input wire ea, input wire [270:0] a, output wire [270:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(271), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail274 (input wire ckf, input wire ea, input wire [273:0] a, output wire [273:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(274), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail280 (input wire ckf, input wire ea, input wire [279:0] a, output wire [279:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(280), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail281 (input wire ckf, input wire ea, input wire [280:0] a, output wire [280:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(281), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail297 (input wire ckf, input wire ea, input wire [296:0] a, output wire [296:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(297), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail352 (input wire ckf, input wire ea, input wire [351:0] a, output wire [351:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(352), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail512 (input wire ckf, input wire ea, input wire [511:0] a, output wire [511:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(512), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail516 (input wire ckf, input wire ea, input wire [515:0] a, output wire [515:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(516), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail520 (input wire ckf, input wire ea, input wire [519:0] a, output wire [519:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(520), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail524 (input wire ckf, input wire ea, input wire [523:0] a, output wire [523:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(524), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail562 (input wire ckf, input wire ea, input wire [561:0] a, output wire [561:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(562), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail594 (input wire ckf, input wire ea, input wire [593:0] a, output wire [593:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(594), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail596 (input wire ckf, input wire ea, input wire [595:0] a, output wire [595:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(596), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tail614 (input wire ckf, input wire ea, input wire [613:0] a, output wire [613:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(614), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail61 (input wire ckf, input wire ea, input wire [60:0] a, output wire [60:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(61), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail65 (input wire ckf, input wire ea, input wire [64:0] a, output wire [64:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(65), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail67 (input wire ckf, input wire ea, input wire [66:0] a, output wire [66:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(67), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail76 (input wire ckf, input wire ea, input wire [75:0] a, output wire [75:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(76), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail83 (input wire ckf, input wire ea, input wire [82:0] a, output wire [82:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(83), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail116 (input wire ckf, input wire ea, input wire [115:0] a, output wire [115:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(116), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail136 (input wire ckf, input wire ea, input wire [135:0] a, output wire [135:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(136), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail138 (input wire ckf, input wire ea, input wire [137:0] a, output wire [137:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(138), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail171 (input wire ckf, input wire ea, input wire [170:0] a, output wire [170:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(171), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail173 (input wire ckf, input wire ea, input wire [172:0] a, output wire [172:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(173), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail207 (input wire ckf, input wire ea, input wire [206:0] a, output wire [206:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(207), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail213 (input wire ckf, input wire ea, input wire [212:0] a, output wire [212:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(213), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail257 (input wire ckf, input wire ea, input wire [256:0] a, output wire [256:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(257), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail271 (input wire ckf, input wire ea, input wire [270:0] a, output wire [270:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(271), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail274 (input wire ckf, input wire ea, input wire [273:0] a, output wire [273:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(274), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail280 (input wire ckf, input wire ea, input wire [279:0] a, output wire [279:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(280), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail281 (input wire ckf, input wire ea, input wire [280:0] a, output wire [280:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(281), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail296 (input wire ckf, input wire ea, input wire [295:0] a, output wire [295:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(296), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail297 (input wire ckf, input wire ea, input wire [296:0] a, output wire [296:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(297), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail352 (input wire ckf, input wire ea, input wire [351:0] a, output wire [351:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(352), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail469 (input wire ckf, input wire ea, input wire [468:0] a, output wire [468:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(469), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail512 (input wire ckf, input wire ea, input wire [511:0] a, output wire [511:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(512), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail516 (input wire ckf, input wire ea, input wire [515:0] a, output wire [515:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(516), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail524 (input wire ckf, input wire ea, input wire [523:0] a, output wire [523:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(524), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail562 (input wire ckf, input wire ea, input wire [561:0] a, output wire [561:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(562), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail596 (input wire ckf, input wire ea, input wire [595:0] a, output wire [595:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(596), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail613 (input wire ckf, input wire ea, input wire [612:0] a, output wire [612:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(613), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tail614 (input wire ckf, input wire ea, input wire [613:0] a, output wire [613:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(614), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_rly_136_WE_tail1 (input wire ck, input wire rs, input wire [0:0] i, output wire [0:0] o);
    ot_hbm_rly #(.W(1), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail2 (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);
    ot_hbm_rly #(.W(2), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail3 (input wire ck, input wire rs, input wire [2:0] i, output wire [2:0] o);
    ot_hbm_rly #(.W(3), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail5 (input wire ck, input wire rs, input wire [4:0] i, output wire [4:0] o);
    ot_hbm_rly #(.W(5), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail7 (input wire ck, input wire rs, input wire [6:0] i, output wire [6:0] o);
    ot_hbm_rly #(.W(7), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail8 (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o);
    ot_hbm_rly #(.W(8), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail11 (input wire ck, input wire rs, input wire [10:0] i, output wire [10:0] o);
    ot_hbm_rly #(.W(11), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail12 (input wire ck, input wire rs, input wire [11:0] i, output wire [11:0] o);
    ot_hbm_rly #(.W(12), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail32 (input wire ck, input wire rs, input wire [31:0] i, output wire [31:0] o);
    ot_hbm_rly #(.W(32), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail37 (input wire ck, input wire rs, input wire [36:0] i, output wire [36:0] o);
    ot_hbm_rly #(.W(37), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail41 (input wire ck, input wire rs, input wire [40:0] i, output wire [40:0] o);
    ot_hbm_rly #(.W(41), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail43 (input wire ck, input wire rs, input wire [42:0] i, output wire [42:0] o);
    ot_hbm_rly #(.W(43), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail48 (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o);
    ot_hbm_rly #(.W(48), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail66 (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);
    ot_hbm_rly #(.W(66), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail79 (input wire ck, input wire rs, input wire [78:0] i, output wire [78:0] o);
    ot_hbm_rly #(.W(79), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail108 (input wire ck, input wire rs, input wire [107:0] i, output wire [107:0] o);
    ot_hbm_rly #(.W(108), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail110 (input wire ck, input wire rs, input wire [109:0] i, output wire [109:0] o);
    ot_hbm_rly #(.W(110), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_136_WE_tail130 (input wire ck, input wire rs, input wire [129:0] i, output wire [129:0] o);
    ot_hbm_rly #(.W(130), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail1 (input wire ck, input wire rs, input wire [0:0] i, output wire [0:0] o);
    ot_hbm_rly #(.W(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail2 (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);
    ot_hbm_rly #(.W(2)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail3 (input wire ck, input wire rs, input wire [2:0] i, output wire [2:0] o);
    ot_hbm_rly #(.W(3)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail4 (input wire ck, input wire rs, input wire [3:0] i, output wire [3:0] o);
    ot_hbm_rly #(.W(4)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail5 (input wire ck, input wire rs, input wire [4:0] i, output wire [4:0] o);
    ot_hbm_rly #(.W(5)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail7 (input wire ck, input wire rs, input wire [6:0] i, output wire [6:0] o);
    ot_hbm_rly #(.W(7)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail8 (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail10 (input wire ck, input wire rs, input wire [9:0] i, output wire [9:0] o);
    ot_hbm_rly #(.W(10)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail14 (input wire ck, input wire rs, input wire [13:0] i, output wire [13:0] o);
    ot_hbm_rly #(.W(14)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail17 (input wire ck, input wire rs, input wire [16:0] i, output wire [16:0] o);
    ot_hbm_rly #(.W(17)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail25 (input wire ck, input wire rs, input wire [24:0] i, output wire [24:0] o);
    ot_hbm_rly #(.W(25)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail28 (input wire ck, input wire rs, input wire [27:0] i, output wire [27:0] o);
    ot_hbm_rly #(.W(28)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail32 (input wire ck, input wire rs, input wire [31:0] i, output wire [31:0] o);
    ot_hbm_rly #(.W(32)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail40 (input wire ck, input wire rs, input wire [39:0] i, output wire [39:0] o);
    ot_hbm_rly #(.W(40)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail41 (input wire ck, input wire rs, input wire [40:0] i, output wire [40:0] o);
    ot_hbm_rly #(.W(41)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tail43 (input wire ck, input wire rs, input wire [42:0] i, output wire [42:0] o);
    ot_hbm_rly #(.W(43)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail1 (input wire ck, input wire rs, input wire [0:0] i, output wire [0:0] o);
    ot_hbm_rly #(.W(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail2 (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);
    ot_hbm_rly #(.W(2)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail3 (input wire ck, input wire rs, input wire [2:0] i, output wire [2:0] o);
    ot_hbm_rly #(.W(3)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail4 (input wire ck, input wire rs, input wire [3:0] i, output wire [3:0] o);
    ot_hbm_rly #(.W(4)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail5 (input wire ck, input wire rs, input wire [4:0] i, output wire [4:0] o);
    ot_hbm_rly #(.W(5)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail8 (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail13 (input wire ck, input wire rs, input wire [12:0] i, output wire [12:0] o);
    ot_hbm_rly #(.W(13)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail14 (input wire ck, input wire rs, input wire [13:0] i, output wire [13:0] o);
    ot_hbm_rly #(.W(14)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail16 (input wire ck, input wire rs, input wire [15:0] i, output wire [15:0] o);
    ot_hbm_rly #(.W(16)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail17 (input wire ck, input wire rs, input wire [16:0] i, output wire [16:0] o);
    ot_hbm_rly #(.W(17)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail25 (input wire ck, input wire rs, input wire [24:0] i, output wire [24:0] o);
    ot_hbm_rly #(.W(25)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail28 (input wire ck, input wire rs, input wire [27:0] i, output wire [27:0] o);
    ot_hbm_rly #(.W(28)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail32 (input wire ck, input wire rs, input wire [31:0] i, output wire [31:0] o);
    ot_hbm_rly #(.W(32)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail35 (input wire ck, input wire rs, input wire [34:0] i, output wire [34:0] o);
    ot_hbm_rly #(.W(35)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail39 (input wire ck, input wire rs, input wire [38:0] i, output wire [38:0] o);
    ot_hbm_rly #(.W(39)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail40 (input wire ck, input wire rs, input wire [39:0] i, output wire [39:0] o);
    ot_hbm_rly #(.W(40)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail41 (input wire ck, input wire rs, input wire [40:0] i, output wire [40:0] o);
    ot_hbm_rly #(.W(41)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tail43 (input wire ck, input wire rs, input wire [42:0] i, output wire [42:0] o);
    ot_hbm_rly #(.W(43)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail1 (input wire ck, input wire rs, input wire [0:0] i, output wire [0:0] o);
    ot_hbm_rly #(.W(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail2 (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);
    ot_hbm_rly #(.W(2)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail3 (input wire ck, input wire rs, input wire [2:0] i, output wire [2:0] o);
    ot_hbm_rly #(.W(3)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail4 (input wire ck, input wire rs, input wire [3:0] i, output wire [3:0] o);
    ot_hbm_rly #(.W(4)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail5 (input wire ck, input wire rs, input wire [4:0] i, output wire [4:0] o);
    ot_hbm_rly #(.W(5)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail8 (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail10 (input wire ck, input wire rs, input wire [9:0] i, output wire [9:0] o);
    ot_hbm_rly #(.W(10)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail13 (input wire ck, input wire rs, input wire [12:0] i, output wire [12:0] o);
    ot_hbm_rly #(.W(13)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail14 (input wire ck, input wire rs, input wire [13:0] i, output wire [13:0] o);
    ot_hbm_rly #(.W(14)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail17 (input wire ck, input wire rs, input wire [16:0] i, output wire [16:0] o);
    ot_hbm_rly #(.W(17)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail25 (input wire ck, input wire rs, input wire [24:0] i, output wire [24:0] o);
    ot_hbm_rly #(.W(25)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail28 (input wire ck, input wire rs, input wire [27:0] i, output wire [27:0] o);
    ot_hbm_rly #(.W(28)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail32 (input wire ck, input wire rs, input wire [31:0] i, output wire [31:0] o);
    ot_hbm_rly #(.W(32)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail35 (input wire ck, input wire rs, input wire [34:0] i, output wire [34:0] o);
    ot_hbm_rly #(.W(35)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail39 (input wire ck, input wire rs, input wire [38:0] i, output wire [38:0] o);
    ot_hbm_rly #(.W(39)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail40 (input wire ck, input wire rs, input wire [39:0] i, output wire [39:0] o);
    ot_hbm_rly #(.W(40)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail41 (input wire ck, input wire rs, input wire [40:0] i, output wire [40:0] o);
    ot_hbm_rly #(.W(41)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tail43 (input wire ck, input wire rs, input wire [42:0] i, output wire [42:0] o);
    ot_hbm_rly #(.W(43)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail1 (input wire ck, input wire rs, input wire [0:0] i, output wire [0:0] o);
    ot_hbm_rly #(.W(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail2 (input wire ck, input wire rs, input wire [1:0] i, output wire [1:0] o);
    ot_hbm_rly #(.W(2)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail3 (input wire ck, input wire rs, input wire [2:0] i, output wire [2:0] o);
    ot_hbm_rly #(.W(3)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail4 (input wire ck, input wire rs, input wire [3:0] i, output wire [3:0] o);
    ot_hbm_rly #(.W(4)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail5 (input wire ck, input wire rs, input wire [4:0] i, output wire [4:0] o);
    ot_hbm_rly #(.W(5)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail7 (input wire ck, input wire rs, input wire [6:0] i, output wire [6:0] o);
    ot_hbm_rly #(.W(7)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail8 (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail9 (input wire ck, input wire rs, input wire [8:0] i, output wire [8:0] o);
    ot_hbm_rly #(.W(9)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail14 (input wire ck, input wire rs, input wire [13:0] i, output wire [13:0] o);
    ot_hbm_rly #(.W(14)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail16 (input wire ck, input wire rs, input wire [15:0] i, output wire [15:0] o);
    ot_hbm_rly #(.W(16)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail17 (input wire ck, input wire rs, input wire [16:0] i, output wire [16:0] o);
    ot_hbm_rly #(.W(17)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail25 (input wire ck, input wire rs, input wire [24:0] i, output wire [24:0] o);
    ot_hbm_rly #(.W(25)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail28 (input wire ck, input wire rs, input wire [27:0] i, output wire [27:0] o);
    ot_hbm_rly #(.W(28)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail32 (input wire ck, input wire rs, input wire [31:0] i, output wire [31:0] o);
    ot_hbm_rly #(.W(32)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail35 (input wire ck, input wire rs, input wire [34:0] i, output wire [34:0] o);
    ot_hbm_rly #(.W(35)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail39 (input wire ck, input wire rs, input wire [38:0] i, output wire [38:0] o);
    ot_hbm_rly #(.W(39)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail40 (input wire ck, input wire rs, input wire [39:0] i, output wire [39:0] o);
    ot_hbm_rly #(.W(40)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail41 (input wire ck, input wire rs, input wire [40:0] i, output wire [40:0] o);
    ot_hbm_rly #(.W(41)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tail43 (input wire ck, input wire rs, input wire [42:0] i, output wire [42:0] o);
    ot_hbm_rly #(.W(43)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail52 (input wire ck, input wire rs, input wire [51:0] i, output wire [51:0] o);
    ot_hbm_rly #(.W(52), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail64 (input wire ck, input wire rs, input wire [63:0] i, output wire [63:0] o);
    ot_hbm_rly #(.W(64), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail65 (input wire ck, input wire rs, input wire [64:0] i, output wire [64:0] o);
    ot_hbm_rly #(.W(65), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail83 (input wire ck, input wire rs, input wire [82:0] i, output wire [82:0] o);
    ot_hbm_rly #(.W(83), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail108 (input wire ck, input wire rs, input wire [107:0] i, output wire [107:0] o);
    ot_hbm_rly #(.W(108), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail116 (input wire ck, input wire rs, input wire [115:0] i, output wire [115:0] o);
    ot_hbm_rly #(.W(116), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail136 (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail138 (input wire ck, input wire rs, input wire [137:0] i, output wire [137:0] o);
    ot_hbm_rly #(.W(138), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail149 (input wire ck, input wire rs, input wire [148:0] i, output wire [148:0] o);
    ot_hbm_rly #(.W(149), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail162 (input wire ck, input wire rs, input wire [161:0] i, output wire [161:0] o);
    ot_hbm_rly #(.W(162), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail173 (input wire ck, input wire rs, input wire [172:0] i, output wire [172:0] o);
    ot_hbm_rly #(.W(173), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail191 (input wire ck, input wire rs, input wire [190:0] i, output wire [190:0] o);
    ot_hbm_rly #(.W(191), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail206 (input wire ck, input wire rs, input wire [205:0] i, output wire [205:0] o);
    ot_hbm_rly #(.W(206), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail207 (input wire ck, input wire rs, input wire [206:0] i, output wire [206:0] o);
    ot_hbm_rly #(.W(207), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail213 (input wire ck, input wire rs, input wire [212:0] i, output wire [212:0] o);
    ot_hbm_rly #(.W(213), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail257 (input wire ck, input wire rs, input wire [256:0] i, output wire [256:0] o);
    ot_hbm_rly #(.W(257), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail258 (input wire ck, input wire rs, input wire [257:0] i, output wire [257:0] o);
    ot_hbm_rly #(.W(258), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail260 (input wire ck, input wire rs, input wire [259:0] i, output wire [259:0] o);
    ot_hbm_rly #(.W(260), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail266 (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);
    ot_hbm_rly #(.W(266), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail271 (input wire ck, input wire rs, input wire [270:0] i, output wire [270:0] o);
    ot_hbm_rly #(.W(271), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail273 (input wire ck, input wire rs, input wire [272:0] i, output wire [272:0] o);
    ot_hbm_rly #(.W(273), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail277 (input wire ck, input wire rs, input wire [276:0] i, output wire [276:0] o);
    ot_hbm_rly #(.W(277), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail278 (input wire ck, input wire rs, input wire [277:0] i, output wire [277:0] o);
    ot_hbm_rly #(.W(278), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail279 (input wire ck, input wire rs, input wire [278:0] i, output wire [278:0] o);
    ot_hbm_rly #(.W(279), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail280 (input wire ck, input wire rs, input wire [279:0] i, output wire [279:0] o);
    ot_hbm_rly #(.W(280), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail281 (input wire ck, input wire rs, input wire [280:0] i, output wire [280:0] o);
    ot_hbm_rly #(.W(281), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail294 (input wire ck, input wire rs, input wire [293:0] i, output wire [293:0] o);
    ot_hbm_rly #(.W(294), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail296 (input wire ck, input wire rs, input wire [295:0] i, output wire [295:0] o);
    ot_hbm_rly #(.W(296), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail298 (input wire ck, input wire rs, input wire [297:0] i, output wire [297:0] o);
    ot_hbm_rly #(.W(298), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail342 (input wire ck, input wire rs, input wire [341:0] i, output wire [341:0] o);
    ot_hbm_rly #(.W(342), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail352 (input wire ck, input wire rs, input wire [351:0] i, output wire [351:0] o);
    ot_hbm_rly #(.W(352), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail400 (input wire ck, input wire rs, input wire [399:0] i, output wire [399:0] o);
    ot_hbm_rly #(.W(400), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail401 (input wire ck, input wire rs, input wire [400:0] i, output wire [400:0] o);
    ot_hbm_rly #(.W(401), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail424 (input wire ck, input wire rs, input wire [423:0] i, output wire [423:0] o);
    ot_hbm_rly #(.W(424), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail441 (input wire ck, input wire rs, input wire [440:0] i, output wire [440:0] o);
    ot_hbm_rly #(.W(441), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail475 (input wire ck, input wire rs, input wire [474:0] i, output wire [474:0] o);
    ot_hbm_rly #(.W(475), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail496 (input wire ck, input wire rs, input wire [495:0] i, output wire [495:0] o);
    ot_hbm_rly #(.W(496), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail514 (input wire ck, input wire rs, input wire [513:0] i, output wire [513:0] o);
    ot_hbm_rly #(.W(514), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail516 (input wire ck, input wire rs, input wire [515:0] i, output wire [515:0] o);
    ot_hbm_rly #(.W(516), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail524 (input wire ck, input wire rs, input wire [523:0] i, output wire [523:0] o);
    ot_hbm_rly #(.W(524), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail528 (input wire ck, input wire rs, input wire [527:0] i, output wire [527:0] o);
    ot_hbm_rly #(.W(528), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail560 (input wire ck, input wire rs, input wire [559:0] i, output wire [559:0] o);
    ot_hbm_rly #(.W(560), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail562 (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o);
    ot_hbm_rly #(.W(562), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail569 (input wire ck, input wire rs, input wire [568:0] i, output wire [568:0] o);
    ot_hbm_rly #(.W(569), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail579 (input wire ck, input wire rs, input wire [578:0] i, output wire [578:0] o);
    ot_hbm_rly #(.W(579), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail586 (input wire ck, input wire rs, input wire [585:0] i, output wire [585:0] o);
    ot_hbm_rly #(.W(586), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail594 (input wire ck, input wire rs, input wire [593:0] i, output wire [593:0] o);
    ot_hbm_rly #(.W(594), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tail596 (input wire ck, input wire rs, input wire [595:0] i, output wire [595:0] o);
    ot_hbm_rly #(.W(596), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail52 (input wire ck, input wire rs, input wire [51:0] i, output wire [51:0] o);
    ot_hbm_rly #(.W(52), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail64 (input wire ck, input wire rs, input wire [63:0] i, output wire [63:0] o);
    ot_hbm_rly #(.W(64), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail65 (input wire ck, input wire rs, input wire [64:0] i, output wire [64:0] o);
    ot_hbm_rly #(.W(65), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail83 (input wire ck, input wire rs, input wire [82:0] i, output wire [82:0] o);
    ot_hbm_rly #(.W(83), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail90 (input wire ck, input wire rs, input wire [89:0] i, output wire [89:0] o);
    ot_hbm_rly #(.W(90), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail108 (input wire ck, input wire rs, input wire [107:0] i, output wire [107:0] o);
    ot_hbm_rly #(.W(108), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail116 (input wire ck, input wire rs, input wire [115:0] i, output wire [115:0] o);
    ot_hbm_rly #(.W(116), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail136 (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail138 (input wire ck, input wire rs, input wire [137:0] i, output wire [137:0] o);
    ot_hbm_rly #(.W(138), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail149 (input wire ck, input wire rs, input wire [148:0] i, output wire [148:0] o);
    ot_hbm_rly #(.W(149), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail162 (input wire ck, input wire rs, input wire [161:0] i, output wire [161:0] o);
    ot_hbm_rly #(.W(162), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail173 (input wire ck, input wire rs, input wire [172:0] i, output wire [172:0] o);
    ot_hbm_rly #(.W(173), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail184 (input wire ck, input wire rs, input wire [183:0] i, output wire [183:0] o);
    ot_hbm_rly #(.W(184), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail191 (input wire ck, input wire rs, input wire [190:0] i, output wire [190:0] o);
    ot_hbm_rly #(.W(191), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail207 (input wire ck, input wire rs, input wire [206:0] i, output wire [206:0] o);
    ot_hbm_rly #(.W(207), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail213 (input wire ck, input wire rs, input wire [212:0] i, output wire [212:0] o);
    ot_hbm_rly #(.W(213), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail218 (input wire ck, input wire rs, input wire [217:0] i, output wire [217:0] o);
    ot_hbm_rly #(.W(218), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail256 (input wire ck, input wire rs, input wire [255:0] i, output wire [255:0] o);
    ot_hbm_rly #(.W(256), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail257 (input wire ck, input wire rs, input wire [256:0] i, output wire [256:0] o);
    ot_hbm_rly #(.W(257), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail260 (input wire ck, input wire rs, input wire [259:0] i, output wire [259:0] o);
    ot_hbm_rly #(.W(260), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail264 (input wire ck, input wire rs, input wire [263:0] i, output wire [263:0] o);
    ot_hbm_rly #(.W(264), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail266 (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);
    ot_hbm_rly #(.W(266), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail271 (input wire ck, input wire rs, input wire [270:0] i, output wire [270:0] o);
    ot_hbm_rly #(.W(271), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail273 (input wire ck, input wire rs, input wire [272:0] i, output wire [272:0] o);
    ot_hbm_rly #(.W(273), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail277 (input wire ck, input wire rs, input wire [276:0] i, output wire [276:0] o);
    ot_hbm_rly #(.W(277), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail279 (input wire ck, input wire rs, input wire [278:0] i, output wire [278:0] o);
    ot_hbm_rly #(.W(279), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail280 (input wire ck, input wire rs, input wire [279:0] i, output wire [279:0] o);
    ot_hbm_rly #(.W(280), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail281 (input wire ck, input wire rs, input wire [280:0] i, output wire [280:0] o);
    ot_hbm_rly #(.W(281), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail294 (input wire ck, input wire rs, input wire [293:0] i, output wire [293:0] o);
    ot_hbm_rly #(.W(294), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail296 (input wire ck, input wire rs, input wire [295:0] i, output wire [295:0] o);
    ot_hbm_rly #(.W(296), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail298 (input wire ck, input wire rs, input wire [297:0] i, output wire [297:0] o);
    ot_hbm_rly #(.W(298), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail314 (input wire ck, input wire rs, input wire [313:0] i, output wire [313:0] o);
    ot_hbm_rly #(.W(314), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail319 (input wire ck, input wire rs, input wire [318:0] i, output wire [318:0] o);
    ot_hbm_rly #(.W(319), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail342 (input wire ck, input wire rs, input wire [341:0] i, output wire [341:0] o);
    ot_hbm_rly #(.W(342), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail351 (input wire ck, input wire rs, input wire [350:0] i, output wire [350:0] o);
    ot_hbm_rly #(.W(351), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail352 (input wire ck, input wire rs, input wire [351:0] i, output wire [351:0] o);
    ot_hbm_rly #(.W(352), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail376 (input wire ck, input wire rs, input wire [375:0] i, output wire [375:0] o);
    ot_hbm_rly #(.W(376), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail400 (input wire ck, input wire rs, input wire [399:0] i, output wire [399:0] o);
    ot_hbm_rly #(.W(400), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail401 (input wire ck, input wire rs, input wire [400:0] i, output wire [400:0] o);
    ot_hbm_rly #(.W(401), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail424 (input wire ck, input wire rs, input wire [423:0] i, output wire [423:0] o);
    ot_hbm_rly #(.W(424), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail441 (input wire ck, input wire rs, input wire [440:0] i, output wire [440:0] o);
    ot_hbm_rly #(.W(441), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail475 (input wire ck, input wire rs, input wire [474:0] i, output wire [474:0] o);
    ot_hbm_rly #(.W(475), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail516 (input wire ck, input wire rs, input wire [515:0] i, output wire [515:0] o);
    ot_hbm_rly #(.W(516), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail520 (input wire ck, input wire rs, input wire [519:0] i, output wire [519:0] o);
    ot_hbm_rly #(.W(520), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail524 (input wire ck, input wire rs, input wire [523:0] i, output wire [523:0] o);
    ot_hbm_rly #(.W(524), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail528 (input wire ck, input wire rs, input wire [527:0] i, output wire [527:0] o);
    ot_hbm_rly #(.W(528), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail562 (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o);
    ot_hbm_rly #(.W(562), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail569 (input wire ck, input wire rs, input wire [568:0] i, output wire [568:0] o);
    ot_hbm_rly #(.W(569), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail586 (input wire ck, input wire rs, input wire [585:0] i, output wire [585:0] o);
    ot_hbm_rly #(.W(586), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail594 (input wire ck, input wire rs, input wire [593:0] i, output wire [593:0] o);
    ot_hbm_rly #(.W(594), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tail596 (input wire ck, input wire rs, input wire [595:0] i, output wire [595:0] o);
    ot_hbm_rly #(.W(596), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail52 (input wire ck, input wire rs, input wire [51:0] i, output wire [51:0] o);
    ot_hbm_rly #(.W(52), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail64 (input wire ck, input wire rs, input wire [63:0] i, output wire [63:0] o);
    ot_hbm_rly #(.W(64), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail67 (input wire ck, input wire rs, input wire [66:0] i, output wire [66:0] o);
    ot_hbm_rly #(.W(67), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail83 (input wire ck, input wire rs, input wire [82:0] i, output wire [82:0] o);
    ot_hbm_rly #(.W(83), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail90 (input wire ck, input wire rs, input wire [89:0] i, output wire [89:0] o);
    ot_hbm_rly #(.W(90), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail108 (input wire ck, input wire rs, input wire [107:0] i, output wire [107:0] o);
    ot_hbm_rly #(.W(108), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail116 (input wire ck, input wire rs, input wire [115:0] i, output wire [115:0] o);
    ot_hbm_rly #(.W(116), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail136 (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail138 (input wire ck, input wire rs, input wire [137:0] i, output wire [137:0] o);
    ot_hbm_rly #(.W(138), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail149 (input wire ck, input wire rs, input wire [148:0] i, output wire [148:0] o);
    ot_hbm_rly #(.W(149), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail162 (input wire ck, input wire rs, input wire [161:0] i, output wire [161:0] o);
    ot_hbm_rly #(.W(162), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail173 (input wire ck, input wire rs, input wire [172:0] i, output wire [172:0] o);
    ot_hbm_rly #(.W(173), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail184 (input wire ck, input wire rs, input wire [183:0] i, output wire [183:0] o);
    ot_hbm_rly #(.W(184), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail191 (input wire ck, input wire rs, input wire [190:0] i, output wire [190:0] o);
    ot_hbm_rly #(.W(191), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail206 (input wire ck, input wire rs, input wire [205:0] i, output wire [205:0] o);
    ot_hbm_rly #(.W(206), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail207 (input wire ck, input wire rs, input wire [206:0] i, output wire [206:0] o);
    ot_hbm_rly #(.W(207), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail213 (input wire ck, input wire rs, input wire [212:0] i, output wire [212:0] o);
    ot_hbm_rly #(.W(213), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail218 (input wire ck, input wire rs, input wire [217:0] i, output wire [217:0] o);
    ot_hbm_rly #(.W(218), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail256 (input wire ck, input wire rs, input wire [255:0] i, output wire [255:0] o);
    ot_hbm_rly #(.W(256), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail257 (input wire ck, input wire rs, input wire [256:0] i, output wire [256:0] o);
    ot_hbm_rly #(.W(257), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail258 (input wire ck, input wire rs, input wire [257:0] i, output wire [257:0] o);
    ot_hbm_rly #(.W(258), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail260 (input wire ck, input wire rs, input wire [259:0] i, output wire [259:0] o);
    ot_hbm_rly #(.W(260), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail264 (input wire ck, input wire rs, input wire [263:0] i, output wire [263:0] o);
    ot_hbm_rly #(.W(264), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail266 (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);
    ot_hbm_rly #(.W(266), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail271 (input wire ck, input wire rs, input wire [270:0] i, output wire [270:0] o);
    ot_hbm_rly #(.W(271), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail273 (input wire ck, input wire rs, input wire [272:0] i, output wire [272:0] o);
    ot_hbm_rly #(.W(273), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail277 (input wire ck, input wire rs, input wire [276:0] i, output wire [276:0] o);
    ot_hbm_rly #(.W(277), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail278 (input wire ck, input wire rs, input wire [277:0] i, output wire [277:0] o);
    ot_hbm_rly #(.W(278), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail279 (input wire ck, input wire rs, input wire [278:0] i, output wire [278:0] o);
    ot_hbm_rly #(.W(279), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail280 (input wire ck, input wire rs, input wire [279:0] i, output wire [279:0] o);
    ot_hbm_rly #(.W(280), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail281 (input wire ck, input wire rs, input wire [280:0] i, output wire [280:0] o);
    ot_hbm_rly #(.W(281), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail294 (input wire ck, input wire rs, input wire [293:0] i, output wire [293:0] o);
    ot_hbm_rly #(.W(294), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail296 (input wire ck, input wire rs, input wire [295:0] i, output wire [295:0] o);
    ot_hbm_rly #(.W(296), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail314 (input wire ck, input wire rs, input wire [313:0] i, output wire [313:0] o);
    ot_hbm_rly #(.W(314), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail319 (input wire ck, input wire rs, input wire [318:0] i, output wire [318:0] o);
    ot_hbm_rly #(.W(319), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail342 (input wire ck, input wire rs, input wire [341:0] i, output wire [341:0] o);
    ot_hbm_rly #(.W(342), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail351 (input wire ck, input wire rs, input wire [350:0] i, output wire [350:0] o);
    ot_hbm_rly #(.W(351), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail352 (input wire ck, input wire rs, input wire [351:0] i, output wire [351:0] o);
    ot_hbm_rly #(.W(352), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail376 (input wire ck, input wire rs, input wire [375:0] i, output wire [375:0] o);
    ot_hbm_rly #(.W(376), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail400 (input wire ck, input wire rs, input wire [399:0] i, output wire [399:0] o);
    ot_hbm_rly #(.W(400), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail401 (input wire ck, input wire rs, input wire [400:0] i, output wire [400:0] o);
    ot_hbm_rly #(.W(401), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail424 (input wire ck, input wire rs, input wire [423:0] i, output wire [423:0] o);
    ot_hbm_rly #(.W(424), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail441 (input wire ck, input wire rs, input wire [440:0] i, output wire [440:0] o);
    ot_hbm_rly #(.W(441), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail475 (input wire ck, input wire rs, input wire [474:0] i, output wire [474:0] o);
    ot_hbm_rly #(.W(475), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail496 (input wire ck, input wire rs, input wire [495:0] i, output wire [495:0] o);
    ot_hbm_rly #(.W(496), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail512 (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o);
    ot_hbm_rly #(.W(512), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail516 (input wire ck, input wire rs, input wire [515:0] i, output wire [515:0] o);
    ot_hbm_rly #(.W(516), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail520 (input wire ck, input wire rs, input wire [519:0] i, output wire [519:0] o);
    ot_hbm_rly #(.W(520), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail524 (input wire ck, input wire rs, input wire [523:0] i, output wire [523:0] o);
    ot_hbm_rly #(.W(524), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail528 (input wire ck, input wire rs, input wire [527:0] i, output wire [527:0] o);
    ot_hbm_rly #(.W(528), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail562 (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o);
    ot_hbm_rly #(.W(562), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail569 (input wire ck, input wire rs, input wire [568:0] i, output wire [568:0] o);
    ot_hbm_rly #(.W(569), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail586 (input wire ck, input wire rs, input wire [585:0] i, output wire [585:0] o);
    ot_hbm_rly #(.W(586), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tail596 (input wire ck, input wire rs, input wire [595:0] i, output wire [595:0] o);
    ot_hbm_rly #(.W(596), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail52 (input wire ck, input wire rs, input wire [51:0] i, output wire [51:0] o);
    ot_hbm_rly #(.W(52), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail55 (input wire ck, input wire rs, input wire [54:0] i, output wire [54:0] o);
    ot_hbm_rly #(.W(55), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail67 (input wire ck, input wire rs, input wire [66:0] i, output wire [66:0] o);
    ot_hbm_rly #(.W(67), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail83 (input wire ck, input wire rs, input wire [82:0] i, output wire [82:0] o);
    ot_hbm_rly #(.W(83), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail90 (input wire ck, input wire rs, input wire [89:0] i, output wire [89:0] o);
    ot_hbm_rly #(.W(90), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail108 (input wire ck, input wire rs, input wire [107:0] i, output wire [107:0] o);
    ot_hbm_rly #(.W(108), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail116 (input wire ck, input wire rs, input wire [115:0] i, output wire [115:0] o);
    ot_hbm_rly #(.W(116), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail120 (input wire ck, input wire rs, input wire [119:0] i, output wire [119:0] o);
    ot_hbm_rly #(.W(120), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail136 (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail138 (input wire ck, input wire rs, input wire [137:0] i, output wire [137:0] o);
    ot_hbm_rly #(.W(138), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail162 (input wire ck, input wire rs, input wire [161:0] i, output wire [161:0] o);
    ot_hbm_rly #(.W(162), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail173 (input wire ck, input wire rs, input wire [172:0] i, output wire [172:0] o);
    ot_hbm_rly #(.W(173), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail184 (input wire ck, input wire rs, input wire [183:0] i, output wire [183:0] o);
    ot_hbm_rly #(.W(184), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail191 (input wire ck, input wire rs, input wire [190:0] i, output wire [190:0] o);
    ot_hbm_rly #(.W(191), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail206 (input wire ck, input wire rs, input wire [205:0] i, output wire [205:0] o);
    ot_hbm_rly #(.W(206), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail207 (input wire ck, input wire rs, input wire [206:0] i, output wire [206:0] o);
    ot_hbm_rly #(.W(207), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail213 (input wire ck, input wire rs, input wire [212:0] i, output wire [212:0] o);
    ot_hbm_rly #(.W(213), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail257 (input wire ck, input wire rs, input wire [256:0] i, output wire [256:0] o);
    ot_hbm_rly #(.W(257), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail258 (input wire ck, input wire rs, input wire [257:0] i, output wire [257:0] o);
    ot_hbm_rly #(.W(258), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail260 (input wire ck, input wire rs, input wire [259:0] i, output wire [259:0] o);
    ot_hbm_rly #(.W(260), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail266 (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);
    ot_hbm_rly #(.W(266), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail271 (input wire ck, input wire rs, input wire [270:0] i, output wire [270:0] o);
    ot_hbm_rly #(.W(271), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail273 (input wire ck, input wire rs, input wire [272:0] i, output wire [272:0] o);
    ot_hbm_rly #(.W(273), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail277 (input wire ck, input wire rs, input wire [276:0] i, output wire [276:0] o);
    ot_hbm_rly #(.W(277), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail278 (input wire ck, input wire rs, input wire [277:0] i, output wire [277:0] o);
    ot_hbm_rly #(.W(278), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail279 (input wire ck, input wire rs, input wire [278:0] i, output wire [278:0] o);
    ot_hbm_rly #(.W(279), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail280 (input wire ck, input wire rs, input wire [279:0] i, output wire [279:0] o);
    ot_hbm_rly #(.W(280), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail281 (input wire ck, input wire rs, input wire [280:0] i, output wire [280:0] o);
    ot_hbm_rly #(.W(281), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail294 (input wire ck, input wire rs, input wire [293:0] i, output wire [293:0] o);
    ot_hbm_rly #(.W(294), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail296 (input wire ck, input wire rs, input wire [295:0] i, output wire [295:0] o);
    ot_hbm_rly #(.W(296), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail298 (input wire ck, input wire rs, input wire [297:0] i, output wire [297:0] o);
    ot_hbm_rly #(.W(298), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail314 (input wire ck, input wire rs, input wire [313:0] i, output wire [313:0] o);
    ot_hbm_rly #(.W(314), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail342 (input wire ck, input wire rs, input wire [341:0] i, output wire [341:0] o);
    ot_hbm_rly #(.W(342), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail352 (input wire ck, input wire rs, input wire [351:0] i, output wire [351:0] o);
    ot_hbm_rly #(.W(352), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail376 (input wire ck, input wire rs, input wire [375:0] i, output wire [375:0] o);
    ot_hbm_rly #(.W(376), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail400 (input wire ck, input wire rs, input wire [399:0] i, output wire [399:0] o);
    ot_hbm_rly #(.W(400), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail424 (input wire ck, input wire rs, input wire [423:0] i, output wire [423:0] o);
    ot_hbm_rly #(.W(424), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail441 (input wire ck, input wire rs, input wire [440:0] i, output wire [440:0] o);
    ot_hbm_rly #(.W(441), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail475 (input wire ck, input wire rs, input wire [474:0] i, output wire [474:0] o);
    ot_hbm_rly #(.W(475), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail496 (input wire ck, input wire rs, input wire [495:0] i, output wire [495:0] o);
    ot_hbm_rly #(.W(496), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail512 (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o);
    ot_hbm_rly #(.W(512), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail516 (input wire ck, input wire rs, input wire [515:0] i, output wire [515:0] o);
    ot_hbm_rly #(.W(516), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail524 (input wire ck, input wire rs, input wire [523:0] i, output wire [523:0] o);
    ot_hbm_rly #(.W(524), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail562 (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o);
    ot_hbm_rly #(.W(562), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail569 (input wire ck, input wire rs, input wire [568:0] i, output wire [568:0] o);
    ot_hbm_rly #(.W(569), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail586 (input wire ck, input wire rs, input wire [585:0] i, output wire [585:0] o);
    ot_hbm_rly #(.W(586), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail594 (input wire ck, input wire rs, input wire [593:0] i, output wire [593:0] o);
    ot_hbm_rly #(.W(594), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tail596 (input wire ck, input wire rs, input wire [595:0] i, output wire [595:0] o);
    ot_hbm_rly #(.W(596), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
`default_nettype wire
