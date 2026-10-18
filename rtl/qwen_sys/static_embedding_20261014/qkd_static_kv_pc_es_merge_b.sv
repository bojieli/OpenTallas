`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, RTL-BUILD-KV/BOOT 2026-10-18 (results/arch/qwen_kv_boot_path_1018/note.md): the per-PC es merge with the
// BOOT source.  qkd_static_kv_pc_es_merge (static writer wes + the embedding read endpoint) plus a third source, the
// PC's HOST slice (qkd_host_pc_slice_die, unchanged): its ctrl_es carries the boot-window traffic of this PC --
// the cold-boot scratch check (qkd_hbm_boot_pc), HOST ingest writes (KV / any host sector, qkd_host_ingest_station)
// and the embedding table's boot writes (station_b land_es -> the slice's landing source) -- and it needs the
// controller's er (credits, the check's read-back) and completions (its ownership ledger) back.
//
// Ownership is by PHASE, not arbitration: own = !emb_boot_ready (registered; emb_ready = est[0] from qkd_embgw_boot_s,
// the die's image-ready word every PC already receives).  emb_ready rises only after the HOST commit-order ledger
// retired every boot write's real completion (BOOT_END is sent after it) and the image sums matched, so the slice's
// traffic, credits and completions are all home when the face flips.
//   own = 1 (boot window): the slice's word passes (hes pin flop +1, select register +1); er and completion_v / we go
//                          to the slice (her / hcv / hcw, output registers, +1); the embedding endpoint sees er = 0.
//   own = 0 (run):         exactly qkd_static_kv_pc_es_merge: same select register, same edges, er straight to the
//                          endpoint (one AND gate, no edge); her / hcv / hcw = 0.
// Faults (sticky, OR'd into fault): any two sources valid on one edge (writer word wins the register, as before; the
// slice word beats an embedding word), a slice word in the run phase, a writer word in the boot window.
// Runtime equivalence: with emb_boot_ready = 1 and hes idle, es / beat_* / corrected / emb_outstanding / fault equal
// qkd_static_kv_pc_es_merge's on every edge (tb_kv_boot_chain lockstep).  No edge is added to the writer -> controller
// es path, the embedding issue -> controller path or the embedding return slot.
// MUT (bench only): 1..3 as qkd_static_kv_pc_es_merge; 4 = er not steered (the endpoint also sees boot-window er);
// 5 = no run-phase slice-word fault; 6 = completions not steered (the slice also sees run-phase completions).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_static_kv_pc_es_merge_b #(
    parameter integer ROW0 = 24427,
    parameter integer MUT  = 0,
    parameter integer RETIME = 1
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    pc,
    input  wire [1:0]    cfg_stack,
    input  wire [287:0]  wes,
    input  wire          emb_boot_ready,
    input  wire          emb_issue_v,
    input  wire [17:0]   emb_token,
    input  wire [5:0]    emb_word_index,
    input  wire          emb_half,
    input  wire          emb_scale,
    input  wire [15:0]   emb_epoch,
    input  wire          emb_return_slot,
    // the HOST slice face (boot window)
    input  wire [287:0]  hes,
    output reg  [260:0]  her,
    input  wire          completion_v,
    input  wire          completion_we,
    output reg           hcv,
    output reg           hcw,
    // the controller face
    output reg  [287:0]  es,
    input  wire [260:0]  er,
    output wire          beat_v,
    output wire [255:0]  beat_data,
    output wire [17:0]   beat_token,
    output wire [5:0]    beat_word,
    output wire          beat_half,
    output wire          beat_scale,
    output wire [15:0]   beat_epoch,
    output wire          corrected,
    output wire          emb_outstanding,
    output wire          fault
);
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    // phase: own = boot window (the slice owns the controller face)
    reg own;
    always @(posedge ck or negedge rs_q) if (!rs_q) own <= 1'b1; else own <= !emb_boot_ready;
    // slice word pin flop
    reg [287:0] hq;
    always @(posedge ck) hq[287:1] <= hes[287:1];
    always @(posedge ck or negedge rs_q) if (!rs_q) hq[0] <= 1'b0; else hq[0] <= hes[0];
    // the embedding endpoint (unchanged master), er steered by phase
    wire [260:0] er_e = (own && MUT != 4) ? 261'd0 : er;
    wire [287:0] ees;
    wire         emb_fault;
    qkd_embedding_static_pc_strap #(.ROW0(ROW0), .MUT(MUT == 2 ? 2 : 0), .RETIME(RETIME)) u_emb (.ck(ck), .rst_n(rs_q),
        .boot_ready(emb_boot_ready), .strap_stack(cfg_stack), .strap_pc(pc),
        .issue_v(emb_issue_v), .token(emb_token), .word_index(emb_word_index), .half(emb_half), .scale(emb_scale),
        .epoch(emb_epoch), .return_slot(emb_return_slot), .es(ees), .er(er_e),
        .beat_v(beat_v), .beat_data(beat_data), .beat_token(beat_token), .beat_word(beat_word), .beat_half(beat_half),
        .beat_scale(beat_scale), .beat_epoch(beat_epoch), .corrected(corrected), .fault(emb_fault),
        .outstanding(emb_outstanding));
    // registered 3:1 slot select (never an arbitration: the schedule / phase makes the slots disjoint)
    reg m_fault;
    wire w_first = (MUT == 3) ? !ees[0] : wes[0];
    always @(posedge ck) es[287:1] <= w_first ? wes[287:1] : (hq[0] ? hq[287:1] : ees[287:1]);
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin es[0] <= 1'b0; m_fault <= 1'b0; end
        else begin
            es[0] <= wes[0] | ees[0] | hq[0];
            if (wes[0] && ees[0] && MUT != 1) m_fault <= 1'b1;
            if (hq[0] && (wes[0] || ees[0])) m_fault <= 1'b1;
            if (hq[0] && !own && MUT != 5) m_fault <= 1'b1;
            if (wes[0] && own) m_fault <= 1'b1;
        end
    // slice return face (output registers)
    wire sl = own || MUT == 6;
    always @(posedge ck) her[258:1] <= er[258:1];
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin her[0] <= 1'b0; her[259] <= 1'b0; her[260] <= 1'b0; hcv <= 1'b0; hcw <= 1'b0; end
        else begin
            her[0] <= own && er[0]; her[259] <= own && er[259]; her[260] <= own && er[260];
            hcv <= sl && completion_v; hcw <= sl && completion_we;
        end
    assign fault = m_fault | emb_fault;
endmodule
