`timescale 1ns/1ps
// s81-svceng-1011: Engram BOOT gate of the stack HBM client: one home die (tb_eng_be_die: eng_SE core + SE half,
// svc_SW's half on relay-delayed narrow pairs, 64 PC models) boots an EXPECT-sector image through the host face
// (aperture CSR words, then the image, then the END marker).  PASS = both halves READY, no fault, every sector at the
// PC / global sector the canonical rowstripe map assigns (stack (n / 9) % 2, PC (n / 18) % 32, global inverse(PC,
// base + n % 9) for the first 64 rows) with its data, host acks = sectors + CSR words.  HMUT 1 (a sector corrupted
// after the fingerprint) must FAIL (the dispatcher's END check).
module tb_eng_be_boot #(parameter integer EXPECT = 576, HMUT = 0, D = 12);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0; integer cyc = 0;
    always @(posedge clk) begin cyc <= cyc + 1; if (cyc == 8) rst_n <= 1; end
    wire [31:0] acks, sent; wire booted, swf; wire [8:0] cd; wire [1:0] cs; wire [281:0] tag_; wire [3:0] tair; wire [531:0] tvm; wire [0:0] tc;
    tb_eng_be_die #(.L(0), .R(0), .EXPECT(EXPECT), .D(D), .HMUT(HMUT)) u (.clk(clk), .rst_n(rst_n), .c_cmd(85'd0), .c_done(cd),
        .c_st(cs), .f_win(73'd0), .t_collective(tc), .t_ag(tag_), .f_agc(1'b0), .f_ai(1124'd0), .t_air(tair), .t_vm(tvm),
        .f_vm(16'd0), .acks(acks), .host_sent(sent), .booted(booted), .sw_fault(swf));
    function automatic [34:0] inverse(input [4:0] p, input [30:0] a); reg [30:0] t; reg [4:0] bank; begin
        t = a >> 2; bank = (p ^ t ^ (t >> 5)) & 31; inverse = ({4'b0, t} << 7) | ({30'b0, bank} << 2) | (a & 3); end endfunction
    integer n, bad = 0, row, st, pc; reg [34:0] g;
    always @(posedge clk) begin
        if (booted && cyc > 20) begin
            repeat (40) @(posedge clk);
            $display("ENGBOOT booted cycles=%0d acks=%0d sent=%0d", cyc, acks, sent);
            check_all();
        end
        if (cs[0] || swf || cyc > 200000) begin
            $display("ENGBOOT FAULT_OR_TIMEOUT fault=%b swf=%b cyc=%0d acks=%0d sent=%0d", cs[0], swf, cyc, acks, sent);
            $display("FAIL"); $finish;
        end
    end
    task automatic check_all();
        integer m, r, s, p; reg [34:0] gg; reg [255:0] exp_, got; integer w;
        begin
            for (m = 0; m < EXPECT; m = m + 1) begin
                r = m / 9; s = r % 2; p = (r / 2) % 32; gg = inverse(p[4:0], 31'((r / 64) * 9 + 4 + m % 9));
                for (w = 0; w < 8; w = w + 1) exp_[32*w +: 32] = m * 32'h9E3779B1 ^ (w * 32'h85EBCA77);
                got = peek(s * 32 + p, gg[29:0]);
                if (got !== exp_) begin if (bad < 4) $display("BOOT MISMATCH sector %0d stack %0d pc %0d", m, s, p); bad = bad + 1; end
            end
            if (bad == 0 && acks == EXPECT + 67 && !cs[0] && !swf) $display("PASS"); else $display("FAIL bad=%0d acks=%0d", bad, acks);
            $finish;
        end
    endtask
    // per-PC peek (generate-indexed hierarchy needs constant indices)
    function automatic [255:0] peek(input integer pcg, input [29:0] a);
        peek = 256'bx;
        case (pcg)
`include "tb_eng_be_peek.svh"
        endcase
    endfunction
endmodule
