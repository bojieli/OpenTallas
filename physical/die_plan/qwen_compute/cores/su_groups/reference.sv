module ref_0 (input wire clk, input wire rst_n, input wire [759:0] c_i, output wire [245:0] c_o, output wire [113:0] ctl_o, output wire [34:0] sc_o, output wire [56:0] stm_o);
wire [0:0] w_u_exp0_fault;
wire [0:0] w_u_exp0_vo;
wire [31:0] w_u_exp0_y;
wire [23:0] w_u_head0_crom_addr;
wire [0:0] w_u_head0_crom_re;
wire [23:0] w_u_head0_kv_waddr;
wire [31:0] w_u_head0_kv_wdata;
wire [0:0] w_u_head0_kv_we;
wire [0:0] w_u_head0_l_fault;
wire [0:0] w_u_head0_l_last;
wire [31:0] w_u_head0_l_out;
wire [0:0] w_u_head0_l_ov;
wire [23:0] w_u_head0_l_raddr;
wire [1:0] w_u_head0_l_red;
wire [0:0] w_u_head0_l_redsq;
wire [0:0] w_u_head0_retire;
wire [0:0] w_u_head0_sx_exp_v;
wire [31:0] w_u_head0_sx_exp_x;
wire [0:0] w_u_head0_sx_rcp_v;
wire [31:0] w_u_head0_sx_rcp_x;
wire [0:0] w_u_head0_sx_rsq_v;
wire [31:0] w_u_head0_sx_rsq_x;
wire [23:0] w_u_head0_va_addr;
wire [0:0] w_u_head0_va_re;
wire [23:0] w_u_head0_vb_addr;
wire [0:0] w_u_head0_vb_re;
wire [23:0] w_u_head0_vc_addr;
wire [0:0] w_u_head0_vc_re;
wire [23:0] w_u_head0_vm_waddr;
wire [31:0] w_u_head0_vm_wdata;
wire [0:0] w_u_head0_vm_we;
wire [23:0] w_u_head0_wrom_addr;
wire [0:0] w_u_head0_wrom_re;
wire [0:0] w_u_lrly0_c_accept;
wire [2:0] w_u_lrly0_c_ad;
wire [23:0] w_u_lrly0_c_asi;
wire [0:0] w_u_lrly0_c_asrc;
wire [23:0] w_u_lrly0_c_bsi;
wire [0:0] w_u_lrly0_c_bsrc;
wire [2:0] w_u_lrly0_c_cls;
wire [63:0] w_u_lrly0_c_crom;
wire [23:0] w_u_lrly0_c_csi;
wire [0:0] w_u_lrly0_c_csrc;
wire [23:0] w_u_lrly0_c_cura;
wire [23:0] w_u_lrly0_c_curb;
wire [23:0] w_u_lrly0_c_curc;
wire [23:0] w_u_lrly0_c_curd;
wire [23:0] w_u_lrly0_c_dsi;
wire [1:0] w_u_lrly0_c_dst;
wire [0:0] w_u_lrly0_c_emit0;
wire [18:0] w_u_lrly0_c_fin_th;
wire [17:0] w_u_lrly0_c_i;
wire [0:0] w_u_lrly0_c_ilast;
wire [31:0] w_u_lrly0_c_imm1;
wire [31:0] w_u_lrly0_c_imm2;
wire [2:0] w_u_lrly0_c_isfu;
wire [0:0] w_u_lrly0_c_live;
wire [1:0] w_u_lrly0_c_ma;
wire [1:0] w_u_lrly0_c_mb;
wire [0:0] w_u_lrly0_c_mc;
wire [0:0] w_u_lrly0_c_md;
wire [1:0] w_u_lrly0_c_red;
wire [0:0] w_u_lrly0_c_redsq;
wire [23:0] w_u_lrly0_c_rrow;
wire [31:0] w_u_lrly0_c_va;
wire [31:0] w_u_lrly0_c_vb;
wire [31:0] w_u_lrly0_c_vc;
wire [255:0] w_u_lrly0_c_wrom;
wire [23:0] w_u_lrly0_crom_addr;
wire [0:0] w_u_lrly0_crom_re;
wire [0:0] w_u_lrly0_h_rst_n;
wire [23:0] w_u_lrly0_kv_waddr;
wire [31:0] w_u_lrly0_kv_wdata;
wire [0:0] w_u_lrly0_kv_we;
wire [0:0] w_u_lrly0_l_fault;
wire [0:0] w_u_lrly0_l_last;
wire [31:0] w_u_lrly0_l_out;
wire [0:0] w_u_lrly0_l_ov;
wire [23:0] w_u_lrly0_l_raddr;
wire [1:0] w_u_lrly0_l_red;
wire [0:0] w_u_lrly0_l_redsq;
wire [0:0] w_u_lrly0_retire;
wire [23:0] w_u_lrly0_va_addr;
wire [0:0] w_u_lrly0_va_re;
wire [23:0] w_u_lrly0_vb_addr;
wire [0:0] w_u_lrly0_vb_re;
wire [23:0] w_u_lrly0_vc_addr;
wire [0:0] w_u_lrly0_vc_re;
wire [23:0] w_u_lrly0_vm_waddr;
wire [31:0] w_u_lrly0_vm_wdata;
wire [0:0] w_u_lrly0_vm_we;
wire [23:0] w_u_lrly0_wrom_addr;
wire [0:0] w_u_lrly0_wrom_re;
wire [0:0] w_u_rcp0_fault;
wire [0:0] w_u_rcp0_vo;
wire [31:0] w_u_rcp0_y;
wire [0:0] w_u_rsq0_fault;
wire [0:0] w_u_rsq0_vo;
wire [31:0] w_u_rsq0_y;
wire [765:0] x_su_c_i_q;
wire [0:0] x_su_c_i_eq;
wire [764:0] x_su_c_p1_i_q;
wire [0:0] x_su_c_p1_i_eq;
assign x_su_c_i_q[63:0] = c_i[0 +: 64];
assign x_su_c_i_q[755:256] = c_i[64 +: 500];
assign x_su_c_i_q[758:756] = c_i[564 +: 3];
assign x_su_c_i_q[759] = c_i[567 +: 1];
assign {x_su_c_p1_i_q[92:0], x_su_c_i_q[765:763]} = c_i[568 +: 96];
assign x_su_c_p1_i_q[412:381] = c_i[664 +: 32];
assign x_su_c_p1_i_q[540:509] = c_i[696 +: 32];
assign x_su_c_p1_i_q[668:637] = c_i[728 +: 32];
ot_hdc_sfu_exp_t u_u_exp0 (
        .clk(clk),
        .fault(w_u_exp0_fault),
        .rst_n(rst_n),
        .v(w_u_head0_sx_exp_v[0]),
        .vo(w_u_exp0_vo),
        .x(w_u_head0_sx_exp_x[31:0]),
        .y(w_u_exp0_y)
    );
qfd_dv_lane_h_safe2 u_u_head0 (
        .accept(w_u_lrly0_c_accept[0]),
        .ad(w_u_lrly0_c_ad[2:0]),
        .asi(w_u_lrly0_c_asi[23:0]),
        .asrc(w_u_lrly0_c_asrc[0]),
        .bsi(w_u_lrly0_c_bsi[23:0]),
        .bsrc(w_u_lrly0_c_bsrc[0]),
        .clk(clk),
        .cls(w_u_lrly0_c_cls[2:0]),
        .crom_addr(w_u_head0_crom_addr),
        .crom_q(w_u_lrly0_c_crom[63:0]),
        .crom_re(w_u_head0_crom_re),
        .csi(w_u_lrly0_c_csi[23:0]),
        .csrc(w_u_lrly0_c_csrc[0]),
        .cura0(w_u_lrly0_c_cura[23:0]),
        .curb0(w_u_lrly0_c_curb[23:0]),
        .curc0(w_u_lrly0_c_curc[23:0]),
        .curd0(w_u_lrly0_c_curd[23:0]),
        .dsi(w_u_lrly0_c_dsi[23:0]),
        .dst(w_u_lrly0_c_dst[1:0]),
        .emit0(w_u_lrly0_c_emit0[0]),
        .fin_th(w_u_lrly0_c_fin_th[18:0]),
        .i(w_u_lrly0_c_i[17:0]),
        .i_last_r(w_u_lrly0_c_ilast[0]),
        .i_sfu(w_u_lrly0_c_isfu[2:0]),
        .imm1(w_u_lrly0_c_imm1[31:0]),
        .imm2(w_u_lrly0_c_imm2[31:0]),
        .kv_waddr(w_u_head0_kv_waddr),
        .kv_wdata(w_u_head0_kv_wdata),
        .kv_we(w_u_head0_kv_we),
        .l_fault(w_u_head0_l_fault),
        .l_last(w_u_head0_l_last),
        .l_out(w_u_head0_l_out),
        .l_ov(w_u_head0_l_ov),
        .l_raddr(w_u_head0_l_raddr),
        .l_red(w_u_head0_l_red),
        .l_redsq(w_u_head0_l_redsq),
        .live(w_u_lrly0_c_live[0]),
        .ma(w_u_lrly0_c_ma[1:0]),
        .mb(w_u_lrly0_c_mb[1:0]),
        .mc(w_u_lrly0_c_mc[0]),
        .md(w_u_lrly0_c_md[0]),
        .red(w_u_lrly0_c_red[1:0]),
        .redsq(w_u_lrly0_c_redsq[0]),
        .retire(w_u_head0_retire),
        .rrow(w_u_lrly0_c_rrow[23:0]),
        .rst_n(rst_n),
        .sx_exp_v(w_u_head0_sx_exp_v),
        .sx_exp_x(w_u_head0_sx_exp_x),
        .sx_rcp_v(w_u_head0_sx_rcp_v),
        .sx_rcp_x(w_u_head0_sx_rcp_x),
        .sx_rsq_v(w_u_head0_sx_rsq_v),
        .sx_rsq_x(w_u_head0_sx_rsq_x),
        .sy_exp_f(w_u_exp0_fault[0]),
        .sy_exp_vo(w_u_exp0_vo[0]),
        .sy_exp_y(w_u_exp0_y[31:0]),
        .sy_rcp_f(w_u_rcp0_fault[0]),
        .sy_rcp_y(w_u_rcp0_y[31:0]),
        .sy_rsq_f(w_u_rsq0_fault[0]),
        .sy_rsq_y(w_u_rsq0_y[31:0]),
        .va_addr(w_u_head0_va_addr),
        .va_q(w_u_lrly0_c_va[31:0]),
        .va_re(w_u_head0_va_re),
        .vb_addr(w_u_head0_vb_addr),
        .vb_q(w_u_lrly0_c_vb[31:0]),
        .vb_re(w_u_head0_vb_re),
        .vc_addr(w_u_head0_vc_addr),
        .vc_q(w_u_lrly0_c_vc[31:0]),
        .vc_re(w_u_head0_vc_re),
        .vm_waddr(w_u_head0_vm_waddr),
        .vm_wdata(w_u_head0_vm_wdata),
        .vm_we(w_u_head0_vm_we),
        .wrom_addr(w_u_head0_wrom_addr),
        .wrom_q(w_u_lrly0_c_wrom[255:0]),
        .wrom_re(w_u_head0_wrom_re)
    );
