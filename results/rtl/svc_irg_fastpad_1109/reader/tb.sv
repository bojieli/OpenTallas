`timescale 1ns/1ps
// die-s81-85 11-09: IRG fastpad READER bench.  One dsdv_idx_rg3 (KR by -G) runs its own sequencing: cold reset, then
// epochs of {warm reset (random 1..12 edges), job frame (IDX_S header + 64 query words) whose header reaches the
// reader's qr pin flop D edges after the reader's reset leaves release, D = 1..DM swept}.  The reader's own chunk-
// column inputs (g_ch[gc].{qv_c, qh_c, qc_c, qs_c}, rst_n = rl[26 + gc]) drive two shadow engines of 4 chunks each:
// chk_ref (original dsdv_idx_rg2_chunk) and chk_fp (OT_IDX_HSLICE_FASTPAD chunk); a bench key stream (1 key / cycle)
// feeds both.  Checks:
//  * q state: 220 edges after the header every slice (chunk gc, position h, head 8 gc + h) holds the frame's query
//    {codes, scales, w} for its head (q_bad_ref / q_bad_fp per chunk per epoch)
//  * records: keys from header + 220 for NK cycles are valid; c_sum / c_fault of ref vs fp compared same cycle
//    (ring of 106, cleared on reset).  fail_open_x = valid records of form x with c_fault 0 from a chunk whose q
//    state is bad; guarded = fp c_fault 1 while ref 0 with fp q_early set (fail-closed guard); mismatch = any other
//    ref / fp difference.
//  * MUTK = k (1..7): the shadow chunks' reset is released k edges after the reader's leaves (= the reader issues its
//    first query load k edges earlier relative to the slices' release).
module tb;
    parameter integer KR = 0;
    localparam integer LAT = 106, NK = 200, HC = 8;
    reg ck = 1'b0;
    always #5 ck = ~ck;
    reg rst = 1'b0;
    reg [512:0] qi = '0;
    wire [512:0] qo; wire [275:0] so; wire [183:0] rqo; wire [9:0] st;
    dsdv_idx_rg3 #(.SRAM_MACRO(1'b0), .KR(KR), .OH(2), .RH(2), .IH(0)) u (.ck(ck), .rst(rst), .sid(4'd0), .qi(qi),
        .qo(qo), .si(276'd0), .so(so), .rqo(rqo), .rri(1088'd0), .st(st));
    integer MUTK, DM, NEP, SEED, DFIX;
    initial begin
        if (!$value$plusargs("MUTK=%d", MUTK)) MUTK = 0;
        if (!$value$plusargs("DM=%d", DM)) DM = 12;
        if (!$value$plusargs("NEP=%d", NEP)) NEP = 240;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        if (!$value$plusargs("D=%d", DFIX)) DFIX = 0;
    end
    reg [543:0] kk = '0;
    // golden query of the current epoch
    reg [511:0] gqc [0:31]; reg [31:0] gqs [0:31]; reg [15:0] gqw [0:31];
    wire [31:0] rsum [0:3], fsum [0:3]; wire [3:0] rf, ff;
    wire [31:0] bad_r, bad_f; wire [3:0] qe;
    genvar gc, gh;
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_sh
        wire rl_c = u.rl[26 + gc];
        reg [7:0] dl;
        always @(posedge ck or negedge rl_c) if (!rl_c) dl <= 8'd0; else dl <= {dl[6:0], 1'b1};
        wire srst = (MUTK == 0) ? rl_c : dl[MUTK - 1];
        wire qv = u.g_ch[gc].qv_c; wire [7:0] qh = u.g_ch[gc].qh_c; wire [511:0] qc = u.g_ch[gc].qc_c;
        wire [47:0] qs = u.g_ch[gc].qs_c;
        chk_ref u_r (.clk(ck), .rst_n(srst), .hb(8'(8 * gc)), .ql_v(qv), .ql_head(qh), .ql_codes(qc), .ql_sc(qs[31:0]),
                     .ql_w(qs[47:32]), .k_key(kk), .c_sum(rsum[gc]), .c_fault(rf[gc]));
        chk_fp  u_f (.clk(ck), .rst_n(srst), .hb(8'(8 * gc)), .ql_v(qv), .ql_head(qh), .ql_codes(qc), .ql_sc(qs[31:0]),
                     .ql_w(qs[47:32]), .k_key(kk), .c_sum(fsum[gc]), .c_fault(ff[gc]));
`ifdef GUARD
        assign qe[gc] = u_f.q_early;
