`timescale 1ns/1ps
// Expert-union bench (tools/dshbm_dspark_rtl_campaign.py union): NCASE cases of P columns x K ascending ids from
// ids.hex (one id a line, column-major), added one column a cycle; then a flush, the union drained with out_ready
// held high.  Prints one U line per emitted {id, mask} and one CASE line with the cycles add -> flush -> last id.
module tb_dshbm_union;
    parameter integer NE = 384, K = 6, P = 6, NCASE = 8, IW = 9;
    parameter IDS = "ids.hex";
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg [31:0] idm [0:NCASE*P*K-1];
    reg clr = 0, add_v = 0, flush = 0; reg [2:0] add_col = 0; reg [K*IW-1:0] add_ids = 0;
    wire out_v, out_last, busy; wire [IW-1:0] out_id; wire [7:0] out_mask; wire [IW:0] count;
    ot_dshbm_expert_union #(.NE(NE), .K(K), .PM(8), .IW(IW)) dut (.clk(clk), .rst_n(rst_n), .clr(clr), .add_v(add_v),
        .add_col(add_col), .add_ids(add_ids), .add_en({K{1'b1}}), .flush(flush), .out_v(out_v), .out_ready(1'b1),
        .out_id(out_id), .out_mask(out_mask), .out_last(out_last), .busy(busy), .count(count));
    integer c, j, k, t_flush, t_first;
    always @(posedge clk) if (out_v) begin
        if (t_first < 0) t_first = cyc;
        $display("U %0d %0d %0d", c, out_id, out_mask);
    end
    initial begin
        $readmemh(IDS, idm);
        repeat (3) @(posedge clk); rst_n = 1;
        for (c = 0; c < NCASE; c = c + 1) begin
            @(negedge clk); clr = 1; @(negedge clk); clr = 0;
            for (j = 0; j < P; j = j + 1) begin
                add_v = 1; add_col = j;
                for (k = 0; k < K; k = k + 1) add_ids[k*IW +: IW] = idm[(c*P + j)*K + k];
                @(negedge clk);
            end
            add_v = 0; flush = 1; t_flush = cyc; t_first = -1; @(negedge clk); flush = 0;
            @(negedge clk); while (busy) @(negedge clk);
            $display("CASE %0d flush_to_first %0d flush_to_done %0d count %0d", c, t_first - t_flush, cyc - t_flush, count);
        end
        $finish;
    end
endmodule
