`timescale 1ps/1fs
// KV-PC 2026-10-19: qkd_kvpc_s_tq (tag queue in two native 32 x 64 banks, registered reads at the pointers' next values,
// write bypass) vs the scheduler's flop array tq[0:63] read asynchronously at tr and tr + 1.  Random writes (any entry,
// including the entries being read: the bypass), random pointer advances and resets of the pointer, every edge both
// heads compared exactly.  +define+KVPC_MUT=1 drops the bypass (must FAIL).
`ifndef KVPC_MUT
`define KVPC_MUT 0
`endif
module tb_kvpc_tq;
    reg clk = 0;
    always #512 clk = ~clk;
    reg [33:0] tq [0:63];
    reg we, adv, clr;
    reg [5:0] wa, tr;
    reg [33:0] wd;
    wire [5:0] a0_next = clr ? 6'd0 : adv ? tr + 1'b1 : tr;
    wire [33:0] h0, h1;
    qkd_kvpc_s_tq #(.TQD(64), .MUT(`KVPC_MUT)) u_dut (.clk(clk), .we(we), .wa(wa), .wd(wd), .a0_next(a0_next),
        .h0(h0), .h1(h1));
    integer bad, chk, byp, seed, edges, t, k;
    always @(posedge clk) begin
        if (we) tq[wa] <= wd;
        tr <= a0_next;
    end
    always @(negedge clk) begin
        if (t > 2) begin
            chk = chk + 1;
            if (h0 !== tq[tr] || h1 !== tq[tr + 6'd1]) begin
                bad = bad + 1;
                if (bad < 10) $display("MISMATCH t=%0d tr=%0d h0 %h/%h h1 %h/%h", t, tr, tq[tr], h0, tq[tr + 6'd1], h1);
            end
        end
        we <= ($urandom % 100) < 60;
        wa <= (($urandom % 4) == 0) ? a0_next_guess(0) : (($urandom % 4) == 0) ? a0_next_guess(1) : $urandom;
        wd <= {$urandom, $urandom};
        adv <= ($urandom % 100) < 50;
        clr <= ($urandom % 500) == 0;
    end
    function [5:0] a0_next_guess(input integer o); begin a0_next_guess = tr + 6'(o) + (($urandom % 2) ? 6'd1 : 6'd0); end
    endfunction
    always @(posedge clk) if (we && (wa == a0_next || wa == a0_next + 6'd1)) byp = byp + 1;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("edges=%d", edges)) edges = 50000;
        k = $urandom(seed);
        bad = 0; chk = 0; byp = 0; t = 0; tr = 0; we = 0; wa = 0; wd = 0; adv = 0; clr = 0;
        for (k = 0; k < 64; k = k + 1) tq[k] = 34'd0;      // the macro model powers up zero (OT_MEM_NO_INIT unset)
        for (t = 0; t < edges; t = t + 1) @(negedge clk);
        if (bad == 0 && byp > 1000)
            $display("KVPC_TQ PASS edges=%0d checks=%0d bypassed=%0d errors=0 mut=%0d", edges, chk, byp, `KVPC_MUT);
        else
            $display("KVPC_TQ FAIL edges=%0d checks=%0d errors=%0d bypassed=%0d mut=%0d", edges, chk, bad, byp, `KVPC_MUT);
        $finish;
    end
endmodule
