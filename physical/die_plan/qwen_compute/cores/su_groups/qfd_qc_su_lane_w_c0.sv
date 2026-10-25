// Grouped unchanged verified bound children; +0 cycles.
`default_nettype none
module qfd_qc_su_lane_w_c0 (
    input wire clk,
    input wire rst_n,
    input wire [759:0] c_i,
    output wire [245:0] c_o,
    output wire [113:0] ctl_o,
    output wire [34:0] sc_o,
    output wire [56:0] stm_o
);
    wire [0:0] w_exp_fault;
    wire [0:0] w_exp_vo;
    wire [31:0] w_exp_y;
    wire [23:0] w_head_crom_addr;
    wire [0:0] w_head_crom_re;
    wire [23:0] w_head_kv_waddr;
    wire [31:0] w_head_kv_wdata;
    wire [0:0] w_head_kv_we;
    wire [0:0] w_head_l_fault;
    wire [0:0] w_head_l_last;
    wire [31:0] w_head_l_out;
    wire [0:0] w_head_l_ov;
    wire [23:0] w_head_l_raddr;
    wire [1:0] w_head_l_red;
    wire [0:0] w_head_l_redsq;
    wire [0:0] w_head_retire;
    wire [0:0] w_head_sx_exp_v;
    wire [31:0] w_head_sx_exp_x;
    wire [0:0] w_head_sx_rcp_v;
    wire [31:0] w_head_sx_rcp_x;
    wire [0:0] w_head_sx_rsq_v;
    wire [31:0] w_head_sx_rsq_x;
    wire [23:0] w_head_va_addr;
    wire [0:0] w_head_va_re;
    wire [23:0] w_head_vb_addr;
    wire [0:0] w_head_vb_re;
    wire [23:0] w_head_vc_addr;
    wire [0:0] w_head_vc_re;
    wire [23:0] w_head_vm_waddr;
    wire [31:0] w_head_vm_wdata;
    wire [0:0] w_head_vm_we;
    wire [23:0] w_head_wrom_addr;
    wire [0:0] w_head_wrom_re;
    wire [0:0] w_lrly_c_accept;
    wire [2:0] w_lrly_c_ad;
    wire [23:0] w_lrly_c_asi;
    wire [0:0] w_lrly_c_asrc;
    wire [23:0] w_lrly_c_bsi;
    wire [0:0] w_lrly_c_bsrc;
    wire [2:0] w_lrly_c_cls;
    wire [63:0] w_lrly_c_crom;
    wire [23:0] w_lrly_c_csi;
    wire [0:0] w_lrly_c_csrc;
    wire [23:0] w_lrly_c_cura;
    wire [23:0] w_lrly_c_curb;
    wire [23:0] w_lrly_c_curc;
    wire [23:0] w_lrly_c_curd;
    wire [23:0] w_lrly_c_dsi;
    wire [1:0] w_lrly_c_dst;
    wire [0:0] w_lrly_c_emit0;
    wire [18:0] w_lrly_c_fin_th;
    wire [17:0] w_lrly_c_i;
    wire [0:0] w_lrly_c_ilast;
    wire [31:0] w_lrly_c_imm1;
    wire [31:0] w_lrly_c_imm2;
    wire [2:0] w_lrly_c_isfu;
    wire [0:0] w_lrly_c_live;
    wire [1:0] w_lrly_c_ma;
    wire [1:0] w_lrly_c_mb;
    wire [0:0] w_lrly_c_mc;
    wire [0:0] w_lrly_c_md;
    wire [1:0] w_lrly_c_red;
    wire [0:0] w_lrly_c_redsq;
    wire [23:0] w_lrly_c_rrow;
    wire [31:0] w_lrly_c_va;
    wire [31:0] w_lrly_c_vb;
    wire [31:0] w_lrly_c_vc;
    wire [255:0] w_lrly_c_wrom;
    wire [23:0] w_lrly_crom_addr;
    wire [0:0] w_lrly_crom_re;
    wire [0:0] w_lrly_h_rst_n;
    wire [23:0] w_lrly_kv_waddr;
    wire [31:0] w_lrly_kv_wdata;
    wire [0:0] w_lrly_kv_we;
    wire [0:0] w_lrly_l_fault;
    wire [0:0] w_lrly_l_last;
    wire [31:0] w_lrly_l_out;
    wire [0:0] w_lrly_l_ov;
    wire [23:0] w_lrly_l_raddr;
    wire [1:0] w_lrly_l_red;
    wire [0:0] w_lrly_l_redsq;
    wire [0:0] w_lrly_retire;
    wire [23:0] w_lrly_va_addr;
    wire [0:0] w_lrly_va_re;
    wire [23:0] w_lrly_vb_addr;
    wire [0:0] w_lrly_vb_re;
    wire [23:0] w_lrly_vc_addr;
    wire [0:0] w_lrly_vc_re;
    wire [23:0] w_lrly_vm_waddr;
    wire [31:0] w_lrly_vm_wdata;
    wire [0:0] w_lrly_vm_we;
    wire [23:0] w_lrly_wrom_addr;
    wire [0:0] w_lrly_wrom_re;
    wire [0:0] w_rcp_fault;
    wire [0:0] w_rcp_vo;
    wire [31:0] w_rcp_y;
    wire [0:0] w_rsq_fault;
    wire [0:0] w_rsq_vo;
    wire [31:0] w_rsq_y;
    ot_hdc_sfu_exp_t u_exp (
        .clk(clk),
        .fault(w_exp_fault),
        .rst_n(rst_n),
        .v(w_head_sx_exp_v[0]),
        .vo(w_exp_vo),
        .x(w_head_sx_exp_x[31:0]),
        .y(w_exp_y)
    );
    qfd_dv_lane_h_safe2 u_head (
        .accept(w_lrly_c_accept[0]),
        .ad(w_lrly_c_ad[2:0]),
        .asi(w_lrly_c_asi[23:0]),
        .asrc(w_lrly_c_asrc[0]),
        .bsi(w_lrly_c_bsi[23:0]),
        .bsrc(w_lrly_c_bsrc[0]),
        .clk(clk),
        .cls(w_lrly_c_cls[2:0]),
        .crom_addr(w_head_crom_addr),
        .crom_q(w_lrly_c_crom[63:0]),
        .crom_re(w_head_crom_re),
        .csi(w_lrly_c_csi[23:0]),
        .csrc(w_lrly_c_csrc[0]),
        .cura0(w_lrly_c_cura[23:0]),
        .curb0(w_lrly_c_curb[23:0]),
        .curc0(w_lrly_c_curc[23:0]),
        .curd0(w_lrly_c_curd[23:0]),
        .dsi(w_lrly_c_dsi[23:0]),
        .dst(w_lrly_c_dst[1:0]),
        .emit0(w_lrly_c_emit0[0]),
        .fin_th(w_lrly_c_fin_th[18:0]),
        .i(w_lrly_c_i[17:0]),
        .i_last_r(w_lrly_c_ilast[0]),
        .i_sfu(w_lrly_c_isfu[2:0]),
        .imm1(w_lrly_c_imm1[31:0]),
        .imm2(w_lrly_c_imm2[31:0]),
        .kv_waddr(w_head_kv_waddr),
        .kv_wdata(w_head_kv_wdata),
        .kv_we(w_head_kv_we),
        .l_fault(w_head_l_fault),
        .l_last(w_head_l_last),
        .l_out(w_head_l_out),
        .l_ov(w_head_l_ov),
        .l_raddr(w_head_l_raddr),
        .l_red(w_head_l_red),
        .l_redsq(w_head_l_redsq),
        .live(w_lrly_c_live[0]),
        .ma(w_lrly_c_ma[1:0]),
        .mb(w_lrly_c_mb[1:0]),
        .mc(w_lrly_c_mc[0]),
        .md(w_lrly_c_md[0]),
        .red(w_lrly_c_red[1:0]),
        .redsq(w_lrly_c_redsq[0]),
        .retire(w_head_retire),
        .rrow(w_lrly_c_rrow[23:0]),
        .rst_n(rst_n),
        .sx_exp_v(w_head_sx_exp_v),
        .sx_exp_x(w_head_sx_exp_x),
        .sx_rcp_v(w_head_sx_rcp_v),
        .sx_rcp_x(w_head_sx_rcp_x),
        .sx_rsq_v(w_head_sx_rsq_v),
        .sx_rsq_x(w_head_sx_rsq_x),
        .sy_exp_f(w_exp_fault[0]),
        .sy_exp_vo(w_exp_vo[0]),
        .sy_exp_y(w_exp_y[31:0]),
        .sy_rcp_f(w_rcp_fault[0]),
        .sy_rcp_y(w_rcp_y[31:0]),
        .sy_rsq_f(w_rsq_fault[0]),
        .sy_rsq_y(w_rsq_y[31:0]),
        .va_addr(w_head_va_addr),
        .va_q(w_lrly_c_va[31:0]),
        .va_re(w_head_va_re),
        .vb_addr(w_head_vb_addr),
        .vb_q(w_lrly_c_vb[31:0]),
        .vb_re(w_head_vb_re),
        .vc_addr(w_head_vc_addr),
        .vc_q(w_lrly_c_vc[31:0]),
        .vc_re(w_head_vc_re),
        .vm_waddr(w_head_vm_waddr),
        .vm_wdata(w_head_vm_wdata),
        .vm_we(w_head_vm_we),
        .wrom_addr(w_head_wrom_addr),
        .wrom_q(w_lrly_c_wrom[255:0]),
        .wrom_re(w_head_wrom_re)
    );
    qfd_dv_s5_lrly u_lrly (
        .c_accept(w_lrly_c_accept),
        .c_ad(w_lrly_c_ad),
        .c_asi(w_lrly_c_asi),
        .c_asrc(w_lrly_c_asrc),
        .c_bsi(w_lrly_c_bsi),
        .c_bsrc(w_lrly_c_bsrc),
        .c_cls(w_lrly_c_cls),
        .c_crom(w_lrly_c_crom),
        .c_csi(w_lrly_c_csi),
        .c_csrc(w_lrly_c_csrc),
        .c_cura(w_lrly_c_cura),
        .c_curb(w_lrly_c_curb),
        .c_curc(w_lrly_c_curc),
        .c_curd(w_lrly_c_curd),
        .c_dsi(w_lrly_c_dsi),
        .c_dst(w_lrly_c_dst),
        .c_emit0(w_lrly_c_emit0),
        .c_fin_th(w_lrly_c_fin_th),
        .c_i(w_lrly_c_i),
        .c_ilast(w_lrly_c_ilast),
        .c_imm1(w_lrly_c_imm1),
        .c_imm2(w_lrly_c_imm2),
        .c_isfu(w_lrly_c_isfu),
        .c_live(w_lrly_c_live),
        .c_ma(w_lrly_c_ma),
        .c_mb(w_lrly_c_mb),
        .c_mc(w_lrly_c_mc),
        .c_md(w_lrly_c_md),
        .c_red(w_lrly_c_red),
        .c_redsq(w_lrly_c_redsq),
        .c_rrow(w_lrly_c_rrow),
        .c_va(w_lrly_c_va),
        .c_vb(w_lrly_c_vb),
        .c_vc(w_lrly_c_vc),
        .c_wrom(w_lrly_c_wrom),
        .ck(clk),
        .cr_q(c_i[0 +: 64]),
        .crom_addr(w_lrly_crom_addr),
        .crom_re(w_lrly_crom_re),
        .gb(c_i[64 +: 500]),
        .gv(c_i[564 +: 3]),
        .h_crom_addr(w_head_crom_addr[23:0]),
        .h_crom_re(w_head_crom_re[0]),
        .h_kv_waddr(w_head_kv_waddr[23:0]),
        .h_kv_wdata(w_head_kv_wdata[31:0]),
        .h_kv_we(w_head_kv_we[0]),
        .h_l_fault(w_head_l_fault[0]),
        .h_l_last(w_head_l_last[0]),
        .h_l_out(w_head_l_out[31:0]),
        .h_l_ov(w_head_l_ov[0]),
        .h_l_raddr(w_head_l_raddr[23:0]),
        .h_l_red(w_head_l_red[1:0]),
        .h_l_redsq(w_head_l_redsq[0]),
        .h_retire(w_head_retire[0]),
        .h_rst_n(w_lrly_h_rst_n),
        .h_va_addr(w_head_va_addr[23:0]),
        .h_va_re(w_head_va_re[0]),
        .h_vb_addr(w_head_vb_addr[23:0]),
        .h_vb_re(w_head_vb_re[0]),
        .h_vc_addr(w_head_vc_addr[23:0]),
        .h_vc_re(w_head_vc_re[0]),
        .h_vm_waddr(w_head_vm_waddr[23:0]),
        .h_vm_wdata(w_head_vm_wdata[31:0]),
        .h_vm_we(w_head_vm_we[0]),
        .h_wrom_addr(w_head_wrom_addr[23:0]),
        .h_wrom_re(w_head_wrom_re[0]),
        .kv_waddr(w_lrly_kv_waddr),
        .kv_wdata(w_lrly_kv_wdata),
        .kv_we(w_lrly_kv_we),
        .l_fault(w_lrly_l_fault),
        .l_last(w_lrly_l_last),
        .l_out(w_lrly_l_out),
        .l_ov(w_lrly_l_ov),
        .l_raddr(w_lrly_l_raddr),
        .l_red(w_lrly_l_red),
        .l_redsq(w_lrly_l_redsq),
        .lv1(c_i[567 +: 1]),
        .pd1(c_i[568 +: 96]),
        .retire(w_lrly_retire),
        .rst_n(rst_n),
        .va_addr(w_lrly_va_addr),
        .va_q(c_i[664 +: 32]),
        .va_re(w_lrly_va_re),
        .vb_addr(w_lrly_vb_addr),
        .vb_q(c_i[696 +: 32]),
        .vb_re(w_lrly_vb_re),
        .vc_addr(w_lrly_vc_addr),
        .vc_q(c_i[728 +: 32]),
        .vc_re(w_lrly_vc_re),
        .vm_waddr(w_lrly_vm_waddr),
        .vm_wdata(w_lrly_vm_wdata),
        .vm_we(w_lrly_vm_we),
        .wrom_addr(w_lrly_wrom_addr),
        .wrom_re(w_lrly_wrom_re)
    );
    ot_hdc_sfu_rcp_t u_rcp (
        .clk(clk),
        .fault(w_rcp_fault),
        .rst_n(rst_n),
        .v(w_head_sx_rcp_v[0]),
        .vo(w_rcp_vo),
        .x(w_head_sx_rcp_x[31:0]),
        .y(w_rcp_y)
    );
    ot_hdc_sfu_rsq_t u_rsq (
        .clk(clk),
        .fault(w_rsq_fault),
        .rst_n(rst_n),
        .v(w_head_sx_rsq_v[0]),
        .vo(w_rsq_vo),
        .x(w_head_sx_rsq_x[31:0]),
        .y(w_rsq_y)
    );
    assign c_o = {w_lrly_wrom_re[0], w_lrly_wrom_addr[23], w_lrly_wrom_addr[22], w_lrly_wrom_addr[21], w_lrly_wrom_addr[20], w_lrly_wrom_addr[19], w_lrly_wrom_addr[18], w_lrly_wrom_addr[17], w_lrly_wrom_addr[16], w_lrly_wrom_addr[15], w_lrly_wrom_addr[14], w_lrly_wrom_addr[13], w_lrly_wrom_addr[12], w_lrly_wrom_addr[11], w_lrly_wrom_addr[10], w_lrly_wrom_addr[9], w_lrly_wrom_addr[8], w_lrly_wrom_addr[7], w_lrly_wrom_addr[6], w_lrly_wrom_addr[5], w_lrly_wrom_addr[4], w_lrly_wrom_addr[3], w_lrly_wrom_addr[2], w_lrly_wrom_addr[1], w_lrly_wrom_addr[0], w_lrly_vm_we[0], w_lrly_vm_wdata[31], w_lrly_vm_wdata[30], w_lrly_vm_wdata[29], w_lrly_vm_wdata[28], w_lrly_vm_wdata[27], w_lrly_vm_wdata[26], w_lrly_vm_wdata[25], w_lrly_vm_wdata[24], w_lrly_vm_wdata[23], w_lrly_vm_wdata[22], w_lrly_vm_wdata[21], w_lrly_vm_wdata[20], w_lrly_vm_wdata[19], w_lrly_vm_wdata[18], w_lrly_vm_wdata[17], w_lrly_vm_wdata[16], w_lrly_vm_wdata[15], w_lrly_vm_wdata[14], w_lrly_vm_wdata[13], w_lrly_vm_wdata[12], w_lrly_vm_wdata[11], w_lrly_vm_wdata[10], w_lrly_vm_wdata[9], w_lrly_vm_wdata[8], w_lrly_vm_wdata[7], w_lrly_vm_wdata[6], w_lrly_vm_wdata[5], w_lrly_vm_wdata[4], w_lrly_vm_wdata[3], w_lrly_vm_wdata[2], w_lrly_vm_wdata[1], w_lrly_vm_wdata[0], w_lrly_vm_waddr[23], w_lrly_vm_waddr[22], w_lrly_vm_waddr[21], w_lrly_vm_waddr[20], w_lrly_vm_waddr[19], w_lrly_vm_waddr[18], w_lrly_vm_waddr[17], w_lrly_vm_waddr[16], w_lrly_vm_waddr[15], w_lrly_vm_waddr[14], w_lrly_vm_waddr[13], w_lrly_vm_waddr[12], w_lrly_vm_waddr[11], w_lrly_vm_waddr[10], w_lrly_vm_waddr[9], w_lrly_vm_waddr[8], w_lrly_vm_waddr[7], w_lrly_vm_waddr[6], w_lrly_vm_waddr[5], w_lrly_vm_waddr[4], w_lrly_vm_waddr[3], w_lrly_vm_waddr[2], w_lrly_vm_waddr[1], w_lrly_vm_waddr[0], w_lrly_vc_re[0], w_lrly_vc_addr[23], w_lrly_vc_addr[22], w_lrly_vc_addr[21], w_lrly_vc_addr[20], w_lrly_vc_addr[19], w_lrly_vc_addr[18], w_lrly_vc_addr[17], w_lrly_vc_addr[16], w_lrly_vc_addr[15], w_lrly_vc_addr[14], w_lrly_vc_addr[13], w_lrly_vc_addr[12], w_lrly_vc_addr[11], w_lrly_vc_addr[10], w_lrly_vc_addr[9], w_lrly_vc_addr[8], w_lrly_vc_addr[7], w_lrly_vc_addr[6], w_lrly_vc_addr[5], w_lrly_vc_addr[4], w_lrly_vc_addr[3], w_lrly_vc_addr[2], w_lrly_vc_addr[1], w_lrly_vc_addr[0], w_lrly_vb_re[0], w_lrly_vb_addr[23], w_lrly_vb_addr[22], w_lrly_vb_addr[21], w_lrly_vb_addr[20], w_lrly_vb_addr[19], w_lrly_vb_addr[18], w_lrly_vb_addr[17], w_lrly_vb_addr[16], w_lrly_vb_addr[15], w_lrly_vb_addr[14], w_lrly_vb_addr[13], w_lrly_vb_addr[12], w_lrly_vb_addr[11], w_lrly_vb_addr[10], w_lrly_vb_addr[9], w_lrly_vb_addr[8], w_lrly_vb_addr[7], w_lrly_vb_addr[6], w_lrly_vb_addr[5], w_lrly_vb_addr[4], w_lrly_vb_addr[3], w_lrly_vb_addr[2], w_lrly_vb_addr[1], w_lrly_vb_addr[0], w_lrly_va_re[0], w_lrly_va_addr[23], w_lrly_va_addr[22], w_lrly_va_addr[21], w_lrly_va_addr[20], w_lrly_va_addr[19], w_lrly_va_addr[18], w_lrly_va_addr[17], w_lrly_va_addr[16], w_lrly_va_addr[15], w_lrly_va_addr[14], w_lrly_va_addr[13], w_lrly_va_addr[12], w_lrly_va_addr[11], w_lrly_va_addr[10], w_lrly_va_addr[9], w_lrly_va_addr[8], w_lrly_va_addr[7], w_lrly_va_addr[6], w_lrly_va_addr[5], w_lrly_va_addr[4], w_lrly_va_addr[3], w_lrly_va_addr[2], w_lrly_va_addr[1], w_lrly_va_addr[0], w_lrly_retire[0], w_lrly_l_redsq[0], w_lrly_l_red[1], w_lrly_l_red[0], w_lrly_l_raddr[23], w_lrly_l_raddr[22], w_lrly_l_raddr[21], w_lrly_l_raddr[20], w_lrly_l_raddr[19], w_lrly_l_raddr[18], w_lrly_l_raddr[17], w_lrly_l_raddr[16], w_lrly_l_raddr[15], w_lrly_l_raddr[14], w_lrly_l_raddr[13], w_lrly_l_raddr[12], w_lrly_l_raddr[11], w_lrly_l_raddr[10], w_lrly_l_raddr[9], w_lrly_l_raddr[8], w_lrly_l_raddr[7], w_lrly_l_raddr[6], w_lrly_l_raddr[5], w_lrly_l_raddr[4], w_lrly_l_raddr[3], w_lrly_l_raddr[2], w_lrly_l_raddr[1], w_lrly_l_raddr[0], w_lrly_l_ov[0], w_lrly_l_out[31], w_lrly_l_out[30], w_lrly_l_out[29], w_lrly_l_out[28], w_lrly_l_out[27], w_lrly_l_out[26], w_lrly_l_out[25], w_lrly_l_out[24], w_lrly_l_out[23], w_lrly_l_out[22], w_lrly_l_out[21], w_lrly_l_out[20], w_lrly_l_out[19], w_lrly_l_out[18], w_lrly_l_out[17], w_lrly_l_out[16], w_lrly_l_out[15], w_lrly_l_out[14], w_lrly_l_out[13], w_lrly_l_out[12], w_lrly_l_out[11], w_lrly_l_out[10], w_lrly_l_out[9], w_lrly_l_out[8], w_lrly_l_out[7], w_lrly_l_out[6], w_lrly_l_out[5], w_lrly_l_out[4], w_lrly_l_out[3], w_lrly_l_out[2], w_lrly_l_out[1], w_lrly_l_out[0], w_lrly_l_last[0], w_lrly_l_fault[0], w_lrly_kv_we[0], w_lrly_crom_re[0], w_lrly_crom_addr[23], w_lrly_crom_addr[22], w_lrly_crom_addr[21], w_lrly_crom_addr[20], w_lrly_crom_addr[19], w_lrly_crom_addr[18], w_lrly_crom_addr[17], w_lrly_crom_addr[16], w_lrly_crom_addr[15], w_lrly_crom_addr[14], w_lrly_crom_addr[13], w_lrly_crom_addr[12], w_lrly_crom_addr[11], w_lrly_crom_addr[10], w_lrly_crom_addr[9], w_lrly_crom_addr[8], w_lrly_crom_addr[7], w_lrly_crom_addr[6], w_lrly_crom_addr[5], w_lrly_crom_addr[4], w_lrly_crom_addr[3], w_lrly_crom_addr[2], w_lrly_crom_addr[1], w_lrly_crom_addr[0]};
    assign ctl_o = {w_lrly_vm_we[0], w_lrly_vm_wdata[31], w_lrly_vm_wdata[30], w_lrly_vm_wdata[29], w_lrly_vm_wdata[28], w_lrly_vm_wdata[27], w_lrly_vm_wdata[26], w_lrly_vm_wdata[25], w_lrly_vm_wdata[24], w_lrly_vm_wdata[23], w_lrly_vm_wdata[22], w_lrly_vm_wdata[21], w_lrly_vm_wdata[20], w_lrly_vm_wdata[19], w_lrly_vm_wdata[18], w_lrly_vm_wdata[17], w_lrly_vm_wdata[16], w_lrly_vm_wdata[15], w_lrly_vm_wdata[14], w_lrly_vm_wdata[13], w_lrly_vm_wdata[12], w_lrly_vm_wdata[11], w_lrly_vm_wdata[10], w_lrly_vm_wdata[9], w_lrly_vm_wdata[8], w_lrly_vm_wdata[7], w_lrly_vm_wdata[6], w_lrly_vm_wdata[5], w_lrly_vm_wdata[4], w_lrly_vm_wdata[3], w_lrly_vm_wdata[2], w_lrly_vm_wdata[1], w_lrly_vm_wdata[0], w_lrly_vm_waddr[23], w_lrly_vm_waddr[22], w_lrly_vm_waddr[21], w_lrly_vm_waddr[20], w_lrly_vm_waddr[19], w_lrly_vm_waddr[18], w_lrly_vm_waddr[17], w_lrly_vm_waddr[16], w_lrly_vm_waddr[15], w_lrly_vm_waddr[14], w_lrly_vm_waddr[13], w_lrly_vm_waddr[12], w_lrly_vm_waddr[11], w_lrly_vm_waddr[10], w_lrly_vm_waddr[9], w_lrly_vm_waddr[8], w_lrly_vm_waddr[7], w_lrly_vm_waddr[6], w_lrly_vm_waddr[5], w_lrly_vm_waddr[4], w_lrly_vm_waddr[3], w_lrly_vm_waddr[2], w_lrly_vm_waddr[1], w_lrly_vm_waddr[0], w_lrly_kv_we[0], w_lrly_kv_wdata[31], w_lrly_kv_wdata[30], w_lrly_kv_wdata[29], w_lrly_kv_wdata[28], w_lrly_kv_wdata[27], w_lrly_kv_wdata[26], w_lrly_kv_wdata[25], w_lrly_kv_wdata[24], w_lrly_kv_wdata[23], w_lrly_kv_wdata[22], w_lrly_kv_wdata[21], w_lrly_kv_wdata[20], w_lrly_kv_wdata[19], w_lrly_kv_wdata[18], w_lrly_kv_wdata[17], w_lrly_kv_wdata[16], w_lrly_kv_wdata[15], w_lrly_kv_wdata[14], w_lrly_kv_wdata[13], w_lrly_kv_wdata[12], w_lrly_kv_wdata[11], w_lrly_kv_wdata[10], w_lrly_kv_wdata[9], w_lrly_kv_wdata[8], w_lrly_kv_wdata[7], w_lrly_kv_wdata[6], w_lrly_kv_wdata[5], w_lrly_kv_wdata[4], w_lrly_kv_wdata[3], w_lrly_kv_wdata[2], w_lrly_kv_wdata[1], w_lrly_kv_wdata[0], w_lrly_kv_waddr[23], w_lrly_kv_waddr[22], w_lrly_kv_waddr[21], w_lrly_kv_waddr[20], w_lrly_kv_waddr[19], w_lrly_kv_waddr[18], w_lrly_kv_waddr[17], w_lrly_kv_waddr[16], w_lrly_kv_waddr[15], w_lrly_kv_waddr[14], w_lrly_kv_waddr[13], w_lrly_kv_waddr[12], w_lrly_kv_waddr[11], w_lrly_kv_waddr[10], w_lrly_kv_waddr[9], w_lrly_kv_waddr[8], w_lrly_kv_waddr[7], w_lrly_kv_waddr[6], w_lrly_kv_waddr[5], w_lrly_kv_waddr[4], w_lrly_kv_waddr[3], w_lrly_kv_waddr[2], w_lrly_kv_waddr[1], w_lrly_kv_waddr[0]};
    assign sc_o = {w_lrly_vm_we[0], w_lrly_vm_wdata[31], w_lrly_vm_wdata[30], w_lrly_vm_wdata[29], w_lrly_vm_wdata[28], w_lrly_vm_wdata[27], w_lrly_vm_wdata[26], w_lrly_vm_wdata[25], w_lrly_vm_wdata[24], w_lrly_vm_wdata[23], w_lrly_vm_wdata[22], w_lrly_vm_wdata[21], w_lrly_vm_wdata[20], w_lrly_vm_wdata[19], w_lrly_vm_wdata[18], w_lrly_vm_wdata[17], w_lrly_vm_wdata[16], w_lrly_vm_wdata[15], w_lrly_vm_wdata[14], w_lrly_vm_wdata[13], w_lrly_vm_wdata[12], w_lrly_vm_wdata[11], w_lrly_vm_wdata[10], w_lrly_vm_wdata[9], w_lrly_vm_wdata[8], w_lrly_vm_wdata[7], w_lrly_vm_wdata[6], w_lrly_vm_wdata[5], w_lrly_vm_wdata[4], w_lrly_vm_wdata[3], w_lrly_vm_wdata[2], w_lrly_vm_wdata[1], w_lrly_vm_wdata[0], w_lrly_vm_waddr[23], w_lrly_vm_waddr[22]};
    assign stm_o = {w_lrly_vm_we[0], w_lrly_vm_wdata[31], w_lrly_vm_wdata[30], w_lrly_vm_wdata[29], w_lrly_vm_wdata[28], w_lrly_vm_wdata[27], w_lrly_vm_wdata[26], w_lrly_vm_wdata[25], w_lrly_vm_wdata[24], w_lrly_vm_wdata[23], w_lrly_vm_wdata[22], w_lrly_vm_wdata[21], w_lrly_vm_wdata[20], w_lrly_vm_wdata[19], w_lrly_vm_wdata[18], w_lrly_vm_wdata[17], w_lrly_vm_wdata[16], w_lrly_vm_wdata[15], w_lrly_vm_wdata[14], w_lrly_vm_wdata[13], w_lrly_vm_wdata[12], w_lrly_vm_wdata[11], w_lrly_vm_wdata[10], w_lrly_vm_wdata[9], w_lrly_vm_wdata[8], w_lrly_vm_wdata[7], w_lrly_vm_wdata[6], w_lrly_vm_wdata[5], w_lrly_vm_wdata[4], w_lrly_vm_wdata[3], w_lrly_vm_wdata[2], w_lrly_vm_wdata[1], w_lrly_vm_wdata[0], w_lrly_vm_waddr[23], w_lrly_vm_waddr[22], w_lrly_vm_waddr[21], w_lrly_vm_waddr[20], w_lrly_vm_waddr[19], w_lrly_vm_waddr[18], w_lrly_vm_waddr[17], w_lrly_vm_waddr[16], w_lrly_vm_waddr[15], w_lrly_vm_waddr[14], w_lrly_vm_waddr[13], w_lrly_vm_waddr[12], w_lrly_vm_waddr[11], w_lrly_vm_waddr[10], w_lrly_vm_waddr[9], w_lrly_vm_waddr[8], w_lrly_vm_waddr[7], w_lrly_vm_waddr[6], w_lrly_vm_waddr[5], w_lrly_vm_waddr[4], w_lrly_vm_waddr[3], w_lrly_vm_waddr[2], w_lrly_vm_waddr[1], w_lrly_vm_waddr[0]};
endmodule
`default_nettype wire