`else
        assign qe[gc] = 1'b0;
`endif
        for (gh = 0; gh < HC; gh = gh + 1) begin : g_q
            assign bad_r[8 * gc + gh] = {u_r.g_s[gh].u_s.qc, u_r.g_s[gh].u_s.qs, u_r.g_s[gh].u_s.qw}
                                        !== {gqc[8 * gc + gh], gqs[8 * gc + gh], gqw[8 * gc + gh]};
            assign bad_f[8 * gc + gh] = {u_f.g_s[gh].u_s.qc, u_f.g_s[gh].u_s.qs, u_f.g_s[gh].u_s.qw}
                                        !== {gqc[8 * gc + gh], gqs[8 * gc + gh], gqw[8 * gc + gh]};
        end
    end endgenerate
    // ---- record ring + checks (sample at negedge, then drive)
    reg [LAT-1:0] ring = '0;
    reg kvalid = 1'b0;
    reg [3:0] qbr = 4'd0, qbf = 4'd0;      // per chunk q state bad (this epoch, after the check)
    longint n_valid = 0, n_vfault = 0, n_mis = 0, n_open_r = 0, n_open_f = 0, n_guard = 0, n_cyc = 0;
    integer ep_qbad_r = 0, ep_qbad_f = 0, ep_guard = 0, ep_early_d [0:31], ep_d [0:31];
    integer c;
    always @(negedge ck) begin
        n_cyc = n_cyc + 1;
        if (ring[LAT-1]) for (c = 0; c < 4; c = c + 1) begin
            n_valid = n_valid + 1;
            if (rf[c]) n_vfault = n_vfault + 1;
            if (!rf[c] && qbr[c]) n_open_r = n_open_r + 1;
            if (!ff[c] && qbf[c]) n_open_f = n_open_f + 1;
            if (ff[c] && !rf[c] && qe[c]) n_guard = n_guard + 1;
            else if (rsum[c] !== fsum[c] || rf[c] !== ff[c]) begin
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
    integer ep, i, d, rlen, nb;
    reg [7:0] cnt_d [0:31]; reg [7:0] cnt_bad_d [0:31]; reg [7:0] cnt_grd_d [0:31];
    initial begin
        void'($urandom(SEED));
        for (i = 0; i < 32; i = i + 1) begin gqc[i] = '0; gqs[i] = '0; gqw[i] = '0; cnt_d[i] = 0; cnt_bad_d[i] = 0; cnt_grd_d[i] = 0; end
        repeat (20) @(negedge ck);
        for (ep = 0; ep < NEP; ep = ep + 1) begin
            // warm (or cold) reset
            @(negedge ck); rst = 1'b0; kvalid = 1'b0; qbr = 4'd0; qbf = 4'd0;
            rlen = (ep == 0) ? 20 : $urandom_range(1, 12);
            repeat (rlen) @(negedge ck);
            rst = 1'b1;
            // new epoch query
            for (i = 0; i < 32; i = i + 1) begin
                gqc[i] = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                          $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                gqs[i] = {8'(108 + $urandom_range(0, 38)), 8'(108 + $urandom_range(0, 38)), 8'(108 + $urandom_range(0, 38)),
                          8'(108 + $urandom_range(0, 38))};
                gqw[i] = {1'($urandom), 8'(112 + $urandom_range(0, 28)), 7'($urandom)};
            end
            // reader reset leaves released after edge E: rl[3] seen high at the negedge after E
            while (!u.rl[3]) @(negedge ck);
            d = (DFIX != 0) ? DFIX : 1 + (ep % DM);
            repeat (d - 1) @(negedge ck);
            qi = {job_hdr(), 1'b1};                      // in qr after edge E + d
            for (i = 0; i < 32; i = i + 1) begin
                @(negedge ck); qi = {gqc[i], 1'b1};
                @(negedge ck); qi = {464'd0, gqw[i], gqs[i], 1'b1};
            end
            @(negedge ck); qi = '0;
            repeat (220 - 65) @(negedge ck);
            // q state check, then valid keys
            nb = 0;
            for (c = 0; c < 4; c = c + 1) begin qbr[c] = |bad_r[8 * c +: 8]; qbf[c] = |bad_f[8 * c +: 8]; end
            if (|bad_r) ep_qbad_r = ep_qbad_r + 1;
            if (|bad_f) ep_qbad_f = ep_qbad_f + 1;
            if (|qe) ep_guard = ep_guard + 1;
            cnt_d[d] = cnt_d[d] + 1; if (|bad_f) cnt_bad_d[d] = cnt_bad_d[d] + 1; if (|qe) cnt_grd_d[d] = cnt_grd_d[d] + 1;
            if ((|bad_r || |bad_f) && ep_qbad_f + ep_qbad_r <= 12)
                $display("QBAD ep %0d d %0d ref_bad %b fp_bad %b q_early %b", ep, d, bad_r, bad_f, qe);
            kvalid = 1'b1;
            repeat (NK) @(negedge ck);
            kvalid = 1'b0;
            repeat (LAT + 4) @(negedge ck);
        end
        for (i = 1; i <= DM; i = i + 1)
            $display("D %0d epochs %0d fp_qbad %0d guard %0d", i, cnt_d[i], cnt_bad_d[i], cnt_grd_d[i]);
        $display("kr %0d mutk %0d epochs %0d cyc %0d valid %0d vfault %0d qbad_ep_ref %0d qbad_ep_fp %0d guard_ep %0d",
                 KR, MUTK, NEP, n_cyc, n_valid, n_vfault, ep_qbad_r, ep_qbad_f, ep_guard);
        $display("mismatch %0d fail_open_ref %0d fail_open_fp %0d guarded_records %0d", n_mis, n_open_r, n_open_f, n_guard);
        if (n_mis == 0 && n_open_f == 0 && n_valid > 10000 && n_vfault < n_valid)
            $display("PASS irg_reader kr %0d mutk %0d", KR, MUTK);
        else
            $display("FAIL irg_reader kr %0d mutk %0d", KR, MUTK);
        $finish;
    end
endmodule
