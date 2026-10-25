`timescale 1ns/1ps
// S81U-SVC 2026-10-17: exact bench of the score exchange of the 16 regional service slices (2 x 8 grid, sid = 2 col +
// row, abutted faces) against the GOLDEN q.k reduction of dsfd_svc_c: the balanced heap tree over the 16 TD = 32 tile
// partials in dim order, written exactly as the attention engine's lane tree (ot_hdc_v41x_attn_s g_node, S = 16:
// node i = node 2i+1 + node 2i+2, leaves at S-1+t; equal to the D = 128 quadrant trees + svch_comb (Q0+Q1)+(Q2+Q3)),
// with the same ot_hdc_v41x_qaddf (LAT FX, F12) and flags delay(fa | fb) | adder fault.
// Stimulus: NB beats, random FP32 partials (cancellation-heavy exponents, zeros, subnormals, inf, NaN), sparse flags,
// a random valid pattern shared by all slices; slice s's engine share injects beat b at cycle T0 + slot(b) +
// sx_role_off(s) (the compiled start offsets).  Checks: every root beat (16 heads x 4 rows, flags, tag) == golden in
// order; every slice's SM tap == golden head = its tile; beat counts; no fault.
// S81/SVCG (2026-10-25, DEC12 FOLD 2-BEAT CONTRACT) -DSX_F2B: every slice built with its 2-beat fold gather faces
// (FH = sx_fh(s), dsdv_svc_sx_f2b.svh) and the fold faces wired gh_o -> gh_i (abutted, as the other faces); leaves start
// at the f2b offsets sx_role_off_f2b; beats spaced >= 2 cycles (back-to-back at the allowed rate 1 word / 2 cycles,
// random extra gaps).  Extra checks: every fold-lane word leaves the receiving RX exactly (bit for bit) 3 cycles after
// its TX took it from station A (TX pin register = beat 0, beat 1, RX pin register; a full-width face takes 2: B, C),
// beat 1 in the cycle after a valid beat 0 and never otherwise, and every one of the 11 fold lanes carried words.  -DSX_F2B_RATE: beats at the old 1-cycle spacing (rate violation: must FAIL with a
// sticky fault); -DF2B_MUT=1: TX beat order swapped (must FAIL).
module tb_dsdv_svc_sx;
    localparam integer W = 2132, N = 64, NB = 600, FX = 5;
`ifdef DSDV_SX_MUT_ORDER
`include "dsdv_svc_sx_roles_mut_order.svh"
`else
`include "dsdv_svc_sx_roles.svh"
`endif
`ifdef SX_FMASK
`include "dsdv_svc_rs_faces.svh"
`endif
`ifndef MUT
`define MUT 0
`endif
`ifndef F2B_MUT
`define F2B_MUT 0
`endif
`include "dsdv_svc_sx_f2b.svh"
`ifdef SX_F2B
    localparam bit F2B = 1;
`else
    localparam bit F2B = 0;
`endif
    function automatic integer off_of(input integer sd);
        off_of = F2B ? sx_role_off_f2b(sd) : sx_role_off(sd);
    endfunction
    function automatic [7:0] fh_of(input integer sd);
        fh_of = F2B ? sx_fh(4'(sd)) : 8'h00;
    endfunction
    reg ck = 0, rst = 0;
    always #0.5 ck = ~ck;
    integer seed = 1;
    // ---------------- stimulus ----------------
    reg [W-1:0] beat [0:NB-1][0:15];
    integer slot_c [0:NB-1];
    function automatic [31:0] rfp(input integer sd);
        integer k; reg [31:0] v;
        k = $urandom % 100;
        v = $urandom;
        if (k < 3) rfp = {v[31], 31'd0};
        else if (k < 5) rfp = {v[31], 8'd0, v[22:0]};
        else if (k < 6) rfp = {v[31], 8'hff, 23'd0};
        else if (k < 7) rfp = {v[31], 8'hff, 1'b1, v[21:0]};
        else rfp = {v[31], 8'(120 + ($urandom % 14)), v[22:0]};
    endfunction
    initial begin
        integer b, t, i, c;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        void'($urandom(seed));
        c = 0;
        for (b = 0; b < NB; b++) begin
`ifdef SX_F2B_RATE
            c += (($urandom % 4) == 0) ? 1 + ($urandom % 3) : 1;
