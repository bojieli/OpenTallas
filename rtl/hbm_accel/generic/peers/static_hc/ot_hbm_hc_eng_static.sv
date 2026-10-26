`timescale 1ns/1ps
`default_nettype none
// Static HC engine, die master hc_eng (H-NETLIST/hceng 2026-10-16). Full-form HC.HC_MIX per die, designed top-down to
// the 1,160-cycle price (24 rows x K 20,480 FP32 weights x P <= 8 positions + norm + sigmoid/Sinkhorn tail):
//   PROJECTION  ot_hdc_v41x_hcp_sys1_static (codex a35449ada static-calendar HCP core, W = 256: 2,048 FP32 MAC
//               lanes) + 8 bank tiles ot_hbm_hc_bank_static (term k stage, 32 hard lane leaves, 32 weight + 16 x
//               macros). Per position: ss run + 24 rows, R = 10 runs each = 250 issue cycles; mix = csum(fn.x) * r,
//               r = rsqrt(ss / K + eps) (tools/hdc_golden_v41 Model.hc_mixes, chunk8: bit-exact csum tree order).
//   TAIL        2 x ot_hbm_hc_tail_unit_static (codex exact tail + derived /7 Sinkhorn clock, fixed latency L), so a
//               position's tail (~496 edges) overlaps the next positions' projection (250 edges each).
//   MIX STORE   8 positions x 24 FP32 mixes; written by the projection (full form) or by gathered-mix words from the
//               quadrant clients (G22 form: rows computed elsewhere, gathered through the VM).
//   TABLE       bases[24]/scales[3] per (layer, attn|ffn) set: one 1024x256 macro, set s = rows 4s..4s+3 (rows 0..2
//               bases, row 3 scales in [95:0]); written by the host programme target tbl_* port before a launch.
//   INGRESS     4 quadrant x_wave ports (hc_<q>.x_wave: 32 sectors = 8,192 b every 4 edges from the quadrant's far HC
//               LG tap). ONE wave lands per edge (compiler staggers the 4 readers by phase); a wave is either a
//               residual wave (32 chunks of 8 BF16-valued binary32: x macros, word p*R + r) or a WEIGHT wave (32 chunks
//               of fn row o: weight macros, word slot*256 + o*R + r). Weights of the next (layer, set) reach the VM by
//               the existing DMA.LOAD / kshare VM fill and are moved here by the hc_<q> readers in the background
//               (1,920 waves = 1,920 edges a set); 4 weight slots in the macros.
//   PROGRAMME   ot_hbm_hc_eng_seq_static event words (host target collar ot_static_program_target); events:
//               ingest start (quadrant q expects `count` waves every 4 edges, the first on the edge after the event
//               edge + 1), gathered-mix window, projection launch, raw pop (calendar_pop), mix-clear, table fetch,
//               tail launch (unit, position), emit (unit -> result pins of the quadrants in qmask).
// COLLAR FOLD (H-DIE option A, 0600): the two F20 targets (ot_static_program_target TGT_PIN=1) are inside: programme
// id = strap tgt, table id = tgt + 1 (die straps 164/165). Table rows carry the F20 row header in [255:224], so a
// row holds 7 FP32 words [223:0]: set s = rows 4s..4s+3, base i at row i/7 word i%7 (i = 0..23), scale j at row 3
// word 3+j. Exposes configured (programme target) and folds both target faults into fault.
// X_WAVE LINK (0600): XW_BEATS=4 -> per quadrant 2,048-b beats (ot_hbm_hc_xw_rx_static, pin flops inside), the
// reassembled wave is visible on the same edge as the BEATS=1 pin flop (compiler wave-landing constant unchanged).
// STATIC: no ready, credit, grant or backpressure; every event is a programme time; a wave missing on its due edge, an
// unsolicited wave, a wrong word index, a residual word with nonzero low half, a pop the core cannot honour, a tail
// launch with any of its 24 mixes unwritten or an emit before the unit's fixed result edge raises fault.
// Pin registers: every input lands in a pin flop (x_wave/gm/tbl/cfg/start), every output is a flop.
// Fixed latencies (measured by tb_hbm_hc_eng_static): see results/rtl/hbm_hc_eng_0030/receipt.json.
// MUT (bench): 1 = bank 3 weight slice rotated, 2 = tail pre-sigmoid eps dropped (unit 0), 3 = x landing one run off.
module ot_hbm_hc_eng_static #(
    parameter integer K    = 20480,
    parameter [31:0]  NF   = 32'h46a00000,       // binary32(K)
    parameter integer DRLY = 1,                  // relay registers core <-> bank 0 / bank 7
    parameter integer XW_BEATS = 4,              // x_wave link beats (1 = original 8,192-b form)
    parameter integer MUT  = 0
)(
    input  wire           clk, rst_n,
    // F20 programme bus (folded targets: programme id tgt, table id tgt + 1)
    input  wire [7:0]     tgt,
    input  wire           cfg_v,
    input  wire [7:0]     cfg_target,
    input  wire [11:0]    cfg_addr,
    input  wire [255:0]   cfg_data,
    input  wire           desc_v,
    input  wire [11:0]    desc_base,
    input  wire [12:0]    desc_limit,
    input  wire [15:0]    desc_loops,
    input  wire           launch_v,
    output wire           configured,
    // quadrant clients hc_<q> (q = 0..3 = SW, SE, NW, NE)
    input  wire [3:0]     x_wave_v,
    input  wire [39:0]    x_wave_word,
    input  wire [4*8192/XW_BEATS-1:0] x_wave,
    input  wire [7:0]     x_wave_beat,
    input  wire [3:0]     gathered_mix_v,
    input  wire [19:0]    gathered_mix_row,
    input  wire [11:0]    gathered_mix_pos,
    input  wire [127:0]   gathered_mix_data,
    output reg  [3:0]     result_v,
    output reg  [11:0]    result_position,
    output reg  [3071:0]  result,
    output reg            program_active, program_done, fault
);
    localparam integer W = 256, AW = 10, R = K / (8 * W), WPR = K / 256, NJ = W / 32;
    localparam integer LM = 8, LA = 7, SOR = 1, ML = 2;
    localparam integer SYS_LAT = 1 + 7 * (LA + 1 + SOR) + 3 + 2 + (ML - 2) + LM + LA + SOR + 2 * DRLY;
    localparam integer NVW = $clog2(W) + 1;
    initial if (K % (8 * W) != 0 || R > 16 || WPR > 127) $fatal(1, "K must be a multiple of 2,048, <= 32,768");

    // ------------------------------------------------------------------ pin registers
    wire [3:0] xv_q; wire [39:0] xw_q; wire [32767:0] xd_q; wire [3:0] rx_fault;
    genvar gx;
    for (gx = 0; gx < 4; gx = gx + 1) begin : g_rx
        ot_hbm_hc_xw_rx_static #(.BEATS(XW_BEATS)) u_rx (.clk(clk), .rst_n(rst_n), .x_v(x_wave_v[gx]),
            .x_beat(x_wave_beat[gx*2 +: 2]), .x_word(x_wave_word[gx*10 +: 10]),
            .x_data(x_wave[gx*(8192/XW_BEATS) +: 8192/XW_BEATS]), .wave_v(xv_q[gx]), .wave_word(xw_q[gx*10 +: 10]),
            .wave(xd_q[gx*8192 +: 8192]), .fault(rx_fault[gx]));
    end
    reg [3:0] gv_q; reg [19:0] gr_q; reg [11:0] gp_q; reg [127:0] gd_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) gv_q <= 0; else gv_q <= gathered_mix_v;
    always @(posedge clk) begin
        gr_q <= gathered_mix_row; gp_q <= gathered_mix_pos; gd_q <= gathered_mix_data;
    end
    // ------------------------------------------------------------------ folded F20 targets (pin flops inside)
    wire cfg_we, start_v, tbl_we_q, ptgt_fault, ttgt_fault, seq_active;
    wire [9:0] p_addr, start_base, tbl_addr_q; wire [255:0] p_data, tbl_data_q;
    wire [10:0] start_limit; wire [15:0] start_loops;
    ot_static_program_target #(.PCW(10), .TGT_PIN(1)) u_ptgt (.clk(clk), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v),
        .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
        .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(seq_active),
        .program_cfg_we(cfg_we), .program_cfg_addr(p_addr), .program_cfg_data(p_data), .program_start_v(start_v),
        .program_start_base(start_base), .program_start_limit(start_limit), .program_start_loops(start_loops),
        .configured(configured), .fault(ptgt_fault));
    // table target: only its row-write port has a consumer (a table is data; a launch on id tgt + 1 is never issued)
    ot_static_program_target #(.PCW(10), .TGT_PIN(1)) u_ttgt (.clk(clk), .rst_n(rst_n), .tgt(tgt + 8'd1), .cfg_v(cfg_v),
        .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
        .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(seq_active),
        .program_cfg_we(tbl_we_q), .program_cfg_addr(tbl_addr_q), .program_cfg_data(tbl_data_q), .program_start_v(),
        .program_start_base(), .program_start_limit(), .program_start_loops(), .configured(), .fault(ttgt_fault));

    // ------------------------------------------------------------------ programme
    localparam integer EW = 124;
    wire [EW-1:0] ev; wire ev_v; wire [19:0] ev_t; wire seq_done, seq_fault;
    ot_hbm_hc_eng_seq_static #(.W(EW)) u_seq (.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(p_addr),
        .cfg_data(p_data), .start_v(start_v), .start_base(start_base), .start_limit(start_limit),
        .start_loops(start_loops), .event_word(ev), .event_v(ev_v), .t(ev_t), .active(seq_active), .done(seq_done),
        .fault(seq_fault));
    wire        e_ing   = ev_v && ev[20];
    wire [1:0]  e_ingq  = ev[22:21];
    wire        e_kind  = ev[23];
    wire [1:0]  e_slot  = ev[25:24];
    wire [4:0]  e_lo    = ev[30:26];
    wire [6:0]  e_w     = ev[37:31];
    wire [11:0] e_cnt   = ev[49:38];
    wire [9:0]  e_word  = ev[59:50];
    wire        e_gm    = ev_v && ev[60];
    wire [1:0]  e_gmq   = ev[62:61];
    wire        e_gmo   = ev[63];
    wire        e_launch= ev_v && ev[64];
    wire [3:0]  e_npos  = ev[68:65];
    wire [1:0]  e_wslot = ev[70:69];
    wire [31:0] e_eps   = ev[102:71];
    wire        e_pop   = ev_v && ev[103];
    wire        e_clear = ev_v && ev[104];
    wire        e_tf    = ev_v && ev[105];
    wire [6:0]  e_tset  = ev[112:106];
    wire        e_tl    = ev_v && ev[113];
    wire        e_tunit = ev[114];
    wire [2:0]  e_tpos  = ev[117:115];
    wire        e_emit  = ev_v && ev[118];
    wire [3:0]  e_qmask = ev[122:119];
    wire        e_eunit = ev[123];

    // ------------------------------------------------------------------ ingest sequencers (one per quadrant)
    reg [3:0] in_act, in_kind; reg [1:0] in_ph [0:3]; reg [1:0] in_slot [0:3]; reg [4:0] in_lo [0:3];
    reg [6:0] in_w [0:3]; reg [11:0] in_left [0:3]; reg [9:0] in_word [0:3];
    wire [3:0] due;
    genvar gq;
    for (gq = 0; gq < 4; gq = gq + 1) begin : g_due
        assign due[gq] = in_act[gq] && in_ph[gq] == 2'd0;
    end
    // the one due quadrant this edge (fault if more than one)
    reg [1:0] dq; reg dany, dmulti;
    always @* begin
        dq = 2'd0; dany = 1'b0; dmulti = 1'b0;
        for (integer q = 0; q < 4; q = q + 1) if (due[q]) begin if (dany) dmulti = 1'b1; dany = 1'b1; dq = 2'(q); end
    end
    wire [8191:0] wave = xd_q[dq*8192 +: 8192];
    wire [6:0] dw = in_w[dq];
    wire [3:0] drun = 4'(dw / NJ);
    wire [2:0] dj = 3'(dw % NJ);
    wire [9:0] dxaddr = 10'(in_lo[dq] * R + drun + ((MUT == 3) ? 1 : 0));
    wire [9:0] dwaddr = 10'(in_slot[dq] * 256 + in_lo[dq] * R + drun);
    reg lowbad;
    always @* begin
        lowbad = 1'b0;
        for (integer m = 0; m < 256; m = m + 1) lowbad = lowbad | (|wave[m*32 +: 16]);
    end
    // write stage (registered) -> bank tiles (their pin flops)
    reg b_wv, b_xv; reg [2:0] b_j; reg [9:0] b_a; reg [8191:0] b_d;
    reg ing_fault;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_act <= 0; b_wv <= 0; b_xv <= 0; ing_fault <= 0;
            for (integer q = 0; q < 4; q = q + 1) in_ph[q] <= 0;
        end else begin
            b_wv <= dany && in_kind[dq]; b_xv <= dany && !in_kind[dq];
            if (dmulti) ing_fault <= 1'b1;
            for (integer q = 0; q < 4; q = q + 1) begin
                if (xv_q[q] && !due[q]) ing_fault <= 1'b1;                        // unsolicited wave
                if (due[q]) begin
                    if (!xv_q[q] || xw_q[q*10 +: 10] != in_word[q]) ing_fault <= 1'b1;
                    in_word[q] <= in_word[q] + 1'b1;
                    in_left[q] <= in_left[q] - 1'b1;
                    if (in_left[q] == 12'd1) in_act[q] <= 1'b0;
                    if (in_w[q] == 7'(WPR - 1)) begin
                        in_w[q] <= 7'd0;
                        if (in_kind[q] && in_lo[q] == 5'd23) begin in_lo[q] <= 5'd0; in_slot[q] <= in_slot[q] + 1'b1; end
                        else in_lo[q] <= in_lo[q] + 1'b1;
                    end else in_w[q] <= in_w[q] + 1'b1;
                end
                if (in_act[q]) in_ph[q] <= in_ph[q] + 1'b1;
            end
            if (dany && !in_kind[dq] && lowbad) ing_fault <= 1'b1;               // residual must be BF16-valued
            if (e_ing) begin
                if (in_act[e_ingq] || e_cnt == 0 || e_w >= WPR || e_lo >= (e_kind ? 24 : 8)) ing_fault <= 1'b1;
                in_act[e_ingq] <= 1'b1; in_kind[e_ingq] <= e_kind; in_ph[e_ingq] <= 2'd0;
                in_slot[e_ingq] <= e_slot; in_lo[e_ingq] <= e_lo; in_w[e_ingq] <= e_w;
                in_left[e_ingq] <= e_cnt; in_word[e_ingq] <= e_word;
            end
        end
    end
    always @(posedge clk) begin
        b_j <= dj; b_a <= in_kind[dq] ? dwaddr : dxaddr; b_d <= wave;
    end

    // ------------------------------------------------------------------ projection core + bank tiles
    wire sd_v, sd_ss; wire [NVW-1:0] sd_nv; wire [AW-1:0] sd_wa, sd_xa;
    wire [W*32-1:0] sys_sum; wire sys_fault;
    wire o_valid, o_last, core_fault, core_idle; wire [2:0] o_pos; wire [4:0] o_idx; wire [31:0] o_data;
    ot_hdc_v41x_hcp_sys1_static #(.W(W), .TL(4), .PMAX(8), .OMAX(32), .AW(AW), .CW(16), .ML(ML), .DF(32),
        .STATIC_CALENDAR(1), .SYS(1), .SYS_LAT(SYS_LAT)) u_core (
        .clk(clk), .reduction_clk(clk), .scalar_clk(clk), .rst_n(rst_n), .calendar_pop(e_pop),
        .cmd_valid(e_launch), .cmd_ready(), .cmd_npos(e_npos), .cmd_nout(6'd24), .cmd_nchunk(16'(K / 8)),
        .cmd_scale(1'b1), .cmd_nf(NF), .cmd_eps(e_eps), .cmd_wbase(AW'({e_wslot, 8'd0})), .cmd_xbase({AW{1'b0}}),
        .w_re(), .x_re(), .w_addr(), .x_addr(), .w_data({(8*W*32){1'b0}}), .x_data({(8*W*16){1'b0}}),
        .o_valid(o_valid), .o_ready(1'b1), .o_pos(o_pos), .o_idx(o_idx), .o_data(o_data), .o_last(o_last),
        .fault(core_fault), .idle(core_idle),
        .sd_v(sd_v), .sd_ss(sd_ss), .sd_nv(sd_nv), .sd_wa(sd_wa), .sd_xa(sd_xa), .sys_sum(sys_sum), .sys_fault(sys_fault));
    // relays core -> bank 0 (descriptor) and bank 7 -> core (chunk sums, lane fault)
    localparam integer DW = 2 + NVW + 2 * AW;
    wire [DW-1:0] d_in = {sd_v, sd_ss, sd_nv, sd_wa, sd_xa};
    wire [DW-1:0] d_rel; wire [W*32:0] s_rel;
    wire [W*32:0] s_src;
    if (DRLY == 0) begin : g_nor
        assign d_rel = d_in; assign sys_sum = s_src[W*32-1:0]; assign sys_fault = s_src[W*32];
    end else begin : g_rel
        reg [DW-1:0] dr [0:DRLY-1]; reg [W*32:0] sr [0:DRLY-1];
        always @(posedge clk) begin
            dr[0] <= d_in; sr[0] <= s_src;
            for (integer i = 1; i < DRLY; i = i + 1) begin dr[i] <= dr[i-1]; sr[i] <= sr[i-1]; end
        end
        assign d_rel = dr[DRLY-1]; assign sys_sum = sr[DRLY-1][W*32-1:0]; assign sys_fault = sr[DRLY-1][W*32];
    end
    wire [8:0] cv, css, cf; wire [9*NVW-1:0] cnv; wire [9*AW-1:0] cwa, cxa; wire [9*W*32-1:0] csum;
    assign {cv[0], css[0], cnv[0 +: NVW], cwa[0 +: AW], cxa[0 +: AW]} = d_rel;
    assign csum[0 +: W*32] = {(W*32){1'b0}}; assign cf[0] = 1'b0;
    assign s_src = {cf[8], csum[8*W*32 +: W*32]};
    genvar gk;
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_bank
        ot_hbm_hc_bank_static #(.W(W), .AW(AW), .LM(LM), .LA(LA), .MUT((MUT == 1 && gk == 3) ? 1 : 0)) u_b (
            .clk(clk), .rst_n(rst_n), .first(gk == 0),
            .d_v(cv[gk]), .d_ss(css[gk]), .d_nv(cnv[gk*NVW +: NVW]), .d_wa(cwa[gk*AW +: AW]), .d_xa(cxa[gk*AW +: AW]),
            .o_v(cv[gk+1]), .o_ss(css[gk+1]), .o_nv(cnv[(gk+1)*NVW +: NVW]), .o_wa(cwa[(gk+1)*AW +: AW]),
            .o_xa(cxa[(gk+1)*AW +: AW]), .sum_in(csum[gk*W*32 +: W*32]), .sum_out(csum[(gk+1)*W*32 +: W*32]),
            .f_in(cf[gk]), .f_out(cf[gk+1]),
            .wv(b_wv), .xv(b_xv), .j(b_j), .wa(b_a), .wd(bank_slice(b_d, gk)));
    end
    function automatic [1023:0] bank_slice(input [8191:0] d, input integer k);
        for (integer m = 0; m < 32; m = m + 1) bank_slice[m*32 +: 32] = d[m*256 + k*32 +: 32];
    endfunction

    // ------------------------------------------------------------------ mix store
    reg [8*24*32-1:0] mixes; reg [191:0] have; reg mix_fault; reg [3:0] gm_open;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin have <= 0; mix_fault <= 0; gm_open <= 0; end
        else begin
            if (e_clear) have <= 0;
            if (e_gm) gm_open[e_gmq] <= e_gmo;
            if (o_valid) begin
                if (o_idx >= 5'd24) mix_fault <= 1'b1;
                else begin mixes[(o_pos*24 + o_idx)*32 +: 32] <= o_data; have[o_pos*24 + o_idx] <= 1'b1; end
            end
            for (integer q = 0; q < 4; q = q + 1) if (gv_q[q]) begin
                if (!gm_open[q] || gr_q[q*5 +: 5] >= 5'd24) mix_fault <= 1'b1;
                else begin
                    mixes[(gp_q[q*3 +: 3]*24 + gr_q[q*5 +: 5])*32 +: 32] <= gd_q[q*32 +: 32];
                    have[gp_q[q*3 +: 3]*24 + gr_q[q*5 +: 5]] <= 1'b1;
                end
            end
        end
    end

    // ------------------------------------------------------------------ bases/scales table
    reg [2:0] tf_cnt; reg [6:0] tf_set; reg [1:0] tf_row_q; reg tf_rd_q; reg [895:0] hold; reg tbl_fault;
    wire [255:0] tbl_rd;
    wire tf_rd = tf_cnt != 3'd0;
    wire [1:0] tf_row = 2'(4 - tf_cnt);
    ot_sram_1r1w_1024x256_m2_r2c2 u_tbl (.clk(clk), .r_ce_in(tf_rd), .r_addr_in({1'b0, tf_set, tf_row}),
        .rd_out(tbl_rd), .w_ce_in(tbl_we_q && !seq_active), .w_addr_in(tbl_addr_q), .wd_in(tbl_data_q),
        .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin tf_cnt <= 0; tf_rd_q <= 0; tbl_fault <= 0; end
        else begin
            tf_rd_q <= tf_rd; tf_row_q <= tf_row;
            if (tf_rd) tf_cnt <= tf_cnt - 1'b1;
            if (e_tf) begin if (tf_rd) tbl_fault <= 1'b1; tf_cnt <= 3'd4; tf_set <= e_tset; end
            if (tbl_we_q && seq_active) tbl_fault <= 1'b1;
        end
    end
    always @(posedge clk) if (tf_rd_q) hold[tf_row_q*224 +: 224] <= tbl_rd[223:0];   // row payload (F20 header off)
    // set layout: base i = row i/7 word i%7 = hold word i (i < 24); scale j = row 3 word 3 + j = hold word 24 + j
    wire [767:0] t_bases = hold[767:0]; wire [95:0] t_scales = hold[863:768];

    // ------------------------------------------------------------------ tail units
    wire [1:0] tv, tfl; wire [1535:0] tres; reg [2:0] tpos [0:1]; reg [1:0] tready; reg tail_fault;
    genvar gu;
    for (gu = 0; gu < 2; gu = gu + 1) begin : g_tail
        wire go = e_tl && e_tunit == gu;
        ot_hbm_hc_tail_unit_static #(.MUT_PRE((MUT == 2 && gu == 0) ? 1 : 0)) u_t (.clk(clk), .rst_n(rst_n),
            .launch(go), .mixes(mixes[e_tpos*768 +: 768]), .bases(t_bases), .scales(t_scales),
            .result_v(tv[gu]), .result(tres[gu*768 +: 768]), .fault(tfl[gu]));
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin tready <= 0; tail_fault <= 0; end
        else begin
            for (integer u = 0; u < 2; u = u + 1) begin
                if (tv[u]) tready[u] <= 1'b1;
                if (e_tl && e_tunit == u) begin tready[u] <= 1'b0; tpos[u] <= e_tpos; end
            end
            if (e_tl && have[e_tpos*24 +: 24] != 24'hffffff) tail_fault <= 1'b1;
            if (e_emit && !tready[e_eunit]) tail_fault <= 1'b1;
        end
    end

    // ------------------------------------------------------------------ result pins (all flops)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) result_v <= 4'd0;
        else result_v <= e_emit ? e_qmask : 4'd0;
    end
    always @(posedge clk) if (e_emit) for (integer q = 0; q < 4; q = q + 1) if (e_qmask[q]) begin
        result_position[q*3 +: 3] <= tpos[e_eunit]; result[q*768 +: 768] <= tres[e_eunit*768 +: 768];
    end

    // ------------------------------------------------------------------ status
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 0; program_active <= 0; program_done <= 0; end
        else begin
            program_active <= seq_active; program_done <= seq_done;
            if (seq_fault || ing_fault || core_fault || mix_fault || tbl_fault || tail_fault || (|tfl) || (|rx_fault) ||
                ptgt_fault || ttgt_fault) fault <= 1'b1;
        end
    end
endmodule
`default_nettype wire
