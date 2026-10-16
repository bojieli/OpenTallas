`timescale 1ns/1ps
// The exact full-word register stage in a new horizontal physical slot.
// MUT0 is the production master. Mutants bypass actual DUT fields/stages.
module qkh_head_gather_stage #(parameter integer MUT=0)(
 input wire ck,input wire[1558:0] ti_a,input wire[15:0] e_a,
 output wire[1558:0] ti_b,output wire[15:0] e_b);
 wire[1558:0] tr;wire[15:0] er;
 qkh_head_tstage u_reg(.ck(ck),.ti_a(ti_a),.e_a(e_a),.ti_b(tr),.e_b(er));
 assign ti_b=(MUT==43)?ti_a:(MUT==41)?{tr[1558:531],ti_a[530:519],tr[518:0]}:tr;
 assign e_b=(MUT==42 || MUT==43)?e_a:er;
endmodule
