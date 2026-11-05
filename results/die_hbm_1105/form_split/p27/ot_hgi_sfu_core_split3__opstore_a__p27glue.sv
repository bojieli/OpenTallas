// DIE-HBM-61/SPLIT d44v part 6 (u_core -> ot_hgi_sfu_opsa__comp); from gen_core_kit_hbm.py (ELEM-HBM): pass-through wrapper, plan pins -> RTL top; wires only.
`default_nettype none
module ot_hgi_sfu_core_split3__opstore_a__fcore (
    input wire clk,
    input wire [2047:0] g_operand_0_u_group_sw_d,
    input wire [63:0] g_operand_0_u_group_sw_mask,
    input wire [3:0] glue,
    output wire glue_1,
    input wire [1535:0] x_u_core_u_engine_u_arithmetic_rd_addr,
    output wire [2047:0] x_u_core_u_engine_u_arithmetic_rd_q,
    input wire [63:0] x_u_core_u_engine_u_arithmetic_rd_re,
    input wire [127:0] x_u_core_u_engine_u_arithmetic_rd_src,
    input wire x_u_core_u_engine_u_arithmetic_rst_control_n,
    input wire [143:0] x_u_core_u_engine_u_arithmetic_vm_waddr,
    input wire [15:0] x_u_core_u_engine_u_arithmetic_vm_we,
    input wire x_u_core_u_engine_u_memory_g_operand_2_u_group_flt,
    input wire [511:0] x_u_core_u_engine_u_memory_g_operand_2_u_group_rd,
    output wire [15:0] x_u_core_u_engine_u_memory_g_operand_2_u_group_rq,
    input wire [119:0] x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr,
    output wire [7:0] x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_v,
    input wire x_u_core_u_engine_u_memory_g_operand_3_u_group_flt,
    input wire [511:0] x_u_core_u_engine_u_memory_g_operand_3_u_group_rd,
    output wire [15:0] x_u_core_u_engine_u_memory_g_operand_3_u_group_rq,
    output wire [7:0] x_u_core_u_engine_u_memory_g_operand_3_u_group_sw_v,
    input wire x_u_core_u_engine_u_memory_u_output_flt,
    input wire [29:0] x_u_core_u_engine_u_memory_u_output_sr_addr,
    input wire [1:0] x_u_core_u_engine_u_memory_u_output_sr_v,
    input wire [127:0] x_u_core_u_vm_scalar_data,
    input wire [3:0] x_u_core_u_vm_scalar_load,
    input wire [95:0] x_u_core_u_vm_scalar_load_addr,
    input wire [15:0] x_u_core_u_vm_stage_group,
    input wire [7:0] x_u_core_u_vm_stage_v
);
    wire [35:0] __s_u_core_io_r;
    assign __s_u_core_io_r[3:0] = glue[3:0];
    assign __s_u_core_io_r[5:4] = x_u_core_u_engine_u_memory_u_output_sr_v[1:0];
    assign __s_u_core_io_r[35:6] = x_u_core_u_engine_u_memory_u_output_sr_addr[29:0];
    wire [2:0] __s_u_core_u_engine_u_memory_group_fault;
    assign __s_u_core_u_engine_u_memory_group_fault[0] = x_u_core_u_engine_u_memory_g_operand_2_u_group_flt;
    assign __s_u_core_u_engine_u_memory_group_fault[1] = x_u_core_u_engine_u_memory_g_operand_3_u_group_flt;
    assign __s_u_core_u_engine_u_memory_group_fault[2] = x_u_core_u_engine_u_memory_u_output_flt;
    wire [33:0] __s_u_core_u_vm_g_lg_0_meta_78;
    assign __s_u_core_u_vm_g_lg_0_meta_78[29:0] = x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr[29:0];
    assign __s_u_core_u_vm_g_lg_0_meta_78[33:30] = x_u_core_u_vm_stage_group[3:0];
    wire [33:0] __s_u_core_u_vm_g_lg_1_meta_78;
    assign __s_u_core_u_vm_g_lg_1_meta_78[29:0] = x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr[59:30];
    assign __s_u_core_u_vm_g_lg_1_meta_78[33:30] = x_u_core_u_vm_stage_group[7:4];
    wire [33:0] __s_u_core_u_vm_g_lg_2_meta_78;
    assign __s_u_core_u_vm_g_lg_2_meta_78[29:0] = x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr[89:60];
    assign __s_u_core_u_vm_g_lg_2_meta_78[33:30] = x_u_core_u_vm_stage_group[11:8];
    wire [33:0] __s_u_core_u_vm_g_lg_3_meta_78;
    assign __s_u_core_u_vm_g_lg_3_meta_78[29:0] = x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr[119:90];
    assign __s_u_core_u_vm_g_lg_3_meta_78[33:30] = x_u_core_u_vm_stage_group[15:12];
    ot_hgi_sfu_opsa__comp u_core (
        .clk(clk),
        .u_core_b_rr(g_operand_0_u_group_sw_d),
        .stage_mask(g_operand_0_u_group_sw_mask),
        .u_core_u_engine_u_memory_fault(glue_1),
        .u_core_u_engine_u_arithmetic_u_grid_rd_addr(x_u_core_u_engine_u_arithmetic_rd_addr),
        .u_core_u_engine_u_arithmetic_u_grid_rd_q(x_u_core_u_engine_u_arithmetic_rd_q),
        .u_core_u_engine_u_arithmetic_u_grid_rd_re(x_u_core_u_engine_u_arithmetic_rd_re),
        .u_core_u_engine_u_arithmetic_u_grid_rd_src(x_u_core_u_engine_u_arithmetic_rd_src),
        .u_core_u_rst_relay_q_0(x_u_core_u_engine_u_arithmetic_rst_control_n),
        .u_core_u_engine_u_arithmetic_u_grid_vm_waddr(x_u_core_u_engine_u_arithmetic_vm_waddr),
        .u_core_u_engine_u_arithmetic_u_grid_vm_we(x_u_core_u_engine_u_arithmetic_vm_we),
        .u_core_u_engine_u_memory_g_operand_2_data(x_u_core_u_engine_u_memory_g_operand_2_u_group_rd),
        .u_core_u_engine_u_memory_g_operand_2_req(x_u_core_u_engine_u_memory_g_operand_2_u_group_rq),
        .u_core_u_engine_u_memory_g_operand_2_sw(x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_v),
        .u_core_u_engine_u_memory_g_operand_3_data(x_u_core_u_engine_u_memory_g_operand_3_u_group_rd),
        .u_core_u_engine_u_memory_g_operand_3_req(x_u_core_u_engine_u_memory_g_operand_3_u_group_rq),
        .u_core_u_engine_u_memory_g_operand_3_sw(x_u_core_u_engine_u_memory_g_operand_3_u_group_sw_v),
        .u_core_u_engine_u_memory_scalar_data(x_u_core_u_vm_scalar_data),
        .u_core_u_engine_u_memory_scalar_load(x_u_core_u_vm_scalar_load),
        .u_core_u_vm_scalar_addr_pipe_78(x_u_core_u_vm_scalar_load_addr),
        .u_core_u_engine_u_memory_stage_v(x_u_core_u_vm_stage_v),
        .u_core_io_r(__s_u_core_io_r),
        .u_core_u_engine_u_memory_group_fault(__s_u_core_u_engine_u_memory_group_fault),
        .u_core_u_vm_g_lg_0_meta_78(__s_u_core_u_vm_g_lg_0_meta_78),
        .u_core_u_vm_g_lg_1_meta_78(__s_u_core_u_vm_g_lg_1_meta_78),
        .u_core_u_vm_g_lg_2_meta_78(__s_u_core_u_vm_g_lg_2_meta_78),
        .u_core_u_vm_g_lg_3_meta_78(__s_u_core_u_vm_g_lg_3_meta_78));
endmodule
`default_nettype wire

