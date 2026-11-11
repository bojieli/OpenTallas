`default_nettype none
// BIND-SUBTYPE 11-11: bind-side copy of the d44v part-6 plan glue (results/die_hbm_1103/reform/split_p6/
// ot_hgi_sfu_split3_lane_core__idpin__p6glue.sv) under its own top name, so it never collides with the plan modules.
// Hierarchy u_fcore.u_core.u_{fr,ex,bk} = the plan physical_inst; sub-cores are the BARE plan masters
// (ot_hgi_sfu_split3_lane_core_{fr,ex,bk}, reform_1103), not the bench face-shell models __fs.  Wiring = the plan
// composition ot_hgi_sfu_split3_lane_core__idpin__split, except that sfu_vi_q carries all 32 bits to _fr (the native
// lane passes 32 b to ot_su12_sfu_sp2).  Wires only.  Declared cycle relation to the native lane: d44v part 6 (+4 on
// sfu_vm/kv/ro/fault/coll with kit face shells), priced in the plan of record.
module ot_hgi_sfu_split3_lane_core__idpin__bsub (
    input wire map_clk, input wire map_i_emit, input wire [23:0] map_i_i_v, input wire [23:0] map_i_krow,
    input wire [3:0] map_i_ls, input wire [3:0] map_i_lvw, input wire [23:0] map_i_o_v, input wire [460:0] map_i_pass,
    input wire [3:0] map_lane_j, input wire [479:0] map_ld_terms, input wire map_rst_n, input wire sfu_clk,
    output wire sfu_coll, output wire sfu_fault, output wire [23:0] sfu_kv_waddr, output wire [31:0] sfu_kv_wdata,
    output wire sfu_kv_we, output wire [95:0] sfu_rd_addr, input wire [127:0] sfu_rd_q, output wire [3:0] sfu_rd_re,
    output wire [7:0] sfu_rd_src, output wire sfu_ro_v, output wire [31:0] sfu_ro_x, input wire sfu_rst_n,
    output wire [23:0] sfu_vi_addr, input wire [31:0] sfu_vi_q, output wire sfu_vi_re, output wire [23:0] sfu_vm_waddr,
    output wire [31:0] sfu_vm_wdata, output wire sfu_vm_we);
    ot_hgi_sfu_split3_lane_core__idpin__bsub__fcore u_fcore (.map_clk(map_clk), .map_i_emit(map_i_emit), .map_i_i_v(map_i_i_v), .map_i_krow(map_i_krow), .map_i_ls(map_i_ls), .map_i_lvw(map_i_lvw), .map_i_o_v(map_i_o_v), .map_i_pass(map_i_pass), .map_lane_j(map_lane_j), .map_ld_terms(map_ld_terms), .map_rst_n(map_rst_n), .sfu_clk(sfu_clk), .sfu_coll(sfu_coll), .sfu_fault(sfu_fault), .sfu_kv_waddr(sfu_kv_waddr), .sfu_kv_wdata(sfu_kv_wdata), .sfu_kv_we(sfu_kv_we), .sfu_rd_addr(sfu_rd_addr), .sfu_rd_q(sfu_rd_q), .sfu_rd_re(sfu_rd_re), .sfu_rd_src(sfu_rd_src), .sfu_ro_v(sfu_ro_v), .sfu_ro_x(sfu_ro_x), .sfu_rst_n(sfu_rst_n), .sfu_vi_addr(sfu_vi_addr), .sfu_vi_q(sfu_vi_q), .sfu_vi_re(sfu_vi_re), .sfu_vm_waddr(sfu_vm_waddr), .sfu_vm_wdata(sfu_vm_wdata), .sfu_vm_we(sfu_vm_we));
endmodule

module ot_hgi_sfu_split3_lane_core__idpin__bsub__fcore (
    input wire map_clk, input wire map_i_emit, input wire [23:0] map_i_i_v, input wire [23:0] map_i_krow,
    input wire [3:0] map_i_ls, input wire [3:0] map_i_lvw, input wire [23:0] map_i_o_v, input wire [460:0] map_i_pass,
    input wire [3:0] map_lane_j, input wire [479:0] map_ld_terms, input wire map_rst_n, input wire sfu_clk,
    output wire sfu_coll, output wire sfu_fault, output wire [23:0] sfu_kv_waddr, output wire [31:0] sfu_kv_wdata,
    output wire sfu_kv_we, output wire [95:0] sfu_rd_addr, input wire [127:0] sfu_rd_q, output wire [3:0] sfu_rd_re,
    output wire [7:0] sfu_rd_src, output wire sfu_ro_v, output wire [31:0] sfu_ro_x, input wire sfu_rst_n,
    output wire [23:0] sfu_vi_addr, input wire [31:0] sfu_vi_q, output wire sfu_vi_re, output wire [23:0] sfu_vm_waddr,
    output wire [31:0] sfu_vm_wdata, output wire sfu_vm_we);
    ot_hgi_sfu_split3_lane_core__idpin__bsub__split u_core (.map_clk(map_clk), .map_i_emit(map_i_emit), .map_i_i_v(map_i_i_v), .map_i_krow(map_i_krow), .map_i_ls(map_i_ls), .map_i_lvw(map_i_lvw), .map_i_o_v(map_i_o_v), .map_i_pass(map_i_pass), .map_lane_j(map_lane_j), .map_ld_terms(map_ld_terms), .map_rst_n(map_rst_n), .sfu_clk(sfu_clk), .sfu_coll(sfu_coll), .sfu_fault(sfu_fault), .sfu_kv_waddr(sfu_kv_waddr), .sfu_kv_wdata(sfu_kv_wdata), .sfu_kv_we(sfu_kv_we), .sfu_rd_addr(sfu_rd_addr), .sfu_rd_q(sfu_rd_q), .sfu_rd_re(sfu_rd_re), .sfu_rd_src(sfu_rd_src), .sfu_ro_v(sfu_ro_v), .sfu_ro_x(sfu_ro_x), .sfu_rst_n(sfu_rst_n), .sfu_vi_addr(sfu_vi_addr), .sfu_vi_q(sfu_vi_q), .sfu_vi_re(sfu_vi_re), .sfu_vm_waddr(sfu_vm_waddr), .sfu_vm_wdata(sfu_vm_wdata), .sfu_vm_we(sfu_vm_we));
endmodule

module ot_hgi_sfu_split3_lane_core__idpin__bsub__split (
    input wire map_clk, input wire map_i_emit, input wire [23:0] map_i_i_v, input wire [23:0] map_i_krow,
    input wire [3:0] map_i_ls, input wire [3:0] map_i_lvw, input wire [23:0] map_i_o_v, input wire [460:0] map_i_pass,
    input wire [3:0] map_lane_j, input wire [479:0] map_ld_terms, input wire map_rst_n, input wire sfu_clk,
    output wire sfu_coll, output wire sfu_fault, output wire [23:0] sfu_kv_waddr, output wire [31:0] sfu_kv_wdata,
    output wire sfu_kv_we, output wire [95:0] sfu_rd_addr, input wire [127:0] sfu_rd_q, output wire [3:0] sfu_rd_re,
    output wire [7:0] sfu_rd_src, output wire sfu_ro_v, output wire [31:0] sfu_ro_x, input wire sfu_rst_n,
    output wire [23:0] sfu_vi_addr, input wire [31:0] sfu_vi_q, output wire sfu_vi_re, output wire [23:0] sfu_vm_waddr,
    output wire [31:0] sfu_vm_wdata, output wire sfu_vm_we);
    wire x_exp_v;
    wire [31:0] x_exp_x;
    wire [31:0] x_exp_y;
    wire x_exp_f;
    wire [200:0] x_bus;
    ot_hgi_sfu_split3_lane_core_fr u_fr (.map_clk(map_clk), .map_rst_n(map_rst_n), .map_ld_terms(map_ld_terms),
        .map_i_o_v(map_i_o_v), .map_i_i_v(map_i_i_v), .map_i_krow(map_i_krow), .map_i_ls(map_i_ls), .map_i_lvw(map_i_lvw),
        .map_i_emit(map_i_emit), .map_i_pass(map_i_pass), .sfu_clk(sfu_clk), .sfu_rst_n(sfu_rst_n),
        .sfu_vi_q(sfu_vi_q), .sfu_rd_q(sfu_rd_q), .map_lane_j(map_lane_j), .sfu_vi_re(sfu_vi_re),
        .sfu_vi_addr(sfu_vi_addr), .sfu_rd_addr(sfu_rd_addr), .sfu_rd_re(sfu_rd_re), .sfu_rd_src(sfu_rd_src),
        .x_exp_v(x_exp_v), .x_exp_x(x_exp_x), .x_bus(x_bus));
    ot_hgi_sfu_split3_lane_core_ex u_ex (.sfu_clk(sfu_clk), .sfu_rst_n(sfu_rst_n), .x_exp_v(x_exp_v), .x_exp_x(x_exp_x),
        .x_exp_y(x_exp_y), .x_exp_f(x_exp_f));
    ot_hgi_sfu_split3_lane_core_bk u_bk (.sfu_clk(sfu_clk), .sfu_rst_n(sfu_rst_n), .x_bus(x_bus),
        .x_exp_y(x_exp_y), .x_exp_f(x_exp_f), .sfu_vm_we(sfu_vm_we), .sfu_vm_waddr(sfu_vm_waddr),
        .sfu_vm_wdata(sfu_vm_wdata), .sfu_kv_we(sfu_kv_we), .sfu_kv_waddr(sfu_kv_waddr), .sfu_kv_wdata(sfu_kv_wdata),
        .sfu_ro_v(sfu_ro_v), .sfu_ro_x(sfu_ro_x), .sfu_fault(sfu_fault), .sfu_coll(sfu_coll));
endmodule
`default_nettype wire
