`timescale 1ns/1ps
// lockstep: old (pre-fix, renamed old_*) vs new ot_hdc_sk_csa over N x W; random rows, s and c compared, plus s + c == sum
module tb;
    localparam integer NP = 12;
    function automatic integer pn(input integer i);
        case (i) 0: pn = 1; 1: pn = 2; 2: pn = 3; 3: pn = 4; 4: pn = 5; 5: pn = 7; 6: pn = 9; 7: pn = 13; 8: pn = 24; 9: pn = 29; 10: pn = 6; default: pn = 31; endcase
    endfunction
    function automatic integer pw(input integer i);
        pw = (i % 3 == 0) ? 8 : (i % 3 == 1) ? 30 : 49;
    endfunction
    reg [31*64-1:0] rnd;
    integer errs = 0, sumerr = 0;
    wire [NP-1:0] bad, sbad;
    genvar g;
    generate for (g = 0; g < NP; g = g + 1) begin : g_p
        localparam integer N = pn(g);
        localparam integer W = pw(g);
        wire [W-1:0] so, co, sn, cn;
        old_ot_hdc_sk_csa #(.N(N), .W(W)) uo (.rows(rnd[N*W-1:0]), .s(so), .c(co));
        ot_hdc_sk_csa #(.N(N), .W(W)) un (.rows(rnd[N*W-1:0]), .s(sn), .c(cn));
        assign bad[g] = (so !== sn) || (co !== cn);
        reg [W-1:0] ref_sum;
        integer j;
        always @(*) begin ref_sum = '0; for (j = 0; j < N; j = j + 1) ref_sum = ref_sum + rnd[j*W +: W]; end
        assign sbad[g] = (W'(sn + cn) !== ref_sum);
    end endgenerate
    integer t, k, NV;
    initial begin
        if (!$value$plusargs("nv=%d", NV)) NV = 50000;
        for (t = 0; t < NV; t = t + 1) begin
            for (k = 0; k < 62; k = k + 1) rnd[k*32 +: 32] = (t % 7 == 0) ? 32'hffffffff : (t % 11 == 0) ? 32'h0 : $urandom;
            #1;
            if (bad != 0) begin errs = errs + 1; if (errs <= 5) $display("MISMATCH t %0d bad %b", t, bad); end
            if (sbad != 0) begin sumerr = sumerr + 1; if (sumerr <= 5) $display("SUMERR t %0d %b", t, sbad); end
        end
        $display("CSA_LOCKSTEP vectors %0d params %0d mismatches %0d sum_errors %0d %s", NV, NP, errs, sumerr, (errs == 0 && sumerr == 0) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
