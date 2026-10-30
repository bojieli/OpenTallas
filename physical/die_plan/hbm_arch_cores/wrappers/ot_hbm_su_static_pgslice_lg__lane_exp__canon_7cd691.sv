// CODEX source PREP only: exact physical ID alias, no new state/cycles.
// DIE-HBM/KITS 10-27 (UNCOMMITTED PROPOSAL): canon wrapper ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691 = pure rename of the proven sw2.py member
// wrappers ['ot_hbm_su_static_pgslice_lg__lane_exp1', 'ot_hbm_su_static_pgslice_lg__lane_exp10', 'ot_hbm_su_static_pgslice_lg__lane_exp11', 'ot_hbm_su_static_pgslice_lg__lane_exp12', 'ot_hbm_su_static_pgslice_lg__lane_exp13', 'ot_hbm_su_static_pgslice_lg__lane_exp14', 'ot_hbm_su_static_pgslice_lg__lane_exp2', 'ot_hbm_su_static_pgslice_lg__lane_exp3', 'ot_hbm_su_static_pgslice_lg__lane_exp4', 'ot_hbm_su_static_pgslice_lg__lane_exp5', 'ot_hbm_su_static_pgslice_lg__lane_exp6', 'ot_hbm_su_static_pgslice_lg__lane_exp7', 'ot_hbm_su_static_pgslice_lg__lane_exp8', 'ot_hbm_su_static_pgslice_lg__lane_exp9', 'ot_hbm_su_static_pgslice_lg__lane_exp_l'] (byte-identical after renaming g_*_<n>_ -> g_*_k<i>_ and lane-id straps -> pin).
// Plan pins: cores/ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691__440.64x207.36__canon.json (C19).  Pure wiring; re-run split/miter.py equivalence before sign-off.
`default_nettype none
module ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691 (
    input wire [10:0] strap_lane_lane_id,
    input wire [119:0] g_lane_k0_g_plain_u_lane_vb,
    input wire [127:0] g_lane_k0_g_plain_u_lane_rd_q,
    input wire [1:0] g_lane_k0_g_plain_u_lane_aind,
    input wire [1:0] g_lane_k0_g_plain_u_lane_ce_e2,
    input wire [1:0] g_lane_k0_g_plain_u_lane_cm_m2,
    input wire [1:0] g_lane_k0_g_plain_u_lane_co_dst,
    input wire [1:0] g_lane_k0_g_plain_u_lane_dst,
    input wire [23:0] g_lane_k0_g_plain_u_lane_aibase,
    input wire [23:0] g_lane_k0_g_plain_u_lane_i_v,
    input wire [23:0] g_lane_k0_g_plain_u_lane_krow,
    input wire [23:0] g_lane_k0_g_plain_u_lane_ni,
    input wire [23:0] g_lane_k0_g_plain_u_lane_no,
    input wire [23:0] g_lane_k0_g_plain_u_lane_o_v,
    input wire [23:0] g_lane_k0_g_plain_u_lane_obase,
    input wire [2:0] g_lane_k0_g_plain_u_lane_ca_ad,
    input wire [2:0] g_lane_k0_g_plain_u_lane_ci_sfu,
    input wire [2:0] g_lane_k0_g_plain_u_lane_cm_m1,
    input wire [2:0] g_lane_k0_g_plain_u_lane_cm_qm,
    input wire [2:0] g_lane_k0_g_plain_u_lane_cp_m1,
    input wire [2:0] g_lane_k0_g_plain_u_lane_cs_e1,
    input wire [2:0] g_lane_k0_g_plain_u_lane_cs_sfu,
    input wire [31:0] g_bank_k0_u_bank_write_data,
    input wire [31:0] g_lane_k0_g_plain_u_lane_ca_imm2,
    input wire [31:0] g_lane_k0_g_plain_u_lane_ce_imm1,
    input wire [31:0] g_lane_k0_g_plain_u_lane_cm_imm1,
    input wire [31:0] g_lane_k0_g_plain_u_lane_cp_imm1,
    input wire [31:0] g_lane_k0_g_plain_u_lane_cs_imm2,
    input wire [31:0] g_lane_k0_g_plain_u_lane_cx_imm3,
    input wire [31:0] g_lane_k0_g_plain_u_lane_side_y,
    input wire [3:0] clk_insert,
    input wire [3:0] g_lane_k0_g_plain_u_lane_ls,
    input wire [3:0] g_lane_k0_g_plain_u_lane_lvw,
    input wire [4:0] g_bank_k0_u_bank_read_v,
    input wire [4:0] g_lane_k0_g_plain_u_lane_gsh,
    input wire [5:0] clk_bank_macro,
    input wire [7:0] clk_lane,
    input wire [7:0] g_lane_k0_g_plain_u_lane_cx_srcs,
    input wire [839:0] g_lane_k0_g_plain_u_lane_ld_c,
    input wire [8:0] g_bank_k0_u_bank_read_addr,
    input wire [8:0] g_bank_k0_u_bank_write_addr,
    input wire clk_bank,
    input wire g_bank_k0_u_bank_write_v,
    input wire g_lane_k0_g_plain_u_lane_bank,
    input wire g_lane_k0_g_plain_u_lane_co_rnd,
    input wire g_lane_k0_g_plain_u_lane_cpair,
    input wire g_lane_k0_g_plain_u_lane_cx_amin,
    input wire g_lane_k0_g_plain_u_lane_cx_arelu,
    input wire g_lane_k0_g_plain_u_lane_cx_arnd,
    input wire g_lane_k0_g_plain_u_lane_cx_cclip,
    input wire g_lane_k0_g_plain_u_lane_emit,
    input wire g_lane_k0_g_plain_u_lane_ld,
    input wire g_lane_k0_g_plain_u_lane_ld_bank,
    input wire rst_lane_n,
    input wire rst_n,
    output wire [127:0] g_bank_k0_u_bank_read_data,
    output wire [17:0] g_lane_k0_g_plain_u_lane_kv_waddr,
    output wire [17:0] g_lane_k0_g_plain_u_lane_vm_waddr,
    output wire [31:0] g_lane_k0_g_plain_u_lane_kv_wdata,
    output wire [31:0] g_lane_k0_g_plain_u_lane_ro_x,
    output wire [31:0] g_lane_k0_g_plain_u_lane_vm_wdata,
    output wire [31:0] inj_q,
    output wire [35:0] g_bank_k0_u_bank_read_addr_1,
    output wire [3:0] g_lane_k0_g_plain_u_lane_rd_re,
    output wire [59:0] g_lane_k0_g_plain_u_lane_rd_addr,
    output wire [7:0] g_lane_k0_g_plain_u_lane_rd_src,
    output wire g_lane_k0_g_plain_u_lane_coll,
    output wire g_lane_k0_g_plain_u_lane_fault,
    output wire g_lane_k0_g_plain_u_lane_kv_we,
    output wire g_lane_k0_g_plain_u_lane_ro_v,
    output wire g_lane_k0_g_plain_u_lane_vm_we
);
    wire [95:0] c_lane_rd_addr;
    wire [159:0] c_bank_read_data;
    wire [3:0] c_lane_rd_re;
    wire [7:0] c_lane_rd_src;
    wire c_lane_vm_we;
    wire [17:0] c_lane_vm_waddr;
    wire [31:0] c_lane_vm_wdata;
    wire c_lane_kv_we;
    wire [17:0] c_lane_kv_waddr;
    wire [31:0] c_lane_kv_wdata;
    wire c_lane_ro_v;
    wire [31:0] c_lane_ro_x;
    wire c_lane_fault;
    wire c_lane_coll;
    ot_hbm_su_pg_lane_exp_core #(.MLAT(4), .ALAT(4), .WCOPY(0)) u_core (
        .bank_clk(clk_bank),
        .bank_rst_n(rst_n),
        .bank_clk_macro(clk_bank_macro[5:0]),
        .bank_read_v(g_bank_k0_u_bank_read_v[4:0]),
        .bank_read_addr(g_bank_k0_u_bank_read_addr[8:0]),
        .bank_write_v(g_bank_k0_u_bank_write_v),
        .bank_write_addr(g_bank_k0_u_bank_write_addr[8:0]),
        .bank_write_data(g_bank_k0_u_bank_write_data[31:0]),
        .lane_clk_stage(clk_lane[7:0]),
        .lane_clk_insert(clk_insert[3:0]),
        .lane_rst_n(rst_lane_n),
        .lane_ld(g_lane_k0_g_plain_u_lane_ld),
        .lane_ld_bank(g_lane_k0_g_plain_u_lane_ld_bank),
        .lane_ld_c(g_lane_k0_g_plain_u_lane_ld_c[839:0]),
        .lane_emit(g_lane_k0_g_plain_u_lane_emit),
        .lane_bank(g_lane_k0_g_plain_u_lane_bank),
        .lane_o_v(g_lane_k0_g_plain_u_lane_o_v[23:0]),
        .lane_i_v(g_lane_k0_g_plain_u_lane_i_v[23:0]),
        .lane_no(g_lane_k0_g_plain_u_lane_no[23:0]),
        .lane_ni(g_lane_k0_g_plain_u_lane_ni[23:0]),
        .lane_ls(g_lane_k0_g_plain_u_lane_ls[3:0]),
        .lane_lvw(g_lane_k0_g_plain_u_lane_lvw[3:0]),
        .lane_vb(g_lane_k0_g_plain_u_lane_vb[119:0]),
        .lane_krow(g_lane_k0_g_plain_u_lane_krow[23:0]),
        .lane_obase(g_lane_k0_g_plain_u_lane_obase[23:0]),
        .lane_aibase(g_lane_k0_g_plain_u_lane_aibase[23:0]),
        .lane_aind(g_lane_k0_g_plain_u_lane_aind[1:0]),
        .lane_gsh(g_lane_k0_g_plain_u_lane_gsh[4:0]),
        .lane_cpair(g_lane_k0_g_plain_u_lane_cpair),
        .lane_dst(g_lane_k0_g_plain_u_lane_dst[1:0]),
        .lane_srcs(g_lane_k0_g_plain_u_lane_cx_srcs[7:0]),
        .lane_rd_q(g_lane_k0_g_plain_u_lane_rd_q[127:0]),
        .lane_cx_arnd(g_lane_k0_g_plain_u_lane_cx_arnd),
        .lane_cx_arelu(g_lane_k0_g_plain_u_lane_cx_arelu),
        .lane_cx_amin(g_lane_k0_g_plain_u_lane_cx_amin),
        .lane_cx_cclip(g_lane_k0_g_plain_u_lane_cx_cclip),
        .lane_cx_imm3(g_lane_k0_g_plain_u_lane_cx_imm3[31:0]),
        .lane_cp_m1(g_lane_k0_g_plain_u_lane_cp_m1[2:0]),
        .lane_cp_imm1(g_lane_k0_g_plain_u_lane_cp_imm1[31:0]),
        .lane_cm_m1(g_lane_k0_g_plain_u_lane_cm_m1[2:0]),
        .lane_cm_m2(g_lane_k0_g_plain_u_lane_cm_m2[1:0]),
        .lane_cm_qm(g_lane_k0_g_plain_u_lane_cm_qm[2:0]),
        .lane_cm_imm1(g_lane_k0_g_plain_u_lane_cm_imm1[31:0]),
        .lane_ca_ad(g_lane_k0_g_plain_u_lane_ca_ad[2:0]),
        .lane_ca_imm2(g_lane_k0_g_plain_u_lane_ca_imm2[31:0]),
        .lane_ci_sfu(g_lane_k0_g_plain_u_lane_ci_sfu[2:0]),
        .lane_cs_sfu(g_lane_k0_g_plain_u_lane_cs_sfu[2:0]),
        .lane_cs_e1(g_lane_k0_g_plain_u_lane_cs_e1[2:0]),
        .lane_cs_imm2(g_lane_k0_g_plain_u_lane_cs_imm2[31:0]),
        .lane_ce_e2(g_lane_k0_g_plain_u_lane_ce_e2[1:0]),
        .lane_ce_imm1(g_lane_k0_g_plain_u_lane_ce_imm1[31:0]),
        .lane_co_rnd(g_lane_k0_g_plain_u_lane_co_rnd),
        .lane_co_dst(g_lane_k0_g_plain_u_lane_co_dst[1:0]),
        .lane_side_y(g_lane_k0_g_plain_u_lane_side_y[31:0]),
        .lane_lane_id(strap_lane_lane_id),
        .lane_rd_addr(c_lane_rd_addr),
        .bank_read_data(c_bank_read_data),
        .lane_rd_re(c_lane_rd_re),
        .lane_rd_src(c_lane_rd_src),
        .lane_vm_we(c_lane_vm_we),
        .lane_vm_waddr(c_lane_vm_waddr),
        .lane_vm_wdata(c_lane_vm_wdata),
        .lane_kv_we(c_lane_kv_we),
        .lane_kv_waddr(c_lane_kv_waddr),
        .lane_kv_wdata(c_lane_kv_wdata),
        .lane_ro_v(c_lane_ro_v),
        .lane_ro_x(c_lane_ro_x),
        .lane_fault(c_lane_fault),
        .lane_coll(c_lane_coll));
    assign g_bank_k0_u_bank_read_addr_1 = c_lane_rd_addr[35:0];
    assign g_bank_k0_u_bank_read_data = c_bank_read_data[127:0];
    assign g_lane_k0_g_plain_u_lane_coll = c_lane_coll;
    assign g_lane_k0_g_plain_u_lane_fault = c_lane_fault;
    assign g_lane_k0_g_plain_u_lane_kv_waddr = c_lane_kv_waddr[17:0];
    assign g_lane_k0_g_plain_u_lane_kv_wdata = c_lane_kv_wdata[31:0];
    assign g_lane_k0_g_plain_u_lane_kv_we = c_lane_kv_we;
    assign g_lane_k0_g_plain_u_lane_rd_addr = c_lane_rd_addr[95:36];
    assign g_lane_k0_g_plain_u_lane_rd_re = c_lane_rd_re[3:0];
    assign g_lane_k0_g_plain_u_lane_rd_src = c_lane_rd_src[7:0];
    assign g_lane_k0_g_plain_u_lane_ro_v = c_lane_ro_v;
    assign g_lane_k0_g_plain_u_lane_ro_x = c_lane_ro_x[31:0];
    assign g_lane_k0_g_plain_u_lane_vm_waddr = c_lane_vm_waddr[17:0];
    assign g_lane_k0_g_plain_u_lane_vm_wdata = c_lane_vm_wdata[31:0];
    assign g_lane_k0_g_plain_u_lane_vm_we = c_lane_vm_we;
    assign inj_q = c_bank_read_data[159:128];
endmodule
`default_nettype wire
