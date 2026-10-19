`timescale 1ns/1ps
// LB2-S81/CC-GU (10-18): the compiled G-unit programme of one layer on the REAL units: dsdv_seq_host (boots
// prog/host_boot.memh through its host lane, one host word every 5th edge, then ONE job start on f_ks) -> its cw port ->
// a CW_AGE-edge register line (stand-in for the die's st_cw_seqhost_* stations + ld_cw_seqhost landing: the compiler's
// link age; the link RTL is the die bind's) -> dsdv_gunit (all six leaves + side leaves).  Layer edge 0 = t_ks + 4 (the
// issuer register of calendar age 0, dsdv_seq_host header).  The slices' HP / SC beats are injected on vi_n / vi_s at
// the lowering's planned layer edges (stim_*.memh, fixture data); every beat leaving vo_n / vo_s and every job word on
// the gunit cw pin must be the next expected one AT its planned layer edge, bit-exact (exp_*.memh); the L4 roots
// (24 fn + sum of squares) and the L4r rsqrt of each HC job are read at the leaves and compared with the fixtures; no
// gunit / seq_host fault.  Prints GU_LAYER PASS / GU_LAYER FAIL <n>.  +measure prints every output edge.
module tb_gu_layer;
    localparam integer V = 276;
`ifndef CW_AGE
    localparam integer CW_AGE = 25;
`else
    localparam integer CW_AGE = `CW_AGE;
