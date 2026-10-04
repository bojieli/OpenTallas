`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Unit bench of ot_gpu_cmdproc: behavioural SMs answer launches after random
// delays; checks stream order (no kernel launches before every SM of the
// previous one is done), launch PC/token/position, the completion payload
// (latest RESULT), the no-result, fault-abort and bad-command statuses, and
// that an ENABLE=0 instance drives every output 0.  Icarus or Verilator.
// ---------------------------------------------------------------------------
module tb_gpu_cmdproc_unit;
    localparam integer NSM = 3;
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg cmd_we = 0; reg [7:0] cmd_addr = 0; reg [63:0] cmd_wdata = 0;
    reg db_v = 0; reg [15:0] db_token = 0, db_pos = 0;
    wire db_rdy; wire [NSM-1:0] launch_v; wire [31:0] launch_pc; wire [15:0] launch_token, launch_pos;
    reg [NSM-1:0] sm_done = 0, sm_fault = 0, res_v = 0; reg [NSM*32-1:0] res_data = 0;
    wire cpl_v; reg cpl_rdy = 1; wire [15:0] cpl_token; wire [3:0] cpl_status; wire [31:0] cpl_cycles, st_k, st_b;
    ot_gpu_cmdproc #(.ENABLE(1), .NSM(NSM), .NCMD(256)) dut (.clk(clk), .rst_n(rst_n), .cmd_we(cmd_we), .cmd_addr(cmd_addr),
        .cmd_wdata(cmd_wdata), .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .launch_v(launch_v),
        .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos), .sm_done(sm_done), .sm_fault(sm_fault),
        .res_v(res_v), .res_data(res_data), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy), .cpl_token(cpl_token), .cpl_status(cpl_status),
        .cpl_cycles(cpl_cycles), .st_kernels(st_k), .st_busy(st_b));
    // ENABLE = 0 instance
    wire db_rdy0, cpl_v0; wire [NSM-1:0] lv0; wire [31:0] pc0, cy0, k0, b0; wire [15:0] t0, p0, ct0; wire [3:0] cs0;
    ot_gpu_cmdproc #(.ENABLE(0), .NSM(NSM)) off (.clk(clk), .rst_n(rst_n), .cmd_we(cmd_we), .cmd_addr(cmd_addr),
        .cmd_wdata(cmd_wdata), .db_v(db_v), .db_rdy(db_rdy0), .db_token(db_token), .db_pos(db_pos), .launch_v(lv0),
        .launch_pc(pc0), .launch_token(t0), .launch_pos(p0), .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v),
        .res_data(res_data), .cpl_v(cpl_v0), .cpl_rdy(cpl_rdy), .cpl_token(ct0), .cpl_status(cs0), .cpl_cycles(cy0),
        .st_kernels(k0), .st_busy(b0));

    integer fails = 0, i, k, nk;
    reg [NSM-1:0] running = 0;
    reg clear_stubs = 0;
    integer due [0:NSM-1];
    reg [31:0] seen_pc [0:63];
    reg [NSM-1:0] seen_mask [0:63];
    integer nseen = 0, cyc = 0, fault_at = -1, result_at = -1;
    reg [31:0] result_val;
    always @(posedge clk) cyc <= cyc + 1;
    // behavioural SMs
    always @(posedge clk) begin
        sm_done <= 0; res_v <= 0;
        if (clear_stubs) begin running <= 0; sm_fault <= 0; end else begin
        if (|(launch_v & running)) begin $display("FAIL launch to a running SM"); fails = fails + 1; end
        if (launch_v != 0) begin
            if (running != 0) begin $display("FAIL stream order: launch while SMs still run"); fails = fails + 1; end
            seen_pc[nseen] = launch_pc; seen_mask[nseen] = launch_v; nseen = nseen + 1;
            if (launch_token !== db_token || launch_pos !== db_pos) begin $display("FAIL launch params"); fails = fails + 1; end
        end
        for (i = 0; i < NSM; i = i + 1) begin
            if (launch_v[i]) begin running[i] <= 1; due[i] = cyc + 5 + ($urandom % 200); end
            else if (running[i] && cyc >= due[i]) begin
                if (fault_at == nseen - 1 && i == 1) sm_fault[i] <= 1;
                else begin
                    if (result_at == nseen - 1 && i == 0) begin res_v[0] <= 1; res_data[31:0] <= result_val; end
                    sm_done[i] <= 1; running[i] <= 0;
                end
            end
        end
        end
    end
    task automatic load_cmds(input integer n, input integer bad);
        for (k = 0; k < n; k = k + 1) begin
            @(negedge clk); cmd_we = 1; cmd_addr = k;
            cmd_wdata = (64'd1 << 60) | (64'(((k % 3) == 2) ? 3'b101 : 3'b111) << 44) | (64'h100 * k + 7);
        end
        @(negedge clk); cmd_addr = n; cmd_wdata = bad ? (64'd9 << 60) : (64'd2 << 60);
        @(negedge clk); cmd_we = 0;
    endtask
    task automatic step(input [15:0] tok, input [15:0] pos, input [3:0] want_status, input [15:0] want_tok,
                        input integer want_k);
        nseen = 0;
        @(negedge clk); db_v = 1; db_token = tok; db_pos = pos;
        while (!db_rdy) @(negedge clk);
        @(negedge clk); db_v = 0;
        while (!cpl_v) @(posedge clk);
        if (cpl_status !== want_status || (want_status == 0 && cpl_token !== want_tok) || (want_k >= 0 && nseen != want_k)) begin
            $display("FAIL step tok %0d: status %0d token %0d kernels %0d (want %0d %0d %0d)", tok, cpl_status, cpl_token,
                     nseen, want_status, want_tok, want_k);
            fails = fails + 1;
        end else $display("PASS step tok %0d status %0d token %0d kernels %0d cycles %0d", tok, cpl_status, cpl_token,
                          nseen, cpl_cycles);
        for (k = 0; k < nseen && want_status == 0; k = k + 1)
            if (seen_pc[k] !== 32'h100 * k + 7 || seen_mask[k] !== (((k % 3) == 2) ? 3'b101 : 3'b111)) begin
                $display("FAIL kernel %0d pc %h mask %b", k, seen_pc[k], seen_mask[k]); fails = fails + 1;
            end
        @(posedge clk);
    endtask
    initial begin
        #5 rst_n = 1;
        load_cmds(7, 0);
        result_val = 32'h0001_0457; result_at = 6;
        step(16'd11, 16'd3, 4'd0, 16'h0457, 7);
        result_val = 32'h0000_1111; result_at = 2;
        step(16'd12, 16'd4, 4'd0, 16'h1111, 7);
        result_at = -1;
        step(16'd13, 16'd5, 4'd2, 16'd0, 7);                 // no RESULT posted
        fault_at = 3; result_at = 6;
        step(16'd14, 16'd6, 4'd1, 16'd0, -1);                // SM fault aborts
        fault_at = -1; clear_stubs = 1;
        repeat (3) @(posedge clk);
        clear_stubs = 0;
        repeat (20) @(posedge clk);
        load_cmds(2, 1);
        step(16'd15, 16'd7, 4'd3, 16'd0, 2);                 // bad command
        if (db_rdy0 || cpl_v0 || lv0 != 0 || pc0 != 0 || ct0 != 0 || cs0 != 0 || cy0 != 0) begin
            $display("FAIL ENABLE=0 instance drives a nonzero output"); fails = fails + 1;
        end else $display("PASS ENABLE=0 outputs all 0");
        $display("TB_GPU_CMDPROC_UNIT %s fails=%0d kernels_counter=%0d", fails ? "FAIL" : "PASS", fails, st_k);
        $finish;
    end
endmodule
