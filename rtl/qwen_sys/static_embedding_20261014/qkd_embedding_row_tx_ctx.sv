`timescale 1ns/1ps
// Opt-in EMB context successor: existing row body plus armed diagnostic only.
// Public qkd_embedding_row_tx and its closed native view remain byte-identical.
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, KVJ-C 2026-10-17 (kv_static_join_plan.md N2): the embedding row transmitter, 1 per die, placed beside
// the d2d KV end (its port-2 548-b TX face is local).
//
// Producer side: the qkd_embedding_static_join word stream (one registered 512-b code word per reserved high-half
// slot, or the row's BF16 scale on its scale slot), compiled; the 128 qkd_embedding_static_pc reads of the token are
// issued from the kind-15 RESULT (d2d engine_result_token), which also gives fill_begin / fill_token / fill_epoch here.
// Row staging: ONE ot_sram_1r1w_64x512_m1_r2c2 (the macro of ot_qfd_su_embed_static) written at word_index, the scale
// in a 16-b register.  Consumer side: the d2d port-2 TX slots of the token run (d2d_link_calendar program_profile:
// kind-8 header at emb_header_send, then kind 6 beats 0..31 = words 0..31, kind 7 beats 0..31 = words 32..63), each
// answered one edge after its slot (the port's codec latency 1) with the record layout qfd_sys_face defines:
//     header    = {token18 [547:530], 6'd0, 12'd0, 464'd0, epoch16 [47:32], 16'd0, scale16 [15:0]}
//     code word = {token18 [547:530], word6 [529:524], 12'd0, code512 [511:0]}
// Static: no credit, ready or wait anywhere.  The SRAM read of item n + 1's word is issued on item n's slot edge (the
// macro holds rd_out), so item n + 1 leaves from the macro output through the 548-b output register: no added edge.
// The row must be resident (64 words + scale of fill_token / fill_epoch) at the header slot
// (hbm_embedding_budget.first_emb_send - 1); a late, duplicate, foreign or extra word, a slot without a staged row, a
// 66th slot or a fill_begin that would drop an unsent row latch fault and never move the schedule.  Flow control
// exists only at the d2d boundary (the link's own replay layer), never here.
// Size: 1 macro, 548 + 64 + 16 + 18 + 16 + 7 + ~6 flops + 1 reset pin flop.  Edges: 0 added on the d2d path (the port's codec edge).
// MUT (bench only): 1 = code word index field off by one; 2 = no residency check at the header slot;
//                   3 = word n + 1 read one item late (the payload repeats the previous word);
//                   4 = row_open reports only the resident-unsent window (KV-EMB4 hardened-child bench).
// KV-EMB4 10-19: hardened as its own child kit physical/ref_tile/qkd_embedding_row_tx_ctx (pin regs: row_open leaves
// through one output pin register, so the parent sees armed one edge late on both edges; ctx_start's MIN_GAP covers the
// rise, the fall makes the next admissible new owner >= 2 edges after the 65th send slot -- priced in the GEN9 calendar).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_embedding_row_tx_ctx #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    // compiled fill (token run: the RESULT's token id)
    input  wire          fill_begin,
    input  wire [17:0]   fill_token,
    input  wire [15:0]   fill_epoch,
    // qkd_embedding_static_join word face
    input  wire          word_v,
    input  wire [511:0]  word_data,
    input  wire [17:0]   word_token,
    input  wire [5:0]    word_index,
    input  wire          word_scale,
    input  wire [15:0]   word_epoch,
    // d2d port 2 TX (qkd_d2d_static_core emb_tx_*)
    input  wire          emb_tx_slot,
    output reg           emb_tx_v,
    output reg  [547:0]  emb_tx_payload,
    output reg           fault,
    output wire          row_ready,         // diagnostic: the row is resident and unsent
    output wire          row_open           // diagnostic: existing armed state through the final (65th) send
);
    reg         armed;                       // a fill is open (filled since fill_begin, not yet fully sent)
    reg [63:0]  filled;
    reg         scale_filled;
    reg [17:0]  tok;
    reg [15:0]  ep, scale;
    reg [6:0]   n;                           // items sent: 0 = none, 1 = header, 1 + w = word w, 65 = done
    wire        resident = armed && (&filled) && scale_filled;
    assign row_ready = resident && n == 7'd0;
    assign row_open = (MUT == 4) ? row_ready : armed;   // MUT 4 (bench only): row_open = resident-and-unsent only
    // SRAM read address: the next item's word (item n + 1 is word n; sent on the slot after this one)
    wire [6:0]  rd_w = (MUT == 3) ? ((n == 7'd0) ? 7'd0 : n - 7'd1) : n;
    wire        rd_ce = emb_tx_slot && n < 7'd64;
    wire [511:0] q;
    ot_sram_1r1w_64x512_m1_r2c2 u_row (
        .clk(ck), .r_ce_in(rd_ce), .r_addr_in(rd_w[5:0]), .rd_out(q),
        .w_ce_in(word_v && !word_scale && armed && n == 7'd0), .w_addr_in(word_index),
        .wd_in(word_data), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    wire [5:0]  w_out = (MUT == 1) ? (n[5:0] - 6'd1 + 6'd1) : (n[5:0] - 6'd1);   // item n = word n - 1
    always @(posedge ck) begin
        if (emb_tx_slot)
            emb_tx_payload <= (n == 7'd0) ? {tok, 6'd0, 12'd0, 464'd0, ep, 16'd0, scale}
                                          : {tok, w_out, 12'd0, q};
        if (fill_begin) begin tok <= fill_token; ep <= fill_epoch; end
        if (word_v && word_scale && armed && n == 7'd0) scale <= word_data[15:0];
    end
    // r2 (KV-TILES-A 10-17): rst_n lands in ONE pin flop (plain D, no async term) whose Q is the async reset of every
    // other register, so the port is a D pin under the die hold budget like every data pin (r1 FF -21.55 was the rst_n
    // RESETN removal check straight from the port).  Same +1 edge as the flow's data pin registers: release stays
    // aligned with the registered data faces.
    (* keep *) reg rst_q;
    always @(posedge ck) rst_q <= rst_n;
    always @(posedge ck or negedge rst_q)
        if (!rst_q) begin
            emb_tx_v <= 1'b0; fault <= 1'b0; armed <= 1'b0; filled <= 64'd0; scale_filled <= 1'b0; n <= 7'd0;
        end else begin
            emb_tx_v <= emb_tx_slot;
            if (word_v) begin
                if (!armed || n != 7'd0 || fill_begin) fault <= 1'b1;                  // late or unarmed
                if (word_token != tok || word_epoch != ep) fault <= 1'b1;              // foreign row
                if (word_scale) begin if (scale_filled) fault <= 1'b1; scale_filled <= 1'b1; end
                else begin if (filled[word_index]) fault <= 1'b1; filled[word_index] <= 1'b1; end
            end
            if (emb_tx_slot) begin
                if (n == 7'd0 && !resident && MUT != 2) fault <= 1'b1;               // row not staged by first send
                if (!armed || n == 7'd65) fault <= 1'b1;                               // slot without a row / extra
                if (n != 7'd65) n <= n + 7'd1;
                if (n == 7'd64) armed <= 1'b0;                                          // last word sent
            end
            if (fill_begin) begin
                if (armed || (n != 7'd0 && n != 7'd65) || emb_tx_slot || fill_token >= 18'd151936) fault <= 1'b1;
                armed <= 1'b1; filled <= 64'd0; scale_filled <= 1'b0; n <= 7'd0;
            end
        end
endmodule
