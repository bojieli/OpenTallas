`timescale 1ns/1ps
// RoPE successor: real second HBM row; eight selected words, same token/epoch.
// 73 fixed sends: header,64 code,eight flagged RoPE. No wait/credit.
module qkd_embedding_row_tx_rope #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    // compiled fill (token run: the RESULT's token id)
    input  wire          fill_begin,
    input  wire [17:0]   fill_token,
    input  wire [15:0]   fill_epoch,
    input wire [12:0] fill_position,
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
    reg scale_filled;
    reg [7:0] rope_filled;
    reg [12:0] pos;
    wire is_rope=word_token>=18'd151936;
    wire [17:0] rope_token=18'd151936+{8'd0,pos[12:3]};
    wire selected_rope=word_index[5:3]==pos[2:0];
    reg [17:0]  tok;
    reg [15:0]  ep, scale;
    reg [6:0]   n;                           // items sent: 0 = none, 1 = header, 1 + w = word w, 65 = done
    wire        resident = armed && (&filled) && scale_filled && (&rope_filled);
    assign row_ready = resident && n == 7'd0;
    assign row_open = (MUT == 4) ? row_ready : armed;   // MUT 4 (bench only): row_open = resident-and-unsent only
    // SRAM read address: the next item's word (item n + 1 is word n; sent on the slot after this one)
    wire [6:0]  rd_w = (MUT == 3) ? ((n == 7'd0) ? 7'd0 : n - 7'd1) : n;
    wire        rd_ce = emb_tx_slot && n < 7'd64;
    wire [511:0] q;
    ot_sram_1r1w_64x512_m1_r2c2 u_row (
        .clk(ck), .r_ce_in(rd_ce), .r_addr_in(rd_w[5:0]), .rd_out(q),
        .w_ce_in(word_v && !word_scale && !is_rope && armed && n == 7'd0), .w_addr_in(word_index),
        .wd_in(word_data), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    wire [511:0] rope_q;
    ot_sram_1r1w_64x512_m1_r2c2 u_rope (
      .clk(ck),.r_ce_in(emb_tx_slot && n>=64 && n<72),.r_addr_in(6'(n-64)),.rd_out(rope_q),
      .w_ce_in(word_v && is_rope && selected_rope && !word_scale && armed && n==0),
      .w_addr_in({3'd0,word_index[2:0]}),.wd_in(word_data),.w_mask_in({512{1'b1}}),
      .rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(18'd0));
    wire [5:0]  w_out = (MUT == 1) ? (n[5:0] - 6'd1 + 6'd1) : (n[5:0] - 6'd1);   // item n = word n - 1
    always @(posedge ck) begin
        if (emb_tx_slot)
            emb_tx_payload <= (n == 7'd0) ? {tok, 6'd0, 12'd0, 464'd0, ep, 16'd0, scale}
                                          : n>=65 ? {tok,6'(n-65),11'd0,1'b1,rope_q} : {tok, w_out, 12'd0, q};
        if (fill_begin) begin tok <= fill_token; ep <= fill_epoch; pos <= fill_position; end
        if (word_v && word_scale && !is_rope && armed && n == 7'd0) scale <= word_data[15:0];
    end
    // r2 (KV-TILES-A 10-17): rst_n lands in ONE pin flop (plain D, no async term) whose Q is the async reset of every
    // other register, so the port is a D pin under the die hold budget like every data pin (r1 FF -21.55 was the rst_n
    // RESETN removal check straight from the port).  Same +1 edge as the flow's data pin registers: release stays
    // aligned with the registered data faces.
    (* keep *) reg rst_q;
    always @(posedge ck) rst_q <= rst_n;
    always @(posedge ck or negedge rst_q)
        if (!rst_q) begin
            emb_tx_v <= 1'b0; fault <= 1'b0; armed <= 1'b0; filled <= 64'd0; rope_filled<=0; scale_filled <= 1'b0; n <= 7'd0;
        end else begin
            emb_tx_v <= emb_tx_slot;
            if (word_v) begin
                if (!armed || n != 7'd0 || fill_begin) fault <= 1'b1;                  // late or unarmed
                if (word_token != (is_rope?rope_token:tok) || word_epoch != ep) fault <= 1'b1;              // foreign row
                if(is_rope)begin
                    if(word_scale)fault<=1;
                    if(selected_rope)begin if(rope_filled[word_index[2:0]])fault<=1;rope_filled[word_index[2:0]]<=1;end
                end else if (word_scale) begin if (scale_filled) fault <= 1'b1; scale_filled <= 1'b1; end
                else begin if (filled[word_index]) fault <= 1'b1; filled[word_index] <= 1'b1; end
            end
            if (emb_tx_slot) begin
                if (n == 7'd0 && !resident && MUT != 2) fault <= 1'b1;               // row not staged by first send
                if (!armed || n == 7'd73) fault <= 1'b1;                               // slot without a row / extra
                if (n != 7'd73) n <= n + 7'd1;
                if (n == 7'd72) armed <= 1'b0;                                          // last word sent
            end
            if (fill_begin) begin
                if (armed || (n != 7'd0 && n != 7'd73) || emb_tx_slot || fill_token >= 18'd151936) fault <= 1'b1;
                armed <= 1'b1; filled <= 64'd0; rope_filled<=0; scale_filled <= 1'b0; n <= 7'd0;
            end
        end
endmodule
