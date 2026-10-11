`timescale 1ns/1ps
// qwen-1010/a: seq_su_bi program store, SRAM (default) vs flop store (+define+OT_PROG_FLOPS).  Writes every 64-b
// word of all 64 rows through pw_* in random order, then forces the controller's read port (prog_re / prog_base /
// prog_addr, incl. out-of-range addresses) at random, with random rewrites to OTHER rows interleaved, and prints
// prog_q every edge.  The two builds' transcripts must be identical.
module tb_prog_store;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    reg pw_v = 0; reg [9:0] pw_addr = 0; reg [63:0] pw_data = 0;
    reg re = 0; reg [11:0] base = 0, addr = 0;
    integer k, seed = 11; reg [5:0] wr;
    ot_qfd_seq_su_bi dut (.clk(clk), .rst_n(rst_n), .h_start(1'b0), .stage_in(6'd0), .cb_st_rdy(1'b0),
        .cb_st_rdy_stage(6'd0), .tp_token(18'd0), .tp_pos(18'd0), .kv_write_drained(1'b1), .vm_rq(512'd0),
        .c_ready(1'b0), .r_valid(1'b0), .r_data(512'd0), .r_last(1'b0), .r_rank(2'd0), .r_err(1'b0),
        .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(pw_data));
    initial begin force dut.prog_re = re; force dut.prog_base = base; force dut.prog_addr = addr; end
    always @(*) begin force dut.prog_re = re; force dut.prog_base = base; force dut.prog_addr = addr; end
    integer cyc = 0;
    always @(posedge clk) begin cyc <= cyc + 1; if (rst_n) $display("Q %0d %h", cyc, dut.prog_q); end
    initial begin
        repeat (4) @(negedge clk); rst_n = 1;
        for (k = 0; k < 1024; k = k + 1) begin @(negedge clk); pw_v = 1; pw_addr = (k * 389) % 1024; pw_data = {$random(seed), $random(seed)}; end
        @(negedge clk); pw_v = 0; repeat (4) @(negedge clk);
        for (k = 0; k < 3000; k = k + 1) begin
            @(negedge clk);
            re = $random(seed); base = $random(seed) % 80; addr = $random(seed) % 4;
            // rewrite a row the read cannot touch this cycle or the next few (the controller never reads while loading)
            pw_v = ($random(seed) % 4) == 0; pw_data = {$random(seed), $random(seed)};
            wr = base[5:0] + 6'd20 + ($random(seed) & 7); pw_addr = {wr, 4'd0} | ($random(seed) & 15);
            if (pw_v) begin re = 0; end
        end
        @(negedge clk); pw_v = 0; re = 0; repeat (4) @(negedge clk); $finish;
    end
endmodule
