`timescale 1ps/1fs
// tb_s81_pdie_col (TW-S81/SERDES 2026-10-19): the landed COLUMN SerDes ot_pdie_serdes_col in the two-die link bench of
// tb_s81_pdie_link (die B 300 ppm slow, one random bit error in about every second PMA word A -> B, corrected by KP4).
// MODE 0: column <-> column; MODE 1: column A -> flat reference ot_pdie_serdes B; MODE 2: reference A -> column B
// (the column is wire-compatible with the reference die: same pads, same FEC frame, only fixed latency differs).
// PASS: >= NB - 400 data beats at B, all in order and exact, st(B) live and no fault.
// Mutants (on the column dies): MUT 1 landing 0 (syn -> dly words) bypassed, MUT 2 landing 0 read one edge late:
// words and corrections misalign -> FAIL.
// LS (FAM-S81-SERDES-R4 11-21): the die instantiates the column as #(.LOCKSAFE(1), .HOLD_EDGES(64)) with pma_lock on a pad
// (serdes__t* wrappers, test_serdes_h_form); the forms OT_S81_RCK_RELAY4 / OT_S81_SERDES_COL_PIN / OT_S81_SERDES_BOOT_RELEASE3
// require it (the column's own elaboration checks).  Under those defines the bench builds the die form: LOCKSAFE=1,
// HOLD_EDGES=64, pma_lock rising LOCK_AT core edges after rst release, and the source starts after the guarded release
// (TX_START) so beat 0 is the first beat the released link carries.  Without them: LOCKSAFE=0, unchanged.
`ifdef OT_S81_RCK_RELAY4
`define TB_COL_LS_DEFAULT 1
`elsif OT_S81_SERDES_COL_PIN
`define TB_COL_LS_DEFAULT 1
`elsif OT_S81_SERDES_BOOT_RELEASE3
`define TB_COL_LS_DEFAULT 1
`else
`define TB_COL_LS_DEFAULT 0
`endif
module tb_s81_pdie_col;
    parameter integer MODE = 0, MUT = 0, NB = 6000;
    parameter integer LS = `TB_COL_LS_DEFAULT, LOCK_AT = 4;
    localparam integer TX_START = (LS != 0) ? 400 : 40;
    reg lock = 0;
    reg ca = 0, cb = 0, rst = 0;
    always #416.5 ca = ~ca;
    always #416.62495 cb = ~cb;
    // Check the achieved periods: precision quantization must not erase the CDC offset.
    realtime measured_core_ps, measured_peer_ps, measured_ppm;
    initial begin
        @(posedge ca); measured_core_ps = $realtime;
        @(posedge ca); measured_core_ps = $realtime - measured_core_ps;
        @(posedge cb); measured_peer_ps = $realtime;
        @(posedge cb); measured_peer_ps = $realtime - measured_peer_ps;
        measured_ppm = (measured_peer_ps / measured_core_ps - 1.0) * 1.0e6;
        $display("TB_S81_PDIE_CLOCK core_ps=%0.3f peer_ps=%0.3f ppm=%0.3f",
                 measured_core_ps, measured_peer_ps, measured_ppm);
        if (measured_core_ps < 832.999 || measured_core_ps > 833.001 ||
            measured_ppm < 299.0 || measured_ppm > 301.0)
            $fatal(1, "PHY clock-period/CDC-offset fixture failed");
    end
    reg [511:0] txa = 512'd2; wire [511:0] rxb, rxa; wire [1:0] sta, stb;
    wire [543:0] pa, pb; wire tca, tcb; reg [543:0] pa_e;
    generate if (MODE == 2) begin : g_a_ref
        ot_pdie_serdes u_a (.clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb), .pma_rck(tcb));
    end else begin : g_a_col
        ot_pdie_serdes_col #(.MUT(MUT), .LOCKSAFE(LS), .HOLD_EDGES(64)) u_a (.pma_lock(lock), .clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb), .pma_rck(tcb));
    end endgenerate
    generate if (MODE == 1) begin : g_b_ref
        ot_pdie_serdes u_b (.clk(cb), .rst(rst), .tx(512'd2), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pa_e), .pma_rck(tca));
    end else begin : g_b_col
        ot_pdie_serdes_col #(.MUT(MUT), .LOCKSAFE(LS), .HOLD_EDGES(64)) u_b (.pma_lock(lock), .clk(cb), .rst(rst), .tx(512'd2), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pa_e), .pma_rck(tca));
    end endgenerate
    reg err_on = 0; integer err_bit = 0;
    always @* begin
        pa_e = pa;
        if (err_on) pa_e[err_bit] = ~pa[err_bit];
    end
    always @(posedge tca) begin err_on <= ($urandom % 2) == 0; err_bit <= $urandom % 544; end
    integer k = 0, sent = 0, cyc = 0;
    function automatic [511:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ {64'h0, {448{n[0]}}} & ~512'h3;
    endfunction
    always @(negedge ca) begin
        cyc = cyc + 1;
        if (cyc > TX_START && sent < NB) begin
            if (cyc % 256 == 0) txa <= 512'd2;
            else begin txa <= beat(sent); sent = sent + 1; end
        end else txa <= 512'd2;
    end
    integer got = 0, bad = 0, idles = 0;
    always @(posedge cb) if (rst) begin
        if (rxb[1] && !rxb[0]) idles = idles + 1;
        else begin
            if (rxb !== beat(got)) begin bad = bad + 1; if (bad < 4) $display("ERR beat %0d", got); end
            got = got + 1;
        end
    end
    initial begin
        repeat (8) @(posedge ca); rst = 1;
        if (LS != 0) begin repeat (LOCK_AT) @(posedge ca); lock = 1; end
        wait (sent == NB);
        repeat (500) @(posedge cb);
        $display("TB_S81_PDIE_COL LS=%0d", LS);
        $display("TB_S81_PDIE_COL MODE=%0d MUT=%0d sent=%0d got=%0d bad=%0d idles_seen=%0d stA=%b stB=%b", MODE, MUT, sent, got,
                 bad, idles, sta, stb);
        if (got >= NB - 400 && bad == 0 && stb == 2'b10) $display("TB_S81_PDIE_COL PASS"); else $display("TB_S81_PDIE_COL FAIL");
        $finish;
    end
endmodule
