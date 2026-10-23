`timescale 1ns/1ps
// QW-CB16FULL: lockstep bench qfd_c_land_r1h (registered one-hot AND-OR read) vs qfd_c_land_r (runtime part-select),
// both fed by one qfd_c_land_w ring (W 514, D 4, K 1..3), random words, random reset episodes (stale ring data), 20k edges.
module tb;
    parameter integer W = 514, D = 4, K = 2, AW = 2, N = 20000;
    reg ck = 0, rsi = 0;
    reg [W-1:0] i;
    wire [D*W-1:0] bank; wire [D*(AW+1)-1:0] epo; wire [D-1:0] vld;
    wire [W-1:0] o_ref, o_dut;
    qfd_c_land_w   #(.W(W), .D(D))         uw (.ck(ck), .rsi(rsi), .i(i), .bank(bank), .epo(epo), .vld(vld));
    qfd_c_land_r   #(.W(W), .D(D), .K(K))  ur (.ck(ck), .rsi(rsi), .bank(bank), .epo(epo), .vld(vld), .o(o_ref));
    qfd_c_land_r1h #(.W(W), .D(D), .K(K))  ud (.ck(ck), .rsi(rsi), .bank(bank), .epo(epo), .vld(vld), .o(o_dut));
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
                if (o_ref !== o_dut) begin
                    mism = mism + 1;
                    if (mism <= 3) $display("LAND_R1H_MISMATCH K=%0d edge=%0d ref=%h dut=%h", K, e, o_ref[63:0], o_dut[63:0]);
                end
                if (|o_ref) nz = nz + 1;
            end
        end
        if (mism == 0 && nz > N / 2 && resets > 3) begin
            $display("LAND_R1H_PASS K=%0d edges=%0d nonzero=%0d resets=%0d", K, N, nz, resets); $finish;
        end else begin
            $display("LAND_R1H_FAIL K=%0d mism=%0d nonzero=%0d resets=%0d", K, mism, nz, resets); $fatal(1, "fail");
        end
    end
endmodule
