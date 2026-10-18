`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, KVJ-C 2026-10-17 (kv_static_join_plan.md N3): the per-PC es merge, x128, one hard child of the per-PC
// wires-only parent (qkd_static_kv_pc_path_emb), hardened once.
//
// Both the static KV writer (its lane -> dest-PC es word {sv, sv, address 29, data 256, v}) and the token's embedding
// reads (qkd_embedding_static_pc: {0, 0, bank, col, row, 0, v}) drive the one controller es[287:0] face of a PC.  The
// compiler makes their slots disjoint, so this is a REGISTERED 2:1 SLOT SELECT, never an arbitration: both valid on one
// edge latches fault (and the writer's word wins the register so a KV write is never silently dropped; the schedule is
// not moved).  Added edge: +1 on the writer -> controller es path and +1 on the embedding issue -> controller path
// (the compiler adds 1 to both issue-to-controller latencies and to the embedding return_slot).
// The embedding endpoint is qkd_embedding_static_pc_strap: qkd_embedding_static_pc with the stack / PC identity taken
// from the parent's straps (pc[4:0], cfg_stack[1:0]) instead of parameters, so ONE master serves all 128 PCs; the
// bench tb_qkd_static_kv_pc_es_merge proves it lock-step equal to qkd_embedding_static_pc(STACK, PC) for the strapped
// identity.  Size: 288 (merge) + ~350 (endpoint) flops.
// MUT (bench only): 1 = no conflict fault; 2 = the strap identity check ignored; 3 = the embedding word wins a conflict.
// ---------------------------------------------------------------------------------------------------------------------
// KVJ-G2b 10-17 (coordinator 0cx+++ (b): the HBM side is elastic, the fixed return slot holds only after a re-timing
// buffer): RETIME=1 holds the controller's er word when it arrives BEFORE the compiled return_slot (one outstanding read,
// so one 260-b register) and presents it at the slot; an er on the slot edge passes straight through (the RETIME=0
// behaviour, so every exact-slot schedule is unchanged).  Faults: the slot with no word (late beyond the schedule), a
// second word while one is held, a word with no read pending, er[260] / er[258] as before.  The compiler's return_slot
// is then the WORST-case controller latency, not an exact one.  RETIME=0 = the original exact-arrival endpoint
// (lock-step equal to qkd_embedding_static_pc).
module qkd_embedding_static_pc_strap #(
    parameter integer ROW0 = 24427,
    parameter integer MUT  = 0,
    parameter integer RETIME = 0
)(input wire ck,rst_n,boot_ready,
  input wire [1:0] strap_stack,input wire [4:0] strap_pc,
  input wire issue_v,input wire [17:0] token,input wire [5:0] word_index,
  input wire half,scale,input wire [15:0] epoch,
  input wire return_slot,
  output reg [287:0] es,input wire [260:0] er,
  output reg beat_v,output reg [255:0] beat_data,
  output reg [17:0] beat_token,output reg [5:0] beat_word,
  output reg beat_half,beat_scale,output reg [15:0] beat_epoch,
  output reg corrected,output reg fault,output wire outstanding);
    // qkd_embedding_static_pc term for term; only `stack!=STACK||pc!=PC` reads the straps
    wire [24:0] sector;
    wire [1:0] stack;
    wire [4:0] pc,bank,col;
    wire [18:0] row;
    wire valid_address;
    qkd_embedding_static_map #(.ROW0(ROW0)) u_map(
        .token(token),.word_index(word_index),.half(half),.scale(scale),
        .logical_sector(sector),.stack(stack),.pc(pc),.bank(bank),.col(col),
        .row(row),.valid_address(valid_address));
    reg pending;
    reg [17:0] token_q;
    reg [5:0] word_q;
    reg half_q,scale_q;
    reg [15:0] epoch_q;
    wire wrong_home=(MUT==2)?1'b0:(stack!=strap_stack||pc!=strap_pc);
    assign outstanding=pending;
    // RETIME: the held word (early arrival) or the word on the slot edge
    reg h_v;
    reg [259:1] h_d;
    wire [260:0] eff=(RETIME!=0&&!er[0]&&h_v)?{er[260],h_d,1'b1}:er;
    always @(posedge ck) begin
        es[287:1] <= {1'b0,1'b0,bank,col,row,256'd0};
        if(issue_v) begin token_q<=token;word_q<=word_index;half_q<=half;scale_q<=scale;epoch_q<=epoch;end
        beat_data<=eff[256:1];beat_token<=token_q;beat_word<=word_q;
        beat_half<=half_q;beat_scale<=scale_q;beat_epoch<=epoch_q;
        if(RETIME!=0&&er[0]&&!return_slot) h_d<=er[259:1];
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin pending<=0;beat_v<=0;corrected<=0;fault<=0;es[0]<=0;h_v<=0;end
        else begin
            es[0]<=issue_v;
            beat_v<=return_slot;
            corrected<=return_slot&&eff[257];
            if(return_slot) pending<=0;
            if(issue_v) pending<=1;
            if(issue_v&&(!boot_ready||pending||!valid_address||wrong_home)) fault<=1;
            if(RETIME==0) begin
                if(return_slot!=er[0] || (return_slot&&!pending) || er[260] || (return_slot&&er[258])) fault<=1;
            end else begin
                if(er[0]&&!return_slot) begin h_v<=1; if(!pending||h_v) fault<=1; end
                if(return_slot) h_v<=0;
                if((return_slot&&!eff[0]) || (return_slot&&er[0]&&h_v) || (return_slot&&!pending) || er[260] ||
                   (return_slot&&eff[258])) fault<=1;
            end
        end
endmodule

module qkd_static_kv_pc_es_merge #(
    parameter integer ROW0 = 24427,
    parameter integer MUT  = 0,
    parameter integer RETIME = 1          // KVJ-G2b: the die element re-times an early controller word onto its slot
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    pc,              // parent straps (the pc_path's own pc / cfg_stack)
    input  wire [1:0]    cfg_stack,
    // static writer word for this PC
    input  wire [287:0]  wes,
    // embedding read issue (compiled; the RESULT token) and its compiled return slot
    input  wire          emb_boot_ready,
    input  wire          emb_issue_v,
    input  wire [17:0]   emb_token,
    input  wire [5:0]    emb_word_index,
    input  wire          emb_half,
    input  wire          emb_scale,
    input  wire [15:0]   emb_epoch,
    input  wire          emb_return_slot,
    // the controller face
    output reg  [287:0]  es,
    input  wire [260:0]  er,
    // the retained beat for the return-hop train (qkd_embedding_static_return_hop capture)
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
    // rst_n = the parent's rsi (core-synchronous, active low): one pin capture flop, as every pc_path child
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    wire [287:0] ees;
    wire         emb_fault;
    qkd_embedding_static_pc_strap #(.ROW0(ROW0), .MUT(MUT == 2 ? 2 : 0), .RETIME(RETIME)) u_emb (.ck(ck), .rst_n(rs_q),
        .boot_ready(emb_boot_ready), .strap_stack(cfg_stack), .strap_pc(pc),
        .issue_v(emb_issue_v), .token(emb_token), .word_index(emb_word_index), .half(emb_half), .scale(emb_scale),
        .epoch(emb_epoch), .return_slot(emb_return_slot), .es(ees), .er(er),
        .beat_v(beat_v), .beat_data(beat_data), .beat_token(beat_token), .beat_word(beat_word), .beat_half(beat_half),
        .beat_scale(beat_scale), .beat_epoch(beat_epoch), .corrected(corrected), .fault(emb_fault),
        .outstanding(emb_outstanding));
    reg m_fault;
    wire w_first = (MUT == 3) ? !ees[0] : wes[0];
    always @(posedge ck) es[287:1] <= w_first ? wes[287:1] : ees[287:1];
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin es[0] <= 1'b0; m_fault <= 1'b0; end
        else begin
            es[0] <= wes[0] | ees[0];
            if (wes[0] && ees[0] && MUT != 1) m_fault <= 1'b1;
        end
    assign fault = m_fault | emb_fault;
endmodule
