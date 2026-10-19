`timescale 1ns/1ps
`default_nettype none
// Adapter for CLOSED ot_su12_sfu, whose lane index is physically fixed at5.
// Four registered edges; native broadcast/retirement must price and bind them.
module ot_hgi_sfu_lane_map #(parameter integer MUT_LANE=0,
 // LH-SU (10-19): PASS_OHREP > 0 replicates the pass ring's one-hot per PASS_OHREP bits (ot_hdc_delay_ring OHREP)
 parameter integer PASS_OHREP=0) (
 input wire clk, rst_n,
 input wire [3:0] lane_j,
 input wire [479:0] ld_terms,
 input wire [23:0] i_o_v, i_i_v, i_krow,
 input wire [3:0] i_ls, i_lvw,
 input wire i_emit,
 input wire [460:0] i_pass,
 output reg [1199:0] o_ld_c,
 output reg [23:0] o_o_v, o_i_v, o_krow,
 output reg [3:0] o_ls, o_lvw,
 output reg o_emit,
 output wire [460:0] o_pass
);
 reg f_rst; always @(posedge clk) f_rst<=rst_n;
 reg [479:0] terms0;
 reg [23:0] ov0,iv0,row0;
 reg [3:0] ls0,lvw0,j0;
 reg emit0,emit1,emit2;
 reg [79:0] meta1,meta2;
 // ld is control, not retained payload: reset must not replay a ring slot.
 reg [3:0] ld_pipe;
 ot_hdc_delay_ring #(.W(460),.D(4),.RING(3),.OHREP(PASS_OHREP)) u_pass (.clk(clk),.rst_n(rst_n),.d(i_pass[459:0]),.q(o_pass[459:0]));
 assign o_pass[460]=ld_pipe[3];
 reg [23:0] term1[0:19],pair2[0:9];
 always @(posedge clk) begin
  terms0<=ld_terms; ov0<=i_o_v; iv0<=i_i_v; row0<=i_krow;
  ls0<=i_ls; lvw0<=i_lvw; j0<=lane_j ^ 4'(MUT_LANE);
  // All integer expressions wrap at24 bits, as the frozen lane's kadd.
  meta1<={24'(ov0 + (24'(j0)>>ls0) - (24'd5>>ls0)),
          24'(iv0 + (24'(j0)&((24'd1<<ls0)-1)) - (24'd5&((24'd1<<ls0)-1))),
          24'(row0 + (24'(j0)>>ls0) - (24'd5>>ls0)),
          ls0,(lvw0<3 ? 4'd3 : lvw0)};
  meta2<=meta1;
  {o_o_v,o_i_v,o_krow,o_ls,o_lvw}<=meta2;
  for(integer s=0;s<5;s=s+1) begin
   for(integer k=0;k<4;k=k+1)
    term1[s*4+k]<=j0[k] ? terms0[(s*4+k)*24+:24] : 24'd0;
   pair2[s*2]<=term1[s*4]+term1[s*4+1];
   pair2[s*2+1]<=term1[s*4+2]+term1[s*4+3];
   o_ld_c[s*240+:240]<={216'd0,24'(pair2[s*2]+pair2[s*2+1])};
  end
  if(!f_rst) begin emit0<=0;emit1<=0;emit2<=0;o_emit<=0;ld_pipe<=0;end
  else begin emit0<=i_emit;emit1<=emit0 && (24'(j0)<(24'd1<<lvw0));emit2<=emit1;o_emit<=emit2;ld_pipe<={ld_pipe[2:0],i_pass[460]};end
 end
endmodule
`default_nettype wire
