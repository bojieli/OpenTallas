`timescale 1ns/1ps
// qwen-rtl-finish 2026-10-07: the embedding ROM root / column adapter (ot_qfd_io_embedding_rom: root + columns of taps +
// banks with the bank parents' protocol) against the reference ROM semantics (ot_qwen_rt_embed_rom: code word a, row
// scale r), in order: random request streams under the die-side credits -- token rows (64 consecutive code words of one
// bank + its scale), random single words, random scales -- every response compared with the ROM content of its request.
// MUT = 1 (one bank off in the root decode): must FAIL.
module tb_qfd_embedding_rom;
    parameter integer NCOL = 3, NTAP = 4, NCODE = 10, NSCALE = 2, LWB = 6, LSB = 8, CRD = 4, MUT = 0, PINREG = 0, NREQ = 6000, SEED = 9;
    localparam integer AW = 24;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg ea_v, ea_kind; reg [AW-1:0] ea_addr;
    wire ea_cr, eq_v, fault; wire [511:0] eq_data;
    ot_qfd_io_embedding_rom #(.AW(AW), .NCOL(NCOL), .NTAP(NTAP), .NCODE(NCODE), .NSCALE(NSCALE), .LWB(LWB), .LSB(LSB),
        .CRD(CRD), .MUT(MUT), .PINREG(PINREG)) dut (.clk(clk), .rst_n(rst_n), .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr),
        .ea_cr(ea_cr), .eq_v(eq_v), .eq_data(eq_data), .fault(fault));
    // the reference ROM content (as the banks are filled)
    function automatic [511:0] word(input [31:0] a);
        integer k; reg [31:0] h;
        begin
            for (k = 0; k < 16; k = k + 1) begin
                h = (a * 32'h9E3779B1) ^ (k * 32'h85EBCA6B); h = h ^ (h >> 15); h = h * 32'h2C1B3C6D; word[32*k +: 32] = h ^ (h >> 12);
            end
        end
    endfunction
    function automatic [511:0] expect_of(input k, input [AW-1:0] a);
        expect_of = k ? {496'd0, word(32'h8000_0000 | a)[15:0]} : word(a);
    endfunction
    reg [AW:0] exq [0:8191];
    integer wq, rq, credits, sent, got, bad, cyc, i, tok_left, kind_now;
    reg [AW-1:0] next_a;
    integer seed;
    always @(posedge clk) if (rst_n) begin
        if (eq_v) begin
            if (eq_data !== expect_of(exq[rq % 8192][AW], exq[rq % 8192][AW-1:0])) begin bad = bad + 1; `ifdef DBG if (bad < 4) $display("%0t BAD rq=%0d k=%0d a=%0d sent=%0d", $time, rq, exq[rq % 8192][AW], exq[rq % 8192][AW-1:0], sent); `endif end
            rq = rq + 1; got = got + 1;
        end
        if (ea_cr) credits = credits + 1;
    end
`ifdef DBG
    always @(posedge clk) if (rst_n && $time < 400) begin
        if (ea_v) $display("%0t REQ k=%0d a=%0d", $time, ea_kind, ea_addr);
        if (|dut.u_root.c_v) $display("%0t ISSUE cv=%b tap=%0d line=%0d", $time, dut.u_root.c_v, dut.u_root.c_tap, dut.u_root.c_line);
        if (eq_v) $display("%0t RSP", $time);
    end
`endif
    initial begin
        seed = SEED; wq = 0; rq = 0; credits = CRD; sent = 0; got = 0; bad = 0; tok_left = 0;
        ea_v = 0; ea_kind = 0; ea_addr = 0;
        repeat (4) @(negedge clk); rst_n = 1;
        for (cyc = 0; cyc < 400000 && sent < NREQ; cyc = cyc + 1) begin
            @(negedge clk);
            ea_v = 0;
            if (credits > 0 && ($random(seed) & 3) != 0) begin
                if (tok_left == 0) begin
                    case ($random(seed) & 3)
                        0, 1: begin tok_left = 65; next_a = (($random(seed) & 32'h7fffffff) % (NCODE << LWB)) & ~63; end
                        2: begin ea_kind = 0; ea_addr = ($random(seed) & 32'h7fffffff) % (NCODE << LWB); ea_v = 1; end
                        3: begin ea_kind = 1; ea_addr = ($random(seed) & 32'h7fffffff) % (NSCALE << LSB); ea_v = 1; end
                    endcase
                end
                if (tok_left > 1) begin ea_kind = 0; ea_addr = next_a; next_a = next_a + 1; tok_left = tok_left - 1; ea_v = 1; end
                else if (tok_left == 1) begin ea_kind = 1; ea_addr = (next_a >> 6) % (NSCALE << LSB); tok_left = 0; ea_v = 1; end
                if (ea_v) begin exq[wq % 8192] = {ea_kind, ea_addr}; wq = wq + 1; credits = credits - 1; sent = sent + 1; end
            end
        end
        @(negedge clk); ea_v = 0;
        repeat (3000) @(negedge clk);
        if (bad == 0 && got == sent && !fault && sent == NREQ)
            $display("PASS qfd_embedding_rom NCOL=%0d NTAP=%0d PINREG=%0d requests=%0d responses=%0d cycles=%0d", NCOL, NTAP, PINREG, sent, got, cyc);
        else
            $display("FAIL qfd_embedding_rom mismatches=%0d sent=%0d got=%0d fault=%0d", bad, sent, got, fault);
        $finish;
    end
endmodule
