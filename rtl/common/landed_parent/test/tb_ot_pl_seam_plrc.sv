`timescale 1ns/1ps
// Miter: ot_pl_seam_w_plr (reference) vs ot_pl_seam_w_plrc (registered per-chunk clear), random data and reset pulses.
// MODE 0: rse == rsi waveform (the real d14 leaf): expect 0 diffs.  MODE 1: rse independent: each diff within 2 edges of an event.
module tb_ot_pl_seam_plrc;
    parameter integer W = 53, MODE = 0, N = 40000;
    localparam integer CH = (W + 23) / 24;
    reg ck = 0; always #5 ck = ~ck;
    reg [W-1:0] i; reg [CH-1:0] rsi; reg rse;
    wire [W-1:0] qa, qb;
    ot_pl_seam_w_plr  #(.W(W), .CHUNK_BITS(24), .RSREG(1)) u_a (.ck(ck), .rsi(rsi), .rse(rse), .ir(i), .q(qa));
    ot_pl_seam_w_plrc #(.W(W), .CHUNK_BITS(24), .RSREG(1)) u_b (.ck(ck), .rsi(rsi), .rse(rse), .ir(i), .q(qb));
    integer t, err = 0, nz = 0, ra = 0, rb = 0, last_ev = -10, far = 0;
    reg [CH-1:0] rsi_p; reg rse_p;
    initial begin
        rsi = 0; rse = 0; i = 0; rsi_p = 0; rse_p = 0;
        for (t = 0; t < N; t = t + 1) begin
            @(negedge ck);
            if (qa !== qb) begin
                err = err + 1; if (t - last_ev > 2) far = far + 1;
                if (err < 4) $display("DIFF t=%0d a=%h b=%h", t, qa, qb);
            end
            if (qa != 0) nz = nz + 1;
            i = {$urandom, $urandom, $urandom};
            if (ra > 0) ra = ra - 1; else if (t < 10 || $urandom_range(0, 999) < 3) ra = $urandom_range(1, 12);
            if (rb > 0) rb = rb - 1; else if (t < 10 || $urandom_range(0, 999) < 3) rb = $urandom_range(1, 12);
            rsi_p = rsi; rse_p = rse;
            rsi = (ra > 0) ? {CH{1'b0}} : {CH{1'b1}};
            rse = (MODE == 0) ? rsi[0] : ((rb > 0) ? 1'b0 : 1'b1);
            if (rsi !== rsi_p || rse !== rse_p) last_ev = t;
        end
        $display("SEAM_PLRC MODE=%0d %s cycles=%0d nonzero=%0d diffs=%0d diffs_far_from_event=%0d",
                 MODE, (nz > N/4 && far == 0 && (MODE != 0 || err == 0)) ? "PASS" : "FAIL", N, nz, err, far);
        $finish;
    end
endmodule
