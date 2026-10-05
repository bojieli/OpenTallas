`timescale 1ns/1ps
// Six groups stand in for the O4 die's 6,144: S=4 leaves two idle groups.
module tb_hdc_matvec_nonpower_split;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg go = 0;
    wire [5:0] x_re;
    wire ready;

    ot_hdc_matvec #(.G(6), .W(2), .IL(8)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready),
        .i_nout(16'd16), .i_tiles(16'd1), .i_k(16'd1),
        .i_wsrc(1'b0), .i_split(4'd2), .i_round(1'b1),
        .i_wbase(24'd0), .i_ts(24'd0), .i_ks(24'd0), .i_js(24'd0),
        .i_xbase(24'd0), .i_xks(24'd0), .i_xjs(24'd0), .i_xcs(24'd0),
        .i_jsh(3'd0), .i_wcs(24'd0), .i_obase(24'd0),
        .i_ots(24'd0), .i_ojs(24'd0), .i_mmode(1'b0),
        .i_oen(1'b0), .i_amax(1'b0), .i_rmax(1'b0), .i_mbase(24'd0),
        .wrom_q(192'd0), .kv_q(384'd0), .x_q(192'd0), .x_re(x_re)
    );

    initial begin
        repeat (2) @(negedge clk);
        rst_n = 1;
        @(negedge clk);
        if (!ready) $fatal(1, "engine did not become ready");
        go = 1;
        @(negedge clk);
        go = 0;
        @(negedge clk);
        if (x_re !== 6'b00_1111)
            $fatal(1, "incomplete split tile read x operand: x_re=%b", x_re);
        $display("PASS non-power-of-two group split mask");
        $finish;
    end
endmodule
