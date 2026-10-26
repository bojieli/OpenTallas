`timescale 1ns/1ps
module tb;
  reg clk = 0; reg rst_n = 0; integer cyc = 0; integer ndiff = 0; integer nmut = 0; integer nact = 0;
  always #1 clk = ~clk;
  reg [127:0] p_g_bank_31_u_bank_read_data = 0;
  reg [59:0] p_g_lane_31_g_plain_u_lane_rd_addr = 0;
  reg [59:0] p_g_lane_30_g_plain_u_lane_rd_addr = 0;
  reg [59:0] p_g_lane_29_g_plain_u_lane_rd_addr = 0;
  reg [59:0] p_g_lane_28_g_plain_u_lane_rd_addr = 0;
  reg [31:0] p_g_lane_31_g_plain_u_lane_vm_wdata = 0;
  reg [31:0] p_g_lane_31_g_plain_u_lane_ro_x = 0;
  reg [31:0] p_g_lane_31_g_plain_u_lane_kv_wdata = 0;
  reg [31:0] p_g_lane_30_g_plain_u_lane_vm_wdata = 0;
  reg [31:0] p_g_lane_30_g_plain_u_lane_ro_x = 0;
  reg [31:0] p_g_lane_30_g_plain_u_lane_kv_wdata = 0;
  reg [31:0] p_g_lane_29_g_plain_u_lane_vm_wdata = 0;
  reg [31:0] p_g_lane_29_g_plain_u_lane_ro_x = 0;
  reg [31:0] p_g_lane_29_g_plain_u_lane_kv_wdata = 0;
  reg [31:0] p_g_lane_28_g_plain_u_lane_vm_wdata = 0;
  reg [31:0] p_g_lane_28_g_plain_u_lane_ro_x = 0;
  reg [31:0] p_g_lane_28_g_plain_u_lane_kv_wdata = 0;
  reg [17:0] p_g_lane_31_g_plain_u_lane_vm_waddr = 0;
  reg [17:0] p_g_lane_31_g_plain_u_lane_kv_waddr = 0;
  reg [17:0] p_g_lane_30_g_plain_u_lane_vm_waddr = 0;
  reg [17:0] p_g_lane_30_g_plain_u_lane_kv_waddr = 0;
  reg [17:0] p_g_lane_29_g_plain_u_lane_vm_waddr = 0;
  reg [17:0] p_g_lane_29_g_plain_u_lane_kv_waddr = 0;
  reg [17:0] p_g_lane_28_g_plain_u_lane_vm_waddr = 0;
  reg [17:0] p_g_lane_28_g_plain_u_lane_kv_waddr = 0;
  reg [7:0] p_g_lane_31_g_plain_u_lane_rd_src = 0;
  reg [7:0] p_g_lane_30_g_plain_u_lane_rd_src = 0;
  reg [7:0] p_g_lane_29_g_plain_u_lane_rd_src = 0;
  reg [7:0] p_g_lane_28_g_plain_u_lane_rd_src = 0;
  reg [3:0] p_g_lane_31_g_plain_u_lane_rd_re = 0;
  reg [3:0] p_g_lane_30_g_plain_u_lane_rd_re = 0;
  reg [3:0] p_g_lane_29_g_plain_u_lane_rd_re = 0;
  reg [3:0] p_g_lane_28_g_plain_u_lane_rd_re = 0;
  reg [0:0] p_g_lane_31_g_plain_u_lane_vm_we = 0;
  reg [0:0] p_g_lane_31_g_plain_u_lane_ro_v = 0;
  reg [0:0] p_g_lane_31_g_plain_u_lane_kv_we = 0;
  reg [0:0] p_g_lane_31_g_plain_u_lane_fault = 0;
  reg [0:0] p_g_lane_31_g_plain_u_lane_coll = 0;
  reg [0:0] p_g_lane_30_g_plain_u_lane_vm_we = 0;
  reg [0:0] p_g_lane_30_g_plain_u_lane_ro_v = 0;
  reg [0:0] p_g_lane_30_g_plain_u_lane_kv_we = 0;
  reg [0:0] p_g_lane_30_g_plain_u_lane_fault = 0;
  reg [0:0] p_g_lane_30_g_plain_u_lane_coll = 0;
  reg [0:0] p_g_lane_29_g_plain_u_lane_vm_we = 0;
  reg [0:0] p_g_lane_29_g_plain_u_lane_ro_v = 0;
  reg [0:0] p_g_lane_29_g_plain_u_lane_kv_we = 0;
  reg [0:0] p_g_lane_29_g_plain_u_lane_fault = 0;
  reg [0:0] p_g_lane_29_g_plain_u_lane_coll = 0;
  reg [0:0] p_g_lane_28_g_plain_u_lane_vm_we = 0;
  reg [0:0] p_g_lane_28_g_plain_u_lane_ro_v = 0;
  reg [0:0] p_g_lane_28_g_plain_u_lane_kv_we = 0;
  reg [0:0] p_g_lane_28_g_plain_u_lane_fault = 0;
  reg [0:0] p_g_lane_28_g_plain_u_lane_coll = 0;
  reg [127:0] p_inj_q = 0;
  reg [127:0] p_g_bank_30_u_bank_read_data = 0;
  reg [127:0] p_g_bank_29_u_bank_read_data = 0;
  reg [127:0] p_g_bank_28_u_bank_read_data = 0;
  reg [35:0] p_g_bank_31_u_bank_read_addr = 0;
  reg [35:0] p_g_bank_30_u_bank_read_addr = 0;
  reg [35:0] p_g_bank_29_u_bank_read_addr = 0;
  reg [35:0] p_g_bank_28_u_bank_read_addr_1 = 0;
  wire [35:0] r_g_bank_28_u_bank_read_addr_1;
  wire [35:0] d_g_bank_28_u_bank_read_addr_1;
  wire [35:0] m_g_bank_28_u_bank_read_addr_1;
  wire [35:0] r_g_bank_29_u_bank_read_addr;
  wire [35:0] d_g_bank_29_u_bank_read_addr;
  wire [35:0] m_g_bank_29_u_bank_read_addr;
  wire [35:0] r_g_bank_30_u_bank_read_addr;
  wire [35:0] d_g_bank_30_u_bank_read_addr;
  wire [35:0] m_g_bank_30_u_bank_read_addr;
  wire [35:0] r_g_bank_31_u_bank_read_addr;
  wire [35:0] d_g_bank_31_u_bank_read_addr;
  wire [35:0] m_g_bank_31_u_bank_read_addr;
  reg [127:0] i_g_lane_30_g_plain_u_lane_rd_q = 0;
  reg [127:0] i_g_lane_31_g_plain_u_lane_rd_q = 0;
  wire [127:0] r_g_bank_28_u_bank_read_data;
  wire [127:0] d_g_bank_28_u_bank_read_data;
  wire [127:0] m_g_bank_28_u_bank_read_data;
  wire [127:0] r_g_bank_29_u_bank_read_data;
  wire [127:0] d_g_bank_29_u_bank_read_data;
  wire [127:0] m_g_bank_29_u_bank_read_data;
  wire [127:0] r_g_bank_30_u_bank_read_data;
  wire [127:0] d_g_bank_30_u_bank_read_data;
  wire [127:0] m_g_bank_30_u_bank_read_data;
  reg [0:0] i_g_bank_28_u_bank_write_v = 0;
  reg [0:0] i_g_bank_29_u_bank_write_v = 0;
  reg [0:0] i_g_bank_30_u_bank_write_v = 0;
  reg [0:0] i_g_bank_31_u_bank_write_v = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_bank = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_co_rnd = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_cpair = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_cx_amin = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_cx_arelu = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_cx_arnd = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_cx_cclip = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_emit = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_ld = 0;
  reg [0:0] i_g_lane_28_g_plain_u_lane_ld_bank = 0;
  reg [1:0] i_g_lane_28_g_plain_u_lane_aind = 0;
  reg [1:0] i_g_lane_28_g_plain_u_lane_ce_e2 = 0;
  reg [1:0] i_g_lane_28_g_plain_u_lane_cm_m2 = 0;
  reg [1:0] i_g_lane_28_g_plain_u_lane_co_dst = 0;
  reg [1:0] i_g_lane_28_g_plain_u_lane_dst = 0;
  reg [2:0] i_g_lane_28_g_plain_u_lane_ca_ad = 0;
  reg [2:0] i_g_lane_28_g_plain_u_lane_ci_sfu = 0;
  reg [2:0] i_g_lane_28_g_plain_u_lane_cm_m1 = 0;
  reg [2:0] i_g_lane_28_g_plain_u_lane_cm_qm = 0;
  reg [2:0] i_g_lane_28_g_plain_u_lane_cp_m1 = 0;
  reg [2:0] i_g_lane_28_g_plain_u_lane_cs_e1 = 0;
  reg [2:0] i_g_lane_28_g_plain_u_lane_cs_sfu = 0;
  reg [3:0] i_g_bank_29_u_bank_read_v = 0;
  reg [3:0] i_g_bank_30_u_bank_read_v = 0;
  reg [3:0] i_g_bank_31_u_bank_read_v = 0;
  reg [4:0] i_g_bank_28_u_bank_read_v = 0;
  reg [4:0] i_g_lane_28_g_plain_u_lane_gsh = 0;
  reg [7:0] i_g_lane_28_g_plain_u_lane_cx_srcs = 0;
  reg [8:0] i_g_bank_28_u_bank_read_addr = 0;
  reg [8:0] i_g_bank_28_u_bank_write_addr = 0;
  reg [8:0] i_g_bank_29_u_bank_write_addr = 0;
  reg [8:0] i_g_bank_30_u_bank_write_addr = 0;
  reg [8:0] i_g_bank_31_u_bank_write_addr = 0;
  reg [23:0] i_g_lane_28_g_plain_u_lane_aibase = 0;
  reg [23:0] i_g_lane_28_g_plain_u_lane_i_v = 0;
  reg [23:0] i_g_lane_28_g_plain_u_lane_krow = 0;
  reg [31:0] i_g_bank_28_u_bank_write_data = 0;
  reg [31:0] i_g_bank_29_u_bank_write_data = 0;
  reg [31:0] i_g_bank_30_u_bank_write_data = 0;
  reg [31:0] i_g_bank_31_u_bank_write_data = 0;
  reg [31:0] i_g_lane_28_g_plain_u_lane_ca_imm2 = 0;
  reg [31:0] i_g_lane_28_g_plain_u_lane_ce_imm1 = 0;
  reg [31:0] i_g_lane_28_g_plain_u_lane_cm_imm1 = 0;
  reg [31:0] i_g_lane_28_g_plain_u_lane_cp_imm1 = 0;
  reg [31:0] i_g_lane_28_g_plain_u_lane_cs_imm2 = 0;
  reg [31:0] i_g_lane_28_g_plain_u_lane_cx_imm3 = 0;
  wire [127:0] r_inj_q;
  wire [127:0] d_inj_q;
  wire [127:0] m_inj_q;
  reg [3:0] i_g_lane_28_g_plain_u_lane_ls = 0;
  reg [3:0] i_g_lane_28_g_plain_u_lane_lvw = 0;
  reg [23:0] i_g_lane_28_g_plain_u_lane_ni = 0;
  reg [23:0] i_g_lane_28_g_plain_u_lane_no = 0;
  reg [23:0] i_g_lane_28_g_plain_u_lane_o_v = 0;
  reg [23:0] i_g_lane_28_g_plain_u_lane_obase = 0;
  reg [31:0] i_g_lane_28_g_plain_u_lane_side_y = 0;
  reg [119:0] i_g_lane_28_g_plain_u_lane_vb = 0;
  reg [127:0] i_g_lane_28_g_plain_u_lane_rd_q = 0;
  reg [127:0] i_g_lane_29_g_plain_u_lane_rd_q = 0;
  reg [839:0] i_g_lane_28_g_plain_u_lane_ld_c = 0;
  wire [0:0] r_g_lane_28_g_plain_u_lane_coll;
  wire [0:0] d_g_lane_28_g_plain_u_lane_coll;
  wire [0:0] m_g_lane_28_g_plain_u_lane_coll;
  wire [0:0] r_g_lane_28_g_plain_u_lane_fault;
  wire [0:0] d_g_lane_28_g_plain_u_lane_fault;
  wire [0:0] m_g_lane_28_g_plain_u_lane_fault;
  wire [0:0] r_g_lane_28_g_plain_u_lane_kv_we;
  wire [0:0] d_g_lane_28_g_plain_u_lane_kv_we;
  wire [0:0] m_g_lane_28_g_plain_u_lane_kv_we;
  wire [0:0] r_g_lane_28_g_plain_u_lane_ro_v;
  wire [0:0] d_g_lane_28_g_plain_u_lane_ro_v;
  wire [0:0] m_g_lane_28_g_plain_u_lane_ro_v;
  wire [0:0] r_g_lane_28_g_plain_u_lane_vm_we;
  wire [0:0] d_g_lane_28_g_plain_u_lane_vm_we;
  wire [0:0] m_g_lane_28_g_plain_u_lane_vm_we;
  wire [0:0] r_g_lane_29_g_plain_u_lane_coll;
  wire [0:0] d_g_lane_29_g_plain_u_lane_coll;
  wire [0:0] m_g_lane_29_g_plain_u_lane_coll;
  wire [0:0] r_g_lane_29_g_plain_u_lane_fault;
  wire [0:0] d_g_lane_29_g_plain_u_lane_fault;
  wire [0:0] m_g_lane_29_g_plain_u_lane_fault;
  wire [0:0] r_g_lane_29_g_plain_u_lane_kv_we;
  wire [0:0] d_g_lane_29_g_plain_u_lane_kv_we;
  wire [0:0] m_g_lane_29_g_plain_u_lane_kv_we;
  wire [0:0] r_g_lane_29_g_plain_u_lane_ro_v;
  wire [0:0] d_g_lane_29_g_plain_u_lane_ro_v;
  wire [0:0] m_g_lane_29_g_plain_u_lane_ro_v;
  wire [0:0] r_g_lane_29_g_plain_u_lane_vm_we;
  wire [0:0] d_g_lane_29_g_plain_u_lane_vm_we;
  wire [0:0] m_g_lane_29_g_plain_u_lane_vm_we;
  wire [0:0] r_g_lane_30_g_plain_u_lane_coll;
  wire [0:0] d_g_lane_30_g_plain_u_lane_coll;
  wire [0:0] m_g_lane_30_g_plain_u_lane_coll;
  wire [0:0] r_g_lane_30_g_plain_u_lane_fault;
  wire [0:0] d_g_lane_30_g_plain_u_lane_fault;
  wire [0:0] m_g_lane_30_g_plain_u_lane_fault;
  wire [0:0] r_g_lane_30_g_plain_u_lane_kv_we;
  wire [0:0] d_g_lane_30_g_plain_u_lane_kv_we;
  wire [0:0] m_g_lane_30_g_plain_u_lane_kv_we;
  wire [0:0] r_g_lane_30_g_plain_u_lane_ro_v;
  wire [0:0] d_g_lane_30_g_plain_u_lane_ro_v;
  wire [0:0] m_g_lane_30_g_plain_u_lane_ro_v;
  wire [0:0] r_g_lane_30_g_plain_u_lane_vm_we;
  wire [0:0] d_g_lane_30_g_plain_u_lane_vm_we;
  wire [0:0] m_g_lane_30_g_plain_u_lane_vm_we;
  wire [0:0] r_g_lane_31_g_plain_u_lane_coll;
  wire [0:0] d_g_lane_31_g_plain_u_lane_coll;
  wire [0:0] m_g_lane_31_g_plain_u_lane_coll;
  wire [0:0] r_g_lane_31_g_plain_u_lane_fault;
  wire [0:0] d_g_lane_31_g_plain_u_lane_fault;
  wire [0:0] m_g_lane_31_g_plain_u_lane_fault;
  wire [0:0] r_g_lane_31_g_plain_u_lane_kv_we;
  wire [0:0] d_g_lane_31_g_plain_u_lane_kv_we;
  wire [0:0] m_g_lane_31_g_plain_u_lane_kv_we;
  wire [0:0] r_g_lane_31_g_plain_u_lane_ro_v;
  wire [0:0] d_g_lane_31_g_plain_u_lane_ro_v;
  wire [0:0] m_g_lane_31_g_plain_u_lane_ro_v;
  wire [0:0] r_g_lane_31_g_plain_u_lane_vm_we;
  wire [0:0] d_g_lane_31_g_plain_u_lane_vm_we;
  wire [0:0] m_g_lane_31_g_plain_u_lane_vm_we;
  wire [3:0] r_g_lane_28_g_plain_u_lane_rd_re;
  wire [3:0] d_g_lane_28_g_plain_u_lane_rd_re;
  wire [3:0] m_g_lane_28_g_plain_u_lane_rd_re;
  wire [3:0] r_g_lane_29_g_plain_u_lane_rd_re;
  wire [3:0] d_g_lane_29_g_plain_u_lane_rd_re;
  wire [3:0] m_g_lane_29_g_plain_u_lane_rd_re;
  wire [3:0] r_g_lane_30_g_plain_u_lane_rd_re;
  wire [3:0] d_g_lane_30_g_plain_u_lane_rd_re;
  wire [3:0] m_g_lane_30_g_plain_u_lane_rd_re;
  wire [3:0] r_g_lane_31_g_plain_u_lane_rd_re;
  wire [3:0] d_g_lane_31_g_plain_u_lane_rd_re;
  wire [3:0] m_g_lane_31_g_plain_u_lane_rd_re;
  wire [7:0] r_g_lane_28_g_plain_u_lane_rd_src;
  wire [7:0] d_g_lane_28_g_plain_u_lane_rd_src;
  wire [7:0] m_g_lane_28_g_plain_u_lane_rd_src;
  wire [7:0] r_g_lane_29_g_plain_u_lane_rd_src;
  wire [7:0] d_g_lane_29_g_plain_u_lane_rd_src;
  wire [7:0] m_g_lane_29_g_plain_u_lane_rd_src;
  wire [7:0] r_g_lane_30_g_plain_u_lane_rd_src;
  wire [7:0] d_g_lane_30_g_plain_u_lane_rd_src;
  wire [7:0] m_g_lane_30_g_plain_u_lane_rd_src;
  wire [7:0] r_g_lane_31_g_plain_u_lane_rd_src;
  wire [7:0] d_g_lane_31_g_plain_u_lane_rd_src;
  wire [7:0] m_g_lane_31_g_plain_u_lane_rd_src;
  wire [17:0] r_g_lane_28_g_plain_u_lane_kv_waddr;
  wire [17:0] d_g_lane_28_g_plain_u_lane_kv_waddr;
  wire [17:0] m_g_lane_28_g_plain_u_lane_kv_waddr;
  wire [17:0] r_g_lane_28_g_plain_u_lane_vm_waddr;
  wire [17:0] d_g_lane_28_g_plain_u_lane_vm_waddr;
  wire [17:0] m_g_lane_28_g_plain_u_lane_vm_waddr;
  wire [17:0] r_g_lane_29_g_plain_u_lane_kv_waddr;
  wire [17:0] d_g_lane_29_g_plain_u_lane_kv_waddr;
  wire [17:0] m_g_lane_29_g_plain_u_lane_kv_waddr;
  wire [17:0] r_g_lane_29_g_plain_u_lane_vm_waddr;
  wire [17:0] d_g_lane_29_g_plain_u_lane_vm_waddr;
  wire [17:0] m_g_lane_29_g_plain_u_lane_vm_waddr;
  wire [17:0] r_g_lane_30_g_plain_u_lane_kv_waddr;
  wire [17:0] d_g_lane_30_g_plain_u_lane_kv_waddr;
  wire [17:0] m_g_lane_30_g_plain_u_lane_kv_waddr;
  wire [17:0] r_g_lane_30_g_plain_u_lane_vm_waddr;
  wire [17:0] d_g_lane_30_g_plain_u_lane_vm_waddr;
  wire [17:0] m_g_lane_30_g_plain_u_lane_vm_waddr;
  wire [17:0] r_g_lane_31_g_plain_u_lane_kv_waddr;
  wire [17:0] d_g_lane_31_g_plain_u_lane_kv_waddr;
  wire [17:0] m_g_lane_31_g_plain_u_lane_kv_waddr;
  wire [17:0] r_g_lane_31_g_plain_u_lane_vm_waddr;
  wire [17:0] d_g_lane_31_g_plain_u_lane_vm_waddr;
  wire [17:0] m_g_lane_31_g_plain_u_lane_vm_waddr;
  wire [31:0] r_g_lane_28_g_plain_u_lane_kv_wdata;
  wire [31:0] d_g_lane_28_g_plain_u_lane_kv_wdata;
  wire [31:0] m_g_lane_28_g_plain_u_lane_kv_wdata;
  wire [31:0] r_g_lane_28_g_plain_u_lane_ro_x;
  wire [31:0] d_g_lane_28_g_plain_u_lane_ro_x;
  wire [31:0] m_g_lane_28_g_plain_u_lane_ro_x;
  wire [31:0] r_g_lane_28_g_plain_u_lane_vm_wdata;
  wire [31:0] d_g_lane_28_g_plain_u_lane_vm_wdata;
  wire [31:0] m_g_lane_28_g_plain_u_lane_vm_wdata;
  wire [31:0] r_g_lane_29_g_plain_u_lane_kv_wdata;
  wire [31:0] d_g_lane_29_g_plain_u_lane_kv_wdata;
  wire [31:0] m_g_lane_29_g_plain_u_lane_kv_wdata;
  wire [31:0] r_g_lane_29_g_plain_u_lane_ro_x;
  wire [31:0] d_g_lane_29_g_plain_u_lane_ro_x;
  wire [31:0] m_g_lane_29_g_plain_u_lane_ro_x;
  wire [31:0] r_g_lane_29_g_plain_u_lane_vm_wdata;
  wire [31:0] d_g_lane_29_g_plain_u_lane_vm_wdata;
  wire [31:0] m_g_lane_29_g_plain_u_lane_vm_wdata;
  wire [31:0] r_g_lane_30_g_plain_u_lane_kv_wdata;
  wire [31:0] d_g_lane_30_g_plain_u_lane_kv_wdata;
  wire [31:0] m_g_lane_30_g_plain_u_lane_kv_wdata;
  wire [31:0] r_g_lane_30_g_plain_u_lane_ro_x;
  wire [31:0] d_g_lane_30_g_plain_u_lane_ro_x;
  wire [31:0] m_g_lane_30_g_plain_u_lane_ro_x;
  wire [31:0] r_g_lane_30_g_plain_u_lane_vm_wdata;
  wire [31:0] d_g_lane_30_g_plain_u_lane_vm_wdata;
  wire [31:0] m_g_lane_30_g_plain_u_lane_vm_wdata;
  wire [31:0] r_g_lane_31_g_plain_u_lane_kv_wdata;
  wire [31:0] d_g_lane_31_g_plain_u_lane_kv_wdata;
  wire [31:0] m_g_lane_31_g_plain_u_lane_kv_wdata;
  wire [31:0] r_g_lane_31_g_plain_u_lane_ro_x;
  wire [31:0] d_g_lane_31_g_plain_u_lane_ro_x;
  wire [31:0] m_g_lane_31_g_plain_u_lane_ro_x;
  wire [31:0] r_g_lane_31_g_plain_u_lane_vm_wdata;
  wire [31:0] d_g_lane_31_g_plain_u_lane_vm_wdata;
  wire [31:0] m_g_lane_31_g_plain_u_lane_vm_wdata;
  wire [59:0] r_g_lane_28_g_plain_u_lane_rd_addr;
  wire [59:0] d_g_lane_28_g_plain_u_lane_rd_addr;
  wire [59:0] m_g_lane_28_g_plain_u_lane_rd_addr;
  wire [59:0] r_g_lane_29_g_plain_u_lane_rd_addr;
  wire [59:0] d_g_lane_29_g_plain_u_lane_rd_addr;
  wire [59:0] m_g_lane_29_g_plain_u_lane_rd_addr;
  wire [59:0] r_g_lane_30_g_plain_u_lane_rd_addr;
  wire [59:0] d_g_lane_30_g_plain_u_lane_rd_addr;
  wire [59:0] m_g_lane_30_g_plain_u_lane_rd_addr;
  wire [59:0] r_g_lane_31_g_plain_u_lane_rd_addr;
  wire [59:0] d_g_lane_31_g_plain_u_lane_rd_addr;
  wire [59:0] m_g_lane_31_g_plain_u_lane_rd_addr;
  wire [127:0] r_g_bank_31_u_bank_read_data;
  wire [127:0] d_g_bank_31_u_bank_read_data;
  wire [127:0] m_g_bank_31_u_bank_read_data;
  ot_hbm_su_static_pgslice_lg__lanes_plain12_15__fcore u_ref (.clk_bank({4{clk}}), .rst_lane_n({4{rst_n}}), .clk_insert({16{clk}}), .clk_bank_macro({24{clk}}), .clk_lane({32{clk}}), .g_bank_28_u_bank_read_addr_1(r_g_bank_28_u_bank_read_addr_1), .g_bank_29_u_bank_read_addr(r_g_bank_29_u_bank_read_addr), .g_bank_30_u_bank_read_addr(r_g_bank_30_u_bank_read_addr), .g_bank_31_u_bank_read_addr(r_g_bank_31_u_bank_read_addr), .g_lane_30_g_plain_u_lane_rd_q(i_g_lane_30_g_plain_u_lane_rd_q), .g_lane_31_g_plain_u_lane_rd_q(i_g_lane_31_g_plain_u_lane_rd_q), .g_bank_28_u_bank_read_data(r_g_bank_28_u_bank_read_data), .g_bank_29_u_bank_read_data(r_g_bank_29_u_bank_read_data), .g_bank_30_u_bank_read_data(r_g_bank_30_u_bank_read_data), .rst_n(rst_n), .g_bank_28_u_bank_write_v(i_g_bank_28_u_bank_write_v), .g_bank_29_u_bank_write_v(i_g_bank_29_u_bank_write_v), .g_bank_30_u_bank_write_v(i_g_bank_30_u_bank_write_v), .g_bank_31_u_bank_write_v(i_g_bank_31_u_bank_write_v), .g_lane_28_g_plain_u_lane_bank(i_g_lane_28_g_plain_u_lane_bank), .g_lane_28_g_plain_u_lane_co_rnd(i_g_lane_28_g_plain_u_lane_co_rnd), .g_lane_28_g_plain_u_lane_cpair(i_g_lane_28_g_plain_u_lane_cpair), .g_lane_28_g_plain_u_lane_cx_amin(i_g_lane_28_g_plain_u_lane_cx_amin), .g_lane_28_g_plain_u_lane_cx_arelu(i_g_lane_28_g_plain_u_lane_cx_arelu), .g_lane_28_g_plain_u_lane_cx_arnd(i_g_lane_28_g_plain_u_lane_cx_arnd), .g_lane_28_g_plain_u_lane_cx_cclip(i_g_lane_28_g_plain_u_lane_cx_cclip), .g_lane_28_g_plain_u_lane_emit(i_g_lane_28_g_plain_u_lane_emit), .g_lane_28_g_plain_u_lane_ld(i_g_lane_28_g_plain_u_lane_ld), .g_lane_28_g_plain_u_lane_ld_bank(i_g_lane_28_g_plain_u_lane_ld_bank), .g_lane_28_g_plain_u_lane_aind(i_g_lane_28_g_plain_u_lane_aind), .g_lane_28_g_plain_u_lane_ce_e2(i_g_lane_28_g_plain_u_lane_ce_e2), .g_lane_28_g_plain_u_lane_cm_m2(i_g_lane_28_g_plain_u_lane_cm_m2), .g_lane_28_g_plain_u_lane_co_dst(i_g_lane_28_g_plain_u_lane_co_dst), .g_lane_28_g_plain_u_lane_dst(i_g_lane_28_g_plain_u_lane_dst), .g_lane_28_g_plain_u_lane_ca_ad(i_g_lane_28_g_plain_u_lane_ca_ad), .g_lane_28_g_plain_u_lane_ci_sfu(i_g_lane_28_g_plain_u_lane_ci_sfu), .g_lane_28_g_plain_u_lane_cm_m1(i_g_lane_28_g_plain_u_lane_cm_m1), .g_lane_28_g_plain_u_lane_cm_qm(i_g_lane_28_g_plain_u_lane_cm_qm), .g_lane_28_g_plain_u_lane_cp_m1(i_g_lane_28_g_plain_u_lane_cp_m1), .g_lane_28_g_plain_u_lane_cs_e1(i_g_lane_28_g_plain_u_lane_cs_e1), .g_lane_28_g_plain_u_lane_cs_sfu(i_g_lane_28_g_plain_u_lane_cs_sfu), .g_bank_29_u_bank_read_v(i_g_bank_29_u_bank_read_v), .g_bank_30_u_bank_read_v(i_g_bank_30_u_bank_read_v), .g_bank_31_u_bank_read_v(i_g_bank_31_u_bank_read_v), .g_bank_28_u_bank_read_v(i_g_bank_28_u_bank_read_v), .g_lane_28_g_plain_u_lane_gsh(i_g_lane_28_g_plain_u_lane_gsh), .g_lane_28_g_plain_u_lane_cx_srcs(i_g_lane_28_g_plain_u_lane_cx_srcs), .g_bank_28_u_bank_read_addr(i_g_bank_28_u_bank_read_addr), .g_bank_28_u_bank_write_addr(i_g_bank_28_u_bank_write_addr), .g_bank_29_u_bank_write_addr(i_g_bank_29_u_bank_write_addr), .g_bank_30_u_bank_write_addr(i_g_bank_30_u_bank_write_addr), .g_bank_31_u_bank_write_addr(i_g_bank_31_u_bank_write_addr), .g_lane_28_g_plain_u_lane_aibase(i_g_lane_28_g_plain_u_lane_aibase), .g_lane_28_g_plain_u_lane_i_v(i_g_lane_28_g_plain_u_lane_i_v), .g_lane_28_g_plain_u_lane_krow(i_g_lane_28_g_plain_u_lane_krow), .g_bank_28_u_bank_write_data(i_g_bank_28_u_bank_write_data), .g_bank_29_u_bank_write_data(i_g_bank_29_u_bank_write_data), .g_bank_30_u_bank_write_data(i_g_bank_30_u_bank_write_data), .g_bank_31_u_bank_write_data(i_g_bank_31_u_bank_write_data), .g_lane_28_g_plain_u_lane_ca_imm2(i_g_lane_28_g_plain_u_lane_ca_imm2), .g_lane_28_g_plain_u_lane_ce_imm1(i_g_lane_28_g_plain_u_lane_ce_imm1), .g_lane_28_g_plain_u_lane_cm_imm1(i_g_lane_28_g_plain_u_lane_cm_imm1), .g_lane_28_g_plain_u_lane_cp_imm1(i_g_lane_28_g_plain_u_lane_cp_imm1), .g_lane_28_g_plain_u_lane_cs_imm2(i_g_lane_28_g_plain_u_lane_cs_imm2), .g_lane_28_g_plain_u_lane_cx_imm3(i_g_lane_28_g_plain_u_lane_cx_imm3), .inj_q(r_inj_q), .g_lane_28_g_plain_u_lane_ls(i_g_lane_28_g_plain_u_lane_ls), .g_lane_28_g_plain_u_lane_lvw(i_g_lane_28_g_plain_u_lane_lvw), .g_lane_28_g_plain_u_lane_ni(i_g_lane_28_g_plain_u_lane_ni), .g_lane_28_g_plain_u_lane_no(i_g_lane_28_g_plain_u_lane_no), .g_lane_28_g_plain_u_lane_o_v(i_g_lane_28_g_plain_u_lane_o_v), .g_lane_28_g_plain_u_lane_obase(i_g_lane_28_g_plain_u_lane_obase), .g_lane_28_g_plain_u_lane_side_y(i_g_lane_28_g_plain_u_lane_side_y), .g_lane_28_g_plain_u_lane_vb(i_g_lane_28_g_plain_u_lane_vb), .g_lane_28_g_plain_u_lane_rd_q(i_g_lane_28_g_plain_u_lane_rd_q), .g_lane_29_g_plain_u_lane_rd_q(i_g_lane_29_g_plain_u_lane_rd_q), .g_lane_28_g_plain_u_lane_ld_c(i_g_lane_28_g_plain_u_lane_ld_c), .g_lane_28_g_plain_u_lane_coll(r_g_lane_28_g_plain_u_lane_coll), .g_lane_28_g_plain_u_lane_fault(r_g_lane_28_g_plain_u_lane_fault), .g_lane_28_g_plain_u_lane_kv_we(r_g_lane_28_g_plain_u_lane_kv_we), .g_lane_28_g_plain_u_lane_ro_v(r_g_lane_28_g_plain_u_lane_ro_v), .g_lane_28_g_plain_u_lane_vm_we(r_g_lane_28_g_plain_u_lane_vm_we), .g_lane_29_g_plain_u_lane_coll(r_g_lane_29_g_plain_u_lane_coll), .g_lane_29_g_plain_u_lane_fault(r_g_lane_29_g_plain_u_lane_fault), .g_lane_29_g_plain_u_lane_kv_we(r_g_lane_29_g_plain_u_lane_kv_we), .g_lane_29_g_plain_u_lane_ro_v(r_g_lane_29_g_plain_u_lane_ro_v), .g_lane_29_g_plain_u_lane_vm_we(r_g_lane_29_g_plain_u_lane_vm_we), .g_lane_30_g_plain_u_lane_coll(r_g_lane_30_g_plain_u_lane_coll), .g_lane_30_g_plain_u_lane_fault(r_g_lane_30_g_plain_u_lane_fault), .g_lane_30_g_plain_u_lane_kv_we(r_g_lane_30_g_plain_u_lane_kv_we), .g_lane_30_g_plain_u_lane_ro_v(r_g_lane_30_g_plain_u_lane_ro_v), .g_lane_30_g_plain_u_lane_vm_we(r_g_lane_30_g_plain_u_lane_vm_we), .g_lane_31_g_plain_u_lane_coll(r_g_lane_31_g_plain_u_lane_coll), .g_lane_31_g_plain_u_lane_fault(r_g_lane_31_g_plain_u_lane_fault), .g_lane_31_g_plain_u_lane_kv_we(r_g_lane_31_g_plain_u_lane_kv_we), .g_lane_31_g_plain_u_lane_ro_v(r_g_lane_31_g_plain_u_lane_ro_v), .g_lane_31_g_plain_u_lane_vm_we(r_g_lane_31_g_plain_u_lane_vm_we), .g_lane_28_g_plain_u_lane_rd_re(r_g_lane_28_g_plain_u_lane_rd_re), .g_lane_29_g_plain_u_lane_rd_re(r_g_lane_29_g_plain_u_lane_rd_re), .g_lane_30_g_plain_u_lane_rd_re(r_g_lane_30_g_plain_u_lane_rd_re), .g_lane_31_g_plain_u_lane_rd_re(r_g_lane_31_g_plain_u_lane_rd_re), .g_lane_28_g_plain_u_lane_rd_src(r_g_lane_28_g_plain_u_lane_rd_src), .g_lane_29_g_plain_u_lane_rd_src(r_g_lane_29_g_plain_u_lane_rd_src), .g_lane_30_g_plain_u_lane_rd_src(r_g_lane_30_g_plain_u_lane_rd_src), .g_lane_31_g_plain_u_lane_rd_src(r_g_lane_31_g_plain_u_lane_rd_src), .g_lane_28_g_plain_u_lane_kv_waddr(r_g_lane_28_g_plain_u_lane_kv_waddr), .g_lane_28_g_plain_u_lane_vm_waddr(r_g_lane_28_g_plain_u_lane_vm_waddr), .g_lane_29_g_plain_u_lane_kv_waddr(r_g_lane_29_g_plain_u_lane_kv_waddr), .g_lane_29_g_plain_u_lane_vm_waddr(r_g_lane_29_g_plain_u_lane_vm_waddr), .g_lane_30_g_plain_u_lane_kv_waddr(r_g_lane_30_g_plain_u_lane_kv_waddr), .g_lane_30_g_plain_u_lane_vm_waddr(r_g_lane_30_g_plain_u_lane_vm_waddr), .g_lane_31_g_plain_u_lane_kv_waddr(r_g_lane_31_g_plain_u_lane_kv_waddr), .g_lane_31_g_plain_u_lane_vm_waddr(r_g_lane_31_g_plain_u_lane_vm_waddr), .g_lane_28_g_plain_u_lane_kv_wdata(r_g_lane_28_g_plain_u_lane_kv_wdata), .g_lane_28_g_plain_u_lane_ro_x(r_g_lane_28_g_plain_u_lane_ro_x), .g_lane_28_g_plain_u_lane_vm_wdata(r_g_lane_28_g_plain_u_lane_vm_wdata), .g_lane_29_g_plain_u_lane_kv_wdata(r_g_lane_29_g_plain_u_lane_kv_wdata), .g_lane_29_g_plain_u_lane_ro_x(r_g_lane_29_g_plain_u_lane_ro_x), .g_lane_29_g_plain_u_lane_vm_wdata(r_g_lane_29_g_plain_u_lane_vm_wdata), .g_lane_30_g_plain_u_lane_kv_wdata(r_g_lane_30_g_plain_u_lane_kv_wdata), .g_lane_30_g_plain_u_lane_ro_x(r_g_lane_30_g_plain_u_lane_ro_x), .g_lane_30_g_plain_u_lane_vm_wdata(r_g_lane_30_g_plain_u_lane_vm_wdata), .g_lane_31_g_plain_u_lane_kv_wdata(r_g_lane_31_g_plain_u_lane_kv_wdata), .g_lane_31_g_plain_u_lane_ro_x(r_g_lane_31_g_plain_u_lane_ro_x), .g_lane_31_g_plain_u_lane_vm_wdata(r_g_lane_31_g_plain_u_lane_vm_wdata), .g_lane_28_g_plain_u_lane_rd_addr(r_g_lane_28_g_plain_u_lane_rd_addr), .g_lane_29_g_plain_u_lane_rd_addr(r_g_lane_29_g_plain_u_lane_rd_addr), .g_lane_30_g_plain_u_lane_rd_addr(r_g_lane_30_g_plain_u_lane_rd_addr), .g_lane_31_g_plain_u_lane_rd_addr(r_g_lane_31_g_plain_u_lane_rd_addr), .g_bank_31_u_bank_read_data(r_g_bank_31_u_bank_read_data));
  ot_hbm_su_pg_lanes4_core_strap u_dut (.clk_bank({4{clk}}), .rst_lane_n({4{rst_n}}), .clk_insert({16{clk}}), .clk_bank_macro({24{clk}}), .clk_lane({32{clk}}), .bank0_read_addr__lane0_rd_addr(d_g_bank_28_u_bank_read_addr_1), .lane1_rd_addr__g_bank_N_u_bank_read_addr(d_g_bank_29_u_bank_read_addr), .lane2_rd_addr__g_bank_N_u_bank_read_addr(d_g_bank_30_u_bank_read_addr), .lane3_rd_addr__g_bank_N_u_bank_read_addr(d_g_bank_31_u_bank_read_addr), .lane2_rd_q(i_g_lane_30_g_plain_u_lane_rd_q), .lane3_rd_q(i_g_lane_31_g_plain_u_lane_rd_q), .bank0_read_data(d_g_bank_28_u_bank_read_data), .bank1_read_data(d_g_bank_29_u_bank_read_data), .bank2_read_data(d_g_bank_30_u_bank_read_data), .bank0_rst_n(rst_n), .bank0_write_v(i_g_bank_28_u_bank_write_v), .bank1_write_v(i_g_bank_29_u_bank_write_v), .bank2_write_v(i_g_bank_30_u_bank_write_v), .bank3_write_v(i_g_bank_31_u_bank_write_v), .lane0_bank(i_g_lane_28_g_plain_u_lane_bank), .lane0_co_rnd(i_g_lane_28_g_plain_u_lane_co_rnd), .lane0_cpair(i_g_lane_28_g_plain_u_lane_cpair), .lane0_cx_amin(i_g_lane_28_g_plain_u_lane_cx_amin), .lane0_cx_arelu(i_g_lane_28_g_plain_u_lane_cx_arelu), .lane0_cx_arnd(i_g_lane_28_g_plain_u_lane_cx_arnd), .lane0_cx_cclip(i_g_lane_28_g_plain_u_lane_cx_cclip), .lane0_emit(i_g_lane_28_g_plain_u_lane_emit), .lane0_ld(i_g_lane_28_g_plain_u_lane_ld), .lane0_ld_bank(i_g_lane_28_g_plain_u_lane_ld_bank), .lane0_aind(i_g_lane_28_g_plain_u_lane_aind), .lane0_ce_e2(i_g_lane_28_g_plain_u_lane_ce_e2), .lane0_cm_m2(i_g_lane_28_g_plain_u_lane_cm_m2), .lane0_co_dst(i_g_lane_28_g_plain_u_lane_co_dst), .lane0_dst(i_g_lane_28_g_plain_u_lane_dst), .lane0_ca_ad(i_g_lane_28_g_plain_u_lane_ca_ad), .lane0_ci_sfu(i_g_lane_28_g_plain_u_lane_ci_sfu), .lane0_cm_m1(i_g_lane_28_g_plain_u_lane_cm_m1), .lane0_cm_qm(i_g_lane_28_g_plain_u_lane_cm_qm), .lane0_cp_m1(i_g_lane_28_g_plain_u_lane_cp_m1), .lane0_cs_e1(i_g_lane_28_g_plain_u_lane_cs_e1), .lane0_cs_sfu(i_g_lane_28_g_plain_u_lane_cs_sfu), .bank1_read_v(i_g_bank_29_u_bank_read_v), .bank2_read_v(i_g_bank_30_u_bank_read_v), .bank3_read_v(i_g_bank_31_u_bank_read_v), .bank0_read_v(i_g_bank_28_u_bank_read_v), .lane0_gsh(i_g_lane_28_g_plain_u_lane_gsh), .lane0_srcs(i_g_lane_28_g_plain_u_lane_cx_srcs), .g_bank_N_u_bank_read_addr(i_g_bank_28_u_bank_read_addr), .bank0_write_addr(i_g_bank_28_u_bank_write_addr), .bank1_write_addr(i_g_bank_29_u_bank_write_addr), .bank2_write_addr(i_g_bank_30_u_bank_write_addr), .bank3_write_addr(i_g_bank_31_u_bank_write_addr), .lane0_aibase(i_g_lane_28_g_plain_u_lane_aibase), .lane0_i_v(i_g_lane_28_g_plain_u_lane_i_v), .lane0_krow(i_g_lane_28_g_plain_u_lane_krow), .bank0_write_data(i_g_bank_28_u_bank_write_data), .bank1_write_data(i_g_bank_29_u_bank_write_data), .bank2_write_data(i_g_bank_30_u_bank_write_data), .bank3_write_data(i_g_bank_31_u_bank_write_data), .lane0_ca_imm2(i_g_lane_28_g_plain_u_lane_ca_imm2), .lane0_ce_imm1(i_g_lane_28_g_plain_u_lane_ce_imm1), .lane0_cm_imm1(i_g_lane_28_g_plain_u_lane_cm_imm1), .lane0_cp_imm1(i_g_lane_28_g_plain_u_lane_cp_imm1), .lane0_cs_imm2(i_g_lane_28_g_plain_u_lane_cs_imm2), .lane0_cx_imm3(i_g_lane_28_g_plain_u_lane_cx_imm3), .inj_q(d_inj_q), .lane0_ls(i_g_lane_28_g_plain_u_lane_ls), .lane0_lvw(i_g_lane_28_g_plain_u_lane_lvw), .lane0_ni(i_g_lane_28_g_plain_u_lane_ni), .lane0_no(i_g_lane_28_g_plain_u_lane_no), .lane0_o_v(i_g_lane_28_g_plain_u_lane_o_v), .lane0_obase(i_g_lane_28_g_plain_u_lane_obase), .lane0_side_y(i_g_lane_28_g_plain_u_lane_side_y), .lane0_vb(i_g_lane_28_g_plain_u_lane_vb), .lane0_rd_q(i_g_lane_28_g_plain_u_lane_rd_q), .lane1_rd_q(i_g_lane_29_g_plain_u_lane_rd_q), .lane0_ld_c(i_g_lane_28_g_plain_u_lane_ld_c), .lane0_coll(d_g_lane_28_g_plain_u_lane_coll), .lane0_fault(d_g_lane_28_g_plain_u_lane_fault), .lane0_kv_we(d_g_lane_28_g_plain_u_lane_kv_we), .lane0_ro_v(d_g_lane_28_g_plain_u_lane_ro_v), .lane0_vm_we(d_g_lane_28_g_plain_u_lane_vm_we), .lane1_coll(d_g_lane_29_g_plain_u_lane_coll), .lane1_fault(d_g_lane_29_g_plain_u_lane_fault), .lane1_kv_we(d_g_lane_29_g_plain_u_lane_kv_we), .lane1_ro_v(d_g_lane_29_g_plain_u_lane_ro_v), .lane1_vm_we(d_g_lane_29_g_plain_u_lane_vm_we), .lane2_coll(d_g_lane_30_g_plain_u_lane_coll), .lane2_fault(d_g_lane_30_g_plain_u_lane_fault), .lane2_kv_we(d_g_lane_30_g_plain_u_lane_kv_we), .lane2_ro_v(d_g_lane_30_g_plain_u_lane_ro_v), .lane2_vm_we(d_g_lane_30_g_plain_u_lane_vm_we), .lane3_coll(d_g_lane_31_g_plain_u_lane_coll), .lane3_fault(d_g_lane_31_g_plain_u_lane_fault), .lane3_kv_we(d_g_lane_31_g_plain_u_lane_kv_we), .lane3_ro_v(d_g_lane_31_g_plain_u_lane_ro_v), .lane3_vm_we(d_g_lane_31_g_plain_u_lane_vm_we), .lane0_rd_re(d_g_lane_28_g_plain_u_lane_rd_re), .lane1_rd_re(d_g_lane_29_g_plain_u_lane_rd_re), .lane2_rd_re(d_g_lane_30_g_plain_u_lane_rd_re), .lane3_rd_re(d_g_lane_31_g_plain_u_lane_rd_re), .lane0_rd_src(d_g_lane_28_g_plain_u_lane_rd_src), .lane1_rd_src(d_g_lane_29_g_plain_u_lane_rd_src), .lane2_rd_src(d_g_lane_30_g_plain_u_lane_rd_src), .lane3_rd_src(d_g_lane_31_g_plain_u_lane_rd_src), .lane0_kv_waddr(d_g_lane_28_g_plain_u_lane_kv_waddr), .lane0_vm_waddr(d_g_lane_28_g_plain_u_lane_vm_waddr), .lane1_kv_waddr(d_g_lane_29_g_plain_u_lane_kv_waddr), .lane1_vm_waddr(d_g_lane_29_g_plain_u_lane_vm_waddr), .lane2_kv_waddr(d_g_lane_30_g_plain_u_lane_kv_waddr), .lane2_vm_waddr(d_g_lane_30_g_plain_u_lane_vm_waddr), .lane3_kv_waddr(d_g_lane_31_g_plain_u_lane_kv_waddr), .lane3_vm_waddr(d_g_lane_31_g_plain_u_lane_vm_waddr), .lane0_kv_wdata(d_g_lane_28_g_plain_u_lane_kv_wdata), .lane0_ro_x(d_g_lane_28_g_plain_u_lane_ro_x), .lane0_vm_wdata(d_g_lane_28_g_plain_u_lane_vm_wdata), .lane1_kv_wdata(d_g_lane_29_g_plain_u_lane_kv_wdata), .lane1_ro_x(d_g_lane_29_g_plain_u_lane_ro_x), .lane1_vm_wdata(d_g_lane_29_g_plain_u_lane_vm_wdata), .lane2_kv_wdata(d_g_lane_30_g_plain_u_lane_kv_wdata), .lane2_ro_x(d_g_lane_30_g_plain_u_lane_ro_x), .lane2_vm_wdata(d_g_lane_30_g_plain_u_lane_vm_wdata), .lane3_kv_wdata(d_g_lane_31_g_plain_u_lane_kv_wdata), .lane3_ro_x(d_g_lane_31_g_plain_u_lane_ro_x), .lane3_vm_wdata(d_g_lane_31_g_plain_u_lane_vm_wdata), .lane0_rd_addr(d_g_lane_28_g_plain_u_lane_rd_addr), .lane1_rd_addr__g_lane_N_g_plain_u_lane_rd_addr(d_g_lane_29_g_plain_u_lane_rd_addr), .lane2_rd_addr__g_lane_N_g_plain_u_lane_rd_addr(d_g_lane_30_g_plain_u_lane_rd_addr), .lane3_rd_addr__g_lane_N_g_plain_u_lane_rd_addr(d_g_lane_31_g_plain_u_lane_rd_addr), .bank3_read_data(d_g_bank_31_u_bank_read_data), .strap_lane0_lane_id(11'b00001001100), .strap_lane1_lane_id(11'b00001001101), .strap_lane2_lane_id(11'b00001001110), .strap_lane3_lane_id(11'b00001001111));
  ot_hbm_su_pg_lanes4_core_strap u_mut (.clk_bank({4{clk}}), .rst_lane_n({4{rst_n}}), .clk_insert({16{clk}}), .clk_bank_macro({24{clk}}), .clk_lane({32{clk}}), .bank0_read_addr__lane0_rd_addr(m_g_bank_28_u_bank_read_addr_1), .lane1_rd_addr__g_bank_N_u_bank_read_addr(m_g_bank_29_u_bank_read_addr), .lane2_rd_addr__g_bank_N_u_bank_read_addr(m_g_bank_30_u_bank_read_addr), .lane3_rd_addr__g_bank_N_u_bank_read_addr(m_g_bank_31_u_bank_read_addr), .lane2_rd_q(i_g_lane_30_g_plain_u_lane_rd_q), .lane3_rd_q(i_g_lane_31_g_plain_u_lane_rd_q), .bank0_read_data(m_g_bank_28_u_bank_read_data), .bank1_read_data(m_g_bank_29_u_bank_read_data), .bank2_read_data(m_g_bank_30_u_bank_read_data), .bank0_rst_n(rst_n), .bank0_write_v(i_g_bank_28_u_bank_write_v), .bank1_write_v(i_g_bank_29_u_bank_write_v), .bank2_write_v(i_g_bank_30_u_bank_write_v), .bank3_write_v(i_g_bank_31_u_bank_write_v), .lane0_bank(i_g_lane_28_g_plain_u_lane_bank), .lane0_co_rnd(i_g_lane_28_g_plain_u_lane_co_rnd), .lane0_cpair(i_g_lane_28_g_plain_u_lane_cpair), .lane0_cx_amin(i_g_lane_28_g_plain_u_lane_cx_amin), .lane0_cx_arelu(i_g_lane_28_g_plain_u_lane_cx_arelu), .lane0_cx_arnd(i_g_lane_28_g_plain_u_lane_cx_arnd), .lane0_cx_cclip(i_g_lane_28_g_plain_u_lane_cx_cclip), .lane0_emit(i_g_lane_28_g_plain_u_lane_emit), .lane0_ld(i_g_lane_28_g_plain_u_lane_ld), .lane0_ld_bank(i_g_lane_28_g_plain_u_lane_ld_bank), .lane0_aind(i_g_lane_28_g_plain_u_lane_aind), .lane0_ce_e2(i_g_lane_28_g_plain_u_lane_ce_e2), .lane0_cm_m2(i_g_lane_28_g_plain_u_lane_cm_m2), .lane0_co_dst(i_g_lane_28_g_plain_u_lane_co_dst), .lane0_dst(i_g_lane_28_g_plain_u_lane_dst), .lane0_ca_ad(i_g_lane_28_g_plain_u_lane_ca_ad), .lane0_ci_sfu(i_g_lane_28_g_plain_u_lane_ci_sfu), .lane0_cm_m1(i_g_lane_28_g_plain_u_lane_cm_m1), .lane0_cm_qm(i_g_lane_28_g_plain_u_lane_cm_qm), .lane0_cp_m1(i_g_lane_28_g_plain_u_lane_cp_m1), .lane0_cs_e1(i_g_lane_28_g_plain_u_lane_cs_e1), .lane0_cs_sfu(i_g_lane_28_g_plain_u_lane_cs_sfu), .bank1_read_v(i_g_bank_29_u_bank_read_v), .bank2_read_v(i_g_bank_30_u_bank_read_v), .bank3_read_v(i_g_bank_31_u_bank_read_v), .bank0_read_v(i_g_bank_28_u_bank_read_v), .lane0_gsh(i_g_lane_28_g_plain_u_lane_gsh), .lane0_srcs(i_g_lane_28_g_plain_u_lane_cx_srcs), .g_bank_N_u_bank_read_addr(i_g_bank_28_u_bank_read_addr), .bank0_write_addr(i_g_bank_28_u_bank_write_addr), .bank1_write_addr(i_g_bank_29_u_bank_write_addr), .bank2_write_addr(i_g_bank_30_u_bank_write_addr), .bank3_write_addr(i_g_bank_31_u_bank_write_addr), .lane0_aibase(i_g_lane_28_g_plain_u_lane_aibase), .lane0_i_v(i_g_lane_28_g_plain_u_lane_i_v), .lane0_krow(i_g_lane_28_g_plain_u_lane_krow), .bank0_write_data(i_g_bank_28_u_bank_write_data), .bank1_write_data(i_g_bank_29_u_bank_write_data), .bank2_write_data(i_g_bank_30_u_bank_write_data), .bank3_write_data(i_g_bank_31_u_bank_write_data), .lane0_ca_imm2(i_g_lane_28_g_plain_u_lane_ca_imm2), .lane0_ce_imm1(i_g_lane_28_g_plain_u_lane_ce_imm1), .lane0_cm_imm1(i_g_lane_28_g_plain_u_lane_cm_imm1), .lane0_cp_imm1(i_g_lane_28_g_plain_u_lane_cp_imm1), .lane0_cs_imm2(i_g_lane_28_g_plain_u_lane_cs_imm2), .lane0_cx_imm3(i_g_lane_28_g_plain_u_lane_cx_imm3), .inj_q(m_inj_q), .lane0_ls(i_g_lane_28_g_plain_u_lane_ls), .lane0_lvw(i_g_lane_28_g_plain_u_lane_lvw), .lane0_ni(i_g_lane_28_g_plain_u_lane_ni), .lane0_no(i_g_lane_28_g_plain_u_lane_no), .lane0_o_v(i_g_lane_28_g_plain_u_lane_o_v), .lane0_obase(i_g_lane_28_g_plain_u_lane_obase), .lane0_side_y(i_g_lane_28_g_plain_u_lane_side_y), .lane0_vb(i_g_lane_28_g_plain_u_lane_vb), .lane0_rd_q(i_g_lane_28_g_plain_u_lane_rd_q), .lane1_rd_q(i_g_lane_29_g_plain_u_lane_rd_q), .lane0_ld_c(i_g_lane_28_g_plain_u_lane_ld_c), .lane0_coll(m_g_lane_28_g_plain_u_lane_coll), .lane0_fault(m_g_lane_28_g_plain_u_lane_fault), .lane0_kv_we(m_g_lane_28_g_plain_u_lane_kv_we), .lane0_ro_v(m_g_lane_28_g_plain_u_lane_ro_v), .lane0_vm_we(m_g_lane_28_g_plain_u_lane_vm_we), .lane1_coll(m_g_lane_29_g_plain_u_lane_coll), .lane1_fault(m_g_lane_29_g_plain_u_lane_fault), .lane1_kv_we(m_g_lane_29_g_plain_u_lane_kv_we), .lane1_ro_v(m_g_lane_29_g_plain_u_lane_ro_v), .lane1_vm_we(m_g_lane_29_g_plain_u_lane_vm_we), .lane2_coll(m_g_lane_30_g_plain_u_lane_coll), .lane2_fault(m_g_lane_30_g_plain_u_lane_fault), .lane2_kv_we(m_g_lane_30_g_plain_u_lane_kv_we), .lane2_ro_v(m_g_lane_30_g_plain_u_lane_ro_v), .lane2_vm_we(m_g_lane_30_g_plain_u_lane_vm_we), .lane3_coll(m_g_lane_31_g_plain_u_lane_coll), .lane3_fault(m_g_lane_31_g_plain_u_lane_fault), .lane3_kv_we(m_g_lane_31_g_plain_u_lane_kv_we), .lane3_ro_v(m_g_lane_31_g_plain_u_lane_ro_v), .lane3_vm_we(m_g_lane_31_g_plain_u_lane_vm_we), .lane0_rd_re(m_g_lane_28_g_plain_u_lane_rd_re), .lane1_rd_re(m_g_lane_29_g_plain_u_lane_rd_re), .lane2_rd_re(m_g_lane_30_g_plain_u_lane_rd_re), .lane3_rd_re(m_g_lane_31_g_plain_u_lane_rd_re), .lane0_rd_src(m_g_lane_28_g_plain_u_lane_rd_src), .lane1_rd_src(m_g_lane_29_g_plain_u_lane_rd_src), .lane2_rd_src(m_g_lane_30_g_plain_u_lane_rd_src), .lane3_rd_src(m_g_lane_31_g_plain_u_lane_rd_src), .lane0_kv_waddr(m_g_lane_28_g_plain_u_lane_kv_waddr), .lane0_vm_waddr(m_g_lane_28_g_plain_u_lane_vm_waddr), .lane1_kv_waddr(m_g_lane_29_g_plain_u_lane_kv_waddr), .lane1_vm_waddr(m_g_lane_29_g_plain_u_lane_vm_waddr), .lane2_kv_waddr(m_g_lane_30_g_plain_u_lane_kv_waddr), .lane2_vm_waddr(m_g_lane_30_g_plain_u_lane_vm_waddr), .lane3_kv_waddr(m_g_lane_31_g_plain_u_lane_kv_waddr), .lane3_vm_waddr(m_g_lane_31_g_plain_u_lane_vm_waddr), .lane0_kv_wdata(m_g_lane_28_g_plain_u_lane_kv_wdata), .lane0_ro_x(m_g_lane_28_g_plain_u_lane_ro_x), .lane0_vm_wdata(m_g_lane_28_g_plain_u_lane_vm_wdata), .lane1_kv_wdata(m_g_lane_29_g_plain_u_lane_kv_wdata), .lane1_ro_x(m_g_lane_29_g_plain_u_lane_ro_x), .lane1_vm_wdata(m_g_lane_29_g_plain_u_lane_vm_wdata), .lane2_kv_wdata(m_g_lane_30_g_plain_u_lane_kv_wdata), .lane2_ro_x(m_g_lane_30_g_plain_u_lane_ro_x), .lane2_vm_wdata(m_g_lane_30_g_plain_u_lane_vm_wdata), .lane3_kv_wdata(m_g_lane_31_g_plain_u_lane_kv_wdata), .lane3_ro_x(m_g_lane_31_g_plain_u_lane_ro_x), .lane3_vm_wdata(m_g_lane_31_g_plain_u_lane_vm_wdata), .lane0_rd_addr(m_g_lane_28_g_plain_u_lane_rd_addr), .lane1_rd_addr__g_lane_N_g_plain_u_lane_rd_addr(m_g_lane_29_g_plain_u_lane_rd_addr), .lane2_rd_addr__g_lane_N_g_plain_u_lane_rd_addr(m_g_lane_30_g_plain_u_lane_rd_addr), .lane3_rd_addr__g_lane_N_g_plain_u_lane_rd_addr(m_g_lane_31_g_plain_u_lane_rd_addr), .bank3_read_data(m_g_bank_31_u_bank_read_data), .strap_lane0_lane_id(11'b00001001101), .strap_lane1_lane_id(11'b00001001101), .strap_lane2_lane_id(11'b00001001110), .strap_lane3_lane_id(11'b00001001111));
  always @(negedge clk) begin
    i_g_lane_30_g_plain_u_lane_rd_q <= {$urandom, $urandom, $urandom, $urandom};
    i_g_lane_31_g_plain_u_lane_rd_q <= {$urandom, $urandom, $urandom, $urandom};
    i_g_bank_28_u_bank_write_v <= {$urandom};
    i_g_bank_29_u_bank_write_v <= {$urandom};
    i_g_bank_30_u_bank_write_v <= {$urandom};
    i_g_bank_31_u_bank_write_v <= {$urandom};
    i_g_lane_28_g_plain_u_lane_bank <= {$urandom};
    i_g_lane_28_g_plain_u_lane_co_rnd <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cpair <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cx_amin <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cx_arelu <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cx_arnd <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cx_cclip <= {$urandom};
    i_g_lane_28_g_plain_u_lane_emit <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ld <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ld_bank <= {$urandom};
    i_g_lane_28_g_plain_u_lane_aind <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ce_e2 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cm_m2 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_co_dst <= {$urandom};
    i_g_lane_28_g_plain_u_lane_dst <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ca_ad <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ci_sfu <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cm_m1 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cm_qm <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cp_m1 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cs_e1 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cs_sfu <= {$urandom};
    i_g_bank_29_u_bank_read_v <= {$urandom};
    i_g_bank_30_u_bank_read_v <= {$urandom};
    i_g_bank_31_u_bank_read_v <= {$urandom};
    i_g_bank_28_u_bank_read_v <= {$urandom};
    i_g_lane_28_g_plain_u_lane_gsh <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cx_srcs <= {$urandom};
    i_g_bank_28_u_bank_read_addr <= {$urandom};
    i_g_bank_28_u_bank_write_addr <= {$urandom};
    i_g_bank_29_u_bank_write_addr <= {$urandom};
    i_g_bank_30_u_bank_write_addr <= {$urandom};
    i_g_bank_31_u_bank_write_addr <= {$urandom};
    i_g_lane_28_g_plain_u_lane_aibase <= {$urandom};
    i_g_lane_28_g_plain_u_lane_i_v <= {$urandom};
    i_g_lane_28_g_plain_u_lane_krow <= {$urandom};
    i_g_bank_28_u_bank_write_data <= {$urandom};
    i_g_bank_29_u_bank_write_data <= {$urandom};
    i_g_bank_30_u_bank_write_data <= {$urandom};
    i_g_bank_31_u_bank_write_data <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ca_imm2 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ce_imm1 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cm_imm1 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cp_imm1 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cs_imm2 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_cx_imm3 <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ls <= {$urandom};
    i_g_lane_28_g_plain_u_lane_lvw <= {$urandom};
    i_g_lane_28_g_plain_u_lane_ni <= {$urandom};
    i_g_lane_28_g_plain_u_lane_no <= {$urandom};
    i_g_lane_28_g_plain_u_lane_o_v <= {$urandom};
    i_g_lane_28_g_plain_u_lane_obase <= {$urandom};
    i_g_lane_28_g_plain_u_lane_side_y <= {$urandom};
    i_g_lane_28_g_plain_u_lane_vb <= {$urandom, $urandom, $urandom, $urandom};
    i_g_lane_28_g_plain_u_lane_rd_q <= {$urandom, $urandom, $urandom, $urandom};
    i_g_lane_29_g_plain_u_lane_rd_q <= {$urandom, $urandom, $urandom, $urandom};
    i_g_lane_28_g_plain_u_lane_ld_c <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
  end
  always @(posedge clk) begin
    cyc <= cyc + 1; if (cyc == 8) rst_n <= 1;
    if (d_g_bank_28_u_bank_read_addr_1 !== r_g_bank_28_u_bank_read_addr_1) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_bank_28_u_bank_read_addr_1", cyc); end
    if (m_g_bank_28_u_bank_read_addr_1 !== r_g_bank_28_u_bank_read_addr_1) nmut = nmut + 1;
    if (r_g_bank_28_u_bank_read_addr_1 !== p_g_bank_28_u_bank_read_addr_1) nact = nact + 1; p_g_bank_28_u_bank_read_addr_1 <= r_g_bank_28_u_bank_read_addr_1;
    if (d_g_bank_29_u_bank_read_addr !== r_g_bank_29_u_bank_read_addr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_bank_29_u_bank_read_addr", cyc); end
    if (m_g_bank_29_u_bank_read_addr !== r_g_bank_29_u_bank_read_addr) nmut = nmut + 1;
    if (r_g_bank_29_u_bank_read_addr !== p_g_bank_29_u_bank_read_addr) nact = nact + 1; p_g_bank_29_u_bank_read_addr <= r_g_bank_29_u_bank_read_addr;
    if (d_g_bank_30_u_bank_read_addr !== r_g_bank_30_u_bank_read_addr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_bank_30_u_bank_read_addr", cyc); end
    if (m_g_bank_30_u_bank_read_addr !== r_g_bank_30_u_bank_read_addr) nmut = nmut + 1;
    if (r_g_bank_30_u_bank_read_addr !== p_g_bank_30_u_bank_read_addr) nact = nact + 1; p_g_bank_30_u_bank_read_addr <= r_g_bank_30_u_bank_read_addr;
    if (d_g_bank_31_u_bank_read_addr !== r_g_bank_31_u_bank_read_addr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_bank_31_u_bank_read_addr", cyc); end
    if (m_g_bank_31_u_bank_read_addr !== r_g_bank_31_u_bank_read_addr) nmut = nmut + 1;
    if (r_g_bank_31_u_bank_read_addr !== p_g_bank_31_u_bank_read_addr) nact = nact + 1; p_g_bank_31_u_bank_read_addr <= r_g_bank_31_u_bank_read_addr;
    if (d_g_bank_28_u_bank_read_data !== r_g_bank_28_u_bank_read_data) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_bank_28_u_bank_read_data", cyc); end
    if (m_g_bank_28_u_bank_read_data !== r_g_bank_28_u_bank_read_data) nmut = nmut + 1;
    if (r_g_bank_28_u_bank_read_data !== p_g_bank_28_u_bank_read_data) nact = nact + 1; p_g_bank_28_u_bank_read_data <= r_g_bank_28_u_bank_read_data;
    if (d_g_bank_29_u_bank_read_data !== r_g_bank_29_u_bank_read_data) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_bank_29_u_bank_read_data", cyc); end
    if (m_g_bank_29_u_bank_read_data !== r_g_bank_29_u_bank_read_data) nmut = nmut + 1;
    if (r_g_bank_29_u_bank_read_data !== p_g_bank_29_u_bank_read_data) nact = nact + 1; p_g_bank_29_u_bank_read_data <= r_g_bank_29_u_bank_read_data;
    if (d_g_bank_30_u_bank_read_data !== r_g_bank_30_u_bank_read_data) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_bank_30_u_bank_read_data", cyc); end
    if (m_g_bank_30_u_bank_read_data !== r_g_bank_30_u_bank_read_data) nmut = nmut + 1;
    if (r_g_bank_30_u_bank_read_data !== p_g_bank_30_u_bank_read_data) nact = nact + 1; p_g_bank_30_u_bank_read_data <= r_g_bank_30_u_bank_read_data;
    if (d_inj_q !== r_inj_q) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d inj_q", cyc); end
    if (m_inj_q !== r_inj_q) nmut = nmut + 1;
    if (r_inj_q !== p_inj_q) nact = nact + 1; p_inj_q <= r_inj_q;
    if (d_g_lane_28_g_plain_u_lane_coll !== r_g_lane_28_g_plain_u_lane_coll) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_coll", cyc); end
    if (m_g_lane_28_g_plain_u_lane_coll !== r_g_lane_28_g_plain_u_lane_coll) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_coll !== p_g_lane_28_g_plain_u_lane_coll) nact = nact + 1; p_g_lane_28_g_plain_u_lane_coll <= r_g_lane_28_g_plain_u_lane_coll;
    if (d_g_lane_28_g_plain_u_lane_fault !== r_g_lane_28_g_plain_u_lane_fault) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_fault", cyc); end
    if (m_g_lane_28_g_plain_u_lane_fault !== r_g_lane_28_g_plain_u_lane_fault) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_fault !== p_g_lane_28_g_plain_u_lane_fault) nact = nact + 1; p_g_lane_28_g_plain_u_lane_fault <= r_g_lane_28_g_plain_u_lane_fault;
    if (d_g_lane_28_g_plain_u_lane_kv_we !== r_g_lane_28_g_plain_u_lane_kv_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_kv_we", cyc); end
    if (m_g_lane_28_g_plain_u_lane_kv_we !== r_g_lane_28_g_plain_u_lane_kv_we) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_kv_we !== p_g_lane_28_g_plain_u_lane_kv_we) nact = nact + 1; p_g_lane_28_g_plain_u_lane_kv_we <= r_g_lane_28_g_plain_u_lane_kv_we;
    if (d_g_lane_28_g_plain_u_lane_ro_v !== r_g_lane_28_g_plain_u_lane_ro_v) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_ro_v", cyc); end
    if (m_g_lane_28_g_plain_u_lane_ro_v !== r_g_lane_28_g_plain_u_lane_ro_v) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_ro_v !== p_g_lane_28_g_plain_u_lane_ro_v) nact = nact + 1; p_g_lane_28_g_plain_u_lane_ro_v <= r_g_lane_28_g_plain_u_lane_ro_v;
    if (d_g_lane_28_g_plain_u_lane_vm_we !== r_g_lane_28_g_plain_u_lane_vm_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_vm_we", cyc); end
    if (m_g_lane_28_g_plain_u_lane_vm_we !== r_g_lane_28_g_plain_u_lane_vm_we) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_vm_we !== p_g_lane_28_g_plain_u_lane_vm_we) nact = nact + 1; p_g_lane_28_g_plain_u_lane_vm_we <= r_g_lane_28_g_plain_u_lane_vm_we;
    if (d_g_lane_29_g_plain_u_lane_coll !== r_g_lane_29_g_plain_u_lane_coll) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_coll", cyc); end
    if (m_g_lane_29_g_plain_u_lane_coll !== r_g_lane_29_g_plain_u_lane_coll) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_coll !== p_g_lane_29_g_plain_u_lane_coll) nact = nact + 1; p_g_lane_29_g_plain_u_lane_coll <= r_g_lane_29_g_plain_u_lane_coll;
    if (d_g_lane_29_g_plain_u_lane_fault !== r_g_lane_29_g_plain_u_lane_fault) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_fault", cyc); end
    if (m_g_lane_29_g_plain_u_lane_fault !== r_g_lane_29_g_plain_u_lane_fault) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_fault !== p_g_lane_29_g_plain_u_lane_fault) nact = nact + 1; p_g_lane_29_g_plain_u_lane_fault <= r_g_lane_29_g_plain_u_lane_fault;
    if (d_g_lane_29_g_plain_u_lane_kv_we !== r_g_lane_29_g_plain_u_lane_kv_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_kv_we", cyc); end
    if (m_g_lane_29_g_plain_u_lane_kv_we !== r_g_lane_29_g_plain_u_lane_kv_we) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_kv_we !== p_g_lane_29_g_plain_u_lane_kv_we) nact = nact + 1; p_g_lane_29_g_plain_u_lane_kv_we <= r_g_lane_29_g_plain_u_lane_kv_we;
    if (d_g_lane_29_g_plain_u_lane_ro_v !== r_g_lane_29_g_plain_u_lane_ro_v) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_ro_v", cyc); end
    if (m_g_lane_29_g_plain_u_lane_ro_v !== r_g_lane_29_g_plain_u_lane_ro_v) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_ro_v !== p_g_lane_29_g_plain_u_lane_ro_v) nact = nact + 1; p_g_lane_29_g_plain_u_lane_ro_v <= r_g_lane_29_g_plain_u_lane_ro_v;
    if (d_g_lane_29_g_plain_u_lane_vm_we !== r_g_lane_29_g_plain_u_lane_vm_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_vm_we", cyc); end
    if (m_g_lane_29_g_plain_u_lane_vm_we !== r_g_lane_29_g_plain_u_lane_vm_we) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_vm_we !== p_g_lane_29_g_plain_u_lane_vm_we) nact = nact + 1; p_g_lane_29_g_plain_u_lane_vm_we <= r_g_lane_29_g_plain_u_lane_vm_we;
    if (d_g_lane_30_g_plain_u_lane_coll !== r_g_lane_30_g_plain_u_lane_coll) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_coll", cyc); end
    if (m_g_lane_30_g_plain_u_lane_coll !== r_g_lane_30_g_plain_u_lane_coll) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_coll !== p_g_lane_30_g_plain_u_lane_coll) nact = nact + 1; p_g_lane_30_g_plain_u_lane_coll <= r_g_lane_30_g_plain_u_lane_coll;
    if (d_g_lane_30_g_plain_u_lane_fault !== r_g_lane_30_g_plain_u_lane_fault) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_fault", cyc); end
    if (m_g_lane_30_g_plain_u_lane_fault !== r_g_lane_30_g_plain_u_lane_fault) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_fault !== p_g_lane_30_g_plain_u_lane_fault) nact = nact + 1; p_g_lane_30_g_plain_u_lane_fault <= r_g_lane_30_g_plain_u_lane_fault;
    if (d_g_lane_30_g_plain_u_lane_kv_we !== r_g_lane_30_g_plain_u_lane_kv_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_kv_we", cyc); end
    if (m_g_lane_30_g_plain_u_lane_kv_we !== r_g_lane_30_g_plain_u_lane_kv_we) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_kv_we !== p_g_lane_30_g_plain_u_lane_kv_we) nact = nact + 1; p_g_lane_30_g_plain_u_lane_kv_we <= r_g_lane_30_g_plain_u_lane_kv_we;
    if (d_g_lane_30_g_plain_u_lane_ro_v !== r_g_lane_30_g_plain_u_lane_ro_v) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_ro_v", cyc); end
    if (m_g_lane_30_g_plain_u_lane_ro_v !== r_g_lane_30_g_plain_u_lane_ro_v) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_ro_v !== p_g_lane_30_g_plain_u_lane_ro_v) nact = nact + 1; p_g_lane_30_g_plain_u_lane_ro_v <= r_g_lane_30_g_plain_u_lane_ro_v;
    if (d_g_lane_30_g_plain_u_lane_vm_we !== r_g_lane_30_g_plain_u_lane_vm_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_vm_we", cyc); end
    if (m_g_lane_30_g_plain_u_lane_vm_we !== r_g_lane_30_g_plain_u_lane_vm_we) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_vm_we !== p_g_lane_30_g_plain_u_lane_vm_we) nact = nact + 1; p_g_lane_30_g_plain_u_lane_vm_we <= r_g_lane_30_g_plain_u_lane_vm_we;
    if (d_g_lane_31_g_plain_u_lane_coll !== r_g_lane_31_g_plain_u_lane_coll) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_coll", cyc); end
    if (m_g_lane_31_g_plain_u_lane_coll !== r_g_lane_31_g_plain_u_lane_coll) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_coll !== p_g_lane_31_g_plain_u_lane_coll) nact = nact + 1; p_g_lane_31_g_plain_u_lane_coll <= r_g_lane_31_g_plain_u_lane_coll;
    if (d_g_lane_31_g_plain_u_lane_fault !== r_g_lane_31_g_plain_u_lane_fault) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_fault", cyc); end
    if (m_g_lane_31_g_plain_u_lane_fault !== r_g_lane_31_g_plain_u_lane_fault) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_fault !== p_g_lane_31_g_plain_u_lane_fault) nact = nact + 1; p_g_lane_31_g_plain_u_lane_fault <= r_g_lane_31_g_plain_u_lane_fault;
    if (d_g_lane_31_g_plain_u_lane_kv_we !== r_g_lane_31_g_plain_u_lane_kv_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_kv_we", cyc); end
    if (m_g_lane_31_g_plain_u_lane_kv_we !== r_g_lane_31_g_plain_u_lane_kv_we) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_kv_we !== p_g_lane_31_g_plain_u_lane_kv_we) nact = nact + 1; p_g_lane_31_g_plain_u_lane_kv_we <= r_g_lane_31_g_plain_u_lane_kv_we;
    if (d_g_lane_31_g_plain_u_lane_ro_v !== r_g_lane_31_g_plain_u_lane_ro_v) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_ro_v", cyc); end
    if (m_g_lane_31_g_plain_u_lane_ro_v !== r_g_lane_31_g_plain_u_lane_ro_v) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_ro_v !== p_g_lane_31_g_plain_u_lane_ro_v) nact = nact + 1; p_g_lane_31_g_plain_u_lane_ro_v <= r_g_lane_31_g_plain_u_lane_ro_v;
    if (d_g_lane_31_g_plain_u_lane_vm_we !== r_g_lane_31_g_plain_u_lane_vm_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_vm_we", cyc); end
    if (m_g_lane_31_g_plain_u_lane_vm_we !== r_g_lane_31_g_plain_u_lane_vm_we) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_vm_we !== p_g_lane_31_g_plain_u_lane_vm_we) nact = nact + 1; p_g_lane_31_g_plain_u_lane_vm_we <= r_g_lane_31_g_plain_u_lane_vm_we;
    if (d_g_lane_28_g_plain_u_lane_rd_re !== r_g_lane_28_g_plain_u_lane_rd_re) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_rd_re", cyc); end
    if (m_g_lane_28_g_plain_u_lane_rd_re !== r_g_lane_28_g_plain_u_lane_rd_re) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_rd_re !== p_g_lane_28_g_plain_u_lane_rd_re) nact = nact + 1; p_g_lane_28_g_plain_u_lane_rd_re <= r_g_lane_28_g_plain_u_lane_rd_re;
    if (d_g_lane_29_g_plain_u_lane_rd_re !== r_g_lane_29_g_plain_u_lane_rd_re) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_rd_re", cyc); end
    if (m_g_lane_29_g_plain_u_lane_rd_re !== r_g_lane_29_g_plain_u_lane_rd_re) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_rd_re !== p_g_lane_29_g_plain_u_lane_rd_re) nact = nact + 1; p_g_lane_29_g_plain_u_lane_rd_re <= r_g_lane_29_g_plain_u_lane_rd_re;
    if (d_g_lane_30_g_plain_u_lane_rd_re !== r_g_lane_30_g_plain_u_lane_rd_re) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_rd_re", cyc); end
    if (m_g_lane_30_g_plain_u_lane_rd_re !== r_g_lane_30_g_plain_u_lane_rd_re) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_rd_re !== p_g_lane_30_g_plain_u_lane_rd_re) nact = nact + 1; p_g_lane_30_g_plain_u_lane_rd_re <= r_g_lane_30_g_plain_u_lane_rd_re;
    if (d_g_lane_31_g_plain_u_lane_rd_re !== r_g_lane_31_g_plain_u_lane_rd_re) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_rd_re", cyc); end
    if (m_g_lane_31_g_plain_u_lane_rd_re !== r_g_lane_31_g_plain_u_lane_rd_re) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_rd_re !== p_g_lane_31_g_plain_u_lane_rd_re) nact = nact + 1; p_g_lane_31_g_plain_u_lane_rd_re <= r_g_lane_31_g_plain_u_lane_rd_re;
    if (d_g_lane_28_g_plain_u_lane_rd_src !== r_g_lane_28_g_plain_u_lane_rd_src) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_rd_src", cyc); end
    if (m_g_lane_28_g_plain_u_lane_rd_src !== r_g_lane_28_g_plain_u_lane_rd_src) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_rd_src !== p_g_lane_28_g_plain_u_lane_rd_src) nact = nact + 1; p_g_lane_28_g_plain_u_lane_rd_src <= r_g_lane_28_g_plain_u_lane_rd_src;
    if (d_g_lane_29_g_plain_u_lane_rd_src !== r_g_lane_29_g_plain_u_lane_rd_src) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_rd_src", cyc); end
    if (m_g_lane_29_g_plain_u_lane_rd_src !== r_g_lane_29_g_plain_u_lane_rd_src) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_rd_src !== p_g_lane_29_g_plain_u_lane_rd_src) nact = nact + 1; p_g_lane_29_g_plain_u_lane_rd_src <= r_g_lane_29_g_plain_u_lane_rd_src;
    if (d_g_lane_30_g_plain_u_lane_rd_src !== r_g_lane_30_g_plain_u_lane_rd_src) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_rd_src", cyc); end
    if (m_g_lane_30_g_plain_u_lane_rd_src !== r_g_lane_30_g_plain_u_lane_rd_src) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_rd_src !== p_g_lane_30_g_plain_u_lane_rd_src) nact = nact + 1; p_g_lane_30_g_plain_u_lane_rd_src <= r_g_lane_30_g_plain_u_lane_rd_src;
    if (d_g_lane_31_g_plain_u_lane_rd_src !== r_g_lane_31_g_plain_u_lane_rd_src) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_rd_src", cyc); end
    if (m_g_lane_31_g_plain_u_lane_rd_src !== r_g_lane_31_g_plain_u_lane_rd_src) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_rd_src !== p_g_lane_31_g_plain_u_lane_rd_src) nact = nact + 1; p_g_lane_31_g_plain_u_lane_rd_src <= r_g_lane_31_g_plain_u_lane_rd_src;
    if (d_g_lane_28_g_plain_u_lane_kv_waddr !== r_g_lane_28_g_plain_u_lane_kv_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_kv_waddr", cyc); end
    if (m_g_lane_28_g_plain_u_lane_kv_waddr !== r_g_lane_28_g_plain_u_lane_kv_waddr) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_kv_waddr !== p_g_lane_28_g_plain_u_lane_kv_waddr) nact = nact + 1; p_g_lane_28_g_plain_u_lane_kv_waddr <= r_g_lane_28_g_plain_u_lane_kv_waddr;
    if (d_g_lane_28_g_plain_u_lane_vm_waddr !== r_g_lane_28_g_plain_u_lane_vm_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_vm_waddr", cyc); end
    if (m_g_lane_28_g_plain_u_lane_vm_waddr !== r_g_lane_28_g_plain_u_lane_vm_waddr) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_vm_waddr !== p_g_lane_28_g_plain_u_lane_vm_waddr) nact = nact + 1; p_g_lane_28_g_plain_u_lane_vm_waddr <= r_g_lane_28_g_plain_u_lane_vm_waddr;
    if (d_g_lane_29_g_plain_u_lane_kv_waddr !== r_g_lane_29_g_plain_u_lane_kv_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_kv_waddr", cyc); end
    if (m_g_lane_29_g_plain_u_lane_kv_waddr !== r_g_lane_29_g_plain_u_lane_kv_waddr) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_kv_waddr !== p_g_lane_29_g_plain_u_lane_kv_waddr) nact = nact + 1; p_g_lane_29_g_plain_u_lane_kv_waddr <= r_g_lane_29_g_plain_u_lane_kv_waddr;
    if (d_g_lane_29_g_plain_u_lane_vm_waddr !== r_g_lane_29_g_plain_u_lane_vm_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_vm_waddr", cyc); end
    if (m_g_lane_29_g_plain_u_lane_vm_waddr !== r_g_lane_29_g_plain_u_lane_vm_waddr) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_vm_waddr !== p_g_lane_29_g_plain_u_lane_vm_waddr) nact = nact + 1; p_g_lane_29_g_plain_u_lane_vm_waddr <= r_g_lane_29_g_plain_u_lane_vm_waddr;
    if (d_g_lane_30_g_plain_u_lane_kv_waddr !== r_g_lane_30_g_plain_u_lane_kv_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_kv_waddr", cyc); end
    if (m_g_lane_30_g_plain_u_lane_kv_waddr !== r_g_lane_30_g_plain_u_lane_kv_waddr) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_kv_waddr !== p_g_lane_30_g_plain_u_lane_kv_waddr) nact = nact + 1; p_g_lane_30_g_plain_u_lane_kv_waddr <= r_g_lane_30_g_plain_u_lane_kv_waddr;
    if (d_g_lane_30_g_plain_u_lane_vm_waddr !== r_g_lane_30_g_plain_u_lane_vm_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_vm_waddr", cyc); end
    if (m_g_lane_30_g_plain_u_lane_vm_waddr !== r_g_lane_30_g_plain_u_lane_vm_waddr) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_vm_waddr !== p_g_lane_30_g_plain_u_lane_vm_waddr) nact = nact + 1; p_g_lane_30_g_plain_u_lane_vm_waddr <= r_g_lane_30_g_plain_u_lane_vm_waddr;
    if (d_g_lane_31_g_plain_u_lane_kv_waddr !== r_g_lane_31_g_plain_u_lane_kv_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_kv_waddr", cyc); end
    if (m_g_lane_31_g_plain_u_lane_kv_waddr !== r_g_lane_31_g_plain_u_lane_kv_waddr) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_kv_waddr !== p_g_lane_31_g_plain_u_lane_kv_waddr) nact = nact + 1; p_g_lane_31_g_plain_u_lane_kv_waddr <= r_g_lane_31_g_plain_u_lane_kv_waddr;
    if (d_g_lane_31_g_plain_u_lane_vm_waddr !== r_g_lane_31_g_plain_u_lane_vm_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_vm_waddr", cyc); end
    if (m_g_lane_31_g_plain_u_lane_vm_waddr !== r_g_lane_31_g_plain_u_lane_vm_waddr) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_vm_waddr !== p_g_lane_31_g_plain_u_lane_vm_waddr) nact = nact + 1; p_g_lane_31_g_plain_u_lane_vm_waddr <= r_g_lane_31_g_plain_u_lane_vm_waddr;
    if (d_g_lane_28_g_plain_u_lane_kv_wdata !== r_g_lane_28_g_plain_u_lane_kv_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_kv_wdata", cyc); end
    if (m_g_lane_28_g_plain_u_lane_kv_wdata !== r_g_lane_28_g_plain_u_lane_kv_wdata) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_kv_wdata !== p_g_lane_28_g_plain_u_lane_kv_wdata) nact = nact + 1; p_g_lane_28_g_plain_u_lane_kv_wdata <= r_g_lane_28_g_plain_u_lane_kv_wdata;
    if (d_g_lane_28_g_plain_u_lane_ro_x !== r_g_lane_28_g_plain_u_lane_ro_x) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_ro_x", cyc); end
    if (m_g_lane_28_g_plain_u_lane_ro_x !== r_g_lane_28_g_plain_u_lane_ro_x) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_ro_x !== p_g_lane_28_g_plain_u_lane_ro_x) nact = nact + 1; p_g_lane_28_g_plain_u_lane_ro_x <= r_g_lane_28_g_plain_u_lane_ro_x;
    if (d_g_lane_28_g_plain_u_lane_vm_wdata !== r_g_lane_28_g_plain_u_lane_vm_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_vm_wdata", cyc); end
    if (m_g_lane_28_g_plain_u_lane_vm_wdata !== r_g_lane_28_g_plain_u_lane_vm_wdata) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_vm_wdata !== p_g_lane_28_g_plain_u_lane_vm_wdata) nact = nact + 1; p_g_lane_28_g_plain_u_lane_vm_wdata <= r_g_lane_28_g_plain_u_lane_vm_wdata;
    if (d_g_lane_29_g_plain_u_lane_kv_wdata !== r_g_lane_29_g_plain_u_lane_kv_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_kv_wdata", cyc); end
    if (m_g_lane_29_g_plain_u_lane_kv_wdata !== r_g_lane_29_g_plain_u_lane_kv_wdata) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_kv_wdata !== p_g_lane_29_g_plain_u_lane_kv_wdata) nact = nact + 1; p_g_lane_29_g_plain_u_lane_kv_wdata <= r_g_lane_29_g_plain_u_lane_kv_wdata;
    if (d_g_lane_29_g_plain_u_lane_ro_x !== r_g_lane_29_g_plain_u_lane_ro_x) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_ro_x", cyc); end
    if (m_g_lane_29_g_plain_u_lane_ro_x !== r_g_lane_29_g_plain_u_lane_ro_x) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_ro_x !== p_g_lane_29_g_plain_u_lane_ro_x) nact = nact + 1; p_g_lane_29_g_plain_u_lane_ro_x <= r_g_lane_29_g_plain_u_lane_ro_x;
    if (d_g_lane_29_g_plain_u_lane_vm_wdata !== r_g_lane_29_g_plain_u_lane_vm_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_vm_wdata", cyc); end
    if (m_g_lane_29_g_plain_u_lane_vm_wdata !== r_g_lane_29_g_plain_u_lane_vm_wdata) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_vm_wdata !== p_g_lane_29_g_plain_u_lane_vm_wdata) nact = nact + 1; p_g_lane_29_g_plain_u_lane_vm_wdata <= r_g_lane_29_g_plain_u_lane_vm_wdata;
    if (d_g_lane_30_g_plain_u_lane_kv_wdata !== r_g_lane_30_g_plain_u_lane_kv_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_kv_wdata", cyc); end
    if (m_g_lane_30_g_plain_u_lane_kv_wdata !== r_g_lane_30_g_plain_u_lane_kv_wdata) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_kv_wdata !== p_g_lane_30_g_plain_u_lane_kv_wdata) nact = nact + 1; p_g_lane_30_g_plain_u_lane_kv_wdata <= r_g_lane_30_g_plain_u_lane_kv_wdata;
    if (d_g_lane_30_g_plain_u_lane_ro_x !== r_g_lane_30_g_plain_u_lane_ro_x) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_ro_x", cyc); end
    if (m_g_lane_30_g_plain_u_lane_ro_x !== r_g_lane_30_g_plain_u_lane_ro_x) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_ro_x !== p_g_lane_30_g_plain_u_lane_ro_x) nact = nact + 1; p_g_lane_30_g_plain_u_lane_ro_x <= r_g_lane_30_g_plain_u_lane_ro_x;
    if (d_g_lane_30_g_plain_u_lane_vm_wdata !== r_g_lane_30_g_plain_u_lane_vm_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_vm_wdata", cyc); end
    if (m_g_lane_30_g_plain_u_lane_vm_wdata !== r_g_lane_30_g_plain_u_lane_vm_wdata) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_vm_wdata !== p_g_lane_30_g_plain_u_lane_vm_wdata) nact = nact + 1; p_g_lane_30_g_plain_u_lane_vm_wdata <= r_g_lane_30_g_plain_u_lane_vm_wdata;
    if (d_g_lane_31_g_plain_u_lane_kv_wdata !== r_g_lane_31_g_plain_u_lane_kv_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_kv_wdata", cyc); end
    if (m_g_lane_31_g_plain_u_lane_kv_wdata !== r_g_lane_31_g_plain_u_lane_kv_wdata) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_kv_wdata !== p_g_lane_31_g_plain_u_lane_kv_wdata) nact = nact + 1; p_g_lane_31_g_plain_u_lane_kv_wdata <= r_g_lane_31_g_plain_u_lane_kv_wdata;
    if (d_g_lane_31_g_plain_u_lane_ro_x !== r_g_lane_31_g_plain_u_lane_ro_x) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_ro_x", cyc); end
    if (m_g_lane_31_g_plain_u_lane_ro_x !== r_g_lane_31_g_plain_u_lane_ro_x) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_ro_x !== p_g_lane_31_g_plain_u_lane_ro_x) nact = nact + 1; p_g_lane_31_g_plain_u_lane_ro_x <= r_g_lane_31_g_plain_u_lane_ro_x;
    if (d_g_lane_31_g_plain_u_lane_vm_wdata !== r_g_lane_31_g_plain_u_lane_vm_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_vm_wdata", cyc); end
    if (m_g_lane_31_g_plain_u_lane_vm_wdata !== r_g_lane_31_g_plain_u_lane_vm_wdata) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_vm_wdata !== p_g_lane_31_g_plain_u_lane_vm_wdata) nact = nact + 1; p_g_lane_31_g_plain_u_lane_vm_wdata <= r_g_lane_31_g_plain_u_lane_vm_wdata;
    if (d_g_lane_28_g_plain_u_lane_rd_addr !== r_g_lane_28_g_plain_u_lane_rd_addr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_28_g_plain_u_lane_rd_addr", cyc); end
    if (m_g_lane_28_g_plain_u_lane_rd_addr !== r_g_lane_28_g_plain_u_lane_rd_addr) nmut = nmut + 1;
    if (r_g_lane_28_g_plain_u_lane_rd_addr !== p_g_lane_28_g_plain_u_lane_rd_addr) nact = nact + 1; p_g_lane_28_g_plain_u_lane_rd_addr <= r_g_lane_28_g_plain_u_lane_rd_addr;
    if (d_g_lane_29_g_plain_u_lane_rd_addr !== r_g_lane_29_g_plain_u_lane_rd_addr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_29_g_plain_u_lane_rd_addr", cyc); end
    if (m_g_lane_29_g_plain_u_lane_rd_addr !== r_g_lane_29_g_plain_u_lane_rd_addr) nmut = nmut + 1;
    if (r_g_lane_29_g_plain_u_lane_rd_addr !== p_g_lane_29_g_plain_u_lane_rd_addr) nact = nact + 1; p_g_lane_29_g_plain_u_lane_rd_addr <= r_g_lane_29_g_plain_u_lane_rd_addr;
    if (d_g_lane_30_g_plain_u_lane_rd_addr !== r_g_lane_30_g_plain_u_lane_rd_addr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_30_g_plain_u_lane_rd_addr", cyc); end
    if (m_g_lane_30_g_plain_u_lane_rd_addr !== r_g_lane_30_g_plain_u_lane_rd_addr) nmut = nmut + 1;
    if (r_g_lane_30_g_plain_u_lane_rd_addr !== p_g_lane_30_g_plain_u_lane_rd_addr) nact = nact + 1; p_g_lane_30_g_plain_u_lane_rd_addr <= r_g_lane_30_g_plain_u_lane_rd_addr;
    if (d_g_lane_31_g_plain_u_lane_rd_addr !== r_g_lane_31_g_plain_u_lane_rd_addr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_31_g_plain_u_lane_rd_addr", cyc); end
    if (m_g_lane_31_g_plain_u_lane_rd_addr !== r_g_lane_31_g_plain_u_lane_rd_addr) nmut = nmut + 1;
    if (r_g_lane_31_g_plain_u_lane_rd_addr !== p_g_lane_31_g_plain_u_lane_rd_addr) nact = nact + 1; p_g_lane_31_g_plain_u_lane_rd_addr <= r_g_lane_31_g_plain_u_lane_rd_addr;
    if (d_g_bank_31_u_bank_read_data !== r_g_bank_31_u_bank_read_data) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_bank_31_u_bank_read_data", cyc); end
    if (m_g_bank_31_u_bank_read_data !== r_g_bank_31_u_bank_read_data) nmut = nmut + 1;
    if (r_g_bank_31_u_bank_read_data !== p_g_bank_31_u_bank_read_data) nact = nact + 1; p_g_bank_31_u_bank_read_data <= r_g_bank_31_u_bank_read_data;
    if (cyc == 3000) begin $display("RESULT master=ot_hbm_su_pg_lanes4_core_strap old=ot_hbm_su_static_pgslice_lg__lanes_plain12_15 straps={strap_lane0_lane_id: 11'b00001001100, strap_lane1_lane_id: 11'b00001001101, strap_lane2_lane_id: 11'b00001001110, strap_lane3_lane_id: 11'b00001001111} cycles=%0d dut_vs_ref_diffs=%0d mutant_diffs=%0d ref_output_changes=%0d %s", cyc, ndiff, nmut, nact, (ndiff == 0 && nmut > 0 && nact > 0) ? "PASS" : "FAIL"); $finish; end
  end
endmodule