`endif
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    // ---------------------------------------------------------------- seq_host
    reg [514:0] f_host = 0; wire [76:0] t_host; reg [52:0] f_ks = 0; wire [53:0] t_kd;
    wire [V-1:0] h_vo_s, h_vo_n;
    wire cw_v; wire [9:0] cw_a; wire [255:0] cw_d;
    wire [32:0] s_j; wire [291:0] s_hw_w, s_hw_e;
    dsdv_seq_host #(.V(V)) u_sh (.ck(ck), .rst_n(rst_n), .tap_k(8'h00), .sink_k(8'h00), .vi_s({V{1'b0}}), .vo_s(h_vo_s),
        .vi_n({V{1'b0}}), .vo_n(h_vo_n), .f_host(f_host), .t_host(t_host), .f_lf(4'b0101), .f_ks(f_ks), .t_kd(t_kd),
        .s_j(s_j), .s_jd_w(2'b00), .s_jd_e(2'b00), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(9'd0), .s_hc_e(9'd0),
        .st_rg_w(2'b01), .st_rg_e(2'b01), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    // ---------------------------------------------------------------- cw link (CW_AGE register stages)
    reg [266:0] cl [0:CW_AGE-1];
    integer q;
    always @(posedge ck) begin cl[0] <= {cw_d, cw_a, cw_v}; for (q = 1; q < CW_AGE; q = q + 1) cl[q] <= cl[q - 1]; end
    wire g_cw_v = rst_n && cl[CW_AGE-1][0]; wire [9:0] g_cw_a = cl[CW_AGE-1][10:1]; wire [255:0] g_cw_d = cl[CW_AGE-1][266:11];
    // ---------------------------------------------------------------- gunit
    reg [V-1:0] vi_n = 0, vi_s = 0; wire [V-1:0] vo_n, vo_s; wire g_fault;
    dsdv_gunit #(.V(V)) u_gu (.clk(ck), .rst_n(rst_n), .sid(4'd3), .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n),
        .cw_v(g_cw_v), .cw_a(g_cw_a), .cw_d(g_cw_d), .fault(g_fault));
    // ---------------------------------------------------------------- images
    reg [514:0] HS [0:1023];
    reg [307:0] SN [0:2047], SS [0:2047], EN [0:63], ES [0:63], EC [0:15];
    reg [31:0] EI [0:63];
    reg [1023:0] dir;
    integer nhs, nsn, nss, nen, nes, nec, tend, measure, hsp = 0, cyc = 0, t_ks = -1, launch0 = -1, base = -1;
    integer pn = 0, ps = 0, qn = 0, qs = 0, qc = 0, errs = 0, job = 0, nroot = 0, nr = 0;
    integer age_n = -1, age_s = -1, hc_row0 = 1000, hc_row1 = 1008;
    integer age_last_n = -1, age_last_s = -1, age_last_cw = -1;
    initial begin
        if (!$value$plusargs("HC_AGE_N=%d", age_n)) age_n = -1;
        if (!$value$plusargs("HC_AGE_S=%d", age_s)) age_s = -1;
        if (!$value$plusargs("HC_ROW0=%d", hc_row0)) hc_row0 = 1000;
        if (!$value$plusargs("HC_ROW1=%d", hc_row1)) hc_row1 = 1008;
    end
    initial begin
        if (!$value$plusargs("dir=%s", dir)) $fatal(1, "+dir required");
        if (!$value$plusargs("nhs=%d", nhs)) $fatal(1, "+nhs");
        if (!$value$plusargs("nsn=%d", nsn)) $fatal(1, "+nsn");
        if (!$value$plusargs("nss=%d", nss)) $fatal(1, "+nss");
        if (!$value$plusargs("nen=%d", nen)) $fatal(1, "+nen");
        if (!$value$plusargs("nes=%d", nes)) $fatal(1, "+nes");
        if (!$value$plusargs("nec=%d", nec)) $fatal(1, "+nec");
        if (!$value$plusargs("tend=%d", tend)) $fatal(1, "+tend");
        if (!$value$plusargs("measure=%d", measure)) measure = 0;
        $readmemh({dir, "/prog/host_boot.memh"}, HS, 0, nhs - 1);
        $readmemh({dir, "/stim_n.memh"}, SN, 0, nsn - 1);
        $readmemh({dir, "/stim_s.memh"}, SS, 0, nss - 1);
        $readmemh({dir, "/exp_n.memh"}, EN, 0, nen - 1);
        $readmemh({dir, "/exp_s.memh"}, ES, 0, nes - 1);
        $readmemh({dir, "/exp_c.memh"}, EC, 0, nec - 1);
        $readmemh({dir, "/exp_int.memh"}, EI, 0, 2 * 26 - 1);
        repeat (10) @(posedge ck); #0.2 rst_n = 1;
    end
    always @(posedge ck) if (rst_n) cyc <= cyc + 1;
    // ---------------------------------------------------------------- stimulus (negedge: captured on posedge cyc)
    always @(negedge ck) if (rst_n) begin
        f_host <= 515'd0; f_ks <= 53'd0; vi_n <= {V{1'b0}}; vi_s <= {V{1'b0}};
        if (cyc > 30 && cyc % 5 == 0 && hsp < nhs) begin f_host <= HS[hsp]; hsp = hsp + 1; end
        // launch rule of tb_dv_prog_seqhost / tb_dsdv_seq_host (issuer start phase)
        if (launch0 < 0 && hsp == nhs && u_sh.u_l1.u_iss.sealed && u_sh.u_l1.u_iss.phase_q == 2'd0 && cyc > 200)
            launch0 = cyc + 29;
        if (launch0 >= 0 && t_ks < 0 && cyc + 1 == launch0) begin
            f_ks <= {1'b1, 10'd37, 21'd1000, 21'd5000}; t_ks = cyc + 1; base = t_ks + 4;
            $display("GU KS %0d base %0d", t_ks, base);
        end
        if (base >= 0) begin
            if (pn < nsn && SN[pn][307:276] == cyc - base) begin vi_n <= SN[pn][275:0]; pn = pn + 1; end
            if (ps < nss && SS[ps][307:276] == cyc - base) begin vi_s <= SS[ps][275:0]; ps = ps + 1; end
        end
    end
    // ---------------------------------------------------------------- monitor (posedge cyc: the values the gunit / its
    // neighbours capture on this edge)
    always @(posedge ck) if (rst_n) begin
        // Actual port-capture edges, independent of planned expected timestamps.
        if (vi_n[0] && vi_n[4:1] == 4'd7) begin
            age_last_n = cyc - base;
            if (measure && vi_n[44:40] == 5'd23)
                $display("GU_AGE_HP N edge=%0d acc=%0d source=%0d", cyc-base, vi_n[44:40], vi_n[12:9]);
        end
        if (vi_s[0] && vi_s[4:1] == 4'd7) begin
            age_last_s = cyc - base;
            if (measure && vi_s[44:40] == 5'd23)
                $display("GU_AGE_HP S edge=%0d acc=%0d source=%0d", cyc-base, vi_s[44:40], vi_s[12:9]);
        end
        if (g_cw_v && g_cw_a[9:8] == 2'b10 && g_cw_a[0]) begin
            age_last_cw = cyc - base;
            $display("GU_AGE_ISSUE edge=%0d which=%0d row=%0d", cyc-base, g_cw_d[41], g_cw_d[30:21]);
        end
        if (vo_n[0] && vo_n[60:57] == 4'hf &&
            (vo_n[56:47] == hc_row0 || vo_n[56:47] == hc_row1)) begin
            $display("GU_AGE_RESULT N edge=%0d row=%0d last_hp_n=%0d last_hp_s=%0d issue=%0d age_from_n=%0d", cyc-base, vo_n[56:47], age_last_n, age_last_s, age_last_cw, cyc-base-age_last_n);
            if (age_n >= 0 && cyc-base-age_last_n != age_n) begin
                errs = errs + 1;
                $display("GU_AGE_CONTRACT_FAIL N measured=%0d expected=%0d", cyc-base-age_last_n, age_n);
            end
        end
        if (vo_s[0] && vo_s[60:57] == 4'hf &&
            (vo_s[56:47] == hc_row0 || vo_s[56:47] == hc_row1)) begin
            $display("GU_AGE_RESULT S edge=%0d row=%0d last_hp_n=%0d last_hp_s=%0d issue=%0d age_from_n=%0d", cyc-base, vo_s[56:47], age_last_n, age_last_s, age_last_cw, cyc-base-age_last_n);
            if (age_s >= 0 && cyc-base-age_last_n != age_s) begin
                errs = errs + 1;
                $display("GU_AGE_CONTRACT_FAIL S measured=%0d expected=%0d", cyc-base-age_last_n, age_s);
            end
        end
        if (vo_n[0]) begin
            if (measure) $display("GU OUT N %0d %h", cyc - base, vo_n);
            if (qn < nen && EN[qn][307:276] == cyc - base && EN[qn][275:0] == vo_n) qn = qn + 1;
            else begin errs = errs + 1; if (errs < 12) $display("ERR vo_n beat at layer edge %0d (expected #%0d at %0d)", cyc - base, qn, EN[qn][307:276]); end
        end
        if (vo_s[0]) begin
            if (measure) $display("GU OUT S %0d %h", cyc - base, vo_s);
            if (qs < nes && ES[qs][307:276] == cyc - base && ES[qs][275:0] == vo_s) qs = qs + 1;
            else begin errs = errs + 1; if (errs < 12) $display("ERR vo_s beat at layer edge %0d (expected #%0d at %0d)", cyc - base, qs, ES[qs][307:276]); end
        end
        if (g_cw_v && g_cw_a[9]) begin
            if (measure) $display("GU CW %0d %h %h", cyc - base, g_cw_a, g_cw_d);
            if (qc < nec && EC[qc][307:276] == cyc - base && EC[qc][265:0] == {g_cw_a, g_cw_d}) qc = qc + 1;
            else begin errs = errs + 1; if (errs < 12) $display("ERR gunit job on cw at layer edge %0d (expected #%0d at %0d)", cyc - base, qc, EC[qc][307:276]); end
        end
        // L4 roots (fn rows 0..23, sum of squares 24) and L4r rsqrt of each HC job vs the fixtures
        if (u_gu.u_l4.root_v) begin
            if (u_gu.u_l4.root != EI[26 * job + u_gu.u_l4.root_acc]) begin
                errs = errs + 1; if (errs < 12) $display("ERR job %0d root acc %0d %h != %h", job, u_gu.u_l4.root_acc, u_gu.u_l4.root, EI[26 * job + u_gu.u_l4.root_acc]);
            end
            if (measure) $display("GU ROOT %0d job %0d acc %0d %h", cyc - base, job, u_gu.u_l4.root_acc, u_gu.u_l4.root);
            nroot = nroot + 1;
        end
        if (u_gu.u_l4r.r_v) begin
            if (u_gu.u_l4r.r_y != EI[26 * job + 25]) begin
                errs = errs + 1; if (errs < 12) $display("ERR job %0d rsqrt %h != %h", job, u_gu.u_l4r.r_y, EI[26 * job + 25]);
            end
            if (measure) $display("GU RSQRT %0d job %0d %h", cyc - base, job, u_gu.u_l4r.r_y);
            nr = nr + 1;
        end
        if (u_gu.u_l4.launch) job = job + 1;
        if (base >= 0 && cyc - base == tend) begin
            if (g_fault) begin errs = errs + 1; $display("ERR gunit fault"); end
            if (qn != nen || qs != nes || qc != nec || pn != nsn || ps != nss || nroot != 50 || nr != 2) begin
                errs = errs + 1;
                $display("ERR counts out n %0d/%0d s %0d/%0d cw %0d/%0d  in n %0d/%0d s %0d/%0d roots %0d/50 rsqrt %0d/2",
                         qn, nen, qs, nes, qc, nec, pn, nsn, ps, nss, nroot, nr);
            end
            if (errs == 0) $display("GU_LAYER PASS layer edges: %0d jobs, %0d HP/SC beats in, %0d CTL rows out each side, roots %0d, rsqrt %0d, no fault",
                                    nec, nsn + nss, nen, nroot, nr);
            else $display("GU_LAYER FAIL %0d", errs);
            $finish;
        end
    end
    initial begin #3000000; $display("GU_LAYER FAIL timeout"); $finish; end
endmodule
