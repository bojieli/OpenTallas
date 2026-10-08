`timescale 1ns/1ps
// Lockstep bench for the SAFE pin-register reducer (Claude:hbm-su 2026-10-06): reference = 16 x slice64_c12m +
// top1024_c12m (the round-11 margin reducer), DUT = 16 x slice64_c12s + top1024_c12s.  Same random stimulus every
// cycle; every DUT output at t + 4 must equal the reference output at t (o_we/o_addr/o_data/o_meta/o_ev/fault);
// busy: DUT busy must be high whenever the reference was busy 4 cycles earlier or a reduction is in flight; at the
// end both drained.  OT_NEG_RED_PREG (tags one stage short) must FAIL.
module tb_red_safe;
    parameter integer NCYC = 20000;
    parameter integer SEED = 1;
    localparam integer D = 4;
    parameter integer FL = 1;            // extra fault latency of the DUT top (c12s FREG)
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg v; reg [32767:0] x; reg [1023:0] live; reg mx, sq; reg [3:0] lt; reg span; reg [2:0] l; reg last;
    reg [7:0] nres; reg rnd; reg [23:0] rbase; reg [4:0] rsh; reg [8:0] meta;
    wire [7679:0] rlv, dlv; wire [15:0] rsf, dsf;
    genvar s;
    for (s = 0; s < 16; s = s + 1) begin : g_s
        ot_hdc_v41x_vred_slice64_c12m r (.clk(clk), .rst_n(rst_n), .v_in(v), .x_in(x[2048*s +: 2048]), .live_in(live[64*s +: 64]),
            .mx_in(mx), .sq_in(sq), .lv_o(rlv[480*s +: 480]), .fault_o(rsf[s]));
        ot_hdc_v41x_vred_slice64_c12s d (.clk(clk), .rst_n(rst_n), .v_in(v), .x_in(x[2048*s +: 2048]), .live_in(live[64*s +: 64]),
            .mx_in(mx), .sq_in(sq), .lv_o(dlv[480*s +: 480]), .fault_o(dsf[s]));
    end
    wire [127:0] rwe, dwe; wire [3071:0] ra, da; wire [4095:0] rd, dd; wire [8:0] rm, dm; wire rev, dev, rb, db, rf, df;
    ot_hdc_v41x_vred_top1024_c12m rt (.clk(clk), .rst_n(rst_n), .v_in(v), .mx_in(mx), .lt_in(lt), .span_in(span), .l_in(l),
        .last_in(last), .nres_in(nres), .rnd_in(rnd), .rbase_in(rbase), .rsh_in(rsh), .meta_in(meta), .lv_in(rlv),
        .sfault_in(rsf), .o_we(rwe), .o_addr(ra), .o_data(rd), .o_meta(rm), .o_ev(rev), .busy(rb), .fault(rf));
    ot_hdc_v41x_vred_top1024_c12s dt (.clk(clk), .rst_n(rst_n), .v_in(v), .mx_in(mx), .lt_in(lt), .span_in(span), .l_in(l),
        .last_in(last), .nres_in(nres), .rnd_in(rnd), .rbase_in(rbase), .rsh_in(rsh), .meta_in(meta), .lv_in(dlv),
        .sfault_in(dsf), .o_we(dwe), .o_addr(da), .o_data(dd), .o_meta(dm), .o_ev(dev), .busy(db), .fault(df));
    // reference outputs delayed D
    reg [127:0] hwe [0:D-1]; reg [3071:0] ha [0:D-1]; reg [4095:0] hd [0:D-1]; reg [8:0] hm [0:D-1];
    reg hev [0:D-1]; reg hf [0:D+1]; reg hb [0:D-1];
    integer i, cyc = 0, mism = 0, ev = 0, bmis = 0, seed = SEED, w;
    always @(posedge clk) begin
        for (i = D-1; i > 0; i = i - 1) begin hwe[i] <= hwe[i-1]; ha[i] <= ha[i-1]; hd[i] <= hd[i-1]; hm[i] <= hm[i-1];
            hev[i] <= hev[i-1]; hb[i] <= hb[i-1]; end
        for (i = D+1; i > 0; i = i - 1) hf[i] <= hf[i-1];
        hwe[0] <= rwe; ha[0] <= ra; hd[0] <= rd; hm[0] <= rm; hev[0] <= rev; hf[0] <= rf; hb[0] <= rb;
    end
    always @(negedge clk) if (rst_n && cyc > D + 2) begin
        if (dwe !== hwe[D-1] || (|dwe && (da !== ha[D-1] || dd !== hd[D-1])) || dev !== hev[D-1] || (dev && dm !== hm[D-1]) || df !== hf[D-1+FL]) begin
            mism = mism + 1; if (mism <= 5) $display("MISMATCH cyc=%0d we %0d/%0d ev %0d/%0d f %0d/%0d", cyc, |dwe, |hwe[D-1], dev, hev[D-1], df, hf[D-1+FL]);
        end
        if (hb[D-1] && !db) bmis = bmis + 1;
        if (|dwe || dev) ev = ev + 1;
    end
    task automatic stim(input integer on);
        begin
            v = on && (($random(seed) & 3) != 0);
            for (w = 0; w < 1024; w = w + 1) x[32*w +: 32] = {$random(seed)} & 32'hbfffffff;   // finite-ish fp32 mix
            live = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
                    $random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
                    $random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
                    $random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
            mx = $random(seed); sq = $random(seed); lt = $random(seed); span = $random(seed); l = $random(seed) % 7;
            last = $random(seed); nres = $random(seed); rnd = $random(seed); rbase = $random(seed); rsh = $random(seed);
            meta = $random(seed);
        end
    endtask
    initial begin
        stim(0); repeat (4) @(posedge clk); rst_n = 1;
        while (cyc < NCYC) begin @(posedge clk); #0.1 stim(cyc < NCYC - 400); cyc = cyc + 1; end
        $display("RED_SAFE cycles=%0d events=%0d mismatches=%0d busy_low_while_ref_busy=%0d busy_end ref=%0d dut=%0d", cyc, ev, mism, bmis, rb, db);
        if (mism != 0 || ev == 0 || bmis != 0 || rb != db) $fatal(1, "RED_SAFE FAIL");
        $display("RED_SAFE PASS");
        $finish;
    end
endmodule
