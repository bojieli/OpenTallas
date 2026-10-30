// DIE-HEAD-36: the generated local_status_depth=4 form of hd_st_str d_o (u_cland_loc_d_o_1 N=2 -> _2 -> _3 -> u_cland_up_d_o),
// stage text copied from src25q ot_s81hd_st_str.sv; reference = the src25p depth-1 form (u_cland_up_d_o N=2) delayed 3 cycles.
module tb_landing_status_relay(input wire clk, rst_n, input wire [1:0] ready_i, fault_i,
    output wire ready_o, fault_o, ready_ref, fault_ref);
    wire cland_loc_r_d_o_1, cland_loc_f_d_o_1, cland_loc_r_d_o_2, cland_loc_f_d_o_2, cland_loc_r_d_o_3, cland_loc_f_d_o_3;
    ot_dp_landing_collect #(.N(2)) u_cland_loc_d_o_1 (.clk(clk), .rst_n(rst_n), .ready_i(ready_i),
        .fault_i(fault_i), .ready_o(cland_loc_r_d_o_1), .fault_o(cland_loc_f_d_o_1));
    ot_dp_landing_collect #(.N(1)) u_cland_loc_d_o_2 (.clk(clk), .rst_n(rst_n), .ready_i({cland_loc_r_d_o_1}),
        .fault_i({cland_loc_f_d_o_1}), .ready_o(cland_loc_r_d_o_2), .fault_o(cland_loc_f_d_o_2));
    ot_dp_landing_collect #(.N(1)) u_cland_loc_d_o_3 (.clk(clk), .rst_n(rst_n), .ready_i({cland_loc_r_d_o_2}),
        .fault_i({cland_loc_f_d_o_2}), .ready_o(cland_loc_r_d_o_3), .fault_o(cland_loc_f_d_o_3));
    ot_dp_landing_collect #(.N(1)) u_cland_up_d_o (.clk(clk), .rst_n(rst_n), .ready_i({cland_loc_r_d_o_3}),
        .fault_i({cland_loc_f_d_o_3}), .ready_o(ready_o), .fault_o(fault_o));
    ot_dp_landing_collect #(.N(2)) u_ref (.clk(clk), .rst_n(rst_n), .ready_i(ready_i), .fault_i(fault_i),
        .ready_o(ready_ref), .fault_o(fault_ref));
endmodule
