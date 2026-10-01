`timescale 1ns/1ps
// W15 link-layer unit bench: one link direction between two dies with
// independent clock phases.  Die A sends a deterministic pseudo-random record
// stream (a function of A's global time only) plus credit pulses; die B checks
// order, payload and -- with DET = 1 -- that every record reaches its hub at
// exactly ts + DREL.  Prints a digest of (delivery cycle, payload) so runs
// with different seeds can be compared bit for bit and cycle for cycle.
module tb_w15b_link_unit #(
    parameter integer NVC = 1, PW = 64, CW = 2, TSW = 16,
    parameter integer WIRE_TX = 4, WIRE_RX = 4, AW_TX = 4, AW_RX = 6, NL = 2,
    parameter integer FRAME_CYCLES = 1, ENC_STAGES = 0, DEC_STAGES = 0,
    parameter integer DREL = 40, DET = 1,
    parameter real T_CORE = 0.92, T_LINK = 1.0, DLY_NS = 2.0, JSTATIC_NS = 0.5, WANDER_NS = 0.1,
    parameter integer NREC = 2000
);
    localparam integer BW = TSW + NVC + CW + NVC * PW, SW = BW + 1, NS = FRAME_CYCLES * NL, FRW = NS * SW + 32;
    integer seed, seed0, flip_at, send_pct;
    real pha, phb, phl;
    reg clk_a = 0, clk_b = 0, lclk = 0;
    reg go = 0;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("FLIP=%d", flip_at)) flip_at = -1;
        if (!$value$plusargs("PCT=%d", send_pct)) send_pct = 60;
        pha = T_CORE * (($unsigned($random(seed)) % 1000) / 1000.0);
        phb = T_CORE * (($unsigned($random(seed)) % 1000) / 1000.0);
        phl = T_LINK * (($unsigned($random(seed)) % 1000) / 1000.0);
        $display("PHASES seed=%0d a=%0.3f b=%0.3f l=%0.3f", seed0, pha, phb, phl);
        go = 1;
    end
    initial begin wait(go); #(pha); forever #(T_CORE/2) clk_a = ~clk_a; end
    initial begin wait(go); #(phb); forever #(T_CORE/2) clk_b = ~clk_b; end
    initial begin wait(go); #(phl); forever #(T_LINK/2) lclk = ~lclk; end
    // common reset release (the SYSREF-style time sync): every counter starts at its first edge after 20 ns
    reg rst_a = 0, rst_b = 0, rst_l = 0;
    always @(posedge clk_a) rst_a <= ($realtime > 20.0);
    always @(posedge clk_b) rst_b <= ($realtime > 20.0);
    always @(posedge lclk)  rst_l <= ($realtime > 20.0);
    reg [TSW-1:0] now_a = 0, now_b = 0;
    always @(posedge clk_a) if (rst_a) now_a <= now_a + 1'b1;
    always @(posedge clk_b) if (rst_b) now_b <= now_b + 1'b1;

    // sender: record k carries {k, ts}
    wire [NVC-1:0] rdy;
    reg  [31:0] sent = 0;
    function automatic [31:0] h(input [31:0] x);
        h = (x * 32'h9E3779B1) ^ (x >> 7);
    endfunction
    wire want = rst_a && (sent < NREC) && ((h(now_a) % 100) < send_pct);
    wire [NVC-1:0] vv = (want && rdy[0]) ? 1 : 0;
    wire [31:0]    hc = h(now_a + 99);
    wire [CW-1:0]  cp = (rst_a && sent < NREC) ? (hc[CW-1:0] & {CW{(h(now_a) % 3) == 0}}) : 0;
    wire [PW-1:0]  rec = {{(PW-48){1'b0}}, now_a, sent};
    always @(posedge clk_a) if (vv[0]) sent <= sent + 1;
    reg [31:0] crsent [0:CW-1];
    integer c;
    initial for (c = 0; c < CW; c = c + 1) crsent[c] = 0;
    always @(posedge clk_a) for (c = 0; c < CW; c = c + 1) if (cp[c]) crsent[c] = crsent[c] + 1;

    wire fv, rfv, rclk;
    wire [FRW-1:0] fd, rfd;
    wire ftx;
    ot_w15_link_tx #(.NVC(NVC), .PW(PW), .CW(CW), .TSW(TSW), .WIRE(WIRE_TX), .AW(AW_TX), .NL(NL),
                 .FRAME_CYCLES(FRAME_CYCLES), .ENC_STAGES(ENC_STAGES)) u_tx (
        .clk(clk_a), .rst_n(rst_a), .now(now_a), .vc_valid(vv), .vc_ready(rdy), .vc_rec(rec), .cr_pulse(cp),
        .lclk(lclk), .lrst_n(rst_l), .f_valid(fv), .f_data(fd), .fault(ftx), .stat_bundles(), .stat_gated_stall());
    ot_link_chan_model #(.FRW(FRW), .T_NS(T_LINK), .JDYN_FRAC(0.8)) u_ch (
        .DLY_NS(DLY_NS), .JSTATIC_NS(JSTATIC_NS), .WANDER_NS(WANDER_NS), .clk_tx(lclk), .f_valid(fv), .f_data(fd), .seed(seed0), .flip_at(flip_at),
        .rclk(rclk), .rf_valid(rfv), .rf_data(rfd));
    reg rst_r = 0;
    always @(posedge rclk) rst_r <= ($realtime > 20.0);
    wire [NVC-1:0] ov;
    wire [NVC*PW-1:0] orec;
    wire [CW-1:0] ocr;
    wire fcrc, flate, fovf;
    wire [TSW-1:0] amin, amax;
    wire [15:0] wmax;
    ot_w15_link_rx #(.NVC(NVC), .PW(PW), .CW(CW), .TSW(TSW), .WIRE(WIRE_RX), .AW(AW_RX), .NL(NL),
                 .FRAME_CYCLES(FRAME_CYCLES), .DEC_STAGES(DEC_STAGES)) u_rx (
        .rclk(rclk), .rrst_n(rst_r), .f_valid(rfv), .f_data(rfd), .clk(clk_b), .rst_n(rst_b), .now(now_b), .det(DET[0]), .drel(TSW'(DREL)),
        .vc_valid(ov), .vc_rec(orec), .cr_pulse(ocr), .fault_crc(fcrc), .fault_late(flate), .fault_ovf(fovf),
        .stat_min_age(amin), .stat_max_age(amax), .stat_max_wait(wmax), .stat_bundles());

    reg [31:0] got = 0, bad = 0, lmin = 32'hFFFF, lmax = 0;
    reg [63:0] dig = 64'hCBF29CE484222325;
    reg [31:0] crgot [0:CW-1];
    initial for (c = 0; c < CW; c = c + 1) crgot[c] = 0;
    always @(posedge clk_b) begin
        for (c = 0; c < CW; c = c + 1) if (ocr[c]) begin
            crgot[c] = crgot[c] + 1;
            dig = (dig ^ {32'd0, now_b, 14'd0, c[1:0]}) * 64'h100000001B3;
        end
        if (ov[0]) begin : chk
            reg [TSW-1:0] ts;
            reg [31:0] lat;
            ts = orec[47:32];
            lat = {16'd0, now_b - ts};
            if (orec[31:0] != got) bad = bad + 1;
            if (DET != 0 && lat != DREL) bad = bad + 1;
            if (lat < lmin) lmin = lat;
            if (lat > lmax) lmax = lat;
            dig = (dig ^ {now_b, orec[47:0]}) * 64'h100000001B3;
            got = got + 1;
        end
    end
    initial begin : fin
        integer cr_ok;
        wait (got == NREC);
        repeat (DREL + 50) @(posedge clk_b);
        cr_ok = 1;
        for (c = 0; c < CW; c = c + 1) if (crgot[c] != crsent[c]) cr_ok = 0;
        $display("LINKUNIT seed=%0d det=%0d recs=%0d bad=%0d hub_lat_min=%0d hub_lat_max=%0d head_age_min=%0d head_age_max=%0d wait_max=%0d credits_ok=%0d faults=%0d%0d%0d%0d digest=%016h %s",
                 seed0, DET, got, bad, lmin, lmax, amin, amax, wmax, cr_ok, ftx, fcrc, flate, fovf, dig,
                 (bad == 0 && cr_ok && !ftx && !fcrc && !flate && !fovf) ? "PASS" : "FAIL");
        $finish;
    end
    always @(posedge clk_b) if (fcrc && flip_at >= 0) begin
        $display("LINKUNIT seed=%0d crc_fault_detected=1 flip_at=%0d PASS_FAILCLOSED", seed0, flip_at);
        $finish;
    end
    initial begin #(NREC * 20.0 + 20000.0); $display("LINKUNIT TIMEOUT got=%0d", got); $finish; end
endmodule
