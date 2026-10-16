`timescale 1ns/1ps
`default_nettype none
// tb_hbm_smh_attn: SM-ELEMENT attention bench (H-SM-ATT r2 2026-10-15).  The DUT is the whole static SM with attention
// (ot_hbm_accel_smh_attn: 8 columns x 4 leaves, real XS / tcl / tct / pass-through / BE arithmetic and transport, KV
// converter, probability store, descriptor).  The testbench only PLAYS a precompiled per-cycle calendar written by
// tools/hbm_sm_attention/sm_elem_bench.py (the compiler): 192-bit command, KV line packet (declared external stimulus at
// the SM's staging-buffer boundary), x-loader beat and 64-bit KV_DESC word for every cycle.  It never reacts to the DUT:
// no ready, no wait.  It prints every result row (rv / rrow / rdata) with its cycle and stops on the first fault or
// schedule_fault (sticky in the DUT).  Results are compared bit for bit by the compiler script against the golden.
// plusargs: +CMD= +PKT= +XW= +KVD= (hex, one line per cycle) +N=<cycles>
module tb_hbm_smh_attn;
    parameter integer MAXC = 4096;
    parameter integer DMUT = 0;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [191:0]  cmd_m [0:MAXC-1];
    reg [1098:0] pkt_m [0:MAXC-1];
    reg [2062:0] xw_m  [0:MAXC-1];          // {en, addr7, grp7, data2048}
    reg [63:0]   kvd_m [0:MAXC-1];
    reg [191:0] command = 0; reg [1098:0] packet = 0; reg [63:0] kv_desc = 0;
    reg xw_en = 0; reg [6:0] xw_addr = 0, xw_grp = 0; reg [2047:0] xw_data = 0;
    wire [42:0] request; wire rv, fault, sfault; wire [11:0] rrow; wire [255:0] rdata;
    ot_hbm_accel_smh_attn #(.KVMUT(DMUT)) u_dut (.clk(clk), .rst_n(rst_n), .command(command), .kv_desc(kv_desc), .packet(packet),
        .request(request), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data),
        .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault), .schedule_fault(sfault));
    integer n, cyc, k, nres = 0;
    string fc, fp, fx, fk;
    always @(posedge clk) if (rst_n) begin
        if (rv) begin $display("R %0d %03h %064h", cyc, rrow, rdata); nres = nres + 1; end
        if (sfault) begin $display("FAULT schedule cycle %0d", cyc); $fatal(1, "schedule_fault"); end
        if (fault) begin $display("FAULT arithmetic cycle %0d", cyc); $fatal(1, "fault"); end
    end
`ifdef PROBE
    // latency probe (compiler calibration only, never a qualifying run): BE score landings and gather-lane valids
    genvar pc;
    generate for (pc = 0; pc < 8; pc = pc + 1) begin : g_probe
        reg [15:0] sv_q = 0;
        always @(posedge clk) if (rst_n) begin
            if (u_dut.g_c[pc].u_be.score_valid != sv_q) $display("S %0d %0d %04h", cyc, pc, u_dut.g_c[pc].u_be.score_valid);
            sv_q <= u_dut.g_c[pc].u_be.score_valid;
            if (u_dut.g_c[pc].u_be.tv_in) $display("G %0d %0d", cyc, pc);
            if (u_dut.g_c[pc].u_be.kv) $display("K %0d %0d %03h %08h", cyc, pc, u_dut.g_c[pc].u_be.krow, u_dut.g_c[pc].u_be.ky);
        end
    end endgenerate
`endif
    initial begin
        if (!$value$plusargs("CMD=%s", fc) || !$value$plusargs("PKT=%s", fp) || !$value$plusargs("XW=%s", fx) ||
            !$value$plusargs("KVD=%s", fk) || !$value$plusargs("N=%d", n)) $fatal(1, "plusargs");
        if (n > MAXC) $fatal(1, "calendar longer than MAXC");
        $readmemh(fc, cmd_m, 0, n - 1); $readmemh(fp, pkt_m, 0, n - 1); $readmemh(fx, xw_m, 0, n - 1); $readmemh(fk, kvd_m, 0, n - 1);
        repeat (4) @(posedge clk); rst_n <= 1;
        repeat (4) @(posedge clk);
        for (cyc = 0; cyc < n; cyc = cyc + 1) begin
            command <= cmd_m[cyc]; packet <= pkt_m[cyc]; kv_desc <= kvd_m[cyc];
            {xw_en, xw_addr, xw_grp, xw_data} <= xw_m[cyc];
            @(posedge clk);
        end
        command <= 0; packet <= 0; xw_en <= 0; kv_desc <= 0;
        repeat (8) @(posedge clk);
        $display("DONE cycles=%0d results=%0d", n, nres);
        $finish;
    end
endmodule
`default_nettype wire
