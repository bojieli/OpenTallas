`default_nettype none
// Additive structural successors. Parent adoption requires a literal die clock/pin grant.
// Each delay leaf keeps the existing d1 -> d2 -> d3 edge relation.
module ot_hgi_coll_uop_slice96(input wire clk,input wire [95:0] d1,output reg [95:0] d2,output reg [95:0] d3);
 always @(posedge clk) begin
  d2<=d1;
`ifdef OT_COLL_SLICE_MUT_DELAY
  d3<=d1;
`else
  d3<=d2;
`endif
 end
endmodule
module ot_hgi_coll_upipe_sliced_v7(input wire [15:0] clk,input wire [1535:0] d1,output wire [1535:0] d2,d3);
 for(genvar s=0;s<16;s=s+1)begin:SL
  ot_hgi_coll_uop_slice96 u(.clk(clk[s]),.d1(d1[s*96+:96]),.d2(d2[s*96+:96]),.d3(d3[s*96+:96]));
 end
endmodule
// Sixteen adjacent bit columns: 128 data bits in/out, eight bank choices per column.
// Replicated select pipes avoid a 2048-bit global mux fabric. Capture and output edges match V6.
// OHSEL (DIE-HBM-61/CUTS 11-03, default 0 = unchanged): 1 = each 3-bit select field of sp[8] also exists as a
// registered one-hot (oh, loaded from sp[7] on the edge sp[8] loads), and as_il is an AND-OR of raw with oh: same value
// on every edge (0 port cycles); removes the 8:1 mux decode from the raw -> as_il stage.
module ot_hgi_coll_vmasm_slice16 #(parameter integer OHSEL=0)(input wire clk,input wire [23:0] sel,input wire [127:0] rd_il,output reg [127:0] as_il);
 reg [23:0] sp[0:8];reg [127:0] raw;
 generate if(OHSEL!=0) begin:g_oh
 reg [63:0] oh; reg [127:0] ao;
 always @* begin
  ao='0;
  for(integer i=0;i<16;i=i+1)for(integer f=0;f<8;f=f+1)for(integer k=0;k<8;k=k+1)
`ifdef OT_COLL_SLICE_MUT_ONEHOT
   if(oh[f*8+((k==7)?0:k)]) ao[i*8+((f%2==0)?2*(f/2):2*(f/2)+1)]=ao[i*8+((f%2==0)?2*(f/2):2*(f/2)+1)]|raw[i*8+k];
`else
   if(oh[f*8+k]) ao[i*8+((f%2==0)?2*(f/2):2*(f/2)+1)]=ao[i*8+((f%2==0)?2*(f/2):2*(f/2)+1)]|raw[i*8+k];
`endif
 end
 always @(posedge clk) begin
  sp[0]<=sel;for(integer k=1;k<9;k=k+1)sp[k]<=sp[k-1];
  raw<=rd_il;
  // field f = select bits [f*3 +: 3] (f even -> as_il bit 2j, f odd -> 2j+1, j=f/2), as sp[8][j*6 +: 3] / [j*6+3 +: 3]
  for(integer f=0;f<8;f=f+1)for(integer k=0;k<8;k=k+1) oh[f*8+k]<=(sp[7][f*3+:3]==3'(k));
  as_il<=ao;
 end
 end else begin:g_mux
 always @(posedge clk) begin
  sp[0]<=sel;for(integer k=1;k<9;k=k+1)sp[k]<=sp[k-1];
  raw<=rd_il;
  for(integer i=0;i<16;i=i+1)for(integer j=0;j<4;j=j+1)begin
`ifdef OT_COLL_SLICE_MUT_SELECT
   as_il[i*8+2*j]<=raw[i*8+int'(sp[8][j*6+3+:3])];
   as_il[i*8+2*j+1]<=raw[i*8+int'(sp[8][j*6+:3])];
`else
   as_il[i*8+2*j]<=raw[i*8+int'(sp[8][j*6+:3])];
   as_il[i*8+2*j+1]<=raw[i*8+int'(sp[8][j*6+3+:3])];
`endif
  end
 end
 end endgenerate
endmodule
module ot_hgi_coll_vmasm_sliced_v7 #(parameter integer OHSEL=0)(input wire [15:0] clk,input wire [23:0] sel,input wire [2047:0] rd_il,output wire [2047:0] as_il);
 for(genvar s=0;s<16;s=s+1)begin:SL
  ot_hgi_coll_vmasm_slice16 #(.OHSEL(OHSEL)) u(.clk(clk[s]),.sel(sel),.rd_il(rd_il[s*128+:128]),.as_il(as_il[s*128+:128]));
 end
endmodule
`default_nettype wire
