`timescale 1ns/1ps
// tb_dsfd_capt_cd_eq (S-VM-CAPT-CD 2026-10-16): randomized lockstep of ctrl_c/dsfd_capt_cd.sv (DUT) against the frozen
// 2314b2b4d form (test/dsfd_capt_cd_ref1013.sv).  t_cd compared after EVERY ckv edge, including through random
// reset pulses.  Stimulus: f_st redrawn at each negedge with per-segment biases on busy f_st[0] / done f_st[2] so the
// handshake runs (busy -> done rising -> toggle), plus fully random segments.  +SEED=<n> +N=<cycles>.
// With -DSYNTHESIS the DUT's ICG-gated bank is simulated through a behavioural ICG (latch on CLK low + AND).
// -DCAPCD_PINREG (S-VM-CAPT-CD2 2026-10-16): the DUT is dsfd_capt_cd #(.PINREG(1)) and the reference is fed f_st delayed
// by exactly ONE ckv edge (f_st_d, sampled at posedge like the DUT pin registers): the golden alignment moves by +1 ckv
// and nothing else (every t_cd bit, every edge, through resets).
// Verdict: "CAPCD_EQ cycles=.. fires=.. toggles=.. resets=.. mismatches=.. EQ_PASS|EQ_FAIL".
`ifdef SYNTHESIS
module ICGx2_ASAP7_75t_R (input wire CLK, input wire ENA, input wire SE, output wire GCLK);
    reg en_l;
    always @(CLK or ENA or SE) if (!CLK) en_l = ENA | SE;
    assign GCLK = CLK & en_l;
endmodule
`endif
module tb_dsfd_capt_cd_eq;
    reg ckv = 1'b0, rsv = 1'b0;
    reg [13:0] f_st = 14'd0;
    wire [11:0] cd_ref, cd_dut;
`ifdef CAPCD_PINREG
    localparam integer PR = 1;
    reg [13:0] f_st_d = 14'd0;
    always @(posedge ckv) f_st_d <= f_st;       // the +1 ckv alignment of the pin-registered DUT
    wire [13:0] f_ref = f_st_d;
`else
    localparam integer PR = 0;
    wire [13:0] f_ref = f_st;
`endif
    dsfd_capt_cd_ref1013 u_ref (.ckv(ckv), .rsv(rsv), .f_st(f_ref), .t_cd(cd_ref));
    dsfd_capt_cd #(.PINREG(PR)) u_dut (.ckv(ckv), .rsv(rsv), .f_st(f_st), .t_cd(cd_dut));
    integer seed = 1, n = 200000, i, mm = 0, fires = 0, togs = 0, rsts = 0, seg = 0, pb = 50, pd = 50;
    reg tq = 1'b0;
    always #1 ckv = ~ckv;
    // reference phase completions (its enable, sampled before the edge)
    always @(posedge ckv) if (u_ref.rv_s[1] && f_ref[2] && !u_ref.dr_q && u_ref.armed && !f_ref[0]) fires = fires + 1;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("N=%d", n)) n = 200000;
        rsv = 1'b0; repeat (3) @(negedge ckv); rsv = 1'b1;
        for (i = 0; i < n; i = i + 1) begin
            @(negedge ckv);
            // compare the state after the posedge just passed
            if (cd_ref !== cd_dut) begin mm = mm + 1; if (mm < 6) $display("CAPCD_EQ MISMATCH cyc=%0d ref=%h dut=%h", i, cd_ref, cd_dut); end
            if (cd_ref[11] !== tq) begin togs = togs + 1; tq = cd_ref[11]; end
            if (seg == 0) begin seg = 20 + ($random(seed) & 255); pb = $random(seed) & 127; pd = $random(seed) & 127; end
            seg = seg - 1;
            f_st = $random(seed);
            f_st[0] = (($random(seed) & 127) < pb);
            f_st[2] = (($random(seed) & 127) < pd);
            // occasional reset pulse (async assert at negedge, release a few cycles later)
            if ((($random(seed)) & 4095) == 7) begin rsv = 1'b0; rsts = rsts + 1; end
            else if (!rsv && (($random(seed) & 3) == 0)) rsv = 1'b1;
        end
        $display("CAPCD_EQ cycles=%0d fires=%0d toggles=%0d resets=%0d mismatches=%0d %s", n, fires, togs, rsts, mm,
                 (mm == 0 && fires > 100 && togs > 100 && rsts > 0) ? "EQ_PASS" : "EQ_FAIL");
        $finish;
    end
endmodule
