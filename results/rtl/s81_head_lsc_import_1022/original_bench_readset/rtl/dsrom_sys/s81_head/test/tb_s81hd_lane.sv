`timescale 1ns/1ps
// HD-CTLGATE (S81-HEAD 10-21): ot_s81hd_lane behavioural bench.  Two head-die lane blocks A / B, SerDes loopback through
// the lanes (A.rx <- B.tx, B.rx <- A.tx; ot_pdie_serdes st = {live 1, fault 0}), so every core flit A.tx_d goes
// A adapter TX buffer -> A lane (gearbox, endpoint, CRC, replay) -> B lane -> B adapter RX pin flops -> B.rx_d.
// Phase 1 (cycles 40 .. P2): both sides send on the STATIC schedule the ctl uses (<= 1 frame per 2 cycles, random
//   gaps), with CRC-corruption windows (NAK / go-back-N replay) on both directions.  Check: every flit delivered on
//   rx of side j is exactly the next flit sent on tx of side 1-j (in order, once, bit-exact), >= 1000 flits each way,
//   and no adapter fault (flt[3]) on either side.
// Phase 2 (P2 ..): side A violates the schedule (tx_v every cycle, above the lane rate 0.764), so its 3-flit buffer
//   fills.  Check: A raises the sticky static-overflow fault flt[3]; B stays clean.
// Mutants (each must FAIL): +define+OT_S81HD_LANE_MUT_OVF (overflow never flagged), +define+OT_S81HD_LANE_MUT_RP
//   (TX read pointer sticks -> wrong flits).  Prints the mean tx_v -> rx_v latency (schedule ledger).
module tb_s81hd_lane;
    parameter integer P2 = 20000, NCYC = 21000;
    reg ck = 0, rst_n = 0; always #0.5 ck = ~ck;
    reg [31:0] rng = 32'h5e8d1a3c;
    reg tv [0:1]; reg [552:0] td [0:1];
    wire [511:0] tx [0:1]; wire rv [0:1]; wire [552:0] rd [0:1]; wire [3:0] flt [0:1];
    reg [511:0] imp [0:1];
    ot_s81hd_lane u_a (.ck(ck), .rst_n(rst_n), .chb(1'b1), .rx({2'b10, tx[1] ^ imp[1]}), .tx(tx[0]),
        .tx_v(tv[0]), .tx_d(td[0]), .rx_v(rv[0]), .rx_d(rd[0]), .flt(flt[0]));
    ot_s81hd_lane u_b (.ck(ck), .rst_n(rst_n), .chb(1'b1), .rx({2'b10, tx[0] ^ imp[0]}), .tx(tx[1]),
        .tx_v(tv[1]), .tx_d(td[1]), .rx_v(rv[1]), .rx_d(rd[1]), .flt(flt[1]));
    function automatic [552:0] word(input integer side, input integer k);
        reg [31:0] h; integer b; begin
            h = 32'h9e3779b9 * (k + 1) ^ (side * 32'h85ebca6b);
            for (b = 0; b < 553; b = b + 1) begin word[b] = h[b % 32] ^ h[(b / 32 + k) % 32]; if (b % 32 == 31) h = h ^ (h << 13) ^ (h >> 7); end
        end endfunction
    integer c = 0, err = 0, i, sk [0:1], rk [0:1], gap [0:1], f1 = 0; longint lat = 0; integer ts [0:1][0:4095];
    initial begin for (i = 0; i < 2; i = i + 1) begin sk[i] = 0; rk[i] = 0; gap[i] = 0; tv[i] = 0; td[i] = 0; imp[i] = 0; end end
    always @(negedge ck) begin
        c = c + 1;
        rst_n = (c >= 8);
        for (i = 0; i < 2; i = i + 1) if (rst_n) begin
            // the flit on rx of side i came from tx of side 1-i
            if (rv[i] && c < P2) begin
                if (rd[i] !== word(1 - i, rk[i])) begin err = err + 1; if (err < 8) $display("HD_LANE_DATA_ERR cycle=%0d side=%0d flit=%0d", c, i, rk[i]); end
                if (rk[i] >= sk[1 - i]) begin err = err + 1; if (err < 8) $display("HD_LANE_DUP_ERR cycle=%0d side=%0d flit=%0d sent=%0d", c, i, rk[i], sk[1 - i]); end
                lat = lat + (c - ts[1 - i][rk[i] % 4096]);
                rk[i] = rk[i] + 1;
            end
            if (tv[i]) begin ts[i][sk[i] % 4096] = c - 1; sk[i] = sk[i] + 1; end
        end
        if (c < P2 && (flt[0][3] || flt[1][3])) f1 = 1;
        rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
        imp[0] = 0; imp[1] = 0;
        if ((c >= 6000 && c < 6004) || (c >= 13000 && c < 13020)) imp[0] = {rng, rng[15:0]} << 96;
        if ((c >= 9000 && c < 9003) || (c >= 16000 && c < 16010)) imp[1] = {rng[7:0], rng} << 300;
        for (i = 0; i < 2; i = i + 1) begin
            if (c >= P2 && i == 0) tv[i] = 1'b1;                                     // phase 2: A off-schedule
            else tv[i] = rst_n && c > 40 && c < P2 - 400 && gap[i] >= 1 && rng[i * 3];  // <= 1 per 2 cycles
            gap[i] = tv[i] ? 0 : gap[i] + 1;
            td[i] = word(i, sk[i]);
        end
        if (c == NCYC) begin
            $display("HD_LANE_STATS sent=%0d/%0d received=%0d/%0d mean_latency=%0d errors=%0d phase1_fault=%0d flt=%b/%b",
                sk[0], sk[1], rk[1], rk[0], lat / ((rk[0] + rk[1]) > 0 ? (rk[0] + rk[1]) : 1), err, f1, flt[0], flt[1]);
            if (err != 0 || rk[0] < 1000 || rk[1] < 1000) $display("FAIL hd_lane data: errors %0d received %0d/%0d", err, rk[1], rk[0]);
            else if (f1 != 0) $display("FAIL hd_lane adapter fault on the static schedule");
            else if (flt[0][3] !== 1'b1) $display("FAIL hd_lane static overflow not flagged (A flt %b)", flt[0]);
            else if (flt[1][3] !== 1'b0) $display("FAIL hd_lane spurious fault on B (flt %b)", flt[1]);
            else $display("PASS hd_lane flits %0d/%0d exact, overflow flagged", rk[1], rk[0]);
            $finish;
        end
    end
endmodule
