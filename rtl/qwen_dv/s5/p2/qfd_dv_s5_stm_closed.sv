`timescale 1ns/1ps
// Closed c3r stream and ns4 tload child binding; adapter/parent remains UNCLOSED.
module qfd_dv_s5_stm_closed #(parameter integer HARD = 1, parameter integer MUT = 0, parameter integer TSLICE = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,
    input  wire [30:0]    stm_cfg,
    input  wire [1087:0]  sw_i,
    input  wire [1087:0]  se_i,
    output wire [1087:0]  so_e,
    output wire [1087:0]  so_w,
    input  wire [7:0]     vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire [8:0]     treq_i,
    output wire           tw_we,
    output wire [1:0]     tw_kind,
    output wire [23:0]    tw_addr,
    output wire [1023:0]  tw_data,
    output wire           xt_v,
    output wire [23:0]    xt_a,
    output wire [1023:0]  xt_d,
    output wire           xt_bad,
    output wire           stm_fault,
    output wire           tld_fault
);
    wire rst;
    // Preserve the existing stm adapter reset run before each child's own landing.
    qfd_dv_s5_rst2 u_rl(.ck(ck),.rst_n(rst_n),.rst(rst));
    wire[7:0]su_x_we=(|vm_we&&vm_waddr[23:22]==2'b01)?vm_we:8'd0;
    wire s_we;wire[1:0]s_kind;wire[23:0]s_addr;wire[1023:0]s_data;
    qfd_dv_stream_tile u_stream(.ck(ck),.rst_n(rst),.sid(sid),
        .cfg_v(stm_cfg[30]),.cfg_dir(stm_cfg[29:28]),.cfg_tag(stm_cfg[27:0]),
        .sw_lo(sw_i[543:0]),.sw_hi(sw_i[1086:544]),.sw_v(sw_i[1087]),
        .se_lo(se_i[543:0]),.se_hi(se_i[1086:544]),.se_v(se_i[1087]),
        .so_e(so_e),.so_w(so_w),.xw_we(su_x_we),.xw_addr(vm_waddr),.xw_data(vm_wdata),
        .tw_we(s_we),.tw_kind(s_kind),.tw_addr(s_addr),.tw_data_lo(s_data[511:0]),.tw_data_hi(s_data[1023:512]),
        .xt_v(xt_v),.xt_a(xt_a),.xt_d_lo(xt_d[511:0]),.xt_d_hi(xt_d[1023:512]),.xt_bad(xt_bad),.fault(stm_fault));
    wire j_we;wire[1:0]j_kind;wire[23:0]j_addr;wire[1023:0]j_data;
    qfd_dv_slice_tload #(.SLICE(TSLICE),.CAPTURE_STAGE(1),.LOCAL_JOIN(1)) u_tload(
        .ck(ck),.rst_n(rst),.treq(treq_i),.s_we(s_we),.s_kind(s_kind),.s_addr(s_addr),.s_data(s_data),
        .tw_we(j_we),.tw_kind(j_kind),.tw_addr(j_addr),.tw_data(j_data),.busy(),.done(),.fault(tld_fault));
    // Original HARD parent table-write publication retained, payload/reset policy unchanged.
    reg twv;reg[1:0]twk;reg[23:0]twa;reg[1023:0]twd;
    always @(posedge ck or negedge rst)if(!rst)twv<=0;else twv<=j_we;
    always @(posedge ck)begin twk<=j_kind;twa<=j_addr;twd<=j_data;end
    assign tw_we=twv;assign tw_kind=twk;assign tw_addr=twa;assign tw_data=twd;
endmodule
