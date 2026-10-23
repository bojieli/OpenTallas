`timescale 1ns/1ps
// Lockstep: ot_pl_land_vector_reset_w/r (D=4) vs ot_pl_seam_w/r, random data, random shared reset pulses.
// MUT 0: seam K = land K (expect PASS); MUT 1: seam K+1 (expect FAIL); MUT 2: seam rsi age +1 on the read half (FAIL).
module tb_ot_pl_seam;
    parameter integer W = 53, K = 2, MUT = 0, N = 20000;
    localparam integer CH = (W + 23) / 24;
    reg ck = 0; always #5 ck = ~ck;
    reg [W-1:0] i;
    reg [CH-1:0] rsi, rsi_d;
    wire [4*W-1:0] bank; wire [4*3-1:0] epo; wire [4*CH-1:0] vld;
    wire [W-1:0] o_ref, o_dut, q;
    ot_pl_land_vector_reset_w #(.W(W), .D(4), .CHUNK_BITS(24)) u_lw (.ck(ck), .rsi(rsi), .i(i), .bank(bank), .epo(epo), .vld(vld));
    ot_pl_land_vector_reset_r #(.W(W), .D(4), .K(K), .CHUNK_BITS(24)) u_lr (.ck(ck), .rsi(rsi), .bank(bank), .epo(epo), .vld(vld), .o(o_ref));
    ot_pl_seam_w #(.W(W), .CHUNK_BITS(24)) u_sw (.ck(ck), .rsi(rsi), .i(i), .q(q));
    ot_pl_seam_r #(.W(W), .K(MUT == 1 ? K + 1 : K), .CHUNK_BITS(24)) u_sr (.ck(ck), .rsi(MUT == 2 ? rsi_d : rsi), .d(q), .o(o_dut));
    integer t, err = 0, nz = 0, rst_left = 0;
    initial begin
        rsi = 0; rsi_d = 0; i = 0;
        for (t = 0; t < N; t = t + 1) begin
            @(negedge ck);
            if (o_ref !== o_dut) begin err = err + 1; if (err < 5) $display("MISMATCH t=%0d ref=%h dut=%h", t, o_ref, o_dut); end
            if (o_ref != 0) nz = nz + 1;
            i = {$urandom, $urandom, $urandom};
            if (rst_left > 0) rst_left = rst_left - 1;
            else if (t < 10 || $urandom_range(0, 999) < 3) rst_left = $urandom_range(1, 12);
            rsi_d = rsi;
            rsi = (rst_left > 0) ? {CH{1'b0}} : {CH{1'b1}};
        end
        $display("SEAM_LOCKSTEP %s W=%0d K=%0d MUT=%0d cycles=%0d nonzero=%0d mismatches=%0d",
                 (err == 0 && nz > N/4) ? "PASS" : "FAIL", W, K, MUT, N, nz, err);
        $finish;
    end
endmodule
