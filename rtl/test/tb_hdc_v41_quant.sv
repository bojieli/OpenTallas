`timescale 1ns/1ps
// Streams golden vectors through the two DeepSeek-V4.1 quantisers with random
// bubbles and checks every output bit, in order:
//   ot_hdc_actquant  aq_in.mem  {mode[3:0], x[1023:0]}
//                    aq_exp.mem {fault[3:0], e[11:0], q[255:0], y[511:0]}
//   ot_hdc_fp4qdq    q4_in.mem  {x[1023:0]}
//                    q4_exp.mem {fault[3:0], y[511:0]}
// (tools/rtl_hdc_v41_blockdot_campaign.py writes them in the run directory).
// +NAQ / +NQ4: vector counts; +SEED; +BUBBLE: bubble probability in 1/16ths.
// Clocked by the Verilator harness, or by tb_hdc_v41_quant_icarus.
module tb_hdc_v41_quant #(
    parameter integer MAXA = 1 << 17,
    parameter integer MAXQ = 1 << 16
) (input wire clk);
    reg [1027:0] aq_in  [0:MAXA-1];
    reg [783:0]  aq_exp [0:MAXA-1];
    reg [1023:0] q4_in  [0:MAXQ-1];
    reg [515:0]  q4_exp [0:MAXQ-1];
    integer naq = 0, nq4 = 0, bubble = 4;
    reg [31:0] seed = 32'h2468ace1;
    initial begin
        if (!$value$plusargs("NAQ=%d", naq)) naq = 0;
        if (!$value$plusargs("NQ4=%d", nq4)) nq4 = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 32'h2468ace1;
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 4;
        if (naq > 0) $readmemh("aq_in.mem", aq_in, 0, naq - 1);
        if (naq > 0) $readmemh("aq_exp.mem", aq_exp, 0, naq - 1);
        if (nq4 > 0) $readmemh("q4_in.mem", q4_in, 0, nq4 - 1);
        if (nq4 > 0) $readmemh("q4_exp.mem", q4_exp, 0, nq4 - 1);
    end
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg rst_n = 1'b0;
    reg          a_v = 1'b0, a_fp4 = 1'b0, b_v = 1'b0;
    reg [1023:0] a_x = 0, b_x = 0;
    wire         a_vo, a_fault, b_vo, b_fault;
    wire [255:0] a_q;
    wire signed [9:0] a_e;
    wire [511:0] a_y, b_y;
    ot_hdc_actquant dut_a (.clk(clk), .rst_n(rst_n), .v(a_v), .fp4(a_fp4), .x(a_x),
                           .vo(a_vo), .q(a_q), .e(a_e), .y(a_y), .fault(a_fault));
    ot_hdc_fp4qdq   dut_b (.clk(clk), .rst_n(rst_n), .v(b_v), .x(b_x),
                           .vo(b_vo), .y(b_y), .fault(b_fault));

    integer cyc = 0, ia = 0, ib = 0, oa = 0, ob = 0, ea = 0, eb = 0, idle = 0, bubbles = 0;
    reg [783:0] ex;
    reg [515:0] ey;
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (cyc > 5) begin
            seed = xs(seed);
            if (ia < naq && (seed[3:0] >= bubble)) begin
                a_v <= 1'b1; a_fp4 <= aq_in[ia][1024]; a_x <= aq_in[ia][1023:0]; ia = ia + 1;
            end else begin
                a_v <= 1'b0; a_x <= {32{seed}};           // bubbles carry junk
                if (ia < naq) bubbles = bubbles + 1;
            end
            if (ib < nq4 && (seed[7:4] >= bubble)) begin
                b_v <= 1'b1; b_x <= q4_in[ib]; ib = ib + 1;
            end else begin
                b_v <= 1'b0; b_x <= {32{~seed}};
            end
        end
        if (rst_n && a_vo) begin
            ex = aq_exp[oa];
            if (a_fault !== ex[780] || (!ex[780] && ({a_e, a_q, a_y} !== {ex[777:768], ex[767:0]}))) begin
                if (ea < 10) $display("AQ MISMATCH idx=%0d fault=%b e=%0d/%0d q=%h/%h y=%h/%h", oa, a_fault,
                                      a_e, $signed(ex[777:768]), a_q, ex[767:512], a_y, ex[511:0]);
                ea = ea + 1;
            end
            oa = oa + 1;
        end
        if (rst_n && b_vo) begin
            ey = q4_exp[ob];
            if (b_fault !== ey[512] || (!ey[512] && b_y !== ey[511:0])) begin
                if (eb < 10) $display("Q4 MISMATCH idx=%0d y=%h exp=%h", ob, b_y, ey[511:0]);
                eb = eb + 1;
            end
            ob = ob + 1;
        end
        if (ia == naq && ib == nq4) idle = idle + 1;
        if (idle == 40) begin
            $display("V41Q actquant vectors=%0d checked=%0d errors=%0d fp4qdq vectors=%0d checked=%0d errors=%0d bubbles=%0d cycles=%0d",
                     naq, oa, ea, nq4, ob, eb, bubbles, cyc);
            if (ea == 0 && eb == 0 && oa == naq && ob == nq4) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule

`ifndef VERILATOR
module tb_hdc_v41_quant_icarus;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    tb_hdc_v41_quant #(.MAXA(1 << 12), .MAXQ(1 << 12)) u (.clk(clk));
endmodule
`endif
