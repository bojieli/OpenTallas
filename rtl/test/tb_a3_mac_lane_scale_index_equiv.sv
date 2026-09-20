`timescale 1ns/1ps
// The lane's E8M0 scale ADDRESSES against amendment A15's scale_index(), element
// by element, for every configuration the lane admits.
//
// WHY. ot_a3_mac_lane used to call scale_index() twice on the issue path, which
// put SIX 32-bit divisions and a multiply in one cycle and made the lane the ABI
// 3.0 datapath's slowest block at 64.7 MHz. The quotients are counters now --
// ``k / block`` wrapping at the block size, ``row / rows_per_block`` and
// ``col / rows_per_block`` wrapping at theirs and adding ``depth / block`` on the
// wrap, and that stride itself read off one extra advance of the k counter rather
// than divided. Nothing about the values may change, and "nothing changes" is a
// claim about an address SEQUENCE, so this checks the sequence.
//
// The lane is driven for real and its own s_rd_addr and t_rd_addr are compared
// against cfg_scale_*_base plus scale_index(row, k, ...) recomputed here from the
// bench's own row, column and reduction counters, which are advanced by watching
// the lane's state rather than by assuming its schedule.
//
// THE CONFIGURATIONS ARE THE AWKWARD ONES. A block that divides the depth and one
// that does not; rows_per_block of one (amendment A8's case), of the row count,
// and of neither; a block of one; a depth of one; and a block larger than the
// depth, where every quotient is zero and the stride is zero too.
module tb_a3_mac_lane_scale_index_equiv;
    localparam integer WORDS = 4096;

    reg clk = 0, rst_n = 0, start = 0;
    reg [15:0] cfg_rows, cfg_cols, cfg_depth;
    reg [7:0]  cfg_dtype_a, cfg_dtype_b;
    reg [31:0] cfg_a_base, cfg_b_base;
    reg        cfg_scale_a, cfg_scale_b;
    reg [15:0] cfg_block_a, cfg_block_b, cfg_block_rows_a, cfg_block_rows_b;
    reg [31:0] cfg_scale_a_base, cfg_scale_b_base, cfg_out_base;

    wire a_rd_en, b_rd_en, s_rd_en, t_rd_en, out_we, busy, done;
    wire [31:0] a_rd_addr, b_rd_addr, s_rd_addr, t_rd_addr, out_addr, out_data;
    wire [31:0] out_count, saturation_count, mac_count;
    wire [7:0]  error_code;

    //: A flat memory for every port; the values do not matter here, only that
    //: they are finite so the lane does not stop early.
    reg [31:0] store [0:WORDS-1];
    reg [31:0] a_rd_data, b_rd_data, s_rd_data, t_rd_data;
    always @(posedge clk) begin
        a_rd_data <= store[a_rd_addr[11:0]];
        b_rd_data <= store[b_rd_addr[11:0]];
        s_rd_data <= store[s_rd_addr[11:0]];
        t_rd_data <= store[t_rd_addr[11:0]];
    end

    ot_a3_mac_lane dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a), .cfg_block_rows_b(cfg_block_rows_b),
        .cfg_scale_a_base(cfg_scale_a_base), .cfg_scale_b_base(cfg_scale_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(a_rd_en), .a_rd_addr(a_rd_addr), .a_rd_data(a_rd_data),
        .b_rd_en(b_rd_en), .b_rd_addr(b_rd_addr), .b_rd_data(b_rd_data),
        .s_rd_en(s_rd_en), .s_rd_addr(s_rd_addr), .s_rd_data(s_rd_data),
        .t_rd_en(t_rd_en), .t_rd_addr(t_rd_addr), .t_rd_data(t_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .saturation_count(saturation_count),
        .mac_count(mac_count)
    );

    always #1 clk = ~clk;

    //: scale_index() copied verbatim from the lane, which is the point: this is
    //: the contract the counters must reproduce.
    function automatic [31:0] scale_index;
        input [15:0] element_row;
        input [15:0] element_column;
        input [15:0] depth;
        input [15:0] block;
        input [15:0] block_rows;
        reg [15:0] rows_per_block;
        reg [15:0] elements_per_block;
        begin
            rows_per_block = (block_rows == 16'd0) ? 16'd1 : block_rows;
            elements_per_block = (block == 16'd0) ? 16'd1 : block;
            scale_index = ({16'b0, element_row} / {16'b0, rows_per_block}) *
                          ({16'b0, depth} / {16'b0, elements_per_block}) +
                          ({16'b0, element_column} / {16'b0, elements_per_block});
        end
    endfunction

    integer errors = 0, checked = 0;
    //: The bench's own position in the walk, advanced by watching the lane issue
    //: and retire rather than by assuming a cycle count.
    integer b_row, b_col, b_k;
    reg [31:0] want_s, want_t;

    //: S_ISSUE is the only state that raises all four read enables together.
    always @(negedge clk) begin
        if (rst_n && s_rd_en && t_rd_en && a_rd_en && b_rd_en) begin
            want_s = cfg_scale_a_base +
                     scale_index(b_row[15:0], b_k[15:0], cfg_depth,
                                 cfg_block_a, cfg_block_rows_a);
            want_t = cfg_scale_b_base +
                     scale_index(b_col[15:0], b_k[15:0], cfg_depth,
                                 cfg_block_b, cfg_block_rows_b);
            checked = checked + 1;
            if (s_rd_addr !== want_s || t_rd_addr !== want_t) begin
                errors = errors + 1;
                if (errors < 12)
                    $display("FAIL row=%0d col=%0d k=%0d: s %0d/%0d t %0d/%0d",
                             b_row, b_col, b_k, s_rd_addr, want_s,
                             t_rd_addr, want_t);
            end
        end
        if (rst_n && out_we) begin
            //: one output element retired: advance the bench's walk
            b_k = 0;
            if (b_col + 1 == cfg_cols) begin
                b_col = 0;
                b_row = b_row + 1;
            end else begin
                b_col = b_col + 1;
            end
        end else if (rst_n && s_rd_en && t_rd_en && a_rd_en && b_rd_en) begin
            b_k = b_k + 1;
        end
    end

    task run(input [15:0] rows, input [15:0] cols, input [15:0] depth,
             input [15:0] block_a, input [15:0] rows_a,
             input [15:0] block_b, input [15:0] rows_b);
        begin
            cfg_rows = rows; cfg_cols = cols; cfg_depth = depth;
            cfg_block_a = block_a; cfg_block_rows_a = rows_a;
            cfg_block_b = block_b; cfg_block_rows_b = rows_b;
            b_row = 0; b_col = 0; b_k = 0;
            @(negedge clk); start = 1'b1;
            @(negedge clk); start = 1'b0;
            wait (done);
            @(negedge clk);
            if (error_code != 8'd0)
                $display("NOTE rows=%0d cols=%0d depth=%0d stopped with error %0d",
                         rows, cols, depth, error_code);
        end
    endtask

    integer w;
    initial begin
        //: BF16 codes for 1.0 everywhere, and E8M0 code 127 (a scale of one), so
        //: nothing is nonfinite and the lane runs the whole walk.
        for (w = 0; w < WORDS; w = w + 1) store[w] = 32'h0000_3f80;
        cfg_dtype_a = 8'h10; cfg_dtype_b = 8'h10;  //: FMT_BF16, which is 0x10
                                                  //: and not zero -- zero is FMT_U8
                                                  //: and the lane refuses it
        cfg_a_base = 0; cfg_b_base = 0; cfg_out_base = 3072;
        cfg_scale_a = 1'b1; cfg_scale_b = 1'b1;
        cfg_scale_a_base = 1024; cfg_scale_b_base = 2048;
        b_row = 0; b_col = 0; b_k = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk);

        run(3, 4, 8,  4, 1,  4, 1);     //: A8's case: rows_per_block one
        run(3, 4, 8,  4, 2,  2, 3);     //: rows_per_block neither one nor the rows
        run(4, 4, 6,  4, 2,  4, 4);     //: a block that does NOT divide the depth
        run(2, 3, 5,  1, 1,  1, 2);     //: a block of one
        run(2, 2, 1,  4, 1,  4, 2);     //: a depth of one
        run(3, 3, 4,  8, 2,  8, 3);     //: a block LARGER than the depth
        run(1, 1, 4,  2, 1,  2, 1);     //: one output element
        run(5, 1, 7,  3, 2,  3, 5);     //: cfg_cols of one, where the first store
                                        //: both latches the stride and advances row
        run(2, 5, 9,  0, 0,  0, 0);     //: no block declared: the substituted one

        if (errors == 0)
            $display("PASS tb_a3_mac_lane_scale_index_equiv %0d addresses", checked);
        else
            $display("FAIL tb_a3_mac_lane_scale_index_equiv %0d of %0d addresses",
                     errors, checked);
        $finish;
    end
endmodule
