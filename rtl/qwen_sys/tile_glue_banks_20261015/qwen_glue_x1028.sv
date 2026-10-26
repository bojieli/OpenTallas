`timescale 1ns/1ps
// PM-H-S paired W-face master (Q-COMPUTE-ELEM r13, 2026-10-15): the tile's facing tree words are bit-interleaved on
// the W face (t_out[k]/n_b[k], n_y[k]/n_a[k] one 0.096 um M4 track apart) so a mirrored neighbour's word lands one
// track from this tile's partner word.  One master holds both 514-bit face registers of a pair so its W pins can sit
// on the interleaved slots: oq (launch to the W face, from od) and iq (capture from the W face id, to the interior).
// Exactly the two qwen_glue_v514 registers it replaces: same ot_qkh_packet_pipe, two independent clock roots
// (clk_o / clk_i keep the parent's ck_bank entries), two resets; zero added edges.
module qwen_glue_x1028 #(parameter integer MUT=0)(
 input wire clk_o, clk_i, rst_o_n, rst_i_n,
 input wire [513:0] od, output wire [513:0] oq,
 input wire [513:0] id, output wire [513:0] iq);
 ot_qkh_packet_pipe #(.W(514),.MUT(MUT)) u_o(.clk(clk_o),.rst_n(rst_o_n),.d(od),.q(oq));
 ot_qkh_packet_pipe #(.W(514),.MUT(MUT)) u_i(.clk(clk_i),.rst_n(rst_i_n),.d(id),.q(iq));
endmodule
