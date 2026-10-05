`timescale 1ns/1ps
// A reduced complete K-split matrix op: signed INT8 words, synchronous row
// scales, post-tree scale, writeback and argmax. The largest raw sum is tied;
// only scaling makes row 16 the winner.
module tb_hdc_qwen_int8_matvec;
    parameter integer SPLIT = 0;
    parameter integer SCALE_SEPARATE = 0;
    reg clk = 0, rst_n = 0, go = 0;
    always #5 clk = ~clk;
    wire ready, idle, scale_re, wrom_re, kv_re, ov, mx_we, fault, am_any;
    wire [1:0] scale_gre;
    wire [23:0] wrom_addr, mx_addr;
    wire [47:0] scale_addr;
    reg [63:0] scale_q = 0;
    wire [1:0] o_we, x_re;
    wire [47:0] o_addr, x_addr, kv_addr;
    wire [3:0] o_mask;
    wire [127:0] o_data;
    wire [15:0] am_idx, progress;
    wire [31:0] am_val;
    wire [1:0] mx_mask;
    wire [63:0] mx_data;
    integer scale_reads = 0, group_reads = 0, writes = 0, cycles = 0;
    integer first_raw_cycle = -1, first_output_cycle = -1;
    function automatic [15:0] scale_for_slot(input integer slot);
        case (slot)
            0: scale_for_slot = 16'h4000; // 2
            1: scale_for_slot = 16'h4040; // 3
            2: scale_for_slot = 16'h4080; // 4
            3: scale_for_slot = 16'h40A0; // 5
            4: scale_for_slot = 16'h40C0; // 6
            5: scale_for_slot = 16'h40E0; // 7
            6: scale_for_slot = 16'h4100; // 8
            default: scale_for_slot = 16'h4110; // 9
        endcase
    endfunction
    function automatic [31:0] expected_lane1(input integer slot, input integer split);
        case (slot)
            0: expected_lane1 = split ? 32'h41400000 : 32'h40800000;
            1: expected_lane1 = split ? 32'h41900000 : 32'h40C00000;
            2: expected_lane1 = split ? 32'h41C00000 : 32'h41000000;
            3: expected_lane1 = split ? 32'h41F00000 : 32'h41200000;
            4: expected_lane1 = split ? 32'h42100000 : 32'h41400000;
            5: expected_lane1 = split ? 32'h42280000 : 32'h41600000;
            6: expected_lane1 = split ? 32'h42400000 : 32'h41800000;
            default: expected_lane1 = split ? 32'h42580000 : 32'h41900000;
        endcase
    endfunction

    ot_hdc_matvec #(.G(2), .W(2), .IL(8), .INT8_WEIGHT(1),
                    .INT8_SCALE_WCS_BASE(SCALE_SEPARATE)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(SPLIT ? 16'd2 : 16'd18), .i_tiles(16'd1), .i_k(16'd2),
        .i_wsrc(1'b0), .i_wbase(24'd100), .i_ts(24'd0),
        .i_ks(24'd0), .i_js(24'd0),
        .i_xbase(24'd0), .i_xks(24'd0), .i_xjs(24'd0), .i_xcs(24'd0),
        .i_jsh(3'd0), .i_split(SPLIT ? 4'd1 : 4'd0),
        .i_wcs(SCALE_SEPARATE ? 24'd300 : 24'd0), .i_round(1'b1),
        .i_obase(24'd0), .i_ots(24'd8), .i_ojs(24'd1),
        .i_mmode(1'b0), .i_oen(1'b1), .i_amax(1'b1),
        .i_rmax(1'b0), .i_mbase(24'd0),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(SPLIT ? 32'h02020101 : 32'h01010101),
        .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr), .scale_q(scale_q),
        .kv_re(kv_re), .kv_addr(kv_addr), .kv_q(128'd0),
        .x_re(x_re), .x_addr(x_addr), .x_q({2{32'h3F800000}}),
        .ov(ov), .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(progress), .fault(fault)
    );
    // One-cycle synchronous ROM. Scale words are addressed by the matrix's
    // weight base plus the output row-word offset; group 1 is 8 words ahead.
    always @(posedge clk) if (scale_re) begin
        if (scale_gre !== (SPLIT ? 2'b01 : (scale_reads == 0 ? 2'b11 : 2'b01)))
            $fatal(1, "active scale groups mismatch split=%0d read=%0d mask=%b", SPLIT, scale_reads, scale_gre);
        if (scale_addr[23:0] !== (SCALE_SEPARATE ? 24'd300 : 24'd100) + scale_reads ||
            scale_addr[47:24] !== (SCALE_SEPARATE ? 24'd300 : 24'd100) +
                                    (scale_gre[1] ? 24'd8 + scale_reads : 24'd0))
            $fatal(1, "scale address mismatch at request %0d: %h", scale_reads, scale_addr);
        scale_q <= {scale_gre[1] ? 16'h3F80 : 16'h7FC0,
                    scale_gre[1] ? 16'h4040 : 16'h7FC0,
                    scale_for_slot(scale_reads), 16'h3F00};
        group_reads <= group_reads + scale_gre[0] + scale_gre[1];
        scale_reads <= scale_reads + 1;
    end
    always @(posedge clk) begin
        cycles <= cycles + 1;
        if (dut.raw_v && dut.raw_last && first_raw_cycle < 0)
            first_raw_cycle <= cycles;
        if (ov && first_output_cycle < 0)
            first_output_cycle <= cycles;
        if (o_we[0] || o_we[1]) begin
            writes <= writes + 1;
            if ((!SPLIT || writes == 0) &&
                (o_data[63:32] !== expected_lane1(writes, SPLIT) ||
                 o_data[31:0] !== (SPLIT ? 32'h40400000 : 32'h3F800000)))
                $fatal(1, "wrong scale for slot %0d: data=%h expected lane1=%h",
                       writes, o_data[63:0], expected_lane1(writes, SPLIT));
            if (writes == 0)
                if (SPLIT ?
                    (o_we !== 2'b01 || o_mask !== 4'b0011 ||
                     o_data[63:0] !== {32'h41400000,32'h40400000}) :
                    (o_we !== 2'b11 || o_mask !== 4'b1111 ||
                     o_data !== {32'h40000000,32'h40C00000,32'h40800000,32'h3F800000}))
                    $fatal(1, "scaled first slot mismatch split=%0d mask=%b data=%h", SPLIT, o_mask, o_data);
        end
    end
    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1;
        @(negedge clk); go = 1;
        @(negedge clk); go = 0;
        @(negedge clk);
        if (ready) $fatal(1, "matvec reported ready while issue loop was active");
        go = 1; // a second request while busy must not restart the matrix op
        @(negedge clk); go = 0;
        wait (idle);
        @(negedge clk);
        if (scale_reads != (SPLIT ? 1 : 8) || group_reads != (SPLIT ? 1 : 9) || writes != 8 ||
            first_output_cycle - first_raw_cycle != 7 || !am_any ||
            am_idx != (SPLIT ? 1 : 15) ||
            am_val != (SPLIT ? 32'h41400000 : 32'h41900000) || fault)
            $fatal(1, "final mismatch reads=%0d group_reads=%0d writes=%0d latency=%0d argmax=%b/%0d/%h fault=%b cycles=%0d",
                   scale_reads, group_reads, writes, first_output_cycle - first_raw_cycle,
                   am_any, am_idx, am_val, fault, cycles);
        $display("PASS Qwen INT8 matvec split=%0d scale/argmax, %0d requests, %0d group reads, %0d writes", SPLIT, scale_reads, group_reads, writes);
        $finish;
    end
    initial begin
        #20000;
        $fatal(1, "matvec did not drain");
    end
endmodule
