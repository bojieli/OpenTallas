`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM-NEXT FUSED N-ROW ENGINE (lane HBM-NEXT-UNITS-FUSED, 2026-10-19; next-release P = 4 die, not a release gate).
// FUSED.HC_PRE_NORM and FUSED.HC_POST as ONE record for N rows (HGI-1R ROWX: nm1, rgap, rs_A / rs_B / rs_C / rs_O).
//
// WHY A NEW STATIC ENGINE (not a port).  The d4g GEN2 die has no FUSED HC datapath: layer_coverage maps the two ops to
// the static HC masters, but those implement HC.HC_MIX only, and the die contract lists the HC_PRE_NORM / HC_POST
// producer as open gaps G-HC / G-HC-ENG (results/rtl/hbm_ds_layer_tput_1018/coverage.json: unit_bench null).  The P6
// RTL 8fe5d18bd (results/arch/hbm_mtp_1015/p6_rtl_2330, II 197) is the CREDITED lane-local engine ot_hgi_hc_eng_ll
// (wrq_cr / wwq_cr credits, job_rdy, rg / wg request-grant, per-lane chunk FIFOs) -- not a fork of any d4g static
// master and not legal on the static die.  This engine keeps the LL engine's ARITHMETIC exactly (same primitives in the
// same golden order: ot_dsrom_su_norm_mix, square + 7-add chunk chain, 32-chunk block tree + padded heap, ot_dsrom_divc,
// + eps, ot_dsrom_rsqrt, y = bf16(w * (x * r)); HC_POST ot_dsrom_su_hcpost_lane) and replaces its control by a
// static calendar: no credit, ready, grant, FIFO admission or wait; every VM access is issued on a counter-fixed edge,
// every response is checked against its fixed return edge, and every collision is a FAULT.
//
//   lane L (ot_hnx_fused_lane, x32): reads ONLY VM bank L, writes ONLY bank L (lane-local rule: A / B / O bank phase
//     equal, row strides multiples of 256 words).  Per record: JOB, SCRD (scalar sector reads, prologue), WGT beats
//     (per-row scalar set into one of 2 coefficient slots, row-tagged), GO; then a fixed calendar:
//       HC_PRE_NORM  gain phase: NM = D/256 sector reads (FP32 gain, read ONCE, held across all N rows);
//                    row p (start NM + p (4 NM + rgap)): 4 NM h reads (h0..h3 of each sector) -> mix with row p's pre
//                    -> x into x slot p mod KX -> squares -> chunk chain -> chunk sum up.  Row p's r (RSTD channel)
//                    scales x slot p: y = bf16(w * (x * r)) -> bank L at O + p rs_O.
//       HC_POST      row p (start p (5 NM + rgap)): per sector y, res0..3 (5 reads) -> 4-row sweep with row p's
//                    post / comb -> out[k] at O + p rs_O + k SD.
//   top (ot_hnx_fused_top): job decode + checks, the scalar prologue, relayed command bus (RL), relayed lane status,
//     the golden csum tree (lanes in lockstep: all 32 chunk sums of a block land on one edge, no FIFOs), the padded heap
//     made ROW-PIPELINED (a node is cleared when its parent consumes it; a new value on a full node is a collision
//     FAULT), / D, + eps, rsqrt, r broadcast (own RL relay), retire on the lanes' fin pulses (all on one edge).
//
// Row II (static): PRE 4 NM + rgap (read-bound, 80 at D 5,120), POST 5 NM + rgap (100).  x slots: row p + KX reuses
// slot p; the compiler's rgap must leave the slot free (checked: FAULT).  KX = 4 runs rgap 0 at D 5,120.
// Per-record fixed span: JOB + N NS scalar reads + scalar return + WGT beats + GO + gain (PRE) + tail.
// MUT (bench negatives, must FAIL): 1 every row uses coefficient slot 0 (no per-row scalar set; tag check off);
//   2 A row stride ignored (every row reads row 0's A); 3 every row uses x slot 0 (slot check off); 4 heap not cleared
//   on consume (collision check off); 5 gain not held (gain buffer cleared at row 1); 6 row r not per row (row 0's r for
//   every row).
// ---------------------------------------------------------------------------------------------------------------------

module ot_hnx_fused_rly #(parameter integer W = 8, parameter integer N = 4) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [W-1:0] d,
    output wire         vq,
    output wire [W-1:0] q
);
    generate if (N == 0) begin : g_0
        assign vq = v; assign q = d;
    end else begin : g_n
        wire [N:0] vd;
        ot_hdc_vline #(.D(N)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
        ot_hdc_delay #(.W(W), .D(N)) u_d (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
        assign vq = vd[N];
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// lane.  Down command {op 3, x 8, d 128}: op 0 JOB d = {rgap 8, rso 16, rsb 16, rsa 16, o_s 16, b_s 16, a_s 16, nm1 4,
// post 1} (sector units, strides two's complement mod 2^16); op 1 WGT x = {row 4, slot 1, beat 3}, d = scalar words
// 4 beat .. 4 beat + 3 of that row; op 2 SCRD d[15:0] = scalar sector, x = its index (the owning lane reads it);
// op 3 GO.  RSTD channel: r_v / r_d = the next row's r.  Up: {v, t (0 scalar, 1 chunk sum), x 10, d 256}; fin (pulse:
// the record's last output write), flt (sticky).
// VM bank lane: rq_v / rq_s registered; the response is EXPECTED at the lane pin flop RR + 1 edges later (fixed).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_fused_lane #(
    parameter integer D   = 5120,
    parameter integer KX  = 4,               // x-buffer row slots (power of two)
    parameter integer RR  = 10,              // VM read return: rr valid RR edges after the edge rq was sampled
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [4:0]    lid,
    output reg           rq_v,
    output reg  [15:0]   rq_s,
    input  wire          rr_v,
    input  wire [255:0]  rr_d,
    output reg           wq_v,
    output reg  [15:0]   wq_s,
    output reg  [255:0]  wq_d,
    input  wire          dn_v,
    input  wire [2:0]    dn_op,
    input  wire [7:0]    dn_x,
    input  wire [127:0]  dn_d,
    input  wire          r_v,
    input  wire [31:0]   r_d,
    output reg           up_v,
    output reg           up_t,
    output reg  [9:0]    up_x,
    output reg  [255:0]  up_d,
    output reg           fin,
    output reg           flt
);
    localparam integer SD = D / 8;           // sectors a vector
    localparam integer NM = D / 256;         // sectors a lane (a vector)
    localparam integer KB = (KX > 1) ? $clog2(KX) : 1;
    localparam integer LM = 5, LA = 6, LMS = 6, ML = 7, AL = 6;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction
    wire [0:0] rlr; wire rl = rlr[0];
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rlr));
    // ---- pin flops
    reg dv_q, rv_q, r_vq; reg [2:0] dop_q; reg [7:0] dx_q; reg [127:0] dd_q; reg [255:0] rd_q; reg [31:0] r_dq;
    reg [4:0] lid_q;
    always @(posedge clk or negedge rl)
        if (!rl) begin dv_q <= 1'b0; rv_q <= 1'b0; r_vq <= 1'b0; end
        else begin dv_q <= dn_v; rv_q <= rr_v; r_vq <= r_v; end
    always @(posedge clk) begin dop_q <= dn_op; dx_q <= dn_x; dd_q <= dn_d; rd_q <= rr_d; r_dq <= r_d; lid_q <= lid; end
    wire c_job = dv_q && dop_q == 3'd0, c_wgt = dv_q && dop_q == 3'd1, c_scr = dv_q && dop_q == 3'd2;
    wire c_go = dv_q && dop_q == 3'd3;
    wire scr_mine = c_scr && dd_q[4:0] == lid_q;

    // ---- job registers
    reg post; reg [3:0] nm1; reg [15:0] a_s, b_s, o_s, rsa, rsb, rso; reg [7:0] rgap; reg [4:0] u;
    always @(posedge clk)
        if (c_job) begin
            post <= dd_q[0]; nm1 <= dd_q[4:1]; a_s <= dd_q[20:5]; b_s <= dd_q[36:21]; o_s <= dd_q[52:37];
            rsa <= dd_q[68:53]; rsb <= dd_q[84:69]; rso <= dd_q[100:85]; rgap <= dd_q[108:101];
            u <= 5'(lid_q - dd_q[9:5]);
        end
    // ---- per-row scalar sets: 2 coefficient slots of 640 b, each tagged with its row
    reg [639:0] ws [0:1]; reg [3:0] wtag [0:1]; reg [1:0] wval;
    always @(posedge clk) if (c_wgt) begin ws[dx_q[3]][128*dx_q[2:0] +: 128] <= dd_q; wtag[dx_q[3]] <= dx_q[7:4]; end

    // ---- static read calendar
    reg run, gph; reg [3:0] ip; reg [4:0] im; reg [2:0] it; reg [7:0] gc; reg [15:0] a_r, b_r;
    wire [15:0] i_s = {6'd0, u} + {6'd0, im, 5'd0};
    reg iss; reg [15:0] isec; reg [19:0] imeta;      // {scalar, x 6 / 0, gph, row 4, m 5, t 3}
    always @* begin
        iss = 1'b0; isec = '0; imeta = '0;
        if (scr_mine) begin iss = 1'b1; isec = dd_q[15:0]; imeta = {1'b1, dx_q[5:0], 13'd0}; end
        else if (run && gc == 8'd0) begin
            iss = 1'b1; imeta = {1'b0, 6'd0, gph, ip, im, it};
            if (gph) isec = b_s + i_s;
            else if (post) isec = (it == 3'd0) ? (a_r + i_s) : (b_r + 16'(it - 3'd1) * 16'(SD) + i_s);
            else isec = a_r + 16'(it[1:0]) * 16'(SD) + i_s;
        end
    end
    reg [19:0] meta_q;
    always @(posedge clk or negedge rl) if (!rl) rq_v <= 1'b0; else rq_v <= iss;
    always @(posedge clk) begin rq_s <= isec; meta_q <= imeta; end
    // fixed return: the response of the read registered at edge n is at the pin flop after edge n + RR + 1
    wire [RR+1:0] vexp; wire [19:0] rmeta;
    ot_hdc_vline #(.D(RR + 1)) u_vexp (.clk(clk), .rst_n(rl), .v(rq_v), .vd(vexp));
    ot_hdc_delay #(.W(20), .D(RR + 1)) u_rmeta (.clk(clk), .rst_n(rl), .d(meta_q), .q(rmeta));
    wire r_sc = rmeta[19]; wire [5:0] r_sx = rmeta[18:13]; wire r_g = rmeta[12]; wire [3:0] r_row = rmeta[11:8];
    wire [4:0] r_m = rmeta[7:3]; wire [2:0] r_t = rmeta[2:0];
    wire rsp = rv_q && !r_sc, srsp = rv_q && r_sc;

    // ---- responses
    reg [255:0] asb [0:3];
    reg [255:0] op [0:4];
    // gain store gb (NM x 256) and x store xb (KX x NM x 256) are 1R1W SRAM macros (ot_sram_1r1w_128x256_m1_r2c2,
    // 128 rows: gb uses NM = 20, xb KX NM = 80).  Both were runtime-indexed flop arrays read through a registered
    // 80:1 / 20:1 x 256-b mux; the macro's registered read (rd_out valid the edge after the address edge,
    // read-before-write) is the same 1-edge registered read, so the calendar, the row II and every result are
    // unchanged edge for edge (gate 10-19: the flop x store stalled yosys > 2,700 s).
    wire [255:0] gb_rd, xb_rd;
    generate if (KX * NM > 128 || NM > 128) begin : g_xb_fit
        $error("ot_hnx_fused_lane: KX * NM = %0d x-store rows exceed the 128-row macro", KX * NM);
    end endgenerate
    reg sw; reg [1:0] kk; reg sws; reg mx_v; reg [127:0] pre_q;
    wire [0:0] pslot = (MUT == 1) ? 1'b0 : r_row[0];
    wire pre_last = rsp && !r_g && !post && r_t == 3'd3;
    wire post_last = rsp && post && r_t == 3'd4;
    always @(posedge clk) begin
        if (rsp && !r_g && r_t != 3'd4 && !(post ? 1'b0 : r_t == 3'd3)) asb[r_t[1:0]] <= rd_q;
        if (pre_last) begin
            op[0] <= asb[0]; op[1] <= asb[1]; op[2] <= asb[2]; op[3] <= rd_q; pre_q <= ws[pslot][127:0];
        end
        if (post_last) begin op[0] <= asb[0]; op[1] <= asb[1]; op[2] <= asb[2]; op[3] <= asb[3]; op[4] <= rd_q; end
    end
    // MUT 5 (bench negative): the gain is cleared at row 1 -- every gain read issued after that edge returns zero
    reg g_clr, g_clr_q;
    always @(posedge clk or negedge rl)
        if (!rl) begin g_clr <= 1'b0; g_clr_q <= 1'b0; end
        else begin
            if (c_job) g_clr <= 1'b0;
            else if (MUT == 5 && run && !gph && ip == 4'd1 && im == 5'd0 && it == 3'd0) g_clr <= 1'b1;
            g_clr_q <= g_clr;
        end

    // ---- datapath (the LL lane's flat element pipelines, unchanged)
    wire [7:0] hv; wire [255:0] ho; wire [7:0] hf;
    wire [255:0] xl; wire [7:0] mf, sf; wire [255:0] sq;
    wire [255:0] qq; wire [7:0] f1, f2;
    localparam integer DM = LM + 3 * LA + 1;
    wire [DM:0] vm;
    ot_hdc_vline #(.D(DM)) u_vm (.clk(clk), .rst_n(rl), .v(mx_v), .vd(vm));
    wire x_v = vm[DM];
    reg sc_run; reg [4:0] sm; reg [3:0] sr; reg [31:0] rh;
    wire [KB-1:0] ss_sl = (MUT == 3) ? '0 : KB'(sr);
    reg [255:0] xo; reg xo_v; reg [4:0] xo_m;
    wire [6:0] xb_ra = 7'(32'(ss_sl) * NM + 32'(sm));
    always @(posedge clk) xo_m <= sm;
    always @* xo = xb_rd;
    always @(posedge clk or negedge rl) if (!rl) xo_v <= 1'b0; else xo_v <= sc_run;
    wire [4:0] wm_d;
    ot_hdc_delay #(.W(5), .D(LMS - 1)) u_wm (.clk(clk), .rst_n(rl), .d(xo_m), .q(wm_d));
    wire [255:0] wo = (MUT == 5 && g_clr_q) ? 256'd0 : gb_rd;
    ot_sram_1r1w_128x256_m1_r2c2 u_gb (.clk(clk), .r_ce_in(1'b1), .r_addr_in(7'(wm_d)), .rd_out(gb_rd),
        .w_ce_in(rsp && r_g), .w_addr_in(7'(r_m)), .wd_in(rd_q), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    wire [LMS:0] vx;
    ot_hdc_vline #(.D(LMS)) u_vx (.clk(clk), .rst_n(rl), .v(xo_v), .vd(vx));
    wire [639:0] wsw = ws[sws];
    genvar e;
    generate for (e = 0; e < 8; e = e + 1) begin : g_el
        ot_hnx_fused_el u_e (.clk(clk), .rst_n(rl), .sw(sw), .mx_v(mx_v), .x_v(x_v), .xo_v(xo_v), .wv(vx[LMS]),
            .y(op[0][32*e +: 32]), .r0(op[1][32*e +: 32]), .r1(op[2][32*e +: 32]), .r2(op[3][32*e +: 32]),
            .r3(op[4][32*e +: 32]), .pre(pre_q), .c0(wsw[32*(4 + 0 + kk) +: 32]), .c1(wsw[32*(4 + 4 + kk) +: 32]),
            .c2(wsw[32*(4 + 8 + kk) +: 32]), .c3(wsw[32*(4 + 12 + kk) +: 32]), .pc(wsw[32*kk +: 32]),
            .xo(xo[32*e +: 32]), .rh(rh), .wo(wo[32*e +: 32]),
            .hv(hv[e]), .ho(ho[32*e +: 32]), .hf(hf[e]), .xl(xl[32*e +: 32]), .mf(mf[e]), .sq(sq[32*e +: 32]),
            .sf(sf[e]), .qq(qq[32*e +: 32]), .f1(f1[e]), .f2(f2[e]));
    end endgenerate
    // the chunk chain (ot_dsrom_su_norm's, N = 8) over the squares
    localparam integer DS = LM + 7 * LA;
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rl), .v(x_v), .vd(vs));
    wire [31:0] acc [0:7]; wire [7:0] cf;
    assign acc[0] = sq[31:0]; assign cf[0] = 1'b0;
    genvar k;
    generate for (k = 1; k < 8; k = k + 1) begin : g_ch
        wire [31:0] sd;
        ot_hdc_delay #(.W(32), .D(LA * (k - 1))) u_sd (.clk(clk), .rst_n(rl), .d(sq[32*k +: 32]), .q(sd));
        ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rl, vs[LM + LA * (k - 1)], acc[k - 1], sd, acc[k], cf[k]);
    end endgenerate
    wire cs_v = vs[DS];
    wire [LMS:0] vq;
    ot_hdc_vline #(.D(LMS)) u_vq (.clk(clk), .rst_n(rl), .v(vx[LMS]), .vd(vq));
    reg y_v; reg [255:0] yb;
    always @(posedge clk) for (integer w = 0; w < 8; w = w + 1) yb[32*w +: 32] <= bf16(qq[32*w +: 32]);
    always @(posedge clk or negedge rl) if (!rl) y_v <= 1'b0; else y_v <= vq[LMS];

    // ---- x slots: written by the mix of row xr (sector xm), freed by the scale of that row
    reg [3:0] xr; reg [4:0] xm; reg [KX-1:0] xbusy;
    wire [KB-1:0] xw_sl = (MUT == 3) ? '0 : KB'(xr);
    ot_sram_1r1w_128x256_m1_r2c2 u_xb (.clk(clk), .r_ce_in(1'b1), .r_addr_in(xb_ra), .rd_out(xb_rd),
        .w_ce_in(x_v), .w_addr_in(7'(32'(xw_sl) * NM + 32'(xm))), .wd_in(xl), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    // ---- outputs
    reg [3:0] yr, orow; reg [4:0] ym, om; reg [1:0] ok; reg [15:0] o_y, o_p;
    wire [15:0] y_i = {6'd0, u} + {6'd0, ym, 5'd0}, o_i = {6'd0, u} + {6'd0, om, 5'd0};

    // ---- control
    always @(posedge clk or negedge rl) begin
        if (!rl) begin
            run <= 1'b0; gph <= 1'b0; ip <= '0; im <= '0; it <= '0; gc <= '0; a_r <= '0; b_r <= '0; wval <= '0;
            sw <= 1'b0; kk <= '0; sws <= 1'b0; mx_v <= 1'b0; sc_run <= 1'b0; sm <= '0; sr <= '0; rh <= '0;
            xr <= '0; xm <= '0; xbusy <= '0; yr <= '0; ym <= '0; orow <= '0; om <= '0; ok <= '0; o_y <= '0; o_p <= '0;
            up_v <= 1'b0; up_t <= 1'b0; up_x <= '0; up_d <= '0; wq_v <= 1'b0; wq_s <= '0; wq_d <= '0; fin <= 1'b0; flt <= 1'b0;
        end else begin
            up_v <= 1'b0; mx_v <= 1'b0; wq_v <= 1'b0; fin <= 1'b0;
            if (c_job) begin
                run <= 1'b0; gph <= 1'b0; ip <= '0; im <= '0; it <= '0; gc <= '0; a_r <= dd_q[20:5]; b_r <= dd_q[36:21];
                wval <= '0; sw <= 1'b0; sc_run <= 1'b0; sm <= '0; sr <= '0; xr <= '0; xm <= '0; xbusy <= '0;
                yr <= '0; ym <= '0; orow <= '0; om <= '0; ok <= '0; o_y <= dd_q[52:37]; o_p <= dd_q[52:37]; flt <= 1'b0;
            end
            if (c_wgt) wval[dx_q[3]] <= 1'b1;
            if (c_go) begin run <= 1'b1; gph <= !post; end
            if (scr_mine && run) flt <= 1'b1;                            // scalar read inside the data calendar
            // ---- read calendar
            if (run && !scr_mine) begin
                if (gc != 8'd0) gc <= gc - 8'd1;
                else if (gph) begin
                    if (im == 5'(NM - 1)) begin im <= '0; gph <= 1'b0; end else im <= im + 5'd1;
                end else if (it == (post ? 3'd4 : 3'd3)) begin
                    it <= '0;
                    if (im == 5'(NM - 1)) begin
                        im <= '0;
                        if (ip == nm1) run <= 1'b0;
                        else begin
                            ip <= ip + 4'd1; gc <= rgap;
                            if (MUT != 2) a_r <= a_r + rsa;
                            b_r <= b_r + rsb;
                        end
                    end else im <= im + 5'd1;
                end else it <= it + 3'd1;
            end
            // ---- response checks: every response on its fixed edge, nothing unsolicited
            if (rv_q != vexp[RR + 1]) flt <= 1'b1;
            if (srsp) begin up_v <= 1'b1; up_t <= 1'b0; up_x <= {4'd0, r_sx}; up_d <= rd_q; end
            // PRE: the mix of a sector with ITS row's pre (slot tag must name the row)
            if (pre_last) begin
                mx_v <= 1'b1;
                if (MUT != 1 && (!wval[r_row[0]] || wtag[r_row[0]] != r_row)) flt <= 1'b1;
            end
            // POST: a 4-row sweep (k = 0..3) of the sector with its row's post / comb
            if (post_last) begin
                sw <= 1'b1; kk <= '0; sws <= pslot;
                if (sw) flt <= 1'b1;                                     // sweeps never overlap (5 reads a sector)
                if (MUT != 1 && (!wval[r_row[0]] || wtag[r_row[0]] != r_row)) flt <= 1'b1;
            end else if (sw) begin if (kk == 2'd3) sw <= 1'b0; kk <= kk + 2'd1; end
            // x into its slot (row xr): the slot must be free (the row KX before scaled)
            if (x_v) begin
                if (xm == 5'd0) begin
                    if (MUT != 3 && xbusy[xw_sl]) flt <= 1'b1;
                    xbusy[xw_sl] <= 1'b1;
                end
                if (xm == 5'(NM - 1)) begin xm <= '0; xr <= xr + 4'd1; end else xm <= xm + 5'd1;
            end
            if (cs_v) begin
                up_v <= 1'b1; up_t <= 1'b1; up_x <= '0; up_d[31:0] <= acc[7];
                if (srsp) flt <= 1'b1;
            end
            // PRE phase C: row sr's r lands -> scale its x slot (x complete, no scale running)
            if (r_vq) begin
                if (MUT != 6 || sr == 4'd0) rh <= r_dq;
                if (sc_run || xo_v || xr <= sr || post) flt <= 1'b1;
                sc_run <= 1'b1;
            end
            if (sc_run) begin
                if (sm == 5'(NM - 1)) begin sc_run <= 1'b0; sm <= '0; sr <= sr + 4'd1; xbusy[ss_sl] <= 1'b0; end
                else sm <= sm + 5'd1;
            end
            // outputs (one write a cycle at most: PRE y NM a row, POST 4 a sector every >= 5 cycles)
            if (y_v) begin
                wq_v <= 1'b1; wq_s <= o_y + y_i; wq_d <= yb;
                if (ym == 5'(NM - 1)) begin
                    ym <= '0; yr <= yr + 4'd1; o_y <= o_y + rso;
                    if (yr == nm1) fin <= 1'b1;
                end else ym <= ym + 5'd1;
            end
            if (hv[0]) begin
                wq_v <= 1'b1; wq_s <= o_p + 16'(ok) * 16'(SD) + o_i; wq_d <= ho;
                ok <= ok + 2'd1;
                if (ok == 2'd3) begin
                    if (om == 5'(NM - 1)) begin
                        om <= '0; orow <= orow + 4'd1; o_p <= o_p + rso;
                        if (orow == nm1) fin <= 1'b1;
                    end else om <= om + 5'd1;
                end
                if (y_v) flt <= 1'b1;
            end
            if ((|hf) || (|mf) || (|sf) || (|cf) || (|f1) || (|f2)) flt <= 1'b1;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// one FUSED element (lane column e of 8): the LL lane's per-element pipelines, unchanged (HC_POST sweep lane, norm mix,
// square, x * r, w * (x r)).  (* keep_hierarchy *) + no parameter override: the 8 identical columns are synthesised
// and ABC-mapped ONCE (the flat lane, 852k cells, ran yosys SHARE 1,476 s + ABC 1,385 s > the 2,700 s gate cap).
// Latencies are the lane's: ML 7, AL 6 (hcpost), LM 5, LA 6 (mix / square), LMS 6 (scale multipliers).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_hnx_fused_el (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         sw,
    input  wire         mx_v,
    input  wire         x_v,
    input  wire         xo_v,
    input  wire         wv,
    input  wire [31:0]  y,
    input  wire [31:0]  r0,
    input  wire [31:0]  r1,
    input  wire [31:0]  r2,
    input  wire [31:0]  r3,
    input  wire [127:0] pre,
    input  wire [31:0]  c0,
    input  wire [31:0]  c1,
    input  wire [31:0]  c2,
    input  wire [31:0]  c3,
    input  wire [31:0]  pc,
    input  wire [31:0]  xo,
    input  wire [31:0]  rh,
    input  wire [31:0]  wo,
    output wire         hv,
    output wire [31:0]  ho,
    output wire         hf,
    output wire [31:0]  xl,
    output wire         mf,
    output wire [31:0]  sq,
    output wire         sf,
    output wire [31:0]  qq,
    output wire         f1,
    output wire         f2
);
    localparam integer LM = 5, LA = 6, LMS = 6, ML = 7, AL = 6;
    wire [31:0] pp;
    ot_dsrom_su_hcpost_lane #(.ML(ML), .AL(AL)) u_h (.clk(clk), .rst_n(rst_n), .v(sw),
        .r0(r0), .r1(r1), .r2(r2), .r3(r3), .y(y), .c0(c0), .c1(c1), .c2(c2), .c3(c3), .p(pc),
        .vo(hv), .o(ho), .fault(hf));
    ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rst_n), .v(mx_v), .h0(y), .h1(r0), .h2(r1),
        .h3(r2), .pre(pre), .x(xl), .fault(mf));
    ot_hdc_qmul_lat #(LM) u_sq (clk, rst_n, x_v, xl, xl, sq, sf);
    ot_hdc_qmul_lat #(LMS) u_xr (clk, rst_n, xo_v, xo, rh, pp, f1);
    ot_hdc_qmul_lat #(LMS) u_w  (clk, rst_n, wv, wo, pp, qq, f2);
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// top.  job (217 b, the decoded HGI-1R record fields this unit uses; VM FP32 word addresses / strides):
//   [0] post (0 HC_PRE_NORM, 1 HC_POST)  [4:1] nm1 = N - 1  [23:5] A  [42:24] B  [61:43] C  [80:62] O
//   [104:81] rs_A  [128:105] rs_B  [152:129] rs_C  [176:153] rs_O (signed)  [184:177] rgap  [216:185] eps
// job_v is a static launch (compiler edge): a launch while busy, or a refused job, FAULTs (no lane activity).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_fused_top #(
    parameter integer D    = 5120,
    parameter integer KX   = 4,
    parameter integer RR   = 10,
    parameter integer RL   = 4,
    parameter integer NMAX = 8,
    parameter integer MUT  = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              job_v,
    input  wire [216:0]      job,
    output reg               done,
    output reg               fault,
    output wire              busy,
    output wire [31:0]       rq_v,
    output wire [32*16-1:0]  rq_s,
    input  wire [31:0]       rr_v,
    input  wire [32*256-1:0] rr_d,
    output wire [31:0]       wq_v,
    output wire [32*16-1:0]  wq_s,
    output wire [32*256-1:0] wq_d
);
    localparam integer SD = D / 8, NM = D / 256, NB = NM;
    localparam integer NBP = (NB <= 1) ? 1 : (1 << $clog2(NB));
    localparam integer LG = $clog2(NBP);
    localparam integer LM = 5, LA = 6;
    localparam integer WSC = 2 * RL + RR + 8;            // last SCRD -> its scalar in scb (fixed; checked)
    function automatic integer tz(input integer x);
        integer t;
        begin t = 0; while (t < 31 && ((x >> t) & 1) == 0) t = t + 1; tz = t; end
    endfunction
    localparam integer DK = tz(D), DF = D >> DK;
    generate if (D % 256 != 0 || NM > 31 || NMAX > 16) begin : g_bad
        ot_hnx_fused_D_must_be_a_multiple_of_256 u_trap ();
    end endgenerate

    // ---- job decode
    reg [216:0] jq;
    wire j_post = jq[0]; wire [3:0] j_nm1 = jq[4:1];
    wire [18:0] ja = jq[23:5], jb = jq[42:24], jc = jq[61:43], jo = jq[80:62];
    wire [23:0] rsA = jq[104:81], rsB = jq[128:105], rsC = jq[152:129], rsO = jq[176:153];
    wire [5:0] nsc_j = j_post ? 6'(3 * (32'(j_nm1) + 1)) : 6'(32'(j_nm1) + 1);
    wire job_ok = (ja[2:0] == 3'd0) && (jb[2:0] == 3'd0) && (jc[2:0] == 3'd0) && (jo[2:0] == 3'd0) &&
                  (ja[7:3] == jb[7:3]) && (ja[7:3] == jo[7:3]) &&                    // lane-local: one bank phase
                  (rsA[7:0] == 8'd0) && (rsB[7:0] == 8'd0) && (rsO[7:0] == 8'd0) && (rsC[2:0] == 3'd0) &&
                  (j_post || rsB == 24'd0) &&                                        // PRE: the gain is a broadcast
                  (32'(j_nm1) < NMAX);

    // ---- command bus + r channel -> RL relays per lane; lane status -> RL relays
    reg cv; reg [2:0] cop; reg [7:0] cx; reg [127:0] cd;
    reg rbv; reg [31:0] rb;
    wire [31:0] l_upv, l_upt, l_fin, l_flt; wire [32*10-1:0] l_upx; wire [32*256-1:0] l_upd;
    genvar gl;
    generate for (gl = 0; gl < 32; gl = gl + 1) begin : g_ln
        wire dv; wire [138:0] dd; wire lrv; wire [31:0] lr;
        ot_hnx_fused_rly #(.W(139), .N(RL)) u_dn (.clk(clk), .rst_n(rst_n), .v(cv), .d({cop, cx, cd}), .vq(dv), .q(dd));
        ot_hnx_fused_rly #(.W(32), .N(RL)) u_rd (.clk(clk), .rst_n(rst_n), .v(rbv), .d(rb), .vq(lrv), .q(lr));
        wire uv, ut, fn, fl; wire [9:0] ux; wire [255:0] ud;
        ot_hnx_fused_lane #(.D(D), .KX(KX), .RR(RR), .MUT(MUT == 4 ? 0 : MUT)) u_l (.clk(clk), .rst_n(rst_n),
            .lid(5'(gl)), .rq_v(rq_v[gl]), .rq_s(rq_s[gl*16 +: 16]), .rr_v(rr_v[gl]), .rr_d(rr_d[gl*256 +: 256]),
            .wq_v(wq_v[gl]), .wq_s(wq_s[gl*16 +: 16]), .wq_d(wq_d[gl*256 +: 256]),
            .dn_v(dv), .dn_op(dd[138:136]), .dn_x(dd[135:128]), .dn_d(dd[127:0]), .r_v(lrv), .r_d(lr),
            .up_v(uv), .up_t(ut), .up_x(ux), .up_d(ud), .fin(fn), .flt(fl));
        wire [2:0] sq;
        ot_hdc_delay #(.W(3), .D(RL), .RESET(1)) u_st (.clk(clk), .rst_n(rst_n), .d({fn, fl, 1'b0}), .q(sq));
        wire uq; wire [266:0] uqd;
        ot_hnx_fused_rly #(.W(267), .N(RL)) u_up (.clk(clk), .rst_n(rst_n), .v(uv), .d({ut, ux, ud}), .vq(uq), .q(uqd));
        assign l_upv[gl] = uq; assign l_upt[gl] = uqd[266]; assign l_upx[gl*10 +: 10] = uqd[265:256];
        assign l_upd[gl*256 +: 256] = uqd[255:0];
        assign l_fin[gl] = sq[2]; assign l_flt[gl] = sq[1];
    end endgenerate

    // ---- scalars (prologue): scb[x] = scalar sector x (row p, sector j at x = p NS + j)
    reg [255:0] scb [0:47]; reg [5:0] scl;
    always @(posedge clk) for (integer w = 0; w < 32; w = w + 1) if (l_upv[w] && !l_upt[w]) scb[l_upx[w*10 +: 6]] <= l_upd[w*256 +: 256];

    // ---- chunk sums: the 32 lanes run one calendar, so a block's 32 chunk sums land on ONE edge
    reg [4:0] ph;                            // chunk u + 32 m is lane (u + ph) mod 32
    wire c_any = |(l_upv & l_upt), c_all = &(l_upv & l_upt);
    reg b0_v; reg [1023:0] b0; reg [5:0] b0_i; reg [5:0] bi;
    always @(posedge clk) if (c_all) begin
        for (integer L = 0; L < 32; L = L + 1) b0[32*L +: 32] <= l_upd[32'(5'(L + ph)) * 256 +: 32];
        b0_i <= bi;
    end
    // block tree: 5 pairwise levels in the golden order (left = even chunk), pipelined
    wire [31:0] tv [0:5][0:31]; wire [5:0] tf;
    localparam integer DTB = 5 * LA;
    wire [DTB:0] tvl;
    ot_hdc_vline #(.D(DTB)) u_tvl (.clk(clk), .rst_n(rst_n), .v(b0_v), .vd(tvl));
    wire [5:0] tbi;
    ot_hdc_delay #(.W(6), .D(DTB)) u_tbi (.clk(clk), .rst_n(rst_n), .d(b0_i), .q(tbi));
    genvar c, kt, n;
    generate
        for (c = 0; c < 32; c = c + 1) begin : g_t0 assign tv[0][c] = b0[32*c +: 32]; end
        assign tf[0] = 1'b0;
        for (kt = 1; kt <= 5; kt = kt + 1) begin : g_tl
            wire [(32 >> kt)-1:0] f;
            for (c = 0; c < (32 >> kt); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rst_n, tvl[LA * (kt - 1)], tv[kt - 1][2 * c], tv[kt - 1][2 * c + 1],
                                               tv[kt][c], f[c]);
            end
            for (c = (32 >> kt); c < 32; c = c + 1) begin : g_tz assign tv[kt][c] = 32'd0; end
            assign tf[kt] = |f;
        end
    endgenerate
    wire vsum_v = tvl[DTB]; wire [31:0] vsum = tv[5][0];
    // ROW-PIPELINED padded heap (ot_dsrom_su_norm's vector levels): leaves NBP + b; a node whose right subtree is all
    // padding passes its left value.  A real node holds (vld) its value until its consumer fires; a new value on a held
    // node is a collision (FAULT).  Row p + 1's blocks therefore enter while row p's upper levels finish.
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer hgt(input integer x);            // height of heap node x (leaves 0)
        integer h, y;
        begin h = LG; y = x; while (y > 1) begin y = y >> 1; h = h - 1; end hgt = h; end
    endfunction
    function automatic integer is_add(input integer x);         // internal node with a real right subtree
        is_add = (x >= 1 && x < NBP && ((((2 * x + 1) << (hgt(x) - 1)) - NBP) < NB)) ? 1 : 0;
    endfunction
    wire [31:0] nv [1:2*NBP-1]; wire nd [1:2*NBP-1]; wire cons [1:2*NBP-1]; wire fire [1:2*NBP-1];
    wire [2*NBP-1:0] ncol;
    assign ncol[0] = 1'b0;
    generate
        for (n = NBP; n < 2 * NBP; n = n + 1) begin : g_leaf
            assign fire[n] = 1'b0;
            if (n - NBP < NB) begin : g_r
                reg [31:0] val; reg vld;
                wire hit = vsum_v && tbi == 6'(n - NBP);
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) vld <= 1'b0;
                    else if (hit) vld <= 1'b1;
                    else if (cons[n] && MUT != 4) vld <= 1'b0;
                always @(posedge clk) if (hit) val <= vsum;
                assign nd[n] = vld; assign nv[n] = val;
                assign ncol[n] = hit && vld && !cons[n] && MUT != 4;
            end else begin : g_p
                assign nd[n] = 1'b0; assign nv[n] = 32'd0; assign ncol[n] = 1'b0;
            end
        end
        for (n = 1; n < NBP; n = n + 1) begin : g_vn
            if (is_add(n)) begin : g_add
                reg vld; reg [31:0] val; wire [LAV:0] av; wire [31:0] s; wire af;
                assign fire[n] = nd[2 * n] && nd[2 * n + 1];
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rst_n), .v(fire[n]), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rst_n, fire[n], nv[2 * n], nv[2 * n + 1], s, af);
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) vld <= 1'b0;
                    else if (av[LAV]) vld <= 1'b1;
                    else if (cons[n] && MUT != 4) vld <= 1'b0;
                always @(posedge clk) if (av[LAV]) val <= s;
                assign nd[n] = vld; assign nv[n] = val;
                assign ncol[n] = (av[LAV] && vld && !cons[n] && MUT != 4) || af;
            end else begin : g_pass
                assign fire[n] = 1'b0; assign nd[n] = nd[2 * n]; assign nv[n] = nv[2 * n]; assign ncol[n] = 1'b0;
            end
        end
        // consumers: a node's value is taken when its parent fires (through pass nodes: the pass node's consumer)
        assign cons[1] = nd[1];
        for (n = 2; n < 2 * NBP; n = n + 1) begin : g_cons
            if (is_add(n >> 1)) begin : g_ca assign cons[n] = fire[n >> 1]; end
            else if ((n & 1) == 0) begin : g_cp assign cons[n] = cons[n >> 1]; end
            else begin : g_cz assign cons[n] = 1'b0; end
        end
    endgenerate
    wire ss_v = nd[1]; wire [31:0] ss = nv[1];
    // scalar tail: / D, + eps, rsqrt
    reg [31:0] eps_r;
    reg ssv_q; reg [31:0] ss_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) ssv_q <= 1'b0; else ssv_q <= ss_v;
    always @(posedge clk) ss_q <= ss;
    wire [31:0] mq, me, rr; wire mq_v, rr_v2, f_div, f_eps, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rst_n), .v(ssv_q), .x(ss_q), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rst_n, mq_v, mq, eps_r, me, f_eps);
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(ve[LA]), .x(me), .y(rr), .vo(rr_v2), .fault(f_rsq));

    // ---- sequencer (static calendar)
    localparam [2:0] S_IDLE = 0, S_SC = 1, S_SCW = 2, S_WG = 3, S_RUN = 4;
    reg [2:0] st; reg post; reg [3:0] nm1; reg [5:0] nsc, scs; reg [7:0] wt; reg sfault;
    reg [15:0] cs_r; reg [1:0] cj; reg [15:0] rsc_s;
    reg [3:0] wrow; reg [2:0] wb; reg [15:0] tg; reg [15:0] tw_next; reg [15:0] per; reg [4:0] gofs;
    reg [3:0] hr;
    assign busy = (st != S_IDLE);
    wire [2:0] nbt = post ? 3'd5 : 3'd1;                         // WGT beats a row
    wire [5:0] wsx = post ? 6'(3 * wrow + wb / 2) : 6'(wrow);  // scalar sector of beat wb of row wrow
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; cv <= 1'b0; cop <= '0; cx <= '0; cd <= '0; rbv <= 1'b0; rb <= '0;
            jq <= '0; post <= 1'b0; nm1 <= '0; nsc <= '0; scs <= '0; scl <= '0; wt <= '0; sfault <= 1'b0; cs_r <= '0;
            cj <= '0; rsc_s <= '0; wrow <= '0; wb <= '0; tg <= '0; tw_next <= '0; per <= '0; gofs <= '0; ph <= '0;
            b0_v <= 1'b0; bi <= '0; hr <= '0; eps_r <= '0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cv <= 1'b0; b0_v <= 1'b0; rbv <= 1'b0;
            for (integer w = 0; w < 32; w = w + 1) if (l_upv[w] && !l_upt[w]) scl <= scl + 6'd1;
            // chunk sums: all 32 lanes or none
            if (c_any != c_all) sfault <= 1'b1;
            if (c_all) begin b0_v <= 1'b1; bi <= (bi == 6'(NB - 1)) ? 6'd0 : bi + 6'd1; end
            if (|ncol || (|tf)) sfault <= 1'b1;
            if (f_div || f_eps || f_rsq) sfault <= 1'b1;
            // r of the row whose sum left the heap -> the lanes (own channel: never collides with WGT beats)
            if (rr_v2) begin rbv <= 1'b1; rb <= rr; hr <= hr + 4'd1; end
            if (|l_fin && !(&l_fin)) sfault <= 1'b1;
            if (job_v && st != S_IDLE) sfault <= 1'b1;                  // launch collision
            case (st)
                S_IDLE: if (job_v) begin
                    jq <= job;
                    st <= S_SC;                                         // decode next edge (job registered)
                    scs <= '0; scl <= '0; sfault <= 1'b0; hr <= '0; bi <= '0;
                    cop <= 3'd7;                                        // marks "decode pending"
                end
                S_SC: if (cop == 3'd7) begin
                    if (!job_ok) begin fault <= 1'b1; st <= S_IDLE; cop <= '0; end
                    else begin
                        post <= j_post; nm1 <= j_nm1; nsc <= nsc_j; eps_r <= jq[216:185]; ph <= ja[7:3];
                        cs_r <= jc[18:3]; cj <= '0; rsc_s <= rsC[18:3];
                        per <= j_post ? 16'(5 * NM) + 16'(jq[184:177]) : 16'(4 * NM) + 16'(jq[184:177]);
                        gofs <= j_post ? 5'd0 : 5'(NM);
                        cv <= 1'b1; cop <= 3'd0; cx <= '0;
                        cd <= {19'd0, jq[184:177], rsO[18:3], rsB[18:3], rsA[18:3], jo[18:3], jb[18:3], ja[18:3], j_nm1, j_post};
                    end
                end else begin                                          // one SCRD a cycle
                    cv <= 1'b1; cop <= 3'd2; cx <= 8'(scs); cd <= {112'd0, cs_r + 16'(cj)};
                    if (cj == (post ? 2'd2 : 2'd0)) begin cj <= '0; cs_r <= cs_r + rsc_s; end else cj <= cj + 2'd1;
                    scs <= scs + 6'd1;
                    if (scs + 6'd1 == nsc) begin st <= S_SCW; wt <= 8'(WSC); end
                end
                S_SCW: if (wt != 8'd0) wt <= wt - 8'd1;
                       else begin
                           if (scl != nsc) sfault <= 1'b1;               // a scalar missed its fixed return
                           st <= S_WG; wrow <= '0; wb <= '0;
                       end
                S_WG: begin                                             // rows 0 and 1 into slots 0 / 1, then GO
                    if (wrow <= nm1 && wrow < 4'd2) begin
                        cv <= 1'b1; cop <= 3'd1; cx <= {wrow, wrow[0], wb}; cd <= scb[wsx][128*(wb % 2) +: 128];
                        if (wb == nbt - 3'd1) begin wb <= '0; wrow <= wrow + 4'd1; end else wb <= wb + 3'd1;
                    end else begin
                        cv <= 1'b1; cop <= 3'd3; st <= S_RUN; tg <= '0; wb <= '0;
                        // row p >= 2 beats arrive RR + 8 cycles after row p - 1 starts (slot p mod 2 then free)
                        tw_next <= 16'(gofs) + per + 16'(RR + 8);
                    end
                end
                S_RUN: begin
                    tg <= tg + 16'd1;
                    if (wrow <= nm1 && tg >= tw_next) begin
                        cv <= 1'b1; cop <= 3'd1; cx <= {wrow, wrow[0], wb}; cd <= scb[wsx][128*(wb % 2) +: 128];
                        if (wb == nbt - 3'd1) begin wb <= '0; wrow <= wrow + 4'd1; tw_next <= tw_next + per; end
                        else wb <= wb + 3'd1;
                    end
                    if (&l_fin) begin
                        st <= S_IDLE;
                        if (sfault || (|l_flt) || (!post && hr != nm1 + 4'd1)) fault <= 1'b1; else done <= 1'b1;
                    end
                end
                default: st <= S_IDLE;
            endcase
            if (|l_flt) sfault <= 1'b1;
        end
    end
endmodule
`default_nettype wire
