`timescale 1ns/1ps
// Cycle-exact lockstep: unchanged ot_ds_hbm_cmdproc20 vs ot_hfd_cmdproc20_m (command memory in the SRAM macro model),
// ENABLE 1, NSM 16, NCMD 256; one random stimulus (program writes at any time incl. during execution and on the FETCH
// address, doorbells, SM done / fault / result pulses, completion ready); every output compared every cycle.
module tb_cmdproc_m_equiv;
    localparam integer NSM = 16, NCMD = 256, TW = 17, PW = 20;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0, cmd_we = 0, db_v = 0, cpl_rdy = 0; reg [7:0] cmd_addr = 0; reg [63:0] cmd_wdata = 0;
    reg [TW-1:0] db_token = 0; reg [PW-1:0] db_pos = 0; reg [31:0] db_job = 0; reg [3:0] db_gen = 0;
    reg [NSM-1:0] sm_done = 0, sm_fault = 0, res_v = 0; reg [NSM*32-1:0] res_data = 0;
    `define PORTS(p) .clk(clk), .rst_n(rst_n), .cmd_we(cmd_we), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata), .db_v(db_v), \
        .db_rdy(p``_db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(db_job), .db_generation(db_gen), \
        .cpl_position(p``_cpl_position), .cpl_job(p``_cpl_job), .cpl_generation(p``_cpl_generation), .launch_v(p``_launch_v), \
        .launch_pc(p``_launch_pc), .launch_token(p``_launch_token), .launch_pos(p``_launch_pos), .sm_done(sm_done), \
        .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data), .cpl_v(p``_cpl_v), .cpl_rdy(cpl_rdy), .cpl_token(p``_cpl_token), \
        .cpl_status(p``_cpl_status), .cpl_cycles(p``_cpl_cycles), .st_kernels(p``_st_kernels), .st_busy(p``_st_busy)
    `define DECL(p) wire p``_db_rdy, p``_cpl_v; wire [PW-1:0] p``_cpl_position, p``_launch_pos; wire [31:0] p``_cpl_job, \
        p``_launch_pc, p``_cpl_cycles, p``_st_kernels, p``_st_busy; wire [3:0] p``_cpl_generation, p``_cpl_status; \
        wire [NSM-1:0] p``_launch_v; wire [TW-1:0] p``_launch_token, p``_cpl_token;
    `DECL(a) `DECL(b)
    ot_ds_hbm_cmdproc20 #(.ENABLE(1), .NSM(NSM), .NCMD(NCMD)) ua (`PORTS(a));
    `DUT #(.ENABLE(1), .NSM(NSM), .NCMD(NCMD)) ub (`PORTS(b));
    wire [1023:0] oa = {a_db_rdy, a_cpl_v, a_cpl_position, a_launch_pos, a_cpl_job, a_launch_pc, a_cpl_cycles, a_st_kernels,
                        a_st_busy, a_cpl_generation, a_cpl_status, a_launch_v, a_launch_token, a_cpl_token};
    wire [1023:0] ob = {b_db_rdy, b_cpl_v, b_cpl_position, b_launch_pos, b_cpl_job, b_launch_pc, b_cpl_cycles, b_st_kernels,
                        b_st_busy, b_cpl_generation, b_cpl_status, b_launch_v, b_launch_token, b_cpl_token};
    integer cyc, mism = 0, nl = 0, nc = 0, i; reg [3:0] op; reg [NSM-1:0] msk;
    initial begin
        // the macro has no reset: preload both memories with one program image through the write port
        repeat (3) @(posedge clk);
        for (i = 0; i < NCMD; i = i + 1) begin
            @(negedge clk); cmd_we = 1; cmd_addr = i;
            op = (i % 7 == 6) ? 4'd2 : 4'd1; msk = $urandom; if (i % 11 == 0) msk = 0;
            cmd_wdata = {op, msk, 12'd0, $urandom};
        end
        @(negedge clk); cmd_we = 0; rst_n = 1;
        for (cyc = 0; cyc < `CYC; cyc = cyc + 1) begin
            @(negedge clk);
            if (oa !== ob) begin mism = mism + 1; if (mism < 5) $display("MISMATCH cyc %0d", cyc); end
            nl = nl + (a_launch_v != 0); nc = nc + (a_cpl_v && cpl_rdy);
            cmd_we = ($urandom % 9) == 0; cmd_addr = ($urandom % 3 == 0) ? ($urandom % 16) : $urandom;
            op = ($urandom % 6 == 0) ? 4'd2 : (($urandom % 25 == 0) ? 4'd7 : 4'd1); msk = $urandom; if ($urandom % 13 == 0) msk = 0;
            cmd_wdata = {op, msk, 12'd0, $urandom};
            db_v = ($urandom % 4) == 0; db_token = $urandom; db_pos = ($urandom % 50 == 0) ? 20'hFFFFF : $urandom % 1000;
            db_job = $urandom; db_gen = $urandom;
            sm_done = ($urandom % 3 == 0) ? $urandom : 0; sm_fault = ($urandom % 400 == 0) ? (1 << ($urandom % NSM)) : 0;
            res_v = ($urandom % 8 == 0) ? (1 << ($urandom % NSM)) : 0;
            for (i = 0; i < NSM; i = i + 1) res_data[i*32 +: 32] = ($urandom % 4 == 0) ? $urandom : ($urandom % 131072);
            cpl_rdy = $urandom % 2;
            if (cyc % 5000 == 4999) rst_n = 0; else rst_n = 1;
        end
        $display("CPM_EQUIV cycles=%0d launches=%0d completions=%0d mismatches=%0d", cyc, nl, nc, mism);
        if (mism || nl == 0 || nc == 0) $fatal(1, "FAIL"); $finish;
    end
endmodule
