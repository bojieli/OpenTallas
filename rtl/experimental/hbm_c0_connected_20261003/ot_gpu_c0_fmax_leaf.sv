// Source PC40 finite FMAX, binary32 bit selection after explicit NEG producer.
// No arithmetic reassociation; zero result canonicalized like primitive VM.
// One SECDED mutable pipeline word/lane. No measured SS/FF clock claim.
module ot_gpu_c0_fmax_leaf(input wire clk,por_n,valid_in,input wire[31:0]a,b,
 output wire[31:0]y,output wire valid_out,fault);
 import ot_gpu_w6_secded_pkg::*;
 wire [30:0] unused_sum;wire magnitude_ge;
 ot_hdc_ksadd_k #(.W(31)) u_cmp(.a(a[30:0]),.b(~b[30:0]),.cin(1'b1),.s(unused_sum),.cout(magnitude_ge));
 wire choose_a=(a[31]!=b[31]) ? !a[31] : (a[31] ? !magnitude_ge : magnitude_ge);
 wire [31:0] selected=choose_a?a:b;
 wire [31:0] canonical=(selected[30:0]==0)?32'd0:selected;
 wire bad_input=(a[30:23]==8'hff)||(b[30:23]==8'hff);
 reg[71:0] coded;
 wire [65:0] decoded=decode64(coded);
 assign valid_out=!decoded[65] && !(|decoded[63:34]) && decoded[32];
 assign y=decoded[31:0];
 assign fault=decoded[65] || (|decoded[63:34]) || (decoded[32] && decoded[33]);
 always @(posedge clk or negedge por_n)begin
  if(!por_n)coded<=0;
  else coded<=encode64({30'd0,bad_input,valid_in,canonical});
 end
endmodule
