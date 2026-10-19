`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_su_bank6_ws (HBM-NEXT-UNITS-SUDMA2 2026-10-19): the pinned SU store bank hard tile of the next HBM die =
// the d4g CLOSED bank tile ot_hbm_su_static_bank6_clock_physical (unchanged, 6 SRAM providers, 7 clock entries) +
// the split write phase ot_hnx_su_wsplit + the bank write-port mux that ot_hnx_su_pgslice applies per bank, folded
// into the tile (the deferral register sits on the bank's own register root, beside the write pins; glue in tiles).
// Ports = the d4g tile's, with the single write port split into:
//   ow_v / ow_addr / ow_data   the fill / RED_CARRY writer, already muxed by the slice (fw ? fill : dw) -- d4g timing;
//   lane_v / lane_a / lane_d   the lane result (vm_we | kv_we, row {la[17:16], la[13:7]}), BEFORE the deferral;
//   wsplit                     record-static (the slice's local copy ws_l); defer (die strap: 1 on HI = 0 banks).
// Outputs conflict (fill / other writer and a lane write on one edge = the slice's st_conflict term) and clash (fresh +
// deferred lane write on one edge) go to the slice's fault OR, registered (+1 edge). wsplit = 0: the d4g bank write bit for bit.
// One master for all 512 banks (defer is a strap pin, not a parameter).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_su_bank6_ws #(parameter integer WMUT=0)(
 input wire clk,clk_rd,clk_ws,clk_macro0,clk_macro1,clk_macro2,clk_macro3,clk_macro4,clk_macro5,rst_n,
 input wire[5:0]read_v,input wire[53:0]read_addr,
 output wire[191:0]read_data,output wire[5:0]read_return,
 input wire ow_v,input wire[8:0]ow_addr,input wire[31:0]ow_data,
 input wire lane_v,input wire[8:0]lane_a,input wire[31:0]lane_d,
 input wire wsplit,defer,
 output wire conflict,clash
);
 wire lw; wire [8:0] lwa; wire [31:0] ldat; wire c0;
 // one boundary reset register for the deferral flop (the bank keeps its own registered W-face reset, PIN_RST 1)
 (* keep = "true" *) reg rst_q; always @(posedge clk) rst_q<=rst_n;
 // the deferral is a strap-selected copy of ot_hnx_su_wsplit (DEFER 1 when defer, else pass-through)
 ot_hnx_su_wsplit #(.DEFER(1),.RB(9),.WMUT(WMUT)) u_ws(.clk(clk),.rst_n(rst_q),.wsplit(wsplit&&defer),
  .lane_v(lane_v),.lane_a(lane_a),.lane_d(lane_d),.lw_v(lw),.lw_a(lwa),.lw_d(ldat),.clash(c0));
 // fault terms leave from registers (+1 edge into the slice's sticky fault OR; no logic behind the output pins)
 reg conflict_q,clash_q;
 always @(posedge clk or negedge rst_q) if(!rst_q)begin conflict_q<=1'b0; clash_q<=1'b0; end
  else begin conflict_q<=ow_v&&lw; clash_q<=c0; end
 assign clash=clash_q;
 assign conflict=conflict_q;
 ot_hbm_su_static_bank6_clock_physical u_bank(.clk(clk),.clk_rd(clk_rd),.clk_ws(clk_ws),.clk_macro0(clk_macro0),
  .clk_macro1(clk_macro1),.clk_macro2(clk_macro2),.clk_macro3(clk_macro3),.clk_macro4(clk_macro4),.clk_macro5(clk_macro5),
  .rst_n(rst_n),.read_v(read_v),.read_addr(read_addr),.read_data(read_data),.read_return(read_return),
  .write_v(ow_v|lw),.write_addr(ow_v?ow_addr:lwa),.write_data(ow_v?ow_data:ldat));
endmodule
`default_nettype wire
