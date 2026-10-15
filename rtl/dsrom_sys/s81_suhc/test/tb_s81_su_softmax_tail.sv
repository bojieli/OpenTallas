`timescale 1ns/1ps
// Real synthesizable lane, no DPI arithmetic. Every lane of a 133-position
// head is replayed through this physical leaf, including adjacent vector beats.
module tb_s81_su_softmax_tail;
    reg clk=0; always #0.5 clk=~clk;
    reg rst=0, cv=0, sv=0, mv=0;
    reg [31:0] sd=0;
    wire mxv, ev, es, el;
    wire [31:0] mx, ed;
    ot_s81_su_sml dut(.clk(clk), .rst_in(rst), .sk_en(1'b0),
        .i_cv(cv), .i_nv(7'd9), .i_scale(32'h3f800000), .i_sink(32'd0),
        .i_sv(sv), .i_s(sd), .i_mv(mv), .i_nmb(32'hbf800000),
        .o_mxv(mxv), .o_mx(mx), .o_ev(ev), .o_es(es), .o_el(el), .o_e(ed));
    reg [31:0] scores[0:143], expected[0:143];
    integer lane, v, ix, got=0, bad=0;
    always @(negedge clk) if(rst && ev && !es) begin
        ix=16*got+lane;
        if(ed !== expected[ix]) begin
            $display("TAIL mismatch lane=%0d vector=%0d got=%h want=%h",lane,got,ed,expected[ix]);
            bad=bad+1;
        end
        if(el !== (got==8)) bad=bad+1;
        got=got+1;
    end
    initial begin
        $readmemh("scores.mem",scores); $readmemh("expected.mem",expected);
        repeat(8) @(negedge clk); rst=1;
        repeat(8) @(negedge clk);
        for(lane=0;lane<16;lane=lane+1) begin
            got=0;
            cv=1; @(negedge clk); cv=0;
            repeat(4) @(negedge clk);
            for(v=0;v<9;v=v+1) begin sv=1;sd=scores[16*v+lane]; @(negedge clk); end
            sv=0;
            wait(mxv); @(negedge clk); mv=1; @(negedge clk); mv=0;
            repeat(130) @(negedge clk);
            if(got!=9) begin $display("TAIL missing lane=%0d got=%0d",lane,got);bad=bad+1; end
        end
        $display("TAIL checked=144 bad=%0d",bad);
        if(bad) $fatal(1,"TAIL FAIL");
        $display("TAIL PASS");$finish;
    end
    initial begin #20000; $fatal(1,"TAIL TIMEOUT"); end
endmodule