// DIE-HBM-61/SPLIT d44v part 6: plan module ot_hgi_sfu_core_split3__opstore_a = thin parent glue of the split hard core (wires only; the
// sub-cores of ot_hgi_sfu_opsa__comp are the hard cores, each with its own kit face shell).  Ports open in the composition: none.
`default_nettype none
module ot_hgi_sfu_core_split3__opstore_a (
    input wire clk,
    input wire [2047:0] g_operand_0_u_group_sw_d,
    input wire [63:0] g_operand_0_u_group_sw_mask,
    input wire [3:0] glue,
    output wire glue_1,
    input wire [1535:0] x_u_core_u_engine_u_arithmetic_rd_addr,
    output wire [2047:0] x_u_core_u_engine_u_arithmetic_rd_q,
    input wire [63:0] x_u_core_u_engine_u_arithmetic_rd_re,
    input wire [127:0] x_u_core_u_engine_u_arithmetic_rd_src,
    input wire x_u_core_u_engine_u_arithmetic_rst_control_n,
    input wire [143:0] x_u_core_u_engine_u_arithmetic_vm_waddr,
    input wire [15:0] x_u_core_u_engine_u_arithmetic_vm_we,
    input wire x_u_core_u_engine_u_memory_g_operand_2_u_group_flt,
    input wire [511:0] x_u_core_u_engine_u_memory_g_operand_2_u_group_rd,
    output wire [15:0] x_u_core_u_engine_u_memory_g_operand_2_u_group_rq,
    input wire [119:0] x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr,
    output wire [7:0] x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_v,
    input wire x_u_core_u_engine_u_memory_g_operand_3_u_group_flt,
    input wire [511:0] x_u_core_u_engine_u_memory_g_operand_3_u_group_rd,
    output wire [15:0] x_u_core_u_engine_u_memory_g_operand_3_u_group_rq,
    output wire [7:0] x_u_core_u_engine_u_memory_g_operand_3_u_group_sw_v,
    input wire x_u_core_u_engine_u_memory_u_output_flt,
    input wire [29:0] x_u_core_u_engine_u_memory_u_output_sr_addr,
    input wire [1:0] x_u_core_u_engine_u_memory_u_output_sr_v,
    input wire [127:0] x_u_core_u_vm_scalar_data,
    input wire [3:0] x_u_core_u_vm_scalar_load,
    input wire [95:0] x_u_core_u_vm_scalar_load_addr,
    input wire [15:0] x_u_core_u_vm_stage_group,
    input wire [7:0] x_u_core_u_vm_stage_v
);
    ot_hgi_sfu_core_split3__opstore_a__fcore u_fcore (.clk(clk), .g_operand_0_u_group_sw_d(g_operand_0_u_group_sw_d), .g_operand_0_u_group_sw_mask(g_operand_0_u_group_sw_mask), .glue(glue), .glue_1(glue_1), .x_u_core_u_engine_u_arithmetic_rd_addr(x_u_core_u_engine_u_arithmetic_rd_addr), .x_u_core_u_engine_u_arithmetic_rd_q(x_u_core_u_engine_u_arithmetic_rd_q), .x_u_core_u_engine_u_arithmetic_rd_re(x_u_core_u_engine_u_arithmetic_rd_re), .x_u_core_u_engine_u_arithmetic_rd_src(x_u_core_u_engine_u_arithmetic_rd_src), .x_u_core_u_engine_u_arithmetic_rst_control_n(x_u_core_u_engine_u_arithmetic_rst_control_n), .x_u_core_u_engine_u_arithmetic_vm_waddr(x_u_core_u_engine_u_arithmetic_vm_waddr), .x_u_core_u_engine_u_arithmetic_vm_we(x_u_core_u_engine_u_arithmetic_vm_we), .x_u_core_u_engine_u_memory_g_operand_2_u_group_flt(x_u_core_u_engine_u_memory_g_operand_2_u_group_flt), .x_u_core_u_engine_u_memory_g_operand_2_u_group_rd(x_u_core_u_engine_u_memory_g_operand_2_u_group_rd), .x_u_core_u_engine_u_memory_g_operand_2_u_group_rq(x_u_core_u_engine_u_memory_g_operand_2_u_group_rq), .x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr(x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr), .x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_v(x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_v), .x_u_core_u_engine_u_memory_g_operand_3_u_group_flt(x_u_core_u_engine_u_memory_g_operand_3_u_group_flt), .x_u_core_u_engine_u_memory_g_operand_3_u_group_rd(x_u_core_u_engine_u_memory_g_operand_3_u_group_rd), .x_u_core_u_engine_u_memory_g_operand_3_u_group_rq(x_u_core_u_engine_u_memory_g_operand_3_u_group_rq), .x_u_core_u_engine_u_memory_g_operand_3_u_group_sw_v(x_u_core_u_engine_u_memory_g_operand_3_u_group_sw_v), .x_u_core_u_engine_u_memory_u_output_flt(x_u_core_u_engine_u_memory_u_output_flt), .x_u_core_u_engine_u_memory_u_output_sr_addr(x_u_core_u_engine_u_memory_u_output_sr_addr), .x_u_core_u_engine_u_memory_u_output_sr_v(x_u_core_u_engine_u_memory_u_output_sr_v), .x_u_core_u_vm_scalar_data(x_u_core_u_vm_scalar_data), .x_u_core_u_vm_scalar_load(x_u_core_u_vm_scalar_load), .x_u_core_u_vm_scalar_load_addr(x_u_core_u_vm_scalar_load_addr), .x_u_core_u_vm_stage_group(x_u_core_u_vm_stage_group), .x_u_core_u_vm_stage_v(x_u_core_u_vm_stage_v));
endmodule
`default_nettype wire
