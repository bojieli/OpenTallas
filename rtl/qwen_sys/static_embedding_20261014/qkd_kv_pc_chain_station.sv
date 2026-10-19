`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, KVJ-C3 2026-10-17 (kv_static_join_plan.md items 6 + 7): the per-PC STATION of the static PC chain, x128,
// ONE master (identity from the parent's pc / cfg_stack straps), a hard child of the per-PC wires-only parent
// qkd_static_kv_pc_path_fan (glue folded into the PC tile, as the plan's N3 es merge; no separate die tile).
//
// Chain: di (from the root qkd_kv_es_fan_root or the upstream station) -> pin flop c -> do.  One edge per hop.
// (1) Writer lane -> PC fan-out tap: the edge's two lanes carry their ACTUAL dest pc; a lane whose pc equals this PC's
//     strap becomes the PC's writer word wes = {sv, sv, address 29, data 256, v} (registered, +1).  The independent
//     expected descriptor (COMPILED expected pc) and the actual write context {1, identity, generation, full mask}
//     follow CTX_LAG = 1 edge later, so they meet the word at the controller after the es merge's +1 edge
//     (qkd_static_kv_pc_es_merge), exactly where the controller's native intake check compares them.  A word never
//     addressed to this PC leaves context bit 317 = 0, so the PC's embedding reads are never intake-checked.
// (2) Embedding slot player: the token-run start rides the chain; on its arrival the player latches the token / epoch
//     and plays the PC's compiled calendar from 8 boot constants (16-b offsets from the start capture, FFFF = never;
//     the calendar ends on the largest configured offset):
//        0 ISS  code read issue     1 RET  code return slot   2 CAP  station capture   3 TRN  station transfer
//        4 SISS scale read issue    5 SRET scale return slot  6 SCAP scale capture     7 STRN scale transfer
//     Code read: word_index = {stack, pc[4:1]}, half = pc[0] (qkd_embedding_static_map: every PC reads exactly one
//     code half of the token row).  Scale read: only on the token's scale home (stack token[10:9], pc token[8:4]),
//     word 0, half 0, scale 1.  Output X (a register) is high on the single edge start pin capture + 2 + OFF_X.
//     capture_slot / transfer_slot drive this PC's return station (qkd_embedding_static_return_head / _hop).
// Static: no credit, ready or wait; the calendar never moves.  Faults (sticky): two lanes or two expected descriptors
// for one PC on one edge, a start while the previous calendar still runs, a boot write while running.
// Size: ~779 (chain) + 704 (PC face, +99 lag) + ~200 (player) flops.
// MUT (bench only): 1 = lane pc compared on pc[3:0] only (misroute), 3 = PC 5 transfers one edge late,
//                   4 = scale home ignores the stack, 5 = context / expected not lagged (CTX_LAG 0).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_kv_pc_chain_station #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    pc,
    input  wire [1:0]    cfg_stack,
    input  wire [778:0]  di,
    output wire [778:0]  dout,
    // PC face: writer word + intake context / expected descriptor
    output reg  [287:0]  wes,
    output wire [317:0]  es_context,
    output reg           es_expected_valid,
    output reg  [60:0]   es_expected_identity,
    output reg  [28:0]   es_expected_address,
    output reg  [4:0]    es_expected_pc,
    output reg  [1:0]    es_expected_stack,
    // PC face: embedding read issue (qkd_static_kv_pc_es_merge)
    output reg           emb_issue_v,
    output reg  [17:0]   emb_token,
    output reg  [5:0]    emb_word_index,
    output reg           emb_half,
    output reg           emb_scale,
    output reg  [15:0]   emb_epoch,
    output reg           emb_return_slot,
    // the PC's return station
    output reg           capture_slot,
    output reg           transfer_slot,
    output reg           fault
);
    localparam integer F_V = 0, F_PC0 = 2, F_PC1 = 7, F_D0 = 12, F_D1 = 268, F_AD = 524, F_SV = 553, F_CTX = 554,
                       F_EV = 615, F_EPC0 = 617, F_EPC1 = 622, F_EST = 627, F_EID = 629, F_EAD = 690,
                       F_SS = 719, F_TOK = 720, F_EP = 738, F_CV = 754, F_CPC = 755, F_CRG = 760, F_CVL = 763, W = 779;
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    // ---- the hop register (pin flop) ----
    reg [W-1:0] c;
    always @(posedge ck) c[W-1:F_V+2] <= di[W-1:F_V+2];
    always @(posedge ck or negedge rs_q)
        if (!rs_q) c[F_V +: 2] <= 2'd0; else c[F_V +: 2] <= di[F_V +: 2];
    // valid-type control bits that are not data-qualified: register with reset
    reg ev0, ev1, ss, cv;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin ev0 <= 1'b0; ev1 <= 1'b0; ss <= 1'b0; cv <= 1'b0; end
        else begin ev0 <= di[F_EV]; ev1 <= di[F_EV + 1]; ss <= di[F_SS]; cv <= di[F_CV]; end
    assign dout = {c[W-1:F_CV+1], cv, c[F_CV-1:F_SS+1], ss, c[F_SS-1:F_EV+2], ev1, ev0, c[F_EV-1:0]};
    // ---- (1) fan-out tap ----
    wire [4:0] pm = (MUT == 1) ? 5'h0f : 5'h1f;
    wire h0 = c[F_V]     && ((c[F_PC0 +: 5] & pm) == (pc & pm));
    wire h1 = c[F_V + 1] && ((c[F_PC1 +: 5] & pm) == (pc & pm));
    wire x0 = ev0 && c[F_EPC0 +: 5] == pc;
    wire x1 = ev1 && c[F_EPC1 +: 5] == pc;
    reg        hit;                       // context valid (bit 317), lagged
    reg [60:0] ctx_id;
    // lag stage (CTX_LAG = 1): context / expected computed from the hop register one edge later than wes
    reg        hit_a, x_a; reg [60:0] ctx_a, eid_a; reg [28:0] ead_a; reg [4:0] epc_a; reg [1:0] est_a;
    always @(posedge ck) begin
        if (h0 | h1) wes[287:1] <= {c[F_SV], c[F_SV], c[F_AD +: 29], h0 ? c[F_D0 +: 256] : c[F_D1 +: 256]};
        if (h0 | h1) ctx_a <= c[F_CTX +: 61];
        if (x0 | x1) begin eid_a <= c[F_EID +: 61]; ead_a <= c[F_EAD +: 29]; epc_a <= x0 ? c[F_EPC0 +: 5] : c[F_EPC1 +: 5];
                           est_a <= c[F_EST +: 2]; end
    end
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin wes[0] <= 1'b0; hit_a <= 1'b0; x_a <= 1'b0; end
        else begin wes[0] <= h0 | h1; hit_a <= h0 | h1; x_a <= x0 | x1; end
    generate
        if (MUT == 5) begin : g_nolag
            always @(*) begin hit = hit_a; ctx_id = ctx_a; es_expected_valid = x_a; es_expected_identity = eid_a;
                              es_expected_address = ead_a; es_expected_pc = epc_a; es_expected_stack = est_a; end
        end else begin : g_lag
            always @(posedge ck) begin
                ctx_id <= ctx_a; es_expected_identity <= eid_a; es_expected_address <= ead_a;
                es_expected_pc <= epc_a; es_expected_stack <= est_a;
            end
            always @(posedge ck or negedge rs_q)
                if (!rs_q) begin hit <= 1'b0; es_expected_valid <= 1'b0; end
                else begin hit <= hit_a; es_expected_valid <= x_a; end
        end
    endgenerate
    assign es_context = {hit, ctx_id, {256{hit}}};
    // ---- (2) embedding slot player ----
    reg [15:0] r [0:7];
    reg [15:0] cnt, last; reg act; reg [17:0] tok; reg [15:0] ep;
    wire home = tok[8:4] == pc && (MUT == 4 || tok[10:9] == cfg_stack);
    wire [15:0] trn = (MUT == 3 && pc == 5'd5) ? r[3] + 16'd1 : r[3];
    integer k;
    always @(posedge ck) if (ss) begin tok <= c[F_TOK +: 18]; ep <= c[F_EP +: 16]; end
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin
            for (k = 0; k < 8; k = k + 1) r[k] <= 16'hffff;
            cnt <= 16'd0; last <= 16'd0; act <= 1'b0; fault <= 1'b0;
            emb_issue_v <= 1'b0; emb_return_slot <= 1'b0; capture_slot <= 1'b0; transfer_slot <= 1'b0;
            emb_token <= 18'd0; emb_epoch <= 16'd0; emb_word_index <= 6'd0; emb_half <= 1'b0; emb_scale <= 1'b0;
        end else begin
            if (cv && c[F_CPC +: 5] == pc) begin
                r[c[F_CRG +: 3]] <= c[F_CVL +: 16];
                if (c[F_CVL +: 16] != 16'hffff && c[F_CVL +: 16] > last) last <= c[F_CVL +: 16];
                if (act) fault <= 1'b1;
            end
            if (ss) begin
                if (act) fault <= 1'b1;
                act <= 1'b1; cnt <= 16'd0;
            end else if (act) begin
                cnt <= cnt + 16'd1;
                if (cnt == last) act <= 1'b0;      // the calendar ends on its last configured event
            end
            emb_token <= tok; emb_epoch <= ep;
            emb_issue_v     <= act && (cnt == r[0] || (home && cnt == r[4]));
            emb_return_slot <= act && (cnt == r[1] || (home && cnt == r[5]));
            capture_slot    <= act && (cnt == r[2] || (home && cnt == r[6]));
            transfer_slot   <= act && (cnt == trn  || (home && cnt == r[7]));
            if (act && cnt == r[0]) begin emb_word_index <= {cfg_stack, pc[4:1]}; emb_half <= pc[0]; emb_scale <= 1'b0; end
            else if (act && home && cnt == r[4]) begin emb_word_index <= 6'd0; emb_half <= 1'b0; emb_scale <= 1'b1; end
            if ((h0 && h1) || (x0 && x1)) fault <= 1'b1;
        end
endmodule
