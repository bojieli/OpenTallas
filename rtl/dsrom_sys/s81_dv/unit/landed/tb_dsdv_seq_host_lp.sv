`timescale 1ns/1ps
// S81U-SEQ bench for dsdv_seq_host: lock-step against the REUSED goldens, cycle-exact on every unit output.
//   golden host  dsfd_host_c (+DSFD_HOST_C_STATIC, ckv = ck) fed the same host stream (minus the 0x13 template words the
//                unit intercepts): s_hw must equal its hw EVERY cycle and t_host[64:0] its t_collective completions,
//                HSH edges later (S81U-SEQ7: the unit's ingest runs APIPE 6, whose registered request-FIFO write lands
//                every host sector in u_ox one edge later than the golden's APIPE 3 = the documented +1 host-path shift).
//   golden seq   ot_s81_fixed_issue (NENG 5, ENG_PRESENT 10011) loaded with the golden host's t_sseq_pw / t_sseq_plen
//                (its own paced path), reset with the unit's sequencer reset, launched D = 20 edges AHEAD of the unit
//                (same clock phase), its completions modelled from its own commands.  Every golden command maps to an
//                expected unit output: engine 0 / 1 -> CTL beat on vo_n / vo_s (template + context splice, independent
//                model) at +D+LVO, engine 2 -> cw (gunit job) at +D+LCW, engine 2 -> cw (gunit job) at +D+LCW, engine 4 -> s_j {1, arg, slot, op} at +D+LJ; host 0x14 rows -> cw at +LCF; host 0x14 rows -> cw at +LCF; KIT -> t_kd at +D+LKD.
//   rung         random traffic both ways (single beats, XQ / XB 4-fragment beats) only in slots the compiled program
//                leaves free; expected vo = arrival 6 edges later or the injected beat.
//   svc chain    a fixed-latency model per half (RTL-BUILD-S81 10-18): s_jd_w done LS edges after each s_j (the W half is
//                the far one), s_jd_e done LS - LSD edges after it; the unit's merged done must land at LS (calendar
//                row unchanged).  s_hw_w / s_hw_e must each equal the golden's hw on the cycles the golden sector routes
//                to that half (svc PC owner: pcmap(addr)[4], markers to both) and be invalid otherwise; each half returns
//                s_hc {ack 1, cr 1} 3 edges after each of its own words (marker acks from W only).  +stdrop=1: the W
//                half's region live drops after the first job and the unit's status must show rg_drop (wf[2]).
// Program: R rows over engines 0 / 1 / 2 / 4 (issue ages in disjoint residues mod 8, contexts launched 4 mod 8 apart, two
// contexts live), one KIT, one END; 6 jobs.  +collide=1: one rung arrival is placed on an injection slot of the last
// job and the unit's status fault must rise (wf[0]).  PASS line "SEQHOST PASS".
// PL-SEQ (PARENTS-LANDED 10-18): COPY of tb_dsdv_seq_host.sv (S81U-SEQ goldens, unchanged checks on the flat dut) plus a
// LANDED SHADOW: dsdv_seq_host_wf_lp (lp.py, rtl/dsrom_sys/s81_dv/unit/landed/) runs on the same golden stimulus with its
// reset RB edges earlier, every input presented OI_<p> edges later and every output compared OO_<p> edges later
// (results/arch/landed_parent_1018/dsdv_seq_host/dsdv_seq_host_wf_lp_record.json "compiler"; run_lp_shadow_bench.sh checks
// these constants against the record).  +define+LP_MUT=m selects the landed mutant (1 landing bypass, 2 read K+1,
// 4 u_l1 reset run one stage long): the shadow mismatches must turn SEQHOST PASS into FAIL.
module tb_dsdv_seq_host_lp;
    localparam integer V = 276, D = 20, LVO = 7, LJ = 2, LKD = 3, LR = 6, LS = 9, LCW = 3, LCF = 6;
    localparam integer DV_V = 5, DV_S = LS + 5, LSD = 3;
    localparam integer HSH = 1;                     // unit host path (f_host -> s_hw / t_host completion) = golden + HSH     // calendar done row = issue + DV (V beat posted / svc chain done)
`ifndef MUT
    localparam integer MUT = 0;
