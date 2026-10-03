`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_dsrom_hcoll: the DS-ROM stage collective group end to end on physical-link
// models (gate record results/rtl/dsrom_c5hc_collective_gate_20261003).
//
//   PD = 2  C5hc: 8 dies = 4 packages x 2 dies, TP-8 symmetric peers.  Each die
//           has a UCIe-A link to its package partner (W15 link layer, 4 VCs:
//           own + 3 relays) and a 112G light-FEC board link to its counterpart
//           in each of the 3 other packages (fc4 quad, the package's lanes
//           split into 2 counterpart planes).
//   PD = 1  C1 / PAR2: the 4 TP-4 owner dies, one per package, each with the
//           package's whole board link to the 3 other owners (fc4 quad).
//
// Every die runs on its own clock with its own UCIe and SerDes link clocks
// (random phases, per-seed static latency draws and wander in the channel
// models); links are ot_w15_link_tx -> ot_link_chan_model -> ot_w15_link_rx
// (CDC, framing, CRC, FEC encode/decode stages, wire stages, credit return in
// every bundle, deterministic release at DET = 1).  The engine is
// rtl/rom/collectives/ot_rom_hcoll_die.sv.
//
// Each die's DMA streams its partial from the VM at one 64 B word a cycle and
// commits results through the four-bank VM write port (GW = 4 words a cycle;
// +WSTALL = p stalls the write port p% of cycles: backpressure).  Ops are issued
// at fixed global times (SPACING > 0: op k at T0 + k * SPACING on every die's
// synchronised counter, the previous op having completed) or self-timed
// (SPACING = 0: GAP cycles after the die's own previous op).  Every committed
// word is checked against the golden image as it is written; per op and die the
// bench prints issue and first / last VM commit cycles.
// ---------------------------------------------------------------------------
module tb_dsrom_hcoll #(
    parameter integer PD = 2,
    parameter integer NPKG = 4,
    parameter integer DEPTH = 1024,
    parameter integer ADD_LAT = 7,
    parameter real    T_CORE = 0.8333,
    parameter real    U_T = 1.0,
    parameter integer U_WIRE = 34, U_ENC = 0, U_DEC = 0, U_FC = 1, U_NL = 2,
    parameter real    X_T = 1.349,
    parameter integer X_WIRE = 45, X_ENC = 3, X_DEC = 41, X_FC = 2, X_NL = 2,
    parameter integer X_PACE_NUM = 0, X_PACE_DEN = 1,
    parameter integer MAXOPS = 64, MAXW = 1024,
    parameter integer T0 = 64
);
    localparam integer N = NPKG * PD, NB = NPKG - 1, UV = NPKG, LANES = 16, FW = 512, PW = FW + 34, GW = 4;
    localparam integer TSW = 16;
    localparam integer U_CW = UV, X_CW = 1;
    localparam integer UBW = TSW + UV + U_CW + UV*PW, UFRW = U_FC*U_NL*(UBW+1) + 32;
    localparam integer X_CNTW = (X_PACE_NUM > 0) ? 3 : 1, XBW = TSW + 1 + X_CW * X_CNTW + PW,
                       XFRW = X_FC*X_NL*(XBW+1) + 32;

    integer seed, seed0, DET, U_DREL, X_DREL, OPS, SPACING, GAP, WSTALL;
    real U_DLY, U_JS, U_WAN, X_DLY, X_JS, X_WAN;
    string vecdir;
    reg [31:0] desc [0:MAXOPS-1];                 // {mode[31], n[14:0]}
    reg [FW-1:0] part [0:MAXOPS*N*MAXW-1];        // (op, die, word)
    reg [FW-1:0] expected [0:MAXOPS*N*MAXW-1];    // (op, result word in VM order)
    reg images_ready = 0, go_clk = 0;
    real ph [0:3*N-1];
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("VEC=%s", vecdir)) $fatal(1, "missing VEC");
        if (!$value$plusargs("OPS=%d", OPS)) $fatal(1, "missing OPS");
        if (!$value$plusargs("DET=%d", DET)) DET = 1;
        if (!$value$plusargs("SPACING=%d", SPACING)) SPACING = 0;
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 2;
        if (!$value$plusargs("WSTALL=%d", WSTALL)) WSTALL = 0;
        if (!$value$plusargs("U_DREL=%d", U_DREL)) U_DREL = 4000;
        if (!$value$plusargs("X_DREL=%d", X_DREL)) X_DREL = 4000;
        if (!$value$plusargs("U_DLY=%f", U_DLY)) U_DLY = 2.0;
        if (!$value$plusargs("U_JS=%f", U_JS)) U_JS = 0.5;
        if (!$value$plusargs("U_WAN=%f", U_WAN)) U_WAN = 0.05;
        if (!$value$plusargs("X_DLY=%f", X_DLY)) X_DLY = 57.70;
        if (!$value$plusargs("X_JS=%f", X_JS)) X_JS = 3.0;
        if (!$value$plusargs("X_WAN=%f", X_WAN)) X_WAN = 0.2;
        for (integer i = 0; i < 3*N; i = i + 1) ph[i] = (($unsigned($random(seed)) % 1000) / 1000.0);
        $readmemh({vecdir, "/desc.hex"}, desc);
        $readmemh({vecdir, "/part.hex"}, part);
        $readmemh({vecdir, "/expected.hex"}, expected);
        images_ready = 1;
        $display("HCCFG seed=%0d pd=%0d n=%0d depth=%0d det=%0d ops=%0d spacing=%0d gap=%0d wstall=%0d U(T=%0.4f wire=%0d dly=%0.3f js=%0.3f drel=%0d) X(T=%0.5f wire=%0d enc=%0d dec=%0d dly=%0.3f js=%0.3f drel=%0d)",
                 seed0, PD, N, DEPTH, DET, OPS, SPACING, GAP, WSTALL, U_T, U_WIRE, U_DLY, U_JS, U_DREL,
                 X_T, X_WIRE, X_ENC, X_DEC, X_DLY, X_JS, X_DREL);
        go_clk = 1;
    end

    // ---- clocks ------------------------------------------------------------------------------------------
    reg [N-1:0] clk = 0, lu = 0, lx = 0, rst_n = 0, rst_u = 0, rst_x = 0;
    reg [TSW-1:0] now [0:N-1];
    integer gnow [0:N-1];
    genvar s, j;
    generate for (s = 0; s < N; s = s + 1) begin : g_clk
        initial begin wait(go_clk); #(T_CORE * ph[3*s]);   forever #(T_CORE/2) clk[s] = ~clk[s]; end
        initial begin wait(go_clk); #(U_T * ph[3*s+1]);    forever #(U_T/2) lu[s] = ~lu[s]; end
        initial begin wait(go_clk); #(X_T * ph[3*s+2]);    forever #(X_T/2) lx[s] = ~lx[s]; end
        always @(posedge clk[s]) rst_n[s] <= ($realtime > 40.0) && images_ready;
        always @(posedge lu[s]) rst_u[s] <= ($realtime > 40.0);
        always @(posedge lx[s]) rst_x[s] <= ($realtime > 40.0);
        initial begin now[s] = 0; gnow[s] = 0; end
        always @(posedge clk[s]) if (rst_n[s]) begin now[s] <= now[s] + 1'b1; gnow[s] <= gnow[s] + 1; end
    end endgenerate

    // ---- nets ----------------------------------------------------------------------------------------------
    wire [N-1:0] ev, er, el, em, ov, ory, ol, og, oerr, efault;
    wire [N*FW-1:0] ed;
    wire [N*32-1:0] etag;
    wire [N*GW*FW-1:0] od;
    wire [N*3-1:0] ecode;
    wire [N*NB-1:0] btv, btr, bci, brv, bco;
    wire [N*PW-1:0] btrec;
    wire [N*NB*PW-1:0] brrec;
    wire [N*UV-1:0] utv, uci, urv, uco;
    wire [N*UV*PW-1:0] utrec, urrec;
    wire [N-1:0] utr;
    wire [N*(NB+1)-1:0] lfault;
    reg  [N-1:0] fin = 0;
    integer bad = 0;
    reg rep = 0;

    generate for (s = 0; s < N; s = s + 1) begin : g_die
        // ---- sequencer + DMA (read 1 word / cycle, commit GW words / cycle) ------------------------------
        integer op = -1, st = 0, waitc = 0, rk = 0, nw = 0, wr = 0, expw = 0;
        reg busy = 0, md = 0;
        integer issue_c [0:MAXOPS-1], fvm [0:MAXOPS-1], lvm [0:MAXOPS-1], wrc [0:MAXOPS-1];
        reg [31:0] rnd = 0;
        reg [FW-1:0] sk_d [0:1];
        reg sk_l [0:1];
        reg [1:0] sk_n = 0;
        reg sk_wp = 0, sk_rp = 0, rq = 0;
        integer rq_k = 0;
        wire epop = ev[s] && er[s];
        assign ev[s] = busy && sk_n != 0;
        assign ed[s*FW +: FW] = sk_d[sk_rp];
        assign el[s] = sk_l[sk_rp];
        assign em[s] = md;
        assign etag[s*32 +: 32] = op;
        assign ory[s] = (WSTALL == 0) || ((rnd % 100) >= WSTALL);
        always @(posedge clk[s]) if (rst_n[s]) begin : seqr
            integer k, a, r_, idx;
            rnd <= rnd ^ (rnd << 13) ^ (rnd >> 17) ^ (rnd << 5) ^ (32'h9e3779b9 * (s + 1)) ^ seed0;
            case (st)
                0: if (gnow[s] >= T0 - 2) st <= 1;
                1: begin
                    if (op + 1 >= OPS) begin fin[s] <= 1'b1; st <= 9; end
                    else if (SPACING == 0 || gnow[s] + 1 >= T0 + (op + 1) * SPACING) begin
                        op = op + 1;
                        md <= desc[op][31];
                        nw = integer'(desc[op][14:0]);
                        expw = desc[op][31] ? N * nw : nw;
                        busy <= 1'b1; rk = 0; wr = 0; rq <= 1'b0; sk_n <= 0; sk_wp <= 1'b0; sk_rp <= 1'b0;
                        issue_c[op] = gnow[s] + 1; fvm[op] = -1; lvm[op] = -1; wrc[op] = 0;
                        if (SPACING != 0 && gnow[s] + 1 > T0 + op * SPACING)
                            $display("HCLATE die=%0d op=%0d by=%0d", s, op, gnow[s] + 1 - (T0 + op * SPACING));
                        st <= 2;
                    end
                end
                2: begin
                    // read pipeline: a word read this cycle lands in the skid next cycle (VM read latency 1)
                    if (epop) sk_rp <= ~sk_rp;
                    if (rq) begin
                        sk_d[sk_wp] <= part[(op*N + s)*MAXW + rq_k];
                        sk_l[sk_wp] <= (rq_k == nw - 1);
                        sk_wp <= ~sk_wp;
                    end
                    sk_n <= sk_n + (rq ? 2'd1 : 2'd0) - (epop ? 2'd1 : 2'd0);
                    if (rk < nw && (sk_n + (rq ? 2'd1 : 2'd0) - (epop ? 2'd1 : 2'd0)) < 2) begin rq <= 1'b1; rq_k <= rk; rk = rk + 1; end
                    else rq <= 1'b0;
                    // commits
                    if (ov[s] && ory[s]) begin
                        if (oerr[s]) begin bad = bad + 1; $display("HCERR die=%0d op=%0d", s, op); end
                        if (og[s] != md) begin bad = bad + 1; $display("HCMODE die=%0d op=%0d", s, op); end
                        for (k = 0; k < (md ? GW : 1); k = k + 1) begin
                            if (md) begin idx = wr / N; r_ = wr % N; a = r_ * nw + idx; end
                            else a = wr;
                            if (od[(s*GW + k)*FW +: FW] !== expected[op*N*MAXW + a]) begin
                                bad = bad + 1;
                                if (bad < 8) $display("HCMISMATCH die=%0d op=%0d word=%0d", s, op, a);
                            end
                            wr = wr + 1;
                        end
                        if (ol[s] != (wr == expw)) begin
                            bad = bad + 1;
                            if (bad < 8) $display("HCLAST die=%0d op=%0d wr=%0d last=%0d", s, op, wr, ol[s]);
                        end
                        wrc[op] = wr;
                        if (fvm[op] < 0) fvm[op] = gnow[s];
                        lvm[op] = gnow[s];
                        if (wr >= expw) begin busy <= 1'b0; st <= (SPACING == 0) ? 3 : 1; waitc <= GAP; end
                    end
                end
                3: if (waitc <= 1) st <= 1; else waitc <= waitc - 1;
                default: ;
            endcase
        end

        // +TRACEOP=k: per-die event trace of op k (fires, FIFO pushes / pops, level-1 drain, results)
        integer traceop = -1;
        initial if (!$value$plusargs("TRACEOP=%d", traceop)) traceop = -1;
        always @(posedge clk[s]) if (rst_n[s] && op == traceop && busy)
            if (u_eng.fire || (|u_eng.push) || (|u_eng.pop) || u_eng.drain || u_eng.of_push || (ov[s] && ory[s]))
                $display("TR die=%0d t=%0d fire=%0d push=%b pop=%b drain=%0d ofpush=%0d commit=%0d bcr0=%0d ucr0=%0d brdy=%b",
                         s, gnow[s] - issue_c[op], u_eng.fire, u_eng.push, u_eng.pop, u_eng.drain, u_eng.of_push,
                         ov[s] && ory[s], u_eng.bcr[0], u_eng.ucr0, btr[s*NB +: NB]);
        ot_rom_hcoll_die #(.NPKG(NPKG), .PD(PD), .RANK(s), .LANES(LANES), .TAGW(32), .DEPTH(DEPTH),
                           .ADD_LAT(ADD_LAT), .GW(GW)) u_eng (
            .clk(clk[s]), .rst_n(rst_n[s]),
            .in_valid(ev[s]), .in_ready(er[s]), .in_data(ed[s*FW +: FW]), .in_last(el[s]), .in_mode(em[s]),
            .in_tag(etag[s*32 +: 32]),
            .b_tx_valid(btv[s*NB +: NB]), .b_tx_rec(btrec[s*PW +: PW]), .b_tx_ready(btr[s*NB +: NB]),
            .b_cr_in(bci[s*NB +: NB]), .b_rx_valid(brv[s*NB +: NB]), .b_rx_rec(brrec[s*NB*PW +: NB*PW]),
            .b_cr_out(bco[s*NB +: NB]),
            .u_tx_valid(utv[s*UV +: UV]), .u_tx_rec(utrec[s*UV*PW +: UV*PW]), .u_tx_ready(utr[s]),
            .u_cr_in(uci[s*UV +: UV]), .u_rx_valid(urv[s*UV +: UV]), .u_rx_rec(urrec[s*UV*PW +: UV*PW]),
            .u_cr_out(uco[s*UV +: UV]),
            .out_valid(ov[s]), .out_ready(ory[s]), .out_data(od[s*GW*FW +: GW*FW]), .out_last(ol[s]),
            .out_gather(og[s]), .out_err(oerr[s]), .fault(efault[s]), .fault_code(ecode[s*3 +: 3]));
    end endgenerate

    // ---- board links: die s, port j -> die t = rp_s(j) * PD + L_s, arriving on t's port jt -------------
    generate for (s = 0; s < N; s = s + 1) begin : g_bl
        for (j = 0; j < NB; j = j + 1) begin : g_p
            localparam integer PS = s / PD, LS = s % PD;
            localparam integer PT = j + ((j >= PS) ? 1 : 0);
            localparam integer T = PT * PD + LS;
            localparam integer JT = PS - ((PS > PT) ? 1 : 0);
            wire fv, rfv, rclk, f0, f1, f2, f3;
            wire [XFRW-1:0] fd, rfd;
            wire [TSW-1:0] amin, amax;
            wire [15:0] wmax;
            ot_w15_link_tx #(.NVC(1), .PW(PW), .CW(X_CW), .TSW(TSW), .WIRE(X_WIRE), .AW(6), .NL(X_NL),
                             .FRAME_CYCLES(X_FC), .ENC_STAGES(X_ENC), .PACE_NUM(X_PACE_NUM), .PACE_DEN(X_PACE_DEN)) u_tx (
                .clk(clk[s]), .rst_n(rst_n[s]), .now(now[s]), .vc_valid(btv[s*NB+j]), .vc_ready(btr[s*NB+j]),
                .vc_rec(btrec[s*PW +: PW]), .cr_pulse(bco[s*NB+j]), .lclk(lx[s]), .lrst_n(rst_x[s]),
                .f_valid(fv), .f_data(fd), .fault(f0), .stat_bundles(), .stat_gated_stall());
            ot_link_chan_model #(.FRW(XFRW), .T_NS(X_T), .JDYN_FRAC(0.8)) u_ch (
                .DLY_NS(X_DLY), .JSTATIC_NS(X_JS), .WANDER_NS(X_WAN), .clk_tx(lx[s]), .f_valid(fv), .f_data(fd),
                .seed(seed0 * 97 + s * 16 + j), .flip_at(-1), .rclk(rclk), .rf_valid(rfv), .rf_data(rfd));
            reg rr = 0;
            always @(posedge rclk) rr <= ($realtime > 40.0);
            ot_w15_link_rx #(.NVC(1), .PW(PW), .CW(X_CW), .TSW(TSW), .WIRE(X_WIRE), .AW(5), .NL(X_NL),
                             .FRAME_CYCLES(X_FC), .DEC_STAGES(X_DEC), .CNTW(X_CNTW)) u_rx (
                .rclk(rclk), .rrst_n(rr), .f_valid(rfv), .f_data(rfd), .clk(clk[T]), .rst_n(rst_n[T]),
                .now(now[T]), .det(DET[0]), .drel(TSW'(X_DREL)), .vc_valid(brv[T*NB+JT]),
                .vc_rec(brrec[(T*NB+JT)*PW +: PW]), .cr_pulse(bci[T*NB+JT]),
                .fault_crc(f1), .fault_late(f2), .fault_ovf(f3), .stat_min_age(amin), .stat_max_age(amax),
                .stat_max_wait(wmax), .stat_bundles());
            assign lfault[s*(NB+1)+j] = f0 | f1 | f2 | f3;
            always @(posedge rep) $display("LINK src=%0d dst=%0d class=board age_min=%0d age_max=%0d wait_max=%0d wire=%0d faults=%0d%0d%0d%0d",
                                           s, T, amin, amax, wmax, X_WIRE, f0, f1, f2, f3);
        end
    end endgenerate

    // ---- UCIe links: die s -> partner (PD = 2) -------------------------------------------------------------
    generate for (s = 0; s < N; s = s + 1) begin : g_ul
        if (PD == 2) begin : g_u
            localparam integer T = s ^ 1;
            wire fv, rfv, rclk, f0, f1, f2, f3;
            wire [UFRW-1:0] fd, rfd;
            wire [TSW-1:0] amin, amax;
            wire [15:0] wmax;
            wire [UV-1:0] rdy;
            ot_w15_link_tx #(.NVC(UV), .PW(PW), .CW(U_CW), .TSW(TSW), .WIRE(U_WIRE), .AW(6), .NL(U_NL),
                             .FRAME_CYCLES(U_FC), .ENC_STAGES(U_ENC), .GATED({{(UV-1){1'b0}}, 1'b1})) u_tx (
                .clk(clk[s]), .rst_n(rst_n[s]), .now(now[s]), .vc_valid(utv[s*UV +: UV]), .vc_ready(rdy),
                .vc_rec(utrec[s*UV*PW +: UV*PW]), .cr_pulse(uco[s*UV +: UV]), .lclk(lu[s]), .lrst_n(rst_u[s]),
                .f_valid(fv), .f_data(fd), .fault(f0), .stat_bundles(), .stat_gated_stall());
            assign utr[s] = rdy[0];
            ot_link_chan_model #(.FRW(UFRW), .T_NS(U_T), .JDYN_FRAC(0.8)) u_ch (
                .DLY_NS(U_DLY), .JSTATIC_NS(U_JS), .WANDER_NS(U_WAN), .clk_tx(lu[s]), .f_valid(fv), .f_data(fd),
                .seed(seed0 * 97 + s * 16 + 15), .flip_at(-1), .rclk(rclk), .rf_valid(rfv), .rf_data(rfd));
            reg rr = 0;
            always @(posedge rclk) rr <= ($realtime > 40.0);
            ot_w15_link_rx #(.NVC(UV), .PW(PW), .CW(U_CW), .TSW(TSW), .WIRE(U_WIRE), .AW(5), .NL(U_NL),
                             .FRAME_CYCLES(U_FC), .DEC_STAGES(U_DEC)) u_rx (
                .rclk(rclk), .rrst_n(rr), .f_valid(rfv), .f_data(rfd), .clk(clk[T]), .rst_n(rst_n[T]),
                .now(now[T]), .det(DET[0]), .drel(TSW'(U_DREL)), .vc_valid(urv[T*UV +: UV]),
                .vc_rec(urrec[T*UV*PW +: UV*PW]), .cr_pulse(uci[T*UV +: UV]),
                .fault_crc(f1), .fault_late(f2), .fault_ovf(f3), .stat_min_age(amin), .stat_max_age(amax),
                .stat_max_wait(wmax), .stat_bundles());
            assign lfault[s*(NB+1)+NB] = f0 | f1 | f2 | f3;
            always @(posedge rep) $display("LINK src=%0d dst=%0d class=ucie age_min=%0d age_max=%0d wait_max=%0d wire=%0d faults=%0d%0d%0d%0d",
                                           s, T, amin, amax, wmax, U_WIRE, f0, f1, f2, f3);
        end else begin : g_nu
            assign utr[s] = 1'b0;
            assign uci[s*UV +: UV] = {UV{1'b0}};
            assign urv[s*UV +: UV] = {UV{1'b0}};
            assign urrec[s*UV*PW +: UV*PW] = {UV*PW{1'b0}};
            assign lfault[s*(NB+1)+NB] = 1'b0;
        end
    end endgenerate

    // ---- finish ------------------------------------------------------------------------------------------------
    initial begin : finish
        integer o, d, fl;
        wait (&fin);
        repeat (40) @(posedge clk[0]);
        fl = (|efault) || (|lfault);
        if (fl) $display("HCFAULT engine=%b code=%b link=%b", efault, ecode, lfault);
        for (o = 0; o < OPS; o = o + 1)
            for (d = 0; d < N; d = d + 1)
                $display("OP op=%0d die=%0d mode=%0d words=%0d issue=%0d first_vm=%0d last_vm=%0d writes=%0d",
                         o, d, desc[o][31], desc[o][14:0], die_issue(d, o), die_fvm(d, o), die_lvm(d, o),
                         die_wr(d, o));
        rep = 1; #0.01;
        $display("HCDONE seed=%0d det=%0d u_drel=%0d x_drel=%0d faults=%0d mismatches=%0d", seed0, DET, U_DREL,
                 X_DREL, fl, bad);
        $finish;
    end
    initial begin #(5000000.0); $display("HCTIMEOUT fin=%b", fin); $finish; end

    function automatic integer die_issue(input integer d, input integer o);
        case (d) 0: die_issue = g_die[0].issue_c[o]; 1: die_issue = g_die[1].issue_c[o];
                 2: die_issue = g_die[2].issue_c[o]; 3: die_issue = g_die[3].issue_c[o];
`ifdef HC_N8
                 4: die_issue = g_die[4].issue_c[o]; 5: die_issue = g_die[5].issue_c[o];
                 6: die_issue = g_die[6].issue_c[o]; 7: die_issue = g_die[7].issue_c[o];
