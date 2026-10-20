`timescale 1ns/1ps
`default_nettype none
module hbfd_land0_136_NS_tw #(parameter integer TW = 136) (input wire ck_s, input wire en, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_136_SN_tw #(parameter integer TW = 136) (input wire ck_s, input wire en, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_136_WE_tw #(parameter integer TW = 136) (input wire ck_s, input wire en, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land0_48_NS_tw #(parameter integer TW = 48) (input wire ck_s, input wire en, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(1)) u_land (.ckf(ck_s), .ea(en), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_EW_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_NS_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_SN_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_136_WE_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_EW_tw #(parameter integer TW = 48) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_NS_tw #(parameter integer TW = 48) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_SN_tw #(parameter integer TW = 48) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_48_WE_tw #(parameter integer TW = 48) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_EW_tw #(parameter integer TW = 624) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_NS_tw #(parameter integer TW = 624) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_SN_tw #(parameter integer TW = 624) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_land_624_WE_tw #(parameter integer TW = 624) (input wire ckf, input wire ea, input wire [TW-1:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire [TW-1:0] b, output wire fault);
    ot_qfd_land #(.W(TW), .D(4), .FIRST(0)) u_land (.ckf(ckf), .ea(ea), .i(a), .ck(ck), .rs(rs), .k({k2, k1, k0}), .o(b), .fault(fault));
endmodule
module hbfd_lh0_136_EW_tw #(parameter integer TW = 136) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_f2_tw #(parameter integer TW = 136) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [2*TW-1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(2), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_EW_f3_tw #(parameter integer TW = 136) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [3*TW-1:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(3), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_tw #(parameter integer TW = 136) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_NS_f3_tw #(parameter integer TW = 136) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [3*TW-1:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(3), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_tw #(parameter integer TW = 136) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_SN_f3_tw #(parameter integer TW = 136) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [3*TW-1:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(3), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_136_WE_tw #(parameter integer TW = 136) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_EW_tw #(parameter integer TW = 48) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_NS_tw #(parameter integer TW = 48) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_SN_tw #(parameter integer TW = 48) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_48_WE_tw #(parameter integer TW = 48) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_EW_tw #(parameter integer TW = 624) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_NS_tw #(parameter integer TW = 624) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_SN_tw #(parameter integer TW = 624) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh0_624_WE_tw #(parameter integer TW = 624) (input wire ck, input wire en, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(1), .FIRST(1)) u_st (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f2_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [2*TW-1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_EW_f3_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [3*TW-1:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f2_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [2*TW-1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_NS_f3_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [3*TW-1:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f2_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [2*TW-1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_SN_f3_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [3*TW-1:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f2_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [2*TW-1:0] b, output wire [1:0] eb, output wire [1:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(2), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_136_WE_f3_tw #(parameter integer TW = 136) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [3*TW-1:0] b, output wire [2:0] eb, output wire [2:0] ck_o);
    ot_hbm_lane_stf #(.W(TW), .N(3), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_EW_tw #(parameter integer TW = 48) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_NS_tw #(parameter integer TW = 48) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_SN_tw #(parameter integer TW = 48) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_48_WE_tw #(parameter integer TW = 48) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_EW_tw #(parameter integer TW = 624) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_NS_tw #(parameter integer TW = 624) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_SN_tw #(parameter integer TW = 624) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_lh_624_WE_tw #(parameter integer TW = 624) (input wire ckf, input wire ea, input wire [TW-1:0] a, output wire [TW-1:0] b, output wire eb, output wire ck_o);
    ot_qfd_lane_st #(.W(TW), .FIRST(0)) u_st (.ck(ckf), .en(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module hbfd_rly_136_WE_tw #(parameter integer TW = 136) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_EW_tw #(parameter integer TW = 48) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_NS_tw #(parameter integer TW = 48) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_SN_tw #(parameter integer TW = 48) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_48_WE_tw #(parameter integer TW = 48) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_EW_tw #(parameter integer TW = 624) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_NS_tw #(parameter integer TW = 624) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_SN_tw #(parameter integer TW = 624) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module hbfd_rly_624_WE_tw #(parameter integer TW = 624) (input wire ck, input wire rs, input wire [TW-1:0] i, output wire [TW-1:0] o);
    ot_hbm_rly #(.W(TW), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
`default_nettype wire
