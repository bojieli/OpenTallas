// STM-DQ EQ gate (DIE-QC-97 11-10): the qfd_dv_s6_stm stream half, DEFAULT (u_rl 2-stage landing -> unchanged tile)
// vs OT_QC_STMDQ (raw rst_n -> STM-DQ tile).  GENERATED wrappers for stmdq_eq.ys; tile sources renamed by stmdq_eq.sh.
`timescale 1ns/1ps
module qfd_dv_s5_rst2_eq (input wire ck, input wire rst_n, output wire rst);   // = qfd_dv_s5_rst2, verbatim body
    reg rs1, rs2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rs2 <= 1'b0; end
        else begin rs1 <= 1'b1; rs2 <= rs1; end
    assign rst = rs2;
endmodule
module stm_half_def (
    input wire  ck,
    input wire  rst_n,
    input wire [3:0] sid,
    input wire  cfg_v,
    input wire [1:0] cfg_dir,
    input wire [27:0] cfg_tag,
    input wire [543:0] sw_lo,
    input wire  sw_v,
    input wire [542:0] sw_hi,
    input wire [543:0] se_lo,
    input wire  se_v,
    input wire [542:0] se_hi,
    output wire [1087:0] so_e,
    output wire [1087:0] so_w,
    input wire [7:0] xw_we,
    input wire [191:0] xw_addr,
    input wire [255:0] xw_data,
    output wire  tw_we,
    output wire [1:0] tw_kind,
    output wire [23:0] tw_addr,
    output wire [511:0] tw_data_lo,
    output wire [511:0] tw_data_hi,
    output wire  xt_v,
    output wire [23:0] xt_a,
    output wire [511:0] xt_d_lo,
    output wire [511:0] xt_d_hi,
    output wire  xt_bad,
    output wire  fault
);
    wire rst_l;
    qfd_dv_s5_rst2_eq u_rl (.ck(ck), .rst_n(rst_n), .rst(rst_l));
    qfd_dv_stream_tile_def u_t (.ck(ck),.rst_n(rst_l),.sid(sid),.cfg_v(cfg_v),.cfg_dir(cfg_dir),.cfg_tag(cfg_tag),.sw_lo(sw_lo),.sw_v(sw_v),.sw_hi(sw_hi),.se_lo(se_lo),.se_v(se_v),.se_hi(se_hi),.so_e(so_e),.so_w(so_w),.xw_we(xw_we),.xw_addr(xw_addr),.xw_data(xw_data),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data_lo(tw_data_lo),.tw_data_hi(tw_data_hi),.xt_v(xt_v),.xt_a(xt_a),.xt_d_lo(xt_d_lo),.xt_d_hi(xt_d_hi),.xt_bad(xt_bad),.fault(fault));
endmodule
module stm_half_dq (
    input wire  ck,
    input wire  rst_n,
    input wire [3:0] sid,
    input wire  cfg_v,
    input wire [1:0] cfg_dir,
    input wire [27:0] cfg_tag,
    input wire [543:0] sw_lo,
    input wire  sw_v,
    input wire [542:0] sw_hi,
    input wire [543:0] se_lo,
    input wire  se_v,
    input wire [542:0] se_hi,
    output wire [1087:0] so_e,
    output wire [1087:0] so_w,
    input wire [7:0] xw_we,
    input wire [191:0] xw_addr,
    input wire [255:0] xw_data,
    output wire  tw_we,
    output wire [1:0] tw_kind,
    output wire [23:0] tw_addr,
    output wire [511:0] tw_data_lo,
    output wire [511:0] tw_data_hi,
    output wire  xt_v,
    output wire [23:0] xt_a,
    output wire [511:0] xt_d_lo,
    output wire [511:0] xt_d_hi,
    output wire  xt_bad,
    output wire  fault
);
    qfd_dv_stream_tile_dq u_t (.ck(ck),.rst_n(rst_n),.sid(sid),.cfg_v(cfg_v),.cfg_dir(cfg_dir),.cfg_tag(cfg_tag),.sw_lo(sw_lo),.sw_v(sw_v),.sw_hi(sw_hi),.se_lo(se_lo),.se_v(se_v),.se_hi(se_hi),.so_e(so_e),.so_w(so_w),.xw_we(xw_we),.xw_addr(xw_addr),.xw_data(xw_data),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data_lo(tw_data_lo),.tw_data_hi(tw_data_hi),.xt_v(xt_v),.xt_a(xt_a),.xt_d_lo(xt_d_lo),.xt_d_hi(xt_d_hi),.xt_bad(xt_bad),.fault(fault));
endmodule
module stm_half_se0_def (
    input wire  ck,
    input wire  rst_n,
    input wire [3:0] sid,
    input wire  cfg_v,
    input wire [1:0] cfg_dir,
    input wire [27:0] cfg_tag,
    input wire [543:0] sw_lo,
    input wire  sw_v,
    input wire [542:0] sw_hi,
    output wire [1087:0] so_e,
    output wire [1087:0] so_w,
    input wire [7:0] xw_we,
    input wire [191:0] xw_addr,
    input wire [255:0] xw_data,
    output wire  tw_we,
    output wire [1:0] tw_kind,
    output wire [23:0] tw_addr,
    output wire [511:0] tw_data_lo,
    output wire [511:0] tw_data_hi,
    output wire  xt_v,
    output wire [23:0] xt_a,
    output wire [511:0] xt_d_lo,
    output wire [511:0] xt_d_hi,
    output wire  xt_bad,
    output wire  fault
);
    wire rst_l;
    qfd_dv_s5_rst2_eq u_rl (.ck(ck), .rst_n(rst_n), .rst(rst_l));
    qfd_dv_stream_tile_se0_def u_t (.ck(ck),.rst_n(rst_l),.sid(sid),.cfg_v(cfg_v),.cfg_dir(cfg_dir),.cfg_tag(cfg_tag),.sw_lo(sw_lo),.sw_v(sw_v),.sw_hi(sw_hi),.so_e(so_e),.so_w(so_w),.xw_we(xw_we),.xw_addr(xw_addr),.xw_data(xw_data),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data_lo(tw_data_lo),.tw_data_hi(tw_data_hi),.xt_v(xt_v),.xt_a(xt_a),.xt_d_lo(xt_d_lo),.xt_d_hi(xt_d_hi),.xt_bad(xt_bad),.fault(fault));
endmodule
module stm_half_se0_dq (
    input wire  ck,
    input wire  rst_n,
    input wire [3:0] sid,
    input wire  cfg_v,
    input wire [1:0] cfg_dir,
    input wire [27:0] cfg_tag,
    input wire [543:0] sw_lo,
    input wire  sw_v,
    input wire [542:0] sw_hi,
    output wire [1087:0] so_e,
    output wire [1087:0] so_w,
    input wire [7:0] xw_we,
    input wire [191:0] xw_addr,
    input wire [255:0] xw_data,
    output wire  tw_we,
    output wire [1:0] tw_kind,
    output wire [23:0] tw_addr,
    output wire [511:0] tw_data_lo,
    output wire [511:0] tw_data_hi,
    output wire  xt_v,
    output wire [23:0] xt_a,
    output wire [511:0] xt_d_lo,
    output wire [511:0] xt_d_hi,
    output wire  xt_bad,
    output wire  fault
);
    qfd_dv_stream_tile_se0_dq u_t (.ck(ck),.rst_n(rst_n),.sid(sid),.cfg_v(cfg_v),.cfg_dir(cfg_dir),.cfg_tag(cfg_tag),.sw_lo(sw_lo),.sw_v(sw_v),.sw_hi(sw_hi),.so_e(so_e),.so_w(so_w),.xw_we(xw_we),.xw_addr(xw_addr),.xw_data(xw_data),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data_lo(tw_data_lo),.tw_data_hi(tw_data_hi),.xt_v(xt_v),.xt_a(xt_a),.xt_d_lo(xt_d_lo),.xt_d_hi(xt_d_hi),.xt_bad(xt_bad),.fault(fault));
endmodule
