`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM 4-SLICE + RING + STAR COMPOSITION BENCH (el1011-hbm-b2-vm, SPEC v0.4): four ot_vms_slice (sid 0..3) on the
// CW and CCW rings (both wide, 2 VCs sharing each channel), S relay stages (ot_vms_relay) on every hop, and the COLL
// star (one 2,130-b edge a slice, S relay stages) driven by a behavioural coll source.  Golden = a behavioural VM (one main space of 262,144
// words + one mirror window), updated in each client's issue order (every region has exactly one writer):
//   phase 2  per slice: 4 packet clients -- reads / word-masked writes of their own main sectors in ALL 4 slices (local,
//            CW 1-2 hops, CCW 1 hop), mirror writes (local + broadcast) and mirror reads of their own mirror sectors,
//            each response checked in order against the golden; 2 wide write groups per slice writing their own
//            MIRROR sectors (8-lane WBC broadcasts, CW copy -> sid+1/+2, CCW copy -> sid+3) and own main sectors;
//            COLL star records (8 sectors, per-word masks) into all 4 slices.
//   phase 3  after every slice's mirror_busy fell: client 0 of every slice reads the whole mirror window in use and the
//            main sectors it hosts; every word must equal the golden (the four mirror copies are identical).
// PASS = 0 mismatches, no fault status.  Mutants: BMUT=1 (a mirror write not broadcast), CMUT=2 (every 8th VC0 ring
// credit dropped), CMUT=3 (CCW stops return VC1 credits on VC0: VC mixing on the shared channel), HMUT=1 (wrong slice
// routing) must FAIL (mismatch or timeout).
module tb_vms_ring4;
    parameter integer S = 2, HMUT = 0, BMUT = 0, CMUT = 0, SEED = 1, NPK = 300, NWG = 200, NKQ = 40;
    parameter integer RS = 3;                       // lane-group relay stages: credits 4 + 2 RS a wide lane (SPEC v0.8)
    localparam integer NC = 4, RG = 2, WG = 2, LQC = 4 + 2 * RS;
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;
    // ---------------------------------------------------------------- 4 slices + ring
    reg  [NC*338-1:0] cq [0:3]; wire [NC*274-1:0] cr [0:3];
    reg  [WG*8*281-1:0] wq [0:3]; wire [WG*8-1:0] wq_cr [0:3], wq_done [0:3];
    reg  [2129:0] vcb [0:3]; wire vcb_cr [0:3]; wire [7:0] kq_done [0:3];
    wire [8*18-1:0] bst [0:3]; wire [2:0] hst [0:3]; wire [1:0] mbs [0:3]; wire [3:0] mb;
    wire [2223:0] cwo [0:3], cwi [0:3]; wire [1:0] cwo_cr [0:3], cwi_cr [0:3];
    wire [2223:0] ccwo [0:3], ccwi [0:3]; wire [1:0] ccwo_cr [0:3], ccwi_cr [0:3];
    genvar s, k;
    for (s = 0; s < 4; s = s + 1) begin : g_s
        wire [RG*8-1:0] rqcr; wire [RG*8*257-1:0] rr; wire [7:0] dqd;
        wire [2129:0] sf [0:S]; wire scr [0:S];
        assign sf[0] = vcb[s]; assign vcb_cr[s] = scr[0];
        ot_vms_slice #(.NC(NC), .RG(RG), .WG(WG), .RRS({RG{4'(RS)}}), .WRS({WG{4'(RS)}}), .BMUT(BMUT), .HMUT(HMUT), .CMUT(CMUT)) u (.clk(clk), .rst_n(rst_n), .sid(2'(s)),
            .cq(cq[s]), .cr(cr[s]), .rq('0), .rq_cr(rqcr), .rr(rr), .wq(wq[s]), .wq_cr(wq_cr[s]), .wq_done(wq_done[s]),
            .dq('0), .dq_done(dqd), .vcb(sf[S]), .vcb_cr(scr[S]), .kq_done(kq_done[s]),
            .cw_in(cwi[s]), .cw_in_cr(cwi_cr[s]), .cw_out(cwo[s]), .cw_out_cr(cwo_cr[s]),
            .ccw_in(ccwi[s]), .ccw_in_cr(ccwi_cr[s]), .ccw_out(ccwo[s]), .ccw_out_cr(ccwo_cr[s]),
            .bank_status(bst[s]), .hub_status(hst[s]), .mirror_busy(mbs[s]));
        assign mb[s] = |mbs[s];
        // CW hop s -> s+1 and CCW hop s -> s-1, S relay stages each
        wire [2223:0] cf [0:S]; wire [1:0] cc [0:S]; wire [2223:0] nf [0:S]; wire [1:0] nc_ [0:S];
        assign cf[0] = cwo[s]; assign cwi[(s + 1) % 4] = cf[S]; assign cc[S] = cwi_cr[(s + 1) % 4]; assign cwo_cr[s] = cc[0];
        assign nf[0] = ccwo[s]; assign ccwi[(s + 3) % 4] = nf[S]; assign nc_[S] = ccwi_cr[(s + 3) % 4]; assign ccwo_cr[s] = nc_[0];
        for (k = 0; k < S; k = k + 1) begin : g_r
            ot_vms_relay #(.W(2224), .C(2)) rc (.clk(clk), .rst_n(rst_n), .f_in(cf[k]), .f_out(cf[k+1]), .cr_in(cc[k+1]), .cr_out(cc[k]));
            ot_vms_relay #(.W(2224), .C(2)) rn (.clk(clk), .rst_n(rst_n), .f_in(nf[k]), .f_out(nf[k+1]), .cr_in(nc_[k+1]), .cr_out(nc_[k]));
            ot_vms_relay #(.W(2130), .C(1)) rs (.clk(clk), .rst_n(rst_n), .f_in(sf[k]), .f_out(sf[k+1]), .cr_in(scr[k+1]), .cr_out(scr[k]));
        end
    end
    // ---------------------------------------------------------------- golden
    reg [255:0] gm [int];                      // key = {m, S15}
    function automatic [255:0] gget(input integer key); gget = gm.exists(key) ? gm[key] : 256'd0; endfunction
    function automatic [255:0] merge(input [255:0] o, input [255:0] d, input [7:0] wm);
        reg [255:0] r; begin r = o; for (integer w = 0; w < 8; w = w + 1) if (wm[w]) r[w*32 +: 32] = d[w*32 +: 32]; merge = r; end
    endfunction
    function automatic [255:0] rnd256(input integer dummy);
        reg [255:0] r; begin for (integer q = 0; q < 8; q = q + 1) r[q*32 +: 32] = $urandom; rnd256 = r; end
    endfunction
    function automatic [337:0] pkreq(input reg we, input reg m, input [14:0] sec, input [255:0] d, input [7:0] wm, input [15:0] tag);
        reg [31:0] bm; begin for (integer w = 0; w < 8; w = w + 1) bm[4*w +: 4] = {4{wm[w]}}; pkreq = {1'b1, we, 11'd0, m, sec, 5'd0, d, we ? bm : 32'd0, tag}; end
    endfunction
    // regions (x = 13-bit sector within a slice / the mirror window)
    //   owner o = s*4 + c: main x = 1024 + o*64 + j in every slice d; mirror x = o*32 + j
    //   wide group (s, g): mirror x = 512 + (s*2 + g)*64 + j; main x = 4096 + g*256 + j in slice s
    //   coll star: mirror x = 1024 + j (j < 256), 8-sector records
    // ---------------------------------------------------------------- drivers
    integer phase = 0, cyc = 0, fails = 0;
    integer pi [0:3][0:NC-1], po [0:3][0:NC-1], pd [0:3][0:NC-1];
    reg [272:0] ex [0:3][0:NC-1][0:7]; integer eh [0:3][0:NC-1], et [0:3][0:NC-1];
    integer wi [0:3][0:WG-1], wcr [0:3][0:WG*8-1], wdn [0:3];
    integer ki = 0, kcr [0:3], kdn [0:3];
    integer bi [0:3], bd [0:3];
    localparam integer NB = 1280 + 1024;       // phase 3 reads per slice: mirror 0..1279 + main 1024..2047
    initial begin
        void'($urandom(SEED));
        for (integer a = 0; a < 4; a = a + 1) begin
            for (integer c = 0; c < NC; c = c + 1) begin pi[a][c] = 0; po[a][c] = 0; pd[a][c] = 0; eh[a][c] = 0; et[a][c] = 0; end
            for (integer g = 0; g < WG; g = g + 1) wi[a][g] = 0;
            for (integer l = 0; l < WG*8; l = l + 1) wcr[a][l] = LQC;
            kcr[a] = 2;
            wdn[a] = 0; kdn[a] = 0; bi[a] = 0; bd[a] = 0;
        end
    end
    function automatic [273:0] rsp(input [15:0] tag, input reg we, input [255:0] d); rsp = {1'b1, tag, we, we ? 256'd0 : d}; endfunction
    always @(posedge clk) if (rst_n) begin : drive
        cyc <= cyc + 1;
        for (integer a = 0; a < 4; a = a + 1) begin cq[a] <= '0; wq[a] <= '0; vcb[a] <= '0; end
        for (integer a = 0; a < 4; a = a + 1) begin
            // ---- responses: checked in order against the expectation queued at issue
            for (integer c = 0; c < NC; c = c + 1) if (cr[a][c*274 + 273]) begin
                if (ex[a][c][eh[a][c]] !== cr[a][c*274 +: 273]) begin
                    if (fails < 10) $display("MISMATCH slice %0d client %0d phase %0d: got tag %0d %h exp tag %0d %h", a, c, phase,
                        cr[a][c*274 + 257 +: 16], cr[a][c*274 +: 64], ex[a][c][eh[a][c]][272:257], ex[a][c][eh[a][c]][63:0]);
                    fails = fails + 1;
                end
                eh[a][c] = (eh[a][c] + 1) % 8; po[a][c] = po[a][c] - 1; pd[a][c] = pd[a][c] + 1;
            end
            for (integer l = 0; l < WG*8; l = l + 1) begin if (wq_cr[a][l]) wcr[a][l] = wcr[a][l] + 1; if (wq_done[a][l]) wdn[a] = wdn[a] + 1; end
            if (vcb_cr[a]) kcr[a] = kcr[a] + 1;
            for (integer l = 0; l < 8; l = l + 1) if (kq_done[a][l]) kdn[a] = kdn[a] + 1;
            if (phase == 2) begin
                // ---- packet clients
                for (integer c = 0; c < NC; c = c + 1) if (pi[a][c] < NPK && po[a][c] < 4 && $urandom % 2 == 0) begin : pk
                    integer o, r, key, x, d; reg we, m; reg [14:0] sec; reg [255:0] dat; reg [7:0] wm;
                    o = a*4 + c; r = $urandom % 100; dat = rnd256(0); wm = 8'($urandom) | 8'h01;
                    if (r < 60) begin m = 1'b0; d = $urandom % 4; x = 1024 + o*64 + $urandom % 64; sec = {2'(d), 13'(x)}; we = r < 30; end
                    else begin m = 1'b1; x = o*32 + $urandom % 32; sec = {2'd0, 13'(x)}; we = r < 80; end
                    key = {m, sec};
                    if (we) gm[key] = merge(gget(key), dat, wm);
                    ex[a][c][et[a][c]] = rsp(16'(pi[a][c]), we, gget(key)); et[a][c] = (et[a][c] + 1) % 8;
                    cq[a][c*338 +: 338] <= pkreq(we, m, sec, dat, wm, 16'(pi[a][c]));
                    pi[a][c] = pi[a][c] + 1; po[a][c] = po[a][c] + 1;
                end
                // ---- wide write groups: one op a group a cycle (half mirror broadcasts, half own main)
                for (integer g = 0; g < WG; g = g + 1) if (wi[a][g] < NWG && $urandom % 2 == 0) begin : wg
                    integer x, l, key; reg m; reg [14:0] sec; reg [255:0] dat; reg [7:0] wm;
                    m = $urandom % 2; x = m ? 512 + (a*2 + g)*64 + $urandom % 64 : 4096 + g*256 + $urandom % 256;
                    sec = m ? {2'd0, 13'(x)} : {2'(a), 13'(x)}; l = g*8 + x % 8; dat = rnd256(0); wm = 8'($urandom);
                    if (wcr[a][l] > 0) begin
                        key = {m, sec}; gm[key] = merge(gget(key), dat, wm);
                        wq[a][l*281 +: 281] <= {1'b1, m, sec, dat, wm}; wcr[a][l] = wcr[a][l] - 1; wi[a][g] = wi[a][g] + 1;
                    end
                end
            end
            if (phase == 3 && bi[a] < NB && po[a][0] < 4) begin : rb
                integer x, key; reg m; reg [14:0] sec;
                if (bi[a] < 1280) begin m = 1'b1; x = bi[a]; sec = {2'd0, 13'(x)}; end
                else begin m = 1'b0; x = 1024 + bi[a] - 1280; sec = {2'(a), 13'(x)}; end
                key = {m, sec};
                ex[a][0][et[a][0]] = rsp(16'(bi[a]), 1'b0, gget(key)); et[a][0] = (et[a][0] + 1) % 8;
                cq[a][0 +: 338] <= pkreq(1'b0, m, sec, 256'd0, 8'd0, 16'(bi[a]));
                bi[a] = bi[a] + 1; po[a][0] = po[a][0] + 1;
            end
        end
        // ---- COLL star: one 8-sector record into all four slices (needs a star credit for each)
        if (phase == 2 && ki < NKQ && $urandom % 4 == 0) begin : kb
            integer x0, key; reg ok; reg [255:0] dat; reg [7:0] wm; reg [2129:0] rec;
            x0 = 1024 + 8 * ($urandom % 32); ok = 1'b1;
            for (integer a = 0; a < 4; a = a + 1) if (kcr[a] == 0) ok = 1'b0;
            if (ok) begin
                rec = '0; rec[2129] = 1'b1; rec[2128:2116] = {1'b1, 12'(x0 >> 3)}; rec[3:0] = 4'(ki);
                for (integer l = 0; l < 8; l = l + 1) begin
                    dat = rnd256(0); wm = 8'($urandom); key = {1'b1, 15'(x0 + l)}; gm[key] = merge(gget(key), dat, wm);
                    rec[68 + l*256 +: 256] = dat; rec[4 + l*8 +: 8] = wm;
                end
                for (integer a = 0; a < 4; a = a + 1) begin vcb[a] <= rec; kcr[a] = kcr[a] - 1; end
                ki = ki + 1;
            end
        end
    end
    // ---------------------------------------------------------------- sequence
    task automatic waitc(input integer n); repeat (n) @(posedge clk); endtask
    function automatic integer pdone(input integer dummy);
        integer t; begin t = 0; for (integer a = 0; a < 4; a = a + 1) for (integer c = 0; c < NC; c = c + 1) t = t + pd[a][c]; pdone = t; end
    endfunction
    integer t0, wsum, ksum;
    initial begin
        for (integer a = 0; a < 4; a = a + 1) begin cq[a] = '0; wq[a] = '0; vcb[a] = '0; end
        waitc(4); rst_n = 1'b1; waitc(2);
        phase = 2; t0 = cyc;
        forever begin
            waitc(1);
            wsum = wdn[0] + wdn[1] + wdn[2] + wdn[3]; ksum = kdn[0] + kdn[1] + kdn[2] + kdn[3];
            if (pdone(0) == 4*NC*NPK && wsum == 4*WG*NWG && ksum == 4*8*NKQ && mb == 4'd0) break;
            if (cyc - t0 > 400000) begin
                $display("VMS_RING4 TIMEOUT phase 2: pk %0d/%0d wg %0d/%0d coll %0d/%0d mirror_busy %b", pdone(0), 4*NC*NPK, wsum, 4*WG*NWG, ksum, 4*8*NKQ, mb);
                $display("VMS_RING4_BENCH FAIL"); $finish;
            end
        end
        waitc(20);
        for (integer a = 0; a < 4; a = a + 1) pd[a][0] = 0;
        phase = 3; t0 = cyc;
        while (pd[0][0] + pd[1][0] + pd[2][0] + pd[3][0] < 4*NB) begin
            waitc(1);
            if (cyc - t0 > 200000) begin $display("VMS_RING4 TIMEOUT phase 3"); $display("VMS_RING4_BENCH FAIL"); $finish; end
        end
        waitc(10);
        for (integer a = 0; a < 4; a = a + 1) begin
            for (integer b = 0; b < 8; b = b + 1) if (bst[a][b*18 + 17] || bst[a][b*18 + 16]) begin $display("SLICE %0d BANK %0d FAULT %h", a, b, bst[a][b*18 +: 18]); fails = fails + 1; end
            if (hst[a] != 3'd0) begin $display("SLICE %0d HUB FAULT %b", a, hst[a]); fails = fails + 1; end
        end
        $display("VMS_RING4 S=%0d cycles %0d: pk %0d wide-wr %0d coll %0d readback %0d, mismatches %0d", S, cyc, 4*NC*NPK, 4*WG*NWG, NKQ, 4*NB, fails);
        if (fails == 0) $display("VMS_RING4_BENCH PASS"); else $display("VMS_RING4_BENCH FAIL");
        $finish;
    end
endmodule
`default_nettype wire
