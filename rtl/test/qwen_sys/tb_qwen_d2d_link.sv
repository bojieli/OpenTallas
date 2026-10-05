`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Unit bench of ot_qwen_d2d_link: two link ends A and B joined by two
// ot_qwen_d2d_chan directions.  Each end's engine side sends NREC records
// (a counter in the low bits, an LFSR in the rest) at a random rate and
// returns engine credits at a random rate.  Checks: every record arrives
// exactly once, in order, bit-exact; every credit arrives exactly once; under
// injected bit errors (+FLIP=<period> on both directions) every error is
// detected (CRC) and recovered by replay; with +BREAK the B->A direction
// corrupts every flit after training and A must latch link_fault.
// ---------------------------------------------------------------------------
module tb_qwen_d2d_link (input wire clk);
    localparam integer PW = 554, LAT = 12;
    localparam integer FW = 32 + 1 + 1 + 8 + 1 + 8 + 1 + 1 + 3 + PW;
    reg rst_n = 0;
    integer cyc = 0, nrec = 2000, flip = 0, brk = 0, seed = 1;
    wire [FW-1:0] a_tx, b_tx, ab_f, ba_f;
    wire ab_v, ba_v;
    integer ab_n, ba_n;
    reg  a_uv, b_uv, a_ucr, b_ucr;
    wire a_ur, b_ur, a_dv, b_dv, a_dcr, b_dcr, a_up, b_up, a_ft, b_ft;
    reg  [PW-1:0] a_rec, b_rec;
    wire [PW-1:0] a_drec, b_drec;
    wire [31:0] a_crc, a_rep, a_drop, a_sent, b_crc, b_rep, b_drop, b_sent;
    ot_qwen_d2d_link #(.PW(PW), .TMO(64)) A (.clk(clk), .rst_n(rst_n),
        .up_valid(a_uv), .up_ready(a_ur), .up_rec(a_rec), .up_cr(a_ucr),
        .dn_valid(a_dv), .dn_rec(a_drec), .dn_cr(a_dcr),
        .tx_flit(a_tx), .rx_valid(ba_v), .rx_flit(ba_f),
        .link_up(a_up), .link_fault(a_ft), .n_crc_err(a_crc), .n_replay(a_rep), .n_seq_drop(a_drop), .n_sent(a_sent));
    ot_qwen_d2d_link #(.PW(PW), .TMO(64)) B (.clk(clk), .rst_n(rst_n),
        .up_valid(b_uv), .up_ready(b_ur), .up_rec(b_rec), .up_cr(b_ucr),
        .dn_valid(b_dv), .dn_rec(b_drec), .dn_cr(b_dcr),
        .tx_flit(b_tx), .rx_valid(ab_v), .rx_flit(ab_f),
        .link_up(b_up), .link_fault(b_ft), .n_crc_err(b_crc), .n_replay(b_rep), .n_seq_drop(b_drop), .n_sent(b_sent));
    integer fp_ab, fp_ba;
    ot_qwen_d2d_chan #(.FW(FW), .LAT(LAT)) cab (.clk(clk), .rst_n(rst_n), .in_flit(a_tx), .out_valid(ab_v), .out_flit(ab_f),
        .flip_period(fp_ab), .flip_start(200), .flip_bit(17), .n_flipped(ab_n));
    ot_qwen_d2d_chan #(.FW(FW), .LAT(LAT)) cba (.clk(clk), .rst_n(rst_n), .in_flit(b_tx), .out_valid(ba_v), .out_flit(ba_f),
        .flip_period(fp_ba), .flip_start(brk ? 400 : 233), .flip_bit(301), .n_flipped(ba_n));

    function automatic [PW-1:0] payload(input integer side, input integer k);
        reg [PW+31:0] x; integer i; reg [31:0] h;
        begin
            h = 32'h9E37_79B9 * (k + 1) ^ (side ? 32'h5bd1e995 : 32'h1b873593);
            for (i = 0; i < PW / 32 + 1; i = i + 1) begin
                h = h ^ (h << 13); h = h ^ (h >> 17); h = h ^ (h << 5);
                x[32*i +: 32] = h;
            end
            x[31:0] = k;
            payload = x[PW-1:0];
        end
    endfunction

    integer a_k = 0, b_k = 0, a_got = 0, b_got = 0, bad = 0;
    integer a_cr_sent = 0, b_cr_sent = 0, a_cr_got = 0, b_cr_got = 0;
    integer rs;
    reg [63:0] lfsr;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1;
        // engine sides: offer records at ~70%, credits at ~30%
        if (a_uv && a_ur) a_k = a_k + 1;
        if (b_uv && b_ur) b_k = b_k + 1;
        if (a_ucr) a_cr_sent = a_cr_sent + 1;
        if (b_ucr) b_cr_sent = b_cr_sent + 1;
        lfsr = lfsr ^ (lfsr << 13); lfsr = lfsr ^ (lfsr >> 7); lfsr = lfsr ^ (lfsr << 17);
        rs = lfsr[31:0];
        a_uv <= (a_k < nrec) && rs[2:0] != 0 && rs[2:0] != 1;
        b_uv <= (b_k < nrec) && rs[5:3] != 0 && rs[5:3] != 3;
        a_ucr <= rst_n && (a_cr_sent < nrec) && rs[9:8] == 0;
        b_ucr <= rst_n && (b_cr_sent < nrec) && rs[11:10] == 0;
        a_rec <= payload(0, (a_uv && a_ur) ? a_k : a_k);
        b_rec <= payload(1, b_k);
        // receive checks
        if (b_dv) begin
            if (b_drec !== payload(0, b_got)) begin bad = bad + 1; if (bad < 5) $display("A->B mismatch at %0d", b_got); end
            b_got = b_got + 1;
        end
        if (a_dv) begin
            if (a_drec !== payload(1, a_got)) begin bad = bad + 1; if (bad < 5) $display("B->A mismatch at %0d", a_got); end
            a_got = a_got + 1;
        end
        if (b_dcr) b_cr_got = b_cr_got + 1;
        if (a_dcr) a_cr_got = a_cr_got + 1;
        if (brk && a_ft) begin
            $display("BREAK link_fault latched at cycle %0d replays=%0d crc_err=%0d", cyc, a_rep, a_crc);
            $display("PASS");
            $finish;
        end
        if (!brk && b_got == nrec && a_got == nrec && a_cr_got == b_cr_sent && b_cr_got == a_cr_sent
            && a_cr_sent == nrec && b_cr_sent == nrec) begin
            $display("LINK flip_period=%0d cycles=%0d recs=%0d/%0d credits=%0d/%0d flipped=%0d/%0d crc_err=%0d/%0d replays=%0d/%0d seq_drops=%0d/%0d mismatches=%0d faults=%0d/%0d",
                     flip, cyc, b_got, a_got, b_cr_got, a_cr_got, ab_n, ba_n, b_crc, a_crc, a_rep, b_rep, b_drop, a_drop, bad, a_ft, b_ft);
            if (bad == 0 && !a_ft && !b_ft && (b_crc <= ab_n && ab_n - b_crc <= LAT && a_crc <= ba_n && ba_n - a_crc <= LAT)) $display("PASS"); else $display("FAIL");
            $finish;
        end
        if (cyc > 400000) begin
            $display("TIMEOUT got=%0d/%0d credits=%0d/%0d up=%0d/%0d fault=%0d/%0d", b_got, a_got, b_cr_got, a_cr_got, a_up, b_up, a_ft, b_ft);
            $display("FAIL"); $finish;
        end
    end
    initial begin
        a_uv = 0; b_uv = 0; a_ucr = 0; b_ucr = 0;
        if (!$value$plusargs("FLIP=%d", flip)) flip = 0;
        if (!$value$plusargs("NREC=%d", nrec)) nrec = 2000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        lfsr = 64'h9E3779B97F4A7C15 ^ seed;
        if ($test$plusargs("BREAK")) brk = 1;
        fp_ab = brk ? 0 : flip;
        fp_ba = brk ? 1 : flip;
    end
endmodule
