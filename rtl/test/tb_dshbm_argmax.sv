`timescale 1ns/1ps
// Argmax epilogue bench (tools/dshbm_dspark_rtl_campaign.py argmax): NROW rows of NV FP32 values (and FP32 bias
// rows when BIAS = 1) from rows.hex / bias.hex, streamed LP a beat back to back; prints one ROW line per result
// (index, nan flag) and the cycles from the row's first beat to its result.
module tb_dshbm_argmax;
    parameter integer LP = 8, NV = 4040, NROW = 16, BIAS = 0, IW = 17;
    parameter ROWS = "rows.hex", BIASF = "bias.hex";
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg [31:0] rv [0:NROW*NV-1];
    reg [31:0] bv [0:NROW*NV-1];
    reg in_v = 0, in_last = 0; reg [LP-1:0] in_mask = 0; reg [LP*32-1:0] in_vals = 0, in_bias = 0;
    wire out_v, out_nan, fault; wire [IW-1:0] out_idx;
    ot_dshbm_argmax #(.LP(LP), .IW(IW), .FLAT(7)) dut (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_last(in_last),
        .in_bias_en(BIAS[0]), .in_mask(in_mask), .in_vals(in_vals), .in_bias(in_bias), .out_v(out_v),
        .out_idx(out_idx), .out_nan(out_nan), .fault(fault));
    integer t_first [0:NROW-1];
    integer nout = 0;
    always @(posedge clk) if (out_v) begin
        $display("ROW %0d idx %0d nan %0d cycles %0d fault %0d", nout, out_idx, out_nan, cyc - t_first[nout], fault);
        nout = nout + 1;
    end
    integer r, b, k;
    initial begin
        $readmemh(ROWS, rv);
        if (BIAS) $readmemh(BIASF, bv);
        repeat (3) @(posedge clk);
        rst_n = 1;
        @(negedge clk);
        for (r = 0; r < NROW; r = r + 1) begin
            for (b = 0; b < NV; b = b + LP) begin
                if (b == 0) t_first[r] = cyc;
                in_v = 1; in_last = (b + LP >= NV);
                for (k = 0; k < LP; k = k + 1) begin
                    in_mask[k] = (b + k < NV);
                    in_vals[32*k +: 32] = (b + k < NV) ? rv[r*NV + b + k] : 32'd0;
                    in_bias[32*k +: 32] = (BIAS && b + k < NV) ? bv[r*NV + b + k] : 32'd0;
                end
                @(negedge clk);
            end
        end
        in_v = 0; in_last = 0;
        while (nout < NROW) @(negedge clk);
        $display("DONE rows %0d", nout);
        $finish;
    end
    initial begin #50000000; $display("TIMEOUT"); $finish; end
endmodule
