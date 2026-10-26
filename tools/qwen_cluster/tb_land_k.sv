`timescale 1ns/1ps
// QW-CB16FULL2: lockstep bench of the native-census-safe ring halves qfd_c_land_w1k + qfd_c_land_r1k (qfd_c_land_k.sv)
// vs the reference qfd_c_land_w + qfd_c_land_r (qfd_c_land.sv): same rsi / i, random words, random reset episodes
// (stale ring data), 20k edges.  Compares the ring bank, the written flags and the read output on every edge.
module tb;
    parameter integer W = 514, D = 4, K = 2, AW = 2, N = 20000;
    reg ck = 0, rsi = 0;
    reg [W-1:0] i;
    localparam integer NGS = (W + 29) / 30;
    wire [D*W-1:0] bank_r, bank_d; wire [D*(AW+1)-1:0] epo_r, epo_d; wire [D-1:0] vld_r; wire [D*NGS-1:0] vld_d;
    reg vok; integer gg;
    wire [W-1:0] o_ref, o_dut;
    qfd_c_land_w   #(.W(W), .D(D))         uwr (.ck(ck), .rsi(rsi), .i(i), .bank(bank_r), .epo(epo_r), .vld(vld_r));
    qfd_c_land_r   #(.W(W), .D(D), .K(K))  urr (.ck(ck), .rsi(rsi), .bank(bank_r), .epo(epo_r), .vld(vld_r), .o(o_ref));
    qfd_c_land_w1k #(.W(W), .D(D))         uwd (.ck(ck), .rsi(rsi), .i(i), .bank(bank_d), .epo(epo_d), .vld(vld_d));
    qfd_c_land_r1k #(.W(W), .D(D), .K(K))  urd (.ck(ck), .rsi(rsi), .bank(bank_d), .epo(epo_d), .vld(vld_d), .o(o_dut));
    integer e, k, nz, mism, resets;
    always #1 ck = ~ck;
    initial begin
        nz = 0; mism = 0; resets = 0; i = 0;
        for (e = 0; e < N; e = e + 1) begin
            @(negedge ck);
            for (k = 0; k < W; k = k + 32) i[k +: 32] = $random;
            if (e < 8) rsi = 0;
            else if (($random & 1023) == 0) begin rsi = 0; resets = resets + 1; end
            else rsi = 1;
            @(posedge ck); #0.1;
            if (e > 4) begin
                vok = 1; for (gg = 0; gg < NGS; gg = gg + 1) if (vld_d[gg*D +: D] !== vld_r) vok = 0;
                if (o_ref !== o_dut || !vok || (e > 12 && bank_r !== bank_d)) begin
                    mism = mism + 1;
                    if (mism <= 3) $display("LAND_K_MISMATCH K=%0d edge=%0d o=%0d vld=%0d bank=%0d", K, e, o_ref !== o_dut, !vok, bank_r !== bank_d);
                end
                if (|o_ref) nz = nz + 1;
            end
        end
        if (mism == 0 && nz > N / 2 && resets > 3) begin
            $display("LAND_K_PASS K=%0d edges=%0d nonzero=%0d resets=%0d", K, N, nz, resets); $finish;
        end else begin
            $display("LAND_K_FAIL K=%0d mism=%0d nonzero=%0d resets=%0d", K, mism, nz, resets); $fatal(1, "fail");
        end
    end
endmodule
