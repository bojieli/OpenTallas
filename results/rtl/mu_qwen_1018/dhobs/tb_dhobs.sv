`timescale 1ns/1ps
// MU-DQ-DHUSER 10-19: bench of qfd_sys_face_mu_dhobs (the die's tt_ctlm.dh_user observer, default = compiled lists).
// Plays the face's per-token h_start sequence (stages 1..36, 8 x 37, 0 = the compiled STG_SEQ) as seq_dh for P token
// periods: h_start pulses at LFSR gaps (0 = back to back), random tok / pos / dh_prog bits, random stage field between
// h_starts.  PASS: dh_user == 0 and res_user == 0 on every edge (OPSEG: every face start is user 0), mu_fault stays 0.
// +bad=N: the N-th h_start carries a wrong stage (a face T image off the compiled list): PASS = mu_fault rises on the edge
// after it (detected) and stays (sticky).  -GMUT=2 (leaf stage check dropped) + +bad=N: TB_DHOBS FAIL (the mutant witness).
module tb_dhobs;
    parameter integer MUT = 0;
    localparam integer NS = 45;
    reg ck = 1'b0;
    always #1 ck = ~ck;
    reg rst_n = 1'b0;
    reg [186:0] sd = '0;
    wire [1:0] du, ru; wire mf;
    qfd_sys_face_mu_dhobs #(.MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .seq_dh(sd), .dh_user(du), .res_user(ru), .mu_fault(mf));
    function automatic [5:0] stg(input integer k);
        stg = (k < 36) ? 6'(k + 1) : (k < 44) ? 6'd37 : 6'd0;
    endfunction
    function automatic [31:0] lf(input [31:0] x); lf = {x[30:0], x[31] ^ x[21] ^ x[1] ^ x[0]}; endfunction
    integer P = 40, p, k, g, gap, err = 0, nhs = 0, bad = -1, det = -1;
    reg [31:0] x = 32'hC0FFEE11;
    initial begin
        if (!$value$plusargs("bad=%d", bad)) bad = -1;
        repeat (3) @(negedge ck);
        rst_n = 1'b1;
        for (p = 0; p < P; p = p + 1)
            for (k = 0; k < NS; k = k + 1) begin
                x = lf(lf(lf(x))); gap = x[3:0] < 4 ? 0 : x[6:0];
                for (g = 0; g < gap; g = g + 1) begin
                    @(negedge ck); x = lf(x);
                    sd = {x[24:0], x, x, x, x, x[29:0]}; sd[42] = 1'b0;                  // idle: random fields, no h_start
                    @(posedge ck); #0.1;
                    if (du !== 2'd0 || ru !== 2'd0) begin err = err + 1; if (err < 5) $display("idle user %0d res %0d", du, ru); end
                    if (bad < 0 && mf !== 1'b0) begin err = err + 1; if (err < 5) $display("fault p%0d k%0d", p, k); end
                end
                @(negedge ck); x = lf(x);
                sd = {x[24:0], x, x, x, x, x[29:0]}; sd[42] = 1'b1;
                sd[41:36] = (nhs == bad) ? stg(k) ^ 6'd5 : stg(k);
                #0.5;
                if (du !== 2'd0) begin err = err + 1; if (err < 5) $display("h_start user %0d", du); end
                @(posedge ck); #0.1;
                if (bad >= 0 && nhs == bad && mf === 1'b1) det = nhs;
                if (bad >= 0 && nhs > bad && mf !== 1'b1) begin err = err + 1; if (err < 5) $display("fault not sticky"); end
                if (bad < 0 && mf !== 1'b0) begin err = err + 1; if (err < 5) $display("fault on good stream p%0d k%0d", p, k); end
                nhs = nhs + 1;
            end
        if (bad >= 0) begin
            if (det == bad && err == 0) $display("TB_DHOBS PASS (bad stage at h_start %0d detected on its edge) h_starts %0d", bad, nhs);
            else $display("TB_DHOBS FAIL (bad stage at %0d not detected: det %0d err %0d)", bad, det, err);
        end else if (err == 0) $display("TB_DHOBS PASS h_starts %0d periods %0d (dh_user = res_user = 0, mu_fault 0)", nhs, P);
        else $display("TB_DHOBS FAIL errors %0d", err);
        $finish;
    end
endmodule
