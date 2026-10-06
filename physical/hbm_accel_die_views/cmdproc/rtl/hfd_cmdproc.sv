// hfd_cmdproc: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  INTERIM: two unchanged ot_ds_hbm_cmdproc20 (ENABLE 1, NSM 16) on the die ports; not routed before, not closed. Program store and doorbell are loaded through the loader bus f_loader (cmd_we/addr/wdata 73 b + db_v/token/pos/job/generation 74 b); launch_v[n] drives SM n start and d_valid, launch_pc the op fields (40 b) and d_base, launch_pos d_lines; SM arrive -> t_barrier, barrier release f_barrier -> release_in, SM released -> sm_done. res_v/res_data/sm_fault/cpl_rdy have no die net (cfg chain); completion/status outputs fold into spare die output bits. The pipelined issue sequencer of the ledger is not built.
module hfd_cmdproc (
    inout wire [826:0] cNE,
    inout wire [826:0] cNW,
    inout wire [826:0] cSE,
    inout wire [826:0] cSW,
    input wire [0:0] ck,
    input wire [63:0] f_barrier,
    input wire [32:0] f_coll,
    input wire [340:0] f_loader,
    input wire [63:0] f_router,
    input wire [0:0] rst,
    output wire [63:0] t_barrier,
    output wire [24:0] t_coll,
    output wire [63:0] t_su_NE,
    output wire [63:0] t_su_NW,
    output wire [63:0] t_su_SE,
    output wire [63:0] t_su_SW
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [826:0] i_cNE; always @(posedge clk) i_cNE <= cNE;
    reg [826:0] i_cNW; always @(posedge clk) i_cNW <= cNW;
    reg [826:0] i_cSE; always @(posedge clk) i_cSE <= cSE;
    reg [826:0] i_cSW; always @(posedge clk) i_cSW <= cSW;
    reg [63:0] i_f_barrier; always @(posedge clk) i_f_barrier <= f_barrier;
    reg [32:0] i_f_coll; always @(posedge clk) i_f_coll <= f_coll;
    reg [340:0] i_f_loader; always @(posedge clk) i_f_loader <= f_loader;
    reg [63:0] i_f_router; always @(posedge clk) i_f_router <= f_router;
    wire [0:0] w_cpS_clk;
    wire [0:0] w_cpS_rst_n;
    wire [0:0] w_cpS_cmd_we;
    wire [7:0] w_cpS_cmd_addr;
    wire [63:0] w_cpS_cmd_wdata;
    wire [0:0] w_cpS_db_v;
    wire [0:0] w_cpS_db_rdy;
    wire [16:0] w_cpS_db_token;
    wire [19:0] w_cpS_db_pos;
    wire [31:0] w_cpS_db_job;
    wire [3:0] w_cpS_db_generation;
    wire [19:0] w_cpS_cpl_position;
    wire [31:0] w_cpS_cpl_job;
    wire [3:0] w_cpS_cpl_generation;
    wire [15:0] w_cpS_launch_v;
    wire [31:0] w_cpS_launch_pc;
    wire [16:0] w_cpS_launch_token;
    wire [19:0] w_cpS_launch_pos;
    wire [15:0] w_cpS_sm_done;
    wire [15:0] w_cpS_sm_fault;
    wire [15:0] w_cpS_res_v;
    wire [511:0] w_cpS_res_data;
    wire [0:0] w_cpS_cpl_v;
    wire [0:0] w_cpS_cpl_rdy;
    wire [16:0] w_cpS_cpl_token;
    wire [3:0] w_cpS_cpl_status;
    wire [31:0] w_cpS_cpl_cycles;
    wire [31:0] w_cpS_st_kernels;
    wire [31:0] w_cpS_st_busy;
    wire [0:0] w_cpN_clk;
    wire [0:0] w_cpN_rst_n;
    wire [0:0] w_cpN_cmd_we;
    wire [7:0] w_cpN_cmd_addr;
    wire [63:0] w_cpN_cmd_wdata;
    wire [0:0] w_cpN_db_v;
    wire [0:0] w_cpN_db_rdy;
    wire [16:0] w_cpN_db_token;
    wire [19:0] w_cpN_db_pos;
    wire [31:0] w_cpN_db_job;
    wire [3:0] w_cpN_db_generation;
    wire [19:0] w_cpN_cpl_position;
    wire [31:0] w_cpN_cpl_job;
    wire [3:0] w_cpN_cpl_generation;
    wire [15:0] w_cpN_launch_v;
    wire [31:0] w_cpN_launch_pc;
    wire [16:0] w_cpN_launch_token;
    wire [19:0] w_cpN_launch_pos;
    wire [15:0] w_cpN_sm_done;
    wire [15:0] w_cpN_sm_fault;
    wire [15:0] w_cpN_res_v;
    wire [511:0] w_cpN_res_data;
    wire [0:0] w_cpN_cpl_v;
    wire [0:0] w_cpN_cpl_rdy;
    wire [16:0] w_cpN_cpl_token;
    wire [3:0] w_cpN_cpl_status;
    wire [31:0] w_cpN_cpl_cycles;
    wire [31:0] w_cpN_st_kernels;
    wire [31:0] w_cpN_st_busy;
    // configuration chain: 1088 RTL input bits the die interface does not carry, shifted from die input cNE[42]
    reg [1087:0] cfg; always @(posedge clk) cfg <= {cfg[1086:0], i_cNE[42]};
    assign w_cpS_clk = {1{clk}};
    assign w_cpS_rst_n = {1{rst_n}};
    assign w_cpS_cmd_we = {i_f_loader[0:0]};
    assign w_cpS_cmd_addr = {i_f_loader[8:1]};
    assign w_cpS_cmd_wdata = {i_f_loader[72:9]};
    assign w_cpS_db_v = {i_f_loader[73:73]};
    assign w_cpS_db_token = {i_f_loader[90:74]};
    assign w_cpS_db_pos = {i_f_loader[110:91]};
    assign w_cpS_db_job = {i_f_loader[142:111]};
    assign w_cpS_db_generation = {i_f_loader[146:143]};
    assign w_cpS_sm_done = {i_cSE[765:765], i_cSE[662:662], i_cSE[559:559], i_cSE[456:456], i_cSE[353:353], i_cSE[250:250], i_cSE[147:147], i_cSE[44:44], i_cSW[765:765], i_cSW[662:662], i_cSW[559:559], i_cSW[456:456], i_cSW[353:353], i_cSW[250:250], i_cSW[147:147], i_cSW[44:44]};
    assign w_cpS_sm_fault = cfg[15:0];
    assign w_cpS_res_v = cfg[31:16];
    assign w_cpS_res_data = cfg[543:32];
    assign w_cpS_cpl_rdy = 1'd1;
    ot_ds_hbm_cmdproc20 #(.TW(17), .PW(20), .CONTEXT_POSITIONS(1048576), .ENABLE(1), .NSM(16), .NCMD(256)) u_cpS (.clk(w_cpS_clk), .rst_n(w_cpS_rst_n), .cmd_we(w_cpS_cmd_we), .cmd_addr(w_cpS_cmd_addr), .cmd_wdata(w_cpS_cmd_wdata), .db_v(w_cpS_db_v), .db_rdy(w_cpS_db_rdy), .db_token(w_cpS_db_token), .db_pos(w_cpS_db_pos), .db_job(w_cpS_db_job), .db_generation(w_cpS_db_generation), .cpl_position(w_cpS_cpl_position), .cpl_job(w_cpS_cpl_job), .cpl_generation(w_cpS_cpl_generation), .launch_v(w_cpS_launch_v), .launch_pc(w_cpS_launch_pc), .launch_token(w_cpS_launch_token), .launch_pos(w_cpS_launch_pos), .sm_done(w_cpS_sm_done), .sm_fault(w_cpS_sm_fault), .res_v(w_cpS_res_v), .res_data(w_cpS_res_data), .cpl_v(w_cpS_cpl_v), .cpl_rdy(w_cpS_cpl_rdy), .cpl_token(w_cpS_cpl_token), .cpl_status(w_cpS_cpl_status), .cpl_cycles(w_cpS_cpl_cycles), .st_kernels(w_cpS_st_kernels), .st_busy(w_cpS_st_busy));
    assign w_cpN_clk = {1{clk}};
    assign w_cpN_rst_n = {1{rst_n}};
    assign w_cpN_cmd_we = {i_f_loader[147:147]};
    assign w_cpN_cmd_addr = {i_f_loader[155:148]};
    assign w_cpN_cmd_wdata = {i_f_loader[219:156]};
    assign w_cpN_db_v = {i_f_loader[220:220]};
    assign w_cpN_db_token = {i_f_loader[237:221]};
    assign w_cpN_db_pos = {i_f_loader[257:238]};
    assign w_cpN_db_job = {i_f_loader[289:258]};
    assign w_cpN_db_generation = {i_f_loader[293:290]};
    assign w_cpN_sm_done = {i_cNE[765:765], i_cNE[662:662], i_cNE[559:559], i_cNE[456:456], i_cNE[353:353], i_cNE[250:250], i_cNE[147:147], i_cNE[44:44], i_cNW[765:765], i_cNW[662:662], i_cNW[559:559], i_cNW[456:456], i_cNW[353:353], i_cNW[250:250], i_cNW[147:147], i_cNW[44:44]};
    assign w_cpN_sm_fault = cfg[559:544];
    assign w_cpN_res_v = cfg[575:560];
    assign w_cpN_res_data = cfg[1087:576];
    assign w_cpN_cpl_rdy = 1'd1;
    ot_ds_hbm_cmdproc20 #(.TW(17), .PW(20), .CONTEXT_POSITIONS(1048576), .ENABLE(1), .NSM(16), .NCMD(256)) u_cpN (.clk(w_cpN_clk), .rst_n(w_cpN_rst_n), .cmd_we(w_cpN_cmd_we), .cmd_addr(w_cpN_cmd_addr), .cmd_wdata(w_cpN_cmd_wdata), .db_v(w_cpN_db_v), .db_rdy(w_cpN_db_rdy), .db_token(w_cpN_db_token), .db_pos(w_cpN_db_pos), .db_job(w_cpN_db_job), .db_generation(w_cpN_db_generation), .cpl_position(w_cpN_cpl_position), .cpl_job(w_cpN_cpl_job), .cpl_generation(w_cpN_cpl_generation), .launch_v(w_cpN_launch_v), .launch_pc(w_cpN_launch_pc), .launch_token(w_cpN_launch_token), .launch_pos(w_cpN_launch_pos), .sm_done(w_cpN_sm_done), .sm_fault(w_cpN_sm_fault), .res_v(w_cpN_res_v), .res_data(w_cpN_res_data), .cpl_v(w_cpN_cpl_v), .cpl_rdy(w_cpN_cpl_rdy), .cpl_token(w_cpN_cpl_token), .cpl_status(w_cpN_cpl_status), .cpl_cycles(w_cpN_cpl_cycles), .st_kernels(w_cpN_st_kernels), .st_busy(w_cpN_st_busy));
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_cpS_db_rdy
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_db_rdy[k]), .q());
    end
    for (genvar k = 0; k < 20; k = k + 1) begin : g_sink_w_cpS_cpl_position
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_cpl_position[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_cpS_cpl_job
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_cpl_job[k]), .q());
    end
    for (genvar k = 0; k < 4; k = k + 1) begin : g_sink_w_cpS_cpl_generation
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_cpl_generation[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_cpS_cpl_v
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_cpl_v[k]), .q());
    end
    for (genvar k = 0; k < 17; k = k + 1) begin : g_sink_w_cpS_cpl_token
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_cpl_token[k]), .q());
    end
    for (genvar k = 0; k < 4; k = k + 1) begin : g_sink_w_cpS_cpl_status
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_cpl_status[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_cpS_cpl_cycles
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_cpl_cycles[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_cpS_st_kernels
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_st_kernels[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_cpS_st_busy
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpS_st_busy[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_cpN_db_rdy
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_db_rdy[k]), .q());
    end
    for (genvar k = 0; k < 20; k = k + 1) begin : g_sink_w_cpN_cpl_position
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_cpl_position[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_cpN_cpl_job
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_cpl_job[k]), .q());
    end
    for (genvar k = 0; k < 4; k = k + 1) begin : g_sink_w_cpN_cpl_generation
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_cpl_generation[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_cpN_cpl_v
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_cpl_v[k]), .q());
    end
    for (genvar k = 0; k < 17; k = k + 1) begin : g_sink_w_cpN_cpl_token
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_cpl_token[k]), .q());
    end
    for (genvar k = 0; k < 4; k = k + 1) begin : g_sink_w_cpN_cpl_status
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_cpl_status[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_cpN_cpl_cycles
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_cpl_cycles[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_cpN_st_kernels
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_st_kernels[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_cpN_st_busy
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_cpN_st_busy[k]), .q());
    end
    wire fclk_0; ot_fwd_clk_inv u_fclk_0 (.a(clk), .y(fclk_0));
    wire fclk_1; ot_fwd_clk_inv u_fclk_1 (.a(clk), .y(fclk_1));
    wire fclk_2; ot_fwd_clk_inv u_fclk_2 (.a(clk), .y(fclk_2));
    wire fclk_3; ot_fwd_clk_inv u_fclk_3 (.a(clk), .y(fclk_3));
    wire fclk_4; ot_fwd_clk_inv u_fclk_4 (.a(clk), .y(fclk_4));
    wire fclk_5; ot_fwd_clk_inv u_fclk_5 (.a(clk), .y(fclk_5));
    wire fclk_6; ot_fwd_clk_inv u_fclk_6 (.a(clk), .y(fclk_6));
    wire fclk_7; ot_fwd_clk_inv u_fclk_7 (.a(clk), .y(fclk_7));
    wire [826:0] od_cNE = {8'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[15:15], 3'd0, i_f_barrier[31], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[15:15], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[14:14], 3'd0, i_f_barrier[30], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[14:14], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[13:13], 3'd0, i_f_barrier[29], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[13:13], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[12:12], 3'd0, i_f_barrier[28], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[12:12], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[11:11], 3'd0, i_f_barrier[27], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[11:11], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[10:10], 3'd0, i_f_barrier[26], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[10:10], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[9:9], 3'd0, i_f_barrier[25], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[9:9], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[8:8], 3'd0, i_f_barrier[24], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[8:8]};
    wire [826:0] o_cNE;
    for (genvar k = 0; k < 827; k = k + 1) begin : g_o_cNE
        ot_hfd_oreg1 u (.clk(clk), .d(od_cNE[k]), .q(o_cNE[k]));
    end
    assign cNE[41:0] = o_cNE[41:0];
    assign cNE[101:45] = o_cNE[101:45];
    assign cNE[144:103] = o_cNE[144:103];
    assign cNE[204:148] = o_cNE[204:148];
    assign cNE[247:206] = o_cNE[247:206];
    assign cNE[307:251] = o_cNE[307:251];
    assign cNE[350:309] = o_cNE[350:309];
    assign cNE[410:354] = o_cNE[410:354];
    assign cNE[453:412] = o_cNE[453:412];
    assign cNE[513:457] = o_cNE[513:457];
    assign cNE[556:515] = o_cNE[556:515];
    assign cNE[616:560] = o_cNE[616:560];
    assign cNE[659:618] = o_cNE[659:618];
    assign cNE[719:663] = o_cNE[719:663];
    assign cNE[762:721] = o_cNE[762:721];
    assign cNE[822:766] = o_cNE[822:766];
    assign cNE[824] = fclk_0;
    assign cNE[825] = fclk_1;
    wire [826:0] od_cNW = {8'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[7:7], 3'd0, i_f_barrier[23], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[7:7], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[6:6], 3'd0, i_f_barrier[22], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[6:6], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[5:5], 3'd0, i_f_barrier[21], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[5:5], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[4:4], 3'd0, i_f_barrier[20], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[4:4], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[3:3], 3'd0, i_f_barrier[19], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[3:3], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[2:2], 3'd0, i_f_barrier[18], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[2:2], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[1:1], 3'd0, i_f_barrier[17], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[1:1], 5'd0, w_cpN_launch_pos[19:0], w_cpN_launch_pc[31:0], w_cpN_launch_v[0:0], 3'd0, i_f_barrier[16], 8'd0, w_cpN_launch_pc[31:0], w_cpN_launch_v[0:0]};
    wire [826:0] o_cNW;
    for (genvar k = 0; k < 827; k = k + 1) begin : g_o_cNW
        ot_hfd_oreg1 u (.clk(clk), .d(od_cNW[k]), .q(o_cNW[k]));
    end
    assign cNW[41:0] = o_cNW[41:0];
    assign cNW[101:45] = o_cNW[101:45];
    assign cNW[144:103] = o_cNW[144:103];
    assign cNW[204:148] = o_cNW[204:148];
    assign cNW[247:206] = o_cNW[247:206];
    assign cNW[307:251] = o_cNW[307:251];
    assign cNW[350:309] = o_cNW[350:309];
    assign cNW[410:354] = o_cNW[410:354];
    assign cNW[453:412] = o_cNW[453:412];
    assign cNW[513:457] = o_cNW[513:457];
    assign cNW[556:515] = o_cNW[556:515];
    assign cNW[616:560] = o_cNW[616:560];
    assign cNW[659:618] = o_cNW[659:618];
    assign cNW[719:663] = o_cNW[719:663];
    assign cNW[762:721] = o_cNW[762:721];
    assign cNW[822:766] = o_cNW[822:766];
    assign cNW[824] = fclk_2;
    assign cNW[825] = fclk_3;
    wire [826:0] od_cSE = {8'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[15:15], 3'd0, i_f_barrier[15], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[15:15], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[14:14], 3'd0, i_f_barrier[14], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[14:14], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[13:13], 3'd0, i_f_barrier[13], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[13:13], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[12:12], 3'd0, i_f_barrier[12], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[12:12], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[11:11], 3'd0, i_f_barrier[11], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[11:11], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[10:10], 3'd0, i_f_barrier[10], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[10:10], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[9:9], 3'd0, i_f_barrier[9], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[9:9], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[8:8], 3'd0, i_f_barrier[8], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[8:8]};
    wire [826:0] o_cSE;
    for (genvar k = 0; k < 827; k = k + 1) begin : g_o_cSE
        ot_hfd_oreg1 u (.clk(clk), .d(od_cSE[k]), .q(o_cSE[k]));
    end
    assign cSE[41:0] = o_cSE[41:0];
    assign cSE[101:45] = o_cSE[101:45];
    assign cSE[144:103] = o_cSE[144:103];
    assign cSE[204:148] = o_cSE[204:148];
    assign cSE[247:206] = o_cSE[247:206];
    assign cSE[307:251] = o_cSE[307:251];
    assign cSE[350:309] = o_cSE[350:309];
    assign cSE[410:354] = o_cSE[410:354];
    assign cSE[453:412] = o_cSE[453:412];
    assign cSE[513:457] = o_cSE[513:457];
    assign cSE[556:515] = o_cSE[556:515];
    assign cSE[616:560] = o_cSE[616:560];
    assign cSE[659:618] = o_cSE[659:618];
    assign cSE[719:663] = o_cSE[719:663];
    assign cSE[762:721] = o_cSE[762:721];
    assign cSE[822:766] = o_cSE[822:766];
    assign cSE[824] = fclk_4;
    assign cSE[825] = fclk_5;
    wire [826:0] od_cSW = {8'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[7:7], 3'd0, i_f_barrier[7], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[7:7], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[6:6], 3'd0, i_f_barrier[6], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[6:6], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[5:5], 3'd0, i_f_barrier[5], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[5:5], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[4:4], 3'd0, i_f_barrier[4], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[4:4], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[3:3], 3'd0, i_f_barrier[3], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[3:3], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[2:2], 3'd0, i_f_barrier[2], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[2:2], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[1:1], 3'd0, i_f_barrier[1], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[1:1], 5'd0, w_cpS_launch_pos[19:0], w_cpS_launch_pc[31:0], w_cpS_launch_v[0:0], 3'd0, i_f_barrier[0], 8'd0, w_cpS_launch_pc[31:0], w_cpS_launch_v[0:0]};
    wire [826:0] o_cSW;
    for (genvar k = 0; k < 827; k = k + 1) begin : g_o_cSW
        ot_hfd_oreg1 u (.clk(clk), .d(od_cSW[k]), .q(o_cSW[k]));
    end
    assign cSW[41:0] = o_cSW[41:0];
    assign cSW[101:45] = o_cSW[101:45];
    assign cSW[144:103] = o_cSW[144:103];
    assign cSW[204:148] = o_cSW[204:148];
    assign cSW[247:206] = o_cSW[247:206];
    assign cSW[307:251] = o_cSW[307:251];
    assign cSW[350:309] = o_cSW[350:309];
    assign cSW[410:354] = o_cSW[410:354];
    assign cSW[453:412] = o_cSW[453:412];
    assign cSW[513:457] = o_cSW[513:457];
    assign cSW[556:515] = o_cSW[556:515];
    assign cSW[616:560] = o_cSW[616:560];
    assign cSW[659:618] = o_cSW[659:618];
    assign cSW[719:663] = o_cSW[719:663];
    assign cSW[762:721] = o_cSW[762:721];
    assign cSW[822:766] = o_cSW[822:766];
    assign cSW[824] = fclk_6;
    assign cSW[825] = fclk_7;
    wire [63:0] od_t_barrier = {32'd0, i_cNE[764], i_cNE[661], i_cNE[558], i_cNE[455], i_cNE[352], i_cNE[249], i_cNE[146], i_cNE[43], i_cNW[764], i_cNW[661], i_cNW[558], i_cNW[455], i_cNW[352], i_cNW[249], i_cNW[146], i_cNW[43], i_cSE[764], i_cSE[661], i_cSE[558], i_cSE[455], i_cSE[352], i_cSE[249], i_cSE[146], i_cSE[43], i_cSW[764], i_cSW[661], i_cSW[558], i_cSW[455], i_cSW[352], i_cSW[249], i_cSW[146], i_cSW[43]};
    wire [63:0] o_t_barrier;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_barrier
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_barrier[k]), .q(o_t_barrier[k]));
    end
    assign t_barrier[63:0] = o_t_barrier[63:0];
    wire [24:0] od_t_coll = {25'd0};
    wire [24:0] o_t_coll;
    for (genvar k = 0; k < 25; k = k + 1) begin : g_o_t_coll
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_coll[k]), .q(o_t_coll[k]));
    end
    assign t_coll[24:0] = o_t_coll[24:0];
    wire [63:0] od_t_su_NE = {47'd0, w_cpN_launch_token[16:0]};
    wire [63:0] o_t_su_NE;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_su_NE
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_su_NE[k]), .q(o_t_su_NE[k]));
    end
    assign t_su_NE[63:0] = o_t_su_NE[63:0];
    wire [63:0] od_t_su_NW = {47'd0, w_cpN_launch_token[16:0]};
    wire [63:0] o_t_su_NW;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_su_NW
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_su_NW[k]), .q(o_t_su_NW[k]));
    end
    assign t_su_NW[63:0] = o_t_su_NW[63:0];
    wire [63:0] od_t_su_SE = {47'd0, w_cpS_launch_token[16:0]};
    wire [63:0] o_t_su_SE;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_su_SE
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_su_SE[k]), .q(o_t_su_SE[k]));
    end
    assign t_su_SE[63:0] = o_t_su_SE[63:0];
    wire [63:0] od_t_su_SW = {47'd0, w_cpS_launch_token[16:0]};
    wire [63:0] o_t_su_SW;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_su_SW
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_su_SW[k]), .q(o_t_su_SW[k]));
    end
    assign t_su_SW[63:0] = o_t_su_SW[63:0];
endmodule
