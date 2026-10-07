`timescale 1ns/1ps
`ifndef RDREG_B
`define RDREG_B 1
`endif
// Transaction-level exactness of ot_hfd_cmdproc20_m RDREG 1 (registered SRAM read word: +1 cycle per executed
// command) against the unchanged ot_ds_hbm_cmdproc20.  Each DUT sits in its own copy of one REACTIVE environment
// whose every decision is indexed by transaction count, not by cycle, so both see the same transaction stream:
//   * the same program image (random ops: launch with random / zero SM mask, completion, invalid op), and between
//     tokens (DUT idle, db_rdy) the same program rewrites, applied before the doorbell;
//   * doorbell k (token, position incl. out-of-range, job, generation) after gap[k] idle cycles;
//   * SM model: launch n -> result pulse res_v (from table n, optional) at launch + r[n], then sm_done of every
//     launched SM at launch + d[n] (r[n] < d[n]: an SM writes its result before it signals done), optional fault
//     on one launched SM at launch + f[n] < d[n];
//   * completion accepted (cpl_rdy) c[k] cycles after cpl_v.
// Compared (hash + count): every launch (launch_v, launch_pc, launch_token, launch_pos) and every completion
// (cpl_token, cpl_status, cpl_position, cpl_job, cpl_generation, st_kernels).  cpl_cycles / st_busy count cycles
// and differ by design (+1 per command).  `DUT_B selects the module of env b; `MUT_B builds b from a mutant copy.
module cpr_env #(parameter integer MARGIN = 0, parameter integer SEED = 1, parameter integer NTOK = 200)
    (input wire clk, output reg [63:0] lhash, output reg [63:0] chash, output integer nl, output integer nc, output reg done);
    localparam integer NSM = 16, NCMD = 256, TW = 17, PW = 20;
    reg rst_n = 0, cmd_we = 0, db_v = 0, cpl_rdy = 0; reg [7:0] cmd_addr = 0; reg [63:0] cmd_wdata = 0;
    reg [TW-1:0] db_token = 0; reg [PW-1:0] db_pos = 0; reg [31:0] db_job = 0; reg [3:0] db_gen = 0;
    reg [NSM-1:0] sm_done = 0, sm_fault = 0, res_v = 0; reg [NSM*32-1:0] res_data = 0;
    wire db_rdy, cpl_v; wire [PW-1:0] cpl_position, launch_pos; wire [31:0] cpl_job, launch_pc, cpl_cycles, st_kernels, st_busy;
    wire [3:0] cpl_generation, cpl_status; wire [NSM-1:0] launch_v; wire [TW-1:0] launch_token, cpl_token;
    `define CPR_PORTS .clk(clk), .rst_n(rst_n), .cmd_we(cmd_we), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata), .db_v(db_v), \
        .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(db_job), .db_generation(db_gen), \
        .cpl_position(cpl_position), .cpl_job(cpl_job), .cpl_generation(cpl_generation), .launch_v(launch_v), \
        .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos), .sm_done(sm_done), \
        .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy), .cpl_token(cpl_token), \
        .cpl_status(cpl_status), .cpl_cycles(cpl_cycles), .st_kernels(st_kernels), .st_busy(st_busy)
    generate if (MARGIN) begin : g_m
        `DUT_B #(.ENABLE(1), .NSM(NSM), .NCMD(NCMD), .RDREG(`RDREG_B)) dut (`CPR_PORTS);
    end else begin : g_o
        ot_ds_hbm_cmdproc20 #(.ENABLE(1), .NSM(NSM), .NCMD(NCMD)) dut (`CPR_PORTS);
    end endgenerate
    // deterministic per-index tables (same in both environments)
    function automatic [31:0] h(input integer a, input integer b);
        reg [63:0] x; begin x = {32'(a), 32'(b)} ^ (64'h9E3779B97F4A7C15 * (SEED + 1));
            x = x ^ (x >> 31); x = x * 64'hBF58476D1CE4E5B9; x = x ^ (x >> 29); x = x * 64'h94D049BB133111EB; h = x[31:0] ^ x[63:32]; end
    endfunction
    function automatic [63:0] word(input integer a, input integer gen);
        reg [3:0] op; reg [NSM-1:0] m; begin
            op = (h(a, gen + 1) % 6 == 0) ? 4'd2 : ((h(a, gen + 2) % 23 == 0) ? 4'd7 : 4'd1);
            m = h(a, gen + 3); if (h(a, gen + 4) % 11 == 0) m = 0; else if (h(a, gen + 5) % 3 == 0) m = 1 << (h(a, gen + 6) % NSM);
            word = {op, m, 12'd0, h(a, gen + 7)};
        end
    endfunction
    integer i, k, cyc, nlaunch;
    // SM model: per launch n, a schedule relative to the launch cycle
    reg [NSM-1:0] l_mask [0:4095]; integer l_t [0:4095]; integer pend_lo = 0; integer si, sk;   // the SM model's own loop variables (the driver owns i / k)
    always @(posedge clk) begin
        sm_done <= 0; sm_fault <= 0; res_v <= 0;
        if (rst_n) begin
            if (launch_v != 0) begin
                l_mask[nlaunch % 4096] <= launch_v; l_t[nlaunch % 4096] <= cyc; nlaunch <= nlaunch + 1;
                lhash <= (lhash ^ {launch_v, launch_pc, 16'(launch_token)}) * 64'h100000001B3 + {44'd0, launch_pos};
                nl <= nl + 1;
            end
            for (si = pend_lo; si < nlaunch; si = si + 1) begin
                // r < f < d (relative cycles), all >= 1
                if (cyc == l_t[si % 4096] + 1 + (h(si, 101) % 6) && h(si, 102) % 3 != 0) begin
                    res_v <= 1 << (h(si, 103) % NSM);
                    for (sk = 0; sk < NSM; sk = sk + 1) res_data[sk*32 +: 32] <= (h(si, 104) % 4 == 0) ? h(si, 105 + sk) : (h(si, 105 + sk) % 131072);
                end
                // a faulting launch: one launched SM faults and no SM of it signals done
                if (cyc == l_t[si % 4096] + 8 + (h(si, 106) % 4) && h(si, 107) % 97 == 0)
                    sm_fault <= l_mask[si % 4096] & (~l_mask[si % 4096] + 1'b1);
                if (cyc == l_t[si % 4096] + 13 + (h(si, 108) % 40) && h(si, 107) % 97 != 0) sm_done <= l_mask[si % 4096];
            end
            while (pend_lo < nlaunch && cyc > l_t[pend_lo % 4096] + 64) pend_lo = pend_lo + 1;
        end
    end
    // completion log
    integer ncpl_seen = 0, crdy_at = -1;
    always @(posedge clk) if (rst_n && cpl_v && cpl_rdy) begin
        chash <= (chash ^ {cpl_token, cpl_status, cpl_generation, 3'd0, cpl_job}) * 64'h100000001B3 + {cpl_position, st_kernels};
        nc <= nc + 1;
    end
    // driver: program image, then per token: idle rewrites, doorbell after a gap, completion acceptance after a delay
    initial begin
        lhash = 0; chash = 0; nl = 0; nc = 0; done = 0; nlaunch = 0; cyc = 0;
        repeat (3) @(posedge clk);
        for (i = 0; i < NCMD; i = i + 1) begin @(negedge clk); cmd_we = 1; cmd_addr = i; cmd_wdata = word(i, 0); end
        @(negedge clk); cmd_we = 0; rst_n = 1;
        for (k = 0; k < NTOK; k = k + 1) begin
            while (!db_rdy) @(negedge clk);
            for (i = 0; i < (h(k, 1) % 5); i = i + 1) begin
                @(negedge clk); cmd_we = 1; cmd_addr = (h(k, 10 + i) % 2) ? (h(k, 20 + i) % 16) : h(k, 20 + i); cmd_wdata = word(h(k, 30 + i), k + 1);
            end
            @(negedge clk); cmd_we = 0;
            repeat (h(k, 2) % 4) @(negedge clk);
            db_v = 1; db_token = h(k, 3); db_pos = (h(k, 4) % 40 == 0) ? 20'hFFFFF : h(k, 5) % 1000; db_job = h(k, 6); db_gen = h(k, 7);
            @(negedge clk); db_v = 0;          // idle (db_rdy) at the posedge in between: accepted there
            while (!cpl_v) @(negedge clk);
            repeat (h(k, 8) % 4) @(negedge clk);
            cpl_rdy = 1; @(negedge clk); cpl_rdy = 0;
        end
        repeat (4) @(negedge clk);
        done = 1;
    end
    always @(posedge clk) cyc <= cyc + 1;
endmodule

module tb_cmdproc_rd_equiv;
    reg clk = 0; always #0.5 clk = ~clk;
    wire [63:0] la, ca, lb, cb; integer nla, nca, nlb, ncb; wire da, db;
    cpr_env #(.MARGIN(0), .SEED(`SEED), .NTOK(`NTOK)) a (.clk(clk), .lhash(la), .chash(ca), .nl(nla), .nc(nca), .done(da));
    cpr_env #(.MARGIN(1), .SEED(`SEED), .NTOK(`NTOK)) b (.clk(clk), .lhash(lb), .chash(cb), .nl(nlb), .nc(ncb), .done(db));
    integer t = 0;
    always @(posedge clk) begin
        t <= t + 1;
        if ((da && db) || t > 5000000) begin
            $display("CPR_EQUIV seed=%0d launches=%0d/%0d completions=%0d/%0d launch_hash=%s cpl_hash=%s",
                     `SEED, nla, nlb, nca, ncb, (la === lb) ? "MATCH" : "DIFF", (ca === cb) ? "MATCH" : "DIFF");
            if (!(da && db) || la !== lb || ca !== cb || nla != nlb || nca != ncb || nla == 0 || nca == 0) $fatal(1, "FAIL");
            $finish;
        end
    end
endmodule
