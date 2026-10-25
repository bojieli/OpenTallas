`timescale 1ns/1ps
// MU-S81-2/SEQ (2026-10-19): the multi-user host plane on the REAL seq_host parent the MU die binds.
//   default: dsdv_seq_host_mux = the parameter-free p4l MU die master (bind_table_p4l3_mu): dsdv_seq_host_mu
//          NSLOT 47 / NEV 8 / NEP 4 / NRT 2 around the real dsdv_seq_host (L0 link, L1 ot_dsdv_fixed_issue, L2 V packer,
//          L3/L4 hops), its boot config f_mc decoded from host CSR 0x15 words on f_host (0 die wires).
//   +define+PLAIN: the plain single-user dsdv_seq_host (p4l die of record) -- the zero-latency / bit-identity reference.
// The compiled layer programme (dv_layer_compile prog/host_boot.memh) boots through the host lane (one word every 5th
// edge, as tb_dv_prog_seqhost), then the CSR words of +cfg=FILE ("IDX WORD" hex a line: 0x15 f_mc = gap table, RL;
// 0x16 f_mw = window events / per-slot attributes; sent in BOTH modes, the plain unit's ingest ignores them), then the job
// starts of +mu=FILE ("shift user pos tok [slot]" a line; shift in edges after the launch edge) on f_ks.
// Logs (posedge, edge = cyc): PROG KS / VO S|N / CW / SJ / KD (all 54 b of t_kd) / MC <ep> (mu_c, 34 b) / MR <ep>
// (mu_rc, 11 b) / FAULT (issuer) / MF (first edge of each t_mf bit) and at the end FCODE, STATUS, TMF, END.
// check_seq_host_mu.py compares runs.  MU_MUT (bench mutants of dsdv_mu_hslot, set by defparam on the MUX path).
module tb_dsdv_seq_host_mu;
    localparam integer MUX = 1;
  `define ISS g_mux.dut.u_seqhost.u.u_u.u_l1.u_iss
    localparam integer V = 276, NMU = 256, NHS = 16384;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    reg [V-1:0] vi_s = 0, vi_n = 0; wire [V-1:0] vo_s, vo_n;
    reg [514:0] f_host = 0; wire [76:0] t_host; reg [52:0] f_ks = 0; wire [53:0] t_kd;
    wire cw_v; wire [9:0] cw_a; wire [255:0] cw_d;
    wire [32:0] s_j; reg [1:0] s_jd_w = 0, s_jd_e = 0; wire [291:0] s_hw_w, s_hw_e; reg [8:0] s_hc_w = 0, s_hc_e = 0;
    reg [1:0] st_rg_w = 2'b01, st_rg_e = 2'b01;
    wire [3:0] t_mf; wire [4*34-1:0] mu_c; wire [4*11-1:0] mu_rc; reg [31:0] mu_rt_7n = 0, mu_rt_0n = 0;
    if (1) begin : g_mux
        wire sid_l, vid_l;
        dsdv_hostb_seqhost_mux #(.HOSTB_ENABLE(0), .STATIC_KS6(0)) dut (
            .select_hbe(1'b0), .hbe_f_host(515'd0), .starter_f_ks(53'd0), .hbe_ks_slot(3'd0),
            .engram_f_ks(), .hb_starter_armed(), .sid_ri(sid_l), .vid_ri(vid_l), .sid_ro(sid_l), .vid_ro(vid_l),.ck(ck), .rst_n(rst_n), .tap_k(8'h00), .sink_k(8'h00), .vi_s(vi_s), .vo_s(vo_s),
            .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(4'b0101), .f_ks(f_ks), .t_kd(t_kd),
            .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w),
            .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d),
            .mu_c_7n(mu_c[0 +: 34]), .mu_c_7s(mu_c[34 +: 34]), .mu_c_0n(mu_c[68 +: 34]), .mu_c_0s(mu_c[102 +: 34]),
            .mu_rc_7n(mu_rc[0 +: 11]), .mu_rc_7s(mu_rc[11 +: 11]), .mu_rc_0n(mu_rc[22 +: 11]), .mu_rc_0s(mu_rc[33 +: 11]),
            .mu_rt_7n(mu_rt_7n), .mu_rt_0n(mu_rt_0n));
        // S81/PORTFIX-FLT 10-25: t_mf is internal now (bench tap); the fault rings are closed head -> end (no stops)
        assign t_mf = dut.t_mf;
    end
    // the issuer of the real unit (fixed_issue): sealed / start phase / fault, through either wrapper
    wire iss_sealed = `ISS.sealed;
    wire [1:0] iss_ph = `ISS.phase_q;
    wire iss_fault = `ISS.fault;
    wire [3:0] iss_code = `ISS.fault_code;
    wire [15:0] iss_jobs = 16'(`ISS.st_jobs);
    reg [514:0] HS [0:NHS-1];
    reg [25:0] CF [0:NHS-1]; reg [7:0] CI [0:NHS-1]; reg [7:0] ci;
    // Fleet closure paths can exceed128bytes; strings preserve full manifest paths.
    string dir, mufile, cfgfile;
    integer nhs, ncf = 0, hsp = 0, cfp = 0, cyc = 0, t_ks = -1, ncy, launch0 = -1, tmo;
    integer nmu = 0, kmu = 0, fd, rc;
    integer mu_sh [0:NMU-1]; reg [9:0] mu_us [0:NMU-1]; reg [20:0] mu_ps [0:NMU-1], mu_tk [0:NMU-1];
    integer a0, a1, a2, a3;
    reg [25:0] cw;
    reg flt_q = 0; reg [3:0] mf_q = 0;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) $fatal(1, "+dir required");
        if (!$value$plusargs("n=%d", nhs)) $fatal(1, "+n required");
        if (!$value$plusargs("cyc=%d", ncy)) ncy = 3000;
        if (!$value$plusargs("timeout=%d", tmo)) tmo = 4000000;
        $readmemh({dir, "/prog/host_boot.memh"}, HS, 0, nhs - 1);
        if ($value$plusargs("cfg=%s", cfgfile)) begin
            fd = $fopen(cfgfile, "r");
            if (fd == 0) $fatal(1, "+cfg file");
            while (!$feof(fd) && ncf < NHS) begin
                rc = $fscanf(fd, "%h %h\n", ci, cw);
                if (rc == 2) begin CI[ncf] = ci; CF[ncf] = cw; ncf = ncf + 1; end
            end
            $fclose(fd);
        end
        if (!$value$plusargs("mu=%s", mufile)) $fatal(1, "+mu required");
        fd = $fopen(mufile, "r");
        if (fd == 0) $fatal(1, "+mu file");
        while (!$feof(fd) && nmu < NMU) begin
            rc = $fscanf(fd, "%d %d %d %d", a0, a1, a2, a3);
            if (rc == 4) begin mu_sh[nmu] = a0; mu_us[nmu] = a1[9:0]; mu_ps[nmu] = a2[20:0]; mu_tk[nmu] = a3[20:0]; nmu = nmu + 1; end
            rc = $fgetc(fd); while (rc != 10 && rc != -1) rc = $fgetc(fd);       // optional trailing columns (slot)
        end
        $fclose(fd);
        $display("PROG MUX %0d MU %0d starts CFG %0d words", MUX, nmu, ncf);
        repeat (10) @(posedge ck); #0.2 rst_n = 1;
    end
    always @(posedge ck) if (rst_n) cyc <= cyc + 1;
    always @(negedge ck) if (rst_n) begin
        f_host <= 515'd0; f_ks <= 53'd0;
        if (cyc > 30 && cyc % 5 == 0) begin
            if (hsp < nhs) begin f_host <= HS[hsp]; hsp = hsp + 1; end
            else if (cfp < ncf) begin                     // CSR 0x15 / 0x16 {h_cls 0, h_d[7:0] index, h_d[57:32] word, h_v}
                f_host <= {2'd0, 454'd0, CF[cfp], 24'd0, CI[cfp], 1'b1}; cfp = cfp + 1;
            end
        end
        // launch rule of tb_dv_prog_seqhost: once booted and sealed, phase_q 0 seen at cyc -> launch edge cyc + 29
        if (launch0 < 0 && hsp == nhs && cfp == ncf && iss_sealed && iss_ph == 2'd0 && cyc > 200) launch0 = cyc + 29;
        if (launch0 >= 0 && kmu < nmu && cyc + 1 == launch0 + mu_sh[kmu]) begin
            f_ks <= {1'b1, mu_us[kmu], mu_tk[kmu], mu_ps[kmu]}; t_ks = cyc + 1;
            $display("PROG KS %0d user %0d pos %0d tok %0d shift %0d", t_ks, mu_us[kmu], mu_ps[kmu], mu_tk[kmu], mu_sh[kmu]);
            kmu = kmu + 1;
        end
    end
    integer e;
    always @(posedge ck) if (rst_n) begin
        if (vo_s[0]) $display("PROG VO S %0d %h", cyc, vo_s);
        if (vo_n[0]) $display("PROG VO N %0d %h", cyc, vo_n);
        if (cw_v) $display("PROG CW %0d %h %h", cyc, cw_a, cw_d);
        if (s_j[32]) $display("PROG SJ %0d %h", cyc, s_j);
        if (t_kd[53]) $display("PROG KD %0d %h", cyc, t_kd);
        for (e = 0; e < 4; e = e + 1) begin
            if (mu_c[34 * e]) $display("PROG MC%0d %0d %h", e, cyc, mu_c[34 * e +: 34]);
            if (mu_rc[11 * e]) $display("PROG MR%0d %0d %h", e, cyc, mu_rc[11 * e +: 11]);
        end
        if (iss_fault && !flt_q) $display("PROG FAULT %0d code %0d", cyc, iss_code);
        for (e = 0; e < 4; e = e + 1) if (t_mf[e] && !mf_q[e]) $display("PROG MF %0d bit %0d", cyc, e);
        flt_q <= iss_fault; mf_q <= t_mf;
        if (t_ks >= 0 && cyc == t_ks + ncy && kmu == nmu) begin
            $display("PROG FCODE %0d fault %0d jobs %0d", iss_code, iss_fault, iss_jobs);
            $display("PROG STATUS %0d t_host %h", cyc, t_host);
            $display("PROG TMF %b", t_mf);
            $display("PROG END");
            $finish;
        end
        if (cyc > tmo) begin $display("PROG TIMEOUT launch0=%0d hsp=%0d/%0d cfp=%0d/%0d kmu=%0d/%0d", launch0, hsp, nhs, cfp,
            ncf, kmu, nmu); $finish; end
    end
endmodule
