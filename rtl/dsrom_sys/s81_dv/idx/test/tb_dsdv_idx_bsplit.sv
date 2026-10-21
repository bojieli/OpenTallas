`timescale 1ns/1ps
// DRIVE-S81-IDX4 (10-20): self-checking bench of dsdv_idx_bsplit (the slice iq split of band-port-B bo).  Random
// stream of SVC FRAME PROTOCOL v1.1 frames (header + len payload words, random idle gaps, back-to-back frames, len-0
// headers) of types {1, 2, 3, 7, 9, 12, 13, 14} (svc) and {4, 8, 10} (index), payload words drawn so that their bits
// [511:508] often look like index / svc types (a router that re-decodes payload words fails).  Checks every edge: o_i ==
// the word driven 1 edge earlier when it belongs to an index frame (else valid 0), o_s the same for svc frames; the
// payload of both outputs == the input word 1 edge earlier.  Prints TB_BS PASS / FAIL.  MUT 1 (type 10 on svc) must FAIL.
module tb_dsdv_idx_bsplit;
    parameter integer MUT = 0;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    reg  [512:0] i = 0;
    wire [512:0] o_s, o_i;
    dsdv_idx_bsplit #(.BW(513), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .i(i), .o_s(o_s), .o_i(o_i));
    integer cyc = 0, nerr = 0, n_i = 0, n_s = 0, left = 0, idxf = 0, k;
    reg [512:0] pw; reg pidx; reg pval;
    integer types_s [0:7]; integer types_i [0:2];
    initial begin
        types_s[0] = 1; types_s[1] = 2; types_s[2] = 3; types_s[3] = 7; types_s[4] = 9; types_s[5] = 12; types_s[6] = 13; types_s[7] = 14;
        types_i[0] = 4; types_i[1] = 8; types_i[2] = 10;
    end
    function automatic [511:0] rnd512();
        integer q; rnd512 = 512'd0;
        for (q = 0; q < 16; q = q + 1) rnd512[32 * q +: 32] = $urandom;
    endfunction
    initial begin
        pw = 0; pidx = 0; pval = 0;
        repeat (4) @(posedge ck);
        #0.2 rst_n = 1;
        repeat (4) @(posedge ck);
        for (cyc = 0; cyc < 20000; cyc = cyc + 1) begin
            @(posedge ck); #0.1;
            // check the outputs for the word driven before this edge
            if (rst_n && cyc > 0) begin
                if (o_i[0] !== (pval && pidx) || o_s[0] !== (pval && !pidx)) begin
                    nerr = nerr + 1; if (nerr < 8) $display("TB_BS valid mismatch cyc %0d o_i %0d o_s %0d exp v%0d idx%0d", cyc, o_i[0], o_s[0], pval, pidx);
                end
                if (pval && (o_i[512:1] !== pw[512:1] || o_s[512:1] !== pw[512:1])) begin
                    nerr = nerr + 1; if (nerr < 8) $display("TB_BS data mismatch cyc %0d", cyc);
                end
                if (o_i[0]) n_i = n_i + 1; if (o_s[0]) n_s = n_s + 1;
            end
            // next input word
            if ($urandom % 4 == 0) begin i = {rnd512(), 1'b0}; pval = 0; end      // idle (payload noise, valid 0)
            else begin
                i[512:1] = rnd512(); i[0] = 1'b1;
                if (left == 0) begin                                               // header
                    idxf = ($urandom % 2);
                    k = idxf ? types_i[$urandom % 3] : types_s[$urandom % 8];
                    i[512:509] = k[3:0];
                    left = ($urandom % 5 == 0) ? 0 : 1 + $urandom % 9;
                    i[492:481] = left[11:0];
                end else begin
                    if ($urandom % 2) i[512:509] = (($urandom % 2) ? 4'd10 : 4'd2);  // payload that looks like a header
                    left = left - 1;
                end
                pval = 1; pidx = idxf;
            end
            pw = i;
        end
        if (n_i < 1000 || n_s < 1000) begin nerr = nerr + 1; $display("TB_BS too few frames i %0d s %0d", n_i, n_s); end
        $display("TB_BS words idx %0d svc %0d errors %0d", n_i, n_s, nerr);
        if (nerr == 0) $display("TB_BS PASS"); else $display("TB_BS FAIL");
        $finish;
    end
endmodule