qfd_dv_s5_lrly u_u_lrly0 (
        .c_accept(w_u_lrly0_c_accept),
        .c_ad(w_u_lrly0_c_ad),
        .c_asi(w_u_lrly0_c_asi),
        .c_asrc(w_u_lrly0_c_asrc),
        .c_bsi(w_u_lrly0_c_bsi),
        .c_bsrc(w_u_lrly0_c_bsrc),
        .c_cls(w_u_lrly0_c_cls),
        .c_crom(w_u_lrly0_c_crom),
        .c_csi(w_u_lrly0_c_csi),
        .c_csrc(w_u_lrly0_c_csrc),
        .c_cura(w_u_lrly0_c_cura),
        .c_curb(w_u_lrly0_c_curb),
        .c_curc(w_u_lrly0_c_curc),
        .c_curd(w_u_lrly0_c_curd),
        .c_dsi(w_u_lrly0_c_dsi),
        .c_dst(w_u_lrly0_c_dst),
        .c_emit0(w_u_lrly0_c_emit0),
        .c_fin_th(w_u_lrly0_c_fin_th),
        .c_i(w_u_lrly0_c_i),
        .c_ilast(w_u_lrly0_c_ilast),
        .c_imm1(w_u_lrly0_c_imm1),
        .c_imm2(w_u_lrly0_c_imm2),
        .c_isfu(w_u_lrly0_c_isfu),
        .c_live(w_u_lrly0_c_live),
        .c_ma(w_u_lrly0_c_ma),
        .c_mb(w_u_lrly0_c_mb),
        .c_mc(w_u_lrly0_c_mc),
        .c_md(w_u_lrly0_c_md),
        .c_red(w_u_lrly0_c_red),
        .c_redsq(w_u_lrly0_c_redsq),
        .c_rrow(w_u_lrly0_c_rrow),
        .c_va(w_u_lrly0_c_va),
        .c_vb(w_u_lrly0_c_vb),
        .c_vc(w_u_lrly0_c_vc),
        .c_wrom(w_u_lrly0_c_wrom),
        .ck(clk),
        .cr_q(x_su_c_i_q[63:0]),
        .crom_addr(w_u_lrly0_crom_addr),
        .crom_re(w_u_lrly0_crom_re),
        .gb(x_su_c_i_q[755:256]),
        .gv(x_su_c_i_q[758:756]),
        .h_crom_addr(w_u_head0_crom_addr[23:0]),
        .h_crom_re(w_u_head0_crom_re[0]),
        .h_kv_waddr(w_u_head0_kv_waddr[23:0]),
        .h_kv_wdata(w_u_head0_kv_wdata[31:0]),
        .h_kv_we(w_u_head0_kv_we[0]),
        .h_l_fault(w_u_head0_l_fault[0]),
        .h_l_last(w_u_head0_l_last[0]),
        .h_l_out(w_u_head0_l_out[31:0]),
        .h_l_ov(w_u_head0_l_ov[0]),
        .h_l_raddr(w_u_head0_l_raddr[23:0]),
        .h_l_red(w_u_head0_l_red[1:0]),
        .h_l_redsq(w_u_head0_l_redsq[0]),
        .h_retire(w_u_head0_retire[0]),
        .h_rst_n(w_u_lrly0_h_rst_n),
        .h_va_addr(w_u_head0_va_addr[23:0]),
        .h_va_re(w_u_head0_va_re[0]),
        .h_vb_addr(w_u_head0_vb_addr[23:0]),
        .h_vb_re(w_u_head0_vb_re[0]),
        .h_vc_addr(w_u_head0_vc_addr[23:0]),
        .h_vc_re(w_u_head0_vc_re[0]),
        .h_vm_waddr(w_u_head0_vm_waddr[23:0]),
        .h_vm_wdata(w_u_head0_vm_wdata[31:0]),
        .h_vm_we(w_u_head0_vm_we[0]),
        .h_wrom_addr(w_u_head0_wrom_addr[23:0]),
        .h_wrom_re(w_u_head0_wrom_re[0]),
        .kv_waddr(w_u_lrly0_kv_waddr),
        .kv_wdata(w_u_lrly0_kv_wdata),
        .kv_we(w_u_lrly0_kv_we),
        .l_fault(w_u_lrly0_l_fault),
        .l_last(w_u_lrly0_l_last),
        .l_out(w_u_lrly0_l_out),
        .l_ov(w_u_lrly0_l_ov),
        .l_raddr(w_u_lrly0_l_raddr),
        .l_red(w_u_lrly0_l_red),
        .l_redsq(w_u_lrly0_l_redsq),
        .lv1(x_su_c_i_q[759]),
        .pd1({x_su_c_p1_i_q[92:0], x_su_c_i_q[765:763]}),
        .retire(w_u_lrly0_retire),
        .rst_n(rst_n),
        .va_addr(w_u_lrly0_va_addr),
        .va_q(x_su_c_p1_i_q[412:381]),
        .va_re(w_u_lrly0_va_re),
        .vb_addr(w_u_lrly0_vb_addr),
        .vb_q(x_su_c_p1_i_q[540:509]),
        .vb_re(w_u_lrly0_vb_re),
        .vc_addr(w_u_lrly0_vc_addr),
        .vc_q(x_su_c_p1_i_q[668:637]),
        .vc_re(w_u_lrly0_vc_re),
        .vm_waddr(w_u_lrly0_vm_waddr),
        .vm_wdata(w_u_lrly0_vm_wdata),
        .vm_we(w_u_lrly0_vm_we),
        .wrom_addr(w_u_lrly0_wrom_addr),
        .wrom_re(w_u_lrly0_wrom_re)
    );
ot_hdc_sfu_rcp_t u_u_rcp0 (
        .clk(clk),
        .fault(w_u_rcp0_fault),
        .rst_n(rst_n),
        .v(w_u_head0_sx_rcp_v[0]),
        .vo(w_u_rcp0_vo),
        .x(w_u_head0_sx_rcp_x[31:0]),
        .y(w_u_rcp0_y)
    );
ot_hdc_sfu_rsq_t u_u_rsq0 (
        .clk(clk),
        .fault(w_u_rsq0_fault),
        .rst_n(rst_n),
        .v(w_u_head0_sx_rsq_v[0]),
        .vo(w_u_rsq0_vo),
        .x(w_u_head0_sx_rsq_x[31:0]),
        .y(w_u_rsq0_y)
    );
