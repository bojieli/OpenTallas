`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CLAUDE s81-svcq-1011 [svcq-idx]: INDEX READER of one S81 scan-service slab (HBM stack ST of the die): one select
// quarter of a pooled-index scan, behind the svc frame protocol v1 (s81-svceng-1011; header [511:508] type,
// [507] END, [506:503] quadrant mask, [502:495] tag, [491:480] len, [479:459] pos, [458:449] user, [448:0] spec).
//
// Chain (every arithmetic / layout block unchanged):
//   IDX_Q frame -> query store (32 heads) -> ot_hdc_v41x_idx_score_quarter ql port (head by head)
//   IDX_Q header -> ot_hdc_v41x_idx_ring_ranges (W11 quarter-per-stack ring: RSB 64, RTAIL 32; stack q = ST holds
//                   positions [q Qs, (q+1) Qs) (quarter 3: [3 Qs, N)), Qs = 8 floor(N / 32), position p at ring
//                   slot p mod C) -> ot_hdc_v41x_idx_kstream_ring (32 pseudo-channels, native per-PC ports)
//   stream beats (16 keys, from the first super-block's key 0) -> skip: the cmd_skip / 16 leading beats dropped,
//                   lanes below skip masked in the next -> ot_hdc_v41x_idx_score_quarter (4 x NK4 score slices,
//                   the exact chunk8 indexer arithmetic) -> x words in the SELECTOR-NATIVE format
//                   (rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv):
//     HDR  [511:508] 1, [507:500] tag, [19:0] base = position of lane 0 of the first emitted beat, [29:20] k,
//          [31:30] qslot = ST
//     BEAT [511:508] 2, [507:500] tag, [255:0] 16 BF16 scores (lane i at [16 i +: 16]), [271:256] lane valid,
//          [272] last of the quarter; lane i is position cur + i, cur += 16 per beat (masked lanes advance too).
//     An empty quarter sends HDR (base = q Qs) and one BEAT with no valid lane and last = 1.
//     END (svc endpoint) = the BEAT with [272] set.
// IDX_Q (type 4, quadrant mask bit 0, len 64): spec [32:0] N (keys of the user's scan), [55:33] key base block,
// [65:56] k (<= 512); header user [458:449], tag [502:495]; payload word 2h = head h's 128 FP4 codes (4 x 128 b),
// word 2h + 1 = {[47:32] head weight BF16, [31:0] 4 x UE8M0 scale} (ql_codes / ql_sc / ql_w of head h).
// Keys stream into the scorer only after all 32 heads are loaded; the HBM scan starts at the header (overlap).
// Faults (sticky, fail closed: no x word after a fault): any scored key with o_fault, the score quarter's
// protocol_fault, ring geometry fault, an IDX_Q while a scan is active, bad len / k, a stream beat after the
// quarter's last key.
// ---------------------------------------------------------------------------
module ot_s81_svcq_idx #(
    parameter integer ST = 0,
    parameter integer NPC = 32,
    parameter integer AW = 30,
    parameter integer HW = 23,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer WB = 128,
    parameter integer GA = 120,
    parameter integer RSB = 64,
    parameter integer RTAIL = 32
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 q_v,
    input  wire [511:0]         q_d,
    // HBM stack, one port per pseudo-channel (kstream native)
    output wire [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output wire [NPC*AW-1:0]    req_addr,
    output wire [NPC*LENW-1:0]  req_len,
    output wire [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    input  wire [NPC*256-1:0]   rsp_data,
    // selector stream
    output reg                  x_v,
    output reg  [511:0]         x_d,
    input  wire                 x_r,
    output reg                  busy,
    output wire                 fault,
    output wire [7:0]           fault_code
);
    localparam integer NW = HW + 10, IH = 32, NB = 4, IW = 30;

    // ---------------- frame parser ----------------
    reg in_frame, f_mine;
    reg [11:0] left;
    reg [3:0] f_type;
    reg [11:0] f_idx;
    wire is_hdr = q_v && !in_frame;
    wire is_pay = q_v && in_frame;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin in_frame <= 0; left <= 0; f_type <= 0; f_mine <= 0; f_idx <= 0; end
        else if (is_hdr) begin
            f_type <= q_d[511:508]; f_mine <= q_d[503]; f_idx <= 0; left <= q_d[491:480];
            in_frame <= q_d[491:480] != 0;
        end else if (is_pay) begin
            f_idx <= f_idx + 1'b1; left <= left - 1'b1;
            if (left == 12'd1) in_frame <= 1'b0;
        end
    end
    wire h_idx = is_hdr && q_d[503] && q_d[511:508] == 4'd4;
    wire p_idx = is_pay && f_mine && f_type == 4'd4;

    // ---------------- job ----------------
    reg [7:0] fc;
    assign fault_code = fc;
    assign fault = |fc;
    reg [NW-1:0] j_n; reg [HW-1:0] j_kb; reg [9:0] j_k; reg [9:0] j_user; reg [7:0] j_tag;
    wire accept = h_idx && !busy && q_d[491:480] == 12'd64 && q_d[65:56] <= 10'd512;
    reg geo_go;                                       // one cycle after accept: geometry valid
    wire [4*HW-1:0] r_base1, r_base2; wire [4*10-1:0] r_skip; wire [4*NW-1:0] r_n1, r_n2; wire r_gfault;
    ot_hdc_v41x_idx_ring_ranges #(.HW(HW), .UW(10), .RSB(RSB), .RTAIL(RTAIL)) u_geo (
        .i_nkeys(j_n), .i_user(j_user), .cfg_key_base_block(j_kb),
        .o_base1(r_base1), .o_skip(r_skip), .o_n1(r_n1), .o_base2(r_base2), .o_n2(r_n2),
        .o_user_base(), .o_fault(r_gfault));
    wire [HW-1:0] g_base1 = r_base1[ST*HW +: HW], g_base2 = r_base2[ST*HW +: HW];
    wire [9:0] g_skip = r_skip[ST*10 +: 10];
    wire [NW-1:0] g_n1 = r_n1[ST*NW +: NW], g_n2 = r_n2[ST*NW +: NW];
    wire [NW-1:0] qsv = (j_n >> 5) << 3;
    wire [NW-1:0] g_len = g_n1 + g_n2;
    wire [NW+1:0] g_qstart = (NW+2)'(ST) * (NW+2)'(qsv);

    // ---------------- query store + loader ----------------
    reg [NB*128-1:0] qcodes [0:IH-1];
    reg [NB*8+16-1:0] qscw [0:IH-1];
    reg [6:0] q_words;                                // payload words received (64 = all)
    reg [5:0] ql_h;                                   // next head to load
    reg q_loaded;
    wire ql_ready;
    wire ql_v = busy && q_words == 7'd64 && !q_loaded && !fault;
    always @(posedge clk) if (p_idx) begin
        if (!f_idx[0]) qcodes[f_idx[5:1]] <= q_d[NB*128-1:0];
        else qscw[f_idx[5:1]] <= q_d[NB*8+16-1:0];
    end

    // ---------------- key stream ----------------
    wire s_valid; reg s_ready; wire [15:0] s_kv; wire [16*544-1:0] s_key; wire ks_busy;
    ot_hdc_v41x_idx_kstream_ring #(.NPC(NPC), .WB(WB), .GA(GA), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW),
                                   .BEATW(BEATW), .DW(256)) u_ks (
        .clk(clk), .rst_n(rst_n),
        .cmd_v(geo_go && g_len != 0 && !r_gfault), .cmd_base(g_base1), .cmd_skip(g_skip), .cmd_nkeys(g_n1),
        .cmd_base2(g_base2), .cmd_nkeys2(g_n2), .busy(ks_busy),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data),
        .o_valid(s_valid), .o_ready(s_ready), .o_kv(s_kv), .o_key(s_key),
        .cnt_keys_streamed(), .cnt_hbm_beats());
    // stream beat b holds stream keys 16 b .. 16 b + 15 = positions qstart - skip + 16 b + lane
    reg [9:0] j_skip;
    reg [NW:0] j_span;                                // skip + quarter length (stream keys)
    reg [NW+1:0] j_qstart;
    reg [NW-1:0] sb;                                  // stream beat index
    wire [NW+4:0] k0 = (NW+5)'(sb) << 4;              // first stream key of the beat
    wire drop = (k0 + 16) <= (NW+5)'(j_skip);         // every lane before the skip
    wire beat_last = (k0 + 16) >= (NW+5)'(j_span);
    reg [15:0] lane_ok;
    integer ln;
    always @(*) for (ln = 0; ln < 16; ln = ln + 1)
`ifdef SVCQ_IDX_MUT_SKIP
        lane_ok[ln] = s_kv[ln] && (k0 + ln) < (NW+5)'(j_span);