`endif
                 default: die_issue = -1; endcase
    endfunction
    function automatic integer die_fvm(input integer d, input integer o);
        case (d) 0: die_fvm = g_die[0].fvm[o]; 1: die_fvm = g_die[1].fvm[o];
                 2: die_fvm = g_die[2].fvm[o]; 3: die_fvm = g_die[3].fvm[o];
`ifdef HC_N8
                 4: die_fvm = g_die[4].fvm[o]; 5: die_fvm = g_die[5].fvm[o];
                 6: die_fvm = g_die[6].fvm[o]; 7: die_fvm = g_die[7].fvm[o];
`endif
                 default: die_fvm = -1; endcase
    endfunction
    function automatic integer die_lvm(input integer d, input integer o);
        case (d) 0: die_lvm = g_die[0].lvm[o]; 1: die_lvm = g_die[1].lvm[o];
                 2: die_lvm = g_die[2].lvm[o]; 3: die_lvm = g_die[3].lvm[o];
`ifdef HC_N8
                 4: die_lvm = g_die[4].lvm[o]; 5: die_lvm = g_die[5].lvm[o];
                 6: die_lvm = g_die[6].lvm[o]; 7: die_lvm = g_die[7].lvm[o];
`endif
                 default: die_lvm = -1; endcase
    endfunction
    function automatic integer die_wr(input integer d, input integer o);
        case (d) 0: die_wr = g_die[0].wrc[o]; 1: die_wr = g_die[1].wrc[o];
                 2: die_wr = g_die[2].wrc[o]; 3: die_wr = g_die[3].wrc[o];
`ifdef HC_N8
                 4: die_wr = g_die[4].wrc[o]; 5: die_wr = g_die[5].wrc[o];
                 6: die_wr = g_die[6].wrc[o]; 7: die_wr = g_die[7].wrc[o];
`endif
                 default: die_wr = -1; endcase
    endfunction
endmodule
