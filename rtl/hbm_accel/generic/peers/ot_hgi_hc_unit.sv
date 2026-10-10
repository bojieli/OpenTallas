`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 HC unit die body (hgi-adapters, 2026-10-09; D1 stage / drain model, docs/HBM_GENERIC_INTERFACE.md 2.4).
// HC.HC_MIX end to end: the record adapter ot_hgi_hc_record (LEGACY 0) -> this body:
//   STAGE  A = h (VM, HC x D FP32 words, BF16-valued) into the HCP's local x memory through one VM packet client
//          (4 reads outstanding, in-order responses); any A alignment; a word whose low 16 bits are nonzero faults
//          (the golden asserts the residual is BF16).  x bank k, word r, lane l = flat[8 (r W + l) + k] (BF16).
//   PROJ   24 rows, each one HCP command (the r25 engine ot_hdc_v41x_hcp, npos 1, nout 1, scale 1: the row's
//          csum dot with the flat residual times r = rsqrt(ss / K + eps)) on a weight window of 8 banks of
//          R = ceil(K / 8W) words (ot_hdc_v41x_weight_window, the r25 HBM window, bank stride R at run time).
//   POST   Model.hc_mixes' tail on one multiplier, one adder, the r25 exp pipe and the r25 divider, then the r25
//          Sinkhorn (ot_hdc_sinkhorn_mc): pre = sigmoid(mix * scale0 + base) + hc_eps,
//          post = 2 sigmoid(mix * scale1 + base), comb = Sinkhorn(exp(mix * scale2 + base - rowmax)).
//   DRAIN  the 24 words [pre 4 | post 4 | comb 16] to O (any alignment, word-masked sector writes); retire after.
// HBM weight-set format (B.base >> 5 = sector S0; SPW = W / 8 sectors a word; RS = R x SPW):
//   row o (0..23), bank k (0..7), word r: sector S0 + (8 o + k) RS + r SPW = W binary32 lanes fn[o][8 (r W + l) + k]
//   (lanes past K / 8 zero); then at S0 + 192 RS four sectors: scale[0..2] at words 0..2, base[0..23] at words 8..31.
// HBM client: one request channel {sector addr, len (sectors), tag {src 4, slot}}, responses {tag, beat, data} in
// any order (src 0..7 = weight bank, 8 = the scale / base fetch); always ready (registered).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hc_unit #(
    parameter integer W = 32,               // HCP lanes per group (8W MAC lanes)
    parameter integer RMAX = 128,           // window words per bank: K <= 8 W RMAX
    parameter integer ITERS = 20,           // Sinkhorn iterations (hc_sinkhorn_iters)
    parameter integer STEP_CYC = 7,         // Sinkhorn multicycle step
    parameter [31:0]  HC_EPS = 32'h358637BD, // hc_eps (1e-6)
    parameter integer HAW = 35,
    parameter integer MUT_POST = 0,         // mutant: pre without + hc_eps
    parameter integer TW = $clog2(RMAX),
    parameter integer TG = 4 + TW
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [31:0]   cfg_norm_eps,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a, rec_b, rec_o,
    input  wire [20:0]   rec_n_a, rec_n_o,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    output reg           hq_v,
    input  wire          hq_rdy,
    output reg  [HAW-1:0] hq_addr,
    output reg  [2:0]    hq_len,
    output reg  [TG-1:0] hq_tag,
    input  wire          hr_v,
    input  wire [TG-1:0] hr_tag,
    input  wire [1:0]    hr_beat,
    input  wire [255:0]  hr_data
);
    localparam integer SPW = W / 8, LW = $clog2(W), LS = $clog2(SPW), AW = 16, CWW = $clog2(RMAX + 1);
    // ---- the record adapter
    wire job_v; reg job_rdy, job_done, job_fault; wire [228:0] job;
    ot_hgi_hc_record #(.LEGACY(0)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .cfg_hc_eps(cfg_norm_eps),
        .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_a(rec_a), .rec_b(rec_b), .rec_o(rec_o),
        .rec_n_a(rec_n_a), .rec_n_o(rec_n_o), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted),
        .lg_v(1'b0), .lg_rdy(), .lg_job(229'd0), .job_v(job_v), .job_rdy(job_rdy), .job(job), .job_done(job_done),
        .job_fault(job_fault));
    // job: {obase 18, nwords 24, w_hbm 35, xbase 18, wbase 16, eps 32, nf 32, scale 1, nchunk 18, nout 5, npos 1}
    reg [17:0] nchunk, xbase, obase; reg [31:0] nf, eps; reg [34:0] wsec;
    reg [17:0] rr;                               // R
    reg [HAW-1:0] rs, rowstride, rowbase, pbase; reg [HAW-1:0] boff [0:7];

    // ---- local x memory (8 banks) and the HCP
    reg [W*16-1:0] xm [0:8*RMAX-1];
    wire [7:0] x_re, w_re; wire [8*AW-1:0] x_addr, w_addr; reg [8*W*16-1:0] xq1, xd; wire [8*W*32-1:0] wq;
    reg [8*W*32-1:0] wd;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_xr
        always @(posedge clk) if (x_re[g]) xq1[g*W*16 +: W*16] <= xm[g*RMAX + (x_addr[g*AW +: AW] & (RMAX - 1))];
    end endgenerate
    always @(posedge clk) begin xd <= xq1; wd <= wq; end
    reg h_cv; wire h_cr, h_ov, h_last, h_fault, h_idle; wire [31:0] h_od;
    ot_hdc_v41x_hcp #(.W(W), .TL(TW), .PMAX(1), .OMAX(2), .AW(AW), .CW(16), .ML(2)) u_hcp (.clk(clk), .rst_n(rst_n),
        .cmd_valid(h_cv), .cmd_ready(h_cr), .cmd_npos(2'd1), .cmd_nout(2'd1), .cmd_nchunk(nchunk[15:0]),
        .cmd_scale(1'b1), .cmd_nf(nf), .cmd_eps(eps), .cmd_wbase(16'd0), .cmd_xbase(16'd0),
        .w_re(w_re), .w_addr(w_addr), .w_data(wd), .x_re(x_re), .x_addr(x_addr), .x_data(xd),
        .o_valid(h_ov), .o_ready(1'b1), .o_pos(), .o_idx(), .o_data(h_od), .o_last(h_last), .fault(h_fault),
        .idle(h_idle));

    // ---- the weight windows (8 banks) and the HBM channel
    reg w_start, w_rel; wire [7:0] w_rdy, w_flt, wq_v; reg [7:0] wq_ack;
    wire [8*HAW-1:0] wq_addr; wire [8*3-1:0] wq_len; wire [8*TW-1:0] wq_tag;
    reg hr_vq; reg [TG-1:0] hr_tq; reg [1:0] hr_bq; reg [255:0] hr_dq;
    always @(posedge clk) begin hr_tq <= hr_tag; hr_bq <= hr_beat; hr_dq <= hr_data; end
    always @(posedge clk or negedge rst_n) if (!rst_n) hr_vq <= 1'b0; else hr_vq <= hr_v;
    generate for (g = 0; g < 8; g = g + 1) begin : g_win
        wire [3:0] why; wire [CWW-1:0] fetched; wire [31:0] rcv;
        ot_hdc_v41x_weight_window #(.WB(W*32), .SB(256), .WORDS(RMAX), .AW(AW), .HAW(HAW), .NPC(1), .LENW(3)) u_w (
            .clk(clk), .rst_n(rst_n), .start(w_start), .release_window(w_rel), .rom_base(16'd0),
            .hbm_base(rowbase + boff[g]), .nwords(rr[CWW-1:0]), .ready(w_rdy[g]), .hq_v(wq_v[g]), .hq_rdy(wq_ack[g]),
            .hq_addr(wq_addr[g*HAW +: HAW]), .hq_len(wq_len[g*3 +: 3]), .hq_tag(wq_tag[g*TW +: TW]),
            .hr_v(hr_vq && hr_tq[TG-1 -: 4] == g), .hr_rdy(), .hr_tag(hr_tq[TW-1:0]), .hr_beat(hr_bq),
            .hr_data(hr_dq), .rom_re(w_re[g]), .rom_addr(w_addr[g*AW +: AW]), .rom_q(wq[g*W*32 +: W*32]),
            .fault(w_flt[g]), .fault_why(why), .fetched_words(fetched), .received_sectors(rcv));
    end endgenerate
    reg p_req; reg [31:0] pw [0:31]; reg [3:0] p_got;
    // request register: lowest-index source first (8 = the parameter fetch)
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hq_v <= 1'b0; hq_addr <= 0; hq_len <= 3'd0; hq_tag <= 0; end
        else if (!hq_v || hq_rdy) begin
            hq_v <= 1'b0;
            begin : pick
                reg f; f = 1'b0;
                for (k = 0; k < 8; k = k + 1)
                    if (!f && wq_v[k]) begin
                        f = 1'b1; hq_v <= 1'b1; hq_addr <= wq_addr[k*HAW +: HAW]; hq_len <= wq_len[k*3 +: 3];
                        hq_tag <= {k[3:0], wq_tag[k*TW +: TW]};
                    end
                if (!f && p_req) begin hq_v <= 1'b1; hq_addr <= pbase; hq_len <= 3'd4; hq_tag <= {4'd8, {TW{1'b0}}}; end
            end
        end
    end
    always @* begin
        wq_ack = 8'd0;
        if (!hq_v || hq_rdy) begin : ack
            reg f; f = 1'b0;
            for (k = 0; k < 8; k = k + 1) if (!f && wq_v[k]) begin f = 1'b1; wq_ack[k] = 1'b1; end
        end
    end
    wire p_iss = (!hq_v || hq_rdy) && p_req && !(|wq_v);

    // ---- post-processing units
    reg mu_v, ad_v, ex_v, dv_v; reg [31:0] mu_a, mu_b, ad_a, ad_b, ex_a, dv_a, dv_b;
    wire mu_o, ad_o, ex_o, dv_o, ex_f, dv_f; wire [1:0] mu_e, ad_e; wire [31:0] mu_y, ad_y, ex_y, dv_y;
    ot_hdc_fp32_mul_fast u_mul (.clk(clk), .rst_n(rst_n), .valid_in(mu_v), .a(mu_a), .b(mu_b), .y(mu_y), .err(mu_e),
        .valid_out(mu_o));
    ot_hdc_fp32_add_fast u_add (.clk(clk), .rst_n(rst_n), .valid_in(ad_v), .a(ad_a), .b(ad_b), .y(ad_y), .err(ad_e),
        .valid_out(ad_o));
    ot_hdc_v41x_exp #(.LM(3), .LA(3)) u_exp (.clk(clk), .rst_n(rst_n), .v(ex_v), .x(ex_a), .y(ex_y), .vo(ex_o),
        .fault(ex_f));
    ot_hdc_v41x_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(dv_v), .a(dv_a), .b(dv_b), .y(dv_y), .vo(dv_o), .fault(dv_f));
    reg sk_req; reg [511:0] sk_in; wire sk_busy, sk_done, sk_fault; wire [511:0] sk_y;
    ot_hdc_sinkhorn_mc #(.STEP_CYC(STEP_CYC), .ITERS(ITERS), .EPS(HC_EPS)) u_sk (.clk(clk), .rst_n(rst_n), .req(sk_req),
        .in_e(sk_in), .busy(sk_busy), .done(sk_done), .y(sk_y), .fault(sk_fault));
    // destination FIFOs (each unit is in order)
    reg [4:0] mq [0:31], aq [0:31], eq [0:31], dq [0:31];
    reg [4:0] mw, mr, aw, ar, ew, er, dw, drp;
    reg [31:0] T [0:23]; reg [31:0] MX [0:3];
    reg [5:0] outst;

    // ---- control
    localparam [4:0] S_IDLE = 0, S_PAR = 1, S_STAGE = 2, S_ROW = 3, S_RW = 4, S_RC = 5, S_REL = 6, S_P1 = 7,
                     S_P2 = 8, S_MAX = 9, S_P3 = 10, S_P4 = 11, S_P5 = 12, S_P6 = 13, S_P7 = 14, S_SK = 15,
                     S_SKW = 16, S_DRAIN = 17, S_DRW = 18, S_DONE = 19, S_FAULT = 20, S_GEO = 21, S_GEO2 = 22;
    reg [4:0] st; reg [4:0] i; reg iss_done; reg [4:0] row;
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg [26:0] sec, sec_end, rsec; reg [2:0] vo_n; reg flt;
    wire [31:0] F_ONE = 32'h3F800000, F_TWO = 32'h40000000;
    function automatic fgt(input [31:0] a, input [31:0] b);    // a > b for non-NaN binary32
        if (a[31] != b[31]) fgt = !a[31] && (a[30:0] != 0 || b[30:0] != 0);
        else if (!a[31]) fgt = a[30:0] > b[30:0];
        else fgt = a[30:0] < b[30:0];
    endfunction
    function automatic isnan(input [31:0] a); isnan = a[30:23] == 8'hFF && a[22:0] != 0; endfunction
    integer q, e2;
    reg [3:0] wb_n;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; job_rdy <= 1'b1; job_done <= 1'b0; job_fault <= 1'b0; vmq <= 338'd0; w_start <= 1'b0;
            w_rel <= 1'b0; h_cv <= 1'b0; p_req <= 1'b0; mu_v <= 1'b0; ad_v <= 1'b0; ex_v <= 1'b0; dv_v <= 1'b0;
            sk_req <= 1'b0; mw <= 0; mr <= 0; aw <= 0; ar <= 0; ew <= 0; er <= 0; dw <= 0; drp <= 0; outst <= 0;
            flt <= 1'b0; vo_n <= 3'd0; p_got <= 4'd0;
        end else begin
            job_done <= 1'b0; job_fault <= 1'b0; vmq[337] <= 1'b0; w_start <= 1'b0; w_rel <= 1'b0;
            mu_v <= 1'b0; ad_v <= 1'b0; ex_v <= 1'b0; dv_v <= 1'b0;
            if (p_iss) p_req <= 1'b0;
            // parameter sectors
            if (hr_vq && hr_tq[TG-1 -: 4] == 4'd8) begin
                for (q = 0; q < 8; q = q + 1) pw[{hr_bq, 3'b000} + q] <= hr_dq[32*q +: 32];
                p_got <= p_got + 4'd1;
            end
            // unit write-backs
            if (mu_o) begin T[mq[mr]] <= mu_y; mr <= mr + 5'd1; if (mu_e != 2'd0) flt <= 1'b1; end
            if (ad_o) begin T[aq[ar]] <= ad_y; ar <= ar + 5'd1; if (ad_e != 2'd0) flt <= 1'b1; end
            if (ex_o) begin T[eq[er]] <= ex_y; er <= er + 5'd1; end
            if (dv_o) begin T[dq[drp]] <= dv_y; drp <= drp + 5'd1; end
            if (ex_f || dv_f || |w_flt || h_fault || sk_fault) flt <= 1'b1;
            wb_n = {3'd0, mu_o} + {3'd0, ad_o} + {3'd0, ex_o} + {3'd0, dv_o};
            outst <= outst - {2'd0, wb_n} + ((!flt && !iss_done && (st == S_P1 || st == S_P2 || st == S_P3 ||
                     st == S_P4 || st == S_P5 || st == S_P6 || st == S_P7)) ? 6'd1 : 6'd0);
            if (flt && st != S_FAULT && st != S_IDLE) st <= S_FAULT;
            else case (st)
                S_IDLE: if (job_v && job_rdy) begin
                    job_rdy <= 1'b0;
                    nchunk <= job[23:6]; nf <= job[56:25]; eps <= job[88:57]; xbase <= job[122:105];
                    wsec <= job[157:123]; obase <= job[199:182];
                    st <= S_GEO;
                end
                S_GEO: begin                                         // R, RS, row stride, parameter base
                    rr <= (nchunk + W - 1) >> LW;
                    st <= S_GEO2;
                end
                S_GEO2: begin
                    rs <= {{(HAW-18){1'b0}}, rr} << LS;
                    rowstride <= {{(HAW-18){1'b0}}, rr} << (LS + 3);
                    pbase <= wsec[HAW-1:0] + (({{(HAW-18){1'b0}}, rr} << (LS + 3)) * 24);
                    rowbase <= wsec[HAW-1:0];
                    if (rr > RMAX || rr == 0) flt <= 1'b1;
                    st <= S_PAR;
                end
                S_PAR: begin
                    for (q = 0; q < 8; q = q + 1) boff[q] <= rs * q;
                    p_req <= 1'b1; p_got <= 4'd0;
                    sec <= xbase >> 3; rsec <= xbase >> 3; sec_end <= ({9'd0, xbase} + {6'd0, nchunk, 3'd0} - 27'd1) >> 3;
                    vo_n <= 3'd0; st <= S_STAGE;
                end
                S_STAGE: begin                                       // A sectors -> x banks, 4 outstanding
                    if (vo_n < 3'd4 && sec <= sec_end) begin
                        vmq <= {1'b1, 1'b0, sec, 5'd0, 256'd0, 32'd0, 16'h4843};
                        sec <= sec + 27'd1;
                    end
                    if (vr[273] && !vr[256]) begin
                        for (q = 0; q < 8; q = q + 1) begin
                            e2 = {rsec, q[2:0]} - xbase;             // element index of word q
                            if (e2 >= 0 && e2 < {nchunk, 3'b000}) begin
                                xm[(e2 & 7) * RMAX + ((e2 >> 3) >> LW)][16 * ((e2 >> 3) & (W - 1)) +: 16] <= vr[32*q + 16 +: 16];
                                if (vr[32*q +: 16] != 16'd0) flt <= 1'b1;
                            end
                        end
                        rsec <= rsec + 27'd1;
                    end
                    vo_n <= vo_n + ((vo_n < 3'd4 && sec <= sec_end) ? 3'd1 : 3'd0) - ((vr[273] && !vr[256]) ? 3'd1 : 3'd0);
                    if (rsec > sec_end && vo_n == 3'd0) begin row <= 5'd0; st <= S_ROW; end   // lanes past K / 8: HCP-masked
                end
                S_ROW: if (p_got == 4'd4 || row != 5'd0) begin w_start <= 1'b1; st <= S_RW; end
                S_RW: if (&w_rdy && h_cr) begin h_cv <= 1'b1; st <= S_RC; end
                S_RC: begin
                    if (h_cv && h_cr) h_cv <= 1'b0;
                    if (h_ov) begin T[row] <= h_od; w_rel <= 1'b1; st <= S_REL; end
                end
                S_REL: begin
                    rowbase <= rowbase + rowstride;
                    if (row == 5'd23) begin
                        i <= 5'd0; iss_done <= 1'b0; st <= S_P1;
                    end else begin row <= row + 5'd1; st <= S_ROW; end
                end
                // ---- post phases: issue one element per edge, then wait for every write-back
                S_P1, S_P2, S_P3, S_P4, S_P5, S_P6, S_P7: begin
                    if (!iss_done) begin
                        case (st)
                            S_P1: begin mu_v <= 1'b1; mu_a <= T[i]; mu_b <= (i < 4) ? pw[0] : (i < 8) ? pw[1] : pw[2];
                                        mq[mw] <= i; mw <= mw + 5'd1; end
                            S_P2: begin ad_v <= 1'b1; ad_a <= T[i]; ad_b <= pw[8 + i]; aq[aw] <= i; aw <= aw + 5'd1; end
                            S_P3: begin ad_v <= 1'b1; ad_a <= T[i]; ad_b <= MX[(i - 8) >> 2] ^ 32'h80000000;
                                        aq[aw] <= i; aw <= aw + 5'd1; end
                            S_P4: begin ex_v <= 1'b1; ex_a <= (i < 8) ? T[i] ^ 32'h80000000 : T[i]; eq[ew] <= i;
                                        ew <= ew + 5'd1; end
                            S_P5: begin ad_v <= 1'b1; ad_a <= T[i]; ad_b <= F_ONE; aq[aw] <= i; aw <= aw + 5'd1; end
                            S_P6: begin dv_v <= 1'b1; dv_a <= F_ONE; dv_b <= T[i]; dq[dw] <= i; dw <= dw + 5'd1; end
                            default: if (i < 4) begin
                                         ad_v <= 1'b1; ad_a <= T[i]; ad_b <= MUT_POST ? 32'd0 : HC_EPS;
                                         aq[aw] <= i; aw <= aw + 5'd1;
                                     end else begin
                                         mu_v <= 1'b1; mu_a <= T[i]; mu_b <= F_TWO; mq[mw] <= i; mw <= mw + 5'd1;
                                     end
                        endcase
                        if (i == ((st == S_P1 || st == S_P2 || st == S_P3 || st == S_P4) ? 5'd23 : 5'd7)) iss_done <= 1'b1;
                        else i <= i + 5'd1;
                    end else if (outst == 6'd0 && !mu_o && !ad_o && !ex_o && !dv_o) begin
                        iss_done <= 1'b0;
                        case (st)
                            S_P1: begin i <= 5'd0; st <= S_P2; end
                            S_P2: st <= S_MAX;
                            S_P3: begin i <= 5'd0; st <= S_P4; end
                            S_P4: begin i <= 5'd0; st <= S_P5; end
                            S_P5: begin i <= 5'd0; st <= S_P6; end
                            S_P6: begin i <= 5'd0; st <= S_P7; end
                            default: st <= S_SK;
                        endcase
                    end
                end
                S_MAX: begin                                         // row maxima of comb (np.max; NaN faults)
                    for (q = 0; q < 4; q = q + 1) begin : mx
                        reg [31:0] m; integer c;
                        m = T[8 + 4*q];
                        for (c = 1; c < 4; c = c + 1) if (fgt(T[8 + 4*q + c], m)) m = T[8 + 4*q + c];
                        MX[q] <= m;
                    end
                    for (q = 8; q < 24; q = q + 1) if (isnan(T[q])) flt <= 1'b1;
                    i <= 5'd8; st <= S_P3;
                end
                S_SK: begin
                    for (q = 0; q < 16; q = q + 1) sk_in[32*q +: 32] <= T[8 + q];
                    sk_req <= 1'b1; st <= S_SKW;
                end
                S_SKW: begin
                    if (sk_busy) sk_req <= 1'b0;
                    if (sk_done) begin
                        for (q = 0; q < 16; q = q + 1) T[8 + q] <= sk_y[32*q +: 32];
                        sec <= obase >> 3; sec_end <= ({9'd0, obase} + 27'd23) >> 3; vo_n <= 3'd0; st <= S_DRAIN;
                    end
                end
                S_DRAIN: begin                                       // word-masked sector writes of the 24 results
                    if (vo_n < 3'd4 && sec <= sec_end) begin : dr
                        reg [255:0] dat; reg [31:0] msk; integer j;
                        dat = 256'd0; msk = 32'd0;
                        for (q = 0; q < 8; q = q + 1) begin
                            j = {sec, q[2:0]} - obase;
                            if (j >= 0 && j < 24) begin dat[32*q +: 32] = T[j]; msk[4*q +: 4] = 4'hF; end
                        end
                        vmq <= {1'b1, 1'b1, sec, 5'd0, dat, msk, 16'h4844};
                        sec <= sec + 27'd1;
                    end
                    vo_n <= vo_n + ((vo_n < 3'd4 && sec <= sec_end) ? 3'd1 : 3'd0) - ((vr[273] && vr[256]) ? 3'd1 : 3'd0);
                    if (sec > sec_end && vo_n == 3'd0) st <= S_DONE;
                end
                S_DONE: begin job_done <= 1'b1; job_rdy <= 1'b1; st <= S_IDLE; end
                S_FAULT: begin job_fault <= 1'b1; st <= S_IDLE; job_rdy <= 1'b0; end   // the adapter halts
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
