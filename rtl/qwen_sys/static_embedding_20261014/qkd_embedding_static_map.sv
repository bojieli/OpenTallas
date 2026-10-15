`timescale 1ns/1ps
// Exact selected HBM bootstrap ABI, unchanged from emb_loc/code_bcr/scale_loc
// in qkd_embgw_splitboot and ot_qkvd_emb_strip_c. Mapping only, no scheduler.
module qkd_embedding_static_map #(
    parameter integer ROW0=24427
)(input wire [17:0] token,input wire [5:0] word_index,
  input wire half,scale,
  output wire [24:0] logical_sector,
  output wire [1:0] stack,
  output wire [4:0] pc,bank,col,
  output wire [18:0] row,
  output wire valid_address);
    wire [13:0] s=token[17:4];
    wire [9:0] p=scale?(10'd384+{3'd0,s[13:7]}):token[9:0];
    assign logical_sector=scale?(25'd19447808+{11'd0,s}):({token,7'd0}+{18'd0,word_index,half});
    assign stack=scale?s[6:5]:word_index[5:4];
    assign pc=scale?s[4:0]:{word_index[3:0],half};
    assign bank={p[9:7],p[1:0]};
    assign col=p[6:2];
    assign row=19'(ROW0)+(scale?19'd148:{11'd0,token[17:10]});
    assign valid_address=(token<151936)&&(!scale||!half);
endmodule
