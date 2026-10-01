`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W15: the V4.1 HBM comparator's TP-G collectives through one NVLink-class
// switch tier with deterministic in-switch reduction, end to end in RTL.
//
//   dies      2*P, each on its own clock; a package is two dies on UCIe-A
//             (ot_link_tx/rx, the package-internal step of the comparator's
//             fabric); the even die leads the package on the switch link.
//   switch    ot_link_nvls_switch (P ports), its own clock; every die link to
//             it is a full-KP4 RS(544,514) 112G rack-cable link (ot_link_tx ->
//             ot_link_chan_model -> ot_link_rx), both directions.
//   ALL-REDUCE  each package adds its two dies' partials (d_even + d_odd,
//             binary32 RNE), the switch adds the P package sums in its fixed
//             pairwise tree and multicasts; the leader forwards the result to
//             its partner.
//   ALL-GATHER  every die's records go through the leader and the switch to
//             every package; records carry {source die, index}.
// Every die checks every result record against the golden image as it lands;
// per op and die the bench prints issue and last-result cycles (die clock).
// ---------------------------------------------------------------------------
module tb_w15_v41_hbm_nvls #(
    parameter integer P = 48,
    parameter integer LANES = 16,
    parameter integer OPS = 8, MAXW = 8,
    parameter real    T_CORE = 0.96721, T_SW = 0.96721,
    parameter real    U_T = 1.0,
    parameter integer U_WIRE = 16,
    parameter real    X_T = 0.71429,
    parameter integer X_WIRE = 16, X_ENC = 6, X_DEC = 194,
    parameter integer SW_PIPE = 238,
    parameter integer T0 = 64, GAP = 2
);
    localparam integer N = 2 * P, FW = 32 * LANES, TAGW = 32, PW = FW + 2 + TAGW, TSW = 16, NL = 2;
    localparam integer BW = TSW + 1 + 1 + PW, FRW = NL * (BW + 1) + 32;   // UCIe and board: FRAME_CYCLES 1
    integer seed, seed0, DET, U_DREL, X_DREL;
    real U_DLY, U_JS, U_WAN, X_DLY, X_JS, X_WAN;
    string vecdir;
    reg [31:0] desc [0:OPS-1];
    reg [FW-1:0] part [0:OPS*N*MAXW-1];
    reg [FW-1:0] expw [0:OPS*MAXW-1];
    reg ready = 0, go_clk = 0;
    real ph [0:2*N+1];
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("VEC=%s", vecdir)) $fatal(1, "missing VEC");
        if (!$value$plusargs("DET=%d", DET)) DET = 1;
        if (!$value$plusargs("U_DREL=%d", U_DREL)) U_DREL = 60;
        if (!$value$plusargs("X_DREL=%d", X_DREL)) X_DREL = 260;
        if (!$value$plusargs("U_DLY=%f", U_DLY)) U_DLY = 2.0;
        if (!$value$plusargs("U_JS=%f", U_JS)) U_JS = 0.5;
        if (!$value$plusargs("U_WAN=%f", U_WAN)) U_WAN = 0.05;
        if (!$value$plusargs("X_DLY=%f", X_DLY)) X_DLY = 57.41;
        if (!$value$plusargs("X_JS=%f", X_JS)) X_JS = 3.0;
        if (!$value$plusargs("X_WAN=%f", X_WAN)) X_WAN = 0.2;
        for (integer i = 0; i < 2*N+2; i = i + 1) ph[i] = (($unsigned($random(seed)) % 1000) / 1000.0);
        $readmemh({vecdir, "/desc.hex"}, desc);
        $readmemh({vecdir, "/part.hex"}, part);
        $readmemh({vecdir, "/expected.hex"}, expw);
        ready = 1;
        $display("W15HCFG seed=%0d P=%0d det=%0d u_drel=%0d x_drel=%0d sw_pipe=%0d", seed0, P, DET, U_DREL, X_DREL, SW_PIPE);
        go_clk = 1;
    end
    // ---- clocks: dies, their UCIe / SerDes link clocks, the switch and its SerDes link clock -----------------
    reg [N-1:0] clk = 0, lu = 0, lx = 0, rst_n = 0, rst_u = 0, rst_x = 0;
    reg sclk = 0, slx = 0, srst = 0, srst_x = 0;
    reg [TSW-1:0] now [0:N-1];
    reg [TSW-1:0] snow = 0;
    genvar d, p;
    generate for (d = 0; d < N; d = d + 1) begin : g_clk
        initial begin wait(go_clk); #(T_CORE * ph[2*d]);   forever #(T_CORE/2) clk[d] = ~clk[d]; end
        initial begin wait(go_clk); #(U_T * ph[2*d+1]);    forever #(U_T/2) lu[d] = ~lu[d]; end
        initial begin wait(go_clk); #(X_T * ph[2*d+1]);    forever #(X_T/2) lx[d] = ~lx[d]; end
        always @(posedge clk[d]) rst_n[d] <= ($realtime > 40.0) && ready;
        always @(posedge lu[d]) rst_u[d] <= ($realtime > 40.0);
        always @(posedge lx[d]) rst_x[d] <= ($realtime > 40.0);
        initial now[d] = 0;
        always @(posedge clk[d]) if (rst_n[d]) now[d] <= now[d] + 1'b1;
    end endgenerate
    initial begin wait(go_clk); #(T_SW * ph[2*N]);   forever #(T_SW/2) sclk = ~sclk; end
    initial begin wait(go_clk); #(X_T * ph[2*N+1]);  forever #(X_T/2) slx = ~slx; end
    always @(posedge sclk) srst <= ($realtime > 40.0) && ready;
    always @(posedge slx) srst_x <= ($realtime > 40.0);
    always @(posedge sclk) if (srst) snow <= snow + 1'b1;

    // ---- switch ------------------------------------------------------------------------------------------
    wire [P-1:0] sw_iv;
    wire [P*PW-1:0] sw_ir;
    wire sw_ov, sw_fault;
    wire [PW-1:0] sw_or;
    ot_link_nvls_switch #(.P(P), .LANES(LANES), .SW_PIPE(SW_PIPE)) u_sw (
        .clk(sclk), .rst_n(srst), .in_valid(sw_iv), .in_rec(sw_ir), .out_valid(sw_ov), .out_rec(sw_or),
        .fault(sw_fault));

    // ---- per-die sequencer / producer / checker, per-package leader logic and links ------------------------
    wire [N-1:0] lf;
    reg rep = 0, dump = 0;
    reg  [N-1:0] fin = 0;
    generate for (p = 0; p < P; p = p + 1) begin : g_pkg
        localparam integer D0 = 2 * p, D1 = 2 * p + 1;
        // producers: each die streams its op's words, one a cycle, from issue
        wire [1:0] pv;
        wire [2*PW-1:0] pr;
        // results delivered to each die
        wire [1:0] rv;
        wire [2*PW-1:0] rr;
        for (genvar j = 0; j < 2; j = j + 1) begin : g_die
            localparam integer DD = 2 * p + j;
            integer op = -1, k = 0, st = 0, waitc = 0, got = 0, n_ = 0, want = 0;
            integer issue_c [0:OPS-1], last_c [0:OPS-1], ftx [0:OPS-1], ltx [0:OPS-1], wr [0:OPS-1];
            // first_vm is not tracked separately: first_vm = last_vm = the last result (issue -> last result is fitted)
            always @(posedge dump)
                for (integer o = 0; o < OPS; o = o + 1)
                    $display("OP op=%0d die=%0d mode=%0d words=%0d issue=%0d first_tx=%0d last_tx=%0d first_vm=%0d last_vm=%0d done=%0d writes=%0d expect=%0d",
                             o, DD, desc[o][31], desc[o][14:0], issue_c[o], ftx[o], ltx[o], last_c[o], last_c[o],
                             last_c[o] + 1, wr[o], desc[o][31] ? N * integer'(desc[o][14:0]) : integer'(desc[o][14:0]));
            wire md = desc[op < 0 ? 0 : op][31];
            assign pv[j] = (st == 2) && (k < n_);
            assign pr[j*PW +: PW] = {DD[7:0], k[15:0], op[7:0], md, k == n_ - 1, part[(op*N + DD)*MAXW + k]};
            always @(posedge clk[DD]) if (rst_n[DD]) begin
                case (st)
                    0: if (now[DD] == T0 - 1) st <= 1;
                    1: begin : issue
                        integer o;
                        o = op + 1;
                        op <= o; k <= 0; got <= 0;
                        n_ <= integer'(desc[o][14:0]);
                        want <= desc[o][31] ? N * integer'(desc[o][14:0]) : integer'(desc[o][14:0]);
                        issue_c[o] = now[DD] + 1; ftx[o] = -1; ltx[o] = -1; last_c[o] = -1; wr[o] = 0;
                        st <= 2;
                    end
                    2: begin
                        if (k < n_) begin
                            if (ftx[op] < 0) ftx[op] = now[DD];
                            if (k == n_ - 1) ltx[op] = now[DD];
                            k <= k + 1;
                        end
                        if (got == want) begin
                            last_c[op] = now[DD] - 1;
                            if (op == OPS - 1) begin fin[DD] <= 1'b1; st <= 4; end
                            else begin waitc <= GAP; st <= 3; end
                        end
                    end
                    3: if (waitc <= 1) st <= 1; else waitc <= waitc - 1;
                    default: ;
                endcase
                if (rv[j] && op >= 0) begin : chk
                    reg [PW-1:0] x;
                    integer src, idx;
                    x = rr[j*PW +: PW];
                    src = integer'(x[PW-1 -: 8]); idx = integer'(x[PW-9 -: 16]);
                    if (md) begin
                        if (src >= N || idx >= n_ || x[FW-1:0] !== part[(op*N + src)*MAXW + idx])
                            $fatal(1, "gather mismatch op=%0d die=%0d src=%0d idx=%0d", op, DD, src, idx);
                    end else if (src != 255 || idx >= n_ || x[FW-1:0] !== expw[op*MAXW + idx])
                        $fatal(1, "reduce mismatch op=%0d die=%0d idx=%0d", op, DD, idx);
                    got <= got + 1;
                    wr[op] = wr[op] + 1;
                end
            end
        end

        // ---- in-package links: D1 -> D0 (partner records) and D0 -> D1 (results) --------------------------
        wire u10_v, u01_v, fu0, fu1, fu2, fu3, fu4, fu5, fu6, fu7;
        wire [PW-1:0] u10_r, u01_r;
        wire [FRW-1:0] uf10, urf10, uf01, urf01;
        wire uv10, urv10, uv01, urv01, urc10, urc01;
        // leader's forward of every downlink record to its partner
        wire dl_v;
        wire [PW-1:0] dl_r;
        ot_link_tx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(U_WIRE), .AW(5), .NL(NL), .FRAME_CYCLES(1), .HUBFC(0)) u_t10 (
            .clk(clk[D1]), .rst_n(rst_n[D1]), .now(now[D1]), .vc_valid(pv[1]), .vc_ready(), .vc_rec(pr[PW +: PW]),
            .cr_pulse(1'b0), .lclk(lu[D1]), .lrst_n(rst_u[D1]), .f_valid(uv10), .f_data(uf10), .fault(fu0),
            .stat_bundles(), .stat_gated_stall());
        ot_link_chan_model #(.FRW(FRW), .T_NS(U_T), .JDYN_FRAC(0.8)) u_c10 (.DLY_NS(U_DLY), .JSTATIC_NS(U_JS),
            .WANDER_NS(U_WAN), .clk_tx(lu[D1]), .f_valid(uv10), .f_data(uf10), .seed(seed0 * 977 + 4 * p),
            .flip_at(-1), .rclk(urc10), .rf_valid(urv10), .rf_data(urf10));
        reg rr10 = 0; always @(posedge urc10) rr10 <= ($realtime > 40.0);
        ot_link_rx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(U_WIRE), .AW(6), .NL(NL), .FRAME_CYCLES(1)) u_r10 (
            .rclk(urc10), .rrst_n(rr10), .f_valid(urv10), .f_data(urf10), .clk(clk[D0]), .rst_n(rst_n[D0]),
            .now(now[D0]), .det(DET[0]), .drel(TSW'(U_DREL)), .vc_valid(u10_v), .vc_rec(u10_r), .cr_pulse(),
            .fault_crc(fu1), .fault_late(fu2), .fault_ovf(fu3), .stat_min_age(), .stat_max_age(), .stat_max_wait(),
            .stat_bundles());
        ot_link_tx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(U_WIRE), .AW(5), .NL(NL), .FRAME_CYCLES(1), .HUBFC(0)) u_t01 (
            .clk(clk[D0]), .rst_n(rst_n[D0]), .now(now[D0]), .vc_valid(dl_v), .vc_ready(), .vc_rec(dl_r),
            .cr_pulse(1'b0), .lclk(lu[D0]), .lrst_n(rst_u[D0]), .f_valid(uv01), .f_data(uf01), .fault(fu4),
            .stat_bundles(), .stat_gated_stall());
        ot_link_chan_model #(.FRW(FRW), .T_NS(U_T), .JDYN_FRAC(0.8)) u_c01 (.DLY_NS(U_DLY), .JSTATIC_NS(U_JS),
            .WANDER_NS(U_WAN), .clk_tx(lu[D0]), .f_valid(uv01), .f_data(uf01), .seed(seed0 * 977 + 4 * p + 1),
            .flip_at(-1), .rclk(urc01), .rf_valid(urv01), .rf_data(urf01));
        reg rr01 = 0; always @(posedge urc01) rr01 <= ($realtime > 40.0);
        wire [TSW-1:0] ua10min, ua10max, ua01min, ua01max;
        ot_link_rx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(U_WIRE), .AW(6), .NL(NL), .FRAME_CYCLES(1)) u_r01 (
            .rclk(urc01), .rrst_n(rr01), .f_valid(urv01), .f_data(urf01), .clk(clk[D1]), .rst_n(rst_n[D1]),
            .now(now[D1]), .det(DET[0]), .drel(TSW'(U_DREL)), .vc_valid(u01_v), .vc_rec(u01_r), .cr_pulse(),
            .fault_crc(fu5), .fault_late(fu6), .fault_ovf(fu7), .stat_min_age(ua01min), .stat_max_age(ua01max),
            .stat_max_wait(), .stat_bundles());
        assign rv[1] = u01_v;
        assign rr[PW +: PW] = u01_r;

        // ---- leader: own and partner records -> uplink (AR: d_even + d_odd) ----------------------------------
        reg  [PW-1:0] qo [0:63], qp [0:63];
        reg  [6:0] ho = 0, to_ = 0, hp = 0, tp = 0;
        wire no = ho != to_, np = hp != tp;
        wire [PW-1:0] hdo = qo[ho[5:0]], hdp = qp[hp[5:0]];
        wire red = no && np && !hdo[FW+1];                     // both heads present, all-reduce
        wire gat_o = no && hdo[FW+1];
        wire gat_p = np && hdp[FW+1] && !gat_o;
        always @(posedge clk[D0]) begin
            if (pv[0]) begin qo[to_[5:0]] <= pr[0 +: PW]; to_ <= to_ + 1'b1; end
            if (u10_v) begin qp[tp[5:0]] <= u10_r; tp <= tp + 1'b1; end
            if (red || gat_o) ho <= ho + 1'b1;
            if (red || gat_p) hp <= hp + 1'b1;
        end
        wire [LANES-1:0] av;
        wire [FW-1:0] asum;
        wire [2*LANES-1:0] aerr;
        for (genvar ln = 0; ln < LANES; ln = ln + 1) begin : g_add
            ot_hdc_fp32_add_fast u_a (.clk(clk[D0]), .rst_n(rst_n[D0]), .valid_in(red),
                .a(hdo[32*ln +: 32]), .b(hdp[32*ln +: 32]), .y(asum[32*ln +: 32]), .err(aerr[2*ln +: 2]),
                .valid_out(av[ln]));
        end
        reg [3*(PW-FW)-1:0] atag;                              // {tag, mode, last} aligned with the adder
        always @(posedge clk[D0]) atag <= {atag[2*(PW-FW)-1:0], hdo[PW-1:FW]};
        reg gv = 0; reg [PW-1:0] gr;
        always @(posedge clk[D0]) begin gv <= gat_o || gat_p; gr <= gat_o ? hdo : hdp; end
        wire up_v = av[0] || gv;
        wire [PW-1:0] up_r = av[0] ? {atag[3*(PW-FW)-1 -: (PW-FW)], asum} : gr;
        // uplink to the switch, downlink from it
        wire xv, xrv, xrc, sxv, sxrv, sxrc, fx0, fx1, fx2, fx3, fx4, fx5, fx6, fx7, dv;
        wire [FRW-1:0] xf, xrf, sxf, sxrf;
        wire [PW-1:0] dr;
        wire [TSW-1:0] xamin, xamax, sxamin, sxamax;
        ot_link_tx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(X_WIRE), .AW(5), .NL(NL), .FRAME_CYCLES(1),
                     .ENC_STAGES(X_ENC), .HUBFC(0)) u_tx_up (
            .clk(clk[D0]), .rst_n(rst_n[D0]), .now(now[D0]), .vc_valid(up_v), .vc_ready(), .vc_rec(up_r),
            .cr_pulse(1'b0), .lclk(lx[D0]), .lrst_n(rst_x[D0]), .f_valid(xv), .f_data(xf), .fault(fx0),
            .stat_bundles(), .stat_gated_stall());
        ot_link_chan_model #(.FRW(FRW), .T_NS(X_T), .JDYN_FRAC(0.8)) u_cup (.DLY_NS(X_DLY), .JSTATIC_NS(X_JS),
            .WANDER_NS(X_WAN), .clk_tx(lx[D0]), .f_valid(xv), .f_data(xf), .seed(seed0 * 977 + 4 * p + 2),
            .flip_at(-1), .rclk(xrc), .rf_valid(xrv), .rf_data(xrf));
        reg rup = 0; always @(posedge xrc) rup <= ($realtime > 40.0);
        ot_link_rx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(1), .AW(6), .NL(NL), .FRAME_CYCLES(1),
                     .DEC_STAGES(X_DEC)) u_rx_up (
            .rclk(xrc), .rrst_n(rup), .f_valid(xrv), .f_data(xrf), .clk(sclk), .rst_n(srst), .now(snow),
            .det(DET[0]), .drel(TSW'(X_DREL)), .vc_valid(sw_iv[p]), .vc_rec(sw_ir[p*PW +: PW]),
            .cr_pulse(), .fault_crc(fx1), .fault_late(fx2), .fault_ovf(fx3), .stat_min_age(xamin),
            .stat_max_age(xamax), .stat_max_wait(), .stat_bundles());
        ot_link_tx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(1), .AW(5), .NL(NL), .FRAME_CYCLES(1),
                     .ENC_STAGES(X_ENC), .HUBFC(0)) u_tx_dn (
            .clk(sclk), .rst_n(srst), .now(snow), .vc_valid(sw_ov), .vc_ready(), .vc_rec(sw_or), .cr_pulse(1'b0),
            .lclk(slx), .lrst_n(srst_x), .f_valid(sxv), .f_data(sxf), .fault(fx4), .stat_bundles(),
            .stat_gated_stall());
        ot_link_chan_model #(.FRW(FRW), .T_NS(X_T), .JDYN_FRAC(0.8)) u_cdn (.DLY_NS(X_DLY), .JSTATIC_NS(X_JS),
            .WANDER_NS(X_WAN), .clk_tx(slx), .f_valid(sxv), .f_data(sxf), .seed(seed0 * 977 + 4 * p + 3),
            .flip_at(-1), .rclk(sxrc), .rf_valid(sxrv), .rf_data(sxrf));
        reg rdn = 0; always @(posedge sxrc) rdn <= ($realtime > 40.0);
        ot_link_rx #(.NVC(1), .PW(PW), .CW(1), .TSW(TSW), .WIRE(X_WIRE), .AW(6), .NL(NL), .FRAME_CYCLES(1),
                     .DEC_STAGES(X_DEC)) u_rx_dn (
            .rclk(sxrc), .rrst_n(rdn), .f_valid(sxrv), .f_data(sxrf), .clk(clk[D0]), .rst_n(rst_n[D0]),
            .now(now[D0]), .det(DET[0]), .drel(TSW'(X_DREL)), .vc_valid(dv), .vc_rec(dr),
            .cr_pulse(), .fault_crc(fx5), .fault_late(fx6), .fault_ovf(fx7), .stat_min_age(sxamin),
            .stat_max_age(sxamax), .stat_max_wait(), .stat_bundles());
        assign rv[0] = dv;
        assign rr[0 +: PW] = dr;
        assign dl_v = dv;
        assign dl_r = dr;
        always @(posedge rep) if (fu2 | fx2 | fx6 | fu6)
            $display("W15LATE pkg=%0d u10=%0d up=%0d dn=%0d u01=%0d", p, fu2, fx2, fx6, fu6);
        assign lf[D0] = fu1 | fu2 | fu3 | fu4 | fx0 | fx5 | fx6 | fx7 | (|aerr & av[0]);
        assign lf[D1] = fu0 | fu5 | fu6 | fu7 | fx1 | fx2 | fx3 | fx4;
    end endgenerate

    generate for (p = 0; p < P; p = p + 1) begin : g_rep
        always @(posedge rep) begin
            $display("LINK src=%0d dst=%0d class=ucie age_min=%0d age_max=%0d wait_max=0 wire=%0d faults=0000", 2*p, 2*p+1,
                     g_pkg[p].ua01min, g_pkg[p].ua01max, U_WIRE);
            $display("LINK src=%0d dst=%0d class=board age_min=%0d age_max=%0d wait_max=0 wire=%0d faults=0000", 2*p, 999,
                     g_pkg[p].xamin, g_pkg[p].xamax, 1);
            $display("LINK src=%0d dst=%0d class=board age_min=%0d age_max=%0d wait_max=0 wire=%0d faults=0000", 999, 2*p,
                     g_pkg[p].sxamin, g_pkg[p].sxamax, X_WIRE);
        end
    end endgenerate
    initial begin : finish
        wait (&fin);
        repeat (20) @(posedge clk[0]);
        dump = 1; #0.01;
        rep = 1; #0.01;
        $display("W15FAULTS lf=%b sw=%0d", lf, sw_fault);
        $display("W15DONE seed=%0d det=%0d u_drel=%0d x_drel=%0d faults=%0d", seed0, DET, U_DREL, X_DREL,
                 (|lf) || sw_fault);
        $finish;
    end
    initial begin #(4000000.0); $display("W15TIMEOUT"); $finish; end
endmodule
