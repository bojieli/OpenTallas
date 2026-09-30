`timescale 1ns/1ps
// W11 streaming units: the latency-cut arithmetic (ot_hdc_v41x_q4dot QL 3..5, ot_hdc_v41x_bmul ML 3..5,
// ot_hdc_v41x_attn_bmul ML 3..6) equals the as-built LAT-3 unit delayed by the added cycles, output for output,
// on random operands streaming at one per cycle (+NCYC, default 20,000).  Prints W11SEQ checked=<n> errors=<n>.
module tb_w11s_cut_equiv;
    reg clk = 0;
    always #1 clk = ~clk;
    integer seed = 32'h5eed, cyc = 0, checked = 0, errors = 0, ncyc = 20000;
    initial if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
    reg [127:0] qa, qb;
    reg [7:0]   ua, ub;
    reg [15:0]  ba, bw, ab, bb;
    reg         pad;
    function automatic [7:0] scale(input [31:0] r);    // mostly in range, some refused bytes
        scale = (r[3:0] == 0) ? (8'd250 + r[6:4]) : (8'd100 + r[12:8] + r[20:16]);
    endfunction
    function automatic [15:0] bf(input [31:0] r);      // BF16 over the exponent range, zeros, subnormals
        case (r[2:0])
            3'd0: bf = {r[15], 15'd0};
            3'd1: bf = {r[15], 8'd0, r[22:16]};
            3'd2: bf = {r[15], 8'd254, r[22:16]};
            default: bf = {r[15], r[30:23], r[22:16]};
        endcase
    endfunction
    always @(posedge clk) begin
        qa <= {$random(seed), $random(seed), $random(seed), $random(seed)};
        qb <= {$random(seed), $random(seed), $random(seed), $random(seed)};
        ua <= scale($random(seed)); ub <= scale($random(seed));
        ba <= bf($random(seed)); bw <= bf($random(seed)); ab <= bf($random(seed)); bb <= bf($random(seed));
        pad <= ($random(seed) & 15) == 0;
        cyc <= cyc + 1;
    end
    wire [31:0] qy [3:5];
    wire        qo [3:5];
    wire [15:0] my [3:5];
    wire        mo [3:5];
    wire [31:0] ay [3:6];
    wire        ao [3:6];
    genvar l;
    generate
        for (l = 3; l <= 5; l = l + 1) begin : g_q
            ot_hdc_v41x_q4dot #(.QL(l)) u (.clk(clk), .a(qa), .b(qb), .ua(ua), .ub(ub), .y(qy[l]), .ovf(qo[l]));
            ot_hdc_v41x_bmul #(.ML(l)) m (.clk(clk), .a(ba), .w(bw), .y(my[l]), .ovf(mo[l]));
        end
        for (l = 3; l <= 6; l = l + 1) begin : g_a
            ot_hdc_v41x_attn_bmul #(.ML(l)) u (.clk(clk), .a(ab), .b(bb), .pad(pad), .y(ay[l]), .flt(ao[l]));
        end
    endgenerate
    // LAT-3 outputs, delayed 0..3 cycles
    reg [32:0] qd [0:3];
    reg [16:0] md [0:3];
    reg [32:0] ad [0:3];
    integer i;
    always @(posedge clk) begin
        qd[0] <= {qo[3], qy[3]}; md[0] <= {mo[3], my[3]}; ad[0] <= {ao[3], ay[3]};
        for (i = 1; i < 4; i = i + 1) begin qd[i] <= qd[i-1]; md[i] <= md[i-1]; ad[i] <= ad[i-1]; end
    end
    always @(negedge clk) if (cyc > 12) begin
        for (i = 4; i <= 5; i = i + 1) begin
            checked = checked + 2;
            if ({qo[i], qy[i]} !== qd[i-4]) begin errors = errors + 1; if (errors < 8) $display("Q%0d %h %h", i, {qo[i], qy[i]}, qd[i-4]); end
            if ({mo[i], my[i]} !== md[i-4]) begin errors = errors + 1; if (errors < 8) $display("M%0d %h %h", i, {mo[i], my[i]}, md[i-4]); end
        end
        for (i = 4; i <= 6; i = i + 1) begin
            checked = checked + 1;
            if ({ao[i], ay[i]} !== ad[i-4]) begin errors = errors + 1; if (errors < 8) $display("A%0d %h %h", i, {ao[i], ay[i]}, ad[i-4]); end
        end
        if (cyc == ncyc + 12) begin
            $display("W11SEQ checked=%0d errors=%0d", checked, errors);
            $finish;
        end
    end
endmodule
