`timescale 1ns/1ps
// die-s81-85 11-09: IRG rg3 PRIME bench (copy of results/rtl/svc_irg_fastpad_1109/reader/tb.sv + a second reader).
// u  = dsdv_idx_rg3 as of 9b6810c755 (reference reader, no prime counter).
// up = dsdv_idx_rg3_p = this branch's dsdv_idx_rg3.sv, built with the variant's defines (none / OT_IDX_RG3_PRIME /
//      OT_IDX_RG3_PRIME + OT_IDX_RG3_PRIME_MUT).  Both get the same qi / si / rri.
// Shadow chunk engines (driven from u's chunk-column inputs, rst_n = rl[26 + gc], MUTK as the reader bench):
//      chk_ref = original dsdv_idx_rg2_chunk, chk_fp = OT_IDX_HSLICE_FASTPAD chunk WITHOUT the 9b6810c755 guard
//      (b9200f3611 text), so the prime counter alone must cover both forms.
// Epochs: warm reset (random 1..12 edges), job frame whose header reaches qr at E + D (D = 1..DM swept).
// Checks (pf = up.st[0], the rg3 sticky fault; pf5 = up.st[7] = fc[5], the cause the prime counter sets):
//  * fail_open_ref_p / fail_open_fp_p: valid records with c_fault 0 from a chunk with bad q state AND pf 0   -> 0
//  * fail_open_ref_p5 / fail_open_fp_p5: the same against pf5 alone (no credit from other fault causes)     -> 0
//  * prime fault per D: every epoch with D < PRIME_EXP (6) has pf5, no epoch with D >= 6 has it           -> exact
//  (this bench answers no reads (rri = 0), so other fc causes (fc_seen) rise late in every epoch in u and up alike)
//  * out_diff_ge6: {qo, so, rqo, st} of up vs u differ in an epoch with D >= 6                             -> 0
//  * chunk_in_diff: up's chunk-column inputs differ from u's (the stream is never altered)                 -> 0
//  * mismatch: ref vs fp records differ                                                                    -> 0
//  * out_diff_all (reported): with no define, up == u on every cycle (default netlist / outputs unchanged)
module tb;
    parameter integer KR = 0;
    localparam integer LAT = 106, NK = 200, HC = 8, PRIME_EXP = 6;
    reg ck = 1'b0;
    always #5 ck = ~ck;
    reg rst = 1'b0;
    reg [512:0] qi = '0;
    wire [512:0] qo; wire [275:0] so; wire [183:0] rqo; wire [9:0] st;
    wire [512:0] qo_p; wire [275:0] so_p; wire [183:0] rqo_p; wire [9:0] st_p;
    dsdv_idx_rg3 #(.SRAM_MACRO(1'b0), .KR(KR), .OH(2), .RH(2), .IH(0)) u (.ck(ck), .rst(rst), .sid(4'd0), .qi(qi),
        .qo(qo), .si(276'd0), .so(so), .rqo(rqo), .rri(1088'd0), .st(st));
    dsdv_idx_rg3_p #(.SRAM_MACRO(1'b0), .KR(KR), .OH(2), .RH(2), .IH(0)) up (.ck(ck), .rst(rst), .sid(4'd0), .qi(qi),
        .qo(qo_p), .si(276'd0), .so(so_p), .rqo(rqo_p), .rri(1088'd0), .st(st_p));
    integer MUTK, DM, NEP, SEED, DFIX;
    initial begin
        if (!$value$plusargs("MUTK=%d", MUTK)) MUTK = 0;
        if (!$value$plusargs("DM=%d", DM)) DM = 12;
        if (!$value$plusargs("NEP=%d", NEP)) NEP = 240;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        if (!$value$plusargs("D=%d", DFIX)) DFIX = 0;
    end
    reg [543:0] kk = '0;
    reg [511:0] gqc [0:31]; reg [31:0] gqs [0:31]; reg [15:0] gqw [0:31];
    wire [31:0] rsum [0:3], fsum [0:3]; wire [3:0] rf, ff;
    wire [31:0] bad_r, bad_f; wire [3:0] cin_diff;
    genvar gc, gh;
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_sh
        wire rl_c = u.rl[26 + gc];
        reg [7:0] dl;
        always @(posedge ck or negedge rl_c) if (!rl_c) dl <= 8'd0; else dl <= {dl[6:0], 1'b1};
        wire srst = (MUTK == 0) ? rl_c : dl[MUTK - 1];
        wire qv = u.g_ch[gc].qv_c; wire [7:0] qh = u.g_ch[gc].qh_c; wire [511:0] qc = u.g_ch[gc].qc_c;
        wire [47:0] qs = u.g_ch[gc].qs_c;
        assign cin_diff[gc] = {up.g_ch[gc].qv_c, up.g_ch[gc].qh_c, up.g_ch[gc].qc_c, up.g_ch[gc].qs_c, up.g_ch[gc].kk_c,
                               up.rl[26 + gc]} !== {qv, qh, qc, qs, u.g_ch[gc].kk_c, rl_c};
        chk_ref u_r (.clk(ck), .rst_n(srst), .hb(8'(8 * gc)), .ql_v(qv), .ql_head(qh), .ql_codes(qc), .ql_sc(qs[31:0]),
                     .ql_w(qs[47:32]), .k_key(kk), .c_sum(rsum[gc]), .c_fault(rf[gc]));
        chk_fp  u_f (.clk(ck), .rst_n(srst), .hb(8'(8 * gc)), .ql_v(qv), .ql_head(qh), .ql_codes(qc), .ql_sc(qs[31:0]),
                     .ql_w(qs[47:32]), .k_key(kk), .c_sum(fsum[gc]), .c_fault(ff[gc]));
        for (gh = 0; gh < HC; gh = gh + 1) begin : g_q
            assign bad_r[8 * gc + gh] = {u_r.g_s[gh].u_s.qc, u_r.g_s[gh].u_s.qs, u_r.g_s[gh].u_s.qw}
                                        !== {gqc[8 * gc + gh], gqs[8 * gc + gh], gqw[8 * gc + gh]};
            assign bad_f[8 * gc + gh] = {u_f.g_s[gh].u_s.qc, u_f.g_s[gh].u_s.qs, u_f.g_s[gh].u_s.qw}
                                        !== {gqc[8 * gc + gh], gqs[8 * gc + gh], gqw[8 * gc + gh]};
        end
    end endgenerate
    wire pf = st_p[0], pf5 = st_p[7];
    reg [7:0] fc_seen = 8'd0;
    // ---- record ring + checks (sample at negedge, then drive)
    reg [LAT-1:0] ring = '0;
    reg kvalid = 1'b0;
    reg [3:0] qbr = 4'd0, qbf = 4'd0;
    longint n_valid = 0, n_vfault = 0, n_mis = 0, n_open_r = 0, n_open_f = 0, n_open_rp = 0, n_open_fp = 0, n_open_rp5 = 0, n_open_fp5 = 0, n_cyc = 0;
    longint n_odiff = 0, n_odiff_ge6 = 0, n_cdiff = 0, n_pfrec = 0;
    integer ep_qbad_r = 0, ep_qbad_f = 0, d = 1, pk_bad = 0;
    integer c;
    reg ep_odiff = 1'b0;
    always @(negedge ck) begin
        n_cyc = n_cyc + 1;
        if ({qo_p, so_p, rqo_p, st_p} !== {qo, so, rqo, st}) begin
            n_odiff = n_odiff + 1; ep_odiff = 1'b1;
            if (d >= PRIME_EXP) begin
                n_odiff_ge6 = n_odiff_ge6 + 1;
                if (n_odiff_ge6 <= 4) $display("ODIFF t %0t d %0d st %h st_p %h", $time, d, st, st_p);
            end
        end
        if (|cin_diff) n_cdiff = n_cdiff + 1;
        fc_seen = fc_seen | st[9:2];
`ifdef PRIME
        if (up.hdr_job && up.pk != 3'((d < `PRIME) ? d : `PRIME)) begin
            pk_bad = pk_bad + 1;
            if (pk_bad <= 4) $display("PK t %0t d %0d pk %0d", $time, d, up.pk);
        end
`endif
        if (ring[LAT-1]) for (c = 0; c < 4; c = c + 1) begin
            n_valid = n_valid + 1;
            if (rf[c]) n_vfault = n_vfault + 1;
            if (pf) n_pfrec = n_pfrec + 1;
            if (!rf[c] && qbr[c]) n_open_r = n_open_r + 1;
            if (!ff[c] && qbf[c]) n_open_f = n_open_f + 1;
            if (!rf[c] && qbr[c] && !pf) n_open_rp = n_open_rp + 1;
            if (!ff[c] && qbf[c] && !pf) n_open_fp = n_open_fp + 1;
            if (!rf[c] && qbr[c] && !pf5) n_open_rp5 = n_open_rp5 + 1;
            if (!ff[c] && qbf[c] && !pf5) n_open_fp5 = n_open_fp5 + 1;
            if (rsum[c] !== fsum[c] || rf[c] !== ff[c]) begin
                n_mis = n_mis + 1;
                if (n_mis <= 8) $display("MIS t %0t chunk %0d ref %h/%0d fp %h/%0d", $time, c, rsum[c], rf[c], fsum[c], ff[c]);
            end
        end
        ring = rst ? {ring[LAT-2:0], kvalid} : '0;
        kk = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
              $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        for (c = 0; c < 4; c = c + 1) kk[512 + 8 * c +: 8] = ($urandom_range(0, 99) == 0) ? 8'd255 : 8'(108 + $urandom_range(0, 38));
    end
    function automatic [511:0] job_hdr();
        reg [511:0] h;
        h = 512'd0;
        h[511:508] = 4'd4; h[502:495] = 8'h5A; h[491:480] = 12'd64; h[458:449] = 10'd3;
        h[19:0] = 20'd13; h[40:20] = 21'd4096; h[50:41] = 10'd512; h[80:51] = 30'd64;
        h[96:81] = 16'd400; h[100:97] = 4'd3; h[103:101] = 3'd5; h[106:104] = 3'd0;
        job_hdr = h;
    endfunction
    integer ep, i, rlen, nb, pf_wrong = 0;
    integer cnt_d [0:31], cnt_bad_d [0:31], cnt_pf_d [0:31], cnt_od_d [0:31], cnt_open_d [0:31];
    longint o_r0, o_f0;
    initial begin
        void'($urandom(SEED));
        for (i = 0; i < 32; i = i + 1) begin gqc[i] = '0; gqs[i] = '0; gqw[i] = '0; cnt_d[i] = 0; cnt_bad_d[i] = 0;
                                             cnt_pf_d[i] = 0; cnt_od_d[i] = 0; cnt_open_d[i] = 0; end
        repeat (20) @(negedge ck);
        for (ep = 0; ep < NEP; ep = ep + 1) begin
            @(negedge ck); rst = 1'b0; kvalid = 1'b0; qbr = 4'd0; qbf = 4'd0; ep_odiff = 1'b0;
            rlen = (ep == 0) ? 20 : $urandom_range(1, 12);
            repeat (rlen) @(negedge ck);
            rst = 1'b1;
            d = (DFIX != 0) ? DFIX : 1 + (ep % DM); ep_odiff = 1'b0;   // diffs before here belong to the last epoch
            for (i = 0; i < 32; i = i + 1) begin
                gqc[i] = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                          $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                gqs[i] = {8'(108 + $urandom_range(0, 38)), 8'(108 + $urandom_range(0, 38)), 8'(108 + $urandom_range(0, 38)),
                          8'(108 + $urandom_range(0, 38))};
                gqw[i] = {1'($urandom), 8'(112 + $urandom_range(0, 28)), 7'($urandom)};
            end
            while (!u.rl[3]) @(negedge ck);
            repeat (d - 1) @(negedge ck);
            qi = {job_hdr(), 1'b1};                      // in qr after edge E + d
            for (i = 0; i < 32; i = i + 1) begin
                @(negedge ck); qi = {gqc[i], 1'b1};
                @(negedge ck); qi = {464'd0, gqw[i], gqs[i], 1'b1};
            end
            @(negedge ck); qi = '0;
            repeat (220 - 65) @(negedge ck);
            for (c = 0; c < 4; c = c + 1) begin qbr[c] = |bad_r[8 * c +: 8]; qbf[c] = |bad_f[8 * c +: 8]; end
            if (|bad_r) ep_qbad_r = ep_qbad_r + 1;
            if (|bad_f) ep_qbad_f = ep_qbad_f + 1;
            cnt_d[d] = cnt_d[d] + 1;
            if (|bad_r || |bad_f) cnt_bad_d[d] = cnt_bad_d[d] + 1;
            if (pf5) cnt_pf_d[d] = cnt_pf_d[d] + 1;
            if (pf5 !== (d < PRIME_EXP)) begin
                pf_wrong = pf_wrong + 1;
                if (pf_wrong <= 4) $display("PFWRONG ep %0d d %0d pf5 %0d st_p %h", ep, d, pf5, st_p);
            end
            o_r0 = n_open_rp5; o_f0 = n_open_fp5;
            kvalid = 1'b1;
            repeat (NK) @(negedge ck);
            kvalid = 1'b0;
            repeat (LAT + 4) @(negedge ck);
            if (n_open_rp5 != o_r0 || n_open_fp5 != o_f0) cnt_open_d[d] = cnt_open_d[d] + 1;
            if (ep_odiff) cnt_od_d[d] = cnt_od_d[d] + 1;
        end
        for (i = 1; i <= DM; i = i + 1)
            $display("D %0d epochs %0d qbad %0d prime_fault %0d fail_open_ep %0d out_diff_ep %0d", i, cnt_d[i],
                     cnt_bad_d[i], cnt_pf_d[i], cnt_open_d[i], cnt_od_d[i]);
        $display("kr %0d mutk %0d epochs %0d cyc %0d valid %0d vfault %0d pf_records %0d qbad_ep_ref %0d qbad_ep_fp %0d",
                 KR, MUTK, NEP, n_cyc, n_valid, n_vfault, n_pfrec, ep_qbad_r, ep_qbad_f);
        $display("mismatch %0d fail_open_ref %0d fail_open_fp %0d fail_open_ref_p %0d fail_open_fp_p %0d pf_wrong %0d",
                 n_mis, n_open_r, n_open_f, n_open_rp, n_open_fp, pf_wrong);
        $display("fail_open_ref_p5 %0d fail_open_fp_p5 %0d fc_seen_u %b", n_open_rp5, n_open_fp5, fc_seen);
        $display("out_diff_all %0d out_diff_ge6 %0d chunk_in_diff %0d pk_bad %0d", n_odiff, n_odiff_ge6, n_cdiff, pk_bad);
        if (n_mis == 0 && n_open_rp == 0 && n_open_fp == 0 && n_open_rp5 == 0 && n_open_fp5 == 0 && pf_wrong == 0 && n_odiff_ge6 == 0 && n_cdiff == 0 &&
            pk_bad == 0 && n_valid > 10000)
            $display("PASS irg_prime kr %0d mutk %0d", KR, MUTK);
        else
            $display("FAIL irg_prime kr %0d mutk %0d", KR, MUTK);
        $finish;
    end
endmodule
