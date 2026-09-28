`timescale 1ns/1ps
// Full-shape QE datapath: one 192-block matrix, eight output rows.
module tb_hdc_v41_fullshape_qe;
    reg clk = 0;
    always #1 clk = ~clk;
    reg rst_n = 0, go = 0, unrounded = 0, fp4 = 0;
    wire ready, idle, vi_re, xr_re, qr_re, fault;
    wire [29:0] vi_addr, xr_addr, qr_addr, w_addr, kvb_src_addr;
    reg [31:0] vi_q = 0;
    reg [1023:0] xr_q = 0;
    reg [271:0] qr_q = 0;
    wire [0:0] w_we;
    wire [31:0] w_mask;
    wire [1023:0] w_data;
    wire kvb_v, kvb_fault;
    wire [255:0] kvb_codes;
    wire [7:0] kvb_scale;
    reg [1023:0] xmem [0:191];
    reg [271:0] qmem [0:1535];
    reg [31:0] expected_acc [0:7];
    reg [31:0] expected_bf16 [0:7];
    integer seen = 0, errors = 0, cycles = 0, mode = 0, fp4_mode = 0;

    ot_hdc_v41_qe #(.AW(30), .NW(21), .BL(1), .IL(8),
                     .NBMAX(192), .CHUNK8(1), .MP(1)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_mode(2'd0), .i_fp4(fp4), .i_unrounded(unrounded),
        .i_xbase(30'd0), .i_nb(8'd192), .i_nout(21'd8), .i_tiles(21'd1),
        .i_wbase(30'd0), .i_ind(1'b0), .i_ibase(30'd0), .i_istride(30'd0),
        .i_obase(30'd0), .i_m(3'd0), .i_xps(30'd0), .i_ops(30'd0),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .xr_re(xr_re), .xr_addr(xr_addr), .xr_q(xr_q),
        .w_we(w_we), .w_addr(w_addr), .w_mask(w_mask), .w_data(w_data),
        .kvb_v(kvb_v), .kvb_src_addr(kvb_src_addr), .kvb_codes(kvb_codes),
        .kvb_scale(kvb_scale), .kvb_fault(kvb_fault),
        .qr_re(qr_re), .qr_addr(qr_addr), .qr_q(qr_q), .fault(fault));

    initial begin
        $readmemh("x.mem", xmem);
        $readmemh("q.mem", qmem);
        $readmemh("acc.mem", expected_acc);
        $readmemh("bf16.mem", expected_bf16);
        if (!$value$plusargs("UNROUNDED=%d", mode)) mode = 0;
        if (!$value$plusargs("FP4=%d", fp4_mode)) fp4_mode = 0;
        unrounded = mode != 0;
        fp4 = fp4_mode != 0;
        repeat (5) @(negedge clk);
        rst_n = 1;
        @(negedge clk);
        go = 1;
        @(negedge clk);
        go = 0;
    end
    always @(posedge clk) begin
        if (xr_re) xr_q <= xmem[xr_addr >> 5];
        if (qr_re) qr_q <= qmem[qr_addr];
        if (rst_n) begin
            cycles <= cycles + 1;
            if (w_we[0]) begin
                if (seen >= 8 || w_addr !== 30'(seen) || w_mask !== 32'h1 ||
                    w_data[31:0] !== (unrounded ? expected_acc[seen] : expected_bf16[seen])) begin
                    $display("QE mismatch row=%0d addr=%0d mask=%h data=%h expected=%h",
                             seen, w_addr, w_mask, w_data[31:0],
                             unrounded ? expected_acc[seen] : expected_bf16[seen]);
                    errors <= errors + 1;
                end
                seen <= seen + 1;
            end
            if (idle && seen == 8) begin
                $display("V41QE rows=%0d errors=%0d cycles=%0d unrounded=%0d fp4=%0d fault=%0d",
                         seen, errors, cycles, mode, fp4_mode, fault);
                if (errors == 0 && !fault) $display("PASS"); else $display("FAIL");
                $finish;
            end
            if (cycles > 5000) begin
                $display("FAIL QE timeout rows=%0d errors=%0d", seen, errors);
                $finish;
            end
        end
    end
endmodule
