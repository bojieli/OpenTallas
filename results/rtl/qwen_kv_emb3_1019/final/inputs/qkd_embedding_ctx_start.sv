`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, KV-EMB2 2026-10-19 (tree K.STA.EMB): allocation-owned embedding fill start (MU build default).
//
// Problem (frozen 5f2): the row fill (join4_cal start, row_tx fill_begin/token/epoch, the fan root's emb_start/token/epoch)
// starts on the compute die's kind-15 RESULT (svc[24], NEXT token svc[109:92], OLD terminal TAG epoch svc[89:74]).  That is
// wrong for every prompt position (the HOST scheduler takes the next PROMPT token, not RESULT's next token), never fires
// for the first token (no RESULT), and labels the row with the previous step's epoch, while the compute die's embedding
// face expects the epoch of the HOST context it retained (qfd_host_native_context_rx host_tag / host_epoch).
//
// Source fact: the allocator (ot_qwen_tp8_token_epoch_allocator[_mu] inside qkd_host_lifecycle_collected[_mu]), the prompt
// scheduler and the cohort all sit in the KV-die HOST root.  The full owner O61 = {gen2, TAG59 = {epoch16, stage6 = 0,
// token18, position13, segment6 = 0}} is born on THIS die and already leaves the HOST on its compiled port-1 kind-12
// CONTEXT record (qkd_host_native_context_tx: DATA[58:0] TAG59, DATA[60:59] generation; header epoch == TAG epoch), the
// very record the compute die decodes into its expected identity.  So no compute->KV PREP codec, no kind-15 subtype, no
// new D2D reservation is needed: this module taps the HOST record face (the die fork of record_tx_v / record_tx_observed_v
// / record_tx header + DATA[60:0], the bus HOST -> d2d port 1) and starts the fill from the SAME record the compute die
// pairs with.  RESULT keeps its real meaning (HOST POST / CQ / health) and never starts a fill here.
//
// Rule: a valid (tx_v && observed_v) kind-12 record whose owner differs from the last started owner -> one start pulse with
// that owner's token / epoch (registered outputs); a repeated owner (the context port re-sends its held request every
// token run) starts nothing.  A missing new context leaves the row unstaged, so row_tx faults at its header slot (fail
// closed; the slot never moves).  No credit, ready or wait.
// Faults (sticky): a kind-12 record with a nonzero reserved / beat field, layer != 63, header epoch != TAG epoch, stage or
// segment != 0, token >= 151936, or a new owner while the previous start is younger than MIN_GAP edges (the compiler
// spaces token runs; a closer pair is a schedule fault, never queued).
// Edges: tap register 1 (the face capture, safe-design item 1) + output register 1 = start 2 edges after the record leaves
// the HOST pin register (priced by the die schedule against first_emb_send; see results/rtl/qwen_kv_emb2_1019/README.md).
// State: 99 face + 61 owner + 1 have + 18 + 16 + 1 start + 10 gap + 1 fault = 207 flops; no SRAM, no fanout > 32 except the
// start/token/epoch output register (consumers capture it in their own landing flops; die relays add the fork).
// MUT (bench only): 1 = no repeated-owner suppression; 2 = token from the wrong TAG field (position); 3 = no header-epoch
//                   check; 4 = no kind check (a kind-13 AUTH record starts a fill).
// MUT 5/6/7 remove prior-fault / actual-row-open / early-gap veto, respectively.
// Admission is fail closed: an early new owner or sticky prior fault never changes start/token/epoch/owner.
// MIN_GAP is a consistency floor; the compiler must independently place the next start after full row drain.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_embedding_ctx_start #(
    parameter integer MUT = 0,
    parameter integer MIN_GAP = 66          // >= the 65 row records + 1: a second fill inside one row's send window faults
) (
    input  wire          ck,
    input  wire          rst_n,
    // HOST record face fork (qkd_host_record_port tx_*): header [547:512] and DATA[60:0] of the registered record
    input  wire          row_open,           // existing row_tx armed state: static overlap fault, never waits
    input  wire          ctx_v,
    input  wire          ctx_observed_v,
    input  wire [35:0]   ctx_hdr,              // record[547:512] = {res5 [35:31], kind4 [30:27], layer6 [26:21], epoch16 [20:5], beat5 [4:0]}
    input  wire [60:0]   ctx_owner,            // record[60:0]    = {gen2, TAG59}
    // fill start (to join4_cal start, row_tx fill_*, the fan root emb_* via px_*)
    output reg           start,
    output reg  [17:0]   token,
    output reg  [15:0]   epoch,
    output wire [60:0]   owner,                // last started owner (retained; diagnostic / health)
    output reg           fault
);
    reg         qv, qo;
    reg [35:0]  qh;
    reg [60:0]  qd;
    reg [60:0]  last;
    reg         have;
    reg [9:0]   gap;
    assign owner = last;
    wire [58:0] tag   = qd[58:0];
    wire [15:0] t_ep  = tag[58:43];
    wire [5:0]  t_st  = tag[42:37];
    wire [17:0] t_tok = (MUT == 2) ? {5'd0, tag[18:6]} : tag[36:19];
    wire [5:0]  t_seg = tag[5:0];
    wire        is12  = (MUT == 4) ? 1'b1 : (qh[30:27] == 4'd12);   // kind
    wire        take  = qv && qo && is12;
    wire        hdr_ok = qh[35:31] == 5'd0 && qh[26:21] == 6'd63 && qh[4:0] == 5'd0 && (MUT == 3 || qh[20:5] == t_ep);
    wire        own_ok = t_st == 6'd0 && t_seg == 6'd0 && tag[36:19] < 18'd151936;
    wire        fresh  = !have || qd != last || MUT == 1;
    wire        admit = take && hdr_ok && own_ok && fresh && (MUT == 5 || !fault) && (MUT == 7 || gap == 10'd0) && (MUT == 6 || !row_open);
    // face capture (plain D, no reset: the data face; valid bits carry the reset)
    always @(posedge ck) begin qh <= ctx_hdr; qd <= ctx_owner; end
    always @(posedge ck) if (admit) begin token <= t_tok; epoch <= t_ep; end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            qv <= 1'b0; qo <= 1'b0; start <= 1'b0; last <= 61'd0; have <= 1'b0; gap <= 10'd0; fault <= 1'b0;
        end else begin
            qv <= ctx_v; qo <= ctx_observed_v;
            start <= 1'b0;
            if (gap != 10'd0) gap <= gap - 10'd1;
            if (take) begin
                if (!hdr_ok || !own_ok) fault <= 1'b1;
                else if (fresh) begin
                    if (gap != 10'd0 || row_open) fault <= 1'b1;
                    if (admit) begin
                        start <= 1'b1; last <= qd; have <= 1'b1; gap <= 10'(MIN_GAP);
                    end
                end
            end
        end
endmodule
