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
//   S0 .. S0 + 3: scale[0..2] at words 0..2, base[0..23] at words 8..31;
//   row o (0..23), bank k (0..7), word r: sector S0 + 4 + (8 o + k) RS + r SPW = W binary32 lanes
//   fn[o][8 (r W + l) + k] (lanes past K / 8 zero).
// G22 ops: 0 HC_MIX (above); 1 HC_MIX_ROWS: rows row0 .. row0 + nrows - 1 only (their fn rows alone are read), the raw x r
// mixes drained to O (nrows words), no post; 2 HC_MIX_POST: A = the 24 gathered mixes (VM) -> POST -> O, only the 4
// scale / base sectors read.
// HBM client: one request channel {sector addr, len (sectors), tag {src 4, slot}}, responses {tag, beat, data} in
// any order (src 0..7 = weight bank, 8 = the scale / base fetch); always ready (registered).
// MULTI-POSITION (hgi-1010/d, 2026-10-10): A.m = P positions (rows of A at A.stride; op 2: rows of 24 mixes) are staged
// into the x memory at word p R; each row's weights are fetched ONCE and the HCP runs it for all P positions (npos P:
// the HCP's own per-position ss / r); the post / drain then runs per position into O + p O.stride.  Each position's
// result is the single-position record's bit for bit (positions are independent; the HCP is exact per position).
// X MEMORY: bank k (the HCP's term-k bank) holds RMAX x PMAX words of W BF16 lanes; XMACRO 1 builds it from
// ot_sram_1r1w_1024x256 macros (W / 16 a bank, 16-b lane write mask; RMAX x PMAX <= 1,024), else flops.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hc_unit #(
    parameter integer W = 32,               // HCP lanes per group (8W MAC lanes)
    parameter integer RMAX = 128,           // window words per bank: K <= 8 W RMAX
    parameter integer ITERS = 20,           // Sinkhorn iterations (hc_sinkhorn_iters)
    parameter integer STEP_CYC = 7,         // Sinkhorn multicycle step
    parameter [31:0]  HC_EPS = 32'h358637BD, // hc_eps (1e-6)
    parameter integer HAW = 35,
    parameter integer MUT_POST = 0,         // mutant: pre without + hc_eps
    parameter integer WMACRO = 0,           // hgi-1010/d: 1 = weight windows in ot_sram_1r1w_128x256 macros (RMAX 128)
    parameter integer PMAX = 8,             // hgi-1010/d: positions a record (A.m; the MTP verify), a power of two
    parameter integer XMACRO = 0,           // hgi-1010/d: 1 = the x memory in ot_sram_1r1w_1024x256 macros
    parameter integer MUT_MP = 0,           // mutant: every position lands on position 0's x words
    parameter integer WVM = 0,              // hgi-1010/d: 1 = x staging through a 32-lane VM wide READ group (W group,
                                            //   client 2 of ot_hgi_vm_lanearb): a sector-aligned A row lands 32
                                            //   sectors (one WAVE = one x word row) an edge, VM lane b -> x lane
                                            //   (b - s0) mod 32 (needs W = 32); unaligned rows: the packet path
    parameter integer WLQ = 24,             // its credits a lane (the W bus round trip)
    parameter integer WD = 8,               // waves outstanding (the client's response FIFO depth, a power of two)
    parameter integer MUT_HL = 0,           // mutant: window 3 takes lane 4's responses
    parameter integer HSRC = 0,             // hgi-1010/d weight source: 0 = HBM lanes only; 1 = also the VM APERTURE (lead
                                            //   decision (b)): 2 weight slots in the unit, filled by DMA.LOAD through the
                                            //   VM unit's aperture route onto ap_* (32 write lanes); HC_MIX_ROWS with
                                            //   B = VM 2^18 + 32,768 j reads slot j (no HBM fetch)
    parameter integer MUT_AP = 0,           // mutant: the slot fill count ignores the last bank (the HCP may start early)
    parameter integer SPL = 1,              // striped fetch: sub-windows (HBM lanes) a bank; HL = 8 SPL when > 1
    parameter integer HL = 1,               // hgi-1010/d STRIPED weight fetch: HBM read lanes; 1 = one port shared by the
                                            //   8 windows (+ the parameter fetch); 8 = window g owns lane g (the
                                            //   parameter fetch rides lane 0), 8 windows fill in parallel
    parameter integer MUT_WV = 0,           // mutants: 1 the wide landing rotates one lane too far, 2 the client delivers
                                            //   lane 1 one wave late (ot_hgi_vm_wrd MUT 1)
    parameter integer TW = $clog2(RMAX),
    // a window word is W / 8 sectors; one HBM request carries at most 4 (the 3-bit length of the HBM lane protocol), so
    // a W > 32 word is fetched in W / 32 segments and the window tag grows by their index (hgi-1010/d W sweep)
    parameter integer SGL = (W > 32) ? $clog2(W / 32) : 0,
    parameter integer RTW = TW + SGL,
    parameter integer TG = 4 + RTW
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
    output reg  [HL-1:0]     hq_v,
    input  wire [HL-1:0]     hq_rdy,
    output reg  [HL*HAW-1:0] hq_addr,
    output reg  [HL*3-1:0]   hq_len,
    output reg  [HL*TG-1:0]  hq_tag,
    input  wire [HL-1:0]     hr_v,
    input  wire [HL*TG-1:0]  hr_tag,
    input  wire [HL*2-1:0]   hr_beat,
    input  wire [HL*256-1:0] hr_data,
    // the VM wide read lanes (WVM = 1; a lane-group client: rg_req / rg_gnt per burst, lane b {v, sector15},
    // credits, responses {v, data256} in order per lane); WVM = 0: rg_req / wrq stay 0
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    // the weight aperture write lanes (HSRC = 1; from the VM unit's DMA wide-write route for VM words >= 2^18): lane b
    // {v, sector 13 (aperture sector: slot [12], bank [11:9], word / position [8:0]), data 256, word mask 8}.
    // 8 LANES, lane k = weight bank k (sector[11:9] == k, else a fault): a lane's sector is written the edge after it
    // arrives (each lane owns its bank's macros: no arbitration); ap_cr[k] = its credit (one in flight), ap_done[k]
    // the edge the write lands (hgi-1010/d 10-11: 2,224 b down, 16 b back, per hbm-phys)
    input  wire [8*278-1:0]  ap_q,
    output reg  [7:0]        ap_cr,
    output reg  [7:0]        ap_done
);
    localparam integer SPW = W / 8, LW = $clog2(W), LS = $clog2(SPW), AW = 16, CWW = $clog2(RMAX + 1);
    // ---- the record adapter
    wire job_v; reg job_rdy, job_done, job_fault; wire [228:0] job; wire [3:0] j_np; wire [17:0] j_as, j_os;
    ot_hgi_hc_record #(.LEGACY(0), .PMAX(PMAX)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .cfg_hc_eps(cfg_norm_eps),
        .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_a(rec_a), .rec_b(rec_b), .rec_o(rec_o),
        .rec_n_a(rec_n_a), .rec_n_o(rec_n_o), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted),
        .lg_v(1'b0), .lg_rdy(), .lg_job(229'd0), .job_v(job_v), .job_rdy(job_rdy), .job(job), .job_done(job_done),
        .job_fault(job_fault), .job_npos(j_np), .job_astr(j_as), .job_ostr(j_os));
    // job: {obase 18, nwords 24, w_hbm 35, xbase 18, wbase 16, eps 32, nf 32, scale 1, nchunk 18, nout 5, npos 1}
    reg [17:0] nchunk, xbase, obase; reg [31:0] nf, eps; reg [34:0] wsec; reg [1:0] op; reg [4:0] row0, nrows, rend;
    reg [17:0] rr;                               // R
    reg [3:0] npos, pc; reg [17:0] astr, ostr, xrow, orow; reg [AW-1:0] xwo;   // positions; per-position cursors
    reg [31:0] TP [0:PMAX*24-1];                 // the raw mixes of every position (p 24 + row)
    reg [HAW-1:0] rs, rowstride, rowbase, pbase; reg [HAW-1:0] boff [0:7];

    localparam [4:0] S_IDLE = 0, S_PAR = 1, S_STAGE = 2, S_ROW = 3, S_RW = 4, S_RC = 5, S_REL = 6, S_P1 = 7,
                     S_P2 = 8, S_MAX = 9, S_P3 = 10, S_P4 = 11, S_P5 = 12, S_P6 = 13, S_P7 = 14, S_SK = 15,
                     S_SKW = 16, S_DRAIN = 17, S_DRW = 18, S_DONE = 19, S_FAULT = 20, S_GEO = 21, S_GEO2 = 22,
                     S_LDA = 23, S_PL = 24, S_WST = 25, S_WFL = 26;
    reg wpre, wst;   // wpre: start the first row's windows next edge (boff settled); wst: they are started
    reg [4:0] st; reg [4:0] i; reg iss_done; reg [4:0] row;
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg [26:0] sec, sec_end, rsec; reg [2:0] vo_n; reg flt;
    // ---- local x memory (8 banks) and the HCP
    // x memory: bank k (the HCP's term-k bank), lane l: RMAX BF16 words, one array each (a sector lands one element in
    // every bank; the HCP reads all W lanes of one word of every bank an edge)
    wire x_land;
    wire [7:0] x_re, w_re; wire [8*AW-1:0] x_addr, w_addr; reg [8*W*16-1:0] xq1, xd; wire [8*W*32-1:0] wq;
    reg [8*W*32-1:0] wd;
    genvar g;
    // ---- the wide staging client (WVM): one burst a position row, sectors [xrow / 8, xrow / 8 + nchunk)
    reg w_go; reg [14:0] w_s0; wire w_done, w_fault; reg [1:0] wfl;
    wire [31:0] wd_v; wire [32*15-1:0] wd_sec; wire [32*256-1:0] wd_dat;
    reg  [31:0] xv_l; reg [32*15-1:0] xs_l; reg [32*256-1:0] xd_l;   // the deliveries rotated to x lanes (registered)
    generate if (WVM) begin : g_wvm
        ot_hgi_vm_wrd #(.LQ(WLQ), .D(WD), .SW(15), .MUT(MUT_WV >= 2 ? MUT_WV - 1 : 0)) u_wrd (.clk(clk), .rst_n(rst_n), .start(w_go), .s0(w_s0),
            .ns({1'b0, nchunk[14:0]}), .busy(), .done(w_done), .fault(w_fault), .req(rg_req), .gnt(rg_gnt), .q(wrq), .cr(wrq_cr), .rsp(wrr),
            .d_v(wd_v), .d_sec(wd_sec), .d_data(wd_dat));
        always @(posedge clk) begin : rot
            integer l, b;
            for (l = 0; l < 32; l = l + 1) begin
                b = (l + w_s0[4:0] + (MUT_WV == 1 ? 1 : 0)) % 32;
                xv_l[l] <= wd_v[b]; xs_l[l*15 +: 15] <= wd_sec[b*15 +: 15]; xd_l[l*256 +: 256] <= wd_dat[b*256 +: 256];
            end
        end
    end else begin : g_nowvm
        assign rg_req = 1'b0; assign wrq = '0; assign w_done = 1'b0; assign w_fault = 1'b0; assign wd_v = '0; assign wd_sec = '0; assign wd_dat = '0;
        always @* begin xv_l = '0; xs_l = '0; xd_l = '0; end
    end endgenerate
    localparam integer XD = RMAX * PMAX, XAW = $clog2(XD);
    // per macro (16 lanes): the first lane of a wave present (its sector gives the wave's row)
    reg [3:0] xl_f [0:1];
    always @* for (integer mm = 0; mm < 2; mm = mm + 1) begin
        xl_f[mm] = 4'd0;
        for (integer ll = 15; ll >= 0; ll = ll - 1) if (xv_l[mm*16 + ll]) xl_f[mm] = 4'(ll);
    end
    localparam integer USE_XM = XMACRO && ((W * 16) % 256 == 0) && XD <= 1024;
    generate for (g = 0; g < 8; g = g + 1) begin : g_xr
        wire [2:0] qk = g[2:0] + xrow[2:0];                     // the sector word whose element lands in bank g
        wire [29:0] ek = {rsec, qk} - {12'd0, xrow};
        wire ok = x_land && ek < {9'd0, nchunk, 3'b000};
        wire [XAW-1:0] wa = xwo + ((ek >> 3) >> LW);           // position p's word p R + chunk / W
        wire [LW-1:0] wl = (ek >> 3) & (W - 1);
        if (USE_XM) begin : g_m
            // W / 16 macros, 16 lanes a 256-b row; one lane written an edge (16-b mask), a whole word read an edge
            genvar gm;
            for (gm = 0; gm < W / 16; gm = gm + 1) begin : g_mm
                wire [255:0] ro;
                wire we = ok && (wl >> 4) == gm;
                // a wide wave: the 16 lanes of this macro's row, all at word xwo + wave (one row an edge)
                // the wave covers x lanes [c mod W, + 32) of word c / W (c = the wave's chunks, 32-aligned): this macro
                // (lanes gm 16 ..) takes rotated half gm % 2 when gm / 2 == (c mod W) / 32
                wire [14:0] wcw = xs_l[((gm % 2)*16 + xl_f[gm % 2])*15 +: 15] - w_s0;
                wire ww = (WVM != 0) && |xv_l[(gm % 2)*16 +: 16] && ((W <= 32) || ((wcw >> 5) % (W / 32)) == (gm >> 1));
                wire [255:0] wwd, wwm;
                for (genvar ll = 0; ll < 16; ll = ll + 1) begin : g_wl
                    assign wwd[ll*16 +: 16] = xd_l[((gm % 2)*16 + ll)*256 + 32*g + 16 +: 16];
                    assign wwm[ll*16 +: 16] = {16{xv_l[(gm % 2)*16 + ll]}};
                end
                ot_sram_1r1w_1024x256_m2_r2c2 u_x (.clk(clk), .r_ce_in(x_re[g]), .r_addr_in(10'(x_addr[g*AW +: AW])),
                    .rd_out(ro), .w_ce_in(we || ww), .w_addr_in(ww ? 10'(xwo + XAW'(wcw >> LW)) : 10'(wa)),
                    .wd_in(ww ? wwd : {16{vr[32*qk + 16 +: 16]}}),
                    .w_mask_in(ww ? wwm : ({240'd0, 16'hFFFF} << {wl[3:0], 4'd0})), .rr_en(2'b00), .rr_addr(18'd0),
                    .cr_en(2'b00), .cr_sel(16'd0));
                always @* xq1[g*W*16 + gm*256 +: 256] = ro;
            end
        end else begin : g_f
            genvar gl;
            for (gl = 0; gl < W; gl = gl + 1) begin : g_l
                reg [15:0] m [0:XD-1];
                // wide landing: x lane gl's sector this edge (chunk c = sector - s0 -> word xwo + c / 32, element g)
                wire [14:0] wc = xs_l[(gl % 32)*15 +: 15] - w_s0;     // rotated lane gl mod 32's chunk
                always @(posedge clk) begin
                    if (ok && wl == gl) m[wa] <= vr[32*qk + 16 +: 16];
                    if (WVM != 0 && xv_l[gl % 32] && (W <= 32 || ((wc >> 5) % (W / 32)) == (gl >> 5)))
                        m[xwo + XAW'(wc >> LW)] <= xd_l[(gl % 32)*256 + 32*g + 16 +: 16];
                    if (x_re[g]) xq1[g*W*16 + gl*16 +: 16] <= m[x_addr[g*AW +: AW] & (XD - 1)];
                end
            end
        end
    end endgenerate
    always @(posedge clk) begin xd <= xq1; wd <= wq; end
    reg h_cv; wire h_cr, h_ov, h_last, h_fault, h_idle; wire [31:0] h_od;
    wire [$clog2(PMAX)-1:0] h_opos;
    ot_hdc_v41x_hcp #(.W(W), .TL(TW), .PMAX(PMAX), .OMAX(2), .AW(AW), .CW(16), .ML(2)) u_hcp (.clk(clk), .rst_n(rst_n),
        .cmd_valid(h_cv), .cmd_ready(h_cr), .cmd_npos(npos[$clog2(PMAX):0]), .cmd_nout(2'd1), .cmd_nchunk(nchunk[15:0]),
        .cmd_scale(1'b1), .cmd_nf(nf), .cmd_eps(eps), .cmd_wbase(16'd0), .cmd_xbase(16'd0),
        .w_re(w_re), .w_addr(w_addr), .w_data(wd), .x_re(x_re), .x_addr(x_addr), .x_data(xd),
        .o_valid(h_ov), .o_ready(1'b1), .o_pos(h_opos), .o_idx(), .o_data(h_od), .o_last(h_last), .fault(h_fault),
        .idle(h_idle));

    // ---- the weight APERTURE (HSRC = 1): slot s, bank k, sector position q: one 128x256 SRAM, row = word r
    localparam integer BSEC = RMAX * W / 8;                // sectors a bank in a slot (the aperture layout fixes 512)
    reg [12:0] ap_cnt [0:1];                               // sectors written into slot s since it was last released
    reg ap_job, ap_slot;                                   // this record reads slot ap_slot
    wire [2*8*SPW-1:0] apm_we; wire [2*8*SPW*256-1:0] apm_rd;
    reg [6:0] apm_wa [0:2*8*SPW-1]; reg [255:0] apm_wd [0:2*8*SPW-1], apm_wm [0:2*8*SPW-1]; reg [2*8*SPW-1:0] apm_wv;
    generate if (HSRC != 0) begin : g_ap
        for (genvar am = 0; am < 2 * 8 * SPW; am = am + 1) begin : g_apm
            localparam integer AS = am / (8 * SPW), AK = (am / SPW) % 8, AQ = am % SPW;
            ot_sram_1r1w_128x256_m1_r2c2 u_a (.clk(clk), .r_ce_in(w_re[AK] && ap_job && ap_slot == AS),
                .r_addr_in(7'(w_addr[AK*AW +: AW])), .rd_out(apm_rd[am*256 +: 256]), .w_ce_in(apm_wv[am]),
                .w_addr_in(apm_wa[am]), .wd_in(apm_wd[am]), .w_mask_in(apm_wm[am]), .rr_en(2'b00), .rr_addr(14'd0),
                .cr_en(2'b00), .cr_sel(16'd0));
        end
        // lane k: pin flop -> its bank's macro (slot, position) the next edge; the credit returns with the write
        reg [7:0] al_v; reg [277:0] al_d [0:7];
        always @(posedge clk) for (integer k2 = 0; k2 < 8; k2 = k2 + 1) al_d[k2] <= ap_q[k2*278 +: 278];
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin al_v <= '0; ap_cr <= '0; ap_done <= '0; apm_wv <= '0; ap_cnt[0] <= '0; ap_cnt[1] <= '0;
                              ap_ovf <= 1'b0; end
            else begin : apw
                reg [12:0] s; integer k2, mi; reg [12:0] add0, add1;
                add0 = '0; add1 = '0; apm_wv <= '0;
                for (k2 = 0; k2 < 8; k2 = k2 + 1) al_v[k2] <= ap_q[k2*278 + 277];
                ap_cr <= al_v; ap_done <= ap_cr;
                for (k2 = 0; k2 < 8; k2 = k2 + 1) if (al_v[k2]) begin
                    s = al_d[k2][276:264];
                    if (s[11:9] != k2[2:0]) ap_ovf <= 1'b1;          // a sector on the wrong bank's lane: fail closed
                    mi = s[12] * 8 * SPW + k2 * SPW + (s[8:0] % SPW);
                    apm_wv[mi] <= 1'b1; apm_wa[mi] <= 7'(s[8:0] / SPW); apm_wd[mi] <= al_d[k2][263:8];
                    apm_wm[mi] <= {{32{al_d[k2][7]}}, {32{al_d[k2][6]}}, {32{al_d[k2][5]}}, {32{al_d[k2][4]}},
                                   {32{al_d[k2][3]}}, {32{al_d[k2][2]}}, {32{al_d[k2][1]}}, {32{al_d[k2][0]}}};
                    if (!(MUT_AP != 0 && k2 == 7)) begin if (s[12]) add1 = add1 + 1'b1; else add0 = add0 + 1'b1; end
                end
                // a slot's count clears when the record that read it retires (the next fill waits for that retire)
                ap_cnt[0] <= ((ap_rel && !ap_slot) ? 13'd0 : ap_cnt[0]) + add0;
                ap_cnt[1] <= ((ap_rel && ap_slot) ? 13'd0 : ap_cnt[1]) + add1;
            end
        end
    end else begin : g_noap
        always @* begin ap_cr = '0; ap_done = '0; ap_ovf = 1'b0; ap_cnt[0] = '0; ap_cnt[1] = '0; end
        assign apm_rd = '0;
    end endgenerate
    reg ap_ovf;
    reg ap_rel;                                            // the aperture record retires (its slot is free again)
    wire [12:0] ap_need = 13'(8 * rr * SPW);               // sectors of the record's row (8 banks x R words)
    reg ap_rq;                                             // the HCP read the aperture (rom_q comes from it next edge)

    // ---- the weight windows and the HBM lanes
    // STRIPED FETCH (hgi-1010/d): bank g's R words are split into SPL sub-windows of RS = ceil(R / SPL) consecutive words
    // (window g SPL + k holds words [k RS, (k + 1) RS) of bank g; contiguous in HBM, so the weight-set format is
    // unchanged); every window fills through its own HBM lane (HL = 8 SPL), so a row's weights arrive 8 SPL sectors an
    // edge.  The HCP reads bank g's word w from window g SPL + (w / RS) (registered select of the window's rom_q).
    localparam integer NW = 8 * SPL, SWD = (RMAX + SPL - 1) / SPL;     // windows; words a window
    reg w_start, w_rel; wire [NW-1:0] w_rdy0, w_flt, wq_v; reg [NW-1:0] wq_ack;
    wire [NW*HAW-1:0] wq_addr; wire [NW*3-1:0] wq_len; wire [NW*RTW-1:0] wq_tag;
    reg [17:0] rsw;                                       // RS (words a sub-window this row set), registered at S_PAR
    reg [CWW-1:0] nwk [0:SPL-1];                          // words of sub-window k
    reg [AW-1:0] bnd [0:SPL-1]; reg [HAW-1:0] soff [0:SPL-1];   // k RS (its first word), k RS SPW (its HBM offset)
    wire [NW-1:0] w_rdy = w_rdy0;
    // responses, registered per lane (lane 0 also returns the parameter sectors, tag source 8)
    reg [HL-1:0] hr_vl; reg [HL*TG-1:0] hr_tl; reg [HL*2-1:0] hr_bl; reg [HL*256-1:0] hr_dl;
    always @(posedge clk) begin hr_tl <= hr_tag; hr_bl <= hr_beat; hr_dl <= hr_data; end
    always @(posedge clk or negedge rst_n) if (!rst_n) hr_vl <= '0; else hr_vl <= hr_v;
    wire hr_vq = hr_vl[0]; wire [TG-1:0] hr_tq = hr_tl[TG-1:0]; wire [1:0] hr_bq = hr_bl[1:0]; wire [255:0] hr_dq = hr_dl[255:0];
    wire [NW*W*32-1:0] wqs;
    generate for (g = 0; g < NW; g = g + 1) begin : g_win
        wire [3:0] why; wire [CWW-1:0] fetched; wire [31:0] rcv; wire rdy_i;
        localparam integer GB = g / SPL, GK = g % SPL;   // bank, sub-window
        // this window's HBM lane (mutant: window 3 listens on lane 4, whose sectors it never asked for); with one lane
        // a window to itself the tag source only tells windows from the parameter fetch
        localparam integer LN = (HL == 1) ? 0 : (MUT_HL != 0 && g == 3) ? 4 : g;
        wire src_ok = (HL == 1) ? (hr_tl[LN*TG + TG-1 -: 4] == g) : (hr_tl[LN*TG + TG-1 -: 4] != 4'd8);
        wire empty = (nwk[GK] == 0);
        wire [AW-1:0] la = w_addr[GB*AW +: AW] - bnd[GK];
        ot_hdc_v41x_weight_window #(.WB(W*32), .SB(256), .WORDS(SWD), .AW(AW), .HAW(HAW), .NPC(1), .LENW(3), .BURST_MAX((W / 8 > 4) ? 4 : W / 8), .MACRO(WMACRO)) u_w (
            .clk(clk), .rst_n(rst_n), .start(w_start && !empty), .release_window(w_rel && !empty), .rom_base(16'd0),
            .hbm_base(rowbase + boff[GB] + soff[GK]), .nwords(nwk[GK]), .ready(rdy_i), .hq_v(wq_v[g]),
            .hq_rdy(wq_ack[g]), .hq_addr(wq_addr[g*HAW +: HAW]), .hq_len(wq_len[g*3 +: 3]), .hq_tag(wq_tag[g*RTW +: RTW]),
            .hr_v(hr_vl[LN] && src_ok), .hr_rdy(), .hr_tag(hr_tl[LN*TG +: RTW]), .hr_beat(hr_bl[LN*2 +: 2]),
            .hr_data(hr_dl[LN*256 +: 256]), .rom_re(w_re[GB] && wsel[GB] == GK && !ap_job), .rom_addr(la),
            .rom_q(wqs[g*W*32 +: W*32]), .fault(w_flt[g]), .fault_why(why), .fetched_words(fetched), .received_sectors(rcv));
        assign w_rdy0[g] = empty || rdy_i;
    end endgenerate
    // the HCP's read of bank g: sub-window wsel = w / RS (comparators against k RS), its rom_q one edge later
    reg [3:0] wsel [0:7]; reg [3:0] wsel_q [0:7];
    always @* for (integer gg = 0; gg < 8; gg = gg + 1) begin
        wsel[gg] = 4'd0;
        for (integer kk = 1; kk < SPL; kk = kk + 1) if (w_addr[gg*AW +: AW] >= bnd[kk]) wsel[gg] = 4'(kk);
    end
    always @(posedge clk) for (integer gg = 0; gg < 8; gg = gg + 1) if (w_re[gg]) wsel_q[gg] <= wsel[gg];
    for (g = 0; g < 8; g = g + 1) begin : g_wq
        wire [W*32-1:0] apw;
        for (genvar q2 = 0; q2 < SPW; q2 = q2 + 1) begin : g_apq
            assign apw[q2*256 +: 256] = apm_rd[((ap_slot ? 1 : 0) * 8 * SPW + g * SPW + q2)*256 +: 256];
        end
        assign wq[g*W*32 +: W*32] = (HSRC != 0 && ap_job) ? apw : wqs[(g*SPL + wsel_q[g])*W*32 +: W*32];
    end
    reg p_req; reg [31:0] pw [0:31]; reg [3:0] p_got;
    // request register a lane: lowest-index window of the lane first, then (lane 0) the parameter fetch (source 8)
    integer k, l;
    function automatic on_lane(input integer win, input integer ln);
        on_lane = (HL == 1) || (win == ln);
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hq_v <= '0; hq_addr <= '0; hq_len <= '0; hq_tag <= '0; end
        else for (l = 0; l < HL; l = l + 1) if (!hq_v[l] || hq_rdy[l]) begin : pick
            reg f; f = 1'b0;
            hq_v[l] <= 1'b0;
            for (k = 0; k < NW; k = k + 1)
                if (!f && wq_v[k] && on_lane(k, l)) begin
                    f = 1'b1; hq_v[l] <= 1'b1; hq_addr[l*HAW +: HAW] <= wq_addr[k*HAW +: HAW];
                    hq_len[l*3 +: 3] <= wq_len[k*3 +: 3];
                    hq_tag[l*TG +: TG] <= {(HL == 1) ? k[3:0] : 4'd0, wq_tag[k*RTW +: RTW]};
                end
            if (l == 0 && !f && p_req) begin
                hq_v[0] <= 1'b1; hq_addr[0 +: HAW] <= pbase; hq_len[0 +: 3] <= 3'd4; hq_tag[0 +: TG] <= {4'd8, {RTW{1'b0}}};
            end
        end
    end
    reg ack_f;
    always @* begin
        wq_ack = '0;
        for (l = 0; l < HL; l = l + 1) begin
            ack_f = 1'b0;
            if (!hq_v[l] || hq_rdy[l])
                for (k = 0; k < NW; k = k + 1) if (!ack_f && wq_v[k] && on_lane(k, l)) begin ack_f = 1'b1; wq_ack[k] = 1'b1; end
        end
    end
    wire p_iss = (!hq_v[0] || hq_rdy[0]) && p_req && !(|(wq_v & ((HL == 1) ? {NW{1'b1}} : {{(NW-1){1'b0}}, 1'b1})));

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

    assign x_land = (st == S_STAGE) && vr[273] && !vr[256];
`ifdef HC_DBG
    reg flt_q; always @(posedge clk) begin flt_q <= flt; if (flt && !flt_q) $display("HC_DBG flt rises st %0d pc %0d row %0d", st, pc, row); end
`endif
    // ---- control
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
            flt <= 1'b0; vo_n <= 3'd0; p_got <= 4'd0; wpre <= 1'b0; wst <= 1'b0; w_go <= 1'b0; wfl <= 2'd0;
            ap_rel <= 1'b0; ap_job <= 1'b0; ap_slot <= 1'b0;
        end else begin
            job_done <= 1'b0; job_fault <= 1'b0; vmq[337] <= 1'b0; w_start <= 1'b0; w_rel <= 1'b0; w_go <= 1'b0;
            ap_rel <= 1'b0;
            if (ap_ovf) flt <= 1'b1;
            // wide landing: every staged element must be BF16-valued (the golden's assertion), as on the packet path
            if (w_fault) flt <= 1'b1;
            if (WVM != 0) for (q = 0; q < 32; q = q + 1)
                if (xv_l[q] && (xd_l[q*256 +: 256] & {8{32'h0000FFFF}}) != 256'd0) flt <= 1'b1;
            if (wpre) begin wpre <= 1'b0; w_start <= 1'b1; wst <= 1'b1; end
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
`ifdef HC_DBG
            if (!flt && (ex_f || dv_f || |w_flt || h_fault || sk_fault || (mu_o && mu_e != 0) || (ad_o && ad_e != 0)))
                $display("HC_DBG fault st %0d pc %0d row %0d ex %0d dv %0d w %h h %0d sk %0d mu %0d ad %0d", st, pc, row, ex_f,
                         dv_f, w_flt, h_fault, sk_fault, mu_o && mu_e != 0, ad_o && ad_e != 0);
`endif
            if (flt && st != S_FAULT && st != S_IDLE) st <= S_FAULT;
            else case (st)
                S_IDLE: if (job_v && job_rdy) begin
                    job_rdy <= 1'b0;
                    nchunk <= job[23:6]; nf <= job[56:25]; eps <= job[88:57]; xbase <= job[122:105];
                    wsec <= job[157:123]; obase <= job[199:182]; op <= job[201:200]; row0 <= job[206:202];
                    nrows <= job[211:207]; ap_job <= (HSRC != 0) && job[228]; ap_slot <= job[227];
                    npos <= j_np; astr <= j_as; ostr <= j_os; pc <= 4'd0; xrow <= job[122:105]; orow <= job[199:182];
                    xwo <= 0;
                    st <= S_GEO;
                end
                S_GEO: begin                                         // R, RS, row stride, parameter base
                    rr <= (nchunk + W - 1) >> LW;
                    st <= S_GEO2;
                end
                S_GEO2: begin
                    rs <= {{(HAW-18){1'b0}}, rr} << LS;
                    rsw <= (rr + SPL - 1) / SPL;                     // SPL a power of two: a shift
                    rowstride <= {{(HAW-18){1'b0}}, rr} << (LS + 3);
                    pbase <= wsec[HAW-1:0];
                    rowbase <= wsec[HAW-1:0] + 4 + (({{(HAW-18){1'b0}}, rr} << (LS + 3)) * row0);
                    rend <= row0 + nrows - 5'd1;
                    if (op != 2'd2 && (rr > RMAX || rr == 0)) flt <= 1'b1;
                    st <= S_PAR;
                end
                S_PAR: begin
                    for (q = 0; q < 8; q = q + 1) boff[q] <= rs * q;
                    for (q = 0; q < SPL; q = q + 1) begin bnd[q] <= AW'(rsw * q); soff[q] <= HAW'(rsw * q * SPW); end
                    for (q = 0; q < SPL; q = q + 1)
                        nwk[q] <= ({1'b0, rr} > rsw * q) ? (({1'b0, rr} - rsw * q > {1'b0, rsw}) ? CWW'(rsw) : CWW'(rr - rsw * q)) : '0;
                    wpre <= (op != 2'd2) && !ap_job;                 // the first row's weights stream during x staging
                    p_req <= (op != 2'd1); p_got <= 4'd0;
                    sec <= xrow >> 3; rsec <= xrow >> 3;
                    sec_end <= (op == 2'd2) ? ({9'd0, xrow} + 27'd23) >> 3 : ({9'd0, xrow} + {6'd0, nchunk, 3'd0} - 27'd1) >> 3;
                    vo_n <= 3'd0; st <= (op == 2'd2) ? S_LDA : S_STAGE;
                    if (WVM != 0 && op != 2'd2 && xrow[2:0] == 3'd0) begin   // wide staging: 32 sectors an edge
                        w_go <= 1'b1; w_s0 <= 15'(xrow >> 3); st <= S_WST;
                    end
                end
                S_WST: if (w_done) begin wfl <= 2'd0; st <= S_WFL; end
                S_WFL: if (wfl == 2'd2) begin                         // the last deliveries rotated and landed
                    if (pc + 4'd1 < npos) begin
                        pc <= pc + 4'd1; xrow <= xrow + astr; xwo <= MUT_MP ? xwo : xwo + rr[AW-1:0];
                        if (((xrow + astr) & 18'd7) == 18'd0) begin w_go <= 1'b1; w_s0 <= 15'((xrow + astr) >> 3); st <= S_WST; end
                        else begin                                    // an unaligned row: the packet path
                            sec <= (xrow + astr) >> 3; rsec <= (xrow + astr) >> 3; vo_n <= 3'd0;
                            sec_end <= ({9'd0, xrow + astr} + {6'd0, nchunk, 3'd0} - 27'd1) >> 3; st <= S_STAGE;
                        end
                    end else begin pc <= 4'd0; row <= row0; st <= S_ROW; end
                end else wfl <= wfl + 2'd1;
                S_LDA: begin                                         // op 2: the 24 gathered mixes -> T
                    if (vo_n < 3'd4 && sec <= sec_end) begin
                        vmq <= {1'b1, 1'b0, sec, 5'd0, 256'd0, 32'd0, 16'h4845};
                        sec <= sec + 27'd1;
                    end
                    if (vr[273] && !vr[256]) begin
                        for (q = 0; q < 8; q = q + 1) begin
                            e2 = {rsec, q[2:0]} - xrow;
                            if (e2 >= 0 && e2 < 24) T[e2] <= vr[32*q +: 32];
                        end
                        rsec <= rsec + 27'd1;
                    end
                    vo_n <= vo_n + ((vo_n < 3'd4 && sec <= sec_end) ? 3'd1 : 3'd0) - ((vr[273] && !vr[256]) ? 3'd1 : 3'd0);
                    if (rsec > sec_end && vo_n == 3'd0 && p_got == 4'd4) begin i <= 5'd0; iss_done <= 1'b0; st <= S_P1; end
                end
                S_STAGE: begin                                       // A sectors -> x banks, 4 outstanding
                    if (vo_n < 3'd4 && sec <= sec_end) begin
                        vmq <= {1'b1, 1'b0, sec, 5'd0, 256'd0, 32'd0, 16'h4843};
                        sec <= sec + 27'd1;
                    end
                    if (vr[273] && !vr[256]) begin
                        for (q = 0; q < 8; q = q + 1) begin
                            e2 = {rsec, q[2:0]} - xrow;              // element index of word q
                            if (e2 >= 0 && e2 < {nchunk, 3'b000} && vr[32*q +: 16] != 16'd0) flt <= 1'b1;   // BF16
`ifdef HC_DBG
                            if (e2 >= 0 && e2 < {nchunk, 3'b000} && vr[32*q +: 16] != 16'd0)
                                $display("HC_DBG bf16 pc %0d rsec %0d q %0d xrow %0d e2 %0d word %h", pc, rsec, q, xrow, e2, vr[32*q +: 32]);
`endif
                        end
                        rsec <= rsec + 27'd1;
                    end
                    vo_n <= vo_n + ((vo_n < 3'd4 && sec <= sec_end) ? 3'd1 : 3'd0) - ((vr[273] && !vr[256]) ? 3'd1 : 3'd0);
                    if (rsec > sec_end && vo_n == 3'd0) begin                 // lanes past K / 8: HCP-masked
                        if (pc + 4'd1 < npos) begin                            // the next position's row of A
                            pc <= pc + 4'd1; xrow <= xrow + astr; xwo <= MUT_MP ? xwo : xwo + rr[AW-1:0];
                            sec <= (xrow + astr) >> 3; rsec <= (xrow + astr) >> 3;
                            sec_end <= ({9'd0, xrow + astr} + {6'd0, nchunk, 3'd0} - 27'd1) >> 3;
                        end else begin pc <= 4'd0; row <= row0; st <= S_ROW; end
                    end
                end
                S_ROW: if (ap_job) begin                                // the aperture: wait for the slot's row
                    if (ap_cnt[ap_slot] >= ap_need) st <= S_RW;
                end else if (p_got == 4'd4 || op == 2'd1) begin w_start <= !wst; wst <= 1'b0; st <= S_RW; end
                S_RW: if ((ap_job || &w_rdy) && h_cr) begin h_cv <= 1'b1; st <= S_RC; end
                S_RC: begin
                    if (h_cv && h_cr) h_cv <= 1'b0;
                    if (h_ov) begin                                    // one result a position, positions in order
                        TP[{1'b0, h_opos} * 24 + (row - row0)] <= h_od;
                        if (h_last) begin w_rel <= !ap_job; st <= S_REL; end
                    end
                end
                S_REL: begin
                    rowbase <= rowbase + rowstride;
                    if (row == rend) begin pc <= 4'd0; st <= S_PL; end
                    else begin row <= row + 5'd1; st <= S_ROW; end
                end
                S_PL: begin                                          // position pc's raw mixes -> T, then post / drain
                    for (q = 0; q < 24; q = q + 1) T[q] <= TP[{1'b0, pc} * 24 + q];
                    if (op == 2'd1) begin
                        sec <= orow >> 3; sec_end <= ({9'd0, orow} + {22'd0, nrows} - 27'd1) >> 3; vo_n <= 3'd0;
                        st <= S_DRAIN;
                    end else begin i <= 5'd0; iss_done <= 1'b0; st <= S_P1; end
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
                        sec <= orow >> 3; sec_end <= ({9'd0, orow} + 27'd23) >> 3; vo_n <= 3'd0; st <= S_DRAIN;
                    end
                end
                S_DRAIN: begin                                       // word-masked sector writes of the 24 results
                    if (vo_n < 3'd4 && sec <= sec_end) begin : dr
                        reg [255:0] dat; reg [31:0] msk; integer j;
                        dat = 256'd0; msk = 32'd0;
                        for (q = 0; q < 8; q = q + 1) begin
                            j = {sec, q[2:0]} - orow;
                            if (j >= 0 && j < ((op == 2'd1) ? {27'd0, nrows} : 24)) begin
                                dat[32*q +: 32] = T[j]; msk[4*q +: 4] = 4'hF; end
                        end
                        vmq <= {1'b1, 1'b1, sec, 5'd0, dat, msk, 16'h4844};
                        sec <= sec + 27'd1;
                    end
                    vo_n <= vo_n + ((vo_n < 3'd4 && sec <= sec_end) ? 3'd1 : 3'd0) - ((vr[273] && vr[256]) ? 3'd1 : 3'd0);
                    if (sec > sec_end && vo_n == 3'd0) begin
                        if (pc + 4'd1 < npos) begin                        // the next position
                            pc <= pc + 4'd1; orow <= orow + ostr;
                            if (op == 2'd2) begin                          // op 2: its 24 gathered mixes
                                xrow <= xrow + astr; sec <= (xrow + astr) >> 3; rsec <= (xrow + astr) >> 3;
                                sec_end <= ({9'd0, xrow + astr} + 27'd23) >> 3; vo_n <= 3'd0; st <= S_LDA;
                            end else st <= S_PL;
                        end else st <= S_DONE;
                    end
                end
                S_DONE: begin job_done <= 1'b1; job_rdy <= 1'b1; st <= S_IDLE; ap_rel <= ap_job; end
                S_FAULT: begin job_fault <= 1'b1; st <= S_IDLE; job_rdy <= 1'b0; end   // the adapter halts
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
