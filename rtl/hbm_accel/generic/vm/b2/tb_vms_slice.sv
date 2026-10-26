`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice UNIT BENCH (el1011-hbm-b2-vm): one slice (ot_vms_slice, sid = Q) against the old central VM
// (ot_hgi_vm_unit, the qualified golden) on per-slice traffic -- the same op streams into both, compared exactly:
//   phase 1  DMA fills R0 (both: 8 aligned sectors a cycle)
//   phase 2  concurrent: 4 packet clients (random reads / word-masked writes in private regions, <= 4 outstanding,
//            in order), 2 wide read groups (random reads of R0), 2 wide write groups (private regions), DMA (own region)
//   phase 3  packet client 0 reads back every sector of every region on both
// PASS = every packet response (tag, echo, data), every wide read and every read-back word equal; no fault status.
// Mutants (-G): HMUT=1 wrong slice routing (S[13:12]) must FAIL (timeout or mismatch); BMUT/CMUT are ring mutants
// (tb_vms_ring4); BMUT=2 lane queues one entry short of the 4 + 2 RS credits (overrun -> bank fault) must FAIL.
// Timeout = FAIL.
module tb_vms_slice;
    parameter integer Q = 2, HMUT = 0, BMUT = 0, CMUT = 0, SEED = 1;
    parameter integer NPK = 300, NRG = 300, NWG = 300, NDM = 60;
    parameter integer RS = 3;                       // contract relay stages a lane group: credits 4 + 2 RS a lane (SPEC v0.8)
    localparam integer NC = 4, RG = 2, WG = 2, LQC = 4 + 2 * RS;
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;
    // ---------------------------------------------------------------- DUTs
    reg  [NC*338-1:0] ncq, ocq; wire [NC*274-1:0] ncr, ocr;
    reg  [RG*8*17-1:0] nrq; wire [RG*8-1:0] nrq_cr; wire [RG*8*257-1:0] nrr;
    reg  [WG*8*281-1:0] nwq; wire [WG*8-1:0] nwq_cr, nwq_done;
    reg  [8*281-1:0] ndq; wire [7:0] ndq_done; wire nvcb_cr; wire [7:0] nkq_done;
    wire [2223:0] cwo, ccwo; wire [1:0] cwic, ccwic; wire [8*18-1:0] bst; wire [2:0] hst; wire [1:0] mb;
    ot_vms_slice #(.NC(NC), .RG(RG), .WG(WG), .RRS({RG{4'(RS)}}), .WRS({WG{4'(RS)}}), .BMUT(BMUT), .HMUT(HMUT), .CMUT(CMUT)) dut (.clk(clk), .rst_n(rst_n), .sid(2'(Q)),
        .cq(ncq), .cr(ncr), .rq(nrq), .rq_cr(nrq_cr), .rr(nrr), .wq(nwq), .wq_cr(nwq_cr), .wq_done(nwq_done), .dq(ndq), .dq_done(ndq_done),
        .vcb('0), .vcb_cr(nvcb_cr), .kq_done(nkq_done), .cw_in('0), .cw_in_cr(cwic), .cw_out(cwo), .cw_out_cr(2'b00),
        .ccw_in('0), .ccw_in_cr(ccwic), .ccw_out(ccwo), .ccw_out_cr(2'b00), .bank_status(bst), .hub_status(hst), .mirror_busy(mb));
    reg  [32*280-1:0] owq; wire [31:0] owq_done; reg [64*16-1:0] orq; wire [63:0] orq_cr; wire [64*257-1:0] orr;
    reg  [64*280-1:0] ow2q; wire [63:0] ow2q_cr, ow2q_done; wire [18:0] ost;
    ot_hgi_vm_unit #(.NC(NC), .WP(32), .WDIRECT(1), .RP(64), .W2(64)) gold (.clk(clk), .rst_n(rst_n), .cq(ocq), .cr(ocr), .status(ost),
        .wq(owq), .wq_done(owq_done), .rq(orq), .rq_cr(orq_cr), .rr(orr), .w2q(ow2q), .w2q_cr(ow2q_cr), .w2q_done(ow2q_done), .wq_rdy(), .ap_q(), .ap_cr(8'd0), .ap_done(8'd0));

    // ---------------------------------------------------------------- op streams
    function automatic [14:0] gs(input integer x); gs = {2'(Q), 13'(x)}; endfunction
    localparam integer R0 = 0, PC0 = 1024, WG0 = 3072, WD0 = 4096, NSEC = 5120;
    reg          pk_we [0:NC-1][0:NPK-1]; reg [14:0] pk_s [0:NC-1][0:NPK-1]; reg [255:0] pk_d [0:NC-1][0:NPK-1]; reg [31:0] pk_m [0:NC-1][0:NPK-1];
    reg [14:0]   rg_s [0:RG-1][0:NRG-1];
    reg [14:0]   wg_s [0:WG-1][0:NWG-1]; reg [255:0] wg_d [0:WG-1][0:NWG-1]; reg [7:0] wg_m [0:WG-1][0:NWG-1];
    reg [255:0]  dm_d [0:8*(128+NDM)-1];
    function automatic [255:0] rnd256(input integer dummy);
        reg [255:0] r; begin for (integer k = 0; k < 8; k = k + 1) r[k*32 +: 32] = $urandom; rnd256 = r; end
    endfunction
    initial begin
        void'($urandom(SEED));
        for (integer c = 0; c < NC; c = c + 1) for (integer i = 0; i < NPK; i = i + 1) begin
            pk_we[c][i] = $urandom % 2; pk_s[c][i] = gs(PC0 + c*512 + ($urandom % 64) * 8 + ($urandom % 8));
            pk_d[c][i] = rnd256(0);
            for (integer k = 0; k < 8; k = k + 1) pk_m[c][i][4*k +: 4] = ($urandom % 4 == 0) ? 4'h0 : 4'hf;
        end
        for (integer g = 0; g < RG; g = g + 1) for (integer i = 0; i < NRG; i = i + 1) rg_s[g][i] = gs(R0 + $urandom % 1024);
        for (integer g = 0; g < WG; g = g + 1) for (integer i = 0; i < NWG; i = i + 1) begin
            wg_s[g][i] = gs(WG0 + g*512 + $urandom % 512); wg_d[g][i] = rnd256(0); wg_m[g][i] = 8'($urandom);
        end
        for (integer i = 0; i < 8*(128+NDM); i = i + 1) dm_d[i] = rnd256(0);
    end
    // DMA bundle i: 8 aligned sectors; bundles 0..127 fill R0, 128.. fill the DMA region
    function automatic integer dmx(input integer i); dmx = (i < 128) ? R0 + i*8 : WD0 + ((i - 128) % 128) * 8; endfunction

    // ---------------------------------------------------------------- drivers
    integer phase = 0, cyc = 0, fails = 0;
    // packet clients (both DUTs, independent timing)
    integer pi_n [0:NC-1], pi_o [0:NC-1], po_n [0:NC-1], po_o [0:NC-1], pr_n [0:NC-1], pr_o [0:NC-1];
    reg [272:0] rsN [0:NC-1][0:NPK-1]; reg [272:0] rsO [0:NC-1][0:NPK-1];
    // phase 3 read-back (client 0)
    integer bi_n = 0, bi_o = 0, bo_n = 0, bo_o = 0, br_n = 0, br_o = 0; reg [255:0] bkN [0:NSEC-1]; reg [255:0] bkO [0:NSEC-1];
    // wide reads
    integer ri_n [0:RG-1], ri_o [0:RG-1], rcr_n [0:RG*8-1], rcr_o [0:64-1]; integer rq_n [0:RG*8-1][0:31]; integer rq_o [0:63][0:15];
    integer rh_n [0:RG*8-1], rt_n [0:RG*8-1], rh_o [0:63], rt_o [0:63]; reg [255:0] rdN [0:RG-1][0:NRG-1]; reg [255:0] rdO [0:RG-1][0:NRG-1];
    integer rgot_n = 0, rgot_o = 0;
    // wide writes
    integer wi_n [0:WG-1], wi_o [0:WG-1], wcr_n [0:WG*8-1], wcr_o [0:63]; integer wd_n = 0, wd_o = 0;
    integer di = 0, dd_n = 0, dd_o = 0;
    initial begin
        for (integer c = 0; c < NC; c = c + 1) begin pi_n[c] = 0; pi_o[c] = 0; po_n[c] = 0; po_o[c] = 0; pr_n[c] = 0; pr_o[c] = 0; end
        for (integer g = 0; g < RG; g = g + 1) begin ri_n[g] = 0; ri_o[g] = 0; end
        for (integer g = 0; g < WG; g = g + 1) begin wi_n[g] = 0; wi_o[g] = 0; end
        for (integer l = 0; l < RG*8; l = l + 1) begin rcr_n[l] = LQC; rh_n[l] = 0; rt_n[l] = 0; end
        for (integer l = 0; l < 64; l = l + 1) begin rcr_o[l] = 8; rh_o[l] = 0; rt_o[l] = 0; wcr_o[l] = 8; end
        for (integer l = 0; l < WG*8; l = l + 1) wcr_n[l] = LQC;
    end
    function automatic [337:0] pkreq(input reg we, input [14:0] s, input [255:0] d, input [31:0] m, input [15:0] tag);
        pkreq = {1'b1, we, 11'd0, 1'b0, s, 5'd0, d, we ? m : 32'd0, tag};
    endfunction
    always @(posedge clk) if (rst_n) begin : drive
        reg [63:0] usedN, usedO, wusN, wusO; integer l, lo, x;
        cyc <= cyc + 1;
        ncq <= '0; ocq <= '0; nrq <= '0; orq <= '0; nwq <= '0; ow2q <= '0; ndq <= '0; owq <= '0;
        // ---- responses
        for (integer c = 0; c < NC; c = c + 1) begin
            if (ncr[c*274 + 273]) begin
                if (phase == 3 && c == 0) begin bkN[br_n] = ncr[c*274 +: 256]; br_n = br_n + 1; end
                else begin rsN[c][ncr[c*274 + 257 +: 16]] = ncr[c*274 +: 273]; pr_n[c] = pr_n[c] + 1; end
                po_n[c] = po_n[c] - 1;
            end
            if (ocr[c*274 + 273]) begin
                if (phase == 3 && c == 0) begin bkO[br_o] = ocr[c*274 +: 256]; br_o = br_o + 1; end
                else begin rsO[c][ocr[c*274 + 257 +: 16]] = ocr[c*274 +: 273]; pr_o[c] = pr_o[c] + 1; end
                po_o[c] = po_o[c] - 1;
            end
        end
        for (l = 0; l < RG*8; l = l + 1) begin
            if (nrq_cr[l]) rcr_n[l] = rcr_n[l] + 1;
            if (nrr[l*257 + 256]) begin x = rq_n[l][rh_n[l]]; rh_n[l] = (rh_n[l] + 1) % 32; rdN[l/8][x] = nrr[l*257 +: 256]; rgot_n = rgot_n + 1; end
        end
        for (l = 0; l < 64; l = l + 1) begin
            if (orq_cr[l]) rcr_o[l] = rcr_o[l] + 1;
            if (orr[l*257 + 256]) begin x = rq_o[l][rh_o[l]]; rh_o[l] = (rh_o[l] + 1) % 16; rdO[l/32][x] = orr[l*257 +: 256]; rgot_o = rgot_o + 1; end
            if (ow2q_cr[l]) wcr_o[l] = wcr_o[l] + 1;
            if (ow2q_done[l]) wd_o = wd_o + 1;
        end
        for (l = 0; l < WG*8; l = l + 1) begin if (nwq_cr[l]) wcr_n[l] = wcr_n[l] + 1; if (nwq_done[l]) wd_n = wd_n + 1; end
        for (l = 0; l < 8; l = l + 1) if (ndq_done[l]) dd_n = dd_n + 1;
        for (l = 0; l < 32; l = l + 1) if (owq_done[l]) dd_o = dd_o + 1;
        // ---- DMA (same bundle to both in the same cycle: neither back-pressures)
        if ((phase == 1 && di < 128) || (phase == 2 && di < 128 + NDM && cyc % 3 == 0)) begin
            for (integer k = 0; k < 8; k = k + 1) begin
                reg [14:0] s; s = gs(dmx(di) + k);
                ndq[k*281 +: 281] <= {1'b1, 1'b0, s, dm_d[di*8 + k], 8'hff};
                owq[s[4:0]*280 +: 280] <= {1'b1, s, dm_d[di*8 + k], 8'hff};
            end
            di = di + 1;
        end
        if (phase == 2) begin
            // ---- packet clients
            for (integer c = 0; c < NC; c = c + 1) begin
                if (pi_n[c] < NPK && po_n[c] < 4 && $urandom % 3 != 0) begin
                    ncq[c*338 +: 338] <= pkreq(pk_we[c][pi_n[c]], pk_s[c][pi_n[c]], pk_d[c][pi_n[c]], pk_m[c][pi_n[c]], 16'(pi_n[c]));
                    pi_n[c] = pi_n[c] + 1; po_n[c] = po_n[c] + 1;
                end
                if (pi_o[c] < NPK && po_o[c] < 4 && $urandom % 3 != 0) begin
                    ocq[c*338 +: 338] <= pkreq(pk_we[c][pi_o[c]], pk_s[c][pi_o[c]], pk_d[c][pi_o[c]], pk_m[c][pi_o[c]], 16'(pi_o[c]));
                    pi_o[c] = pi_o[c] + 1; po_o[c] = po_o[c] + 1;
                end
            end
            // ---- wide groups: up to 4 ops a cycle a group, in order, distinct lanes
            usedN = '0; usedO = '0; wusN = '0; wusO = '0;
            for (integer g = 0; g < RG; g = g + 1) begin
                for (integer k = 0; k < 4; k = k + 1) if (ri_n[g] < NRG) begin
                    l = g*8 + rg_s[g][ri_n[g]][2:0];
                    if (rcr_n[l] > 0 && !usedN[l]) begin usedN[l] = 1'b1;
                        nrq[l*17 +: 17] <= {1'b1, 1'b0, rg_s[g][ri_n[g]]}; rcr_n[l] = rcr_n[l] - 1;
                        rq_n[l][rt_n[l]] = ri_n[g]; rt_n[l] = (rt_n[l] + 1) % 32; ri_n[g] = ri_n[g] + 1;
                    end else k = 4;
                end
                for (integer k = 0; k < 4; k = k + 1) if (ri_o[g] < NRG) begin
                    lo = g*32 + rg_s[g][ri_o[g]][4:0];
                    if (rcr_o[lo] > 0 && !usedO[lo]) begin usedO[lo] = 1'b1;
                        orq[lo*16 +: 16] <= {1'b1, rg_s[g][ri_o[g]]}; rcr_o[lo] = rcr_o[lo] - 1;
                        rq_o[lo][rt_o[lo]] = ri_o[g]; rt_o[lo] = (rt_o[lo] + 1) % 16; ri_o[g] = ri_o[g] + 1;
                    end else k = 4;
                end
            end
            for (integer g = 0; g < WG; g = g + 1) begin
                for (integer k = 0; k < 4; k = k + 1) if (wi_n[g] < NWG) begin
                    l = g*8 + wg_s[g][wi_n[g]][2:0];
                    if (wcr_n[l] > 0 && !wusN[l]) begin wusN[l] = 1'b1;
                        nwq[l*281 +: 281] <= {1'b1, 1'b0, wg_s[g][wi_n[g]], wg_d[g][wi_n[g]], wg_m[g][wi_n[g]]}; wcr_n[l] = wcr_n[l] - 1; wi_n[g] = wi_n[g] + 1;
                    end else k = 4;
                end
                for (integer k = 0; k < 4; k = k + 1) if (wi_o[g] < NWG) begin
                    lo = g*32 + wg_s[g][wi_o[g]][4:0];
                    if (wcr_o[lo] > 0 && !wusO[lo]) begin wusO[lo] = 1'b1;
                        ow2q[lo*280 +: 280] <= {1'b1, wg_s[g][wi_o[g]], wg_d[g][wi_o[g]], wg_m[g][wi_o[g]]}; wcr_o[lo] = wcr_o[lo] - 1; wi_o[g] = wi_o[g] + 1;
                    end else k = 4;
                end
            end
        end
        if (phase == 3) begin
            if (bi_n < NSEC && po_n[0] < 4) begin ncq[0 +: 338] <= pkreq(1'b0, gs(bi_n), 256'd0, 32'd0, 16'(bi_n)); bi_n = bi_n + 1; po_n[0] = po_n[0] + 1; end
            if (bi_o < NSEC && po_o[0] < 4) begin ocq[0 +: 338] <= pkreq(1'b0, gs(bi_o), 256'd0, 32'd0, 16'(bi_o)); bi_o = bi_o + 1; po_o[0] = po_o[0] + 1; end
        end
    end
    // ---------------------------------------------------------------- sequence + checks
    task automatic waitc(input integer n); repeat (n) @(posedge clk); endtask
    integer t0;
    initial begin
        ncq = '0; ocq = '0; nrq = '0; orq = '0; nwq = '0; ow2q = '0; ndq = '0; owq = '0;
        waitc(4); rst_n = 1'b1; waitc(2);
        phase = 1; t0 = cyc;
        while (dd_n < 1024 || dd_o < 1024) begin waitc(1); if (cyc - t0 > 20000) begin $display("VMS_SLICE TIMEOUT phase 1 dd %0d/%0d", dd_n, dd_o); $display("VMS_SLICE_BENCH FAIL"); $finish; end end
        phase = 2; t0 = cyc;
        while (!(rgot_n == RG*NRG && rgot_o == RG*NRG && wd_n == WG*NWG && wd_o == WG*NWG && dd_n == 8*(128+NDM) && dd_o == 8*(128+NDM)
                 && pr_n[0] + pr_n[1] + pr_n[2] + pr_n[3] == NC*NPK && pr_o[0] + pr_o[1] + pr_o[2] + pr_o[3] == NC*NPK)) begin
            waitc(1);
            if (cyc - t0 > 200000) begin
                $display("VMS_SLICE TIMEOUT phase 2: rg %0d/%0d wg %0d/%0d dma %0d/%0d pk %0d %0d %0d %0d / %0d", rgot_n, rgot_o, wd_n, wd_o, dd_n, dd_o,
                         pr_n[0], pr_n[1], pr_n[2], pr_n[3], pr_o[0] + pr_o[1] + pr_o[2] + pr_o[3]);
                $display("VMS_SLICE_BENCH FAIL"); $finish;
            end
        end
        waitc(20); phase = 3; t0 = cyc;
        while (br_n < NSEC || br_o < NSEC) begin waitc(1); if (cyc - t0 > 200000) begin $display("VMS_SLICE TIMEOUT phase 3 %0d/%0d", br_n, br_o); $display("VMS_SLICE_BENCH FAIL"); $finish; end end
        waitc(10);
        for (integer c = 0; c < NC; c = c + 1) for (integer i = 0; i < NPK; i = i + 1)
            if (rsN[c][i] !== rsO[c][i]) begin if (fails < 8) $display("PK MISMATCH c%0d op%0d we%0d s%h new %h old %h", c, i, pk_we[c][i], pk_s[c][i], rsN[c][i][63:0], rsO[c][i][63:0]); fails = fails + 1; end
        for (integer g = 0; g < RG; g = g + 1) for (integer i = 0; i < NRG; i = i + 1)
            if (rdN[g][i] !== rdO[g][i]) begin if (fails < 16) $display("RG MISMATCH g%0d op%0d s%h", g, i, rg_s[g][i]); fails = fails + 1; end
        for (integer i = 0; i < NSEC; i = i + 1)
            if (bkN[i] !== bkO[i]) begin if (fails < 24) $display("READBACK MISMATCH x%0d new %h old %h", i, bkN[i][63:0], bkO[i][63:0]); fails = fails + 1; end
        for (integer b = 0; b < 8; b = b + 1) if (bst[b*18 + 17] || bst[b*18 + 16]) begin $display("BANK %0d FAULT status %h", b, bst[b*18 +: 18]); fails = fails + 1; end
        if (hst != 3'd0) begin $display("HUB FAULT %b", hst); fails = fails + 1; end
        $display("VMS_SLICE Q%0d cycles %0d: pk %0d rg %0d wg %0d dma %0d readback %0d, mismatches %0d", Q, cyc, NC*NPK, RG*NRG, WG*NWG,
                 8*(128+NDM), NSEC, fails);
        if (fails == 0) $display("VMS_SLICE_BENCH PASS"); else $display("VMS_SLICE_BENCH FAIL");
        $finish;
    end
endmodule
`default_nettype wire
