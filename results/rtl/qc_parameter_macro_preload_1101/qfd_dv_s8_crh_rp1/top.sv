module top (
    input wire ck,
    input wire rst_n,
    input wire [7:0] cr_re,
    input wire [191:0] cr_addr,
    output wire [255:0] q,
    input wire tw_we,
    input wire [1:0] tw_kind,
    input wire [23:0] tw_addr,
    input wire [511:0] tw_d,
    output wire fault
);
qfd_dv_s8_crh_rp1 #(.MIF(0)) u_child (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .q(q), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(tw_d), .fault(fault));
endmodule