assign c_o = {w_u_lrly0_wrom_re[0], w_u_lrly0_wrom_addr[23], w_u_lrly0_wrom_addr[22], w_u_lrly0_wrom_addr[21], w_u_lrly0_wrom_addr[20], w_u_lrly0_wrom_addr[19], w_u_lrly0_wrom_addr[18], w_u_lrly0_wrom_addr[17], w_u_lrly0_wrom_addr[16], w_u_lrly0_wrom_addr[15], w_u_lrly0_wrom_addr[14], w_u_lrly0_wrom_addr[13], w_u_lrly0_wrom_addr[12], w_u_lrly0_wrom_addr[11], w_u_lrly0_wrom_addr[10], w_u_lrly0_wrom_addr[9], w_u_lrly0_wrom_addr[8], w_u_lrly0_wrom_addr[7], w_u_lrly0_wrom_addr[6], w_u_lrly0_wrom_addr[5], w_u_lrly0_wrom_addr[4], w_u_lrly0_wrom_addr[3], w_u_lrly0_wrom_addr[2], w_u_lrly0_wrom_addr[1], w_u_lrly0_wrom_addr[0], w_u_lrly0_vm_we[0], w_u_lrly0_vm_wdata[31], w_u_lrly0_vm_wdata[30], w_u_lrly0_vm_wdata[29], w_u_lrly0_vm_wdata[28], w_u_lrly0_vm_wdata[27], w_u_lrly0_vm_wdata[26], w_u_lrly0_vm_wdata[25], w_u_lrly0_vm_wdata[24], w_u_lrly0_vm_wdata[23], w_u_lrly0_vm_wdata[22], w_u_lrly0_vm_wdata[21], w_u_lrly0_vm_wdata[20], w_u_lrly0_vm_wdata[19], w_u_lrly0_vm_wdata[18], w_u_lrly0_vm_wdata[17], w_u_lrly0_vm_wdata[16], w_u_lrly0_vm_wdata[15], w_u_lrly0_vm_wdata[14], w_u_lrly0_vm_wdata[13], w_u_lrly0_vm_wdata[12], w_u_lrly0_vm_wdata[11], w_u_lrly0_vm_wdata[10], w_u_lrly0_vm_wdata[9], w_u_lrly0_vm_wdata[8], w_u_lrly0_vm_wdata[7], w_u_lrly0_vm_wdata[6], w_u_lrly0_vm_wdata[5], w_u_lrly0_vm_wdata[4], w_u_lrly0_vm_wdata[3], w_u_lrly0_vm_wdata[2], w_u_lrly0_vm_wdata[1], w_u_lrly0_vm_wdata[0], w_u_lrly0_vm_waddr[23], w_u_lrly0_vm_waddr[22], w_u_lrly0_vm_waddr[21], w_u_lrly0_vm_waddr[20], w_u_lrly0_vm_waddr[19], w_u_lrly0_vm_waddr[18], w_u_lrly0_vm_waddr[17], w_u_lrly0_vm_waddr[16], w_u_lrly0_vm_waddr[15], w_u_lrly0_vm_waddr[14], w_u_lrly0_vm_waddr[13], w_u_lrly0_vm_waddr[12], w_u_lrly0_vm_waddr[11], w_u_lrly0_vm_waddr[10], w_u_lrly0_vm_waddr[9], w_u_lrly0_vm_waddr[8], w_u_lrly0_vm_waddr[7], w_u_lrly0_vm_waddr[6], w_u_lrly0_vm_waddr[5], w_u_lrly0_vm_waddr[4], w_u_lrly0_vm_waddr[3], w_u_lrly0_vm_waddr[2], w_u_lrly0_vm_waddr[1], w_u_lrly0_vm_waddr[0], w_u_lrly0_vc_re[0], w_u_lrly0_vc_addr[23], w_u_lrly0_vc_addr[22], w_u_lrly0_vc_addr[21], w_u_lrly0_vc_addr[20], w_u_lrly0_vc_addr[19], w_u_lrly0_vc_addr[18], w_u_lrly0_vc_addr[17], w_u_lrly0_vc_addr[16], w_u_lrly0_vc_addr[15], w_u_lrly0_vc_addr[14], w_u_lrly0_vc_addr[13], w_u_lrly0_vc_addr[12], w_u_lrly0_vc_addr[11], w_u_lrly0_vc_addr[10], w_u_lrly0_vc_addr[9], w_u_lrly0_vc_addr[8], w_u_lrly0_vc_addr[7], w_u_lrly0_vc_addr[6], w_u_lrly0_vc_addr[5], w_u_lrly0_vc_addr[4], w_u_lrly0_vc_addr[3], w_u_lrly0_vc_addr[2], w_u_lrly0_vc_addr[1], w_u_lrly0_vc_addr[0], w_u_lrly0_vb_re[0], w_u_lrly0_vb_addr[23], w_u_lrly0_vb_addr[22], w_u_lrly0_vb_addr[21], w_u_lrly0_vb_addr[20], w_u_lrly0_vb_addr[19], w_u_lrly0_vb_addr[18], w_u_lrly0_vb_addr[17], w_u_lrly0_vb_addr[16], w_u_lrly0_vb_addr[15], w_u_lrly0_vb_addr[14], w_u_lrly0_vb_addr[13], w_u_lrly0_vb_addr[12], w_u_lrly0_vb_addr[11], w_u_lrly0_vb_addr[10], w_u_lrly0_vb_addr[9], w_u_lrly0_vb_addr[8], w_u_lrly0_vb_addr[7], w_u_lrly0_vb_addr[6], w_u_lrly0_vb_addr[5], w_u_lrly0_vb_addr[4], w_u_lrly0_vb_addr[3], w_u_lrly0_vb_addr[2], w_u_lrly0_vb_addr[1], w_u_lrly0_vb_addr[0], w_u_lrly0_va_re[0], w_u_lrly0_va_addr[23], w_u_lrly0_va_addr[22], w_u_lrly0_va_addr[21], w_u_lrly0_va_addr[20], w_u_lrly0_va_addr[19], w_u_lrly0_va_addr[18], w_u_lrly0_va_addr[17], w_u_lrly0_va_addr[16], w_u_lrly0_va_addr[15], w_u_lrly0_va_addr[14], w_u_lrly0_va_addr[13], w_u_lrly0_va_addr[12], w_u_lrly0_va_addr[11], w_u_lrly0_va_addr[10], w_u_lrly0_va_addr[9], w_u_lrly0_va_addr[8], w_u_lrly0_va_addr[7], w_u_lrly0_va_addr[6], w_u_lrly0_va_addr[5], w_u_lrly0_va_addr[4], w_u_lrly0_va_addr[3], w_u_lrly0_va_addr[2], w_u_lrly0_va_addr[1], w_u_lrly0_va_addr[0], w_u_lrly0_retire[0], w_u_lrly0_l_redsq[0], w_u_lrly0_l_red[1], w_u_lrly0_l_red[0], w_u_lrly0_l_raddr[23], w_u_lrly0_l_raddr[22], w_u_lrly0_l_raddr[21], w_u_lrly0_l_raddr[20], w_u_lrly0_l_raddr[19], w_u_lrly0_l_raddr[18], w_u_lrly0_l_raddr[17], w_u_lrly0_l_raddr[16], w_u_lrly0_l_raddr[15], w_u_lrly0_l_raddr[14], w_u_lrly0_l_raddr[13], w_u_lrly0_l_raddr[12], w_u_lrly0_l_raddr[11], w_u_lrly0_l_raddr[10], w_u_lrly0_l_raddr[9], w_u_lrly0_l_raddr[8], w_u_lrly0_l_raddr[7], w_u_lrly0_l_raddr[6], w_u_lrly0_l_raddr[5], w_u_lrly0_l_raddr[4], w_u_lrly0_l_raddr[3], w_u_lrly0_l_raddr[2], w_u_lrly0_l_raddr[1], w_u_lrly0_l_raddr[0], w_u_lrly0_l_ov[0], w_u_lrly0_l_out[31], w_u_lrly0_l_out[30], w_u_lrly0_l_out[29], w_u_lrly0_l_out[28], w_u_lrly0_l_out[27], w_u_lrly0_l_out[26], w_u_lrly0_l_out[25], w_u_lrly0_l_out[24], w_u_lrly0_l_out[23], w_u_lrly0_l_out[22], w_u_lrly0_l_out[21], w_u_lrly0_l_out[20], w_u_lrly0_l_out[19], w_u_lrly0_l_out[18], w_u_lrly0_l_out[17], w_u_lrly0_l_out[16], w_u_lrly0_l_out[15], w_u_lrly0_l_out[14], w_u_lrly0_l_out[13], w_u_lrly0_l_out[12], w_u_lrly0_l_out[11], w_u_lrly0_l_out[10], w_u_lrly0_l_out[9], w_u_lrly0_l_out[8], w_u_lrly0_l_out[7], w_u_lrly0_l_out[6], w_u_lrly0_l_out[5], w_u_lrly0_l_out[4], w_u_lrly0_l_out[3], w_u_lrly0_l_out[2], w_u_lrly0_l_out[1], w_u_lrly0_l_out[0], w_u_lrly0_l_last[0], w_u_lrly0_l_fault[0], w_u_lrly0_kv_we[0], w_u_lrly0_crom_re[0], w_u_lrly0_crom_addr[23], w_u_lrly0_crom_addr[22], w_u_lrly0_crom_addr[21], w_u_lrly0_crom_addr[20], w_u_lrly0_crom_addr[19], w_u_lrly0_crom_addr[18], w_u_lrly0_crom_addr[17], w_u_lrly0_crom_addr[16], w_u_lrly0_crom_addr[15], w_u_lrly0_crom_addr[14], w_u_lrly0_crom_addr[13], w_u_lrly0_crom_addr[12], w_u_lrly0_crom_addr[11], w_u_lrly0_crom_addr[10], w_u_lrly0_crom_addr[9], w_u_lrly0_crom_addr[8], w_u_lrly0_crom_addr[7], w_u_lrly0_crom_addr[6], w_u_lrly0_crom_addr[5], w_u_lrly0_crom_addr[4], w_u_lrly0_crom_addr[3], w_u_lrly0_crom_addr[2], w_u_lrly0_crom_addr[1], w_u_lrly0_crom_addr[0]};
assign ctl_o = {w_u_lrly0_vm_we[0], w_u_lrly0_vm_wdata[31], w_u_lrly0_vm_wdata[30], w_u_lrly0_vm_wdata[29], w_u_lrly0_vm_wdata[28], w_u_lrly0_vm_wdata[27], w_u_lrly0_vm_wdata[26], w_u_lrly0_vm_wdata[25], w_u_lrly0_vm_wdata[24], w_u_lrly0_vm_wdata[23], w_u_lrly0_vm_wdata[22], w_u_lrly0_vm_wdata[21], w_u_lrly0_vm_wdata[20], w_u_lrly0_vm_wdata[19], w_u_lrly0_vm_wdata[18], w_u_lrly0_vm_wdata[17], w_u_lrly0_vm_wdata[16], w_u_lrly0_vm_wdata[15], w_u_lrly0_vm_wdata[14], w_u_lrly0_vm_wdata[13], w_u_lrly0_vm_wdata[12], w_u_lrly0_vm_wdata[11], w_u_lrly0_vm_wdata[10], w_u_lrly0_vm_wdata[9], w_u_lrly0_vm_wdata[8], w_u_lrly0_vm_wdata[7], w_u_lrly0_vm_wdata[6], w_u_lrly0_vm_wdata[5], w_u_lrly0_vm_wdata[4], w_u_lrly0_vm_wdata[3], w_u_lrly0_vm_wdata[2], w_u_lrly0_vm_wdata[1], w_u_lrly0_vm_wdata[0], w_u_lrly0_vm_waddr[23], w_u_lrly0_vm_waddr[22], w_u_lrly0_vm_waddr[21], w_u_lrly0_vm_waddr[20], w_u_lrly0_vm_waddr[19], w_u_lrly0_vm_waddr[18], w_u_lrly0_vm_waddr[17], w_u_lrly0_vm_waddr[16], w_u_lrly0_vm_waddr[15], w_u_lrly0_vm_waddr[14], w_u_lrly0_vm_waddr[13], w_u_lrly0_vm_waddr[12], w_u_lrly0_vm_waddr[11], w_u_lrly0_vm_waddr[10], w_u_lrly0_vm_waddr[9], w_u_lrly0_vm_waddr[8], w_u_lrly0_vm_waddr[7], w_u_lrly0_vm_waddr[6], w_u_lrly0_vm_waddr[5], w_u_lrly0_vm_waddr[4], w_u_lrly0_vm_waddr[3], w_u_lrly0_vm_waddr[2], w_u_lrly0_vm_waddr[1], w_u_lrly0_vm_waddr[0], w_u_lrly0_kv_we[0], w_u_lrly0_kv_wdata[31], w_u_lrly0_kv_wdata[30], w_u_lrly0_kv_wdata[29], w_u_lrly0_kv_wdata[28], w_u_lrly0_kv_wdata[27], w_u_lrly0_kv_wdata[26], w_u_lrly0_kv_wdata[25], w_u_lrly0_kv_wdata[24], w_u_lrly0_kv_wdata[23], w_u_lrly0_kv_wdata[22], w_u_lrly0_kv_wdata[21], w_u_lrly0_kv_wdata[20], w_u_lrly0_kv_wdata[19], w_u_lrly0_kv_wdata[18], w_u_lrly0_kv_wdata[17], w_u_lrly0_kv_wdata[16], w_u_lrly0_kv_wdata[15], w_u_lrly0_kv_wdata[14], w_u_lrly0_kv_wdata[13], w_u_lrly0_kv_wdata[12], w_u_lrly0_kv_wdata[11], w_u_lrly0_kv_wdata[10], w_u_lrly0_kv_wdata[9], w_u_lrly0_kv_wdata[8], w_u_lrly0_kv_wdata[7], w_u_lrly0_kv_wdata[6], w_u_lrly0_kv_wdata[5], w_u_lrly0_kv_wdata[4], w_u_lrly0_kv_wdata[3], w_u_lrly0_kv_wdata[2], w_u_lrly0_kv_wdata[1], w_u_lrly0_kv_wdata[0], w_u_lrly0_kv_waddr[23], w_u_lrly0_kv_waddr[22], w_u_lrly0_kv_waddr[21], w_u_lrly0_kv_waddr[20], w_u_lrly0_kv_waddr[19], w_u_lrly0_kv_waddr[18], w_u_lrly0_kv_waddr[17], w_u_lrly0_kv_waddr[16], w_u_lrly0_kv_waddr[15], w_u_lrly0_kv_waddr[14], w_u_lrly0_kv_waddr[13], w_u_lrly0_kv_waddr[12], w_u_lrly0_kv_waddr[11], w_u_lrly0_kv_waddr[10], w_u_lrly0_kv_waddr[9], w_u_lrly0_kv_waddr[8], w_u_lrly0_kv_waddr[7], w_u_lrly0_kv_waddr[6], w_u_lrly0_kv_waddr[5], w_u_lrly0_kv_waddr[4], w_u_lrly0_kv_waddr[3], w_u_lrly0_kv_waddr[2], w_u_lrly0_kv_waddr[1], w_u_lrly0_kv_waddr[0]};
assign sc_o = {w_u_lrly0_vm_we[0], w_u_lrly0_vm_wdata[31], w_u_lrly0_vm_wdata[30], w_u_lrly0_vm_wdata[29], w_u_lrly0_vm_wdata[28], w_u_lrly0_vm_wdata[27], w_u_lrly0_vm_wdata[26], w_u_lrly0_vm_wdata[25], w_u_lrly0_vm_wdata[24], w_u_lrly0_vm_wdata[23], w_u_lrly0_vm_wdata[22], w_u_lrly0_vm_wdata[21], w_u_lrly0_vm_wdata[20], w_u_lrly0_vm_wdata[19], w_u_lrly0_vm_wdata[18], w_u_lrly0_vm_wdata[17], w_u_lrly0_vm_wdata[16], w_u_lrly0_vm_wdata[15], w_u_lrly0_vm_wdata[14], w_u_lrly0_vm_wdata[13], w_u_lrly0_vm_wdata[12], w_u_lrly0_vm_wdata[11], w_u_lrly0_vm_wdata[10], w_u_lrly0_vm_wdata[9], w_u_lrly0_vm_wdata[8], w_u_lrly0_vm_wdata[7], w_u_lrly0_vm_wdata[6], w_u_lrly0_vm_wdata[5], w_u_lrly0_vm_wdata[4], w_u_lrly0_vm_wdata[3], w_u_lrly0_vm_wdata[2], w_u_lrly0_vm_wdata[1], w_u_lrly0_vm_wdata[0], w_u_lrly0_vm_waddr[23], w_u_lrly0_vm_waddr[22]};
assign stm_o = {w_u_lrly0_vm_we[0], w_u_lrly0_vm_wdata[31], w_u_lrly0_vm_wdata[30], w_u_lrly0_vm_wdata[29], w_u_lrly0_vm_wdata[28], w_u_lrly0_vm_wdata[27], w_u_lrly0_vm_wdata[26], w_u_lrly0_vm_wdata[25], w_u_lrly0_vm_wdata[24], w_u_lrly0_vm_wdata[23], w_u_lrly0_vm_wdata[22], w_u_lrly0_vm_wdata[21], w_u_lrly0_vm_wdata[20], w_u_lrly0_vm_wdata[19], w_u_lrly0_vm_wdata[18], w_u_lrly0_vm_wdata[17], w_u_lrly0_vm_wdata[16], w_u_lrly0_vm_wdata[15], w_u_lrly0_vm_wdata[14], w_u_lrly0_vm_wdata[13], w_u_lrly0_vm_wdata[12], w_u_lrly0_vm_wdata[11], w_u_lrly0_vm_wdata[10], w_u_lrly0_vm_wdata[9], w_u_lrly0_vm_wdata[8], w_u_lrly0_vm_wdata[7], w_u_lrly0_vm_wdata[6], w_u_lrly0_vm_wdata[5], w_u_lrly0_vm_wdata[4], w_u_lrly0_vm_wdata[3], w_u_lrly0_vm_wdata[2], w_u_lrly0_vm_wdata[1], w_u_lrly0_vm_wdata[0], w_u_lrly0_vm_waddr[23], w_u_lrly0_vm_waddr[22], w_u_lrly0_vm_waddr[21], w_u_lrly0_vm_waddr[20], w_u_lrly0_vm_waddr[19], w_u_lrly0_vm_waddr[18], w_u_lrly0_vm_waddr[17], w_u_lrly0_vm_waddr[16], w_u_lrly0_vm_waddr[15], w_u_lrly0_vm_waddr[14], w_u_lrly0_vm_waddr[13], w_u_lrly0_vm_waddr[12], w_u_lrly0_vm_waddr[11], w_u_lrly0_vm_waddr[10], w_u_lrly0_vm_waddr[9], w_u_lrly0_vm_waddr[8], w_u_lrly0_vm_waddr[7], w_u_lrly0_vm_waddr[6], w_u_lrly0_vm_waddr[5], w_u_lrly0_vm_waddr[4], w_u_lrly0_vm_waddr[3], w_u_lrly0_vm_waddr[2], w_u_lrly0_vm_waddr[1], w_u_lrly0_vm_waddr[0]};
endmodule

