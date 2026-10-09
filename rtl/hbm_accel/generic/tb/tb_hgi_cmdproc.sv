`timescale 1ns/1ps
// hbm-forks 2026-10-09: HGI-1 cmdproc fork bench.
//   CF-0  the config path: every case of tools/hgi_cfg_rtl.py (DS load = no change, Qwen load + read-back of all 9
//         section-C words through a station + receiver, each error code with the previous values kept, E_BUSY, a
//         section-B-only change accepted), doorbells refused while a commit settles, settle >= SETTLE cycles.
//   CF-CP Qwen: ids 131071 / 131072 / 151935 accepted, 151936 refused, pos 40959 accepted / 40960 refused;
//         DS (reset and after a DS reload): 129279 accepted, 129280 refused, pos 2^20-1 accepted.
//   CF-1  lockstep with the legacy DS die core ot_hfd_cmdproc20_m (TW 17) before any load: random command lists,
//         doorbells, SM done / fault / results (DS tokens < 129,280), every output compared every cycle.
// Prints HGI_CMDPROC PASS / FAIL.  Mutants: +define+OT_HGI_MUT_CRC / OT_HGI_MUT_RANGE (must FAIL).
module tb_hgi_cmdproc;
`include "ot_hgi_cfg_consts.svh"
    localparam integer NSM = 16, NCASE = 17, REC = 74;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg cmd_we = 0; reg [8:0] cmd_addr = 0; reg [63:0] cmd_wdata = 0; reg units_busy = 0;
    reg db_v = 0; reg [17:0] db_token = 0; reg [19:0] db_pos = 0; reg [31:0] db_job = 0; reg [3:0] db_gen = 0;
    reg [NSM-1:0] sm_done = 0, sm_fault = 0, res_v = 0; reg [NSM*32-1:0] res_data = 0; reg cpl_rdy = 0;
    wire [39:0] bus, bus1; wire loaded; wire [2:0] err; wire [159:0] md_d; wire [63:0] cp_act;
    wire db_rdy, cpl_v; wire [19:0] cpl_pos, l_pos; wire [31:0] cpl_job, l_pc, cpl_cyc, st_k, st_b; wire [3:0] cpl_gen, cpl_st;
    wire [NSM-1:0] l_v; wire [17:0] l_tok, cpl_tok;
    ot_hgi_cmdproc #(.NSM(NSM), .MACRO(1), .RDREG(2), .SETTLE(64)) dut (.clk(clk), .rst_n(rst_n), .cmd_we(cmd_we),
        .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata), .units_busy(units_busy), .cfg_bus(bus), .cfg_loaded(loaded),
        .cfg_err(err), .cfg_md_d(md_d), .cfg_cp_act(cp_act), .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token),
        .db_pos(db_pos), .db_job(db_job), .db_generation(db_gen), .cpl_position(cpl_pos), .cpl_job(cpl_job),
        .cpl_generation(cpl_gen), .launch_v(l_v), .launch_pc(l_pc), .launch_token(l_tok), .launch_pos(l_pos),
        .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy),
        .cpl_token(cpl_tok), .cpl_status(cpl_st), .cpl_cycles(cpl_cyc), .st_kernels(st_k), .st_busy(st_b));
    // a remote block: one station + a receiver of all 9 section-C words
    wire [9*32-1:0] act9;
    ot_hgi_cfg_stn u_st (.clk(clk), .rst_n(rst_n), .d(bus), .q(bus1));
    ot_hgi_cfg_rx #(.W0(40), .NW(9), .RST(HGI_RST_C)) u_rx9 (.clk(clk), .rst_n(rst_n), .bus(bus1), .act(act9));
    // legacy DS core in lockstep (same command writes with the window bit clear, same doorbells while no load)
    wire r_rdy, r_cv; wire [19:0] r_cpos, r_lpos; wire [31:0] r_cjob, r_lpc, r_ccyc, r_k, r_b; wire [3:0] r_cgen, r_cst;
    wire [NSM-1:0] r_lv; wire [16:0] r_ltok, r_ctok;
    ot_hfd_cmdproc20_m #(.ENABLE(1), .NSM(NSM), .RDREG(2)) ref_ (.clk(clk), .rst_n(rst_n), .cmd_we(cmd_we && !cmd_addr[8]),
        .cmd_addr(cmd_addr[7:0]), .cmd_wdata(cmd_wdata), .db_v(db_v), .db_rdy(r_rdy), .db_token(db_token[16:0]),
        .db_pos(db_pos), .db_job(db_job), .db_generation(db_gen), .cpl_position(r_cpos), .cpl_job(r_cjob),
        .cpl_generation(r_cgen), .launch_v(r_lv), .launch_pc(r_lpc), .launch_token(r_ltok), .launch_pos(r_lpos),
        .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data), .cpl_v(r_cv), .cpl_rdy(cpl_rdy),
        .cpl_token(r_ctok), .cpl_status(r_cst), .cpl_cycles(r_ccyc), .st_kernels(r_k), .st_busy(r_b));
    reg lockstep = 1; integer mism = 0, fails = 0, cyc = 0;
    always @(posedge clk) if (rst_n && lockstep) begin
        cyc = cyc + 1;
        if ({db_rdy, l_v, l_pc, l_tok, l_pos, cpl_v, cpl_tok, cpl_st, cpl_cyc, cpl_pos, cpl_job, cpl_gen, st_k, st_b} !==
            {r_rdy, r_lv, r_lpc, 1'b0, r_ltok, r_lpos, r_cv, 1'b0, r_ctok, r_cst, r_ccyc, r_cpos, r_cjob, r_cgen, r_k, r_b}) begin
            mism = mism + 1;
            if (mism < 5) $display("LOCKSTEP_MISMATCH cyc=%0d rdy %b/%b lv %h/%h cpl %b/%b tok %0d/%0d st %0d/%0d", cyc,
                                   db_rdy, r_rdy, l_v, r_lv, cpl_v, r_cv, cpl_tok, r_ctok, cpl_st, r_cst);
        end
    end
    task tick; begin @(posedge clk); #0.1; end endtask
    reg [31:0] cs [0:NCASE*REC-1];
    initial $readmemh("hgi_cfg_cases.mem", cs);
    // ---- one doorbell + an SM response that posts `res` as the result, returns the completion status
    integer k_;
    task run_job(input [17:0] tok, input [19:0] pos, input [31:0] res, input integer fault, output [3:0] status,
                 output [17:0] ctok);
        integer n;
        begin
            n = 0; while (!db_rdy && n < 1000) begin tick; n = n + 1; end
            if (!db_rdy) begin $display("FAIL db_rdy stuck"); fails = fails + 1; end
            db_token = tok; db_pos = pos; db_job = $random; db_gen = $random; db_v = 1; tick; db_v = 0;
            n = 0;
            while (!cpl_v && n < 200) begin
                if (|l_v) begin : resp
                    reg [NSM-1:0] m; m = l_v;
                    sm_done = 0; sm_fault = 0; res_v = 0;
                    repeat ($urandom % 4) tick;
                    if (fault) sm_fault = m & (~m + 1'b1);
                    else begin sm_done = {NSM{1'b1}}; res_v = 16'h0100; res_data[8*32 +: 32] = res; end
                    tick; sm_done = 0; sm_fault = 0; res_v = 0;
                end else tick;
                n = n + 1;
            end
            if (!cpl_v) begin $display("FAIL no completion"); fails = fails + 1; end
            status = cpl_st; ctok = cpl_tok;
            repeat ($urandom % 3) tick;
            cpl_rdy = 1; tick; cpl_rdy = 0;
        end
    endtask
    task load_list(input integer nk);
        integer j;
        begin
            for (j = 0; j < nk; j = j + 1) begin
                cmd_we = 1; cmd_addr = j; cmd_wdata = (64'd1 << 60) | (64'(($urandom % 65535) + 1) << 44) | $urandom; tick;
            end
            cmd_addr = nk; cmd_wdata = 64'd2 << 60; tick; cmd_we = 0;
        end
    endtask
    // ---- CF-0 case c: write the 32 pairs, commit, wait, check
    task cfg_case(input integer c);
        integer j, settle; reg [9*32-1:0] want; reg [3:0] want_err; reg hold_seen;
        begin
            for (j = 0; j < 32; j = j + 1) begin
                cmd_we = 1; cmd_addr = {1'b1, 3'd0, j[4:0]}; cmd_wdata = {cs[c*REC + 2*j + 1], cs[c*REC + 2*j]}; tick;
            end
            units_busy = cs[c*REC + 64][4];
            cmd_addr = 9'h1FF; cmd_wdata = 0; tick; cmd_we = 0;   // CFG_COMMIT
            settle = 0; hold_seen = 0;
            tick;
            while (dut.hold) begin
                hold_seen = 1; settle = settle + 1;
                if (db_rdy) begin $display("FAIL case %0d: doorbell accepted while the commit settles", c); fails = fails + 1; end
                tick;
            end
            units_busy = 0;
            repeat (4) tick;
            want_err = cs[c*REC + 64][3:0];
            for (j = 0; j < 9; j = j + 1) want[j*32 +: 32] = cs[c*REC + 65 + j];
            if (err !== want_err[2:0] || act9 !== want || cp_act !== want[63:0] ||
                (want_err == 0 && (settle < 64 + 9 || !loaded))) begin
                $display("FAIL cfg case %0d err %0d want %0d settle %0d loaded %b act_ok %b", c, err, want_err, settle, loaded,
                         act9 === want);
                fails = fails + 1;
            end else $display("CF0 case %0d err=%0d settle=%0d ok", c, err, settle);
        end
    endtask
    reg [3:0] s; reg [17:0] t; integer i, c;
    initial begin #4000000; $display("HGI_CMDPROC FAIL timeout cyc=%0d", cyc); $finish; end
    initial begin
        repeat (3) tick; rst_n = 1; tick;
        // ---- CF-1: lockstep against the legacy DS core before any load
        load_list(6);
        for (i = 0; i < 300; i = i + 1) begin
            run_job($urandom % 129280, $urandom % 1048576, (i % 17 == 0) ? 32'h0001_0000 + ($urandom % 63744) :
                    $urandom % 129280, (i % 23 == 5), s, t);
            if (i % 50 == 49) load_list(1 + $urandom % 8);
        end
        // DS reset vocab: 129279 accepted, 129280 refused (the legacy core accepts 129280: leave lockstep first)
        if (mism != 0) begin $display("FAIL CF-1 lockstep mismatches %0d over %0d cycles", mism, cyc); fails = fails + 1; end
        else $display("CF1 lockstep 300 jobs %0d cycles identical", cyc);
        lockstep = 0;
        run_job(129279, 20'hFFFFF, 129279, 0, s, t); if (s !== 0 || t !== 129279) begin $display("FAIL DS 129279"); fails = fails + 1; end
        run_job(129280, 0, 5, 0, s, t); if (s !== 3) begin $display("FAIL DS 129280 not refused"); fails = fails + 1; end
        // ---- CF-0 cases in order (Qwen loads leave Qwen active, errors keep the previous values)
        for (c = 0; c < NCASE; c = c + 1) begin
            cfg_case(c);
            if (c == 1) begin   // after the Qwen load: CF-CP
                run_job(131071, 40959, 131071, 0, s, t); if (s !== 0 || t !== 131071) begin $display("FAIL Q 131071"); fails = fails + 1; end
                run_job(131072, 0, 131072, 0, s, t); if (s !== 0 || t !== 131072) begin $display("FAIL Q 131072"); fails = fails + 1; end
                run_job(151935, 7, 151935, 0, s, t); if (s !== 0 || t !== 151935) begin $display("FAIL Q 151935"); fails = fails + 1; end
                run_job(151936, 7, 1, 0, s, t); if (s !== 3) begin $display("FAIL Q 151936 not refused"); fails = fails + 1; end
                run_job(5, 40960, 1, 0, s, t); if (s !== 3) begin $display("FAIL Q pos 40960 not refused"); fails = fails + 1; end
                run_job(5, 6, 151936, 0, s, t); if (s !== 3) begin $display("FAIL Q result 151936 not refused"); fails = fails + 1; end
            end
        end
        // last case = Qwen reload; reload DS and check the DS range again
        cfg_case(0);
        run_job(129280, 0, 5, 0, s, t); if (s !== 3) begin $display("FAIL DS reload 129280 not refused"); fails = fails + 1; end
        if (md_d[31:0] !== cs[0*REC + 56]) begin $display("FAIL section D entry_ar"); fails = fails + 1; end
        if (fails == 0) $display("HGI_CMDPROC PASS cf0_cases=%0d cf1_jobs=300 cf1_cycles=%0d", NCASE + 1, cyc);
        else $display("HGI_CMDPROC FAIL %0d", fails);
        $finish;
    end
endmodule
