`timescale 1ns/1ps
// tb_s81ph_link_ep (CLAUDE S81-PH collective): two ot_s81ph_link_ep (one per die) cross-wired through four
// ot_dsrom_link_chan (A->B forward, B->A reverse of that link; B->A forward, A->B reverse) against two
// ot_dsrom_link_ct (pinned original, internal channels with the SAME error injection), one per direction.
// LOCKSTEP: every cycle, in_ready, out_valid / out_data / out_last of each direction must be identical, and the
// per-direction counters must match at the end.  The sources push a random flit stream; out_ready is random.
// PASS line: "TB_S81PH_LINK_EP PASS".
module tb_s81ph_link_ep;
    parameter integer FB = 69, CR = 64, SQ = 8, CH = 20, EF = 13, ER = 7, EO = 3, PN = 0, PD = 1, SR = 0;
    parameter integer N = 3000, SEED = 1;
    localparam integer W = FB * 8;
    localparam integer FFW = SQ + 1 + W + 32, RFW = 1 + SQ + $clog2(CR + 1) + 32;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [63:0] rs = 64'h9E3779B97F4A7C15 ^ SEED;
    function [31:0] rnd(input integer dummy);
        begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); rnd = rs[31:0]; end
    endfunction
    // sources (one per direction: 0 = A->B, 1 = B->A)
    reg  [1:0] iv; reg [W-1:0] id [0:1]; reg [1:0] il; reg [1:0] ordy;
    integer sent [0:1]; integer got [0:1];
    wire [1:0] rdy_ref, rdy_dut;
    wire [1:0] ov_ref, ov_dut, ol_ref, ol_dut;
    wire [W-1:0] od_ref [0:1]; wire [W-1:0] od_dut [0:1];
    wire [31:0] r_tx [0:1], r_rx [0:1], r_crc [0:1], r_nak [0:1], r_rep [0:1], r_retx [0:1];
    wire [31:0] d_tx [0:1], d_rx [0:1], d_crc [0:1], d_nak [0:1], d_rep [0:1], d_retx [0:1];
    wire [1:0] r_flt, d_flt;
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_ref
        ot_dsrom_link_ct #(.FLIT_BYTES(FB), .TX_STAGES(2), .RX_STAGES(3), .CHANNEL_CYCLES(CH), .CREDITS(CR),
            .SEQW(SQ), .ERR_PERIOD_FWD(EF), .ERR_PERIOD_REV(ER), .ERR_OFFSET(EO + g), .PHY_NUM(PN), .PHY_DEN(PD)) u (
            .clk(clk), .rst_n(rst_n), .channel_cycles(16'd0),
            .in_valid(iv[g]), .in_ready(rdy_ref[g]), .in_data(id[g]), .in_last(il[g]),
            .out_valid(ov_ref[g]), .out_ready(ordy[g]), .out_data(od_ref[g]), .out_last(ol_ref[g]),
            .credit_stalls(), .fault(r_flt[g]), .fault_code(), .st_flits_tx(r_tx[g]), .st_flits_rx_ok(r_rx[g]),
            .st_crc_err(r_crc[g]), .st_naks(r_nak[g]), .st_replays(r_rep[g]), .st_timeouts(), .st_retx_flits(r_retx[g]),
            .st_max_replay_occ());
    end endgenerate
    // DUT: die A = ep0 (sender of link 0, receiver of link 1); die B = ep1 (sender of link 1, receiver of link 0)
    wire [1:0] ftv, rtv, frv, rrv; wire [FFW-1:0] ft [0:1]; wire [FFW-1:0] fr [0:1];
    wire [RFW-1:0] rt [0:1]; wire [RFW-1:0] rr [0:1];
    generate for (g = 0; g < 2; g = g + 1) begin : g_dut
        ot_s81ph_link_ep #(.FLIT_BYTES(FB), .TX_STAGES(2), .RX_STAGES(3), .CHANNEL_CYCLES(CH), .CREDITS(CR),
            .SEQW(SQ), .PHY_NUM(PN), .PHY_DEN(PD), .SRAM(SR)) u (
            .clk(clk), .rst_n(rst_n), .ch_b(1'b0),
            .in_valid(iv[g]), .in_ready(rdy_dut[g]), .in_data(id[g]), .in_last(il[g]),
            // ep g receives link 1-g
            .out_valid(ov_dut[1-g]), .out_ready(ordy[1-g]), .out_data(od_dut[1-g]), .out_last(ol_dut[1-g]),
            .f_tx_v(ftv[g]), .f_tx(ft[g]), .f_rx_v(frv[g]), .f_rx(fr[g]), .r_tx_v(rtv[g]), .r_tx(rt[g]),
            .r_rx_v(rrv[g]), .r_rx(rr[g]),
            .credit_stalls(), .fault(d_flt[g]), .fault_code(), .st_flits_tx(d_tx[g]), .st_flits_rx_ok(d_rx[1-g]),
            .st_crc_err(d_crc[g]), .st_naks(d_nak[1-g]), .st_replays(d_rep[g]), .st_timeouts(), .st_retx_flits(d_retx[g]),
            .st_max_replay_occ());
        // forward channel of link g: ep g -> ep 1-g (ct's u_fwd: stride 37); reverse of link g: ep 1-g -> ep g (stride 11)
        ot_dsrom_link_chan #(.W(FFW), .MAXD(CH), .ERR_PERIOD(EF), .ERR_OFFSET(EO + g), .ERR_STRIDE(37)) u_f (
            .clk(clk), .rst_n(rst_n), .delay(16'd0), .in_valid(ftv[g]), .in_data(ft[g]),
            .out_valid(frv[1-g]), .out_data(fr[1-g]), .err_injected());
        ot_dsrom_link_chan #(.W(RFW), .MAXD(CH), .ERR_PERIOD(ER), .ERR_OFFSET(EO + g), .ERR_STRIDE(11)) u_r (
            .clk(clk), .rst_n(rst_n), .delay(16'd0), .in_valid(rtv[1-g]), .in_data(rt[1-g]),
            .out_valid(rrv[g]), .out_data(rr[g]), .err_injected());
    end endgenerate
    integer k, cyc = 0, errs = 0;
    reg [W:0] sb [0:1][0:N-1];   // scoreboard: every accepted input, in order
    function [W-1:0] rnd_w(input integer s);
        integer j; begin for (j = 0; j < W; j = j + 32) rnd_w[j +: 32] = rnd(0); end
    endfunction
    initial begin
        iv = 0; il = 0; ordy = 0; id[0] = 0; id[1] = 0; sent[0] = 0; sent[1] = 0; got[0] = 0; got[1] = 0;
        repeat (5) @(posedge clk); rst_n = 1;
    end
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        for (k = 0; k < 2; k = k + 1) begin
            if (rdy_dut[k] !== rdy_ref[k]) begin errs = errs + 1; if (errs < 10) $display("MISMATCH in_ready dir %0d cyc %0d", k, cyc); end
            if (ov_dut[k] !== ov_ref[k] || (ov_ref[k] && (od_dut[k] !== od_ref[k] || ol_dut[k] !== ol_ref[k]))) begin
                errs = errs + 1; if (errs < 10) $display("MISMATCH out dir %0d cyc %0d v %b/%b", k, cyc, ov_dut[k], ov_ref[k]); end
            if (ov_dut[k] && ordy[k]) begin
                if (got[k] >= N || {ol_dut[k], od_dut[k]} !== sb[k][got[k]]) begin
                    errs = errs + 1; if (errs < 10) $display("SCOREBOARD dir %0d flit %0d wrong", k, got[k]); end
                got[k] = got[k] + 1;
            end
            if (iv[k] && rdy_ref[k]) begin if (sent[k] < N) sb[k][sent[k]] = {il[k], id[k]}; sent[k] = sent[k] + 1; end
            // next stimulus
            if (!iv[k] || rdy_ref[k]) begin
                iv[k] <= (sent[k] + (iv[k] && rdy_ref[k] ? 1 : 0) < N) && ((rnd(0) & 3) != 0);
                id[k] <= rnd_w(0); il[k] <= rnd(0);
            end
            ordy[k] <= (rnd(0) & 7) != 0;
        end
        if (cyc > 40 * N + 20000 || (sent[0] == N && sent[1] == N && got[0] == N && got[1] == N && cyc > 100)) begin
            for (k = 0; k < 2; k = k + 1) begin
                if (d_tx[k] != r_tx[k] || d_rx[k] != r_rx[k] || d_nak[k] != r_nak[k] || d_rep[k] != r_rep[k] || d_retx[k] != r_retx[k]) begin
                    errs = errs + 1; $display("MISMATCH counters dir %0d tx %0d/%0d rx %0d/%0d nak %0d/%0d rep %0d/%0d", k, d_tx[k], r_tx[k], d_rx[k], r_rx[k], d_nak[k], r_nak[k], d_rep[k], r_rep[k]);
                end
            end
            if (d_crc[0] + d_crc[1] != r_crc[0] + r_crc[1]) begin errs = errs + 1; $display("MISMATCH crc sum"); end
            if (got[0] != N || got[1] != N) begin errs = errs + 1; $display("INCOMPLETE got %0d %0d of %0d", got[0], got[1], N); end
            if (|r_flt || |d_flt) begin errs = errs + 1; $display("FAULT ref %b dut %b", r_flt, d_flt); end
            $display("STATS cyc %0d flits %0d/%0d tx %0d %0d retx %0d %0d replays %0d %0d naks %0d %0d crc_err %0d",
                cyc, got[0], got[1], r_tx[0], r_tx[1], r_retx[0], r_retx[1], r_rep[0], r_rep[1], r_nak[0], r_nak[1], r_crc[0] + r_crc[1]);
            if (errs == 0 && r_rep[0] + r_rep[1] > 0) $display("TB_S81PH_LINK_EP PASS");
            else $display("TB_S81PH_LINK_EP FAIL errs %0d", errs);
            $finish;
        end
    end
endmodule