module ref_1 (input wire clk, input wire rst_n, input wire [759:0] c_i, output wire [113:0] ctl_o, output wire [0:0] sc_o, output wire [56:0] stm_o, output wire [218:0] c_o);
wire [0:0] w_u_exp1_fault;
wire [0:0] w_u_exp1_vo;
wire [31:0] w_u_exp1_y;
wire [23:0] w_u_head1_crom_addr;
wire [0:0] w_u_head1_crom_re;
wire [23:0] w_u_head1_kv_waddr;
wire [31:0] w_u_head1_kv_wdata;
wire [0:0] w_u_head1_kv_we;
wire [0:0] w_u_head1_l_fault;
wire [0:0] w_u_head1_l_last;
wire [31:0] w_u_head1_l_out;
wire [0:0] w_u_head1_l_ov;
wire [23:0] w_u_head1_l_raddr;
wire [1:0] w_u_head1_l_red;
wire [0:0] w_u_head1_l_redsq;
wire [0:0] w_u_head1_retire;
wire [0:0] w_u_head1_sx_exp_v;
wire [31:0] w_u_head1_sx_exp_x;
wire [0:0] w_u_head1_sx_rcp_v;
wire [31:0] w_u_head1_sx_rcp_x;
wire [0:0] w_u_head1_sx_rsq_v;
wire [31:0] w_u_head1_sx_rsq_x;
wire [23:0] w_u_head1_va_addr;
wire [0:0] w_u_head1_va_re;
wire [23:0] w_u_head1_vb_addr;
wire [0:0] w_u_head1_vb_re;
wire [23:0] w_u_head1_vc_addr;
wire [0:0] w_u_head1_vc_re;
wire [23:0] w_u_head1_vm_waddr;
wire [31:0] w_u_head1_vm_wdata;
wire [0:0] w_u_head1_vm_we;
wire [23:0] w_u_head1_wrom_addr;
wire [0:0] w_u_head1_wrom_re;
wire [0:0] w_u_lrly1_c_accept;
wire [2:0] w_u_lrly1_c_ad;
wire [23:0] w_u_lrly1_c_asi;
wire [0:0] w_u_lrly1_c_asrc;
wire [23:0] w_u_lrly1_c_bsi;
wire [0:0] w_u_lrly1_c_bsrc;
wire [2:0] w_u_lrly1_c_cls;
wire [63:0] w_u_lrly1_c_crom;
wire [23:0] w_u_lrly1_c_csi;
wire [0:0] w_u_lrly1_c_csrc;
wire [23:0] w_u_lrly1_c_cura;
wire [23:0] w_u_lrly1_c_curb;
wire [23:0] w_u_lrly1_c_curc;
wire [23:0] w_u_lrly1_c_curd;
wire [23:0] w_u_lrly1_c_dsi;
wire [1:0] w_u_lrly1_c_dst;
wire [0:0] w_u_lrly1_c_emit0;
wire [18:0] w_u_lrly1_c_fin_th;
wire [17:0] w_u_lrly1_c_i;
wire [0:0] w_u_lrly1_c_ilast;
wire [31:0] w_u_lrly1_c_imm1;
wire [31:0] w_u_lrly1_c_imm2;
wire [2:0] w_u_lrly1_c_isfu;
wire [0:0] w_u_lrly1_c_live;
wire [1:0] w_u_lrly1_c_ma;
wire [1:0] w_u_lrly1_c_mb;
wire [0:0] w_u_lrly1_c_mc;
wire [0:0] w_u_lrly1_c_md;
wire [1:0] w_u_lrly1_c_red;
wire [0:0] w_u_lrly1_c_redsq;
wire [23:0] w_u_lrly1_c_rrow;
wire [31:0] w_u_lrly1_c_va;
wire [31:0] w_u_lrly1_c_vb;
wire [31:0] w_u_lrly1_c_vc;
wire [255:0] w_u_lrly1_c_wrom;
wire [23:0] w_u_lrly1_crom_addr;
wire [0:0] w_u_lrly1_crom_re;
wire [0:0] w_u_lrly1_h_rst_n;
wire [23:0] w_u_lrly1_kv_waddr;
wire [31:0] w_u_lrly1_kv_wdata;
wire [0:0] w_u_lrly1_kv_we;
wire [0:0] w_u_lrly1_l_fault;
wire [0:0] w_u_lrly1_l_last;
wire [31:0] w_u_lrly1_l_out;
wire [0:0] w_u_lrly1_l_ov;
wire [23:0] w_u_lrly1_l_raddr;
wire [1:0] w_u_lrly1_l_red;
wire [0:0] w_u_lrly1_l_redsq;
wire [0:0] w_u_lrly1_retire;
wire [23:0] w_u_lrly1_va_addr;
wire [0:0] w_u_lrly1_va_re;
wire [23:0] w_u_lrly1_vb_addr;
wire [0:0] w_u_lrly1_vb_re;
wire [23:0] w_u_lrly1_vc_addr;
wire [0:0] w_u_lrly1_vc_re;
wire [23:0] w_u_lrly1_vm_waddr;
wire [31:0] w_u_lrly1_vm_wdata;
wire [0:0] w_u_lrly1_vm_we;
wire [23:0] w_u_lrly1_wrom_addr;
wire [0:0] w_u_lrly1_wrom_re;
wire [0:0] w_u_rcp1_fault;
wire [0:0] w_u_rcp1_vo;
wire [31:0] w_u_rcp1_y;
wire [0:0] w_u_rsq1_fault;
wire [0:0] w_u_rsq1_vo;
wire [31:0] w_u_rsq1_y;
wire [765:0] x_su_c_i_q;
wire [0:0] x_su_c_i_eq;
wire [764:0] x_su_c_p1_i_q;
wire [0:0] x_su_c_p1_i_eq;
assign x_su_c_i_q[127:64] = c_i[0 +: 64];
assign x_su_c_i_q[755:256] = c_i[64 +: 500];
assign x_su_c_i_q[758:756] = c_i[564 +: 3];
assign x_su_c_i_q[760] = c_i[567 +: 1];
assign x_su_c_p1_i_q[188:93] = c_i[568 +: 96];
assign x_su_c_p1_i_q[444:413] = c_i[664 +: 32];
assign x_su_c_p1_i_q[572:541] = c_i[696 +: 32];
assign x_su_c_p1_i_q[700:669] = c_i[728 +: 32];
ot_hdc_sfu_exp_t u_u_exp1 (
        .clk(clk),
        .fault(w_u_exp1_fault),
        .rst_n(rst_n),
        .v(w_u_head1_sx_exp_v[0]),
        .vo(w_u_exp1_vo),
        .x(w_u_head1_sx_exp_x[31:0]),
        .y(w_u_exp1_y)
    );
qfd_dv_lane_h_safe2 u_u_head1 (
        .accept(w_u_lrly1_c_accept[0]),
        .ad(w_u_lrly1_c_ad[2:0]),
        .asi(w_u_lrly1_c_asi[23:0]),
        .asrc(w_u_lrly1_c_asrc[0]),
        .bsi(w_u_lrly1_c_bsi[23:0]),
        .bsrc(w_u_lrly1_c_bsrc[0]),
        .clk(clk),
        .cls(w_u_lrly1_c_cls[2:0]),
        .crom_addr(w_u_head1_crom_addr),
        .crom_q(w_u_lrly1_c_crom[63:0]),
        .crom_re(w_u_head1_crom_re),
        .csi(w_u_lrly1_c_csi[23:0]),
        .csrc(w_u_lrly1_c_csrc[0]),
        .cura0(w_u_lrly1_c_cura[23:0]),
        .curb0(w_u_lrly1_c_curb[23:0]),
        .curc0(w_u_lrly1_c_curc[23:0]),
        .curd0(w_u_lrly1_c_curd[23:0]),
        .dsi(w_u_lrly1_c_dsi[23:0]),
        .dst(w_u_lrly1_c_dst[1:0]),
        .emit0(w_u_lrly1_c_emit0[0]),
        .fin_th(w_u_lrly1_c_fin_th[18:0]),
        .i(w_u_lrly1_c_i[17:0]),
        .i_last_r(w_u_lrly1_c_ilast[0]),
        .i_sfu(w_u_lrly1_c_isfu[2:0]),
        .imm1(w_u_lrly1_c_imm1[31:0]),
        .imm2(w_u_lrly1_c_imm2[31:0]),
        .kv_waddr(w_u_head1_kv_waddr),
        .kv_wdata(w_u_head1_kv_wdata),
        .kv_we(w_u_head1_kv_we),
        .l_fault(w_u_head1_l_fault),
        .l_last(w_u_head1_l_last),
        .l_out(w_u_head1_l_out),
        .l_ov(w_u_head1_l_ov),
        .l_raddr(w_u_head1_l_raddr),
        .l_red(w_u_head1_l_red),
        .l_redsq(w_u_head1_l_redsq),
        .live(w_u_lrly1_c_live[0]),
        .ma(w_u_lrly1_c_ma[1:0]),
        .mb(w_u_lrly1_c_mb[1:0]),
        .mc(w_u_lrly1_c_mc[0]),
        .md(w_u_lrly1_c_md[0]),
        .red(w_u_lrly1_c_red[1:0]),
        .redsq(w_u_lrly1_c_redsq[0]),
        .retire(w_u_head1_retire),
        .rrow(w_u_lrly1_c_rrow[23:0]),
        .rst_n(rst_n),
        .sx_exp_v(w_u_head1_sx_exp_v),
        .sx_exp_x(w_u_head1_sx_exp_x),
        .sx_rcp_v(w_u_head1_sx_rcp_v),
        .sx_rcp_x(w_u_head1_sx_rcp_x),
        .sx_rsq_v(w_u_head1_sx_rsq_v),
        .sx_rsq_x(w_u_head1_sx_rsq_x),
        .sy_exp_f(w_u_exp1_fault[0]),
        .sy_exp_vo(w_u_exp1_vo[0]),
        .sy_exp_y(w_u_exp1_y[31:0]),
        .sy_rcp_f(w_u_rcp1_fault[0]),
        .sy_rcp_y(w_u_rcp1_y[31:0]),
        .sy_rsq_f(w_u_rsq1_fault[0]),
        .sy_rsq_y(w_u_rsq1_y[31:0]),
        .va_addr(w_u_head1_va_addr),
        .va_q(w_u_lrly1_c_va[31:0]),
        .va_re(w_u_head1_va_re),
        .vb_addr(w_u_head1_vb_addr),
        .vb_q(w_u_lrly1_c_vb[31:0]),
        .vb_re(w_u_head1_vb_re),
        .vc_addr(w_u_head1_vc_addr),
        .vc_q(w_u_lrly1_c_vc[31:0]),
        .vc_re(w_u_head1_vc_re),
        .vm_waddr(w_u_head1_vm_waddr),
        .vm_wdata(w_u_head1_vm_wdata),
        .vm_we(w_u_head1_vm_we),
        .wrom_addr(w_u_head1_wrom_addr),
        .wrom_q(w_u_lrly1_c_wrom[255:0]),
        .wrom_re(w_u_head1_wrom_re)
    );
qfd_dv_s5_lrly u_u_lrly1 (
        .c_accept(w_u_lrly1_c_accept),
        .c_ad(w_u_lrly1_c_ad),
        .c_asi(w_u_lrly1_c_asi),
        .c_asrc(w_u_lrly1_c_asrc),
        .c_bsi(w_u_lrly1_c_bsi),
        .c_bsrc(w_u_lrly1_c_bsrc),
        .c_cls(w_u_lrly1_c_cls),
        .c_crom(w_u_lrly1_c_crom),
        .c_csi(w_u_lrly1_c_csi),
        .c_csrc(w_u_lrly1_c_csrc),
        .c_cura(w_u_lrly1_c_cura),
        .c_curb(w_u_lrly1_c_curb),
        .c_curc(w_u_lrly1_c_curc),
        .c_curd(w_u_lrly1_c_curd),
        .c_dsi(w_u_lrly1_c_dsi),
        .c_dst(w_u_lrly1_c_dst),
        .c_emit0(w_u_lrly1_c_emit0),
        .c_fin_th(w_u_lrly1_c_fin_th),
        .c_i(w_u_lrly1_c_i),
        .c_ilast(w_u_lrly1_c_ilast),
        .c_imm1(w_u_lrly1_c_imm1),
        .c_imm2(w_u_lrly1_c_imm2),
        .c_isfu(w_u_lrly1_c_isfu),
        .c_live(w_u_lrly1_c_live),
        .c_ma(w_u_lrly1_c_ma),
        .c_mb(w_u_lrly1_c_mb),
        .c_mc(w_u_lrly1_c_mc),
        .c_md(w_u_lrly1_c_md),
        .c_red(w_u_lrly1_c_red),
        .c_redsq(w_u_lrly1_c_redsq),
        .c_rrow(w_u_lrly1_c_rrow),
        .c_va(w_u_lrly1_c_va),
        .c_vb(w_u_lrly1_c_vb),
        .c_vc(w_u_lrly1_c_vc),
        .c_wrom(w_u_lrly1_c_wrom),
        .ck(clk),
        .cr_q(x_su_c_i_q[127:64]),
        .crom_addr(w_u_lrly1_crom_addr),
        .crom_re(w_u_lrly1_crom_re),
        .gb(x_su_c_i_q[755:256]),
        .gv(x_su_c_i_q[758:756]),
        .h_crom_addr(w_u_head1_crom_addr[23:0]),
        .h_crom_re(w_u_head1_crom_re[0]),
        .h_kv_waddr(w_u_head1_kv_waddr[23:0]),
        .h_kv_wdata(w_u_head1_kv_wdata[31:0]),
        .h_kv_we(w_u_head1_kv_we[0]),
        .h_l_fault(w_u_head1_l_fault[0]),
        .h_l_last(w_u_head1_l_last[0]),
        .h_l_out(w_u_head1_l_out[31:0]),
        .h_l_ov(w_u_head1_l_ov[0]),
        .h_l_raddr(w_u_head1_l_raddr[23:0]),
        .h_l_red(w_u_head1_l_red[1:0]),
        .h_l_redsq(w_u_head1_l_redsq[0]),
        .h_retire(w_u_head1_retire[0]),
        .h_rst_n(w_u_lrly1_h_rst_n),
        .h_va_addr(w_u_head1_va_addr[23:0]),
        .h_va_re(w_u_head1_va_re[0]),
        .h_vb_addr(w_u_head1_vb_addr[23:0]),
        .h_vb_re(w_u_head1_vb_re[0]),
        .h_vc_addr(w_u_head1_vc_addr[23:0]),
        .h_vc_re(w_u_head1_vc_re[0]),
        .h_vm_waddr(w_u_head1_vm_waddr[23:0]),
        .h_vm_wdata(w_u_head1_vm_wdata[31:0]),
        .h_vm_we(w_u_head1_vm_we[0]),
        .h_wrom_addr(w_u_head1_wrom_addr[23:0]),
        .h_wrom_re(w_u_head1_wrom_re[0]),
        .kv_waddr(w_u_lrly1_kv_waddr),
        .kv_wdata(w_u_lrly1_kv_wdata),
        .kv_we(w_u_lrly1_kv_we),
        .l_fault(w_u_lrly1_l_fault),
        .l_last(w_u_lrly1_l_last),
        .l_out(w_u_lrly1_l_out),
        .l_ov(w_u_lrly1_l_ov),
        .l_raddr(w_u_lrly1_l_raddr),
        .l_red(w_u_lrly1_l_red),
        .l_redsq(w_u_lrly1_l_redsq),
        .lv1(x_su_c_i_q[760]),
        .pd1(x_su_c_p1_i_q[188:93]),
        .retire(w_u_lrly1_retire),
        .rst_n(rst_n),
        .va_addr(w_u_lrly1_va_addr),
        .va_q(x_su_c_p1_i_q[444:413]),
        .va_re(w_u_lrly1_va_re),
        .vb_addr(w_u_lrly1_vb_addr),
        .vb_q(x_su_c_p1_i_q[572:541]),
        .vb_re(w_u_lrly1_vb_re),
        .vc_addr(w_u_lrly1_vc_addr),
        .vc_q(x_su_c_p1_i_q[700:669]),
        .vc_re(w_u_lrly1_vc_re),
        .vm_waddr(w_u_lrly1_vm_waddr),
        .vm_wdata(w_u_lrly1_vm_wdata),
        .vm_we(w_u_lrly1_vm_we),
        .wrom_addr(w_u_lrly1_wrom_addr),
        .wrom_re(w_u_lrly1_wrom_re)
    );
