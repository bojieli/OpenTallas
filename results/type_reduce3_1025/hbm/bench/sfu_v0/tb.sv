`timescale 1ns/1ps
module tb;
  reg clk = 0; reg rst_n = 0; integer cyc = 0; integer ndiff = 0; integer nmut = 0; integer nact = 0;
  always #1 clk = ~clk;
  reg [0:0] p_vi_re_w = 0;
  reg [23:0] p_vi_addr_w = 0;
  reg [0:0] p_kv_we_w = 0;
  reg [31:0] p_kv_wdata_w = 0;
  reg [23:0] p_kv_waddr_w = 0;
  reg [0:0] p_g_lane_0_u_sfu_vm_we = 0;
  reg [31:0] p_g_lane_0_u_sfu_vm_wdata = 0;
  reg [23:0] p_g_lane_0_u_sfu_vm_waddr = 0;
  reg [31:0] p_g_lane_0_u_sfu_ro_x = 0;
  reg [0:0] p_g_lane_0_u_sfu_ro_v = 0;
  reg [7:0] p_g_lane_0_u_sfu_rd_src = 0;
  reg [3:0] p_g_lane_0_u_sfu_rd_re = 0;
  reg [95:0] p_g_lane_0_u_sfu_rd_addr = 0;
  reg [0:0] p_g_lane_0_u_sfu_fault = 0;
  reg [0:0] p_g_lane_0_u_sfu_coll = 0;
  reg [0:0] i_g_lane_0_g_mono_u_map_i_emit = 0;
  reg [23:0] i_g_lane_0_g_mono_u_map_i_i_v = 0;
  reg [23:0] i_g_lane_0_g_mono_u_map_i_krow = 0;
  reg [3:0] i_g_lane_0_g_mono_u_map_i_ls = 0;
  reg [3:0] i_g_lane_0_g_mono_u_map_i_lvw = 0;
  reg [23:0] i_g_lane_0_g_mono_u_map_i_o_v = 0;
  reg [460:0] i_g_lane_0_g_mono_u_map_i_pass = 0;
  reg [479:0] i_g_lane_0_g_mono_u_map_ld_terms = 0;
  wire [0:0] r_g_lane_0_u_sfu_coll;
  wire [0:0] d_g_lane_0_u_sfu_coll;
  wire [0:0] m_g_lane_0_u_sfu_coll;
  wire [0:0] r_g_lane_0_u_sfu_fault;
  wire [0:0] d_g_lane_0_u_sfu_fault;
  wire [0:0] m_g_lane_0_u_sfu_fault;
  wire [95:0] r_g_lane_0_u_sfu_rd_addr;
  wire [95:0] d_g_lane_0_u_sfu_rd_addr;
  wire [95:0] m_g_lane_0_u_sfu_rd_addr;
  reg [127:0] i_g_lane_0_u_sfu_rd_q = 0;
  wire [3:0] r_g_lane_0_u_sfu_rd_re;
  wire [3:0] d_g_lane_0_u_sfu_rd_re;
  wire [3:0] m_g_lane_0_u_sfu_rd_re;
  wire [7:0] r_g_lane_0_u_sfu_rd_src;
  wire [7:0] d_g_lane_0_u_sfu_rd_src;
  wire [7:0] m_g_lane_0_u_sfu_rd_src;
  wire [0:0] r_g_lane_0_u_sfu_ro_v;
  wire [0:0] d_g_lane_0_u_sfu_ro_v;
  wire [0:0] m_g_lane_0_u_sfu_ro_v;
  wire [31:0] r_g_lane_0_u_sfu_ro_x;
  wire [31:0] d_g_lane_0_u_sfu_ro_x;
  wire [31:0] m_g_lane_0_u_sfu_ro_x;
  wire [23:0] r_g_lane_0_u_sfu_vm_waddr;
  wire [23:0] d_g_lane_0_u_sfu_vm_waddr;
  wire [23:0] m_g_lane_0_u_sfu_vm_waddr;
  wire [31:0] r_g_lane_0_u_sfu_vm_wdata;
  wire [31:0] d_g_lane_0_u_sfu_vm_wdata;
  wire [31:0] m_g_lane_0_u_sfu_vm_wdata;
  wire [0:0] r_g_lane_0_u_sfu_vm_we;
  wire [0:0] d_g_lane_0_u_sfu_vm_we;
  wire [0:0] m_g_lane_0_u_sfu_vm_we;
  wire [23:0] r_kv_waddr_w;
  wire [23:0] d_kv_waddr_w;
  wire [23:0] m_kv_waddr_w;
  wire [31:0] r_kv_wdata_w;
  wire [31:0] d_kv_wdata_w;
  wire [31:0] m_kv_wdata_w;
  wire [0:0] r_kv_we_w;
  wire [0:0] d_kv_we_w;
  wire [0:0] m_kv_we_w;
  wire [23:0] r_vi_addr_w;
  wire [23:0] d_vi_addr_w;
  wire [23:0] m_vi_addr_w;
  reg [31:0] i_vi_q_w = 0;
  wire [0:0] r_vi_re_w;
  wire [0:0] d_vi_re_w;
  wire [0:0] m_vi_re_w;
  ot_hgi_sfu_core_split3__lane0__fcore u_ref (.clk_lane(clk), .clk_map(clk), .g_lane_0_g_mono_u_map_i_emit(i_g_lane_0_g_mono_u_map_i_emit), .g_lane_0_g_mono_u_map_i_i_v(i_g_lane_0_g_mono_u_map_i_i_v), .g_lane_0_g_mono_u_map_i_krow(i_g_lane_0_g_mono_u_map_i_krow), .g_lane_0_g_mono_u_map_i_ls(i_g_lane_0_g_mono_u_map_i_ls), .g_lane_0_g_mono_u_map_i_lvw(i_g_lane_0_g_mono_u_map_i_lvw), .g_lane_0_g_mono_u_map_i_o_v(i_g_lane_0_g_mono_u_map_i_o_v), .g_lane_0_g_mono_u_map_i_pass(i_g_lane_0_g_mono_u_map_i_pass), .g_lane_0_g_mono_u_map_ld_terms(i_g_lane_0_g_mono_u_map_ld_terms), .g_lane_0_u_sfu_coll(r_g_lane_0_u_sfu_coll), .g_lane_0_u_sfu_fault(r_g_lane_0_u_sfu_fault), .g_lane_0_u_sfu_rd_addr(r_g_lane_0_u_sfu_rd_addr), .g_lane_0_u_sfu_rd_q(i_g_lane_0_u_sfu_rd_q), .g_lane_0_u_sfu_rd_re(r_g_lane_0_u_sfu_rd_re), .g_lane_0_u_sfu_rd_src(r_g_lane_0_u_sfu_rd_src), .g_lane_0_u_sfu_ro_v(r_g_lane_0_u_sfu_ro_v), .g_lane_0_u_sfu_ro_x(r_g_lane_0_u_sfu_ro_x), .g_lane_0_u_sfu_vm_waddr(r_g_lane_0_u_sfu_vm_waddr), .g_lane_0_u_sfu_vm_wdata(r_g_lane_0_u_sfu_vm_wdata), .g_lane_0_u_sfu_vm_we(r_g_lane_0_u_sfu_vm_we), .kv_waddr_w(r_kv_waddr_w), .kv_wdata_w(r_kv_wdata_w), .kv_we_w(r_kv_we_w), .rst_lane_n(rst_n), .rst_map_n(rst_n), .vi_addr_w(r_vi_addr_w), .vi_q_w(i_vi_q_w), .vi_re_w(r_vi_re_w));
  ot_hgi_sfu_split3_lane_core_strap u_dut (.sfu_clk(clk), .map_clk(clk), .map_i_emit(i_g_lane_0_g_mono_u_map_i_emit), .map_i_i_v(i_g_lane_0_g_mono_u_map_i_i_v), .map_i_krow(i_g_lane_0_g_mono_u_map_i_krow), .map_i_ls(i_g_lane_0_g_mono_u_map_i_ls), .map_i_lvw(i_g_lane_0_g_mono_u_map_i_lvw), .map_i_o_v(i_g_lane_0_g_mono_u_map_i_o_v), .map_i_pass(i_g_lane_0_g_mono_u_map_i_pass), .map_ld_terms(i_g_lane_0_g_mono_u_map_ld_terms), .sfu_coll(d_g_lane_0_u_sfu_coll), .sfu_fault(d_g_lane_0_u_sfu_fault), .sfu_rd_addr(d_g_lane_0_u_sfu_rd_addr), .sfu_rd_q(i_g_lane_0_u_sfu_rd_q), .sfu_rd_re(d_g_lane_0_u_sfu_rd_re), .sfu_rd_src(d_g_lane_0_u_sfu_rd_src), .sfu_ro_v(d_g_lane_0_u_sfu_ro_v), .sfu_ro_x(d_g_lane_0_u_sfu_ro_x), .sfu_vm_waddr(d_g_lane_0_u_sfu_vm_waddr), .sfu_vm_wdata(d_g_lane_0_u_sfu_vm_wdata), .sfu_vm_we(d_g_lane_0_u_sfu_vm_we), .sfu_kv_waddr(d_kv_waddr_w), .sfu_kv_wdata(d_kv_wdata_w), .sfu_kv_we(d_kv_we_w), .sfu_rst_n(rst_n), .map_rst_n(rst_n), .sfu_vi_addr(d_vi_addr_w), .sfu_vi_q(i_vi_q_w), .sfu_vi_re(d_vi_re_w), .strap_map_lane_j(4'b0000));
  ot_hgi_sfu_split3_lane_core_strap u_mut (.sfu_clk(clk), .map_clk(clk), .map_i_emit(i_g_lane_0_g_mono_u_map_i_emit), .map_i_i_v(i_g_lane_0_g_mono_u_map_i_i_v), .map_i_krow(i_g_lane_0_g_mono_u_map_i_krow), .map_i_ls(i_g_lane_0_g_mono_u_map_i_ls), .map_i_lvw(i_g_lane_0_g_mono_u_map_i_lvw), .map_i_o_v(i_g_lane_0_g_mono_u_map_i_o_v), .map_i_pass(i_g_lane_0_g_mono_u_map_i_pass), .map_ld_terms(i_g_lane_0_g_mono_u_map_ld_terms), .sfu_coll(m_g_lane_0_u_sfu_coll), .sfu_fault(m_g_lane_0_u_sfu_fault), .sfu_rd_addr(m_g_lane_0_u_sfu_rd_addr), .sfu_rd_q(i_g_lane_0_u_sfu_rd_q), .sfu_rd_re(m_g_lane_0_u_sfu_rd_re), .sfu_rd_src(m_g_lane_0_u_sfu_rd_src), .sfu_ro_v(m_g_lane_0_u_sfu_ro_v), .sfu_ro_x(m_g_lane_0_u_sfu_ro_x), .sfu_vm_waddr(m_g_lane_0_u_sfu_vm_waddr), .sfu_vm_wdata(m_g_lane_0_u_sfu_vm_wdata), .sfu_vm_we(m_g_lane_0_u_sfu_vm_we), .sfu_kv_waddr(m_kv_waddr_w), .sfu_kv_wdata(m_kv_wdata_w), .sfu_kv_we(m_kv_we_w), .sfu_rst_n(rst_n), .map_rst_n(rst_n), .sfu_vi_addr(m_vi_addr_w), .sfu_vi_q(i_vi_q_w), .sfu_vi_re(m_vi_re_w), .strap_map_lane_j(4'b0001));
  always @(negedge clk) begin
    i_g_lane_0_g_mono_u_map_i_emit <= {$urandom};
    i_g_lane_0_g_mono_u_map_i_i_v <= {$urandom};
    i_g_lane_0_g_mono_u_map_i_krow <= {$urandom};
    i_g_lane_0_g_mono_u_map_i_ls <= {$urandom};
    i_g_lane_0_g_mono_u_map_i_lvw <= {$urandom};
    i_g_lane_0_g_mono_u_map_i_o_v <= {$urandom};
    i_g_lane_0_g_mono_u_map_i_pass <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
    i_g_lane_0_g_mono_u_map_ld_terms <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
    i_g_lane_0_u_sfu_rd_q <= {$urandom, $urandom, $urandom, $urandom};
    i_vi_q_w <= {$urandom};
  end
  always @(posedge clk) begin
    cyc <= cyc + 1; if (cyc == 8) rst_n <= 1;
    if (d_g_lane_0_u_sfu_coll !== r_g_lane_0_u_sfu_coll) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_coll", cyc); end
    if (m_g_lane_0_u_sfu_coll !== r_g_lane_0_u_sfu_coll) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_coll !== p_g_lane_0_u_sfu_coll) nact = nact + 1; p_g_lane_0_u_sfu_coll <= r_g_lane_0_u_sfu_coll;
    if (d_g_lane_0_u_sfu_fault !== r_g_lane_0_u_sfu_fault) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_fault", cyc); end
    if (m_g_lane_0_u_sfu_fault !== r_g_lane_0_u_sfu_fault) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_fault !== p_g_lane_0_u_sfu_fault) nact = nact + 1; p_g_lane_0_u_sfu_fault <= r_g_lane_0_u_sfu_fault;
    if (d_g_lane_0_u_sfu_rd_addr !== r_g_lane_0_u_sfu_rd_addr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_rd_addr", cyc); end
    if (m_g_lane_0_u_sfu_rd_addr !== r_g_lane_0_u_sfu_rd_addr) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_rd_addr !== p_g_lane_0_u_sfu_rd_addr) nact = nact + 1; p_g_lane_0_u_sfu_rd_addr <= r_g_lane_0_u_sfu_rd_addr;
    if (d_g_lane_0_u_sfu_rd_re !== r_g_lane_0_u_sfu_rd_re) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_rd_re", cyc); end
    if (m_g_lane_0_u_sfu_rd_re !== r_g_lane_0_u_sfu_rd_re) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_rd_re !== p_g_lane_0_u_sfu_rd_re) nact = nact + 1; p_g_lane_0_u_sfu_rd_re <= r_g_lane_0_u_sfu_rd_re;
    if (d_g_lane_0_u_sfu_rd_src !== r_g_lane_0_u_sfu_rd_src) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_rd_src", cyc); end
    if (m_g_lane_0_u_sfu_rd_src !== r_g_lane_0_u_sfu_rd_src) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_rd_src !== p_g_lane_0_u_sfu_rd_src) nact = nact + 1; p_g_lane_0_u_sfu_rd_src <= r_g_lane_0_u_sfu_rd_src;
    if (d_g_lane_0_u_sfu_ro_v !== r_g_lane_0_u_sfu_ro_v) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_ro_v", cyc); end
    if (m_g_lane_0_u_sfu_ro_v !== r_g_lane_0_u_sfu_ro_v) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_ro_v !== p_g_lane_0_u_sfu_ro_v) nact = nact + 1; p_g_lane_0_u_sfu_ro_v <= r_g_lane_0_u_sfu_ro_v;
    if (d_g_lane_0_u_sfu_ro_x !== r_g_lane_0_u_sfu_ro_x) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_ro_x", cyc); end
    if (m_g_lane_0_u_sfu_ro_x !== r_g_lane_0_u_sfu_ro_x) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_ro_x !== p_g_lane_0_u_sfu_ro_x) nact = nact + 1; p_g_lane_0_u_sfu_ro_x <= r_g_lane_0_u_sfu_ro_x;
    if (d_g_lane_0_u_sfu_vm_waddr !== r_g_lane_0_u_sfu_vm_waddr) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_vm_waddr", cyc); end
    if (m_g_lane_0_u_sfu_vm_waddr !== r_g_lane_0_u_sfu_vm_waddr) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_vm_waddr !== p_g_lane_0_u_sfu_vm_waddr) nact = nact + 1; p_g_lane_0_u_sfu_vm_waddr <= r_g_lane_0_u_sfu_vm_waddr;
    if (d_g_lane_0_u_sfu_vm_wdata !== r_g_lane_0_u_sfu_vm_wdata) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_vm_wdata", cyc); end
    if (m_g_lane_0_u_sfu_vm_wdata !== r_g_lane_0_u_sfu_vm_wdata) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_vm_wdata !== p_g_lane_0_u_sfu_vm_wdata) nact = nact + 1; p_g_lane_0_u_sfu_vm_wdata <= r_g_lane_0_u_sfu_vm_wdata;
    if (d_g_lane_0_u_sfu_vm_we !== r_g_lane_0_u_sfu_vm_we) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d g_lane_0_u_sfu_vm_we", cyc); end
    if (m_g_lane_0_u_sfu_vm_we !== r_g_lane_0_u_sfu_vm_we) nmut = nmut + 1;
    if (r_g_lane_0_u_sfu_vm_we !== p_g_lane_0_u_sfu_vm_we) nact = nact + 1; p_g_lane_0_u_sfu_vm_we <= r_g_lane_0_u_sfu_vm_we;
    if (d_kv_waddr_w !== r_kv_waddr_w) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d kv_waddr_w", cyc); end
    if (m_kv_waddr_w !== r_kv_waddr_w) nmut = nmut + 1;
    if (r_kv_waddr_w !== p_kv_waddr_w) nact = nact + 1; p_kv_waddr_w <= r_kv_waddr_w;
    if (d_kv_wdata_w !== r_kv_wdata_w) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d kv_wdata_w", cyc); end
    if (m_kv_wdata_w !== r_kv_wdata_w) nmut = nmut + 1;
    if (r_kv_wdata_w !== p_kv_wdata_w) nact = nact + 1; p_kv_wdata_w <= r_kv_wdata_w;
    if (d_kv_we_w !== r_kv_we_w) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d kv_we_w", cyc); end
    if (m_kv_we_w !== r_kv_we_w) nmut = nmut + 1;
    if (r_kv_we_w !== p_kv_we_w) nact = nact + 1; p_kv_we_w <= r_kv_we_w;
    if (d_vi_addr_w !== r_vi_addr_w) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d vi_addr_w", cyc); end
    if (m_vi_addr_w !== r_vi_addr_w) nmut = nmut + 1;
    if (r_vi_addr_w !== p_vi_addr_w) nact = nact + 1; p_vi_addr_w <= r_vi_addr_w;
    if (d_vi_re_w !== r_vi_re_w) begin ndiff = ndiff + 1; if (ndiff < 5) $display("DIFF cyc %0d vi_re_w", cyc); end
    if (m_vi_re_w !== r_vi_re_w) nmut = nmut + 1;
    if (r_vi_re_w !== p_vi_re_w) nact = nact + 1; p_vi_re_w <= r_vi_re_w;
    if (cyc == 3000) begin $display("RESULT master=ot_hgi_sfu_split3_lane_core_strap old=ot_hgi_sfu_core_split3__lane0 straps={strap_map_lane_j: 4'b0000} cycles=%0d dut_vs_ref_diffs=%0d mutant_diffs=%0d ref_output_changes=%0d %s", cyc, ndiff, nmut, nact, (ndiff == 0 && nmut > 0 && nact > 0) ? "PASS" : "FAIL"); $finish; end
  end
endmodule
