`timescale 1ns/1ps
// Bench of ot_v41_rom_array (W10): tools/rtl_v41_rom_array.py writes, into +DIR=<dir>:
//   cfg.hex     one line per configuration write: {element[7:0], addr[3:0], data[47:0]} (60 bits)
//   stream.hex  one line per cycle from `go` + LEAD: {546-bit FP8/FP4 beat {v, p, b, sv, q0, e0, q1, e1},
//               1,064-bit BF16 beat {v, b, sv[3:0], u[4x8], d[4x256]}} (0 = idle); +BF selects the BF16 family
//   e<i>.viamap.hex   ROM via masks (loaded by the behavioural macro through +OT_ROM_DIR)
// +NROWS=<rows expected>.  The bench prints "ROW <row> <fp32> <bf16> <err> <cycle>" per finished row,
// then "DONE <cycles> <fault>".
module tb_v41_rom_array;
    parameter integer N = 4;
    parameter integer BF16 = 1;
    parameter integer XF = 4;
    localparam integer XBW = 546;
    localparam integer LEAD = 1;
    reg clk = 1'b0, rst_n = 1'b0;
    always #0.5 clk = ~clk;
    reg cfg_v = 1'b0, go = 1'b0;
    reg [7:0] cfg_e;
    reg [3:0] cfg_a;
    reg [47:0] cfg_d;
    reg [XBW-1:0] beat = '0;
    reg [1063:0] bbeat = '0;       // {v, b, sv, u[31:0], d[1023:0]}
    reg go_bf = 1'b0;
    wire r_v, r_e, busy, fault;
    wire [15:0] r_row, r_bf16;
    wire [31:0] r_fp32;
    ot_v41_rom_array #(.N(N), .BF16(BF16), .XF(XF)) dut (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_e(cfg_e), .cfg_a(cfg_a),
        .cfg_d(cfg_d), .go(go), .go_bf(go_bf), .xb_v(bbeat[1063]), .xb_b(bbeat[1062:1060]), .xb_sv(bbeat[1059:1056]),
        .xb_u(bbeat[1055:1024]), .xb_d(bbeat[1023:0]), .xs_v(beat[545]), .xs_p(beat[544:537]), .xs_b(beat[536:534]),
        .xs_sv(beat[533:532]), .xs_q0(beat[531:276]), .xs_e0(beat[275:266]), .xs_q1(beat[265:10]),
        .xs_e1(beat[9:0]), .r_v(r_v), .r_row(r_row), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e),
        .busy(busy), .fault(fault));
    reg [59:0] cfg [0:65535];
    reg [XBW+1064-1:0] stream [0:65535];
    reg [8*1024-1:0] dir;
    integer ncfg, nst, nrows, i, cyc, got, fd;
    reg trace;
    initial trace = $test$plusargs("TRACE");
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        if (!$value$plusargs("NROWS=%d", nrows)) $fatal(1, "+NROWS");
        if (!$value$plusargs("NCFG=%d", ncfg)) $fatal(1, "+NCFG");
        if (!$value$plusargs("NST=%d", nst)) $fatal(1, "+NST");
        $readmemh({dir, "/cfg.hex"}, cfg);
        $readmemh({dir, "/stream.hex"}, stream);
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        for (i = 0; i < ncfg; i = i + 1) begin
            @(negedge clk);
            cfg_v = 1'b1; {cfg_e, cfg_a, cfg_d} = cfg[i];
        end
        @(negedge clk);
        cfg_v = 1'b0;
        go = 1'b1;
        go_bf = $test$plusargs("BF");
        beat = '0;                      // the stream starts LEAD cycles after go
        cyc = 0; got = 0;
        for (cyc = 1; cyc < 200000 && got < nrows; cyc = cyc + 1) begin
            @(negedge clk);
            go = 1'b0;
            {beat, bbeat} = (cyc >= LEAD && cyc - LEAD < nst) ? stream[cyc - LEAD] : '0;
            if (trace && cyc < 400)
                $display("T %0d go=%0d xv=%0d | e0 hit=%0d iss=%0d fc=%0d run=%0d n_run=%0d np=%0d nb=%0d xs_p=%0d xs_b=%0d pv=%0d | l0=%0d c0=%0d tv=%0d",
                    cyc, dut.g_el[0].u_e.go, dut.g_el[0].u_e.xs_v, dut.g_el[0].u_e.hit, dut.g_el[0].u_e.issue,
                    dut.g_el[0].u_e.f_cnt, dut.g_el[0].u_e.w_run, dut.g_el[0].u_e.n_run, dut.g_el[0].u_e.n_pair,
                    dut.g_el[0].u_e.n_b, dut.g_el[0].u_e.xs_p, dut.g_el[0].u_e.xs_b, dut.g_el[0].u_e.pv,
                    dut.g_el[0].u_e.l0_v, dut.g_el[0].u_e.c0_v, dut.g_el[0].u_e.t_v);
            if (trace && dut.g_el[0].u_e.c0_v) $display("C0 %0d slot? %08h tag=%0h", cyc, dut.g_el[0].u_e.c0_s, dut.g_el[0].u_e.c0_t);
            if (trace && dut.g_el[0].u_e.b_v) $display("B0 %0d %08h tag=%0h", cyc, dut.g_el[0].u_e.b_val, dut.g_el[0].u_e.pr_t);
            if (trace && dut.g_el[0].u_e.pv) $display("P0 %0d %08h row=%0d", cyc, dut.g_el[0].u_e.pval, dut.g_el[0].u_e.prow);
            if (r_v) begin
                $display("ROW %0d %08h %04h %0d %0d", r_row, r_fp32, r_bf16, r_e, cyc - 1);
                got = got + 1;
            end
        end
        if (fault) $display("FAULTS elem=%b nodes=%b root=%b", dut.e_fault, dut.nf, dut.rf);
        $display("DONE %0d %0d", cyc - 1, fault);
        $finish;
    end
endmodule
