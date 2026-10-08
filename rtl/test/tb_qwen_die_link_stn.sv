// ot_qwen_die_link_stn: every output == its source input one cycle later (control bits zero during reset sync),
// random stimulus, all three SHAPEs.  NEG = 1 expects zero delay (must fail).
`timescale 1ns/1ps
module tb_qwen_die_link_stn;
    parameter integer N = 50000, NEG = 0, SHAPE = 0, NL = (SHAPE == 1) ? 2 : 1;
    localparam integer LW = 528, CW = 16;
    reg clk = 0, rst_n = 0, sel_e = 0;
    localparam integer BW = (SHAPE == 0) ? NL * LW : 1, CWW = (SHAPE == 0) ? 1 : LW;
    reg [NL*LW-1:0] a_i = 0; reg [BW-1:0] b_i = 0; reg [CWW-1:0] w_i = 0, e_i = 0;
    wire [NL*LW-1:0] a_o; wire [BW-1:0] b_o; wire [CWW-1:0] w_o, e_o;
    ot_qwen_die_link_stn #(.NL(NL), .SHAPE(SHAPE)) u (.clk(clk), .rst_n(rst_n), .sel_e(sel_e), .a_i(a_i), .a_o(a_o),
        .b_i(b_i), .b_o(b_o), .w_i(w_i), .w_o(w_o), .e_i(e_i), .e_o(e_o));
    always #1 clk = ~clk;
    reg [NL*LW-1:0] pa, xa; reg [BW-1:0] pb, xb; reg [CWW-1:0] pw, pe, xw, xe; reg psel;
    integer i, k, bad = 0, checks = 0, seed = 11;
    initial begin
        sel_e = (SHAPE == 2) ? 1'b1 : 1'b0;
        repeat (3) @(posedge clk); rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            if (i > 6) begin
                if (SHAPE == 0) begin xb = NEG ? pa : a_i; xa = NEG ? pb : b_i; xw = 0; xe = 0; end
                else if (SHAPE == 1) begin
                    xw = NEG ? pa[0 +: LW] : a_i[0 +: LW]; xe = NEG ? pa[LW +: LW] : a_i[LW +: LW];
                    xa = NEG ? {pe, pw} : {e_i, w_i}; xb = 0;
                end else begin
                    xw = NEG ? pa : a_i; xe = NEG ? pa : a_i; xa = NEG ? (sel_e ? pe : pw) : (sel_e ? e_i : w_i); xb = 0;
                end
                if (a_o !== xa || b_o !== xb || w_o !== xw || e_o !== xe) bad = bad + 1;
                checks = checks + 1;
            end
            pa = a_i; pb = b_i; pw = w_i; pe = e_i;
            for (k = 0; k < NL*LW; k = k + 32) a_i[k +: 32] = $random(seed);
            if (SHAPE == 0) for (k = 0; k < BW; k = k + 32) b_i[k +: 32] = $random(seed);
            else for (k = 0; k < LW; k = k + 32) begin w_i[k +: 32] = $random(seed); e_i[k +: 32] = $random(seed); end
            psel = sel_e;
        end
        if (bad == 0) $display("PASS link_stn SHAPE=%0d NL=%0d checks=%0d", SHAPE, NL, checks);
        else $display("FAIL link_stn SHAPE=%0d NL=%0d NEG=%0d: %0d mismatches of %0d", SHAPE, NL, NEG, bad, checks);
        $finish;
    end
endmodule
