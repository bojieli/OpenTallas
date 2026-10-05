`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_coll_port: HA3 per-die SM -> collective endpoint of the HBM
// accelerator.  It replaces the pair ot_gpu_coll_mux + ot_gpu_coll_endpoint
// (both stay byte-identical) on the clk_sm side; the LINK side -- record
// format {tag = {src, seq, count, word}, mode, last, LANES x 32 data}, ascending
// word order, one collective outstanding per rank, every received tag checked,
// the clk_sm <-> clk_link crossings in ot_gpu_cdc_fifo -- is the original
// endpoint's, so the fabric (ot_gpu_coll_fabric, or the HA2 direct links) is
// unchanged.
//
// Legacy COLL (s_x = 0): one SM requests with the whole vector; the lowest
// requesting SM is served; response to that SM only.  Same records, same
// order, same reassembly as ot_gpu_coll_endpoint behind ot_gpu_coll_mux.
//
// COLLX (s_x = 1, cut-through, dataflow level 2/5): EVERY SM of the die
// contributes its lanes straight from its register: SM s's data lanes
// 0..nown-1 are collective lanes off..off+nown-1.  The port keeps one bit per
// collective lane; TX record `word` w is sent (in ascending word order, as the
// switch's pop-together reduction requires) as soon as every lane of w below
// count has been contributed -- not after a store, barrier and reload.  A lane
// no SM of the die contributes is +0 once every SM has contributed (a die's
// share of a gather-by-reduce: the other die's lanes are +0, as the
// baseline's ownership mask makes them); a fused collective needs every lane.  When
// every SM has contributed and every record has come back, the result is
// multicast to every SM (each takes it with its own rsp handshake).
//
// Fused receive-path epilogue (s_fuse = 1, reduce only, count = NL): the
// residual lanes off..off+nown-1 of each SM's s_resid (at their own lane
// positions) are captured with the contribution.  Every reduced record that
// arrives goes straight through, in arrival order:
//   x'[l]  = fl(resid[l] + red[l])         (the SM's FADD, same pipe)
//   sq[l]  = fl(x'[l] * x'[l])             (the SM's FMUL, same pipe)
//   chunk c (lanes 8c..8c+7): acc = +0 + sq[8c]; acc = acc + sq[8c+k], k = 1..7
//   ss     = pairwise tree over the NL/8 chunk sums, adjacent pairs
// -- exactly the golden rmsnorm's R-ARITH order (tools/gpu_sys/qwen_hbm.py
// Lib.seg_sum8 over one NL-lane segment, hdc_golden.reduce_chunked).  The
// response data is x', rsp_ss is ss.  Every FP operation uses
// ot_gpu_simt_fplane (the SM's own qualified pipes, FLAT the same), so results
// are bit-identical to the two-op SM program; a nonfinite operand or overflow
// in any of them sets rsp_err (the SM faults: the same fail-closed rule as
// its own pipes) and the sticky fault.
//
// Program contract (checked, a violation latches the sticky fault): the SMs'
// COLLX of one collective agree on mode/count/fuse; lanes are contributed at
// most once and lie below count; fuse needs mode 0 and count = NL.  A legacy
// COLL is only accepted while no COLLX collective is open.
//
// ENABLE = 0 (default): inert, every output 0.
// EPI = 1 (default): the fused receive-path epilogue above is built.  EPI = 0: the cut-through port alone (R3a; the
// epilogue R3b is measured below 1% and rejected): no epilogue pipes, s_rsp_ss = 0, and a fused request latches
// the sticky fault (fail closed) instead of being served.  Every non-fused collective behaves identically.
// ---------------------------------------------------------------------------
module ot_hbm_accel_coll_port #(
    parameter integer ENABLE = 0,
    parameter integer NSM    = 2,
    parameter integer NL     = 128,
    parameter integer LANES  = 16,
    parameter integer R      = 2,
    parameter integer RANK   = 0,
    parameter integer TAGW   = 32,
    parameter integer AW     = 3,
    parameter integer AW_RX  = 4,
    parameter integer SYNC   = 2,
    parameter integer FLAT   = 5,
    parameter integer EPI    = 1,
    parameter integer FW     = 32 * LANES,
    parameter integer PW     = FW + 2 + TAGW
) (
    input  wire                  clk_sm,
    input  wire                  rst_sm_n,
    // SM side (one port per SM)
    input  wire [NSM-1:0]        s_req_v,
    output wire [NSM-1:0]        s_req_rdy,
    input  wire [NSM-1:0]        s_mode,
    input  wire [NSM*8-1:0]      s_count,
    input  wire [NSM*NL*32-1:0]  s_data,
    input  wire [NSM-1:0]        s_x,
    input  wire [NSM*8-1:0]      s_off,
    input  wire [NSM*8-1:0]      s_nown,
    input  wire [NSM-1:0]        s_fuse,
    input  wire [NSM*NL*32-1:0]  s_resid,
    output wire [NSM-1:0]        s_rsp_v,
    input  wire [NSM-1:0]        s_rsp_rdy,
    output wire [NL*32-1:0]      s_rsp_data,
    output wire [31:0]           s_rsp_ss,
    output wire                  s_rsp_err,
    output wire                  fault,           // sticky (clk_sm)
    // statistics (clk_sm): cycles from the open of the last collective to its response
    output reg  [31:0]           st_coll,
    // link side
    input  wire                  clk_link,
    input  wire                  rst_link_n,
    output wire                  lk_tx_v,
    output wire [PW-1:0]         lk_tx_rec,
    input  wire                  lk_rx_v,
    input  wire [PW-1:0]         lk_rx_rec
);
generate if (ENABLE == 0) begin : g_off
    assign s_req_rdy = {NSM{1'b0}}; assign s_rsp_v = {NSM{1'b0}}; assign s_rsp_data = {NL*32{1'b0}};
    assign s_rsp_ss = 32'd0; assign s_rsp_err = 1'b0; assign fault = 1'b0;
    assign lk_tx_v = 1'b0; assign lk_tx_rec = {PW{1'b0}};
    always @(posedge clk_sm) st_coll <= 32'd0;
end else begin : g_on
    localparam integer NWD  = (NL + LANES - 1) / LANES;      // words of a full vector
    localparam integer NCH  = NL / 8;                          // golden chunks of 8
    localparam integer SB   = (NSM > 1) ? $clog2(NSM) : 1;
    localparam integer GPRE = (R - 1) * ((NL / R + LANES - 1) / LANES);
    localparam [7:0]   RK8  = RANK[7:0];
    if (TAGW != 32) begin : g_bad_tagw
        $error("ot_hbm_accel_coll_port: TAGW must be 32");
    end
    if (NL > 255 || NL < 8 || (NL % 8) != 0 || (NL % LANES) != 0 || (LANES % 8) != 0) begin : g_bad_nl
        $error("ot_hbm_accel_coll_port: NL must be a multiple of LANES and of 8, <= 255; LANES a multiple of 8");
    end
    if ((NCH & (NCH - 1)) != 0) begin : g_bad_nch
        $error("ot_hbm_accel_coll_port: NL/8 must be a power of two (the chunk tree)");
    end
    if ((1 << AW_RX) < GPRE + 2) begin : g_bad_rx
        $error("ot_hbm_accel_coll_port: RX FIFO depth 2^AW_RX below the early-gather bound + 2");
    end

    // ------------------------------------------------------------------ collective state
    localparam [1:0] S_IDLE = 2'd0, S_RUN = 2'd1, S_RSP = 2'd2;
    reg  [1:0]       st;
    reg              xm;              // the open collective is a COLLX (multicast) one
    reg  [SB-1:0]    own;             // legacy: the requesting SM
    reg  [NSM-1:0]   contrib;         // COLLX: SMs that contributed
    reg  [NSM-1:0]   taken;           // COLLX: SMs that took the response
    reg  [NL*32-1:0] dat, asmb, resid;
    reg  [NL-1:0]    lane_ok;         // lane contributed (or >= count)
    reg              mode_q, fuse_q;
    reg  [7:0]       cnt_q, seq, sw, nrec;
    reg  [8:0]       nexp, rcv;
    reg              flt;
    reg  [31:0]      t_open;

    // ---- legacy pick (lowest requesting legacy SM; ot_gpu_coll_mux order)
    reg              any_leg;
    reg  [SB-1:0]    pick;
    integer i;
    always @* begin
        any_leg = 1'b0; pick = {SB{1'b0}};
        for (i = NSM - 1; i >= 0; i = i - 1) if (s_req_v[i] && !s_x[i]) begin any_leg = 1'b1; pick = i[SB-1:0]; end
    end
    // ---- COLLX acceptance: in IDLE (opens) or RUN of an open COLLX collective, from SMs that have not contributed
    wire          can_x = (st == S_IDLE && !any_leg) || (st == S_RUN && xm);
    wire [NSM-1:0] acc_x;
    genvar g;
    for (g = 0; g < NSM; g = g + 1) begin : g_acc
        assign acc_x[g] = can_x && s_req_v[g] && s_x[g] && !(st == S_RUN && contrib[g]);
        assign s_req_rdy[g] = acc_x[g] || (st == S_IDLE && any_leg && pick == g && !s_x[g]);
    end
    // the first accepted SM in IDLE fixes mode/count/fuse
    reg  [SB-1:0] fx;
    always @* begin
        fx = {SB{1'b0}};
        for (i = NSM - 1; i >= 0; i = i - 1) if (acc_x[i]) fx = i[SB-1:0];
    end

    // ---- merged contribution of this cycle: each SM's data shifted up by off lanes (a log-depth barrel shifter),
    //      its lane mask ((1 << nown) - 1) << off, the residual at its own lanes
    reg  [NL*32-1:0] dat_n, res_n;
    reg  [NL-1:0]    ok_n;
    reg              bad_x;
    wire [NL*32-1:0] sh_d [0:NSM-1];
    wire [NL-1:0]    sh_m [0:NSM-1];
    wire [NL*32-1:0] sh_m32 [0:NSM-1];
    for (g = 0; g < NSM; g = g + 1) begin : g_sh
        wire [NL:0]  ones = ({{NL{1'b0}}, 1'b1} << s_nown[g*8 +: 8]) - 1'b1;
        assign sh_d[g] = s_data[g*NL*32 +: NL*32] << {s_off[g*8 +: 8], 5'd0};
        assign sh_m[g] = ones[NL-1:0] << s_off[g*8 +: 8];
        for (genvar q = 0; q < NL; q = q + 1) begin : g_m
            assign sh_m32[g][32*q +: 32] = {32{sh_m[g][q]}};
        end
    end
    integer s, l;
    always @* begin
        dat_n = (st == S_IDLE) ? {NL*32{1'b0}} : dat;
        res_n = (st == S_IDLE) ? {NL*32{1'b0}} : resid;
        ok_n  = (st == S_IDLE) ? {NL{1'b0}} : lane_ok;
        bad_x = 1'b0;
        for (s = 0; s < NSM; s = s + 1) if (acc_x[s]) begin
            if (s_mode[s] != ((st == S_IDLE) ? s_mode[fx] : mode_q) ||
                s_count[s*8 +: 8] != ((st == S_IDLE) ? s_count[fx*8 +: 8] : cnt_q) ||
                s_fuse[s] != ((st == S_IDLE) ? s_fuse[fx] : fuse_q) ||
                32'(s_off[s*8 +: 8]) + 32'(s_nown[s*8 +: 8]) > 32'(s_count[s*8 +: 8]))
                bad_x = 1'b1;
            if (|(ok_n & sh_m[s])) bad_x = 1'b1;
            ok_n  = ok_n | sh_m[s];
            dat_n = (dat_n & ~sh_m32[s]) | (sh_d[s] & sh_m32[s]);
            res_n = (res_n & ~sh_m32[s]) | (s_resid[s*NL*32 +: NL*32] & sh_m32[s]);
        end
        // lanes at or above count need no contribution (sent as +0)
        for (l = 0; l < NL; l = l + 1)
            if (l >= 32'((st == S_IDLE) ? s_count[fx*8 +: 8] : cnt_q)) ok_n[l] = 1'b1;
    end

    // ---- TX record of word sw
    reg  [FW-1:0] txd;
    reg           w_ready;
    integer j;
    always @* begin
        w_ready = 1'b1;
        for (j = 0; j < LANES; j = j + 1) begin
            if (32'(sw) * LANES + j < 32'(cnt_q) && 32'(sw) * LANES + j < NL)
                txd[32*j +: 32] = dat[32 * (32'(sw) * LANES + j) +: 32];
            else
                txd[32*j +: 32] = 32'd0;
            if (32'(sw) * LANES + j < NL && !lane_ok[32'(sw) * LANES + j] && !(xm && !fuse_q && contrib == {NSM{1'b1}}))
                w_ready = 1'b0;
        end
    end
    wire [PW-1:0] tx_rec = {RK8, seq, cnt_q, sw, mode_q, (sw + 8'd1 == nrec), txd};
    wire          tx_in_v = (st == S_RUN) && (sw < nrec) && w_ready;
    wire          tx_in_rdy;

    // ---- RX record
    wire          rx_out_v;
    wire [PW-1:0] rx_d;
    wire          rx_take = rx_out_v && (st == S_RUN);
    wire [7:0]    r_src  = rx_d[PW-1 -: 8];
    wire [7:0]    r_seq  = rx_d[PW-9 -: 8];
    wire [7:0]    r_cnt  = rx_d[PW-17 -: 8];
    wire [7:0]    r_word = rx_d[PW-25 -: 8];
    wire          r_mode = rx_d[FW + 1];
    wire          r_bad  = (r_seq != seq) || (r_cnt != cnt_q) || (r_mode != mode_q) || (r_word >= nrec) ||
                           (mode_q ? (32'(r_src) >= R) : (r_src != 8'hFF));
    reg  [NL*32-1:0] asmb_n;
    integer k, idx, dst;
    always @* begin
        asmb_n = asmb;
        for (k = 0; k < LANES; k = k + 1) begin
            idx = 32'(r_word) * LANES + k;
            dst = mode_q ? 32'(r_src) * 32'(cnt_q) + idx : idx;
            if (idx < 32'(cnt_q) && dst < NL) asmb_n[32 * dst +: 32] = rx_d[32*k +: 32];
        end
    end

    // ------------------------------------------------------------------ fused epilogue
    // stage A (x' = resid + red) and stage B (x'^2): LANES fplanes, one record per cycle
    wire [LANES*32-1:0] ea_y, eb_y;
    wire [LANES-1:0]    ea_f, eb_f;
    reg                 ea_v, eb_v;
    reg  [LANES*32-1:0] ea_a, ea_b, eb_a;
    reg  [FLAT:0]       eaq_v, ebq_v;
    reg  [7:0]          eaq_w [0:FLAT];
    reg  [7:0]          ebq_w [0:FLAT];
    if (EPI != 0) begin : g_epi_ab
    for (g = 0; g < LANES; g = g + 1) begin : g_ab
        wire unused_m, unused_mf, unused_a, unused_af;
        ot_gpu_simt_fplane #(.FLAT(FLAT)) u_a (.clk(clk_sm), .rst_n(rst_sm_n), .add_v(ea_v), .mul_v(1'b0),
            .a(ea_a[g*32 +: 32]), .b(ea_b[g*32 +: 32]), .add_y(ea_y[g*32 +: 32]), .add_f(ea_f[g]),
            .mul_y(), .mul_f());
        ot_gpu_simt_fplane #(.FLAT(FLAT)) u_b (.clk(clk_sm), .rst_n(rst_sm_n), .add_v(1'b0), .mul_v(eb_v),
            .a(eb_a[g*32 +: 32]), .b(eb_a[g*32 +: 32]), .add_y(), .add_f(),
            .mul_y(eb_y[g*32 +: 32]), .mul_f(eb_f[g]));
    end
    end else begin : g_no_ab
        assign ea_y = {LANES*32{1'b0}}; assign ea_f = {LANES{1'b0}};
        assign eb_y = {LANES*32{1'b0}}; assign eb_f = {LANES{1'b0}};
    end
    reg  [NL*32-1:0] xo, sq;            // x' and its squares
    reg  [NCH-1:0]   ch_rdy;            // chunk's squares present
    // chunk chains and the tree: NCH adder lanes
    wire [NCH*32-1:0] ec_y;
    wire [NCH-1:0]    ec_f;
    reg  [NCH-1:0]    ec_v;
    reg  [NCH*32-1:0] ec_a, ec_b;
    reg  [FLAT:0]     ecq_v [0:NCH-1];
    if (EPI != 0) begin : g_epi_c
    for (g = 0; g < NCH; g = g + 1) begin : g_c
        ot_gpu_simt_fplane #(.FLAT(FLAT)) u_c (.clk(clk_sm), .rst_n(rst_sm_n), .add_v(ec_v[g]), .mul_v(1'b0),
            .a(ec_a[g*32 +: 32]), .b(ec_b[g*32 +: 32]), .add_y(ec_y[g*32 +: 32]), .add_f(ec_f[g]),
            .mul_y(), .mul_f());
    end
    end else begin : g_no_c
        assign ec_y = {NCH*32{1'b0}}; assign ec_f = {NCH{1'b0}};
    end
    reg  [NCH*32-1:0] acc;              // chunk sums, then tree partials (lane c holds node c)
    reg  [3:0]        ck [0:NCH-1];     // chunk c: next element 0..7, 8 = chunk sum done
    reg  [NCH-1:0]    cbusy;            // an add of lane c is in flight
    reg  [3:0]        lvl;              // tree level in progress (0: chunks)
    reg               ep_done, ep_err;
    localparam integer TL = $clog2(NCH);

    // ------------------------------------------------------------------ main sequencer
    wire all_in   = (contrib | acc_x) == {NSM{1'b1}};
    wire rx_done  = (rcv >= nexp);
    integer c, m;
    always @(posedge clk_sm or negedge rst_sm_n) begin
        if (!rst_sm_n) begin
            st <= S_IDLE; xm <= 1'b0; own <= {SB{1'b0}}; contrib <= {NSM{1'b0}}; taken <= {NSM{1'b0}};
            lane_ok <= {NL{1'b0}}; mode_q <= 1'b0; fuse_q <= 1'b0; cnt_q <= 8'd0; seq <= 8'd0; sw <= 8'd0;
            nrec <= 8'd0; nexp <= 9'd0; rcv <= 9'd0; flt <= 1'b0; asmb <= {NL*32{1'b0}};
            ea_v <= 1'b0; eb_v <= 1'b0; eaq_v <= 0; ebq_v <= 0; ec_v <= {NCH{1'b0}};
            ch_rdy <= {NCH{1'b0}}; cbusy <= {NCH{1'b0}}; lvl <= 4'd0; ep_done <= 1'b0; ep_err <= 1'b0;
            st_coll <= 32'd0; t_open <= 32'd0;
            for (c = 0; c < NCH; c = c + 1) begin ck[c] <= 4'd0; ecq_v[c] <= 0; end
        end else begin
            ea_v <= 1'b0; eb_v <= 1'b0; ec_v <= {NCH{1'b0}};
            t_open <= t_open + 32'd1;
            // ---- epilogue pipes bookkeeping
            eaq_v <= {eaq_v[FLAT-1:0], ea_v};
            ebq_v <= {ebq_v[FLAT-1:0], eb_v};
            for (m = FLAT; m > 0; m = m - 1) begin eaq_w[m] <= eaq_w[m-1]; ebq_w[m] <= ebq_w[m-1]; end
            if (eaq_v[FLAT-1]) begin                       // x' of word eaq_w[FLAT] -> square it
                xo[32*LANES*eaq_w[FLAT] +: 32*LANES] <= ea_y;
                eb_v <= 1'b1; eb_a <= ea_y; ebq_w[0] <= eaq_w[FLAT];
                if (|ea_f) ep_err <= 1'b1;
            end
            if (ebq_v[FLAT-1]) begin
                sq[32*LANES*ebq_w[FLAT] +: 32*LANES] <= eb_y;
                for (c = 0; c < LANES / 8; c = c + 1) ch_rdy[ebq_w[FLAT] * (LANES / 8) + c] <= 1'b1;
                if (|eb_f) ep_err <= 1'b1;
            end
            for (c = 0; c < NCH; c = c + 1) begin
                ecq_v[c] <= {ecq_v[c][FLAT-1:0], ec_v[c]};
                if (ecq_v[c][FLAT-1]) begin
                    acc[32*c +: 32] <= ec_y[32*c +: 32];
                    cbusy[c] <= 1'b0;
                    if (ec_f[c]) ep_err <= 1'b1;
                end
            end
            // chunk chains: acc = +0 + sq[8c]; acc = acc + sq[8c+k]
            if (st == S_RUN && fuse_q && lvl == 4'd0) begin
                for (c = 0; c < NCH; c = c + 1)
                    if (ch_rdy[c] && !cbusy[c] && !ecq_v[c][FLAT-1] && ck[c] < 4'd8) begin
                        ec_v[c] <= 1'b1; cbusy[c] <= 1'b1; ck[c] <= ck[c] + 4'd1;
                        ec_a[32*c +: 32] <= (ck[c] == 4'd0) ? 32'd0 : acc[32*c +: 32];
                        ec_b[32*c +: 32] <= sq[32*(8*c + ck[c]) +: 32];
                    end
                begin : chk_chunks
                    reg alld;
                    alld = 1'b1;
                    for (c = 0; c < NCH; c = c + 1) if (ck[c] != 4'd8 || cbusy[c] || ecq_v[c][FLAT-1]) alld = 1'b0;
                    if (alld) lvl <= 4'd1;
                end
            end
            // pairwise tree, level t: node c = node 2c + node 2c+1 (lanes 0 .. NCH/2^t - 1)
            if (st == S_RUN && fuse_q && lvl != 4'd0 && !ep_done) begin
                begin : tree
                    reg idle;
                    idle = (cbusy == {NCH{1'b0}});
                    for (c = 0; c < NCH; c = c + 1) if (ecq_v[c][FLAT-1]) idle = 1'b0;
                    if (idle && ck[0] != 4'd9) begin
                        for (c = 0; c < NCH; c = c + 1)
                            if (c < (NCH >> lvl)) begin
                                ec_v[c] <= 1'b1; cbusy[c] <= 1'b1;
                                ec_a[32*c +: 32] <= acc[32*(2*c) +: 32];
                                ec_b[32*c +: 32] <= acc[32*(2*c+1) +: 32];
                            end
                        ck[0] <= 4'd9;                     // level issued
                    end else if (idle && ck[0] == 4'd9) begin
                        ck[0] <= 4'd8;
                        if (lvl == 4'(TL)) ep_done <= 1'b1;
                        else lvl <= lvl + 4'd1;
                    end
                end
            end

            case (st)
                S_IDLE: begin
                    taken <= {NSM{1'b0}}; rcv <= 9'd0; sw <= 8'd0; asmb <= {NL*32{1'b0}};
                    ch_rdy <= {NCH{1'b0}}; lvl <= 4'd0; ep_done <= 1'b0; ep_err <= 1'b0;
                    for (c = 0; c < NCH; c = c + 1) ck[c] <= 4'd0;
                    if (any_leg) begin
                        xm <= 1'b0; own <= pick; contrib <= {NSM{1'b0}};
                        dat <= s_data[pick*NL*32 +: NL*32]; lane_ok <= {NL{1'b1}};
                        mode_q <= s_mode[pick]; cnt_q <= s_count[pick*8 +: 8]; fuse_q <= 1'b0;
                        nrec <= 8'((32'(s_count[pick*8 +: 8]) + LANES - 1) / LANES);
                        nexp <= s_mode[pick] ? 9'((32'(s_count[pick*8 +: 8]) + LANES - 1) / LANES * R)
                                             : 9'((32'(s_count[pick*8 +: 8]) + LANES - 1) / LANES);
                        if (s_count[pick*8 +: 8] == 8'd0 || 32'(s_count[pick*8 +: 8]) > NL ||
                            (s_mode[pick] && 32'(s_count[pick*8 +: 8]) * R > NL)) flt <= 1'b1;
                        st <= S_RUN; t_open <= 32'd0;
                    end else if (|acc_x) begin
                        xm <= 1'b1; contrib <= acc_x; dat <= dat_n; resid <= res_n; lane_ok <= ok_n;
                        mode_q <= s_mode[fx]; cnt_q <= s_count[fx*8 +: 8]; fuse_q <= (EPI != 0) && s_fuse[fx];
                        nrec <= 8'((32'(s_count[fx*8 +: 8]) + LANES - 1) / LANES);
                        nexp <= s_mode[fx] ? 9'((32'(s_count[fx*8 +: 8]) + LANES - 1) / LANES * R)
                                           : 9'((32'(s_count[fx*8 +: 8]) + LANES - 1) / LANES);
                        if (bad_x || s_count[fx*8 +: 8] == 8'd0 || 32'(s_count[fx*8 +: 8]) > NL ||
                            (s_mode[fx] && 32'(s_count[fx*8 +: 8]) * R > NL) ||
                            (s_fuse[fx] && (s_mode[fx] || 32'(s_count[fx*8 +: 8]) != NL)) ||
                            (s_fuse[fx] && EPI == 0)) flt <= 1'b1;
                        st <= S_RUN; t_open <= 32'd0;
                    end
                end
                S_RUN: begin
                    if (|acc_x) begin
                        contrib <= contrib | acc_x; dat <= dat_n; resid <= res_n; lane_ok <= ok_n;
                        if (bad_x) flt <= 1'b1;
                    end
                    if (tx_in_v && tx_in_rdy) sw <= sw + 8'd1;
                    if (rx_take) begin
                        if (r_bad) flt <= 1'b1;
                        asmb <= asmb_n;
                        rcv <= rcv + 9'd1;
                        if (fuse_q) begin                    // reduce record -> epilogue stage A
                            ea_v <= 1'b1; eaq_w[0] <= r_word;
                            for (k = 0; k < LANES; k = k + 1) begin
                                ea_a[32*k +: 32] <= resid[32 * (32'(r_word) * LANES + k) +: 32];
                                ea_b[32*k +: 32] <= rx_d[32*k +: 32];
                            end
                        end
                    end
                    if (xm && fuse_q && all_in && ((ok_n | lane_ok) != {NL{1'b1}})) flt <= 1'b1;
                    if (rx_done && (!xm || all_in) && (!fuse_q || ep_done)) begin
                        st <= S_RSP;
                        st_coll <= t_open;
                    end
                end
                S_RSP: begin
                    if (xm) begin
                        taken <= taken | (s_rsp_rdy & ~taken);
                        if ((taken | s_rsp_rdy) == {NSM{1'b1}}) begin st <= S_IDLE; seq <= seq + 8'd1; end
                    end else if (s_rsp_rdy[own]) begin
                        st <= S_IDLE; seq <= seq + 8'd1;
                    end
                end
                default: st <= S_IDLE;
            endcase
            if (ep_err && st == S_RSP) flt <= 1'b1;
        end
    end
    for (g = 0; g < NSM; g = g + 1) begin : g_rsp
        assign s_rsp_v[g] = (st == S_RSP) && (xm ? !taken[g] : (own == g));
    end
    assign s_rsp_data = fuse_q ? xo : asmb;
    assign s_rsp_ss   = (EPI != 0) ? acc[31:0] : 32'd0;
    assign s_rsp_err  = fuse_q && ep_err;

    // ------------------------------------------------------------------ clock crossings (the original endpoint's)
    wire tx_ovf, rx_ovf, rx_in_rdy;
    ot_gpu_cdc_fifo #(.ENABLE(1), .W(PW), .AW(AW), .SYNC(SYNC)) u_tx_cdc (
        .wclk(clk_sm), .wrst_n(rst_sm_n), .in_v(tx_in_v), .in_rdy(tx_in_rdy), .in_d(tx_rec),
        .rclk(clk_link), .rrst_n(rst_link_n), .out_v(lk_tx_v), .out_rdy(1'b1), .out_d(lk_tx_rec),
        .ovf_fault(tx_ovf));
    ot_gpu_cdc_fifo #(.ENABLE(1), .W(PW), .AW(AW_RX), .SYNC(SYNC)) u_rx_cdc (
        .wclk(clk_link), .wrst_n(rst_link_n), .in_v(lk_rx_v), .in_rdy(rx_in_rdy), .in_d(lk_rx_rec),
        .rclk(clk_sm), .rrst_n(rst_sm_n), .out_v(rx_out_v), .out_rdy(st == S_RUN), .out_d(rx_d),
        .ovf_fault(rx_ovf));
    reg flt_lk;
    always @(posedge clk_link or negedge rst_link_n)
        if (!rst_link_n) flt_lk <= 1'b0;
        else if ((lk_rx_v && !rx_in_rdy) || rx_ovf) flt_lk <= 1'b1;
    reg [SYNC-1:0] flt_sync;
    always @(posedge clk_sm or negedge rst_sm_n)
        if (!rst_sm_n) flt_sync <= {SYNC{1'b0}};
        else flt_sync <= {flt_sync[SYNC-2:0], flt_lk};
    assign fault = flt || flt_sync[SYNC-1] || tx_ovf;
end endgenerate
endmodule
