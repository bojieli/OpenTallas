// B2 contiguous quarter lane from source-pinned original LL arithmetic.
// Local sector stride8; PRE chunk tag QID*160+local chunk restores full D5120 golden order.
// Global scalar weights/rstd supplied by the central controller; retirement retains all credit waits.
// MUT (bench negatives, must FAIL; 2 / 4 / 5 as ot_hgi_hc_lane_ll): 6 lane 0 reads its sectors with m pairs swapped
//   (local stride map); 13 the legacy 32-bank phase mask (bank map; differs at a non-zero bank phase); 7 PRE chunk tag
//   rotated by one inside the quarter (a non-golden association); 8 PRE chunk tag of quarter 3 - QID (block order).
module ot_hgi_hc_lane_b2 #(
    parameter integer D   = 1280,             // contiguous quarter of production D5120
    parameter integer BANKS = 8,
    parameter integer QID = 0,
    parameter integer LQ  = 32,
    parameter integer FD  = 64,
    parameter integer HSL = 1,               // 1: the FP datapath as 8 hard element slices (ot_hgi_hc_lane_sl, own clock
                                             //    tree, registered in/out => +2 cycles); 0: flat (one 114k-flop clock root)
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [4:0]    lid,
    // VM bank lane
    output reg  [15:0]   wrq,
    input  wire          wrq_cr,
    input  wire [256:0]  wrr,
    output reg  [279:0]  wwq,
    input  wire          wwq_cr,
    input  wire          wwq_done,
    // top
    input  wire          dn_v,
    input  wire [2:0]    dn_op,
    input  wire [7:0]    dn_x,
    input  wire [127:0]  dn_d,
    output reg           up_v,
    output reg           up_t,
    output reg  [9:0]    up_x,
    output reg  [255:0]  up_d,
    output reg           wdone,
    output reg           fin,
    output reg           flt
);
    generate if (BANKS != 8 || D != 1280 || QID < 0 || QID > 3) begin : g_bad_b2
        ot_hgi_hc_lane_b2_requires_D1280_BANKS8_QID0to3 invalid_shape ();
    end endgenerate
    localparam integer SD = D / 8;           // sectors a row
    localparam integer NM = D / (8 * BANKS);         // sectors a lane (a row)
    localparam integer MB = $clog2(NM + 1);
    localparam integer QB = $clog2(LQ + 1);
    localparam integer FB = $clog2(FD + 1);
    localparam integer LM = 5, LA = 6, LMS = 6, ML = 7, AL = 6;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction
    // ---- local reset relay
    // two reset regions: rl (pin flops, sequencer, FIFO) and rp (the FP pipelines' valid lines); control flops only
    wire [1:0] rlr; wire rl = rlr[0], rp = rlr[1];
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rlr));
    // ---- pin flops
    reg wrq_cr_q, wwq_cr_q, wwq_done_q, rv_q, dv_q; reg [255:0] rd_q; reg [2:0] dop_q; reg [7:0] dx_q; reg [127:0] dd_q;
    reg [4:0] lid_q;
    always @(posedge clk or negedge rl)
        if (!rl) begin wrq_cr_q <= 1'b0; wwq_cr_q <= 1'b0; wwq_done_q <= 1'b0; rv_q <= 1'b0; dv_q <= 1'b0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; rv_q <= wrr[256]; dv_q <= dn_v; end
    always @(posedge clk) begin rd_q <= wrr[255:0]; dop_q <= dn_op; dx_q <= dn_x; dd_q <= dn_d; lid_q <= lid; end

    // ---- job registers
    reg post, run, g_ok, r_ok; reg [14:0] a_s, b_s, o_s; reg [9:0] u;      // u = this lane's first sector of a row
    reg [639:0] wt;                          // scalar words 0..19
    reg [31:0] rh;                           // rstd
    reg scp; reg [7:0] scx;                  // a scalar read pending
    // el1011-hbm-fused GPK: HC_PRE_NORM gain PACKED lane-local (BF16, compiler layout): packed sector u + 32 k of this
    // lane holds the gains of its data sectors u + 32 (2k) (words 0..3) and u + 32 (2k + 1) (words 4..7), so the gain
    // is D / 2 words (half the mover traffic) and still bank-local; NG = gain sectors this lane reads
    reg pk; wire [MB-1:0] NG = pk ? MB'(NM / 2) : MB'(NM);
    // el1011-hbm-fused READ PREFETCH (HC_POST): the lane starts its row reads on the JOB command (pf), not on GO, so the
    // top's scalar fetch / weight broadcast / GO relay (~2 RL + the scalar round trip) overlaps the reads.  Responses land
    // in a ring of RG sector groups {y, r0..r3} (the PRE x / gain buffers, idle on HC_POST); the k sweep consumes a whole
    // group a 4-cycle sweep (1.25 reads a cycle, faster than the 1-a-cycle read lane) once GO has delivered the weights.
    // Scalar reads now interleave with data reads on the bank lane: an in-order 1-bit tag FIFO (depth LQ = the lane's
    // credits) tells a scalar response from a data one.
    localparam integer RG = (2 * NM) / 5;    // ring groups (8 at D 5120)
    localparam integer RGB = (RG > 1) ? $clog2(RG) : 1;
    localparam integer TB = (LQ > 1) ? $clog2(LQ) : 1;
    reg pf;                                  // HC_POST: reads may issue (from JOB)
    reg [RGB-1:0] rgp, cgp; reg [MB:0] cg;   // ring write / consume group pointers, groups consumed
    function automatic [255:0] bf2f(input [127:0] h);
        integer e; begin bf2f = '0; for (e = 0; e < 8; e = e + 1) bf2f[32*e +: 32] = {h[16*e +: 16], 16'd0}; end
    endfunction
    wire c_job = dv_q && dop_q == 3'd0, c_wgt = dv_q && dop_q == 3'd1, c_scr = dv_q && dop_q == 3'd2;
    wire c_go = dv_q && dop_q == 3'd3, c_grdy = dv_q && dop_q == 3'd4, c_rstd = dv_q && dop_q == 3'd5;
    wire scr_mine = c_scr && dd_q[$clog2(BANKS)-1:0] == lid_q[$clog2(BANKS)-1:0];
    always @(posedge clk) begin
        if (c_job) begin post <= dd_q[45]; pk <= dd_q[46] && !dd_q[45]; a_s <= dd_q[14:0]; b_s <= dd_q[29:15]; o_s <= dd_q[44:30];
                         u <= (MUT == 13) ? 10'((lid_q - dd_q[4:0]) & 5'd31) : 10'((lid_q - dd_q[$clog2(BANKS)-1:0]) & (BANKS-1)); end
        if (c_wgt) wt[128*dx_q[2:0] +: 128] <= dd_q;
        if (c_rstd) rh <= dd_q[31:0];
    end

    // ---- read issue: scalar | HC_POST 5 a sector | PRE phase A 4 a sector, phase B 1 a sector (the gain)
    reg [QB-1:0] cr;
    reg [MB-1:0] im; reg [2:0] it;           // issue: sector m (0..NM-1), read t of it
    reg ph_b;                                // PRE: issuing the gain (phase B)
    reg [MB:0] gs, gp;                       // HC_POST: sectors started / fully pushed (FIFO admission)
    reg [FB-1:0] occ;
    wire [MB-1:0] im_x = (MUT == 6 && lid_q == 5'd0 && im < MB'(NM)) ? (im ^ MB'(1)) : im;
    wire [9:0] i_s = u + 10'(im_x * BANKS);       // the row sector of m
    wire rd_done = ph_b ? (im == NG) : (im == MB'(NM));
    reg  iss; reg [14:0] isec;
    always @* begin
        iss = 1'b0; isec = '0;
        if (scr_mine) begin iss = 1'b1; isec = dd_q[14:0]; end
        else if ((run || pf) && cr != '0 && !rd_done) begin
            if (post) begin
                if (it != 3'd0 || (({1'b0, occ} + 8'(4 * (gs - gp)) + 8'd4 <= 8'(FD)) && ((gs - cg) < (MB+1)'(RG)))) begin
                    iss = 1'b1;
                    isec = (it == 3'd0) ? (a_s + 15'(i_s)) : (b_s + 15'(it - 3'd1) * 15'(SD) + 15'(i_s));
                end
            end else if (!ph_b) begin
                iss = 1'b1; isec = a_s + 15'(it[1:0]) * 15'(SD) + 15'(i_s);
            end else if (g_ok || MUT == 5) begin
                iss = 1'b1; isec = b_s + 15'(i_s);
            end
        end
    end
    always @(posedge clk or negedge rl)
        if (!rl) wrq[15] <= 1'b0; else wrq[15] <= iss;
    always @(posedge clk) wrq[14:0] <= isec;

    // ---- responses (in order on the bank lane)
    reg [MB-1:0] rm; reg [2:0] rt; reg rph_b;
    reg [255:0] asb [0:4];                    // sector assembly
    reg [255:0] op [0:4];                    // HC_POST operands of the sector in the k sweep (y, r0..r3)
    reg [255:0] xb [0:NM-1], gb [0:NM-1];    // PRE: x and gain of the lane's sectors
    reg sw; reg [1:0] kk;                    // HC_POST k sweep
    reg mx_v;                                // PRE: a sector's h quad to the mix
    reg [LQ-1:0] tgq; reg [TB-1:0] tgw, tgr;  // tag FIFO: 1 = a scalar read
    wire tg_h = tgq[tgr];
    always @(posedge clk) if (iss) tgq[tgw] <= scr_mine;
    always @(posedge clk or negedge rl)
        if (!rl) begin tgw <= '0; tgr <= '0; end
        else begin if (iss) tgw <= tgw + 1'b1; if (rv_q) tgr <= tgr + 1'b1; end
    wire rsp = rv_q && !tg_h;                // a data response
    wire srsp = rv_q && tg_h;                // a scalar response
    // HC_POST ring: write slot 5 rgp + rt, consume group cgp
    wire [7:0] rs_w = 8'(5 * rgp) + 8'(rt);
    wire cs_go = post && run && ({1'b0, rm} > cg) && (!sw || kk == 2'd3);
    function automatic [255:0] ring(input [7:0] i);
        ring = (i < 8'(NM)) ? xb[i] : gb[i - 8'(NM)];
    endfunction
    wire last_h = rsp && !rph_b && !post && rt == 3'd3;
    always @(posedge clk) begin
        if (rsp && !rph_b && !post) asb[rt] <= rd_q;
        if (cs_go) begin
            op[0] <= ring(8'(5 * cgp)); op[1] <= ring(8'(5 * cgp) + 8'd1); op[2] <= ring(8'(5 * cgp) + 8'd2);
            op[3] <= ring(8'(5 * cgp) + 8'd3); op[4] <= ring(8'(5 * cgp) + 8'd4);
            if (MUT == 2 && lid_q == 5'd0) begin op[1] <= ring(8'(5 * cgp) + 8'd2); op[2] <= ring(8'(5 * cgp) + 8'd1); end
        end
        if (rsp && post && rs_w >= 8'(NM)) gb[rs_w - 8'(NM)] <= rd_q;
        if (last_h) begin
            op[0] <= asb[0]; op[1] <= asb[1]; op[2] <= asb[2]; op[3] <= rd_q;
            if (MUT == 2 && lid_q == 5'd0) begin op[0] <= asb[1]; op[1] <= asb[0]; end
        end
        if (rsp && rph_b && !pk) gb[rm] <= rd_q;
        if (rsp && rph_b && pk) begin gb[{rm, 1'b0}] <= bf2f(rd_q[127:0]); gb[{rm, 1'b1}] <= bf2f(rd_q[255:128]); end
    end

    // ---- datapath: HC_POST 8 element pipelines (row k of the sector a cycle); HC_PRE_NORM mix / x / squares / chunk
    //      chain; phase C scale y = bf16(w * (x * r)).  HSL = 1: each element's pipelines are one hard slice
    //      (ot_hgi_hc_lane_sl) with pin flops in and registered outputs, so every slice output lands SX = 2 cycles later
    //      and the shell's x / chunk / y valid lines are SX longer.
    localparam integer SX = (HSL != 0) ? 2 : 0;
    wire [7:0] hv; wire [255:0] ho; wire [7:0] hf;
    wire [255:0] xl; wire [7:0] mf, sf; wire [255:0] sq;
    wire [255:0] pp, qq; wire [7:0] f1, f2;
    localparam integer DM = LM + 3 * LA + 1;
    wire [DM+SX:0] vm;
    ot_hdc_vline #(.D(DM + SX)) u_vm (.clk(clk), .rst_n(rl), .v(mx_v), .vd(vm));
    wire x_v = vm[DM + SX];
    reg sc_run; reg [MB-1:0] sm;             // scale sector issue
    reg [255:0] xo; reg xo_v; reg [MB-1:0] xo_m;
    always @(posedge clk) begin xo <= xb[sm]; xo_m <= sm; end
    always @(posedge clk or negedge rl) if (!rl) xo_v <= 1'b0; else xo_v <= sc_run;
    wire [MB-1:0] wm_d;                      // the gain read LMS - 1 cycles after x's (the multiplier's operand register)
    ot_hdc_delay #(.W(MB), .D(LMS - 1)) u_wm (.clk(clk), .rst_n(rl), .d(xo_m), .q(wm_d));
    reg [255:0] wo;
    always @(posedge clk) wo <= gb[wm_d];
    wire [LMS:0] vx;
    ot_hdc_vline #(.D(LMS)) u_vx (.clk(clk), .rst_n(rl), .v(xo_v), .vd(vx));
    genvar e;
    generate if (HSL != 0) begin : g_hsl
        // HC_POST coefficients of row kk (shared by the 8 slices; the slices pin-flop them with sw)
        wire [159:0] cf5 = {wt[32*kk +: 32], wt[32*(4 + 12 + kk) +: 32], wt[32*(4 + 8 + kk) +: 32],
                            wt[32*(4 + 4 + kk) +: 32], wt[32*(4 + 0 + kk) +: 32]};
        for (e = 0; e < 8; e = e + 1) begin : g_sl
            // hard child: no parameter overrides (its defaults are this lane's LM / LA / LMS / ML / AL)
            ot_hgi_hc_lane_sl u_sl (.clk(clk), .rst_n(rst_n), .i_sw(sw),
                .i_op({op[4][32*e +: 32], op[3][32*e +: 32], op[2][32*e +: 32], op[1][32*e +: 32], op[0][32*e +: 32]}),
                .i_cf(cf5), .i_mx(mx_v), .i_pre(wt[127:0]), .i_xov(xo_v), .i_xo(xo[32*e +: 32]), .i_rh(rh),
                .i_wov(vx[LMS]), .i_wo(wo[32*e +: 32]),
                .o_hv(hv[e]), .o_ho(ho[32*e +: 32]), .o_hf(hf[e]), .o_xl(xl[32*e +: 32]), .o_mf(mf[e]),
                .o_sq(sq[32*e +: 32]), .o_sf(sf[e]), .o_qq(qq[32*e +: 32]), .o_f1(f1[e]), .o_f2(f2[e]));
        end
        assign pp = '0;
    end else begin : g_flat
        for (e = 0; e < 8; e = e + 1) begin : g_hp
            ot_dsrom_su_hcpost_lane #(.ML(ML), .AL(AL)) u_h (.clk(clk), .rst_n(rp), .v(sw),
                .r0(op[1][32*e +: 32]), .r1(op[2][32*e +: 32]), .r2(op[3][32*e +: 32]), .r3(op[4][32*e +: 32]),
                .y(op[0][32*e +: 32]), .c0(wt[32*(4 + 0 + kk) +: 32]), .c1(wt[32*(4 + 4 + kk) +: 32]),
                .c2(wt[32*(4 + 8 + kk) +: 32]), .c3(wt[32*(4 + 12 + kk) +: 32]), .p(wt[32*kk +: 32]),
                .vo(hv[e]), .o(ho[32*e +: 32]), .fault(hf[e]));
        end
        for (e = 0; e < 8; e = e + 1) begin : g_mx
            ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rp), .v(mx_v), .h0(op[0][32*e +: 32]),
                .h1(op[1][32*e +: 32]), .h2(op[2][32*e +: 32]), .h3(op[3][32*e +: 32]), .pre(wt[127:0]),
                .x(xl[32*e +: 32]), .fault(mf[e]));
            ot_hdc_qmul_lat #(LM) u_sq (clk, rp, x_v, xl[32*e +: 32], xl[32*e +: 32], sq[32*e +: 32], sf[e]);
        end
        for (e = 0; e < 8; e = e + 1) begin : g_sc
            ot_hdc_qmul_lat #(LMS) u_xr (clk, rp, xo_v, xo[32*e +: 32], rh, pp[32*e +: 32], f1[e]);
            ot_hdc_qmul_lat #(LMS) u_w  (clk, rp, vx[LMS], wo[32*e +: 32], pp[32*e +: 32], qq[32*e +: 32], f2[e]);
        end
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
        ot_hdc_delay #(.W(32), .D(LA * (k - 1))) u_sd (.clk(clk), .rst_n(rp), .d(sq[32*k +: 32]), .q(sd));
        ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rp, vs[LM + LA * (k - 1)], acc[k - 1], sd, acc[k], cf[k]);
    end endgenerate
    wire cs_v = vs[DS];
    wire [LMS+SX:0] vq;
    ot_hdc_vline #(.D(LMS + SX)) u_vq (.clk(clk), .rst_n(rl), .v(vx[LMS]), .vd(vq));
    reg y_v; reg [255:0] yb;
    integer w;
    always @(posedge clk) for (w = 0; w < 8; w = w + 1) yb[32*w +: 32] <= bf16(qq[32*w +: 32]);
    always @(posedge clk or negedge rl) if (!rl) y_v <= 1'b0; else y_v <= vq[LMS + SX];

    // ---- outputs into the write FIFO (in order): HC_POST rows (om, ok), PRE y (ym)
    reg [MB-1:0] om, ym, xm, cm; reg [1:0] ok;
    wire [9:0] o_i = u + 10'(om * BANKS), y_i = u + 10'(ym * BANKS), c_i = u + 10'(cm * BANKS);
    wire push = hv[0] || y_v;
    wire [270:0] pdat = hv[0] ? {o_s + 15'(ok) * 15'(SD) + 15'(o_i), ho} : {o_s + 15'(y_i), yb};
    wire f_hv, ovf, pop; wire [270:0] f_hd;
    reg [QB-1:0] wcr;
    ot_fifo_sram_fwft #(.W(271), .DEPTH(FD), .MACRO(0), .ESL(64)) u_f (.clk(clk), .rst_n(rl), .push(push), .wdata(pdat), .pop(pop),
        .hv(f_hv), .head(f_hd), .ovf(ovf));
    assign pop = run && f_hv && (wcr != '0);
    always @(posedge clk or negedge rl) if (!rl) wwq[279] <= 1'b0; else wwq[279] <= pop;
    always @(posedge clk) wwq[278:0] <= {f_hd[270:256], f_hd[255:0], 8'hFF};   // no enable: wwq[279] qualifies

    // ---- control
    reg [7:0] npush, nexp_l;                 // outputs pushed / expected this run (HC_POST 4 NM, PRE NM)
    reg [7:0] npop;
    always @(posedge clk or negedge rl) begin
        if (!rl) begin
            run <= 1'b0; g_ok <= 1'b0; r_ok <= 1'b0; scp <= 1'b0; scx <= '0; cr <= QB'(LQ); im <= '0; it <= '0; ph_b <= 1'b0;
            pf <= 1'b0; rgp <= '0; cgp <= '0; cg <= '0;
            gs <= '0; gp <= '0; occ <= '0; rm <= '0; rt <= '0; rph_b <= 1'b0; sw <= 1'b0; kk <= '0; mx_v <= 1'b0;
            sc_run <= 1'b0; sm <= '0; om <= '0; ym <= '0; xm <= '0; cm <= '0; ok <= '0; wcr <= QB'(LQ);
            npush <= '0; nexp_l <= '0; npop <= '0;
            up_v <= 1'b0; up_t <= 1'b0; wdone <= 1'b0; fin <= 1'b0; flt <= 1'b0;
        end else begin
            up_v <= 1'b0; wdone <= wwq_done_q; mx_v <= 1'b0;
            if (c_job) begin
                run <= 1'b0; g_ok <= 1'b0; r_ok <= 1'b0; im <= '0; it <= '0; ph_b <= 1'b0; gs <= '0; gp <= '0;
                rm <= '0; rt <= '0; rph_b <= 1'b0; sw <= 1'b0; kk <= '0; sc_run <= 1'b0; sm <= '0;
                om <= '0; ym <= '0; xm <= '0; cm <= '0; ok <= '0; npush <= '0; npop <= '0; fin <= 1'b0; flt <= 1'b0;
                nexp_l <= dd_q[45] ? 8'(4 * NM) : 8'(NM);
                pf <= dd_q[45]; rgp <= '0; cgp <= '0; cg <= '0;
            end
            if (c_go) run <= 1'b1;
            if (c_grdy) g_ok <= 1'b1;
            if (scr_mine) begin scp <= 1'b1; scx <= dx_q; end
            // credits
            if (iss && !wrq_cr_q) cr <= cr - 1'b1; else if (!iss && wrq_cr_q) cr <= cr + 1'b1;
            if (pop && !wwq_cr_q) wcr <= wcr - 1'b1; else if (!pop && wwq_cr_q) wcr <= wcr + 1'b1;
            if (push && !pop) occ <= occ + 1'b1; else if (!push && pop) occ <= occ - 1'b1;
            // issue counters
            if (iss && !scr_mine) begin
                if (post) begin
                    if (it == 3'd0) gs <= gs + 1'b1;
                    if (it == 3'd4) begin it <= '0; im <= im + 1'b1; end else it <= it + 1'b1;
                end else if (!ph_b) begin
                    if (it == 3'd3) begin
                        it <= '0;
                        if (im == MB'(NM - 1)) begin im <= '0; ph_b <= 1'b1; end else im <= im + 1'b1;
                    end else it <= it + 1'b1;
                end else im <= im + 1'b1;
            end
            // responses
            if (srsp) begin
                scp <= 1'b0; up_v <= 1'b1; up_t <= 1'b0;
            end else if (rsp) begin
                if (rph_b) rm <= rm + 1'b1;
                else if (post) begin
                    if (rt == 3'd4) begin rt <= '0; rm <= rm + 1'b1; end else rt <= rt + 1'b1;
                end else begin
                    if (rt == 3'd3) begin
                        rt <= '0;
                        if (rm == MB'(NM - 1)) begin rm <= '0; rph_b <= 1'b1; end else rm <= rm + 1'b1;
                    end else rt <= rt + 1'b1;
                end
            end
            if (rsp && post && rt == 3'd4) rgp <= (rgp == RGB'(RG - 1)) ? '0 : rgp + 1'b1;
            if (cs_go) begin
                sw <= 1'b1; kk <= '0; cg <= cg + 1'b1; cgp <= (cgp == RGB'(RG - 1)) ? '0 : cgp + 1'b1;
            end
            else if (sw) begin if (kk == 2'd3) sw <= 1'b0; kk <= kk + 2'd1; end
            if (last_h) mx_v <= 1'b1;
            // PRE: x into its buffer, the chunk sum up
            if (x_v) xm <= xm + 1'b1;
            if (cs_v) begin up_v <= 1'b1; up_t <= 1'b1; cm <= cm + 1'b1; end
            // PRE phase C: the scale starts when r has landed and every gain sector is in
            if (c_rstd) r_ok <= 1'b1;
            if (!post && run && r_ok && !sc_run && sm == '0 && rph_b && rm == NG && ym == '0 && !y_v && !vx[LMS]
                && !xo_v && npush == '0) sc_run <= 1'b1;
            if (sc_run) begin if (sm == MB'(NM - 1)) sc_run <= 1'b0; sm <= sm + 1'b1; end
            // outputs
            if (hv[0]) begin if (ok == 2'd3) begin om <= om + 1'b1; gp <= gp + 1'b1; end ok <= ok + 2'd1; end
            if (y_v) ym <= ym + 1'b1;
            if (push) npush <= npush + 1'b1;
            if (pop) npop <= npop + 1'b1;
            if (run && npush == nexp_l && npop == nexp_l && !f_hv && cr == QB'(LQ) && (MUT == 4 || wcr == QB'(LQ))) fin <= 1'b1;
            if ((|hf) || (|mf) || (|sf) || (|cf) || (|f1) || (|f2) || ovf) flt <= 1'b1;
        end
    end
    always @(posedge clk) if (x_v) xb[xm] <= xl; else if (rsp && post && rs_w < 8'(NM)) xb[rs_w] <= rd_q;
    // up data: a scalar sector (rd_q) or a chunk sum in the low word; 32-bit select, no enable on the 224 upper bits
    always @(posedge clk) begin
        up_d[255:32] <= rd_q[255:32];
        up_d[31:0]   <= cs_v ? acc[7] : rd_q[31:0];
        up_x         <= !cs_v ? {2'd0, scx} : (MUT == 7) ? (10'(QID * SD) + ((c_i == 10'(SD - 1)) ? 10'd0 : c_i + 10'd1)) :
                        (MUT == 8) ? (10'((3 - QID) * SD) + c_i) : (10'(QID * SD) + c_i);
    end
endmodule
