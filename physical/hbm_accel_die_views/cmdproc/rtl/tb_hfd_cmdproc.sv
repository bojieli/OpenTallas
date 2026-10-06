`timescale 1ns/1ps
// lockstep bench of hfd_cmdproc (tools/hbm_die_wrap.py --tb): one seed 20261006
module tb_hfd_cmdproc;
    wire [826:0] cNE;
    reg [826:0] drv_cNE;
    wire [826:0] cNW;
    reg [826:0] drv_cNW;
    wire [826:0] cSE;
    reg [826:0] drv_cSE;
    wire [826:0] cSW;
    reg [826:0] drv_cSW;
    reg [0:0] ck;
    reg [63:0] f_barrier;
    reg [32:0] f_coll;
    reg [340:0] f_loader;
    reg [63:0] f_router;
    reg [0:0] rst;
    wire [63:0] t_barrier;
    wire [24:0] t_coll;
    wire [63:0] t_su_NE;
    wire [63:0] t_su_NW;
    wire [63:0] t_su_SE;
    wire [63:0] t_su_SW;
    hfd_cmdproc dut(.cNE(cNE), .cNW(cNW), .cSE(cSE), .cSW(cSW), .ck(ck), .f_barrier(f_barrier), .f_coll(f_coll), .f_loader(f_loader), .f_router(f_router), .rst(rst), .t_barrier(t_barrier), .t_coll(t_coll), .t_su_NE(t_su_NE), .t_su_NW(t_su_NW), .t_su_SE(t_su_SE), .t_su_SW(t_su_SW));
    assign cSW[42] = drv_cSW[42];
    assign cSW[43] = drv_cSW[43];
    assign cSW[44] = drv_cSW[44];
    assign cSW[102] = drv_cSW[102];
    assign cSW[145] = drv_cSW[145];
    assign cSW[146] = drv_cSW[146];
    assign cSW[147] = drv_cSW[147];
    assign cSW[205] = drv_cSW[205];
    assign cSW[248] = drv_cSW[248];
    assign cSW[249] = drv_cSW[249];
    assign cSW[250] = drv_cSW[250];
    assign cSW[308] = drv_cSW[308];
    assign cSW[351] = drv_cSW[351];
    assign cSW[352] = drv_cSW[352];
    assign cSW[353] = drv_cSW[353];
    assign cSW[411] = drv_cSW[411];
    assign cSW[454] = drv_cSW[454];
    assign cSW[455] = drv_cSW[455];
    assign cSW[456] = drv_cSW[456];
    assign cSW[514] = drv_cSW[514];
    assign cSW[557] = drv_cSW[557];
    assign cSW[558] = drv_cSW[558];
    assign cSW[559] = drv_cSW[559];
    assign cSW[617] = drv_cSW[617];
    assign cSW[660] = drv_cSW[660];
    assign cSW[661] = drv_cSW[661];
    assign cSW[662] = drv_cSW[662];
    assign cSW[720] = drv_cSW[720];
    assign cSW[763] = drv_cSW[763];
    assign cSW[764] = drv_cSW[764];
    assign cSW[765] = drv_cSW[765];
    assign cSW[823] = drv_cSW[823];
    assign cSW[826] = drv_cSW[826];
    assign cNW[42] = drv_cNW[42];
    assign cNW[43] = drv_cNW[43];
    assign cNW[44] = drv_cNW[44];
    assign cNW[102] = drv_cNW[102];
    assign cNW[145] = drv_cNW[145];
    assign cNW[146] = drv_cNW[146];
    assign cNW[147] = drv_cNW[147];
    assign cNW[205] = drv_cNW[205];
    assign cNW[248] = drv_cNW[248];
    assign cNW[249] = drv_cNW[249];
    assign cNW[250] = drv_cNW[250];
    assign cNW[308] = drv_cNW[308];
    assign cNW[351] = drv_cNW[351];
    assign cNW[352] = drv_cNW[352];
    assign cNW[353] = drv_cNW[353];
    assign cNW[411] = drv_cNW[411];
    assign cNW[454] = drv_cNW[454];
    assign cNW[455] = drv_cNW[455];
    assign cNW[456] = drv_cNW[456];
    assign cNW[514] = drv_cNW[514];
    assign cNW[557] = drv_cNW[557];
    assign cNW[558] = drv_cNW[558];
    assign cNW[559] = drv_cNW[559];
    assign cNW[617] = drv_cNW[617];
    assign cNW[660] = drv_cNW[660];
    assign cNW[661] = drv_cNW[661];
    assign cNW[662] = drv_cNW[662];
    assign cNW[720] = drv_cNW[720];
    assign cNW[763] = drv_cNW[763];
    assign cNW[764] = drv_cNW[764];
    assign cNW[765] = drv_cNW[765];
    assign cNW[823] = drv_cNW[823];
    assign cNW[826] = drv_cNW[826];
    assign cSE[42] = drv_cSE[42];
    assign cSE[43] = drv_cSE[43];
    assign cSE[44] = drv_cSE[44];
    assign cSE[102] = drv_cSE[102];
    assign cSE[145] = drv_cSE[145];
    assign cSE[146] = drv_cSE[146];
    assign cSE[147] = drv_cSE[147];
    assign cSE[205] = drv_cSE[205];
    assign cSE[248] = drv_cSE[248];
    assign cSE[249] = drv_cSE[249];
    assign cSE[250] = drv_cSE[250];
    assign cSE[308] = drv_cSE[308];
    assign cSE[351] = drv_cSE[351];
    assign cSE[352] = drv_cSE[352];
    assign cSE[353] = drv_cSE[353];
    assign cSE[411] = drv_cSE[411];
    assign cSE[454] = drv_cSE[454];
    assign cSE[455] = drv_cSE[455];
    assign cSE[456] = drv_cSE[456];
    assign cSE[514] = drv_cSE[514];
    assign cSE[557] = drv_cSE[557];
    assign cSE[558] = drv_cSE[558];
    assign cSE[559] = drv_cSE[559];
    assign cSE[617] = drv_cSE[617];
    assign cSE[660] = drv_cSE[660];
    assign cSE[661] = drv_cSE[661];
    assign cSE[662] = drv_cSE[662];
    assign cSE[720] = drv_cSE[720];
    assign cSE[763] = drv_cSE[763];
    assign cSE[764] = drv_cSE[764];
    assign cSE[765] = drv_cSE[765];
    assign cSE[823] = drv_cSE[823];
    assign cSE[826] = drv_cSE[826];
    assign cNE[42] = drv_cNE[42];
    assign cNE[43] = drv_cNE[43];
    assign cNE[44] = drv_cNE[44];
    assign cNE[102] = drv_cNE[102];
    assign cNE[145] = drv_cNE[145];
    assign cNE[146] = drv_cNE[146];
    assign cNE[147] = drv_cNE[147];
    assign cNE[205] = drv_cNE[205];
    assign cNE[248] = drv_cNE[248];
    assign cNE[249] = drv_cNE[249];
    assign cNE[250] = drv_cNE[250];
    assign cNE[308] = drv_cNE[308];
    assign cNE[351] = drv_cNE[351];
    assign cNE[352] = drv_cNE[352];
    assign cNE[353] = drv_cNE[353];
    assign cNE[411] = drv_cNE[411];
    assign cNE[454] = drv_cNE[454];
    assign cNE[455] = drv_cNE[455];
    assign cNE[456] = drv_cNE[456];
    assign cNE[514] = drv_cNE[514];
    assign cNE[557] = drv_cNE[557];
    assign cNE[558] = drv_cNE[558];
    assign cNE[559] = drv_cNE[559];
    assign cNE[617] = drv_cNE[617];
    assign cNE[660] = drv_cNE[660];
    assign cNE[661] = drv_cNE[661];
    assign cNE[662] = drv_cNE[662];
    assign cNE[720] = drv_cNE[720];
    assign cNE[763] = drv_cNE[763];
    assign cNE[764] = drv_cNE[764];
    assign cNE[765] = drv_cNE[765];
    assign cNE[823] = drv_cNE[823];
    assign cNE[826] = drv_cNE[826];
    reg clk = 0; always #0.4165 clk = ~clk;
    always @* ck[0] = clk;
    reg [826:0] d0_cNE; always @(posedge clk) d0_cNE <= drv_cNE;
    reg [826:0] d1_cNE; always @(posedge clk) d1_cNE <= d0_cNE;
    reg [826:0] d2_cNE; always @(posedge clk) d2_cNE <= d1_cNE;
    reg [826:0] d3_cNE; always @(posedge clk) d3_cNE <= d2_cNE;
    reg [826:0] d_cNE; always @(posedge clk) d_cNE <= d3_cNE;
    reg [826:0] d0_cNW; always @(posedge clk) d0_cNW <= drv_cNW;
    reg [826:0] d1_cNW; always @(posedge clk) d1_cNW <= d0_cNW;
    reg [826:0] d2_cNW; always @(posedge clk) d2_cNW <= d1_cNW;
    reg [826:0] d3_cNW; always @(posedge clk) d3_cNW <= d2_cNW;
    reg [826:0] d_cNW; always @(posedge clk) d_cNW <= d3_cNW;
    reg [826:0] d0_cSE; always @(posedge clk) d0_cSE <= drv_cSE;
    reg [826:0] d1_cSE; always @(posedge clk) d1_cSE <= d0_cSE;
    reg [826:0] d2_cSE; always @(posedge clk) d2_cSE <= d1_cSE;
    reg [826:0] d3_cSE; always @(posedge clk) d3_cSE <= d2_cSE;
    reg [826:0] d_cSE; always @(posedge clk) d_cSE <= d3_cSE;
    reg [826:0] d0_cSW; always @(posedge clk) d0_cSW <= drv_cSW;
    reg [826:0] d1_cSW; always @(posedge clk) d1_cSW <= d0_cSW;
    reg [826:0] d2_cSW; always @(posedge clk) d2_cSW <= d1_cSW;
    reg [826:0] d3_cSW; always @(posedge clk) d3_cSW <= d2_cSW;
    reg [826:0] d_cSW; always @(posedge clk) d_cSW <= d3_cSW;
    reg [0:0] d0_ck; always @(posedge clk) d0_ck <= ck;
    reg [0:0] d1_ck; always @(posedge clk) d1_ck <= d0_ck;
    reg [0:0] d2_ck; always @(posedge clk) d2_ck <= d1_ck;
    reg [0:0] d3_ck; always @(posedge clk) d3_ck <= d2_ck;
    reg [0:0] d_ck; always @(posedge clk) d_ck <= d3_ck;
    reg [63:0] d0_f_barrier; always @(posedge clk) d0_f_barrier <= f_barrier;
    reg [63:0] d1_f_barrier; always @(posedge clk) d1_f_barrier <= d0_f_barrier;
    reg [63:0] d2_f_barrier; always @(posedge clk) d2_f_barrier <= d1_f_barrier;
    reg [63:0] d3_f_barrier; always @(posedge clk) d3_f_barrier <= d2_f_barrier;
    reg [63:0] d_f_barrier; always @(posedge clk) d_f_barrier <= d3_f_barrier;
    reg [32:0] d0_f_coll; always @(posedge clk) d0_f_coll <= f_coll;
    reg [32:0] d1_f_coll; always @(posedge clk) d1_f_coll <= d0_f_coll;
    reg [32:0] d2_f_coll; always @(posedge clk) d2_f_coll <= d1_f_coll;
    reg [32:0] d3_f_coll; always @(posedge clk) d3_f_coll <= d2_f_coll;
    reg [32:0] d_f_coll; always @(posedge clk) d_f_coll <= d3_f_coll;
    reg [340:0] d0_f_loader; always @(posedge clk) d0_f_loader <= f_loader;
    reg [340:0] d1_f_loader; always @(posedge clk) d1_f_loader <= d0_f_loader;
    reg [340:0] d2_f_loader; always @(posedge clk) d2_f_loader <= d1_f_loader;
    reg [340:0] d3_f_loader; always @(posedge clk) d3_f_loader <= d2_f_loader;
    reg [340:0] d_f_loader; always @(posedge clk) d_f_loader <= d3_f_loader;
    reg [63:0] d0_f_router; always @(posedge clk) d0_f_router <= f_router;
    reg [63:0] d1_f_router; always @(posedge clk) d1_f_router <= d0_f_router;
    reg [63:0] d2_f_router; always @(posedge clk) d2_f_router <= d1_f_router;
    reg [63:0] d3_f_router; always @(posedge clk) d3_f_router <= d2_f_router;
    reg [63:0] d_f_router; always @(posedge clk) d_f_router <= d3_f_router;
    reg [0:0] d0_rst; always @(posedge clk) d0_rst <= rst;
    reg [0:0] d1_rst; always @(posedge clk) d1_rst <= d0_rst;
    reg [0:0] d2_rst; always @(posedge clk) d2_rst <= d1_rst;
    reg [0:0] d3_rst; always @(posedge clk) d3_rst <= d2_rst;
    reg [0:0] d_rst; always @(posedge clk) d_rst <= d3_rst;
    wire [0:0] r_cpS_clk;
    assign r_cpS_clk = dut.w_cpS_clk;
    wire [0:0] r_cpS_rst_n;
    assign r_cpS_rst_n = dut.w_cpS_rst_n;
    wire [0:0] r_cpS_cmd_we;
    assign r_cpS_cmd_we = {d_f_loader[0:0]};
    wire [7:0] r_cpS_cmd_addr;
    assign r_cpS_cmd_addr = {d_f_loader[8:1]};
    wire [63:0] r_cpS_cmd_wdata;
    assign r_cpS_cmd_wdata = {d_f_loader[72:9]};
    wire [0:0] r_cpS_db_v;
    assign r_cpS_db_v = {d_f_loader[73:73]};
    wire [0:0] r_cpS_db_rdy;
    reg [0:0] q0_cpS_db_rdy; always @(posedge clk) q0_cpS_db_rdy <= r_cpS_db_rdy;
    reg [0:0] q1_cpS_db_rdy; always @(posedge clk) q1_cpS_db_rdy <= q0_cpS_db_rdy;
    reg [0:0] q2_cpS_db_rdy; always @(posedge clk) q2_cpS_db_rdy <= q1_cpS_db_rdy;
    reg [0:0] q3_cpS_db_rdy; always @(posedge clk) q3_cpS_db_rdy <= q2_cpS_db_rdy;
    reg [0:0] q_cpS_db_rdy; always @(posedge clk) q_cpS_db_rdy <= q3_cpS_db_rdy;
    wire [16:0] r_cpS_db_token;
    assign r_cpS_db_token = {d_f_loader[90:74]};
    wire [19:0] r_cpS_db_pos;
    assign r_cpS_db_pos = {d_f_loader[110:91]};
    wire [31:0] r_cpS_db_job;
    assign r_cpS_db_job = {d_f_loader[142:111]};
    wire [3:0] r_cpS_db_generation;
    assign r_cpS_db_generation = {d_f_loader[146:143]};
    wire [19:0] r_cpS_cpl_position;
    reg [19:0] q0_cpS_cpl_position; always @(posedge clk) q0_cpS_cpl_position <= r_cpS_cpl_position;
    reg [19:0] q1_cpS_cpl_position; always @(posedge clk) q1_cpS_cpl_position <= q0_cpS_cpl_position;
    reg [19:0] q2_cpS_cpl_position; always @(posedge clk) q2_cpS_cpl_position <= q1_cpS_cpl_position;
    reg [19:0] q3_cpS_cpl_position; always @(posedge clk) q3_cpS_cpl_position <= q2_cpS_cpl_position;
    reg [19:0] q_cpS_cpl_position; always @(posedge clk) q_cpS_cpl_position <= q3_cpS_cpl_position;
    wire [31:0] r_cpS_cpl_job;
    reg [31:0] q0_cpS_cpl_job; always @(posedge clk) q0_cpS_cpl_job <= r_cpS_cpl_job;
    reg [31:0] q1_cpS_cpl_job; always @(posedge clk) q1_cpS_cpl_job <= q0_cpS_cpl_job;
    reg [31:0] q2_cpS_cpl_job; always @(posedge clk) q2_cpS_cpl_job <= q1_cpS_cpl_job;
    reg [31:0] q3_cpS_cpl_job; always @(posedge clk) q3_cpS_cpl_job <= q2_cpS_cpl_job;
    reg [31:0] q_cpS_cpl_job; always @(posedge clk) q_cpS_cpl_job <= q3_cpS_cpl_job;
    wire [3:0] r_cpS_cpl_generation;
    reg [3:0] q0_cpS_cpl_generation; always @(posedge clk) q0_cpS_cpl_generation <= r_cpS_cpl_generation;
    reg [3:0] q1_cpS_cpl_generation; always @(posedge clk) q1_cpS_cpl_generation <= q0_cpS_cpl_generation;
    reg [3:0] q2_cpS_cpl_generation; always @(posedge clk) q2_cpS_cpl_generation <= q1_cpS_cpl_generation;
    reg [3:0] q3_cpS_cpl_generation; always @(posedge clk) q3_cpS_cpl_generation <= q2_cpS_cpl_generation;
    reg [3:0] q_cpS_cpl_generation; always @(posedge clk) q_cpS_cpl_generation <= q3_cpS_cpl_generation;
    wire [15:0] r_cpS_launch_v;
    reg [15:0] q0_cpS_launch_v; always @(posedge clk) q0_cpS_launch_v <= r_cpS_launch_v;
    reg [15:0] q1_cpS_launch_v; always @(posedge clk) q1_cpS_launch_v <= q0_cpS_launch_v;
    reg [15:0] q2_cpS_launch_v; always @(posedge clk) q2_cpS_launch_v <= q1_cpS_launch_v;
    reg [15:0] q3_cpS_launch_v; always @(posedge clk) q3_cpS_launch_v <= q2_cpS_launch_v;
    reg [15:0] q_cpS_launch_v; always @(posedge clk) q_cpS_launch_v <= q3_cpS_launch_v;
    wire [31:0] r_cpS_launch_pc;
    reg [31:0] q0_cpS_launch_pc; always @(posedge clk) q0_cpS_launch_pc <= r_cpS_launch_pc;
    reg [31:0] q1_cpS_launch_pc; always @(posedge clk) q1_cpS_launch_pc <= q0_cpS_launch_pc;
    reg [31:0] q2_cpS_launch_pc; always @(posedge clk) q2_cpS_launch_pc <= q1_cpS_launch_pc;
    reg [31:0] q3_cpS_launch_pc; always @(posedge clk) q3_cpS_launch_pc <= q2_cpS_launch_pc;
    reg [31:0] q_cpS_launch_pc; always @(posedge clk) q_cpS_launch_pc <= q3_cpS_launch_pc;
    wire [16:0] r_cpS_launch_token;
    reg [16:0] q0_cpS_launch_token; always @(posedge clk) q0_cpS_launch_token <= r_cpS_launch_token;
    reg [16:0] q1_cpS_launch_token; always @(posedge clk) q1_cpS_launch_token <= q0_cpS_launch_token;
    reg [16:0] q2_cpS_launch_token; always @(posedge clk) q2_cpS_launch_token <= q1_cpS_launch_token;
    reg [16:0] q3_cpS_launch_token; always @(posedge clk) q3_cpS_launch_token <= q2_cpS_launch_token;
    reg [16:0] q_cpS_launch_token; always @(posedge clk) q_cpS_launch_token <= q3_cpS_launch_token;
    wire [19:0] r_cpS_launch_pos;
    reg [19:0] q0_cpS_launch_pos; always @(posedge clk) q0_cpS_launch_pos <= r_cpS_launch_pos;
    reg [19:0] q1_cpS_launch_pos; always @(posedge clk) q1_cpS_launch_pos <= q0_cpS_launch_pos;
    reg [19:0] q2_cpS_launch_pos; always @(posedge clk) q2_cpS_launch_pos <= q1_cpS_launch_pos;
    reg [19:0] q3_cpS_launch_pos; always @(posedge clk) q3_cpS_launch_pos <= q2_cpS_launch_pos;
    reg [19:0] q_cpS_launch_pos; always @(posedge clk) q_cpS_launch_pos <= q3_cpS_launch_pos;
    wire [15:0] r_cpS_sm_done;
    assign r_cpS_sm_done = {d_cSE[765:765], d_cSE[662:662], d_cSE[559:559], d_cSE[456:456], d_cSE[353:353], d_cSE[250:250], d_cSE[147:147], d_cSE[44:44], d_cSW[765:765], d_cSW[662:662], d_cSW[559:559], d_cSW[456:456], d_cSW[353:353], d_cSW[250:250], d_cSW[147:147], d_cSW[44:44]};
    wire [15:0] r_cpS_sm_fault;
    assign r_cpS_sm_fault = dut.w_cpS_sm_fault;
    wire [15:0] r_cpS_res_v;
    assign r_cpS_res_v = dut.w_cpS_res_v;
    wire [511:0] r_cpS_res_data;
    assign r_cpS_res_data = dut.w_cpS_res_data;
    wire [0:0] r_cpS_cpl_v;
    reg [0:0] q0_cpS_cpl_v; always @(posedge clk) q0_cpS_cpl_v <= r_cpS_cpl_v;
    reg [0:0] q1_cpS_cpl_v; always @(posedge clk) q1_cpS_cpl_v <= q0_cpS_cpl_v;
    reg [0:0] q2_cpS_cpl_v; always @(posedge clk) q2_cpS_cpl_v <= q1_cpS_cpl_v;
    reg [0:0] q3_cpS_cpl_v; always @(posedge clk) q3_cpS_cpl_v <= q2_cpS_cpl_v;
    reg [0:0] q_cpS_cpl_v; always @(posedge clk) q_cpS_cpl_v <= q3_cpS_cpl_v;
    wire [0:0] r_cpS_cpl_rdy;
    assign r_cpS_cpl_rdy = dut.w_cpS_cpl_rdy;
    wire [16:0] r_cpS_cpl_token;
    reg [16:0] q0_cpS_cpl_token; always @(posedge clk) q0_cpS_cpl_token <= r_cpS_cpl_token;
    reg [16:0] q1_cpS_cpl_token; always @(posedge clk) q1_cpS_cpl_token <= q0_cpS_cpl_token;
    reg [16:0] q2_cpS_cpl_token; always @(posedge clk) q2_cpS_cpl_token <= q1_cpS_cpl_token;
    reg [16:0] q3_cpS_cpl_token; always @(posedge clk) q3_cpS_cpl_token <= q2_cpS_cpl_token;
    reg [16:0] q_cpS_cpl_token; always @(posedge clk) q_cpS_cpl_token <= q3_cpS_cpl_token;
    wire [3:0] r_cpS_cpl_status;
    reg [3:0] q0_cpS_cpl_status; always @(posedge clk) q0_cpS_cpl_status <= r_cpS_cpl_status;
    reg [3:0] q1_cpS_cpl_status; always @(posedge clk) q1_cpS_cpl_status <= q0_cpS_cpl_status;
    reg [3:0] q2_cpS_cpl_status; always @(posedge clk) q2_cpS_cpl_status <= q1_cpS_cpl_status;
    reg [3:0] q3_cpS_cpl_status; always @(posedge clk) q3_cpS_cpl_status <= q2_cpS_cpl_status;
    reg [3:0] q_cpS_cpl_status; always @(posedge clk) q_cpS_cpl_status <= q3_cpS_cpl_status;
    wire [31:0] r_cpS_cpl_cycles;
    reg [31:0] q0_cpS_cpl_cycles; always @(posedge clk) q0_cpS_cpl_cycles <= r_cpS_cpl_cycles;
    reg [31:0] q1_cpS_cpl_cycles; always @(posedge clk) q1_cpS_cpl_cycles <= q0_cpS_cpl_cycles;
    reg [31:0] q2_cpS_cpl_cycles; always @(posedge clk) q2_cpS_cpl_cycles <= q1_cpS_cpl_cycles;
    reg [31:0] q3_cpS_cpl_cycles; always @(posedge clk) q3_cpS_cpl_cycles <= q2_cpS_cpl_cycles;
    reg [31:0] q_cpS_cpl_cycles; always @(posedge clk) q_cpS_cpl_cycles <= q3_cpS_cpl_cycles;
    wire [31:0] r_cpS_st_kernels;
    reg [31:0] q0_cpS_st_kernels; always @(posedge clk) q0_cpS_st_kernels <= r_cpS_st_kernels;
    reg [31:0] q1_cpS_st_kernels; always @(posedge clk) q1_cpS_st_kernels <= q0_cpS_st_kernels;
    reg [31:0] q2_cpS_st_kernels; always @(posedge clk) q2_cpS_st_kernels <= q1_cpS_st_kernels;
    reg [31:0] q3_cpS_st_kernels; always @(posedge clk) q3_cpS_st_kernels <= q2_cpS_st_kernels;
    reg [31:0] q_cpS_st_kernels; always @(posedge clk) q_cpS_st_kernels <= q3_cpS_st_kernels;
    wire [31:0] r_cpS_st_busy;
    reg [31:0] q0_cpS_st_busy; always @(posedge clk) q0_cpS_st_busy <= r_cpS_st_busy;
    reg [31:0] q1_cpS_st_busy; always @(posedge clk) q1_cpS_st_busy <= q0_cpS_st_busy;
    reg [31:0] q2_cpS_st_busy; always @(posedge clk) q2_cpS_st_busy <= q1_cpS_st_busy;
    reg [31:0] q3_cpS_st_busy; always @(posedge clk) q3_cpS_st_busy <= q2_cpS_st_busy;
    reg [31:0] q_cpS_st_busy; always @(posedge clk) q_cpS_st_busy <= q3_cpS_st_busy;
    ot_hfd_cmdproc20_m #(.TW(17), .PW(20), .CONTEXT_POSITIONS(1048576), .ENABLE(1), .NSM(16), .NCMD(256)) ref_cpS (.clk(r_cpS_clk), .rst_n(r_cpS_rst_n), .cmd_we(r_cpS_cmd_we), .cmd_addr(r_cpS_cmd_addr), .cmd_wdata(r_cpS_cmd_wdata), .db_v(r_cpS_db_v), .db_rdy(r_cpS_db_rdy), .db_token(r_cpS_db_token), .db_pos(r_cpS_db_pos), .db_job(r_cpS_db_job), .db_generation(r_cpS_db_generation), .cpl_position(r_cpS_cpl_position), .cpl_job(r_cpS_cpl_job), .cpl_generation(r_cpS_cpl_generation), .launch_v(r_cpS_launch_v), .launch_pc(r_cpS_launch_pc), .launch_token(r_cpS_launch_token), .launch_pos(r_cpS_launch_pos), .sm_done(r_cpS_sm_done), .sm_fault(r_cpS_sm_fault), .res_v(r_cpS_res_v), .res_data(r_cpS_res_data), .cpl_v(r_cpS_cpl_v), .cpl_rdy(r_cpS_cpl_rdy), .cpl_token(r_cpS_cpl_token), .cpl_status(r_cpS_cpl_status), .cpl_cycles(r_cpS_cpl_cycles), .st_kernels(r_cpS_st_kernels), .st_busy(r_cpS_st_busy));
    wire [0:0] r_cpN_clk;
    assign r_cpN_clk = dut.w_cpN_clk;
    wire [0:0] r_cpN_rst_n;
    assign r_cpN_rst_n = dut.w_cpN_rst_n;
    wire [0:0] r_cpN_cmd_we;
    assign r_cpN_cmd_we = {d_f_loader[147:147]};
    wire [7:0] r_cpN_cmd_addr;
    assign r_cpN_cmd_addr = {d_f_loader[155:148]};
    wire [63:0] r_cpN_cmd_wdata;
    assign r_cpN_cmd_wdata = {d_f_loader[219:156]};
    wire [0:0] r_cpN_db_v;
    assign r_cpN_db_v = {d_f_loader[220:220]};
    wire [0:0] r_cpN_db_rdy;
    reg [0:0] q0_cpN_db_rdy; always @(posedge clk) q0_cpN_db_rdy <= r_cpN_db_rdy;
    reg [0:0] q1_cpN_db_rdy; always @(posedge clk) q1_cpN_db_rdy <= q0_cpN_db_rdy;
    reg [0:0] q2_cpN_db_rdy; always @(posedge clk) q2_cpN_db_rdy <= q1_cpN_db_rdy;
    reg [0:0] q3_cpN_db_rdy; always @(posedge clk) q3_cpN_db_rdy <= q2_cpN_db_rdy;
    reg [0:0] q_cpN_db_rdy; always @(posedge clk) q_cpN_db_rdy <= q3_cpN_db_rdy;
    wire [16:0] r_cpN_db_token;
    assign r_cpN_db_token = {d_f_loader[237:221]};
    wire [19:0] r_cpN_db_pos;
    assign r_cpN_db_pos = {d_f_loader[257:238]};
    wire [31:0] r_cpN_db_job;
    assign r_cpN_db_job = {d_f_loader[289:258]};
    wire [3:0] r_cpN_db_generation;
    assign r_cpN_db_generation = {d_f_loader[293:290]};
    wire [19:0] r_cpN_cpl_position;
    reg [19:0] q0_cpN_cpl_position; always @(posedge clk) q0_cpN_cpl_position <= r_cpN_cpl_position;
    reg [19:0] q1_cpN_cpl_position; always @(posedge clk) q1_cpN_cpl_position <= q0_cpN_cpl_position;
    reg [19:0] q2_cpN_cpl_position; always @(posedge clk) q2_cpN_cpl_position <= q1_cpN_cpl_position;
    reg [19:0] q3_cpN_cpl_position; always @(posedge clk) q3_cpN_cpl_position <= q2_cpN_cpl_position;
    reg [19:0] q_cpN_cpl_position; always @(posedge clk) q_cpN_cpl_position <= q3_cpN_cpl_position;
    wire [31:0] r_cpN_cpl_job;
    reg [31:0] q0_cpN_cpl_job; always @(posedge clk) q0_cpN_cpl_job <= r_cpN_cpl_job;
    reg [31:0] q1_cpN_cpl_job; always @(posedge clk) q1_cpN_cpl_job <= q0_cpN_cpl_job;
    reg [31:0] q2_cpN_cpl_job; always @(posedge clk) q2_cpN_cpl_job <= q1_cpN_cpl_job;
    reg [31:0] q3_cpN_cpl_job; always @(posedge clk) q3_cpN_cpl_job <= q2_cpN_cpl_job;
    reg [31:0] q_cpN_cpl_job; always @(posedge clk) q_cpN_cpl_job <= q3_cpN_cpl_job;
    wire [3:0] r_cpN_cpl_generation;
    reg [3:0] q0_cpN_cpl_generation; always @(posedge clk) q0_cpN_cpl_generation <= r_cpN_cpl_generation;
    reg [3:0] q1_cpN_cpl_generation; always @(posedge clk) q1_cpN_cpl_generation <= q0_cpN_cpl_generation;
    reg [3:0] q2_cpN_cpl_generation; always @(posedge clk) q2_cpN_cpl_generation <= q1_cpN_cpl_generation;
    reg [3:0] q3_cpN_cpl_generation; always @(posedge clk) q3_cpN_cpl_generation <= q2_cpN_cpl_generation;
    reg [3:0] q_cpN_cpl_generation; always @(posedge clk) q_cpN_cpl_generation <= q3_cpN_cpl_generation;
    wire [15:0] r_cpN_launch_v;
    reg [15:0] q0_cpN_launch_v; always @(posedge clk) q0_cpN_launch_v <= r_cpN_launch_v;
    reg [15:0] q1_cpN_launch_v; always @(posedge clk) q1_cpN_launch_v <= q0_cpN_launch_v;
    reg [15:0] q2_cpN_launch_v; always @(posedge clk) q2_cpN_launch_v <= q1_cpN_launch_v;
    reg [15:0] q3_cpN_launch_v; always @(posedge clk) q3_cpN_launch_v <= q2_cpN_launch_v;
    reg [15:0] q_cpN_launch_v; always @(posedge clk) q_cpN_launch_v <= q3_cpN_launch_v;
    wire [31:0] r_cpN_launch_pc;
    reg [31:0] q0_cpN_launch_pc; always @(posedge clk) q0_cpN_launch_pc <= r_cpN_launch_pc;
    reg [31:0] q1_cpN_launch_pc; always @(posedge clk) q1_cpN_launch_pc <= q0_cpN_launch_pc;
    reg [31:0] q2_cpN_launch_pc; always @(posedge clk) q2_cpN_launch_pc <= q1_cpN_launch_pc;
    reg [31:0] q3_cpN_launch_pc; always @(posedge clk) q3_cpN_launch_pc <= q2_cpN_launch_pc;
    reg [31:0] q_cpN_launch_pc; always @(posedge clk) q_cpN_launch_pc <= q3_cpN_launch_pc;
    wire [16:0] r_cpN_launch_token;
    reg [16:0] q0_cpN_launch_token; always @(posedge clk) q0_cpN_launch_token <= r_cpN_launch_token;
    reg [16:0] q1_cpN_launch_token; always @(posedge clk) q1_cpN_launch_token <= q0_cpN_launch_token;
    reg [16:0] q2_cpN_launch_token; always @(posedge clk) q2_cpN_launch_token <= q1_cpN_launch_token;
    reg [16:0] q3_cpN_launch_token; always @(posedge clk) q3_cpN_launch_token <= q2_cpN_launch_token;
    reg [16:0] q_cpN_launch_token; always @(posedge clk) q_cpN_launch_token <= q3_cpN_launch_token;
    wire [19:0] r_cpN_launch_pos;
    reg [19:0] q0_cpN_launch_pos; always @(posedge clk) q0_cpN_launch_pos <= r_cpN_launch_pos;
    reg [19:0] q1_cpN_launch_pos; always @(posedge clk) q1_cpN_launch_pos <= q0_cpN_launch_pos;
    reg [19:0] q2_cpN_launch_pos; always @(posedge clk) q2_cpN_launch_pos <= q1_cpN_launch_pos;
    reg [19:0] q3_cpN_launch_pos; always @(posedge clk) q3_cpN_launch_pos <= q2_cpN_launch_pos;
    reg [19:0] q_cpN_launch_pos; always @(posedge clk) q_cpN_launch_pos <= q3_cpN_launch_pos;
    wire [15:0] r_cpN_sm_done;
    assign r_cpN_sm_done = {d_cNE[765:765], d_cNE[662:662], d_cNE[559:559], d_cNE[456:456], d_cNE[353:353], d_cNE[250:250], d_cNE[147:147], d_cNE[44:44], d_cNW[765:765], d_cNW[662:662], d_cNW[559:559], d_cNW[456:456], d_cNW[353:353], d_cNW[250:250], d_cNW[147:147], d_cNW[44:44]};
    wire [15:0] r_cpN_sm_fault;
    assign r_cpN_sm_fault = dut.w_cpN_sm_fault;
    wire [15:0] r_cpN_res_v;
    assign r_cpN_res_v = dut.w_cpN_res_v;
    wire [511:0] r_cpN_res_data;
    assign r_cpN_res_data = dut.w_cpN_res_data;
    wire [0:0] r_cpN_cpl_v;
    reg [0:0] q0_cpN_cpl_v; always @(posedge clk) q0_cpN_cpl_v <= r_cpN_cpl_v;
    reg [0:0] q1_cpN_cpl_v; always @(posedge clk) q1_cpN_cpl_v <= q0_cpN_cpl_v;
    reg [0:0] q2_cpN_cpl_v; always @(posedge clk) q2_cpN_cpl_v <= q1_cpN_cpl_v;
    reg [0:0] q3_cpN_cpl_v; always @(posedge clk) q3_cpN_cpl_v <= q2_cpN_cpl_v;
    reg [0:0] q_cpN_cpl_v; always @(posedge clk) q_cpN_cpl_v <= q3_cpN_cpl_v;
    wire [0:0] r_cpN_cpl_rdy;
    assign r_cpN_cpl_rdy = dut.w_cpN_cpl_rdy;
    wire [16:0] r_cpN_cpl_token;
    reg [16:0] q0_cpN_cpl_token; always @(posedge clk) q0_cpN_cpl_token <= r_cpN_cpl_token;
    reg [16:0] q1_cpN_cpl_token; always @(posedge clk) q1_cpN_cpl_token <= q0_cpN_cpl_token;
    reg [16:0] q2_cpN_cpl_token; always @(posedge clk) q2_cpN_cpl_token <= q1_cpN_cpl_token;
    reg [16:0] q3_cpN_cpl_token; always @(posedge clk) q3_cpN_cpl_token <= q2_cpN_cpl_token;
    reg [16:0] q_cpN_cpl_token; always @(posedge clk) q_cpN_cpl_token <= q3_cpN_cpl_token;
    wire [3:0] r_cpN_cpl_status;
    reg [3:0] q0_cpN_cpl_status; always @(posedge clk) q0_cpN_cpl_status <= r_cpN_cpl_status;
    reg [3:0] q1_cpN_cpl_status; always @(posedge clk) q1_cpN_cpl_status <= q0_cpN_cpl_status;
    reg [3:0] q2_cpN_cpl_status; always @(posedge clk) q2_cpN_cpl_status <= q1_cpN_cpl_status;
    reg [3:0] q3_cpN_cpl_status; always @(posedge clk) q3_cpN_cpl_status <= q2_cpN_cpl_status;
    reg [3:0] q_cpN_cpl_status; always @(posedge clk) q_cpN_cpl_status <= q3_cpN_cpl_status;
    wire [31:0] r_cpN_cpl_cycles;
    reg [31:0] q0_cpN_cpl_cycles; always @(posedge clk) q0_cpN_cpl_cycles <= r_cpN_cpl_cycles;
    reg [31:0] q1_cpN_cpl_cycles; always @(posedge clk) q1_cpN_cpl_cycles <= q0_cpN_cpl_cycles;
    reg [31:0] q2_cpN_cpl_cycles; always @(posedge clk) q2_cpN_cpl_cycles <= q1_cpN_cpl_cycles;
    reg [31:0] q3_cpN_cpl_cycles; always @(posedge clk) q3_cpN_cpl_cycles <= q2_cpN_cpl_cycles;
    reg [31:0] q_cpN_cpl_cycles; always @(posedge clk) q_cpN_cpl_cycles <= q3_cpN_cpl_cycles;
    wire [31:0] r_cpN_st_kernels;
    reg [31:0] q0_cpN_st_kernels; always @(posedge clk) q0_cpN_st_kernels <= r_cpN_st_kernels;
    reg [31:0] q1_cpN_st_kernels; always @(posedge clk) q1_cpN_st_kernels <= q0_cpN_st_kernels;
    reg [31:0] q2_cpN_st_kernels; always @(posedge clk) q2_cpN_st_kernels <= q1_cpN_st_kernels;
    reg [31:0] q3_cpN_st_kernels; always @(posedge clk) q3_cpN_st_kernels <= q2_cpN_st_kernels;
    reg [31:0] q_cpN_st_kernels; always @(posedge clk) q_cpN_st_kernels <= q3_cpN_st_kernels;
    wire [31:0] r_cpN_st_busy;
    reg [31:0] q0_cpN_st_busy; always @(posedge clk) q0_cpN_st_busy <= r_cpN_st_busy;
    reg [31:0] q1_cpN_st_busy; always @(posedge clk) q1_cpN_st_busy <= q0_cpN_st_busy;
    reg [31:0] q2_cpN_st_busy; always @(posedge clk) q2_cpN_st_busy <= q1_cpN_st_busy;
    reg [31:0] q3_cpN_st_busy; always @(posedge clk) q3_cpN_st_busy <= q2_cpN_st_busy;
    reg [31:0] q_cpN_st_busy; always @(posedge clk) q_cpN_st_busy <= q3_cpN_st_busy;
    ot_hfd_cmdproc20_m #(.TW(17), .PW(20), .CONTEXT_POSITIONS(1048576), .ENABLE(1), .NSM(16), .NCMD(256)) ref_cpN (.clk(r_cpN_clk), .rst_n(r_cpN_rst_n), .cmd_we(r_cpN_cmd_we), .cmd_addr(r_cpN_cmd_addr), .cmd_wdata(r_cpN_cmd_wdata), .db_v(r_cpN_db_v), .db_rdy(r_cpN_db_rdy), .db_token(r_cpN_db_token), .db_pos(r_cpN_db_pos), .db_job(r_cpN_db_job), .db_generation(r_cpN_db_generation), .cpl_position(r_cpN_cpl_position), .cpl_job(r_cpN_cpl_job), .cpl_generation(r_cpN_cpl_generation), .launch_v(r_cpN_launch_v), .launch_pc(r_cpN_launch_pc), .launch_token(r_cpN_launch_token), .launch_pos(r_cpN_launch_pos), .sm_done(r_cpN_sm_done), .sm_fault(r_cpN_sm_fault), .res_v(r_cpN_res_v), .res_data(r_cpN_res_data), .cpl_v(r_cpN_cpl_v), .cpl_rdy(r_cpN_cpl_rdy), .cpl_token(r_cpN_cpl_token), .cpl_status(r_cpN_cpl_status), .cpl_cycles(r_cpN_cpl_cycles), .st_kernels(r_cpN_st_kernels), .st_busy(r_cpN_st_busy));
    integer err = 0, nchk = 0, cyc;
    integer seed = 20261006;
    task automatic randomize_inputs; begin
        drv_cNE[31:0] = $urandom(seed); seed = seed + 1;
        drv_cNE[63:32] = $urandom(seed); seed = seed + 1;
        drv_cNE[95:64] = $urandom(seed); seed = seed + 1;
        drv_cNE[127:96] = $urandom(seed); seed = seed + 1;
        drv_cNE[159:128] = $urandom(seed); seed = seed + 1;
        drv_cNE[191:160] = $urandom(seed); seed = seed + 1;
        drv_cNE[223:192] = $urandom(seed); seed = seed + 1;
        drv_cNE[255:224] = $urandom(seed); seed = seed + 1;
        drv_cNE[287:256] = $urandom(seed); seed = seed + 1;
        drv_cNE[319:288] = $urandom(seed); seed = seed + 1;
        drv_cNE[351:320] = $urandom(seed); seed = seed + 1;
        drv_cNE[383:352] = $urandom(seed); seed = seed + 1;
        drv_cNE[415:384] = $urandom(seed); seed = seed + 1;
        drv_cNE[447:416] = $urandom(seed); seed = seed + 1;
        drv_cNE[479:448] = $urandom(seed); seed = seed + 1;
        drv_cNE[511:480] = $urandom(seed); seed = seed + 1;
        drv_cNE[543:512] = $urandom(seed); seed = seed + 1;
        drv_cNE[575:544] = $urandom(seed); seed = seed + 1;
        drv_cNE[607:576] = $urandom(seed); seed = seed + 1;
        drv_cNE[639:608] = $urandom(seed); seed = seed + 1;
        drv_cNE[671:640] = $urandom(seed); seed = seed + 1;
        drv_cNE[703:672] = $urandom(seed); seed = seed + 1;
        drv_cNE[735:704] = $urandom(seed); seed = seed + 1;
        drv_cNE[767:736] = $urandom(seed); seed = seed + 1;
        drv_cNE[799:768] = $urandom(seed); seed = seed + 1;
        drv_cNE[826:800] = $urandom(seed); seed = seed + 1;
        drv_cNW[31:0] = $urandom(seed); seed = seed + 1;
        drv_cNW[63:32] = $urandom(seed); seed = seed + 1;
        drv_cNW[95:64] = $urandom(seed); seed = seed + 1;
        drv_cNW[127:96] = $urandom(seed); seed = seed + 1;
        drv_cNW[159:128] = $urandom(seed); seed = seed + 1;
        drv_cNW[191:160] = $urandom(seed); seed = seed + 1;
        drv_cNW[223:192] = $urandom(seed); seed = seed + 1;
        drv_cNW[255:224] = $urandom(seed); seed = seed + 1;
        drv_cNW[287:256] = $urandom(seed); seed = seed + 1;
        drv_cNW[319:288] = $urandom(seed); seed = seed + 1;
        drv_cNW[351:320] = $urandom(seed); seed = seed + 1;
        drv_cNW[383:352] = $urandom(seed); seed = seed + 1;
        drv_cNW[415:384] = $urandom(seed); seed = seed + 1;
        drv_cNW[447:416] = $urandom(seed); seed = seed + 1;
        drv_cNW[479:448] = $urandom(seed); seed = seed + 1;
        drv_cNW[511:480] = $urandom(seed); seed = seed + 1;
        drv_cNW[543:512] = $urandom(seed); seed = seed + 1;
        drv_cNW[575:544] = $urandom(seed); seed = seed + 1;
        drv_cNW[607:576] = $urandom(seed); seed = seed + 1;
        drv_cNW[639:608] = $urandom(seed); seed = seed + 1;
        drv_cNW[671:640] = $urandom(seed); seed = seed + 1;
        drv_cNW[703:672] = $urandom(seed); seed = seed + 1;
        drv_cNW[735:704] = $urandom(seed); seed = seed + 1;
        drv_cNW[767:736] = $urandom(seed); seed = seed + 1;
        drv_cNW[799:768] = $urandom(seed); seed = seed + 1;
        drv_cNW[826:800] = $urandom(seed); seed = seed + 1;
        drv_cSE[31:0] = $urandom(seed); seed = seed + 1;
        drv_cSE[63:32] = $urandom(seed); seed = seed + 1;
        drv_cSE[95:64] = $urandom(seed); seed = seed + 1;
        drv_cSE[127:96] = $urandom(seed); seed = seed + 1;
        drv_cSE[159:128] = $urandom(seed); seed = seed + 1;
        drv_cSE[191:160] = $urandom(seed); seed = seed + 1;
        drv_cSE[223:192] = $urandom(seed); seed = seed + 1;
        drv_cSE[255:224] = $urandom(seed); seed = seed + 1;
        drv_cSE[287:256] = $urandom(seed); seed = seed + 1;
        drv_cSE[319:288] = $urandom(seed); seed = seed + 1;
        drv_cSE[351:320] = $urandom(seed); seed = seed + 1;
        drv_cSE[383:352] = $urandom(seed); seed = seed + 1;
        drv_cSE[415:384] = $urandom(seed); seed = seed + 1;
        drv_cSE[447:416] = $urandom(seed); seed = seed + 1;
        drv_cSE[479:448] = $urandom(seed); seed = seed + 1;
        drv_cSE[511:480] = $urandom(seed); seed = seed + 1;
        drv_cSE[543:512] = $urandom(seed); seed = seed + 1;
        drv_cSE[575:544] = $urandom(seed); seed = seed + 1;
        drv_cSE[607:576] = $urandom(seed); seed = seed + 1;
        drv_cSE[639:608] = $urandom(seed); seed = seed + 1;
        drv_cSE[671:640] = $urandom(seed); seed = seed + 1;
        drv_cSE[703:672] = $urandom(seed); seed = seed + 1;
        drv_cSE[735:704] = $urandom(seed); seed = seed + 1;
        drv_cSE[767:736] = $urandom(seed); seed = seed + 1;
        drv_cSE[799:768] = $urandom(seed); seed = seed + 1;
        drv_cSE[826:800] = $urandom(seed); seed = seed + 1;
        drv_cSW[31:0] = $urandom(seed); seed = seed + 1;
        drv_cSW[63:32] = $urandom(seed); seed = seed + 1;
        drv_cSW[95:64] = $urandom(seed); seed = seed + 1;
        drv_cSW[127:96] = $urandom(seed); seed = seed + 1;
        drv_cSW[159:128] = $urandom(seed); seed = seed + 1;
        drv_cSW[191:160] = $urandom(seed); seed = seed + 1;
        drv_cSW[223:192] = $urandom(seed); seed = seed + 1;
        drv_cSW[255:224] = $urandom(seed); seed = seed + 1;
        drv_cSW[287:256] = $urandom(seed); seed = seed + 1;
        drv_cSW[319:288] = $urandom(seed); seed = seed + 1;
        drv_cSW[351:320] = $urandom(seed); seed = seed + 1;
        drv_cSW[383:352] = $urandom(seed); seed = seed + 1;
        drv_cSW[415:384] = $urandom(seed); seed = seed + 1;
        drv_cSW[447:416] = $urandom(seed); seed = seed + 1;
        drv_cSW[479:448] = $urandom(seed); seed = seed + 1;
        drv_cSW[511:480] = $urandom(seed); seed = seed + 1;
        drv_cSW[543:512] = $urandom(seed); seed = seed + 1;
        drv_cSW[575:544] = $urandom(seed); seed = seed + 1;
        drv_cSW[607:576] = $urandom(seed); seed = seed + 1;
        drv_cSW[639:608] = $urandom(seed); seed = seed + 1;
        drv_cSW[671:640] = $urandom(seed); seed = seed + 1;
        drv_cSW[703:672] = $urandom(seed); seed = seed + 1;
        drv_cSW[735:704] = $urandom(seed); seed = seed + 1;
        drv_cSW[767:736] = $urandom(seed); seed = seed + 1;
        drv_cSW[799:768] = $urandom(seed); seed = seed + 1;
        drv_cSW[826:800] = $urandom(seed); seed = seed + 1;
        f_barrier[31:0] = $urandom(seed); seed = seed + 1;
        f_barrier[63:32] = $urandom(seed); seed = seed + 1;
        f_coll[31:0] = $urandom(seed); seed = seed + 1;
        f_coll[32:32] = $urandom(seed); seed = seed + 1;
        f_loader[31:0] = $urandom(seed); seed = seed + 1;
        f_loader[63:32] = $urandom(seed); seed = seed + 1;
        f_loader[95:64] = $urandom(seed); seed = seed + 1;
        f_loader[127:96] = $urandom(seed); seed = seed + 1;
        f_loader[159:128] = $urandom(seed); seed = seed + 1;
        f_loader[191:160] = $urandom(seed); seed = seed + 1;
        f_loader[223:192] = $urandom(seed); seed = seed + 1;
        f_loader[255:224] = $urandom(seed); seed = seed + 1;
        f_loader[287:256] = $urandom(seed); seed = seed + 1;
        f_loader[319:288] = $urandom(seed); seed = seed + 1;
        f_loader[340:320] = $urandom(seed); seed = seed + 1;
        f_router[31:0] = $urandom(seed); seed = seed + 1;
        f_router[63:32] = $urandom(seed); seed = seed + 1;
    end endtask
    initial begin
        rst = 1;
        randomize_inputs;
        repeat (8) @(posedge clk);
        #0.05 rst = 0;
        for (cyc = 0; cyc < 400; cyc = cyc + 1) begin
            @(negedge clk);
            nchk = nchk + 1; if (cSW[0:0] !== q_cpS_launch_v[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[0:0] %h ref %h cyc %0d", cSW[0:0], q_cpS_launch_v[0:0], cyc); end
            nchk = nchk + 1; if (cSW[103:103] !== q_cpS_launch_v[1:1]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[103:103] %h ref %h cyc %0d", cSW[103:103], q_cpS_launch_v[1:1], cyc); end
            nchk = nchk + 1; if (cSW[206:206] !== q_cpS_launch_v[2:2]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[206:206] %h ref %h cyc %0d", cSW[206:206], q_cpS_launch_v[2:2], cyc); end
            nchk = nchk + 1; if (cSW[309:309] !== q_cpS_launch_v[3:3]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[309:309] %h ref %h cyc %0d", cSW[309:309], q_cpS_launch_v[3:3], cyc); end
            nchk = nchk + 1; if (cSW[412:412] !== q_cpS_launch_v[4:4]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[412:412] %h ref %h cyc %0d", cSW[412:412], q_cpS_launch_v[4:4], cyc); end
            nchk = nchk + 1; if (cSW[515:515] !== q_cpS_launch_v[5:5]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[515:515] %h ref %h cyc %0d", cSW[515:515], q_cpS_launch_v[5:5], cyc); end
            nchk = nchk + 1; if (cSW[618:618] !== q_cpS_launch_v[6:6]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[618:618] %h ref %h cyc %0d", cSW[618:618], q_cpS_launch_v[6:6], cyc); end
            nchk = nchk + 1; if (cSW[721:721] !== q_cpS_launch_v[7:7]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[721:721] %h ref %h cyc %0d", cSW[721:721], q_cpS_launch_v[7:7], cyc); end
            nchk = nchk + 1; if (cSE[0:0] !== q_cpS_launch_v[8:8]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[0:0] %h ref %h cyc %0d", cSE[0:0], q_cpS_launch_v[8:8], cyc); end
            nchk = nchk + 1; if (cSE[103:103] !== q_cpS_launch_v[9:9]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[103:103] %h ref %h cyc %0d", cSE[103:103], q_cpS_launch_v[9:9], cyc); end
            nchk = nchk + 1; if (cSE[206:206] !== q_cpS_launch_v[10:10]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[206:206] %h ref %h cyc %0d", cSE[206:206], q_cpS_launch_v[10:10], cyc); end
            nchk = nchk + 1; if (cSE[309:309] !== q_cpS_launch_v[11:11]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[309:309] %h ref %h cyc %0d", cSE[309:309], q_cpS_launch_v[11:11], cyc); end
            nchk = nchk + 1; if (cSE[412:412] !== q_cpS_launch_v[12:12]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[412:412] %h ref %h cyc %0d", cSE[412:412], q_cpS_launch_v[12:12], cyc); end
            nchk = nchk + 1; if (cSE[515:515] !== q_cpS_launch_v[13:13]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[515:515] %h ref %h cyc %0d", cSE[515:515], q_cpS_launch_v[13:13], cyc); end
            nchk = nchk + 1; if (cSE[618:618] !== q_cpS_launch_v[14:14]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[618:618] %h ref %h cyc %0d", cSE[618:618], q_cpS_launch_v[14:14], cyc); end
            nchk = nchk + 1; if (cSE[721:721] !== q_cpS_launch_v[15:15]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[721:721] %h ref %h cyc %0d", cSE[721:721], q_cpS_launch_v[15:15], cyc); end
            nchk = nchk + 1; if (cSW[45:45] !== q_cpS_launch_v[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[45:45] %h ref %h cyc %0d", cSW[45:45], q_cpS_launch_v[0:0], cyc); end
            nchk = nchk + 1; if (cSW[148:148] !== q_cpS_launch_v[1:1]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[148:148] %h ref %h cyc %0d", cSW[148:148], q_cpS_launch_v[1:1], cyc); end
            nchk = nchk + 1; if (cSW[251:251] !== q_cpS_launch_v[2:2]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[251:251] %h ref %h cyc %0d", cSW[251:251], q_cpS_launch_v[2:2], cyc); end
            nchk = nchk + 1; if (cSW[354:354] !== q_cpS_launch_v[3:3]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[354:354] %h ref %h cyc %0d", cSW[354:354], q_cpS_launch_v[3:3], cyc); end
            nchk = nchk + 1; if (cSW[457:457] !== q_cpS_launch_v[4:4]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[457:457] %h ref %h cyc %0d", cSW[457:457], q_cpS_launch_v[4:4], cyc); end
            nchk = nchk + 1; if (cSW[560:560] !== q_cpS_launch_v[5:5]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[560:560] %h ref %h cyc %0d", cSW[560:560], q_cpS_launch_v[5:5], cyc); end
            nchk = nchk + 1; if (cSW[663:663] !== q_cpS_launch_v[6:6]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[663:663] %h ref %h cyc %0d", cSW[663:663], q_cpS_launch_v[6:6], cyc); end
            nchk = nchk + 1; if (cSW[766:766] !== q_cpS_launch_v[7:7]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[766:766] %h ref %h cyc %0d", cSW[766:766], q_cpS_launch_v[7:7], cyc); end
            nchk = nchk + 1; if (cSE[45:45] !== q_cpS_launch_v[8:8]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[45:45] %h ref %h cyc %0d", cSE[45:45], q_cpS_launch_v[8:8], cyc); end
            nchk = nchk + 1; if (cSE[148:148] !== q_cpS_launch_v[9:9]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[148:148] %h ref %h cyc %0d", cSE[148:148], q_cpS_launch_v[9:9], cyc); end
            nchk = nchk + 1; if (cSE[251:251] !== q_cpS_launch_v[10:10]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[251:251] %h ref %h cyc %0d", cSE[251:251], q_cpS_launch_v[10:10], cyc); end
            nchk = nchk + 1; if (cSE[354:354] !== q_cpS_launch_v[11:11]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[354:354] %h ref %h cyc %0d", cSE[354:354], q_cpS_launch_v[11:11], cyc); end
            nchk = nchk + 1; if (cSE[457:457] !== q_cpS_launch_v[12:12]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[457:457] %h ref %h cyc %0d", cSE[457:457], q_cpS_launch_v[12:12], cyc); end
            nchk = nchk + 1; if (cSE[560:560] !== q_cpS_launch_v[13:13]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[560:560] %h ref %h cyc %0d", cSE[560:560], q_cpS_launch_v[13:13], cyc); end
            nchk = nchk + 1; if (cSE[663:663] !== q_cpS_launch_v[14:14]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[663:663] %h ref %h cyc %0d", cSE[663:663], q_cpS_launch_v[14:14], cyc); end
            nchk = nchk + 1; if (cSE[766:766] !== q_cpS_launch_v[15:15]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[766:766] %h ref %h cyc %0d", cSE[766:766], q_cpS_launch_v[15:15], cyc); end
            nchk = nchk + 1; if (cSW[32:1] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[32:1] %h ref %h cyc %0d", cSW[32:1], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[135:104] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[135:104] %h ref %h cyc %0d", cSW[135:104], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[238:207] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[238:207] %h ref %h cyc %0d", cSW[238:207], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[341:310] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[341:310] %h ref %h cyc %0d", cSW[341:310], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[444:413] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[444:413] %h ref %h cyc %0d", cSW[444:413], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[547:516] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[547:516] %h ref %h cyc %0d", cSW[547:516], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[650:619] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[650:619] %h ref %h cyc %0d", cSW[650:619], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[753:722] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[753:722] %h ref %h cyc %0d", cSW[753:722], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[32:1] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[32:1] %h ref %h cyc %0d", cSE[32:1], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[135:104] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[135:104] %h ref %h cyc %0d", cSE[135:104], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[238:207] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[238:207] %h ref %h cyc %0d", cSE[238:207], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[341:310] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[341:310] %h ref %h cyc %0d", cSE[341:310], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[444:413] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[444:413] %h ref %h cyc %0d", cSE[444:413], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[547:516] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[547:516] %h ref %h cyc %0d", cSE[547:516], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[650:619] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[650:619] %h ref %h cyc %0d", cSE[650:619], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[753:722] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[753:722] %h ref %h cyc %0d", cSE[753:722], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[77:46] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[77:46] %h ref %h cyc %0d", cSW[77:46], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[180:149] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[180:149] %h ref %h cyc %0d", cSW[180:149], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[283:252] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[283:252] %h ref %h cyc %0d", cSW[283:252], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[386:355] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[386:355] %h ref %h cyc %0d", cSW[386:355], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[489:458] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[489:458] %h ref %h cyc %0d", cSW[489:458], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[592:561] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[592:561] %h ref %h cyc %0d", cSW[592:561], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[695:664] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[695:664] %h ref %h cyc %0d", cSW[695:664], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSW[798:767] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[798:767] %h ref %h cyc %0d", cSW[798:767], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[77:46] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[77:46] %h ref %h cyc %0d", cSE[77:46], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[180:149] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[180:149] %h ref %h cyc %0d", cSE[180:149], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[283:252] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[283:252] %h ref %h cyc %0d", cSE[283:252], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[386:355] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[386:355] %h ref %h cyc %0d", cSE[386:355], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[489:458] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[489:458] %h ref %h cyc %0d", cSE[489:458], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[592:561] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[592:561] %h ref %h cyc %0d", cSE[592:561], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[695:664] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[695:664] %h ref %h cyc %0d", cSE[695:664], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cSE[798:767] !== q_cpS_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[798:767] %h ref %h cyc %0d", cSE[798:767], q_cpS_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (t_su_SW[16:0] !== q_cpS_launch_token[16:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_su_SW[16:0] %h ref %h cyc %0d", t_su_SW[16:0], q_cpS_launch_token[16:0], cyc); end
            nchk = nchk + 1; if (t_su_SE[16:0] !== q_cpS_launch_token[16:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_su_SE[16:0] %h ref %h cyc %0d", t_su_SE[16:0], q_cpS_launch_token[16:0], cyc); end
            nchk = nchk + 1; if (cSW[97:78] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[97:78] %h ref %h cyc %0d", cSW[97:78], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSW[200:181] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[200:181] %h ref %h cyc %0d", cSW[200:181], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSW[303:284] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[303:284] %h ref %h cyc %0d", cSW[303:284], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSW[406:387] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[406:387] %h ref %h cyc %0d", cSW[406:387], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSW[509:490] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[509:490] %h ref %h cyc %0d", cSW[509:490], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSW[612:593] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[612:593] %h ref %h cyc %0d", cSW[612:593], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSW[715:696] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[715:696] %h ref %h cyc %0d", cSW[715:696], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSW[818:799] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSW[818:799] %h ref %h cyc %0d", cSW[818:799], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSE[97:78] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[97:78] %h ref %h cyc %0d", cSE[97:78], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSE[200:181] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[200:181] %h ref %h cyc %0d", cSE[200:181], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSE[303:284] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[303:284] %h ref %h cyc %0d", cSE[303:284], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSE[406:387] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[406:387] %h ref %h cyc %0d", cSE[406:387], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSE[509:490] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[509:490] %h ref %h cyc %0d", cSE[509:490], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSE[612:593] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[612:593] %h ref %h cyc %0d", cSE[612:593], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSE[715:696] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[715:696] %h ref %h cyc %0d", cSE[715:696], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cSE[818:799] !== q_cpS_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cSE[818:799] %h ref %h cyc %0d", cSE[818:799], q_cpS_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNW[0:0] !== q_cpN_launch_v[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[0:0] %h ref %h cyc %0d", cNW[0:0], q_cpN_launch_v[0:0], cyc); end
            nchk = nchk + 1; if (cNW[103:103] !== q_cpN_launch_v[1:1]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[103:103] %h ref %h cyc %0d", cNW[103:103], q_cpN_launch_v[1:1], cyc); end
            nchk = nchk + 1; if (cNW[206:206] !== q_cpN_launch_v[2:2]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[206:206] %h ref %h cyc %0d", cNW[206:206], q_cpN_launch_v[2:2], cyc); end
            nchk = nchk + 1; if (cNW[309:309] !== q_cpN_launch_v[3:3]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[309:309] %h ref %h cyc %0d", cNW[309:309], q_cpN_launch_v[3:3], cyc); end
            nchk = nchk + 1; if (cNW[412:412] !== q_cpN_launch_v[4:4]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[412:412] %h ref %h cyc %0d", cNW[412:412], q_cpN_launch_v[4:4], cyc); end
            nchk = nchk + 1; if (cNW[515:515] !== q_cpN_launch_v[5:5]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[515:515] %h ref %h cyc %0d", cNW[515:515], q_cpN_launch_v[5:5], cyc); end
            nchk = nchk + 1; if (cNW[618:618] !== q_cpN_launch_v[6:6]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[618:618] %h ref %h cyc %0d", cNW[618:618], q_cpN_launch_v[6:6], cyc); end
            nchk = nchk + 1; if (cNW[721:721] !== q_cpN_launch_v[7:7]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[721:721] %h ref %h cyc %0d", cNW[721:721], q_cpN_launch_v[7:7], cyc); end
            nchk = nchk + 1; if (cNE[0:0] !== q_cpN_launch_v[8:8]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[0:0] %h ref %h cyc %0d", cNE[0:0], q_cpN_launch_v[8:8], cyc); end
            nchk = nchk + 1; if (cNE[103:103] !== q_cpN_launch_v[9:9]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[103:103] %h ref %h cyc %0d", cNE[103:103], q_cpN_launch_v[9:9], cyc); end
            nchk = nchk + 1; if (cNE[206:206] !== q_cpN_launch_v[10:10]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[206:206] %h ref %h cyc %0d", cNE[206:206], q_cpN_launch_v[10:10], cyc); end
            nchk = nchk + 1; if (cNE[309:309] !== q_cpN_launch_v[11:11]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[309:309] %h ref %h cyc %0d", cNE[309:309], q_cpN_launch_v[11:11], cyc); end
            nchk = nchk + 1; if (cNE[412:412] !== q_cpN_launch_v[12:12]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[412:412] %h ref %h cyc %0d", cNE[412:412], q_cpN_launch_v[12:12], cyc); end
            nchk = nchk + 1; if (cNE[515:515] !== q_cpN_launch_v[13:13]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[515:515] %h ref %h cyc %0d", cNE[515:515], q_cpN_launch_v[13:13], cyc); end
            nchk = nchk + 1; if (cNE[618:618] !== q_cpN_launch_v[14:14]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[618:618] %h ref %h cyc %0d", cNE[618:618], q_cpN_launch_v[14:14], cyc); end
            nchk = nchk + 1; if (cNE[721:721] !== q_cpN_launch_v[15:15]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[721:721] %h ref %h cyc %0d", cNE[721:721], q_cpN_launch_v[15:15], cyc); end
            nchk = nchk + 1; if (cNW[45:45] !== q_cpN_launch_v[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[45:45] %h ref %h cyc %0d", cNW[45:45], q_cpN_launch_v[0:0], cyc); end
            nchk = nchk + 1; if (cNW[148:148] !== q_cpN_launch_v[1:1]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[148:148] %h ref %h cyc %0d", cNW[148:148], q_cpN_launch_v[1:1], cyc); end
            nchk = nchk + 1; if (cNW[251:251] !== q_cpN_launch_v[2:2]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[251:251] %h ref %h cyc %0d", cNW[251:251], q_cpN_launch_v[2:2], cyc); end
            nchk = nchk + 1; if (cNW[354:354] !== q_cpN_launch_v[3:3]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[354:354] %h ref %h cyc %0d", cNW[354:354], q_cpN_launch_v[3:3], cyc); end
            nchk = nchk + 1; if (cNW[457:457] !== q_cpN_launch_v[4:4]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[457:457] %h ref %h cyc %0d", cNW[457:457], q_cpN_launch_v[4:4], cyc); end
            nchk = nchk + 1; if (cNW[560:560] !== q_cpN_launch_v[5:5]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[560:560] %h ref %h cyc %0d", cNW[560:560], q_cpN_launch_v[5:5], cyc); end
            nchk = nchk + 1; if (cNW[663:663] !== q_cpN_launch_v[6:6]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[663:663] %h ref %h cyc %0d", cNW[663:663], q_cpN_launch_v[6:6], cyc); end
            nchk = nchk + 1; if (cNW[766:766] !== q_cpN_launch_v[7:7]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[766:766] %h ref %h cyc %0d", cNW[766:766], q_cpN_launch_v[7:7], cyc); end
            nchk = nchk + 1; if (cNE[45:45] !== q_cpN_launch_v[8:8]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[45:45] %h ref %h cyc %0d", cNE[45:45], q_cpN_launch_v[8:8], cyc); end
            nchk = nchk + 1; if (cNE[148:148] !== q_cpN_launch_v[9:9]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[148:148] %h ref %h cyc %0d", cNE[148:148], q_cpN_launch_v[9:9], cyc); end
            nchk = nchk + 1; if (cNE[251:251] !== q_cpN_launch_v[10:10]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[251:251] %h ref %h cyc %0d", cNE[251:251], q_cpN_launch_v[10:10], cyc); end
            nchk = nchk + 1; if (cNE[354:354] !== q_cpN_launch_v[11:11]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[354:354] %h ref %h cyc %0d", cNE[354:354], q_cpN_launch_v[11:11], cyc); end
            nchk = nchk + 1; if (cNE[457:457] !== q_cpN_launch_v[12:12]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[457:457] %h ref %h cyc %0d", cNE[457:457], q_cpN_launch_v[12:12], cyc); end
            nchk = nchk + 1; if (cNE[560:560] !== q_cpN_launch_v[13:13]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[560:560] %h ref %h cyc %0d", cNE[560:560], q_cpN_launch_v[13:13], cyc); end
            nchk = nchk + 1; if (cNE[663:663] !== q_cpN_launch_v[14:14]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[663:663] %h ref %h cyc %0d", cNE[663:663], q_cpN_launch_v[14:14], cyc); end
            nchk = nchk + 1; if (cNE[766:766] !== q_cpN_launch_v[15:15]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[766:766] %h ref %h cyc %0d", cNE[766:766], q_cpN_launch_v[15:15], cyc); end
            nchk = nchk + 1; if (cNW[32:1] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[32:1] %h ref %h cyc %0d", cNW[32:1], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[135:104] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[135:104] %h ref %h cyc %0d", cNW[135:104], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[238:207] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[238:207] %h ref %h cyc %0d", cNW[238:207], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[341:310] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[341:310] %h ref %h cyc %0d", cNW[341:310], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[444:413] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[444:413] %h ref %h cyc %0d", cNW[444:413], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[547:516] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[547:516] %h ref %h cyc %0d", cNW[547:516], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[650:619] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[650:619] %h ref %h cyc %0d", cNW[650:619], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[753:722] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[753:722] %h ref %h cyc %0d", cNW[753:722], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[32:1] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[32:1] %h ref %h cyc %0d", cNE[32:1], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[135:104] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[135:104] %h ref %h cyc %0d", cNE[135:104], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[238:207] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[238:207] %h ref %h cyc %0d", cNE[238:207], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[341:310] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[341:310] %h ref %h cyc %0d", cNE[341:310], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[444:413] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[444:413] %h ref %h cyc %0d", cNE[444:413], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[547:516] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[547:516] %h ref %h cyc %0d", cNE[547:516], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[650:619] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[650:619] %h ref %h cyc %0d", cNE[650:619], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[753:722] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[753:722] %h ref %h cyc %0d", cNE[753:722], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[77:46] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[77:46] %h ref %h cyc %0d", cNW[77:46], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[180:149] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[180:149] %h ref %h cyc %0d", cNW[180:149], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[283:252] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[283:252] %h ref %h cyc %0d", cNW[283:252], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[386:355] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[386:355] %h ref %h cyc %0d", cNW[386:355], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[489:458] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[489:458] %h ref %h cyc %0d", cNW[489:458], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[592:561] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[592:561] %h ref %h cyc %0d", cNW[592:561], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[695:664] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[695:664] %h ref %h cyc %0d", cNW[695:664], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNW[798:767] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[798:767] %h ref %h cyc %0d", cNW[798:767], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[77:46] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[77:46] %h ref %h cyc %0d", cNE[77:46], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[180:149] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[180:149] %h ref %h cyc %0d", cNE[180:149], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[283:252] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[283:252] %h ref %h cyc %0d", cNE[283:252], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[386:355] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[386:355] %h ref %h cyc %0d", cNE[386:355], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[489:458] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[489:458] %h ref %h cyc %0d", cNE[489:458], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[592:561] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[592:561] %h ref %h cyc %0d", cNE[592:561], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[695:664] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[695:664] %h ref %h cyc %0d", cNE[695:664], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (cNE[798:767] !== q_cpN_launch_pc[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[798:767] %h ref %h cyc %0d", cNE[798:767], q_cpN_launch_pc[31:0], cyc); end
            nchk = nchk + 1; if (t_su_NW[16:0] !== q_cpN_launch_token[16:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_su_NW[16:0] %h ref %h cyc %0d", t_su_NW[16:0], q_cpN_launch_token[16:0], cyc); end
            nchk = nchk + 1; if (t_su_NE[16:0] !== q_cpN_launch_token[16:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_su_NE[16:0] %h ref %h cyc %0d", t_su_NE[16:0], q_cpN_launch_token[16:0], cyc); end
            nchk = nchk + 1; if (cNW[97:78] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[97:78] %h ref %h cyc %0d", cNW[97:78], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNW[200:181] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[200:181] %h ref %h cyc %0d", cNW[200:181], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNW[303:284] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[303:284] %h ref %h cyc %0d", cNW[303:284], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNW[406:387] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[406:387] %h ref %h cyc %0d", cNW[406:387], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNW[509:490] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[509:490] %h ref %h cyc %0d", cNW[509:490], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNW[612:593] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[612:593] %h ref %h cyc %0d", cNW[612:593], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNW[715:696] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[715:696] %h ref %h cyc %0d", cNW[715:696], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNW[818:799] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNW[818:799] %h ref %h cyc %0d", cNW[818:799], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNE[97:78] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[97:78] %h ref %h cyc %0d", cNE[97:78], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNE[200:181] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[200:181] %h ref %h cyc %0d", cNE[200:181], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNE[303:284] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[303:284] %h ref %h cyc %0d", cNE[303:284], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNE[406:387] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[406:387] %h ref %h cyc %0d", cNE[406:387], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNE[509:490] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[509:490] %h ref %h cyc %0d", cNE[509:490], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNE[612:593] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[612:593] %h ref %h cyc %0d", cNE[612:593], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNE[715:696] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[715:696] %h ref %h cyc %0d", cNE[715:696], q_cpN_launch_pos[19:0], cyc); end
            nchk = nchk + 1; if (cNE[818:799] !== q_cpN_launch_pos[19:0]) begin err = err + 1; if (err < 10) $display("MISMATCH cNE[818:799] %h ref %h cyc %0d", cNE[818:799], q_cpN_launch_pos[19:0], cyc); end
            randomize_inputs;
        end
        $display("TB_hfd_cmdproc checks=%0d mismatches=%0d", nchk, err);
        if (err != 0 || nchk == 0) $fatal(1, "FAIL");
        $finish;
    end
endmodule