ot_hdc_sfu_rcp_t u_u_rcp1 (
        .clk(clk),
        .fault(w_u_rcp1_fault),
        .rst_n(rst_n),
        .v(w_u_head1_sx_rcp_v[0]),
        .vo(w_u_rcp1_vo),
        .x(w_u_head1_sx_rcp_x[31:0]),
        .y(w_u_rcp1_y)
    );
ot_hdc_sfu_rsq_t u_u_rsq1 (
        .clk(clk),
        .fault(w_u_rsq1_fault),
        .rst_n(rst_n),
        .v(w_u_head1_sx_rsq_v[0]),
        .vo(w_u_rsq1_vo),
        .x(w_u_head1_sx_rsq_x[31:0]),
        .y(w_u_rsq1_y)
    );
assign ctl_o = {w_u_lrly1_vm_we[0], w_u_lrly1_vm_wdata[31], w_u_lrly1_vm_wdata[30], w_u_lrly1_vm_wdata[29], w_u_lrly1_vm_wdata[28], w_u_lrly1_vm_wdata[27], w_u_lrly1_vm_wdata[26], w_u_lrly1_vm_wdata[25], w_u_lrly1_vm_wdata[24], w_u_lrly1_vm_wdata[23], w_u_lrly1_vm_wdata[22], w_u_lrly1_vm_wdata[21], w_u_lrly1_vm_wdata[20], w_u_lrly1_vm_wdata[19], w_u_lrly1_vm_wdata[18], w_u_lrly1_vm_wdata[17], w_u_lrly1_vm_wdata[16], w_u_lrly1_vm_wdata[15], w_u_lrly1_vm_wdata[14], w_u_lrly1_vm_wdata[13], w_u_lrly1_vm_wdata[12], w_u_lrly1_vm_wdata[11], w_u_lrly1_vm_wdata[10], w_u_lrly1_vm_wdata[9], w_u_lrly1_vm_wdata[8], w_u_lrly1_vm_wdata[7], w_u_lrly1_vm_wdata[6], w_u_lrly1_vm_wdata[5], w_u_lrly1_vm_wdata[4], w_u_lrly1_vm_wdata[3], w_u_lrly1_vm_wdata[2], w_u_lrly1_vm_wdata[1], w_u_lrly1_vm_wdata[0], w_u_lrly1_vm_waddr[23], w_u_lrly1_vm_waddr[22], w_u_lrly1_vm_waddr[21], w_u_lrly1_vm_waddr[20], w_u_lrly1_vm_waddr[19], w_u_lrly1_vm_waddr[18], w_u_lrly1_vm_waddr[17], w_u_lrly1_vm_waddr[16], w_u_lrly1_vm_waddr[15], w_u_lrly1_vm_waddr[14], w_u_lrly1_vm_waddr[13], w_u_lrly1_vm_waddr[12], w_u_lrly1_vm_waddr[11], w_u_lrly1_vm_waddr[10], w_u_lrly1_vm_waddr[9], w_u_lrly1_vm_waddr[8], w_u_lrly1_vm_waddr[7], w_u_lrly1_vm_waddr[6], w_u_lrly1_vm_waddr[5], w_u_lrly1_vm_waddr[4], w_u_lrly1_vm_waddr[3], w_u_lrly1_vm_waddr[2], w_u_lrly1_vm_waddr[1], w_u_lrly1_vm_waddr[0], w_u_lrly1_kv_we[0], w_u_lrly1_kv_wdata[31], w_u_lrly1_kv_wdata[30], w_u_lrly1_kv_wdata[29], w_u_lrly1_kv_wdata[28], w_u_lrly1_kv_wdata[27], w_u_lrly1_kv_wdata[26], w_u_lrly1_kv_wdata[25], w_u_lrly1_kv_wdata[24], w_u_lrly1_kv_wdata[23], w_u_lrly1_kv_wdata[22], w_u_lrly1_kv_wdata[21], w_u_lrly1_kv_wdata[20], w_u_lrly1_kv_wdata[19], w_u_lrly1_kv_wdata[18], w_u_lrly1_kv_wdata[17], w_u_lrly1_kv_wdata[16], w_u_lrly1_kv_wdata[15], w_u_lrly1_kv_wdata[14], w_u_lrly1_kv_wdata[13], w_u_lrly1_kv_wdata[12], w_u_lrly1_kv_wdata[11], w_u_lrly1_kv_wdata[10], w_u_lrly1_kv_wdata[9], w_u_lrly1_kv_wdata[8], w_u_lrly1_kv_wdata[7], w_u_lrly1_kv_wdata[6], w_u_lrly1_kv_wdata[5], w_u_lrly1_kv_wdata[4], w_u_lrly1_kv_wdata[3], w_u_lrly1_kv_wdata[2], w_u_lrly1_kv_wdata[1], w_u_lrly1_kv_wdata[0], w_u_lrly1_kv_waddr[23], w_u_lrly1_kv_waddr[22], w_u_lrly1_kv_waddr[21], w_u_lrly1_kv_waddr[20], w_u_lrly1_kv_waddr[19], w_u_lrly1_kv_waddr[18], w_u_lrly1_kv_waddr[17], w_u_lrly1_kv_waddr[16], w_u_lrly1_kv_waddr[15], w_u_lrly1_kv_waddr[14], w_u_lrly1_kv_waddr[13], w_u_lrly1_kv_waddr[12], w_u_lrly1_kv_waddr[11], w_u_lrly1_kv_waddr[10], w_u_lrly1_kv_waddr[9], w_u_lrly1_kv_waddr[8], w_u_lrly1_kv_waddr[7], w_u_lrly1_kv_waddr[6], w_u_lrly1_kv_waddr[5], w_u_lrly1_kv_waddr[4], w_u_lrly1_kv_waddr[3], w_u_lrly1_kv_waddr[2], w_u_lrly1_kv_waddr[1], w_u_lrly1_kv_waddr[0]};
assign sc_o = {w_u_lrly1_vm_we[0]};
assign stm_o = {w_u_lrly1_vm_we[0], w_u_lrly1_vm_wdata[31], w_u_lrly1_vm_wdata[30], w_u_lrly1_vm_wdata[29], w_u_lrly1_vm_wdata[28], w_u_lrly1_vm_wdata[27], w_u_lrly1_vm_wdata[26], w_u_lrly1_vm_wdata[25], w_u_lrly1_vm_wdata[24], w_u_lrly1_vm_wdata[23], w_u_lrly1_vm_wdata[22], w_u_lrly1_vm_wdata[21], w_u_lrly1_vm_wdata[20], w_u_lrly1_vm_wdata[19], w_u_lrly1_vm_wdata[18], w_u_lrly1_vm_wdata[17], w_u_lrly1_vm_wdata[16], w_u_lrly1_vm_wdata[15], w_u_lrly1_vm_wdata[14], w_u_lrly1_vm_wdata[13], w_u_lrly1_vm_wdata[12], w_u_lrly1_vm_wdata[11], w_u_lrly1_vm_wdata[10], w_u_lrly1_vm_wdata[9], w_u_lrly1_vm_wdata[8], w_u_lrly1_vm_wdata[7], w_u_lrly1_vm_wdata[6], w_u_lrly1_vm_wdata[5], w_u_lrly1_vm_wdata[4], w_u_lrly1_vm_wdata[3], w_u_lrly1_vm_wdata[2], w_u_lrly1_vm_wdata[1], w_u_lrly1_vm_wdata[0], w_u_lrly1_vm_waddr[23], w_u_lrly1_vm_waddr[22], w_u_lrly1_vm_waddr[21], w_u_lrly1_vm_waddr[20], w_u_lrly1_vm_waddr[19], w_u_lrly1_vm_waddr[18], w_u_lrly1_vm_waddr[17], w_u_lrly1_vm_waddr[16], w_u_lrly1_vm_waddr[15], w_u_lrly1_vm_waddr[14], w_u_lrly1_vm_waddr[13], w_u_lrly1_vm_waddr[12], w_u_lrly1_vm_waddr[11], w_u_lrly1_vm_waddr[10], w_u_lrly1_vm_waddr[9], w_u_lrly1_vm_waddr[8], w_u_lrly1_vm_waddr[7], w_u_lrly1_vm_waddr[6], w_u_lrly1_vm_waddr[5], w_u_lrly1_vm_waddr[4], w_u_lrly1_vm_waddr[3], w_u_lrly1_vm_waddr[2], w_u_lrly1_vm_waddr[1], w_u_lrly1_vm_waddr[0]};
assign c_o = {w_u_lrly1_wrom_re[0], w_u_lrly1_wrom_addr[23], w_u_lrly1_wrom_addr[22], w_u_lrly1_wrom_addr[21], w_u_lrly1_wrom_addr[20], w_u_lrly1_wrom_addr[19], w_u_lrly1_wrom_addr[18], w_u_lrly1_wrom_addr[17], w_u_lrly1_wrom_addr[16], w_u_lrly1_wrom_addr[15], w_u_lrly1_wrom_addr[14], w_u_lrly1_wrom_addr[13], w_u_lrly1_wrom_addr[12], w_u_lrly1_wrom_addr[11], w_u_lrly1_wrom_addr[10], w_u_lrly1_wrom_addr[9], w_u_lrly1_wrom_addr[8], w_u_lrly1_wrom_addr[7], w_u_lrly1_wrom_addr[6], w_u_lrly1_wrom_addr[5], w_u_lrly1_wrom_addr[4], w_u_lrly1_wrom_addr[3], w_u_lrly1_wrom_addr[2], w_u_lrly1_wrom_addr[1], w_u_lrly1_wrom_addr[0], w_u_lrly1_vm_we[0], w_u_lrly1_vm_wdata[31], w_u_lrly1_vm_wdata[30], w_u_lrly1_vm_wdata[29], w_u_lrly1_vm_wdata[28], w_u_lrly1_vm_wdata[27], w_u_lrly1_vm_wdata[26], w_u_lrly1_vm_wdata[25], w_u_lrly1_vm_wdata[24], w_u_lrly1_vm_wdata[23], w_u_lrly1_vm_wdata[22], w_u_lrly1_vm_wdata[21], w_u_lrly1_vm_wdata[20], w_u_lrly1_vm_wdata[19], w_u_lrly1_vm_wdata[18], w_u_lrly1_vm_wdata[17], w_u_lrly1_vm_wdata[16], w_u_lrly1_vm_wdata[15], w_u_lrly1_vm_wdata[14], w_u_lrly1_vm_wdata[13], w_u_lrly1_vm_wdata[12], w_u_lrly1_vm_wdata[11], w_u_lrly1_vm_wdata[10], w_u_lrly1_vm_wdata[9], w_u_lrly1_vm_wdata[8], w_u_lrly1_vm_wdata[7], w_u_lrly1_vm_wdata[6], w_u_lrly1_vm_wdata[5], w_u_lrly1_vm_wdata[4], w_u_lrly1_vm_wdata[3], w_u_lrly1_vm_wdata[2], w_u_lrly1_vm_wdata[1], w_u_lrly1_vm_wdata[0], w_u_lrly1_vm_waddr[23], w_u_lrly1_vm_waddr[22], w_u_lrly1_vm_waddr[21], w_u_lrly1_vm_waddr[20], w_u_lrly1_vm_waddr[19], w_u_lrly1_vm_waddr[18], w_u_lrly1_vm_waddr[17], w_u_lrly1_vm_waddr[16], w_u_lrly1_vm_waddr[15], w_u_lrly1_vm_waddr[14], w_u_lrly1_vm_waddr[13], w_u_lrly1_vm_waddr[12], w_u_lrly1_vm_waddr[11], w_u_lrly1_vm_waddr[10], w_u_lrly1_vm_waddr[9], w_u_lrly1_vm_waddr[8], w_u_lrly1_vm_waddr[7], w_u_lrly1_vm_waddr[6], w_u_lrly1_vm_waddr[5], w_u_lrly1_vm_waddr[4], w_u_lrly1_vm_waddr[3], w_u_lrly1_vm_waddr[2], w_u_lrly1_vm_waddr[1], w_u_lrly1_vm_waddr[0], w_u_lrly1_vc_re[0], w_u_lrly1_vc_addr[23], w_u_lrly1_vc_addr[22], w_u_lrly1_vc_addr[21], w_u_lrly1_vc_addr[20], w_u_lrly1_vc_addr[19], w_u_lrly1_vc_addr[18], w_u_lrly1_vc_addr[17], w_u_lrly1_vc_addr[16], w_u_lrly1_vc_addr[15], w_u_lrly1_vc_addr[14], w_u_lrly1_vc_addr[13], w_u_lrly1_vc_addr[12], w_u_lrly1_vc_addr[11], w_u_lrly1_vc_addr[10], w_u_lrly1_vc_addr[9], w_u_lrly1_vc_addr[8], w_u_lrly1_vc_addr[7], w_u_lrly1_vc_addr[6], w_u_lrly1_vc_addr[5], w_u_lrly1_vc_addr[4], w_u_lrly1_vc_addr[3], w_u_lrly1_vc_addr[2], w_u_lrly1_vc_addr[1], w_u_lrly1_vc_addr[0], w_u_lrly1_vb_re[0], w_u_lrly1_vb_addr[23], w_u_lrly1_vb_addr[22], w_u_lrly1_vb_addr[21], w_u_lrly1_vb_addr[20], w_u_lrly1_vb_addr[19], w_u_lrly1_vb_addr[18], w_u_lrly1_vb_addr[17], w_u_lrly1_vb_addr[16], w_u_lrly1_vb_addr[15], w_u_lrly1_vb_addr[14], w_u_lrly1_vb_addr[13], w_u_lrly1_vb_addr[12], w_u_lrly1_vb_addr[11], w_u_lrly1_vb_addr[10], w_u_lrly1_vb_addr[9], w_u_lrly1_vb_addr[8], w_u_lrly1_vb_addr[7], w_u_lrly1_vb_addr[6], w_u_lrly1_vb_addr[5], w_u_lrly1_vb_addr[4], w_u_lrly1_vb_addr[3], w_u_lrly1_vb_addr[2], w_u_lrly1_vb_addr[1], w_u_lrly1_vb_addr[0], w_u_lrly1_va_re[0], w_u_lrly1_va_addr[23], w_u_lrly1_va_addr[22], w_u_lrly1_va_addr[21], w_u_lrly1_va_addr[20], w_u_lrly1_va_addr[19], w_u_lrly1_va_addr[18], w_u_lrly1_va_addr[17], w_u_lrly1_va_addr[16], w_u_lrly1_va_addr[15], w_u_lrly1_va_addr[14], w_u_lrly1_va_addr[13], w_u_lrly1_va_addr[12], w_u_lrly1_va_addr[11], w_u_lrly1_va_addr[10], w_u_lrly1_va_addr[9], w_u_lrly1_va_addr[8], w_u_lrly1_va_addr[7], w_u_lrly1_va_addr[6], w_u_lrly1_va_addr[5], w_u_lrly1_va_addr[4], w_u_lrly1_va_addr[3], w_u_lrly1_va_addr[2], w_u_lrly1_va_addr[1], w_u_lrly1_va_addr[0], w_u_lrly1_retire[0], w_u_lrly1_l_ov[0], w_u_lrly1_l_out[31], w_u_lrly1_l_out[30], w_u_lrly1_l_out[29], w_u_lrly1_l_out[28], w_u_lrly1_l_out[27], w_u_lrly1_l_out[26], w_u_lrly1_l_out[25], w_u_lrly1_l_out[24], w_u_lrly1_l_out[23], w_u_lrly1_l_out[22], w_u_lrly1_l_out[21], w_u_lrly1_l_out[20], w_u_lrly1_l_out[19], w_u_lrly1_l_out[18], w_u_lrly1_l_out[17], w_u_lrly1_l_out[16], w_u_lrly1_l_out[15], w_u_lrly1_l_out[14], w_u_lrly1_l_out[13], w_u_lrly1_l_out[12], w_u_lrly1_l_out[11], w_u_lrly1_l_out[10], w_u_lrly1_l_out[9], w_u_lrly1_l_out[8], w_u_lrly1_l_out[7], w_u_lrly1_l_out[6], w_u_lrly1_l_out[5], w_u_lrly1_l_out[4], w_u_lrly1_l_out[3], w_u_lrly1_l_out[2], w_u_lrly1_l_out[1], w_u_lrly1_l_out[0], w_u_lrly1_l_last[0], w_u_lrly1_l_fault[0], w_u_lrly1_kv_we[0], w_u_lrly1_crom_re[0], w_u_lrly1_crom_addr[23], w_u_lrly1_crom_addr[22], w_u_lrly1_crom_addr[21], w_u_lrly1_crom_addr[20], w_u_lrly1_crom_addr[19], w_u_lrly1_crom_addr[18], w_u_lrly1_crom_addr[17], w_u_lrly1_crom_addr[16], w_u_lrly1_crom_addr[15], w_u_lrly1_crom_addr[14], w_u_lrly1_crom_addr[13], w_u_lrly1_crom_addr[12], w_u_lrly1_crom_addr[11], w_u_lrly1_crom_addr[10], w_u_lrly1_crom_addr[9], w_u_lrly1_crom_addr[8], w_u_lrly1_crom_addr[7], w_u_lrly1_crom_addr[6], w_u_lrly1_crom_addr[5], w_u_lrly1_crom_addr[4], w_u_lrly1_crom_addr[3], w_u_lrly1_crom_addr[2], w_u_lrly1_crom_addr[1], w_u_lrly1_crom_addr[0]};
endmodule