`else
        lane_ok[ln] = s_kv[ln] && (k0 + ln) >= (NW+5)'(j_skip) && (k0 + ln) < (NW+5)'(j_span);
`endif
    wire i_ready;
    wire [NW+4:0] lane0_pos = (NW+5)'(j_qstart) - (NW+5)'(j_skip) + k0;
    always @(*) s_ready = drop ? 1'b1 : (q_loaded && i_ready && !fault);
    wire i_valid = s_valid && !drop && q_loaded && !fault;

    // ---------------- scorer ----------------
    wire o_valid, o_last, pfault; reg o_ready;
    wire [15:0] o_kv, o_fault; wire [16*16-1:0] o_score;
    ot_hdc_v41x_idx_score_quarter #(.NK(4), .NB(NB), .IH(IH), .IW(IW), .MD(64)) u_sq (
        .clk(clk), .rst_n(rst_n),
        .ql_v(ql_v), .ql_ready(ql_ready), .ql_head({2'b0, ql_h}), .ql_codes(qcodes[ql_h[4:0]]),
        .ql_sc(qscw[ql_h[4:0]][NB*8-1:0]), .ql_w(qscw[ql_h[4:0]][NB*8 +: 16]),
        .i_valid(i_valid), .i_ready(i_ready), .i_last(beat_last), .i_first_index(IW'(lane0_pos)),
        .i_kv(lane_ok), .i_ref(16'd0), .i_keep(16'hffff), .i_key(s_key),
        .o_valid(o_valid), .o_ready(o_ready), .o_last(o_last), .o_kv(o_kv), .o_fault(o_fault),
        .o_score(o_score), .o_index(), .protocol_fault(pfault));

    // ---------------- x words ----------------
    reg hdr_due, empty_due;
    reg [19:0] hdr_base;
    always @(*) o_ready = !fault && !hdr_due && (!x_v || x_r);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0; geo_go <= 0; q_words <= 0; ql_h <= 0; q_loaded <= 0; sb <= 0; fc <= 0;
            x_v <= 0; hdr_due <= 0; empty_due <= 0;
            j_n <= 0; j_kb <= 0; j_k <= 0; j_user <= 0; j_tag <= 0; j_skip <= 0; j_span <= 0; j_qstart <= 0;
        end else begin
            geo_go <= accept;
            if (accept) begin
                busy <= 1'b1; q_words <= 0; ql_h <= 0; q_loaded <= 0; sb <= 0;
                j_n <= q_d[32:0]; j_kb <= q_d[55:33]; j_k <= q_d[65:56]; j_user <= q_d[458:449]; j_tag <= q_d[502:495];
            end
            if (p_idx) q_words <= q_words + 1'b1;
            if (ql_v && ql_ready) begin
                ql_h <= ql_h + 1'b1;
                if (ql_h == 6'd31) q_loaded <= 1'b1;
            end
            if (geo_go) begin
                j_skip <= g_skip; j_span <= (NW+1)'(g_skip) + (NW+1)'(g_len); j_qstart <= g_qstart;
                hdr_due <= 1'b1; empty_due <= g_len == 0;
`ifdef SVCQ_IDX_MUT_BASE
                hdr_base <= 20'(g_qstart - (NW+2)'(g_skip[3:0]) + 1'b1);
`else
                hdr_base <= 20'(g_qstart - (NW+2)'(g_skip[3:0]));
`endif
            end
            if (s_valid && s_ready) sb <= sb + 1'b1;
            // faults
            if (h_idx && busy) fc[0] <= 1'b1;
            if (h_idx && (q_d[491:480] != 12'd64 || q_d[65:56] > 10'd512)) fc[1] <= 1'b1;
            if (geo_go && r_gfault) fc[2] <= 1'b1;
            if (o_valid && o_ready && |(o_fault & o_kv)) fc[3] <= 1'b1;
            if (pfault) fc[4] <= 1'b1;
            if (s_valid && busy && (NW+5)'(sb) * 16 >= (NW+5)'(j_span) && !geo_go && hdr_due == 0 && j_span != 0)
                fc[5] <= 1'b1;
            if (p_idx && q_words >= 7'd64) fc[6] <= 1'b1;
            if (s_valid && !busy) fc[7] <= 1'b1;
            // output
            if (x_v && x_r) x_v <= 1'b0;
            if (!fault && (!x_v || x_r)) begin
                if (hdr_due) begin
                    x_v <= 1'b1; x_d <= {4'd1, j_tag, 468'd0, 2'(ST), j_k, hdr_base}; hdr_due <= 1'b0;
                end else if (empty_due && busy && !geo_go) begin
                    x_v <= 1'b1; x_d <= {4'd2, j_tag, 227'd0, 1'b1, 16'd0, 256'd0}; empty_due <= 1'b0; busy <= 1'b0;
                end else if (o_valid) begin
                    x_v <= 1'b1;
`ifdef SVCQ_IDX_MUT_LAST
                    x_d <= {4'd2, j_tag, 227'd0, 1'b0, o_kv, o_score};
`else
                    x_d <= {4'd2, j_tag, 227'd0, o_last, o_kv, o_score};
`endif
                    if (o_last) busy <= 1'b0;
                end
            end
        end
    end
endmodule
