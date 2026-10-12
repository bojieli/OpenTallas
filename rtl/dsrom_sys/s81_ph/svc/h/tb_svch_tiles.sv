`timescale 1ns/1ps
// CLAUDE s81die-1011/ctrl svch: tile benches of the hardened svch leaves (fast; the slab-level value gate is
// tb_dsfd_svc_c).
//   tb_dsfd_svch_pcs  one per-PC service slice (QID 1, local PC 3 = PC 11) between credit-lane A / B / G requesters
//                     (random reads of 1..4 sectors in a granule, G one-sector masked writes) and a ctrl + HBM model
//                     (DQ 8 credits, random latency, valid-only responses, wd pulses): every read returns exactly
//                     its beats, in order per request, on ITS lane with its tag and the model's data; every write
//                     completes once on its port; the ctrl credit is never exceeded; landing credits are honoured
//                     (the bench pops responses at random gaps); no fault.  Prints SVCHPCS ... PASS / FAIL.
//   tb_dsfd_svch_rly  one relay station (W 4228, NR 1): the output equals the input one cycle later.
module tb_dsfd_svch_pcs #(parameter integer HDLY = 0);
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst = 0;
    integer cyc = 0, seed = 1, NREQ = 3000, gap = 30;
    localparam integer DA = 14, DB = 14, DG = 8, NG = 13;
    wire [340:0] qrq; reg qrk = 0, qwd = 0, qrv = 0; reg [255:0] qr_data = 0; reg [16:0] qr_tag = 0; reg [3:0] qr_beat = 0;
    reg aq_v = 0, bq_v = 0, gq_v = 0; reg [49:0] aq_d = 0; reg [45:0] bq_d = 0; reg [343:0] gq_d = 0;
    wire aq_c, bq_c, gq_c, ar_v, br_v, gr_v, fo; wire [275:0] ar_d, gr_d; wire [271:0] br_d; wire [NG-1:0] gwd;
    reg ar_c = 0, br_c = 0, gr_c = 0;
    dsfd_svch_pcs #(.QID(1), .PCL(3), .DA(DA), .DB(DB), .DG(DG), .HDLY(HDLY)) dut (.ck(clk), .rst(rst),
        .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat),
        .aq_v(aq_v), .aq_d(aq_d), .aq_c(aq_c), .ar_v(ar_v), .ar_d(ar_d), .ar_c(ar_c),
        .bq_v(bq_v), .bq_d(bq_d), .bq_c(bq_c), .br_v(br_v), .br_d(br_d), .br_c(br_c),
        .gq_v(gq_v), .gq_d(gq_d), .gq_c(gq_c), .gr_v(gr_v), .gr_d(gr_d), .gr_c(gr_c), .gwd(gwd), .fo(fo));
    function automatic [255:0] mem(input [29:0] s); mem = {8{s, 2'b10}} ^ {8{32'h9e3779b9}}; endfunction
    // expected beats per tag (A: 16-b tag, B: 12-b tag, G: port*4096 + tag)
    integer expA [0:65535], expB [0:4095], expG [0:65535];
    reg [29:0] adA [0:65535], adB [0:4095], adG [0:65535];
    integer gotA [0:65535], gotB [0:4095], gotG [0:65535];
    integer wexp [0:NG-1], wgot [0:NG-1];
    integer ca = DA, cb = DB, cg = DG, sent = 0, err = 0, outst = 0, maxo = 0, beats = 0, i, k;
    integer ta = 0, tb = 0, tg = 0;
    // PC model
    localparam integer PQ = 64;
    reg [340:0] pq [0:PQ-1]; integer pt [0:PQ-1]; integer ph = 0, pn = 0, pb = 0;
    reg [29:0] a0; reg [3:0] ln; integer port;
    initial begin
        if ($value$plusargs("seed=%d", seed)) ; void'($urandom(seed));
        for (i = 0; i < 65536; i = i + 1) begin expA[i] = 0; expG[i] = 0; gotA[i] = 0; gotG[i] = 0; end
        for (i = 0; i < 4096; i = i + 1) begin expB[i] = 0; gotB[i] = 0; end
        for (i = 0; i < NG; i = i + 1) begin wexp[i] = 0; wgot[i] = 0; end
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst <= 1;
        aq_v <= 0; bq_v <= 0; gq_v <= 0; ar_c <= 0; br_c <= 0; gr_c <= 0; qrk <= 0; qwd <= 0; qrv <= 0;
        ca = ca + aq_c; cb = cb + bq_c; cg = cg + gq_c;
        if (rst && cyc > 10 && sent < NREQ) begin
            a0 = 30'($urandom) & ~30'd3; ln = 4'(1 + $urandom % 4);
            k = $urandom % 3;
            if (k == 0 && ca > 0 && ($urandom % 100) >= gap) begin
                aq_v <= 1; aq_d <= {ln, a0, 16'(ta)}; expA[ta] = ln; adA[ta] = a0; ta = (ta + 1) % 65536; ca = ca - 1; sent = sent + 1;
            end else if (k == 1 && cb > 0 && ($urandom % 100) >= gap) begin
                bq_v <= 1; bq_d <= {ln, a0, 12'(tb)}; expB[tb] = ln; adB[tb] = a0; tb = (tb + 1) % 4096; cb = cb - 1; sent = sent + 1;
            end else if (k == 2 && cg > 0 && ($urandom % 100) >= gap) begin
                port = $urandom % NG;
                if ($urandom % 3 == 0) begin
                    gq_v <= 1; gq_d <= {2'd1, 3'd3, 4'(port), 1'b1, 4'd1, a0, 12'(tg), 32'hffffffff, mem(a0)};
                    wexp[port] = wexp[port] + 1;
                end else begin
                    gq_v <= 1; gq_d <= {2'd1, 3'd3, 4'(port), 1'b0, ln, a0, 12'(tg), 32'd0, 256'd0};
                    expG[port*4096 + tg] = ln; adG[port*4096 + tg] = a0;
                end
                tg = (tg + 1) % 4096; cg = cg - 1; sent = sent + 1;
            end
        end
        // ctrl + HBM model
        if (qrq[0]) begin
            pq[(ph + pn) % PQ] = qrq; pt[(ph + pn) % PQ] = cyc + 20 + $urandom % 40; pn = pn + 1;
            outst = outst + 1; if (outst > maxo) maxo = outst; if (outst > 8) err = err + 1;
        end
        if (pn > 0 && pt[ph] <= cyc) begin
            if (pq[ph][1]) begin qwd <= 1; qrk <= 1; ph = (ph + 1) % PQ; pn = pn - 1; outst = outst - 1; end
            else begin
                qrv <= 1; qr_tag <= pq[ph][52:36]; qr_beat <= 4'(pb); qr_data <= mem(pq[ph][31:2] + 30'(pb));
                if (pb + 1 == pq[ph][35:32]) begin pb = 0; ph = (ph + 1) % PQ; pn = pn - 1; qrk <= 1; outst = outst - 1; end
                else pb = pb + 1;
            end
        end
        // responses: check, return landing credits
        if (ar_v) begin
            k = ar_d[275:260];
            if (gotA[k] >= expA[k] || ar_d[259:256] != 4'(gotA[k]) || ar_d[255:0] != mem(adA[k] + 30'(gotA[k]))) err = err + 1;
            gotA[k] = gotA[k] + 1; beats = beats + 1; ar_c <= 1;
        end
        if (br_v) begin
            k = br_d[271:260];
            if (gotB[k] >= expB[k] || br_d[259:256] != 4'(gotB[k]) || br_d[255:0] != mem(adB[k] + 30'(gotB[k]))) err = err + 1;
            gotB[k] = gotB[k] + 1; beats = beats + 1; br_c <= 1;
        end
        if (gr_v) begin
            k = gr_d[275:272] * 4096 + gr_d[271:260];
            if (gotG[k] >= expG[k] || gr_d[259:256] != 4'(gotG[k]) || gr_d[255:0] != mem(adG[k] + 30'(gotG[k]))) err = err + 1;
            gotG[k] = gotG[k] + 1; beats = beats + 1; gr_c <= 1;
        end
        for (i = 0; i < NG; i = i + 1) if (gwd[i]) wgot[i] = wgot[i] + 1;
        if (cyc == 200000 || (sent == NREQ && cyc > 20000 && pn == 0 && cyc % 1000 == 0 && beats > 0)) begin
            for (i = 0; i < 65536; i = i + 1) begin if (gotA[i] != expA[i]) err = err + 1; if (gotG[i] != expG[i]) err = err + 1; end
            for (i = 0; i < 4096; i = i + 1) if (gotB[i] != expB[i]) err = err + 1;
            for (i = 0; i < NG; i = i + 1) if (wgot[i] != wexp[i]) err = err + 1;
            $display("SVCHPCS sent=%0d beats=%0d max_outstanding=%0d errors=%0d fault=%0d cycles=%0d verdict=%s", sent, beats, maxo,
                     err, fo, cyc, (err == 0 && !fo && sent == NREQ) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule

module tb_dsfd_svch_rly;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst = 0; integer cyc = 0, err = 0, n = 0;
    reg iv = 0; reg [4227:0] id = 0, pd = 0; reg pv = 0;
    wire ov; wire [4227:0] od;
    dsfd_svch_rly #(.W(4228), .NR(1), .V(1)) dut (.ck(clk), .rst(rst), .i_v(iv), .i_d(id), .o_v(ov), .o_d(od));
    integer k;
    always @(posedge clk) begin
        cyc <= cyc + 1; if (cyc == 3) rst <= 1;
        if (cyc > 8) begin
            if (ov !== pv || (pv && od !== pd)) err = err + 1;
            if (ov) n = n + 1;
        end
        pv <= iv; pd <= id;
        iv <= ($urandom % 2) && cyc > 6;
        for (k = 0; k < 4228 / 32 + 1; k = k + 1) id[32*k +: 32] <= $urandom;
        if (cyc == 5000) begin $display("SVCHRLY beats=%0d errors=%0d verdict=%s", n, err, (err == 0 && n > 1000) ? "PASS" : "FAIL"); $finish; end
    end
endmodule