`else
    localparam integer MUT = `MUT;
`endif
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    integer seed, seed0, collide, cyc, errs, i, k, e;
    // ------------------------------------------------------------------ DUT
    reg [V-1:0] vi_s = 0, vi_n = 0; wire [V-1:0] vo_s, vo_n;
    reg [514:0] f_host = 0; wire [76:0] t_host; reg [52:0] f_ks = 0; wire [53:0] t_kd;
    wire cw_v; wire [9:0] cw_a; wire [255:0] cw_d;
    wire [32:0] s_j; reg [1:0] s_jd_w = 0, s_jd_e = 0; wire [291:0] s_hw_w, s_hw_e; reg [8:0] s_hc_w = 0, s_hc_e = 0;
    reg [1:0] st_rg_w = 2'b01, st_rg_e = 2'b01; integer stdrop, nhw_w = 0, nhw_e = 0, nmk = 0;
    dsdv_seq_host #(.V(V), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .tap_k(8'h00), .sink_k(8'h00), .vi_s(vi_s), .vo_s(vo_s),
        .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(4'b0101), .f_ks(f_ks), .t_kd(t_kd),
        .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e),
        .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    // ------------------------------------------------------------------ LANDED SHADOW (PL-SEQ)
`ifndef LP_MUT
    localparam integer LP_MUT = 0;
`else
    localparam integer LP_MUT = `LP_MUT;