module ref_2 (input wire clk, input wire rst_n, input wire [758:0] c_i, output wire [113:0] ctl_o, output wire [0:0] sc_o, output wire [56:0] stm_o, output wire [218:0] c_o);
wire [0:0] w_u_exp4_fault;
wire [0:0] w_u_exp4_vo;
wire [31:0] w_u_exp4_y;
wire [23:0] w_u_head4_crom_addr;
wire [0:0] w_u_head4_crom_re;
wire [23:0] w_u_head4_kv_waddr;
wire [31:0] w_u_head4_kv_wdata;
wire [0:0] w_u_head4_kv_we;
wire [0:0] w_u_head4_l_fault;
wire [0:0] w_u_head4_l_last;
wire [31:0] w_u_head4_l_out;
wire [0:0] w_u_head4_l_ov;
wire [23:0] w_u_head4_l_raddr;
wire [1:0] w_u_head4_l_red;
wire [0:0] w_u_head4_l_redsq;
wire [0:0] w_u_head4_retire;
wire [0:0] w_u_head4_sx_exp_v;
wire [31:0] w_u_head4_sx_exp_x;
wire [0:0] w_u_head4_sx_rcp_v;
wire [31:0] w_u_head4_sx_rcp_x;
wire [0:0] w_u_head4_sx_rsq_v;
wire [31:0] w_u_head4_sx_rsq_x;
wire [23:0] w_u_head4_va_addr;
wire [0:0] w_u_head4_va_re;
wire [23:0] w_u_head4_vb_addr;
wire [0:0] w_u_head4_vb_re;
wire [23:0] w_u_head4_vc_addr;
wire [0:0] w_u_head4_vc_re;
wire [23:0] w_u_head4_vm_waddr;
wire [31:0] w_u_head4_vm_wdata;
wire [0:0] w_u_head4_vm_we;
wire [23:0] w_u_head4_wrom_addr;
wire [0:0] w_u_head4_wrom_re;
wire [0:0] w_u_lrly4_c_accept;
wire [2:0] w_u_lrly4_c_ad;
wire [23:0] w_u_lrly4_c_asi;
wire [0:0] w_u_lrly4_c_asrc;
wire [23:0] w_u_lrly4_c_bsi;
wire [0:0] w_u_lrly4_c_bsrc;
wire [2:0] w_u_lrly4_c_cls;
wire [63:0] w_u_lrly4_c_crom;
wire [23:0] w_u_lrly4_c_csi;
wire [0:0] w_u_lrly4_c_csrc;
wire [23:0] w_u_lrly4_c_cura;
wire [23:0] w_u_lrly4_c_curb;
wire [23:0] w_u_lrly4_c_curc;
wire [23:0] w_u_lrly4_c_curd;
wire [23:0] w_u_lrly4_c_dsi;
wire [1:0] w_u_lrly4_c_dst;
wire [0:0] w_u_lrly4_c_emit0;
wire [18:0] w_u_lrly4_c_fin_th;
wire [17:0] w_u_lrly4_c_i;
wire [0:0] w_u_lrly4_c_ilast;
wire [31:0] w_u_lrly4_c_imm1;
wire [31:0] w_u_lrly4_c_imm2;
wire [2:0] w_u_lrly4_c_isfu;
wire [0:0] w_u_lrly4_c_live;
wire [1:0] w_u_lrly4_c_ma;
wire [1:0] w_u_lrly4_c_mb;
wire [0:0] w_u_lrly4_c_mc;
wire [0:0] w_u_lrly4_c_md;
wire [1:0] w_u_lrly4_c_red;
wire [0:0] w_u_lrly4_c_redsq;
wire [23:0] w_u_lrly4_c_rrow;
wire [31:0] w_u_lrly4_c_va;
wire [31:0] w_u_lrly4_c_vb;
wire [31:0] w_u_lrly4_c_vc;
wire [255:0] w_u_lrly4_c_wrom;
wire [23:0] w_u_lrly4_crom_addr;
wire [0:0] w_u_lrly4_crom_re;
wire [0:0] w_u_lrly4_h_rst_n;
wire [23:0] w_u_lrly4_kv_waddr;
wire [31:0] w_u_lrly4_kv_wdata;
wire [0:0] w_u_lrly4_kv_we;
wire [0:0] w_u_lrly4_l_fault;
wire [0:0] w_u_lrly4_l_last;
wire [31:0] w_u_lrly4_l_out;
wire [0:0] w_u_lrly4_l_ov;
wire [23:0] w_u_lrly4_l_raddr;
wire [1:0] w_u_lrly4_l_red;
wire [0:0] w_u_lrly4_l_redsq;
wire [0:0] w_u_lrly4_retire;
wire [23:0] w_u_lrly4_va_addr;
wire [0:0] w_u_lrly4_va_re;
wire [23:0] w_u_lrly4_vb_addr;
wire [0:0] w_u_lrly4_vb_re;
wire [23:0] w_u_lrly4_vc_addr;
wire [0:0] w_u_lrly4_vc_re;
wire [23:0] w_u_lrly4_vm_waddr;
wire [31:0] w_u_lrly4_vm_wdata;
wire [0:0] w_u_lrly4_vm_we;
wire [23:0] w_u_lrly4_wrom_addr;
wire [0:0] w_u_lrly4_wrom_re;
wire [0:0] w_u_rcp4_fault;
wire [0:0] w_u_rcp4_vo;
wire [31:0] w_u_rcp4_y;
wire [0:0] w_u_rsq4_fault;
wire [0:0] w_u_rsq4_vo;
wire [31:0] w_u_rsq4_y;
wire [765:0] x_su_c_i_q;
wire [0:0] x_su_c_i_eq;
wire [763:0] x_su_c_p1_i_q;
wire [0:0] x_su_c_p1_i_eq;
assign {x_su_c_i_q[62:0], flt_su_c_i_q[0]} = c_i[0 +: 63];
assign x_su_c_i_q[754:255] = c_i[63 +: 500];
assign x_su_c_i_q[757:755] = c_i[563 +: 3];
assign x_su_c_i_q[758] = c_i[566 +: 1];
assign {x_su_c_p1_i_q[91:0], x_su_c_i_q[765:762]} = c_i[567 +: 96];
assign x_su_c_p1_i_q[411:380] = c_i[663 +: 32];
assign x_su_c_p1_i_q[539:508] = c_i[695 +: 32];
assign x_su_c_p1_i_q[667:636] = c_i[727 +: 32];
ot_hdc_sfu_exp_t u_u_exp4 (
        .clk(clk),
        .fault(w_u_exp4_fault),
        .rst_n(rst_n),
        .v(w_u_head4_sx_exp_v[0]),
        .vo(w_u_exp4_vo),
        .x(w_u_head4_sx_exp_x[31:0]),
        .y(w_u_exp4_y)
    );