`else
            if (F2B) c += (($urandom % 4) == 0) ? 2 + ($urandom % 3) : 2;   // <= 1 gather word / 2 cycles
            else     c += (($urandom % 4) == 0) ? 1 + ($urandom % 3) : 1;
`endif
            slot_c[b] = c;
            for (t = 0; t < 16; t++) begin
                beat[b][t][W-1 -: 16] = 16'(b);
                beat[b][t][W-17 -: 4] = 4'(b * 7 + 3);
                for (i = 0; i < N; i++) begin
                    beat[b][t][N + 32*i +: 32] = rfp(0);
                    beat[b][t][i] = (($urandom % 50) == 0);
                end
            end
        end
    end
    // ---------------- 16 slices ----------------
    wire [3:0] gi_v [0:15], go_v [0:15], si_v [0:15], so_v [0:15];
    wire [4*W-1:0] gi_d [0:15], go_d [0:15]; wire [4*1076-1:0] si_d [0:15], so_d [0:15];
    wire [15:0] rt_v, t_v, flt; wire [W-1:0] rt_d [0:15];
    wire [19:0] t_tag [0:15]; wire [127:0] t_y [0:15]; wire [3:0] t_f [0:15];
    reg [15:0] l_v; reg [W-1:0] l_d [0:15];
    wire [4*1068-1:0] gh_i [0:15], gh_o [0:15];
    genvar s, f;
    function automatic integer nb(input integer sd, input integer fc);   // neighbour sid over face fc, -1 none
        integer r, c;
        r = sd % 2; c = sd / 2;
        case (fc)
            0: nb = (r == 0) ? 2*c + 1 : -1;
            1: nb = (c < 7) ? 2*(c+1) + r : -1;
            2: nb = (r == 1) ? 2*c : -1;
            default: nb = (c > 0) ? 2*(c-1) + r : -1;
        endcase
    endfunction
    generate for (s = 0; s < 16; s = s + 1) begin : g_s
        for (f = 0; f < 4; f = f + 1) begin : g_f
            localparam integer NBS = nb(s, f), OF = (f + 2) % 4;
            if (NBS >= 0) begin : g_c
                assign gi_v[s][f] = go_v[NBS][OF]; assign gi_d[s][W*f +: W] = go_d[NBS][W*OF +: W];
                assign si_v[s][f] = so_v[NBS][OF]; assign si_d[s][1076*f +: 1076] = so_d[NBS][1076*OF +: 1076];
                assign gh_i[s][1068*f +: 1068] = gh_o[NBS][1068*OF +: 1068];
            end else begin : g_e
                assign gh_i[s][1068*f +: 1068] = '0;
                assign gi_v[s][f] = 1'b0; assign gi_d[s][W*f +: W] = '0;
                assign si_v[s][f] = 1'b0; assign si_d[s][1076*f +: 1076] = '0;
            end
        end
`ifdef SX_FMASK
        // S81-P9-FACE: every slice built as its port variant's core (role-derived gather / scatter face masks,
        // dsdv_svc_rs_faces.svh rs_fmask = svc_rs_faces.py); the result must equal the all-faces build bit for bit
`ifdef SX_FMASK_MUT
        // negative control: the fold root (slice 9) loses one gather-in face its role reads -> the bench must FAIL
        localparam logic [39:0] FMS = rs_fmask(4'(s)) & ~((s == 9) ? (40'h1 << (24 + 1)) : 40'h0);
