`timescale 1ns/1ps
// tb_s81_retn_static: cycle-exact bench of ot_s81_retn_static against tools/s81/static_return_calendar.py (the
// compiler model).  Every edge's input word comes from stim.hex; every edge's output (valid, tag, data, err) must equal
// expect.hex, including the empty edges; the final sticky fault must equal FAULT (0 for a legal schedule, 1 for the
// deliberate collision).  +DIR=<vector dir> +T=<edges> +FAULT=<0|1>
module tb_s81_retn_static;
    parameter integer WIN = 2, RST = 1, MUT = 0;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg a_v, b_v, a_e, b_e; reg [31:0] a_t, a_d, b_t, b_d;
    wire o_v, o_e, fault; wire [31:0] o_t, o_d;
    ot_s81_retn_static #(.WIN(WIN), .RST(RST), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n),
        .a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e), .b_v(b_v), .b_t(b_t), .b_d(b_d), .b_e(b_e),
        .o_v(o_v), .o_t(o_t), .o_d(o_d), .o_e(o_e), .fault(fault));
    integer fs, fe, T, n, bad, words, xf, r;
    reg [1023:0] dir;
    integer iav, iae, ibv, ibe, ev, ee; reg [31:0] iat, iad, ibt, ibd, et, ed;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        if (!$value$plusargs("T=%d", T)) $fatal(1, "+T");
        if (!$value$plusargs("FAULT=%d", xf)) $fatal(1, "+FAULT");
        fs = $fopen({dir, "/stim.hex"}, "r"); fe = $fopen({dir, "/expect.hex"}, "r");
        if (fs == 0 || fe == 0) $fatal(1, "vector files");
        a_v = 0; b_v = 0; a_t = 0; a_d = 0; a_e = 0; b_t = 0; b_d = 0; b_e = 0;
        bad = 0; words = 0;
        // edge numbering: edge 0 is the first rising edge after reset release (the model's edge 0)
        repeat (3) @(posedge clk);
        #0.1 rst_n = 1;
        for (n = 0; n < T; n = n + 1) begin
            r = $fscanf(fs, "%d %h %h %d %d %h %h %d\n", iav, iat, iad, iae, ibv, ibt, ibd, ibe);
            r = $fscanf(fe, "%d %h %h %d\n", ev, et, ed, ee);
            a_v = iav; a_t = iat; a_d = iad; a_e = iae; b_v = ibv; b_t = ibt; b_d = ibd; b_e = ibe;
            @(posedge clk);   // edge n samples the inputs above and the output visible before it
            if (ev != 2 && (o_v !== ev[0] || (ev && (o_t !== et || o_d !== ed || o_e !== ee[0])))) begin
                bad = bad + 1;
                if (bad < 8) $display("RETN_STATIC mismatch edge %0d: got v%b t%h d%h e%b want v%0d t%h d%h e%0d",
                                      n, o_v, o_t, o_d, o_e, ev, et, ed, ee);
            end
            if (ev == 1) words = words + 1;
            #0.1;
        end
        if (fault !== xf[0]) begin bad = bad + 1; $display("RETN_STATIC fault %b want %0d", fault, xf); end
        if (bad) begin $display("RETN_STATIC FAIL %0d mismatches", bad); $fatal(1); end
        $display("RETN_STATIC PASS %0d edges %0d output words exact (WIN %0d RST %0d, fault %0d as compiled)", T, words, WIN, RST, xf);
        $finish;
    end
endmodule