`endif
    localparam integer RB = 5;                                   // record reset.depth
    localparam integer OI = 3, OI_VN = 0;                        // input offsets: every core port 3, vi_n 0
    localparam integer OO = 3, OO_VN = 6;                        // output offsets: every core port 3 (vo_s too), vo_n 6
    reg rst_lp = 0;
    initial begin repeat (10 - RB) @(posedge ck); #0.2 rst_lp = 1; end
    localparam integer WI = V + 515 + 53 + 2 + 2 + 9 + 9 + 2 + 2;            // core inputs, one bundle
    localparam integer WO = V + 77 + 54 + 33 + 292 + 292 + 1 + 10 + 256;      // core outputs, one bundle
    wire [WI-1:0] fi_b = {vi_s, f_host, f_ks, s_jd_w, s_jd_e, s_hc_w, s_hc_e, st_rg_w, st_rg_e};
    reg  [WI-1:0] dli [0:OI-1];
    always @(posedge ck) begin : g_dli integer j; dli[0] <= fi_b; for (j = 1; j < OI; j = j + 1) dli[j] <= dli[j - 1]; end
    wire [WI-1:0] li_b = dli[OI - 1];
    wire [V-1:0] l_vo_s, l_vo_n; wire [76:0] l_t_host; wire [53:0] l_t_kd; wire [32:0] l_s_j; wire [291:0] l_s_hw_w, l_s_hw_e;
    wire l_cw_v; wire [9:0] l_cw_a; wire [255:0] l_cw_d;
    dsdv_seq_host_wf_lp #(.V(V), .MUT(LP_MUT)) lpd (.ck_core(ck), .ck_n(ck), .rst_n(rst_lp), .tap_k(8'h00), .sink_k(8'h00),
        .vi_s(li_b[WI-1 -: V]), .vo_s(l_vo_s), .vi_n(vi_n), .vo_n(l_vo_n),
        .f_host(li_b[WI-V-1 -: 515]), .t_host(l_t_host), .f_lf(4'b0101), .f_ks(li_b[WI-V-516 -: 53]), .t_kd(l_t_kd),
        .s_j(l_s_j), .s_jd_w(li_b[25:24]), .s_jd_e(li_b[23:22]), .s_hw_w(l_s_hw_w), .s_hw_e(l_s_hw_e),
        .s_hc_w(li_b[21:13]), .s_hc_e(li_b[12:4]), .st_rg_w(li_b[3:2]), .st_rg_e(li_b[1:0]),
        .cw_v(l_cw_v), .cw_a(l_cw_a), .cw_d(l_cw_d));
    wire [WO-1:0] fo_b = {vo_s, t_host, t_kd, s_j, s_hw_w, s_hw_e, cw_v, cw_a, cw_d};
    wire [WO-1:0] lo_b = {l_vo_s, l_t_host, l_t_kd, l_s_j, l_s_hw_w, l_s_hw_e, l_cw_v, l_cw_a, l_cw_d};
    reg  [WO-1:0] dlo [0:OO-1]; reg [V-1:0] dlo_n [0:OO_VN-1];
    always @(posedge ck) begin : g_dlo integer j; dlo[0] <= fo_b; for (j = 1; j < OO; j = j + 1) dlo[j] <= dlo[j - 1];
        dlo_n[0] <= vo_n; for (j = 1; j < OO_VN; j = j + 1) dlo_n[j] <= dlo_n[j - 1]; end
    integer lp_cmp = 0, lp_mism = 0, lp_cyc = 0;
    always @(negedge ck) if (rst_n) begin
        lp_cyc = lp_cyc + 1;
        if (lp_cyc > 20) begin
            lp_cmp = lp_cmp + 1;
            if (lo_b !== dlo[OO - 1] || l_vo_n !== dlo_n[OO_VN - 1]) begin lp_mism = lp_mism + 1;
                if (lp_mism < 4) $display("LP_SHADOW MISMATCH edge %0d core %0d vo_n %0d", lp_cyc, lo_b !== dlo[OO - 1],
                                          l_vo_n !== dlo_n[OO_VN - 1]); end
        end
    end
    // ------------------------------------------------------------------ golden host
    reg [514:0] g_host = 0; wire [76:0] g_tc; wire [35:0] g_pw; wire [7:0] g_plen; wire [291:0] g_hw; reg [8:0] g_hc = 0;
    dsfd_host_c #(.NS(1), .KVS(1), .ENG(-1)) gh (.ck(ck), .rst(rst_n), .ckv(ck), .rsv(rst_n), .f_collective(g_host),
        .t_collective(g_tc), .f_lf(4'b0101), .t_sseq_pw(g_pw), .t_sseq_plen(g_plen), .f_sseq_st(6'd0), .f_wfc_ft(4'd0),
        .hw(g_hw), .hc(g_hc));
    // ------------------------------------------------------------------ golden sequencer
    reg g_jv = 0; reg [9:0] g_ju = 0; reg [20:0] g_jp = 0, g_jt = 0; reg [4:0] g_dv = 0; reg [39:0] g_dt = 0;
    wire [4:0] g_cv; wire [419:0] g_cd; wire g_done, g_kdone, g_dslot, g_busy, g_fault; wire [3:0] g_code; wire [20:0] g_ktok;
    ot_s81_fixed_issue #(.NOPS(128), .NENG(5), .STAGE(0), .ENG_PRESENT(5'b10111)) gi (.clk(ck), .rst_n(dut.u_l1.rn),
        .pw_v(g_pw[35]), .pw_a(g_pw[34:28]), .pw_d(g_pw[27:0]), .prog_len(g_plen), .job_v(g_jv), .job_user(g_ju),
        .job_pos(g_jp), .job_tok(g_jt), .job_rdy(), .busy(g_busy), .job_done(g_done), .job_kdone(g_kdone),
        .done_slot(g_dslot), .kit_tok(g_ktok), .cmd_v(g_cv), .cmd_d(g_cd), .engine_available(5'h1f), .dn_v(g_dv),
        .dn_tag(g_dt), .fault(g_fault), .fault_code(g_code), .st_jobs(), .st_cmds(), .phase());
    // ------------------------------------------------------------------ program, templates, host stream
    localparam integer NT = 128, NCFG = 24, NR = 48, NJOB = 6, SPAC = 108, NHS = 600, NMAX = 6000;
    reg [185:0] T [0:NT-1];
    integer r_eng [0:NR+1], r_arg [0:NR+1], r_iss [0:NR+1], r_done [0:NR+1], nrow, endage;
    reg [514:0] HS [0:NHS-1]; integer nhs;
    function [185:0] rnd186(input integer dummy);
        integer q; begin for (q = 0; q < 186; q = q + 32) rnd186[q +: 32] = $random(seed); end
    endfunction
    function [514:0] csr(input [7:0] idx, input [511:0] d);
        begin csr = {2'd0, d, 1'b1}; csr[8:1] = idx; end
    endfunction
    task push(input [514:0] w); begin HS[nhs] = w; nhs = nhs + 1; end endtask
    task push_pw(input [6:0] a, input [27:0] d);
        reg [511:0] x; begin x = 512'd0; x[7:0] = 8'h10; x[102:96] = a; x[59:32] = d; push({2'd0, x, 1'b1}); end
    endtask
    task push_raw(input [7:0] tag, input [31:0] base);
        reg [511:0] x; begin
            x = 512'd0; x[3:0] = 4'd0; x[7] = 1'b1; x[15:8] = tag; x[47:16] = base; x[167:144] = 24'd4; x[255:240] = 16'd2;
            push({2'd1, x, 1'b1});
            for (k = 0; k < 2; k = k + 1) begin x = {rnd186(0), rnd186(0), rnd186(0)}; push({2'd2, x, 1'b1}); end
        end
    endtask
    integer used [0:1023];
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1; seed0 = seed;
        if (!$value$plusargs("collide=%d", collide)) collide = 0;
        if (!$value$plusargs("stdrop=%d", stdrop)) stdrop = 0;
        errs = 0; nhs = 0;
        for (i = 0; i < NT; i = i + 1) T[i] = rnd186(0);
        // calendar rows: engine e at ages = res(e) mod 8, unique; END after every done
        for (i = 0; i < 1024; i = i + 1) used[i] = 0;
        nrow = 0;
        for (i = 0; i < NR; i = i + 1) begin
            e = (i % 4 == 3) ? 4 : (i % 4);
            k = (i / 4) * 8 + ((e == 4) ? 2 : (e == 2) ? 3 : e);
            r_eng[nrow] = e; r_iss[nrow] = k;
            r_done[nrow] = k + ((e == 4) ? DV_S : DV_V);
            if (e == 4) r_arg[nrow] = $random(seed) & 24'hffffff;
            else if (e == 2) r_arg[nrow] = ($random(seed) & 127) | (($random(seed) & 1) << 7);
            else r_arg[nrow] = ($random(seed) & 127) | (($unsigned($random(seed)) % 3) << 7);
            nrow = nrow + 1;
        end
        endage = 0; for (i = 0; i < nrow; i = i + 1) if (r_done[i] > endage) endage = r_done[i];
        endage = endage + 4;
        r_eng[nrow] = 14; r_arg[nrow] = 0; r_iss[nrow] = endage - 20; r_done[nrow] = 0; nrow = nrow + 1;    // KIT
        r_eng[nrow] = 15; r_arg[nrow] = 0; r_iss[nrow] = endage;      r_done[nrow] = 0; nrow = nrow + 1;    // END
        if (2 * SPAC <= endage + 4) $fatal(1, "spacing too small for two live contexts");
        // host stream: length, BEGIN, rows (3 pages), SEAL, templates, RAW writes interleaved
        begin : hs
            reg [511:0] x; reg [75:0] pk; reg [27:0] hdr;
            x = 512'd0; x[7:0] = 8'h11; x[39:32] = nrow; push({2'd0, x, 1'b1});
            hdr = (nrow << 9) | (0 << 7) | 0;
            push_pw(7'd0, (28'd3 << 26) | hdr);
            push_raw(8'h31, 32'h0000_1000);
            for (i = 0; i < nrow; i = i + 1) begin
                pk = {24'(r_done[i]), 24'(r_iss[i]), 4'(r_eng[i]), 24'(r_arg[i])};
                for (k = 0; k < 3; k = k + 1) push_pw(7'(i), {2'(k), pk[26 * k +: 26]});
                if (i % 16 == 5) push_raw(8'h40 + i, 32'h0000_2000 + i * 64);
            end
            push_pw(7'd0, (28'd3 << 26) | (28'd1 << 25) | hdr);
            for (i = 0; i < NT; i = i + 1) begin x = 512'd0; x[7:0] = 8'h13; x[14:8] = i; x[16 +: 186] = T[i]; push({2'd0, x, 1'b1}); end
            for (i = 0; i < NCFG; i = i + 1) begin                     // gunit config rows (0x14), a[9] = 0
                x = 512'd0; x[7:0] = 8'h14; x[17:8] = {1'b0, 1'(i & 1), 2'b00, 6'(i)}; x[32 +: 256] = {rnd186(0), rnd186(0)}; push({2'd0, x, 1'b1});
            end
            push_raw(8'h77, 32'h0000_3000);
        end
    end
    // ------------------------------------------------------------------ expected-event tables (DUT edge index)
    reg [V-1:0] EN [0:NMAX+16], ES [0:NMAX+16]; reg RN [0:NMAX+16], RS [0:NMAX+16];   // reserved injection slots
    reg [32:0] EJ [0:NMAX+16]; reg [266:0] ECW [0:NMAX+16]; reg [53:0] EK [0:NMAX+16];
    reg [V-1:0] AN [0:NMAX+16], AS [0:NMAX+16];                                       // arrivals (edge they are driven for)
    reg [4:0] GDV [0:NMAX+16]; reg [39:0] GDT [0:NMAX+16];                            // golden completions
    integer SJD [0:NMAX+16], SJE [0:NMAX+16]; reg [8:0] SHC [0:NMAX+16], SHE [0:NMAX+16], GHC [0:NMAX+16];
    initial begin
        for (i = 0; i <= NMAX + 16; i = i + 1) begin
            RN[i] = 0; RS[i] = 0; ECW[i] = 0; EN[i] = 0; ES[i] = 0; EJ[i] = 0; EK[i] = 0; AN[i] = 0; AS[i] = 0; GDV[i] = 0; GDT[i] = 0;
            SJD[i] = 0; SHC[i] = 0; SHE[i] = 0; SJE[i] = 0; GHC[i] = 0;
        end
    end
    function [V-1:0] beat(input [185:0] t, input [83:0] c);
        reg [185:0] p; begin
            p = t;
            if (c[15:14] == 2'd1) p[134 +: 52] = c[82:31];
            else if (c[15:14] == 2'd2) p[165 +: 21] = c[72:52];
            beat = {V{1'b0}}; beat[0] = 1'b1; beat[12:9] = 4'd4; beat[21 +: 186] = p;
        end
    endfunction
    // ------------------------------------------------------------------ the run
    integer hsp, jobs, gjobs, launch0, ncmd_n, ncmd_s, ncmd_j, nkit, nhw, ncomp, narr, nfrag_s, nfrag_n, coll_at;
    integer ncmd_g, ncw, mism_cw, fr_n, fr_s, mism_n, mism_s, mism_j, mism_k, mism_hw, mism_tc, seen_jobs;
    reg [V-1:0] a; reg [83:0] c;
    reg [291:0] g_hw_p = 0; reg [64:0] g_tc_p = 0;  // the golden's hw / completion HSH (= 1) edge earlier
    initial begin
        cyc = 0; hsp = 0; jobs = 0; gjobs = 0; launch0 = -1; ncmd_n = 0; ncmd_s = 0; ncmd_j = 0; nkit = 0; nhw = 0; ncomp = 0;
        narr = 0; ncmd_g = 0; ncw = 0; mism_cw = 0; fr_n = 0; fr_s = 0; mism_n = 0; mism_s = 0; mism_j = 0; mism_k = 0; mism_hw = 0; mism_tc = 0;
        nfrag_s = 0; nfrag_n = 0; coll_at = -1; seen_jobs = 0;
        repeat (10) @(posedge ck); #0.2 rst_n = 1;
    end
    always @(posedge ck) if (rst_n) begin
        cyc = cyc + 1;
        #0.1;
        // ---- golden commands -> expected unit outputs, golden completions
        for (e = 0; e < 5; e = e + 1) if (g_cv[e]) begin
            c = g_cd[84 * e +: 84];
            if (e == 0) begin EN[cyc + D + LVO] = beat(T[c[13:7]], c); RN[cyc + D + LVO] = 1; ncmd_n = ncmd_n + 1;
                GDV[cyc + DV_V][0] = 1; GDT[cyc + DV_V][0 +: 8] = {c[83], c[6:0]}; end
            if (e == 1) begin ES[cyc + D + LVO] = beat(T[c[13:7]], c); RS[cyc + D + LVO] = 1; ncmd_s = ncmd_s + 1;
                GDV[cyc + DV_V][1] = 1; GDT[cyc + DV_V][8 +: 8] = {c[83], c[6:0]}; end
            if (e == 2) begin ECW[cyc + D + LCW] = {1'b1, 2'b10, 7'd0, c[14], 214'd0, T[c[13:7]][41:0]}; ncmd_g = ncmd_g + 1;
                GDV[cyc + DV_V][2] = 1; GDT[cyc + DV_V][16 +: 8] = {c[83], c[6:0]}; end
            if (e == 4) begin EJ[cyc + D + LJ] = {1'b1, c[30:7], c[83], c[6:0]}; ncmd_j = ncmd_j + 1;
                GDV[cyc + DV_S][4] = 1; GDT[cyc + DV_S][32 +: 8] = {c[83], c[6:0]}; end
        end
        if (g_kdone) begin EK[cyc + D + LKD] = {1'b1, g_ktok, 32'd0}; nkit = nkit + 1; end
        // ---- unit outputs (this edge)
        if (vo_n !== (RN[cyc] ? EN[cyc] : AN[cyc])) begin mism_n = mism_n + 1;
            if (mism_n < 4) $display("MISMATCH vo_n edge %0d res=%0d got %h", cyc, RN[cyc], vo_n[40:0]); end
        if (vo_s !== (RS[cyc] ? ES[cyc] : AS[cyc])) begin mism_s = mism_s + 1;
            if (mism_s < 4) $display("MISMATCH vo_s edge %0d res=%0d got %h", cyc, RS[cyc], vo_s[40:0]); end
        if ((cw_v || ECW[cyc][266]) && {cw_v, cw_a, cw_d} !== ECW[cyc]) begin mism_cw = mism_cw + 1;
            if (mism_cw < 4) $display("MISMATCH cw edge %0d got %0d/%h exp %0d/%h", cyc, cw_v, cw_a, ECW[cyc][266], ECW[cyc][265:256]); end
        if (cw_v) ncw = ncw + 1;
        if (s_j !== EJ[cyc]) begin mism_j = mism_j + 1; if (mism_j < 4) $display("MISMATCH s_j edge %0d got %h exp %h", cyc, s_j, EJ[cyc]); end
        if (t_kd !== EK[cyc]) begin mism_k = mism_k + 1; if (mism_k < 4) $display("MISMATCH t_kd edge %0d got %h exp %h", cyc, t_kd, EK[cyc]); end
        begin : hwchk
            reg [291:0] gw; reg mk, toe; reg [29:0] px;
            gw = (HSH != 0) ? g_hw_p : g_hw; mk = gw[288:257] == 32'hffffffff;
            px = (gw[286:257] >> 2) ^ (gw[286:257] >> 7) ^ (gw[286:257] >> 12); toe = px[4];
            if (s_hw_w[0] !== (gw[0] && (mk || !toe)) || (s_hw_w[0] && s_hw_w !== gw)) begin mism_hw = mism_hw + 1;
                if (mism_hw < 4) $display("MISMATCH s_hw_w edge %0d", cyc); end
            if (s_hw_e[0] !== (gw[0] && (mk || toe)) || (s_hw_e[0] && s_hw_e !== gw)) begin mism_hw = mism_hw + 1;
                if (mism_hw < 4) $display("MISMATCH s_hw_e edge %0d", cyc); end
            if (gw[0] && mk) nmk = nmk + 1;
        end
        if (t_host[64:0] !== (HSH != 0 ? g_tc_p : g_tc[64:0])) begin mism_tc = mism_tc + 1; if (mism_tc < 4) $display("MISMATCH t_host completion edge %0d", cyc); end
        if (s_hw_w[0]) begin SHC[cyc + 3] = 9'b000000011; nhw = nhw + 1; nhw_w = nhw_w + 1; end
        if (s_hw_e[0]) begin SHE[cyc + 3] = (s_hw_e[288:257] == 32'hffffffff) ? 9'b000000001 : 9'b000000011;
            if (!s_hw_w[0]) nhw = nhw + 1; nhw_e = nhw_e + 1; end
        if (g_hw[0]) GHC[cyc + 3] = 9'b000000011;
        g_hw_p = g_hw; g_tc_p = g_tc[64:0];
        if (t_host[64]) ncomp = ncomp + 1;
        if (s_j[32]) begin SJD[cyc + LS] = 1; SJE[cyc + LS - LSD] = 1; end
    end
    // ---- drive (negedge: inputs for edge cyc + 1)
    always @(negedge ck) if (rst_n) begin : drv
        integer t, r, kk;
        t = cyc + 1;
        // host stream: one word every 5th edge (the compiler's host slots; the golden's paced ckv program path takes 1 / 4)
        f_host <= 515'd0; g_host <= 515'd0;
        if (cyc > 30 && cyc % 5 == 0 && hsp < nhs) begin
            f_host <= HS[hsp];
            g_host <= (HS[hsp][2:1] == 2'd0 && (HS[hsp][8:1] == 8'h13 || HS[hsp][8:1] == 8'h14)) ? 515'd0 : HS[hsp];
            if (HS[hsp][2:1] == 2'd0 && HS[hsp][8:1] == 8'h14) ECW[t + LCF] = {1'b1, HS[hsp][18:9], HS[hsp][33 +: 256]};
            hsp = hsp + 1;
        end
        s_hc_w <= SHC[t]; s_hc_e <= SHE[t]; g_hc <= GHC[t]; s_jd_w <= {1'b0, SJD[t] != 0}; s_jd_e <= {1'b0, SJE[t] != 0};
        if (stdrop && jobs >= 2) st_rg_w <= 2'b00;
        g_dv <= GDV[t]; g_dt <= GDT[t];
        // kit starts: first launch once both issuers are sealed and the phase is right; then every SPAC edges
        f_ks <= 53'd0; g_jv <= 1'b0;
        if (launch0 < 0 && hsp == nhs && dut.u_l1.u_iss.sealed && gi.sealed && dut.u_l1.u_iss.phase_q == 2'd0 && cyc > 200)
            launch0 = cyc + D + 9;
        if (launch0 >= 0 && jobs < NJOB && t == launch0 + jobs * SPAC) begin
            f_ks <= {1'b1, 10'(37 + jobs), 21'(1000 + 77 * jobs), 21'(5000 + jobs)};
            jobs = jobs + 1;
        end
        if (launch0 >= 0 && gjobs < NJOB && t + D - 3 == launch0 + gjobs * SPAC) begin
            g_jv <= 1'b1; g_ju <= 10'(37 + gjobs); g_jt <= 21'(1000 + 77 * gjobs); g_jp <= 21'(5000 + gjobs);
            gjobs = gjobs + 1;
        end
        // rung arrivals for edge t: appear at the far pin at t + LR - 1 (edge index of observation = t + LR - 1)
        vi_s <= {V{1'b0}}; vi_n <= {V{1'b0}};
        if (t + LR < NMAX) begin
            // northbound
            if (fr_n > 0) begin a = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed),
                                      $random(seed), $random(seed), $random(seed)}; AN[t + LR - 1] = a; vi_s <= a; fr_n = fr_n - 1; end
            else begin
                r = $random(seed) & 255;
                if (r < 110 && !RN[t + LR - 1]) begin
                    kk = $random(seed) & 7;
                    if ((kk == 1 || kk == 2) && !RN[t + LR] && !RN[t + LR + 1] && !RN[t + LR + 2]) begin fr_n = 3; nfrag_n = nfrag_n + 1; end
                    else if (kk == 1 || kk == 2) kk = 3;
                    a = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed),
                         $random(seed), $random(seed), $random(seed)}; a[0] = 1'b1; a[3:1] = kk;
                    AN[t + LR - 1] = a; vi_s <= a; narr = narr + 1;
                end
                if (collide && jobs == NJOB && coll_at < 0 && RN[t + LR - 1]) begin
                    a = {V{1'b0}}; a[0] = 1'b1; a[3:1] = 3'd5; vi_s <= a; coll_at = t;
                end
            end
            // southbound
            if (fr_s > 0) begin a = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed),
                                      $random(seed), $random(seed), $random(seed)}; AS[t + LR - 1] = a; vi_n <= a; fr_s = fr_s - 1; end
            else begin
                r = $random(seed) & 255;
                if (r < 110 && !RS[t + LR - 1]) begin
                    kk = $random(seed) & 7;
                    if ((kk == 1 || kk == 2) && !RS[t + LR] && !RS[t + LR + 1] && !RS[t + LR + 2]) begin fr_s = 3; nfrag_s = nfrag_s + 1; end
                    else if (kk == 1 || kk == 2) kk = 3;
                    a = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed),
                         $random(seed), $random(seed), $random(seed)}; a[0] = 1'b1; a[3:1] = kk;
                    AS[t + LR - 1] = a; vi_n <= a; narr = narr + 1;
                end
            end
        end
        // ---- end of run
        if (launch0 >= 0 && cyc == launch0 + (NJOB - 1) * SPAC + endage + 80) begin : fin
            integer bad;
            bad = (mism_n + mism_s + mism_j + mism_k + mism_hw + mism_tc + mism_cw + lp_mism) != 0;
            $display("SEQHOST LP_SHADOW LP_MUT=%0d compared=%0d mismatches=%0d", LP_MUT, lp_cmp, lp_mism);
            $display("SEQHOST seed=%0d MUT=%0d collide=%0d jobs=%0d rows=%0d cmds N/S/G/J=%0d/%0d/%0d/%0d cw=%0d kit=%0d hw=%0d host_cpl=%0d arrivals=%0d frag N/S=%0d/%0d mism n/s/j/k/hw/tc/cw=%0d/%0d/%0d/%0d/%0d/%0d/%0d unit_st=%b g_fault=%0d/%0d busy=%0d/%0d",
                seed0, MUT, collide, jobs, nrow, ncmd_n, ncmd_s, ncmd_g, ncmd_j, ncw, nkit, nhw, ncomp, narr, nfrag_n, nfrag_s,
                mism_n, mism_s, mism_j, mism_k, mism_hw, mism_tc, mism_cw, t_host[75:65], g_fault, g_code, dut.u_l1.busy, g_busy);
            $display("SEQHOST HALVES hw W/E=%0d/%0d markers=%0d", nhw_w, nhw_e, nmk);
            if (!collide && !stdrop && (nhw_w == 0 || nhw_e == 0)) bad = 1;      // both halves must be exercised
            if (stdrop) begin
                // the W half's live drop must reach the unit status (rg_drop = wf[2] = t_host[73]) and fault it
                if (!t_host[75] || !t_host[73]) bad = 1;
                $display("SEQHOST STDROP -> %s", bad ? "FAIL" : "PASS (fault raised)");
            end else if (collide) begin
                // the collision must fault the unit (wf[0] = V stop fault), and only that
                if (!t_host[75] || !t_host[71] || coll_at < 0) bad = 1;
                $display("SEQHOST COLLIDE at %0d -> %s", coll_at, bad ? "FAIL" : "PASS (fault raised)");
            end else begin
                if (t_host[75] || g_fault || ncmd_n != NJOB * (NR / 4) || ncmd_s != NJOB * (NR / 4) || ncmd_j != NJOB * (NR / 4) ||
                    ncmd_g != NJOB * (NR / 4) || ncw != NJOB * (NR / 4) + NCFG ||
                    nkit != NJOB || nhw == 0 || ncomp == 0 || dut.u_l1.busy || g_busy || gh.hf || gh.sf) bad = 1;
                $display("SEQHOST %s", bad ? "FAIL" : "PASS");
            end
            $finish;
        end
        if (cyc > NMAX) begin $display("SEQHOST FAIL timeout (launch0=%0d hsp=%0d/%0d sealed=%0d/%0d)", launch0, hsp, nhs,
            dut.u_l1.u_iss.sealed, gi.sealed); $finish; end
    end
endmodule
