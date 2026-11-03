// DIE-HBM-60/LEC C6 (11-03) bench: ot_hdc_sk_step0_en_phys after the sign-constant change (b_m) against the module
// before it (renamed ot_hdc_sk_step0_en_phys_old by sk_step0_c6_check.sh), same random stimulus every edge.
// PASS = (1) bbad_q / abad_q and every b_q magnitude bit are identical (4-state ===) at every edge, (2) every old
// b_q sign bit, once loaded (not X), equals the new one, (3) every new sign bit is 0, (4) every word is loaded.
`timescale 1ns/1ps
module sk_step0_c6_tb;
    parameter integer N = 4000;
    parameter integer SEED = 1;
    reg clk = 0;
    reg sk_en_i = 0, load = 0, pa = 0, pb = 0;
    reg [511:0] in_e = 0;
    wire [511:0] bq_o, bq_n;
    wire bb_o, bb_n, ab_o, ab_n;
    ot_hdc_sk_step0_en_phys_old #(.EN_LAND(1), .EN_DELAY(2)) u_old (.clk(clk), .sk_en_i(sk_en_i), .load(load),
        .in_e(in_e), .pa(pa), .pb(pb), .b_q(bq_o), .bbad_q(bb_o), .abad_q(ab_o));
    ot_hdc_sk_step0_en_phys #(.EN_LAND(1), .EN_DELAY(2)) u_new (.clk(clk), .sk_en_i(sk_en_i), .load(load),
        .in_e(in_e), .pa(pa), .pb(pb), .b_q(bq_n), .bbad_q(bb_n), .abad_q(ab_n));
    integer t, k, errs = 0, seed, loads = 0;
    reg [15:0] seen = 0;
    always #1 clk = ~clk;
    task rnd_word(input integer i);
        reg [31:0] w;
        begin
            w = $random(seed);
            // mostly finite positive values (the operating range), some sign / Inf / NaN / zero / subnormal cases
            case ($unsigned($random(seed)) % 8)
                0: w[31] = 1'b1;
                1: w[30:23] = 8'hFF;
                2: w[30:0] = 31'd0;
                3: w[30:23] = 8'h00;
                default: begin w[31] = 1'b0; w[30:23] = 8'd100 + ($unsigned($random(seed)) % 50); end
            endcase
            in_e[32*i +: 32] = w;
        end
    endtask
    initial begin
        seed = SEED;
        for (t = 0; t < N; t = t + 1) begin
            @(negedge clk);
            sk_en_i = ($unsigned($random(seed)) % 3) != 0;
            load = ($unsigned($random(seed)) % 5) == 0;
            pa = ($unsigned($random(seed)) % 3) == 0;
            pb = ($unsigned($random(seed)) % 3) == 0;
            for (k = 0; k < 16; k = k + 1) rnd_word(k);
            @(posedge clk); #0.5;
            if (bb_o !== bb_n || ab_o !== ab_n) begin
                errs = errs + 1;
                if (errs < 10) $display("MISMATCH t=%0d bad flags old %b%b new %b%b", t, bb_o, ab_o, bb_n, ab_n);
            end
            for (k = 0; k < 16; k = k + 1) begin
                if (bq_o[32*k +: 31] !== bq_n[32*k +: 31]) begin
                    errs = errs + 1;
                    if (errs < 10) $display("MISMATCH t=%0d word %0d magnitude old %h new %h", t, k,
                                            bq_o[32*k +: 31], bq_n[32*k +: 31]);
                end
                if (bq_n[32*k + 31] !== 1'b0) begin
                    errs = errs + 1;
                    if (errs < 10) $display("MISMATCH t=%0d word %0d new sign %b", t, k, bq_n[32*k + 31]);
                end
                if (bq_o[32*k + 31] !== 1'bx) begin
                    if (!seen[k]) loads = loads + 1;
                    seen[k] = 1'b1;
                    if (bq_o[32*k + 31] !== bq_n[32*k + 31]) begin
                        errs = errs + 1;
                        if (errs < 10) $display("MISMATCH t=%0d word %0d loaded sign old %b new %b", t, k,
                                                bq_o[32*k + 31], bq_n[32*k + 31]);
                    end
                end else if (seen[k]) begin
                    errs = errs + 1;
                    if (errs < 10) $display("MISMATCH t=%0d word %0d old sign back to X", t, k);
                end
            end
        end
        if (errs == 0 && seen == 16'hFFFF)
            $display("SK_STEP0_C6 PASS: %0d edges, seed %0d, 16/16 words loaded, magnitude+flags identical, sign 0", N, SEED);
        else
            $display("SK_STEP0_C6 FAIL: %0d mismatches, words loaded %b", errs, seen);
        $finish;
    end
endmodule
