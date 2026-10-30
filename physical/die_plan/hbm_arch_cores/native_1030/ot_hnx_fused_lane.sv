
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
    // n4 (SAFE-DESIGN item 3): one kept reset relay copy per region -- [0] lane control, [1 + e] element column e
    // (n3 gate: ONE relay flop drove 16,053 async-reset loads, textbook_lint REFUSE high_fanout)
    wire [8:0] rlr; wire rl = rlr[0];
    ot_rst_relay #(.REGIONS(9)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rlr));
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
    ot_hdc_delay_ring #(.W(20), .D(RR + 1), .RING(1)) u_rmeta (.clk(clk), .rst_n(rl), .d(meta_q), .q(rmeta));
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
        // n4: the PRE mix runs on the HC_POST product lanes 0..3 (h_j into op[j + 1]); op[0] (the HC_POST y * post
        // lane, unused by the mix) is zeroed so its product is an exact 0 and raises no flag
        if (pre_last) begin
            op[0] <= 256'd0; op[1] <= asb[0]; op[2] <= asb[1]; op[3] <= asb[2]; op[4] <= rd_q; pre_q <= ws[pslot][127:0];
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
    // n4: x leaves the folded chain at ML + 3 AL + 1 (the HC_POST multiplier ML 7 replaces the mix's LM 5: +2 edges)
    localparam integer DM = ML + 3 * AL + 1;
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
    ot_hdc_delay_ring #(.W(5), .D(LMS - 1), .RING(1)) u_wm (.clk(clk), .rst_n(rl), .d(xo_m), .q(wm_d));
    wire [255:0] wo = (MUT == 5 && g_clr_q) ? 256'd0 : gb_rd;
    ot_sram_1r1w_128x256_m1_r2c2 u_gb (.clk(clk), .r_ce_in(1'b1), .r_addr_in(7'(wm_d)), .rd_out(gb_rd),
        .w_ce_in(rsp && r_g), .w_addr_in(7'(r_m)), .wd_in(rd_q), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    wire [LMS:0] vx;
    ot_hdc_vline #(.D(LMS)) u_vx (.clk(clk), .rst_n(rl), .v(xo_v), .vd(vx));
    wire [639:0] wsw = ws[sws];
    genvar e;
    generate for (e = 0; e < 8; e = e + 1) begin : g_el
        // coefficients: HC_POST row post / comb of sweep step kk; PRE the row's pre (static per record: post)
        wire [31:0] cb0 = post ? wsw[32*(4 + 0 + kk) +: 32] : pre_q[0 +: 32];
        wire [31:0] cb1 = post ? wsw[32*(4 + 4 + kk) +: 32] : pre_q[32 +: 32];
        wire [31:0] cb2 = post ? wsw[32*(4 + 8 + kk) +: 32] : pre_q[64 +: 32];
        wire [31:0] cb3 = post ? wsw[32*(4 + 12 + kk) +: 32] : pre_q[96 +: 32];
        wire [31:0] cbp = post ? wsw[32*kk +: 32] : 32'd0;
        ot_hnx_fused_el2 u_e (.clk(clk), .rst_n(rlr[1 + e]), .v(sw || mx_v), .x_v(x_v), .xo_v(xo_v), .wv(vx[LMS]),
            .y(op[0][32*e +: 32]), .a0(op[1][32*e +: 32]), .a1(op[2][32*e +: 32]), .a2(op[3][32*e +: 32]),
            .a3(op[4][32*e +: 32]), .b0(cb0), .b1(cb1), .b2(cb2), .b3(cb3), .p(cbp),
            .xo(xo[32*e +: 32]), .rh(rh), .wo(wo[32*e +: 32]),
            .hv(hv[e]), .ho(ho[32*e +: 32]), .hf(hf[e]), .xl(xl[32*e +: 32]), .sq(sq[32*e +: 32]),
            .sf(sf[e]), .qq(qq[32*e +: 32]), .f1(f1[e]), .f2(f2[e]));
        assign mf[e] = 1'b0;                 // the mix's flags are the folded chain's (hf)
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
        ot_hdc_delay_ring #(.W(32), .D(LA * (k - 1)), .RING(1)) u_sd (.clk(clk), .rst_n(rl), .d(sq[32*k +: 32]), .q(sd));
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
            if (hv[0] && post) begin              // n4: the folded chain also retires PRE mixes (x only)
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
