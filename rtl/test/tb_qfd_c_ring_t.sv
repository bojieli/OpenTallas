`timescale 1ns/1ps
// QW-CB16REG 10-20: bench of the hardened landing ring tiles qfd_c_ringx516 / qfd_c_ringx514 (+define+M_RING514), each
// followed by its closed output station qfd_c_stn516 / qfd_c_stn514 on ck_r (the reader's output register).
// Every output bit every cycle is checked against (1) its cycle model: o(e) = i(e - 2) once warm (D 4, K 2 static
// schedule; 0 before warm-up) and (2) the soft pair it replaces (qfd_c_land_w1k + qfd_c_land_r1k, lockstep from reset).
// Random data, two resets mid-run.  Prints RING_BENCH PASS|FAIL <master> <errors> errors in <N> cycles.
module tb;
`ifdef M_RING514
    localparam integer W = 514; localparam string M = "qfd_c_ringx514";
`else
    localparam integer W = 516; localparam string M = "qfd_c_ringx516";
`endif
    reg ck = 0, rsi = 0;
    reg [W-1:0] i = 0;
    wire [W-1:0] o, o_sel, o_ref;
    always #1 ck = ~ck;
`ifdef M_RING514
    qfd_c_ringx514 dut (.ck_w(ck), .rsi_w(rsi), .i(i), .ck_r(ck), .rsi_r(rsi), .o(o_sel));
    qfd_c_stn514 dut_stn (.ck(ck), .d(o_sel), .q(o));
`else
    qfd_c_ringx516 dut (.ck_w(ck), .rsi_w(rsi), .i(i), .ck_r(ck), .rsi_r(rsi), .o(o_sel));
    qfd_c_stn516 dut_stn (.ck(ck), .d(o_sel), .q(o));
`endif
    localparam integer NGS = (W + 29) / 30;
    wire [4*W-1:0] bank; wire [11:0] epo; wire [4*NGS-1:0] vld;
    qfd_c_land_w1k #(.W(W), .D(4)) rw (.ck(ck), .rsi(rsi), .i(i), .bank(bank), .epo(epo), .vld(vld));
    qfd_c_land_r1k #(.W(W), .D(4), .K(2)) rr (.ck(ck), .rsi(rsi), .bank(bank), .epo(epo), .vld(vld), .o(o_ref));
    integer n, N, err = 0, warm = 0, j;
    reg [W-1:0] h1 = 0, h2 = 0;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 20000;
        for (n = 0; n < N; n = n + 1) begin
            @(negedge ck);
            if (warm > 6 && o !== h2) begin
                if (err < 10) $display("RING_BENCH MISMATCH cycle %0d model", n);
                err = err + 1;
            end
            if (o !== o_ref) begin
                if (err < 10) $display("RING_BENCH MISMATCH cycle %0d soft pair", n);
                err = err + 1;
            end
            h2 = h1; h1 = i;
            rsi = !((n % 7000) < 5);
            warm = rsi ? warm + 1 : 0;
            for (j = 0; j < W; j = j + 32) i[j +: 32] = $urandom;
        end
        if (err == 0) $display("RING_BENCH PASS %s 0 errors in %0d cycles", M, N);
        else $display("RING_BENCH FAIL %s %0d errors in %0d cycles", M, err, N);
        $finish;
    end
endmodule