qfd_dv_lane_h_safe2 u_u_head4 (
        .accept(w_u_lrly4_c_accept[0]),
        .ad(w_u_lrly4_c_ad[2:0]),
        .asi(w_u_lrly4_c_asi[23:0]),
        .asrc(w_u_lrly4_c_asrc[0]),
        .bsi(w_u_lrly4_c_bsi[23:0]),
        .bsrc(w_u_lrly4_c_bsrc[0]),
        .clk(clk),
        .cls(w_u_lrly4_c_cls[2:0]),
        .crom_addr(w_u_head4_crom_addr),
        .crom_q(w_u_lrly4_c_crom[63:0]),
        .crom_re(w_u_head4_crom_re),
        .csi(w_u_lrly4_c_csi[23:0]),
        .csrc(w_u_lrly4_c_csrc[0]),
        .cura0(w_u_lrly4_c_cura[23:0]),
        .curb0(w_u_lrly4_c_curb[23:0]),
        .curc0(w_u_lrly4_c_curc[23:0]),
        .curd0(w_u_lrly4_c_curd[23:0]),
        .dsi(w_u_lrly4_c_dsi[23:0]),
        .dst(w_u_lrly4_c_dst[1:0]),
        .emit0(w_u_lrly4_c_emit0[0]),
        .fin_th(w_u_lrly4_c_fin_th[18:0]),
        .i(w_u_lrly4_c_i[17:0]),
        .i_last_r(w_u_lrly4_c_ilast[0]),
        .i_sfu(w_u_lrly4_c_isfu[2:0]),
        .imm1(w_u_lrly4_c_imm1[31:0]),
        .imm2(w_u_lrly4_c_imm2[31:0]),
        .kv_waddr(w_u_head4_kv_waddr),
        .kv_wdata(w_u_head4_kv_wdata),
        .kv_we(w_u_head4_kv_we),
        .l_fault(w_u_head4_l_fault),
        .l_last(w_u_head4_l_last),
        .l_out(w_u_head4_l_out),
        .l_ov(w_u_head4_l_ov),
        .l_raddr(w_u_head4_l_raddr),
        .l_red(w_u_head4_l_red),
        .l_redsq(w_u_head4_l_redsq),
        .live(w_u_lrly4_c_live[0]),
        .ma(w_u_lrly4_c_ma[1:0]),
        .mb(w_u_lrly4_c_mb[1:0]),
        .mc(w_u_lrly4_c_mc[0]),
        .md(w_u_lrly4_c_md[0]),
        .red(w_u_lrly4_c_red[1:0]),
        .redsq(w_u_lrly4_c_redsq[0]),
        .retire(w_u_head4_retire),
        .rrow(w_u_lrly4_c_rrow[23:0]),
        .rst_n(rst_n),
        .sx_exp_v(w_u_head4_sx_exp_v),
        .sx_exp_x(w_u_head4_sx_exp_x),
        .sx_rcp_v(w_u_head4_sx_rcp_v),
        .sx_rcp_x(w_u_head4_sx_rcp_x),
        .sx_rsq_v(w_u_head4_sx_rsq_v),
        .sx_rsq_x(w_u_head4_sx_rsq_x),
        .sy_exp_f(w_u_exp4_fault[0]),
        .sy_exp_vo(w_u_exp4_vo[0]),
        .sy_exp_y(w_u_exp4_y[31:0]),
        .sy_rcp_f(w_u_rcp4_fault[0]),
        .sy_rcp_y(w_u_rcp4_y[31:0]),
        .sy_rsq_f(w_u_rsq4_fault[0]),
        .sy_rsq_y(w_u_rsq4_y[31:0]),
        .va_addr(w_u_head4_va_addr),
        .va_q(w_u_lrly4_c_va[31:0]),
        .va_re(w_u_head4_va_re),
        .vb_addr(w_u_head4_vb_addr),
        .vb_q(w_u_lrly4_c_vb[31:0]),
        .vb_re(w_u_head4_vb_re),
        .vc_addr(w_u_head4_vc_addr),
        .vc_q(w_u_lrly4_c_vc[31:0]),
        .vc_re(w_u_head4_vc_re),
        .vm_waddr(w_u_head4_vm_waddr),
        .vm_wdata(w_u_head4_vm_wdata),
        .vm_we(w_u_head4_vm_we),
        .wrom_addr(w_u_head4_wrom_addr),
        .wrom_q(w_u_lrly4_c_wrom[255:0]),
        .wrom_re(w_u_head4_wrom_re)
    );
qfd_dv_s5_lrly u_u_lrly4 (
        .c_accept(w_u_lrly4_c_accept),
        .c_ad(w_u_lrly4_c_ad),
        .c_asi(w_u_lrly4_c_asi),
        .c_asrc(w_u_lrly4_c_asrc),
        .c_bsi(w_u_lrly4_c_bsi),
        .c_bsrc(w_u_lrly4_c_bsrc),
        .c_cls(w_u_lrly4_c_cls),
        .c_crom(w_u_lrly4_c_crom),
        .c_csi(w_u_lrly4_c_csi),
        .c_csrc(w_u_lrly4_c_csrc),
        .c_cura(w_u_lrly4_c_cura),
        .c_curb(w_u_lrly4_c_curb),
        .c_curc(w_u_lrly4_c_curc),
        .c_curd(w_u_lrly4_c_curd),
        .c_dsi(w_u_lrly4_c_dsi),
        .c_dst(w_u_lrly4_c_dst),
        .c_emit0(w_u_lrly4_c_emit0),
        .c_fin_th(w_u_lrly4_c_fin_th),
        .c_i(w_u_lrly4_c_i),
        .c_ilast(w_u_lrly4_c_ilast),
        .c_imm1(w_u_lrly4_c_imm1),
        .c_imm2(w_u_lrly4_c_imm2),
        .c_isfu(w_u_lrly4_c_isfu),
        .c_live(w_u_lrly4_c_live),
        .c_ma(w_u_lrly4_c_ma),
        .c_mb(w_u_lrly4_c_mb),
        .c_mc(w_u_lrly4_c_mc),
        .c_md(w_u_lrly4_c_md),
        .c_red(w_u_lrly4_c_red),
        .c_redsq(w_u_lrly4_c_redsq),
        .c_rrow(w_u_lrly4_c_rrow),
        .c_va(w_u_lrly4_c_va),
        .c_vb(w_u_lrly4_c_vb),
        .c_vc(w_u_lrly4_c_vc),
        .c_wrom(w_u_lrly4_c_wrom),
        .ck(clk),
        .cr_q({x_su_c_i_q[62:0], flt_su_c_i_q[0]}),
        .crom_addr(w_u_lrly4_crom_addr),
        .crom_re(w_u_lrly4_crom_re),
        .gb(x_su_c_i_q[754:255]),
        .gv(x_su_c_i_q[757:755]),
        .h_crom_addr(w_u_head4_crom_addr[23:0]),
        .h_crom_re(w_u_head4_crom_re[0]),
        .h_kv_waddr(w_u_head4_kv_waddr[23:0]),
        .h_kv_wdata(w_u_head4_kv_wdata[31:0]),
        .h_kv_we(w_u_head4_kv_we[0]),
        .h_l_fault(w_u_head4_l_fault[0]),
        .h_l_last(w_u_head4_l_last[0]),
        .h_l_out(w_u_head4_l_out[31:0]),
        .h_l_ov(w_u_head4_l_ov[0]),
        .h_l_raddr(w_u_head4_l_raddr[23:0]),
        .h_l_red(w_u_head4_l_red[1:0]),
        .h_l_redsq(w_u_head4_l_redsq[0]),
        .h_retire(w_u_head4_retire[0]),
        .h_rst_n(w_u_lrly4_h_rst_n),
        .h_va_addr(w_u_head4_va_addr[23:0]),
        .h_va_re(w_u_head4_va_re[0]),
        .h_vb_addr(w_u_head4_vb_addr[23:0]),
        .h_vb_re(w_u_head4_vb_re[0]),
        .h_vc_addr(w_u_head4_vc_addr[23:0]),
        .h_vc_re(w_u_head4_vc_re[0]),
        .h_vm_waddr(w_u_head4_vm_waddr[23:0]),
        .h_vm_wdata(w_u_head4_vm_wdata[31:0]),
        .h_vm_we(w_u_head4_vm_we[0]),
        .h_wrom_addr(w_u_head4_wrom_addr[23:0]),
        .h_wrom_re(w_u_head4_wrom_re[0]),
        .kv_waddr(w_u_lrly4_kv_waddr),
        .kv_wdata(w_u_lrly4_kv_wdata),
        .kv_we(w_u_lrly4_kv_we),
        .l_fault(w_u_lrly4_l_fault),
        .l_last(w_u_lrly4_l_last),
        .l_out(w_u_lrly4_l_out),
        .l_ov(w_u_lrly4_l_ov),
        .l_raddr(w_u_lrly4_l_raddr),
        .l_red(w_u_lrly4_l_red),
        .l_redsq(w_u_lrly4_l_redsq),
        .lv1(x_su_c_i_q[758]),
        .pd1({x_su_c_p1_i_q[91:0], x_su_c_i_q[765:762]}),
        .retire(w_u_lrly4_retire),
        .rst_n(rst_n),
        .va_addr(w_u_lrly4_va_addr),
        .va_q(x_su_c_p1_i_q[411:380]),
        .va_re(w_u_lrly4_va_re),
        .vb_addr(w_u_lrly4_vb_addr),
        .vb_q(x_su_c_p1_i_q[539:508]),
        .vb_re(w_u_lrly4_vb_re),
        .vc_addr(w_u_lrly4_vc_addr),
        .vc_q(x_su_c_p1_i_q[667:636]),
        .vc_re(w_u_lrly4_vc_re),
        .vm_waddr(w_u_lrly4_vm_waddr),
        .vm_wdata(w_u_lrly4_vm_wdata),
        .vm_we(w_u_lrly4_vm_we),
        .wrom_addr(w_u_lrly4_wrom_addr),
        .wrom_re(w_u_lrly4_wrom_re)
    );
ot_hdc_sfu_rcp_t u_u_rcp4 (
        .clk(clk),
        .fault(w_u_rcp4_fault),
        .rst_n(rst_n),
        .v(w_u_head4_sx_rcp_v[0]),
        .vo(w_u_rcp4_vo),
        .x(w_u_head4_sx_rcp_x[31:0]),
        .y(w_u_rcp4_y)
    );
ot_hdc_sfu_rsq_t u_u_rsq4 (
        .clk(clk),
        .fault(w_u_rsq4_fault),
        .rst_n(rst_n),
        .v(w_u_head4_sx_rsq_v[0]),
        .vo(w_u_rsq4_vo),
        .x(w_u_head4_sx_rsq_x[31:0]),
        .y(w_u_rsq4_y)
    );
