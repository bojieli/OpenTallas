`timescale 1ns/1ps
module tb_hdc_qwen_m5_verify_array;
    reg clk = 0, rst_n = 0, go = 0;
    always #5 clk = ~clk;
    wire ready, idle, fault, wrom_re, scale_re;
    wire [23:0] wrom_addr;
    wire [47:0] scale_addr;
    reg [63:0] scale_q = 0;
    wire [9:0] x_re, o_we;
    wire [239:0] x_addr, o_addr;
    reg [319:0] x_q;
    wire [19:0] o_mask;
    wire [639:0] o_data;
    wire [4:0] ov, am_any;
    wire [79:0] am_idx;
    wire [159:0] am_val;
    integer cycles = 0, weight_reads = 0, scale_reads = 0, writes = 0;
    integer s;
    function automatic [31:0] fp32_small(input integer v);
        case (v)
            1: fp32_small = 32'h3f800000; 2: fp32_small = 32'h40000000;
            3: fp32_small = 32'h40400000; 4: fp32_small = 32'h40800000;
            5: fp32_small = 32'h40a00000; 8: fp32_small = 32'h41000000;
            12: fp32_small = 32'h41400000; 16: fp32_small = 32'h41800000;
            20: fp32_small = 32'h41a00000;
            default: fp32_small = 32'hffffffff;
        endcase
    endfunction
    ot_hdc_qwen_m5_verify_array #(.W(2), .G(2), .IL(8)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle), .fault(fault),
        .i_nout(16'd18), .i_tiles(16'd1), .i_k(16'd2),
        .i_wbase(24'd100), .i_ts(24'd0), .i_ks(24'd0), .i_js(24'd0),
        .i_xks(24'd0), .i_xjs(24'd0), .i_xcs(24'd0),
        .i_ots(24'd8), .i_ojs(24'd1), .i_split(4'd0), .i_round(1'b1), .i_amax(1'b1),
        .i_xbase({24'd40,24'd30,24'd20,24'd10,24'd0}),
        .i_obase({24'd40,24'd30,24'd20,24'd10,24'd0}),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(32'h01010101),
        .scale_re(scale_re), .scale_addr(scale_addr), .scale_q(scale_q),
        .x_re(x_re), .x_addr(x_addr), .x_q(x_q),
        .ov(ov), .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any)
    );
    always @(posedge clk) begin
        cycles <= cycles + 1;
        if (wrom_re) begin
            if (wrom_addr !== 24'd100) $fatal(1, "shared weight address mismatch");
            weight_reads <= weight_reads + 1;
        end
        if (scale_re) begin
            if (scale_addr[23:0] !== 24'd100 + scale_reads ||
                scale_addr[47:24] !== 24'd108 + scale_reads)
                $fatal(1, "shared scale address mismatch got=%h n=%0d", scale_addr, scale_reads);
            scale_q <= {16'h3f80,16'h4040,16'h4000,16'h3f00};
            scale_reads <= scale_reads + 1;
        end
        for (s = 0; s < 5; s = s + 1) begin
            if (x_re[2*s] || x_re[2*s+1]) begin
                x_q[64*s +: 64] <= {fp32_small(s+1),fp32_small(s+1)};
            end
        end
        if (o_we[0]) begin
            if (o_we !== 10'b11_11_11_11_11 || ov !== 5'b11111)
                $fatal(1, "slot outputs lost lockstep");
            for (s = 0; s < 5; s = s + 1) begin
                if (o_data[128*s +: 32] !== fp32_small(s+1) ||
                    o_data[128*s+32 +: 32] !== fp32_small(4*(s+1)))
                    $fatal(1, "slot %0d scaled result mismatch: %h", s, o_data[128*s +: 64]);
            end
            writes <= writes + 1;
        end
    end
    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1;
        @(negedge clk); go = 1;
        @(negedge clk); go = 0;
        wait (idle);
        @(negedge clk);
        if (fault || writes != 8 || weight_reads != 16 || scale_reads != 8 || am_any !== 5'b11111)
            $fatal(1, "m5 final mismatch fault=%b writes=%0d weight=%0d scales=%0d any=%b",
                   fault, writes, weight_reads, scale_reads, am_any);
        $display("PASS Qwen INT8 m5 shared-weight verify: 5 slots, %0d weight reads, %0d scale reads, %0d result cycles", weight_reads, scale_reads, writes);
        $finish;
    end
    initial begin #20000; $fatal(1, "m5 verify timeout"); end
endmodule
