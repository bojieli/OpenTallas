`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_reindex_chain: the DS-ROM re-index layer's index path with BOTH adopted re-index levers
// on, as one unit (integration checkpoint 2026-10-04, branch claude/dsrom-integration-20261004):
//
//   candidate-block gather (ot_hdc_v41x_idx_kgather_ps, one per HBM3E stack = select quarter,
//   position-slotted lists)  ->  [scorer port: key beats out, scored beats in]  ->
//   mask-drop + streaming top-k select (ot_hdc_v41x_sel_mdrop_top, MDROP)
//
// The levers were measured apart (results/rtl/dsrom_reindex_candidates_20261004: the gather with
// o_ready tied high, the select on golden scores in gather order).  Joining them needs four
// things neither unit has, all added here:
//   * LAST: the gather emits no end-of-list beat; the select needs each quarter's last beat.  A
//     per-quarter block count marks the beat that completes cmd_n blocks; a quarter with
//     cmd_n = 0 sends one empty last beat (the select's contract).
//   * POSITIONS: key j of block b of quarter q is position qbase_q + 8 b + j (the gather's
//     layout); they travel with the beat to the scorer and the select.
//   * KEEP: the gather reads whole 8-key blocks, and the newest candidate block may hold
//     positions after the query's own (not yet written: causal).  keep = lane valid AND
//     position <= the job's position, applied by the mask-drop stage, so MDROP must stay on with
//     the gather (at position 1,048,575 the newest block is full and nothing is dropped).
//   * REPLAY: the select's overflow fallback pulses rep_req (up to twice) and needs the whole
//     segment again; the gather is re-issued from its (still held) list slot once its previous
//     pass has drained, instead of the as-built source's vector-memory re-read.
// start may be issued once the previous job is done and the gathers are idle (else `fault`); `done` is held from the job's last
// out_last until the next start.
// ---------------------------------------------------------------------------
module ot_dsrom_reindex_chain #(
    parameter integer Q    = 4,        // stacks = select quarters
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer AW   = 28,       // HBM sector address
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer LMW  = 11,
    parameter integer DF   = 8,
    parameter integer LSW  = 3,        // list slots 2^LSW (>= WIN); 0 = as-built single list
    parameter integer IW   = 20,       // position bits
    parameter integer K    = 512,
    parameter integer SAW  = 8,        // select line-memory words per quarter (log2)
    parameter integer MDROP = 1,
    localparam integer SLW = (LSW > 0) ? LSW : 1,
    localparam integer KW = $clog2(K + 1),
    localparam integer EW = 17 + IW
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // candidate lists (written ahead by the candidate source)
    input  wire [Q-1:0]          lw_v,
    input  wire [SLW-1:0]        lw_slot,
    input  wire [LMW-1:0]        lw_addr,
    input  wire [Q*LBW-1:0]      lw_blk,
    // job
    input  wire                  start,
    input  wire [SLW-1:0]        start_slot,
    input  wire [IW-1:0]         start_pos,
    input  wire [KW-1:0]         start_k,
    input  wire [Q*HW-1:0]       start_base,
    input  wire [Q*10-1:0]       start_skip,
    input  wire [Q*(LMW+1)-1:0]  start_n,
    input  wire [Q*IW-1:0]       start_qbase,
    output reg                   done,
    output wire                  busy,
    output reg                   fault,
    // HBM (per stack NPC pseudo-channels)
    output wire [Q*NPC-1:0]      req_v,
    input  wire [Q*NPC-1:0]      req_rdy,
    output wire [Q*NPC*AW-1:0]   req_addr,
    output wire [Q*NPC*LENW-1:0] req_len,
    output wire [Q*NPC*TAGW-1:0] req_tag,
    input  wire [Q*NPC-1:0]      rsp_v,
    output wire [Q*NPC-1:0]      rsp_rdy,
    input  wire [Q*NPC*TAGW-1:0] rsp_tag,
    input  wire [Q*NPC*BEATW-1:0] rsp_beat,
    input  wire [Q*NPC*DW-1:0]   rsp_data,
    // scorer: key beats out (16 keys = 2 blocks a beat) ...
    output wire [Q-1:0]          ks_valid,
    input  wire [Q-1:0]          ks_ready,
    output wire [Q*16-1:0]       ks_lv,
    output wire [Q*16*544-1:0]   ks_key,
    output wire [Q*16*IW-1:0]    ks_idx,
    output wire [Q-1:0]          ks_last,
    // ... scored beats in (same beats, same order, BF16 scores)
    input  wire [Q-1:0]          sc_valid,
    output wire [Q-1:0]          sc_ready,
    input  wire [Q*16-1:0]       sc_lv,
    input  wire [Q*16*16-1:0]    sc_val,
    input  wire [Q*16*IW-1:0]    sc_idx,
    input  wire [Q-1:0]          sc_last,
    // selection (per quarter, packed, ascending positions)
    output wire [Q-1:0]          out_valid,
    input  wire [Q-1:0]          out_ready,
    output wire [Q-1:0]          out_last,
    output wire [Q*16-1:0]       out_lv,
    output wire [Q*16*16-1:0]    out_val,
    output wire [Q*16*IW-1:0]    out_idx,
    output wire [Q*16-1:0]       out_ninf,
    output wire                  ovf,
    output wire                  short,
    output reg  [3:0]            passes,     // gather passes of the current job (1 + replays)
    output wire [Q*48-1:0]       cnt_keys,
    output wire [Q*48-1:0]       cnt_beats
);
    // -- job registers ------------------------------------------------------------------------
    reg            run;
    reg [SLW-1:0]  j_slot;
    reg [IW-1:0]   j_pos;
    reg [KW-1:0]   j_k;
    reg [HW-1:0]   j_base [0:Q-1];
    reg [9:0]      j_skip [0:Q-1];
    reg [LMW:0]    j_n    [0:Q-1];
    reg [IW-1:0]   j_qb   [0:Q-1];
    reg            issue;                  // gather command this cycle (all stacks)
    reg [1:0]      rep_pend;               // replays requested, not yet re-issued
    reg [LMW:0]    blks   [0:Q-1];         // blocks passed to the scorer this pass
    reg [Q-1:0]    empty_due;              // quarter with n = 0 owes its empty last beat
    reg [Q-1:0]    qlast;                  // quarter's out_last seen
    reg [31:0]     ks_out [0:Q-1];         // key beats sent this pass
    reg [31:0]     sc_in  [0:Q-1];         // scored beats taken this pass
    wire [Q-1:0]   g_busy, g_fault, g_valid, g_ready;
    wire [Q*16-1:0] g_kv;
    wire [Q*2*LBW-1:0] g_blk;

    genvar s, l;
    generate for (s = 0; s < Q; s = s + 1) begin : g_stack
        ot_hdc_v41x_idx_kgather_ps #(.NPC(NPC), .WB(WB), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW),
            .BEATW(BEATW), .DW(DW), .LBW(LBW), .LMW(LMW), .DF(DF), .LSW(LSW)) u_kg (
            .clk(clk), .rst_n(rst_n), .lw_v(lw_v[s]), .lw_slot(lw_slot), .lw_addr(lw_addr),
            .lw_blk(lw_blk[s*LBW +: LBW]),
            .cmd_v(issue), .cmd_slot(j_slot), .cmd_base(j_base[s]), .cmd_skip(j_skip[s]), .cmd_n(j_n[s]),
            .busy(g_busy[s]), .fault(g_fault[s]),
            .req_v(req_v[s*NPC +: NPC]), .req_rdy(req_rdy[s*NPC +: NPC]),
            .req_addr(req_addr[s*NPC*AW +: NPC*AW]), .req_len(req_len[s*NPC*LENW +: NPC*LENW]),
            .req_tag(req_tag[s*NPC*TAGW +: NPC*TAGW]),
            .rsp_v(rsp_v[s*NPC +: NPC]), .rsp_rdy(rsp_rdy[s*NPC +: NPC]),
            .rsp_tag(rsp_tag[s*NPC*TAGW +: NPC*TAGW]), .rsp_beat(rsp_beat[s*NPC*BEATW +: NPC*BEATW]),
            .rsp_data(rsp_data[s*NPC*DW +: NPC*DW]),
            .o_valid(g_valid[s]), .o_ready(g_ready[s]), .o_kv(g_kv[s*16 +: 16]),
            .o_key(ks_key[s*16*544 +: 16*544]), .o_blk(g_blk[s*2*LBW +: 2*LBW]),
            .cnt_keys_streamed(cnt_keys[s*48 +: 48]), .cnt_hbm_beats(cnt_beats[s*48 +: 48]));
        // key beat: the gather's beat, or the empty last beat of an empty quarter
        wire [1:0] nb = g_kv[s*16 + 8] ? 2'd2 : 2'd1;
        assign ks_valid[s] = run && (g_valid[s] || empty_due[s]);
        assign g_ready[s]  = ks_ready[s] && !empty_due[s];
        assign ks_lv[s*16 +: 16] = empty_due[s] ? 16'd0 : g_kv[s*16 +: 16];
        assign ks_last[s]  = empty_due[s] || (blks[s] + nb == j_n[s]);
        for (l = 0; l < 16; l = l + 1) begin : g_lane
            assign ks_idx[(s*16 + l)*IW +: IW] =
                j_qb[s] + {g_blk[s*2*LBW + (l/8)*LBW +: LBW], 3'd0} + IW'(l % 8);
        end
    end endgenerate

    // -- keep: lane valid and not after the job's position (causal) -----------------------------
    reg [Q*16-1:0] keep;
    integer qk, lk;
    always @* begin
        for (qk = 0; qk < Q; qk = qk + 1)
            for (lk = 0; lk < 16; lk = lk + 1)
                keep[qk*16 + lk] = sc_lv[qk*16 + lk] && (sc_idx[(qk*16 + lk)*IW +: IW] <= j_pos);
    end

    // -- mask-drop + select ----------------------------------------------------------------------
    wire [Q-1:0]       mem_we, mem_re;
    wire [Q*SAW-1:0]   mem_waddr, mem_raddr;
    wire [Q*16*EW-1:0] mem_wdata;
    reg  [Q*16*EW-1:0] mem_rdata;
    wire               rep_req, sel_busy;
    wire [Q*3*(SAW+1)-1:0] stats;
    ot_hdc_v41x_sel_mdrop_top #(.Q(Q), .W(16), .IW(IW), .K(K), .AW(SAW), .MDROP(MDROP)) u_sel (
        .clk(clk), .rst_n(rst_n), .in_valid(sc_valid & {Q{run}}), .in_ready(sc_ready), .in_last(sc_last),
        .in_lv(sc_lv), .in_keep(keep), .in_val(sc_val), .in_idx(sc_idx), .in_k(j_k),
        .out_valid(out_valid), .out_ready(out_ready), .out_last(out_last), .out_lv(out_lv), .out_val(out_val),
        .out_idx(out_idx), .out_ninf(out_ninf),
        .mem_we(mem_we), .mem_waddr(mem_waddr), .mem_wdata(mem_wdata), .mem_re(mem_re),
        .mem_raddr(mem_raddr), .mem_rdata(mem_rdata), .rep_req(rep_req), .ovf(ovf), .busy(sel_busy),
        .stats(stats), .short(short));
    // the select's line memories: one 1R1W synchronous-read memory per quarter
    reg [16*EW-1:0] lm [0:Q*(1 << SAW)-1];
    integer mq;
    always @(posedge clk)
        for (mq = 0; mq < Q; mq = mq + 1) begin
            if (mem_we[mq]) lm[mq*(1 << SAW) + mem_waddr[SAW*mq +: SAW]] <= mem_wdata[16*EW*mq +: 16*EW];
            if (mem_re[mq]) mem_rdata[16*EW*mq +: 16*EW] <= lm[mq*(1 << SAW) + mem_raddr[SAW*mq +: SAW]];
        end

    assign busy = run || (|g_busy) || sel_busy;
    wire [Q-1:0] ks_fire = ks_valid & ks_ready;
    wire [Q-1:0] sc_fire = sc_valid & sc_ready & {Q{run}};
    wire [Q-1:0] olast_fire = out_valid & out_ready & out_last;
    reg  [Q-1:0] drained;
    integer q;
    always @* for (q = 0; q < Q; q = q + 1) drained[q] = !g_busy[q] && (ks_out[q] == sc_in[q]) && !empty_due[q];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; done <= 1'b0; fault <= 1'b0; issue <= 1'b0; rep_pend <= 2'd0; passes <= 4'd0;
            empty_due <= 0; qlast <= 0; j_slot <= 0; j_pos <= 0; j_k <= 0;
            for (q = 0; q < Q; q = q + 1) begin
                blks[q] <= 0; ks_out[q] <= 0; sc_in[q] <= 0;
                j_base[q] <= 0; j_skip[q] <= 0; j_n[q] <= 0; j_qb[q] <= 0;
            end
        end else begin
            issue <= 1'b0;
            if (|g_fault) fault <= 1'b1;
            if (start) begin
                // the select takes the next segment once every quarter emitted out_last (its contract);
                // its `busy` may still be high then, so it is not a start condition
                if (run || (|g_busy)) fault <= 1'b1;
                run <= 1'b1; done <= 1'b0; issue <= 1'b1; rep_pend <= 2'd0; passes <= 4'd1; qlast <= 0;
                j_slot <= start_slot; j_pos <= start_pos; j_k <= start_k;
                for (q = 0; q < Q; q = q + 1) begin
                    j_base[q] <= start_base[q*HW +: HW]; j_skip[q] <= start_skip[q*10 +: 10];
                    j_n[q] <= start_n[q*(LMW+1) +: LMW+1]; j_qb[q] <= start_qbase[q*IW +: IW];
                    empty_due[q] <= (start_n[q*(LMW+1) +: LMW+1] == 0);
                    blks[q] <= 0; ks_out[q] <= 0; sc_in[q] <= 0;
                end
            end else if (run) begin
                for (q = 0; q < Q; q = q + 1) begin
                    if (ks_fire[q]) begin
                        ks_out[q] <= ks_out[q] + 1;
                        if (empty_due[q]) empty_due[q] <= 1'b0;
                        else blks[q] <= blks[q] + (g_kv[q*16 + 8] ? 2 : 1);
                    end
                    if (sc_fire[q]) sc_in[q] <= sc_in[q] + 1;
                end
                if (rep_req) rep_pend <= rep_pend + 2'd1;
                // re-issue the whole segment once the previous pass has drained into the select
                if (rep_pend != 0 && !rep_req && !issue && (&drained)) begin
                    rep_pend <= rep_pend - 2'd1; issue <= 1'b1; passes <= passes + 4'd1;
                    for (q = 0; q < Q; q = q + 1) begin
                        blks[q] <= 0; ks_out[q] <= 0; sc_in[q] <= 0; empty_due[q] <= (j_n[q] == 0);
                    end
                end
                qlast <= qlast | olast_fire;
                if (&(qlast | olast_fire)) begin run <= 1'b0; done <= 1'b1; end
            end
        end
    end
endmodule
