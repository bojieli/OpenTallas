`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_su_rowr (HBM-NEXT-UNITS-SUDMA2 2026-10-19): REDUCER / RF ROW CLASS of the next HBM die's SU (HGI-1R ROWX, P = 4),
// one per SU quarter beside ot_hnx_su_rowx. rowx steps the vmr / vmw / control classes of the 2422-b quarter line; this
// stage steps the remaining two: red_cmd (74 b, line[73:0]) and rf_rd_cmd (54 b, line[127:74]). Control only: no
// datapath, no queue, no ready/credit; d4g qcore / reducer / RF RTL unchanged.
// Why: a norm-style SU.VOP record of N rows reduces every row (per-quarter chains + tree, an export into the RF, the
// cross-quarter sum on reducer 0 from RF class-4 reads, the row scalar broadcast by an RF class 0..3 read, RF sector
// drains by class 5). Unrolled with absolute addresses, every row adds its own scratch / RF words to the red and rf
// columns. Row-relative: the image holds row 0's red / rf words; a per-edge 8-b row code extension (rc2[3:0] reducer
// row, rc2[7:4] RF row; the programme column carries it in column 9's spare bits next to rowx's 20-b code: 2442 -> 2450
// b a quarter line, still 10 columns) and two record strides do the rest. Rows overlap in time (row r + 1's chains run
// while row r's tree / export / cross-quarter sum finish), so a row's scratch MUST be disjoint from its neighbours':
// the scratch stride is what makes the overlap legal.
// Per edge (row codes r_d = rc2[3:0], r_f = rc2[7:4]; strides s_red 10 b scratch words, s_rf 8 b RF words):
//   red_cmd {v73, op72:70, a69:60, b59:50, dst49:40, tag39:8, osel7, lane6:0}:
//     a   += r_d s_red  for op 1 ADD_EXT, 2 ADD_TREE, 3 MAX_EXT, 4 EXPORT, 5 MAX_TREE (the ops that read a)
//     b   += r_d s_red  for op 2, 5
//     dst += r_d s_red  for op 0, 1, 2, 3, 5 (the ops that commit)
//     tag[7:0] += r_d s_rf when op 4 && tag[8] (the export's RF destination word)
//   rf_rd_cmd class c (0..5) {v, addr8}: addr += r_f s_rf (classes 0..4 one RF word; class 5 a sector: s_rf[2:0] must be 0)
// Row 0 (rc2 = 0) passes every word unchanged: N = 1 and every non-row record = the d4g command bit for bit (REG edges
// later; the compiler's start advance + REG, same as rowx, so the two stages stay aligned).
// Checks (sticky FAULT, never a stall): a stepped scratch field carries out of the 1,024-word scratch; a stepped RF word
// carries out of the 256-word RF; a stepped class-5 address is not sector aligned.
// REG 1. MUT (bench only, must FAIL): 1 dst stride dropped; 2 export tag stride dropped; 3 RF read stride dropped;
// 4 a / b stride dropped (operand reads stay on row 0's scratch).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_su_rowr #(parameter integer REG=1,MUT=0)(
 input wire clk,rst_n,
 input wire [127:0] line_in,                  // {rf54, red74} of the quarter line (row-0-relative)
 input wire [7:0] rc2,                        // {RF row, reducer row} of this edge
 input wire [17:0] st2,                       // {s_rf8, s_red10} record strides (static for the record)
 output reg [127:0] line_out,
 output reg fault
);
 wire [3:0] r_d=rc2[3:0], r_f=rc2[7:4];
 wire [9:0] s_red=st2[9:0]; wire [7:0] s_rf=st2[17:10];
 wire [13:0] o_red=14'(r_d*s_red);            // up to 15 x 1,023: carries are checked, never wrapped silently
 wire [11:0] o_tag=12'(r_d*s_rf);
 wire [11:0] o_rf=12'(r_f*s_rf);
 wire [73:0] red=line_in[73:0];
 wire rv=red[73]; wire [2:0] op=red[72:70];
 wire use_a=rv&&(op==3'd1||op==3'd2||op==3'd3||op==3'd4||op==3'd5);
 wire use_b=rv&&(op==3'd2||op==3'd5);
 wire use_d=rv&&(op==3'd0||op==3'd1||op==3'd2||op==3'd3||op==3'd5);
 wire use_t=rv&&op==3'd4&&red[16];
 wire [13:0] na={4'd0,red[69:60]}+((use_a&&MUT!=4)?o_red:14'd0);
 wire [13:0] nb={4'd0,red[59:50]}+((use_b&&MUT!=4)?o_red:14'd0);
 wire [13:0] nd={4'd0,red[49:40]}+((use_d&&MUT!=1)?o_red:14'd0);
 wire [11:0] nt={4'd0,red[15:8]}+((use_t&&MUT!=2)?o_tag:12'd0);
 reg [127:0] y; reg bad; integer c; reg [11:0] ra;
 always @*begin
  y=line_in; bad=1'b0;
  y[69:60]=na[9:0]; y[59:50]=nb[9:0]; y[49:40]=nd[9:0]; y[15:8]=nt[7:0];
  if((use_a&&na[13:10]!=0)||(use_b&&nb[13:10]!=0)||(use_d&&nd[13:10]!=0)||(use_t&&nt[11:8]!=0))bad=1'b1;
  for(c=0;c<6;c=c+1)begin                     // rf class c {v, addr8} at line[74 + 9 c]
   ra={4'd0,line_in[74+9*c+:8]}+((line_in[74+9*c+8]&&MUT!=3)?o_rf:12'd0);
   if(line_in[74+9*c+8])begin
    if(ra[11:8]!=0)bad=1'b1;
    if(c==5&&ra[2:0]!=0)bad=1'b1;
   end
   y[74+9*c+:8]=ra[7:0];
  end
 end
 if(REG!=0)begin:g_reg
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin line_out<='0; fault<=1'b0; end
   else begin line_out<=y; if(bad)fault<=1'b1; end
 end else begin:g_comb
  always @*line_out=y;
  always @(posedge clk or negedge rst_n)if(!rst_n)fault<=1'b0; else if(bad)fault<=1'b1;
 end
endmodule
`default_nettype wire
