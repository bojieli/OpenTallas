`timescale 1ns/1ps
// Transaction-level bench for the HALF-RATE SU reducer (Claude:hbm-su 2026-10-07): reference = 16 x slice64_c12m +
// top1024_c12m on the fast clock, DUT = 16 x slice64_c12h + top1024_c12h (gated half-rate core).  One pre-generated
// stimulus sequence S[k] (random beats at 3/4 duty, random data): the reference takes S[k] in fast cycle k, the DUT in
// its k-th ph = 1 cycle (the interface contract: the controller's beat stream dilated x2; the reducer's TIME levels
// pair beats by cycle distance, so the reference must see the undilated stream).  Every result event (o_we lanes with
// their addr / data, o_ev with o_meta) must match in order, at one constant latency offset; fault runs must match
// in count; both drain.  OT_NEG_RED_HALF (tags one slow stage short) must FAIL.
module tb_red_half;
    parameter integer NCYC = 20000;
    parameter integer SEED = 1;
    localparam integer EW = 128 + 1 + 9 + 3072 + 4096;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    localparam integer SW = 1 + 32768 + 1024 + 1 + 1 + 4 + 1 + 3 + 1 + 8 + 1 + 24 + 5 + 9;
    localparam integer NS = (NCYC - 1200) / 2;
    reg [SW-1:0] S [0:NS-1];
    reg [SW-1:0] rs = 0, ds = 0;
    wire v, mx, sq, span, last, rnd; wire [32767:0] x; wire [1023:0] live; wire [3:0] lt; wire [2:0] l; wire [7:0] nres;
    wire [23:0] rbase; wire [4:0] rsh; wire [8:0] meta;
    wire dv_, dmx, dsq, dspan, dlast, drnd; wire [32767:0] dx; wire [1023:0] dlive; wire [3:0] dlt; wire [2:0] dl;
    wire [7:0] dnres; wire [23:0] drbase; wire [4:0] drsh; wire [8:0] dmeta;
    assign {v, x, live, mx, sq, lt, span, l, last, nres, rnd, rbase, rsh, meta} = rs;
    assign {dv_, dx, dlive, dmx, dsq, dlt, dspan, dl, dlast, dnres, drnd, drbase, drsh, dmeta} = ds;
    wire [7679:0] rlv, dlv; wire [15:0] rsf, dsf;
    genvar s;
    for (s = 0; s < 16; s = s + 1) begin : g_s
        ot_hdc_v41x_vred_slice64_c12m r (.clk(clk), .rst_n(rst_n), .v_in(v), .x_in(x[2048*s +: 2048]), .live_in(live[64*s +: 64]),
            .mx_in(mx), .sq_in(sq), .lv_o(rlv[480*s +: 480]), .fault_o(rsf[s]));
        ot_hdc_v41x_vred_slice64_c12h d (.clk(clk), .rst_n(rst_n), .v_in(dv_), .x_in(dx[2048*s +: 2048]), .live_in(dlive[64*s +: 64]),
            .mx_in(dmx), .sq_in(dsq), .lv_o(dlv[480*s +: 480]), .fault_o(dsf[s]));
    end
    wire [127:0] rwe, dwe; wire [3071:0] ra, da; wire [4095:0] rd, dd; wire [8:0] rm, dm; wire rev, dev, rb, db, rf, df;
    ot_hdc_v41x_vred_top1024_c12m rt (.clk(clk), .rst_n(rst_n), .v_in(v), .mx_in(mx), .lt_in(lt), .span_in(span), .l_in(l),
        .last_in(last), .nres_in(nres), .rnd_in(rnd), .rbase_in(rbase), .rsh_in(rsh), .meta_in(meta), .lv_in(rlv),
        .sfault_in(rsf), .o_we(rwe), .o_addr(ra), .o_data(rd), .o_meta(rm), .o_ev(rev), .busy(rb), .fault(rf));
    ot_hdc_v41x_vred_top1024_c12h dt (.clk(clk), .rst_n(rst_n), .v_in(dv_), .mx_in(dmx), .lt_in(dlt), .span_in(dspan), .l_in(dl),
        .last_in(dlast), .nres_in(dnres), .rnd_in(drnd), .rbase_in(drbase), .rsh_in(drsh), .meta_in(dmeta), .lv_in(dlv),
        .sfault_in(dsf), .o_we(dwe), .o_addr(da), .o_data(dd), .o_meta(dm), .o_ev(dev), .busy(db), .fault(df));
    function automatic [EW-1:0] pack(input [127:0] we, input ev, input [8:0] m, input [3071:0] a, input [4095:0] d);
        reg [3071:0] am; reg [4095:0] dmk; integer i;
        begin
            am = 0; dmk = 0;
            for (i = 0; i < 128; i = i + 1) if (we[i]) begin am[24*i +: 24] = a[24*i +: 24]; dmk[32*i +: 32] = d[32*i +: 32]; end
            pack = {we, ev, ev ? m : 9'd0, am, dmk};
        end
    endfunction
    reg [EW-1:0] rq [$]; integer rcq [$];
    integer cyc = 0, mism = 0, nev = 0, ndev = 0, lat = -1, latbad = 0, rfr = 0, dfr = 0, nbeat = 0, seed = SEED, w;
    reg rf_q = 0, df_q = 0;
    always @(negedge clk) if (rst_n) begin
        if (|rwe || rev) begin rq.push_back(pack(rwe, rev, rm, ra, rd)); rcq.push_back(cyc); nev = nev + 1; end
        if (|dwe || dev) begin
            ndev = ndev + 1;
            if (rq.size() == 0) begin mism = mism + 1; if (mism <= 5) $display("EXTRA DUT event cyc=%0d", cyc); end
            else begin
                if (pack(dwe, dev, dm, da, dd) !== rq[0]) begin mism = mism + 1;
                    if (mism <= 5) $display("MISMATCH cyc=%0d ref_cyc=%0d we %0d/%0d ev %0d/%0d", cyc, rcq[0], |dwe, |rq[0][EW-1 -: 128], dev, rq[0][EW-129]); end
                if (lat < 0) lat = cyc - 2 * rcq[0]; else if (cyc - 2 * rcq[0] != lat) latbad = latbad + 1;
                void'(rq.pop_front()); void'(rcq.pop_front());
            end
        end
        // fault: the reference holds it one fast cycle per affected (undilated) cycle, the DUT pulses once per slow
        // cycle, so the COUNTS of fault cycles match one to one (runs do not: a reference run of k cycles is k pulses)
        if (rf) rfr = rfr + 1;
        if (df) dfr = dfr + 1;
    end
    integer k, kd = 0;
    reg [32767:0] tx; reg [1023:0] tl;
    initial begin
        for (k = 0; k < NS; k = k + 1) begin
            for (w = 0; w < 1024; w = w + 1) tx[32*w +: 32] = {$random(seed)} & 32'hbfffffff;   // finite-ish fp32 mix
            for (w = 0; w < 32; w = w + 1) tl[32*w +: 32] = $random(seed);
            S[k] = {(($random(seed) & 3) != 0) ? 1'b1 : 1'b0, tx, tl, 1'($random(seed)), 1'($random(seed)), 4'($random(seed)),
                    1'($random(seed)), 3'({$random(seed)} % 7), 1'($random(seed)), 8'($random(seed)), 1'($random(seed)),
                    24'($random(seed)), 5'($random(seed)), 9'($random(seed))};
        end
        repeat (4) @(posedge clk); rst_n = 1;
        while (cyc < NCYC) begin
            @(posedge clk); #0.1
            rs = (cyc < NS) ? S[cyc] : {1'b0, S[0][SW-2:0]};
            if (dt.ph && kd < NS) begin ds = S[kd]; kd = kd + 1; end
            else ds = {1'b0, ds[SW-2:0]};
            if (rs[SW-1]) nbeat = nbeat + 1;
            cyc = cyc + 1;
        end
        $display("RED_HALF cycles=%0d beats=%0d ref_events=%0d dut_events=%0d left=%0d mismatches=%0d latency_2x_offset=%0d latency_var=%0d fault_cycles ref=%0d dut=%0d busy_end ref=%0d dut=%0d",
                 cyc, nbeat, nev, ndev, rq.size(), mism, lat, latbad, rfr, dfr, rb, db);
        if (mism != 0 || nev == 0 || ndev != nev || rq.size() != 0 || latbad != 0 || rfr != dfr || rb != db) $fatal(1, "RED_HALF FAIL");
        $display("RED_HALF PASS");
        $finish;
    end
endmodule