assign ctl_o = {w_u_lrly4_vm_we[0], w_u_lrly4_vm_wdata[31], w_u_lrly4_vm_wdata[30], w_u_lrly4_vm_wdata[29], w_u_lrly4_vm_wdata[28], w_u_lrly4_vm_wdata[27], w_u_lrly4_vm_wdata[26], w_u_lrly4_vm_wdata[25], w_u_lrly4_vm_wdata[24], w_u_lrly4_vm_wdata[23], w_u_lrly4_vm_wdata[22], w_u_lrly4_vm_wdata[21], w_u_lrly4_vm_wdata[20], w_u_lrly4_vm_wdata[19], w_u_lrly4_vm_wdata[18], w_u_lrly4_vm_wdata[17], w_u_lrly4_vm_wdata[16], w_u_lrly4_vm_wdata[15], w_u_lrly4_vm_wdata[14], w_u_lrly4_vm_wdata[13], w_u_lrly4_vm_wdata[12], w_u_lrly4_vm_wdata[11], w_u_lrly4_vm_wdata[10], w_u_lrly4_vm_wdata[9], w_u_lrly4_vm_wdata[8], w_u_lrly4_vm_wdata[7], w_u_lrly4_vm_wdata[6], w_u_lrly4_vm_wdata[5], w_u_lrly4_vm_wdata[4], w_u_lrly4_vm_wdata[3], w_u_lrly4_vm_wdata[2], w_u_lrly4_vm_wdata[1], w_u_lrly4_vm_wdata[0], w_u_lrly4_vm_waddr[23], w_u_lrly4_vm_waddr[22], w_u_lrly4_vm_waddr[21], w_u_lrly4_vm_waddr[20], w_u_lrly4_vm_waddr[19], w_u_lrly4_vm_waddr[18], w_u_lrly4_vm_waddr[17], w_u_lrly4_vm_waddr[16], w_u_lrly4_vm_waddr[15], w_u_lrly4_vm_waddr[14], w_u_lrly4_vm_waddr[13], w_u_lrly4_vm_waddr[12], w_u_lrly4_vm_waddr[11], w_u_lrly4_vm_waddr[10], w_u_lrly4_vm_waddr[9], w_u_lrly4_vm_waddr[8], w_u_lrly4_vm_waddr[7], w_u_lrly4_vm_waddr[6], w_u_lrly4_vm_waddr[5], w_u_lrly4_vm_waddr[4], w_u_lrly4_vm_waddr[3], w_u_lrly4_vm_waddr[2], w_u_lrly4_vm_waddr[1], w_u_lrly4_vm_waddr[0], w_u_lrly4_kv_we[0], w_u_lrly4_kv_wdata[31], w_u_lrly4_kv_wdata[30], w_u_lrly4_kv_wdata[29], w_u_lrly4_kv_wdata[28], w_u_lrly4_kv_wdata[27], w_u_lrly4_kv_wdata[26], w_u_lrly4_kv_wdata[25], w_u_lrly4_kv_wdata[24], w_u_lrly4_kv_wdata[23], w_u_lrly4_kv_wdata[22], w_u_lrly4_kv_wdata[21], w_u_lrly4_kv_wdata[20], w_u_lrly4_kv_wdata[19], w_u_lrly4_kv_wdata[18], w_u_lrly4_kv_wdata[17], w_u_lrly4_kv_wdata[16], w_u_lrly4_kv_wdata[15], w_u_lrly4_kv_wdata[14], w_u_lrly4_kv_wdata[13], w_u_lrly4_kv_wdata[12], w_u_lrly4_kv_wdata[11], w_u_lrly4_kv_wdata[10], w_u_lrly4_kv_wdata[9], w_u_lrly4_kv_wdata[8], w_u_lrly4_kv_wdata[7], w_u_lrly4_kv_wdata[6], w_u_lrly4_kv_wdata[5], w_u_lrly4_kv_wdata[4], w_u_lrly4_kv_wdata[3], w_u_lrly4_kv_wdata[2], w_u_lrly4_kv_wdata[1], w_u_lrly4_kv_wdata[0], w_u_lrly4_kv_waddr[23], w_u_lrly4_kv_waddr[22], w_u_lrly4_kv_waddr[21], w_u_lrly4_kv_waddr[20], w_u_lrly4_kv_waddr[19], w_u_lrly4_kv_waddr[18], w_u_lrly4_kv_waddr[17], w_u_lrly4_kv_waddr[16], w_u_lrly4_kv_waddr[15], w_u_lrly4_kv_waddr[14], w_u_lrly4_kv_waddr[13], w_u_lrly4_kv_waddr[12], w_u_lrly4_kv_waddr[11], w_u_lrly4_kv_waddr[10], w_u_lrly4_kv_waddr[9], w_u_lrly4_kv_waddr[8], w_u_lrly4_kv_waddr[7], w_u_lrly4_kv_waddr[6], w_u_lrly4_kv_waddr[5], w_u_lrly4_kv_waddr[4], w_u_lrly4_kv_waddr[3], w_u_lrly4_kv_waddr[2], w_u_lrly4_kv_waddr[1], w_u_lrly4_kv_waddr[0]};
assign sc_o = {w_u_lrly4_vm_we[0]};
assign stm_o = {w_u_lrly4_vm_we[0], w_u_lrly4_vm_wdata[31], w_u_lrly4_vm_wdata[30], w_u_lrly4_vm_wdata[29], w_u_lrly4_vm_wdata[28], w_u_lrly4_vm_wdata[27], w_u_lrly4_vm_wdata[26], w_u_lrly4_vm_wdata[25], w_u_lrly4_vm_wdata[24], w_u_lrly4_vm_wdata[23], w_u_lrly4_vm_wdata[22], w_u_lrly4_vm_wdata[21], w_u_lrly4_vm_wdata[20], w_u_lrly4_vm_wdata[19], w_u_lrly4_vm_wdata[18], w_u_lrly4_vm_wdata[17], w_u_lrly4_vm_wdata[16], w_u_lrly4_vm_wdata[15], w_u_lrly4_vm_wdata[14], w_u_lrly4_vm_wdata[13], w_u_lrly4_vm_wdata[12], w_u_lrly4_vm_wdata[11], w_u_lrly4_vm_wdata[10], w_u_lrly4_vm_wdata[9], w_u_lrly4_vm_wdata[8], w_u_lrly4_vm_wdata[7], w_u_lrly4_vm_wdata[6], w_u_lrly4_vm_wdata[5], w_u_lrly4_vm_wdata[4], w_u_lrly4_vm_wdata[3], w_u_lrly4_vm_wdata[2], w_u_lrly4_vm_wdata[1], w_u_lrly4_vm_wdata[0], w_u_lrly4_vm_waddr[23], w_u_lrly4_vm_waddr[22], w_u_lrly4_vm_waddr[21], w_u_lrly4_vm_waddr[20], w_u_lrly4_vm_waddr[19], w_u_lrly4_vm_waddr[18], w_u_lrly4_vm_waddr[17], w_u_lrly4_vm_waddr[16], w_u_lrly4_vm_waddr[15], w_u_lrly4_vm_waddr[14], w_u_lrly4_vm_waddr[13], w_u_lrly4_vm_waddr[12], w_u_lrly4_vm_waddr[11], w_u_lrly4_vm_waddr[10], w_u_lrly4_vm_waddr[9], w_u_lrly4_vm_waddr[8], w_u_lrly4_vm_waddr[7], w_u_lrly4_vm_waddr[6], w_u_lrly4_vm_waddr[5], w_u_lrly4_vm_waddr[4], w_u_lrly4_vm_waddr[3], w_u_lrly4_vm_waddr[2], w_u_lrly4_vm_waddr[1], w_u_lrly4_vm_waddr[0]};
assign c_o = {w_u_lrly4_wrom_re[0], w_u_lrly4_wrom_addr[23], w_u_lrly4_wrom_addr[22], w_u_lrly4_wrom_addr[21], w_u_lrly4_wrom_addr[20], w_u_lrly4_wrom_addr[19], w_u_lrly4_wrom_addr[18], w_u_lrly4_wrom_addr[17], w_u_lrly4_wrom_addr[16], w_u_lrly4_wrom_addr[15], w_u_lrly4_wrom_addr[14], w_u_lrly4_wrom_addr[13], w_u_lrly4_wrom_addr[12], w_u_lrly4_wrom_addr[11], w_u_lrly4_wrom_addr[10], w_u_lrly4_wrom_addr[9], w_u_lrly4_wrom_addr[8], w_u_lrly4_wrom_addr[7], w_u_lrly4_wrom_addr[6], w_u_lrly4_wrom_addr[5], w_u_lrly4_wrom_addr[4], w_u_lrly4_wrom_addr[3], w_u_lrly4_wrom_addr[2], w_u_lrly4_wrom_addr[1], w_u_lrly4_wrom_addr[0], w_u_lrly4_vm_we[0], w_u_lrly4_vm_wdata[31], w_u_lrly4_vm_wdata[30], w_u_lrly4_vm_wdata[29], w_u_lrly4_vm_wdata[28], w_u_lrly4_vm_wdata[27], w_u_lrly4_vm_wdata[26], w_u_lrly4_vm_wdata[25], w_u_lrly4_vm_wdata[24], w_u_lrly4_vm_wdata[23], w_u_lrly4_vm_wdata[22], w_u_lrly4_vm_wdata[21], w_u_lrly4_vm_wdata[20], w_u_lrly4_vm_wdata[19], w_u_lrly4_vm_wdata[18], w_u_lrly4_vm_wdata[17], w_u_lrly4_vm_wdata[16], w_u_lrly4_vm_wdata[15], w_u_lrly4_vm_wdata[14], w_u_lrly4_vm_wdata[13], w_u_lrly4_vm_wdata[12], w_u_lrly4_vm_wdata[11], w_u_lrly4_vm_wdata[10], w_u_lrly4_vm_wdata[9], w_u_lrly4_vm_wdata[8], w_u_lrly4_vm_wdata[7], w_u_lrly4_vm_wdata[6], w_u_lrly4_vm_wdata[5], w_u_lrly4_vm_wdata[4], w_u_lrly4_vm_wdata[3], w_u_lrly4_vm_wdata[2], w_u_lrly4_vm_wdata[1], w_u_lrly4_vm_wdata[0], w_u_lrly4_vm_waddr[23], w_u_lrly4_vm_waddr[22], w_u_lrly4_vm_waddr[21], w_u_lrly4_vm_waddr[20], w_u_lrly4_vm_waddr[19], w_u_lrly4_vm_waddr[18], w_u_lrly4_vm_waddr[17], w_u_lrly4_vm_waddr[16], w_u_lrly4_vm_waddr[15], w_u_lrly4_vm_waddr[14], w_u_lrly4_vm_waddr[13], w_u_lrly4_vm_waddr[12], w_u_lrly4_vm_waddr[11], w_u_lrly4_vm_waddr[10], w_u_lrly4_vm_waddr[9], w_u_lrly4_vm_waddr[8], w_u_lrly4_vm_waddr[7], w_u_lrly4_vm_waddr[6], w_u_lrly4_vm_waddr[5], w_u_lrly4_vm_waddr[4], w_u_lrly4_vm_waddr[3], w_u_lrly4_vm_waddr[2], w_u_lrly4_vm_waddr[1], w_u_lrly4_vm_waddr[0], w_u_lrly4_vc_re[0], w_u_lrly4_vc_addr[23], w_u_lrly4_vc_addr[22], w_u_lrly4_vc_addr[21], w_u_lrly4_vc_addr[20], w_u_lrly4_vc_addr[19], w_u_lrly4_vc_addr[18], w_u_lrly4_vc_addr[17], w_u_lrly4_vc_addr[16], w_u_lrly4_vc_addr[15], w_u_lrly4_vc_addr[14], w_u_lrly4_vc_addr[13], w_u_lrly4_vc_addr[12], w_u_lrly4_vc_addr[11], w_u_lrly4_vc_addr[10], w_u_lrly4_vc_addr[9], w_u_lrly4_vc_addr[8], w_u_lrly4_vc_addr[7], w_u_lrly4_vc_addr[6], w_u_lrly4_vc_addr[5], w_u_lrly4_vc_addr[4], w_u_lrly4_vc_addr[3], w_u_lrly4_vc_addr[2], w_u_lrly4_vc_addr[1], w_u_lrly4_vc_addr[0], w_u_lrly4_vb_re[0], w_u_lrly4_vb_addr[23], w_u_lrly4_vb_addr[22], w_u_lrly4_vb_addr[21], w_u_lrly4_vb_addr[20], w_u_lrly4_vb_addr[19], w_u_lrly4_vb_addr[18], w_u_lrly4_vb_addr[17], w_u_lrly4_vb_addr[16], w_u_lrly4_vb_addr[15], w_u_lrly4_vb_addr[14], w_u_lrly4_vb_addr[13], w_u_lrly4_vb_addr[12], w_u_lrly4_vb_addr[11], w_u_lrly4_vb_addr[10], w_u_lrly4_vb_addr[9], w_u_lrly4_vb_addr[8], w_u_lrly4_vb_addr[7], w_u_lrly4_vb_addr[6], w_u_lrly4_vb_addr[5], w_u_lrly4_vb_addr[4], w_u_lrly4_vb_addr[3], w_u_lrly4_vb_addr[2], w_u_lrly4_vb_addr[1], w_u_lrly4_vb_addr[0], w_u_lrly4_va_re[0], w_u_lrly4_va_addr[23], w_u_lrly4_va_addr[22], w_u_lrly4_va_addr[21], w_u_lrly4_va_addr[20], w_u_lrly4_va_addr[19], w_u_lrly4_va_addr[18], w_u_lrly4_va_addr[17], w_u_lrly4_va_addr[16], w_u_lrly4_va_addr[15], w_u_lrly4_va_addr[14], w_u_lrly4_va_addr[13], w_u_lrly4_va_addr[12], w_u_lrly4_va_addr[11], w_u_lrly4_va_addr[10], w_u_lrly4_va_addr[9], w_u_lrly4_va_addr[8], w_u_lrly4_va_addr[7], w_u_lrly4_va_addr[6], w_u_lrly4_va_addr[5], w_u_lrly4_va_addr[4], w_u_lrly4_va_addr[3], w_u_lrly4_va_addr[2], w_u_lrly4_va_addr[1], w_u_lrly4_va_addr[0], w_u_lrly4_retire[0], w_u_lrly4_l_ov[0], w_u_lrly4_l_out[31], w_u_lrly4_l_out[30], w_u_lrly4_l_out[29], w_u_lrly4_l_out[28], w_u_lrly4_l_out[27], w_u_lrly4_l_out[26], w_u_lrly4_l_out[25], w_u_lrly4_l_out[24], w_u_lrly4_l_out[23], w_u_lrly4_l_out[22], w_u_lrly4_l_out[21], w_u_lrly4_l_out[20], w_u_lrly4_l_out[19], w_u_lrly4_l_out[18], w_u_lrly4_l_out[17], w_u_lrly4_l_out[16], w_u_lrly4_l_out[15], w_u_lrly4_l_out[14], w_u_lrly4_l_out[13], w_u_lrly4_l_out[12], w_u_lrly4_l_out[11], w_u_lrly4_l_out[10], w_u_lrly4_l_out[9], w_u_lrly4_l_out[8], w_u_lrly4_l_out[7], w_u_lrly4_l_out[6], w_u_lrly4_l_out[5], w_u_lrly4_l_out[4], w_u_lrly4_l_out[3], w_u_lrly4_l_out[2], w_u_lrly4_l_out[1], w_u_lrly4_l_out[0], w_u_lrly4_l_last[0], w_u_lrly4_l_fault[0], w_u_lrly4_kv_we[0], w_u_lrly4_crom_re[0], w_u_lrly4_crom_addr[23], w_u_lrly4_crom_addr[22], w_u_lrly4_crom_addr[21], w_u_lrly4_crom_addr[20], w_u_lrly4_crom_addr[19], w_u_lrly4_crom_addr[18], w_u_lrly4_crom_addr[17], w_u_lrly4_crom_addr[16], w_u_lrly4_crom_addr[15], w_u_lrly4_crom_addr[14], w_u_lrly4_crom_addr[13], w_u_lrly4_crom_addr[12], w_u_lrly4_crom_addr[11], w_u_lrly4_crom_addr[10], w_u_lrly4_crom_addr[9], w_u_lrly4_crom_addr[8], w_u_lrly4_crom_addr[7], w_u_lrly4_crom_addr[6], w_u_lrly4_crom_addr[5], w_u_lrly4_crom_addr[4], w_u_lrly4_crom_addr[3], w_u_lrly4_crom_addr[2], w_u_lrly4_crom_addr[1], w_u_lrly4_crom_addr[0]};
endmodule