`else
        localparam logic [39:0] FMS = rs_fmask(4'(s));
`endif
        dsdv_svc_sx #(.MUT(`MUT), .FM_GI(FMS[27:24]), .FM_GO(FMS[31:28]), .FM_SI(FMS[35:32]), .FM_SO(FMS[39:36]),
                      .FH_GO(fh_of(s) & 8'h0f), .FH_GI(fh_of(s) >> 4), .F2B_MUT(`F2B_MUT)) u (
            .ck(ck), .rst(rst), .sid(4'(s)), .l_v(l_v[s]), .l_d(l_d[s]),
`else
        dsdv_svc_sx #(.MUT(`MUT), .FH_GO(fh_of(s) & 8'h0f), .FH_GI(fh_of(s) >> 4), .F2B_MUT(`F2B_MUT)) u (
            .ck(ck), .rst(rst), .sid(4'(s)), .l_v(l_v[s]), .l_d(l_d[s]),
`endif
            .gi_v(gi_v[s]), .gi_d(gi_d[s]), .go_v(go_v[s]), .go_d(go_d[s]),
            .si_v(si_v[s]), .si_d(si_d[s]), .so_v(so_v[s]), .so_d(so_d[s]),
            .rt_v(rt_v[s]), .rt_d(rt_d[s]), .t_v(t_v[s]), .t_tag(t_tag[s]), .t_y(t_y[s]), .t_f(t_f[s]), .gh_i(gh_i[s]), .gh_o(gh_o[s]), .fault(flt[s]));
    end endgenerate
    // S81/SVCG: fold-lane checks (F2B): the RX word in cycle t + 1 == the TX word in cycle t, bit for bit; beat order
    integer f2b_words = 0, f2b_err = 0, f2b_lanes = 0;
    generate for (s = 0; s < 16; s = s + 1) begin : g_fk
        for (f = 0; f < 4; f = f + 1) begin : g_ff
            localparam integer NBS = nb(s, f), OF = (f + 2) % 4;
            if (NBS >= 0 && fh_of(s) >> f & 1) begin : g_lane
                reg [2:0] pv = 3'b000; reg [W-1:0] pd [0:2]; integer nw = 0;
                wire tv = g_s[s].u.g_fh[f].g_tx.u_tx.v; wire [W-1:0] td = g_s[s].u.g_fh[f].g_tx.u_tx.d;
                wire rv = g_s[NBS].u.g_fh[OF].g_rx.u_rx.v; wire [W-1:0] rd = g_s[NBS].u.g_fh[OF].g_rx.u_rx.d;
                wire [1067:0] bo = gh_o[s][1068*f +: 1068];
                reg pb0v = 1'b0;
                always @(posedge ck) if (rst) begin
                    if (rv !== pv[2] || (pv[2] && rd !== pd[2])) begin
                        f2b_err = f2b_err + 1;
                        if (f2b_err <= 5) $display("F2B MISMATCH lane svc_%0d -> svc_%0d cyc %0d (rx v %b, tx v(t-3) %b)", s, NBS, cyc, rv, pv[2]);
                    end
                    if (pb0v !== bo[1067]) begin      // beat 1 exactly in the cycle after a valid beat 0, never otherwise
                        f2b_err = f2b_err + 1;
                        if (f2b_err <= 5) $display("F2B BEAT ORDER lane svc_%0d -> svc_%0d cyc %0d", s, NBS, cyc);
                    end
                    if (tv) nw = nw + 1;
                    if (tv) f2b_words = f2b_words + 1;
                    pv <= {pv[1:0], tv}; pd[0] <= td; pd[1] <= pd[0]; pd[2] <= pd[1]; pb0v <= !bo[1067] && bo[0];
                end
                initial begin wait (cyc > T0 + slot_c[NB-1] + 150); if (nw > 0) f2b_lanes = f2b_lanes + 1; end
            end
        end
    end endgenerate
    // tile of each slice (from the role ROM head field)
    function automatic integer tile_of(input integer sd);
        reg [43:0] rr; rr = sx_role(4'(sd)); tile_of = rr[42:39];
    endfunction

    // ---------------- golden: the engine lane tree, S = 16 ----------------
    reg gv; reg [W-1:0] gl [0:15];
    wire [(2*16-1)*32*N-1:0] tn; wire [(2*16-1)*N-1:0] tf;
    genvar gs, gk;
    generate
        for (gs = 0; gs < 16; gs = gs + 1) begin : g_leaf
            for (gk = 0; gk < N; gk = gk + 1) begin : g_k
                assign tn[((15+gs)*N + gk)*32 +: 32] = gl[gs][N + 32*gk +: 32];
                assign tf[(15+gs)*N + gk] = gl[gs][gk];
            end
        end
        for (gs = 0; gs < 15; gs = gs + 1) begin : g_node
            for (gk = 0; gk < N; gk = gk + 1) begin : g_k
                wire [31:0] y; wire fa;
                ot_hdc_v41x_qaddf #(.LAT(FX), .F12(1)) u_a (.clk(ck), .rst_n(rst), .v(1'b1), .a(tn[((2*gs+1)*N + gk)*32 +: 32]),
                    .b(tn[((2*gs+2)*N + gk)*32 +: 32]), .y(y), .fault(fa));
                wire fdq;
                ot_hdc_v41x_dly #(.W(1), .D(FX)) u_fd (.clk(ck), .d(tf[(2*gs+1)*N + gk] | tf[(2*gs+2)*N + gk]), .q(fdq));
                assign tn[(gs*N + gk)*32 +: 32] = y; assign tf[gs*N + gk] = fdq | fa;
            end
        end
    endgenerate
    wire gov; wire [19:0] gtag;
    ot_hdc_v41x_vdly #(.D(4*FX)) u_gv (.clk(ck), .rst_n(rst), .d(gv), .q(gov));
    ot_hdc_v41x_dly #(.W(20), .D(4*FX)) u_gt (.clk(ck), .d(gl[0][W-1 -: 20]), .q(gtag));
    reg [W-1:0] gold [0:NB-1]; integer ng = 0;
    always @(posedge ck) if (gov) begin
        gold[ng][W-1 -: 20] <= gtag;
        for (int k = 0; k < N; k++) begin gold[ng][N + 32*k +: 32] <= tn[k*32 +: 32]; gold[ng][k] <= tf[k]; end
        ng <= ng + 1;
    end

    // ---------------- drive ----------------
    function automatic integer skew(input integer sd);   // SX_MUT_SKEW: slice 5's engine share starts one cycle late
`ifdef SX_MUT_SKEW
        skew = (sd == 5) ? 1 : 0;
`else
        skew = 0;
`endif
    endfunction
    integer cyc = 0; localparam integer T0 = 20;
    always @(posedge ck) cyc <= cyc + 1;
    always @(negedge ck) begin
        integer b, s2;
        gv = 1'b0; l_v = '0;
        for (b = 0; b < NB; b++) begin
            if (cyc == T0 + slot_c[b]) begin gv = 1'b1; for (s2 = 0; s2 < 16; s2++) gl[s2] = beat[b][s2]; end
            for (s2 = 0; s2 < 16; s2++)
                if (cyc == T0 + slot_c[b] + off_of(s2) + skew(s2)) begin l_v[s2] = 1'b1; l_d[s2] = beat[b][tile_of(s2)]; end
        end
    end

    // ---------------- checks ----------------
    integer nr = 0, err = 0, nt [0:15], terr = 0;
    initial for (int i = 0; i < 16; i++) nt[i] = 0;
    always @(posedge ck) begin
        for (int s3 = 0; s3 < 16; s3++) begin
            if (rt_v[s3]) begin
                if (nr >= ng || rt_d[s3] !== gold[nr]) begin
                    err = err + 1;
                    if (err <= 5) $display("MISMATCH root beat %0d slice %0d", nr, s3);
                end
                nr = nr + 1;
            end
            if (t_v[s3]) begin
                integer hh, bb; reg [131:0] e;
                hh = tile_of(s3); bb = nt[s3];
                for (int r = 0; r < 4; r++) begin
                    e[32*r +: 32] = gold[bb][N + (r*16 + hh)*32 +: 32]; e[128 + r] = gold[bb][r*16 + hh];
                end
                if (bb >= ng || {t_f[s3], t_y[s3]} !== e || t_tag[s3] !== gold[bb][W-1 -: 20]) begin
                    terr = terr + 1;
                    if (terr <= 5) $display("MISMATCH tap slice %0d head %0d beat %0d", s3, hh, bb);
                end
                nt[s3] = nt[s3] + 1;
            end
        end
    end
    initial begin
        integer tot;
        rst = 0; repeat (5) @(posedge ck); rst = 1;
        wait (cyc > T0 + slot_c[NB-1] + 200);
        tot = 0; for (int i = 0; i < 16; i++) tot += nt[i];
        $display("SX root %0d/%0d beats (err %0d)  taps %0d/%0d (err %0d)  golden %0d  fault %b",
                 nr, NB, err, tot, 16*NB, terr, ng, flt);
        if (F2B) $display("SX F2B fold lanes %0d (words %0d, lane err %0d)  t_root %0d  last slot %0d", f2b_lanes, f2b_words,
                          f2b_err, SX_F2B_TROOT, slot_c[NB-1]);
        if (nr == NB && ng == NB && err == 0 && tot == 16*NB && terr == 0 && flt == 0 &&
            (!F2B || (f2b_err == 0 && f2b_lanes == 11))) $display("SX_BENCH PASS");
        else $display("SX_BENCH FAIL");
        $finish;
    end
endmodule
