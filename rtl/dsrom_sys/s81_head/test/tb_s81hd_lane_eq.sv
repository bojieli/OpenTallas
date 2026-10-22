`timescale 1ns/1ps
// HEAD LANE (b) STACKED (STW-S81c-COLLA2-LANE 10-22): cycle-exact equivalence of the stacked lane (ot_s81hd_lane from
// ot_s81hd_lane_sc6.sv / _sc4.sv) against the CURRENT lane (ot_s81hd_lane.sv, renamed ot_s81hd_lane_ref by the run
// script, mutant hooks disabled).  Two loopback pairs (ref A<->B, dut A<->B) get the IDENTICAL stimulus of
// tb_s81hd_lane (static-schedule traffic with CRC-corruption windows / go-back-N replay, then A off-schedule so the
// TX buffer overflows), and every cycle from reset on, every output of every block is compared:
//   tx [511:0], rx_v, rx_d [552:0], flt [3:0]  (ref A vs dut A, ref B vs dut B).
// PASS needs 0 mismatches over NCYC cycles, >= 1000 flits delivered each way and the overflow fault raised (so the
// comparison covered traffic, replay and the fault path).  Mutants (+define) must FAIL.
module tb_s81hd_lane_eq;
    parameter integer P2 = 20000, NCYC = 21000;
    reg ck = 0, rst_n = 0; always #0.5 ck = ~ck;
    reg [31:0] rng = 32'h5e8d1a3c;
    reg tv [0:1]; reg [552:0] td [0:1];
    reg [511:0] imp [0:1];
    wire [511:0] txr [0:1], txd [0:1]; wire rvr [0:1], rvd [0:1]; wire [552:0] rdr [0:1], rdd [0:1];
    wire [3:0] fr [0:1], fd [0:1];
    ot_s81hd_lane_ref r_a (.ck(ck), .rst_n(rst_n), .chb(1'b1), .rx({2'b10, txr[1] ^ imp[1]}), .tx(txr[0]),
        .tx_v(tv[0]), .tx_d(td[0]), .rx_v(rvr[0]), .rx_d(rdr[0]), .flt(fr[0]));
    ot_s81hd_lane_ref r_b (.ck(ck), .rst_n(rst_n), .chb(1'b1), .rx({2'b10, txr[0] ^ imp[0]}), .tx(txr[1]),
        .tx_v(tv[1]), .tx_d(td[1]), .rx_v(rvr[1]), .rx_d(rdr[1]), .flt(fr[1]));
    ot_s81hd_lane d_a (.ck(ck), .rst_n(rst_n), .chb(1'b1), .rx({2'b10, txd[1] ^ imp[1]}), .tx(txd[0]),
        .tx_v(tv[0]), .tx_d(td[0]), .rx_v(rvd[0]), .rx_d(rdd[0]), .flt(fd[0]));
    ot_s81hd_lane d_b (.ck(ck), .rst_n(rst_n), .chb(1'b1), .rx({2'b10, txd[0] ^ imp[0]}), .tx(txd[1]),
        .tx_v(tv[1]), .tx_d(td[1]), .rx_v(rvd[1]), .rx_d(rdd[1]), .flt(fd[1]));
    function automatic [552:0] word(input integer side, input integer k);
        reg [31:0] h; integer b; begin
            h = 32'h9e3779b9 * (k + 1) ^ (side * 32'h85ebca6b);
            for (b = 0; b < 553; b = b + 1) begin word[b] = h[b % 32] ^ h[(b / 32 + k) % 32]; if (b % 32 == 31) h = h ^ (h << 13) ^ (h >> 7); end
        end endfunction
    integer c = 0, mm = 0, i, sk [0:1], rk [0:1], gap [0:1], ntx = 0;
    initial begin for (i = 0; i < 2; i = i + 1) begin sk[i] = 0; rk[i] = 0; gap[i] = 0; tv[i] = 0; td[i] = 0; imp[i] = 0; end end
    always @(negedge ck) begin
        c = c + 1;
        // compare every output of both blocks of the two pairs (before this cycle's stimulus changes)
        for (i = 0; i < 2; i = i + 1) begin
            if (txr[i] !== txd[i] || rvr[i] !== rvd[i] || flt_ne(fr[i], fd[i]) || (rvr[i] && rdr[i] !== rdd[i]) || (rdr[i] !== rdd[i])) begin
                mm = mm + 1;
                if (mm < 8) $display("LSC_EQ_MISMATCH cycle=%0d side=%0d tx=%0d rv=%b/%b rd=%0d flt=%b/%b", c, i,
                    txr[i] !== txd[i], rvr[i], rvd[i], rdr[i] !== rdd[i], fr[i], fd[i]);
            end
            if (rvr[i]) rk[i] = rk[i] + 1;
            if (|txr[i]) ntx = ntx + 1;
        end
        rst_n = (c >= 8);
        rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
        imp[0] = 0; imp[1] = 0;
        if ((c >= 6000 && c < 6004) || (c >= 13000 && c < 13020)) imp[0] = {rng, rng[15:0]} << 96;
        if ((c >= 9000 && c < 9003) || (c >= 16000 && c < 16010)) imp[1] = {rng[7:0], rng} << 300;
        for (i = 0; i < 2; i = i + 1) begin
            if (rst_n && tv[i]) sk[i] = sk[i] + 1;
            if (c >= P2 && i == 0) tv[i] = 1'b1;
            else tv[i] = rst_n && c > 40 && c < P2 - 400 && gap[i] >= 1 && rng[i * 3];
            gap[i] = tv[i] ? 0 : gap[i] + 1;
            td[i] = word(i, sk[i]);
        end
        if (c == NCYC) begin
            $display("LSC_EQ_STATS cycles=%0d mismatches=%0d sent=%0d/%0d received=%0d/%0d tx_active=%0d flt_ref=%b/%b flt_dut=%b/%b",
                c, mm, sk[0], sk[1], rk[1], rk[0], ntx, fr[0], fr[1], fd[0], fd[1]);
            if (mm != 0) $display("FAIL lsc_eq mismatches %0d", mm);
            else if (rk[0] < 1000 || rk[1] < 1000) $display("FAIL lsc_eq coverage: received %0d/%0d", rk[1], rk[0]);
            else if (fr[0][3] !== 1'b1) $display("FAIL lsc_eq coverage: overflow fault not exercised");
            else $display("PASS lsc_eq cycles %0d outputs exact, flits %0d/%0d, overflow fault matched", c, rk[1], rk[0]);
            $finish;
        end
    end
    function automatic flt_ne(input [3:0] a, input [3:0] b); flt_ne = (a !== b); endfunction
endmodule
