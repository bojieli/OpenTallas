`timescale 1ns/1ps
module tb_v41_w2_packed_spad;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg act_we = 0, act_re = 0, y_we = 0, y_re = 0;
    reg [1:0] act_wr_rank = 0, act_rd_rank = 0, y_wr_rank = 0, y_rd_rank = 0;
    reg [6:0] act_wr_word = 0;
    reg [5:0] y_wr_word = 0;
    reg [2:0] act_rd_expert = 0;
    reg [9:0] act_rd_col = 0;
    reg [10:0] y_rd_col = 0;
    reg [511:0] act_wdata = 0, y_wdata = 0;
    wire act_wfault, act_rvalid, act_rfault;
    wire [7:0] act_code, act_scale;
    wire y_wfault, y_rvalid, y_rfault;
    wire [15:0] y_bf16;
    reg [511:0] act_flit [0:307], y_flit [0:159];
    reg [7:0] code_exp [0:16127], scale_exp [0:16127];
    reg [15:0] y_exp [0:5119];
    integer r, e, c, k, idx, errors = 0;
    string dir;
    ot_chip_v41x_w2_packed_spad u_act (
        .clk(clk), .rst_n(rst_n), .wr_valid(act_we), .wr_rank(act_wr_rank),
        .wr_word(act_wr_word), .wr_data(act_wdata), .wr_fault(act_wfault),
        .rd_valid(act_re), .rd_rank(act_rd_rank), .rd_expert(act_rd_expert),
        .rd_col(act_rd_col), .rd_valid_q(act_rvalid), .rd_code(act_code),
        .rd_scale(act_scale), .rd_fault_q(act_rfault));
    ot_chip_v41x_w2_y_spad u_y (
        .clk(clk), .rst_n(rst_n), .wr_valid(y_we), .wr_rank(y_wr_rank),
        .wr_word(y_wr_word), .wr_data(y_wdata), .wr_fault(y_wfault),
        .rd_valid(y_re), .rd_rank(y_rd_rank), .rd_col(y_rd_col),
        .rd_valid_q(y_rvalid), .rd_bf16(y_bf16), .rd_fault_q(y_rfault));
    initial begin
        if (!$value$plusargs("VEC=%s", dir)) $fatal(1, "missing +VEC");
        $readmemh({dir, "/act_flit.hex"}, act_flit);
        $readmemh({dir, "/y_flit.hex"}, y_flit);
        $readmemh({dir, "/code.hex"}, code_exp);
        $readmemh({dir, "/scale.hex"}, scale_exp);
        $readmemh({dir, "/y.hex"}, y_exp);
        repeat (4) @(negedge clk);
        rst_n = 1;
        for (k = 0; k < 308; k = k + 1) begin
            @(negedge clk);
            act_we = 1;
            act_wr_rank = 2'(k / 77);
            act_wr_word = 7'(k % 77);
            act_wdata = act_flit[k];
        end
        @(negedge clk); act_we = 0;
        for (k = 0; k < 160; k = k + 1) begin
            @(negedge clk);
            y_we = 1;
            y_wr_rank = 2'(k / 40);
            y_wr_word = 6'(k % 40);
            y_wdata = y_flit[k];
        end
        @(negedge clk); y_we = 0;
        if (act_wfault || y_wfault) $fatal(1, "write fault");
        for (r = 0; r < 4; r = r + 1)
            for (e = 0; e < 7; e = e + 1)
                for (c = 0; c < 576; c = c + 1) begin
                    idx = r*7*576 + e*576 + c;
                    @(negedge clk);
                    act_re = 1;
                    act_rd_rank = 2'(r);
                    act_rd_expert = 3'(e);
                    act_rd_col = 10'(c);
                    @(negedge clk); act_re = 0;
                    @(posedge clk); #1;
                    if (!act_rvalid || act_rfault || act_code !== code_exp[idx] || act_scale !== scale_exp[idx]) begin
                        errors = errors + 1;
                        if (errors < 5) $display("ACT_ERROR rank=%0d expert=%0d col=%0d code=%h/%h scale=%h/%h valid=%0d", r,e,c,act_code,code_exp[idx],act_scale,scale_exp[idx],act_rvalid);
                    end
                end
        for (r = 0; r < 4; r = r + 1)
            for (c = 0; c < 1280; c = c + 1) begin
                idx = r*1280 + c;
                @(negedge clk); y_re = 1; y_rd_rank = 2'(r); y_rd_col = 11'(c);
                @(negedge clk); y_re = 0;
                @(posedge clk); #1;
                if (!y_rvalid || y_rfault || y_bf16 !== y_exp[idx]) begin
                    errors = errors + 1;
                    if (errors < 5) $display("Y_ERROR rank=%0d col=%0d bf16=%h/%h valid=%0d",r,c,y_bf16,y_exp[idx],y_rvalid);
                end
            end
        if (errors != 0) $fatal(1, "packed scratchpad mismatches=%0d", errors);
        $display("PACKED_SPAD_PASS act=16128 y=5120 write_flits=308+160 mismatches=0");
        $finish;
    end
endmodule
