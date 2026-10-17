`timescale 1ns/1ps
`default_nettype none
// Actual memory plus stage-control leaf for one W32 HC systolic bank.
// Four parameterless CLOSED LG8 MAC children sit OUTSIDE this leaf and get
// their own clock entries; this leaf's one root owns memory and descriptor FFs.
// Fixed ML3, LA7, SOR1: the exact legacy stage control is retained. Its
// descriptor advances eight edges while arithmetic/partial-sum data travel
// through the external MACs. There is no runtime issue arbitration.
module ot_hgi_hc_bank_shell_shared_static #(
 parameter integer MUT_SLOT=0
)(
 input wire clk,rst_n,
 input wire [2:0] expected_bank_id,
 input wire [277:0] weight_ap,
 input wire x_write_v,
 input wire [9:0] x_write_word,
 input wire [511:0] x_write_data,
 input wire d_v,d_ss,
 input wire [5:0] d_nv,
 input wire [15:0] d_wa,d_xa,
 input wire f_in,
 input wire [3:0] lane_fault,
 output wire o_v,o_ss,
 output wire [5:0] o_nv,
 output wire [15:0] o_wa,o_xa,
 output reg f_out,
 output reg [31:0] lane_valid,lane_ss,
 output reg lane_go,
 output wire [1023:0] weight_data,
 output wire [511:0] residual_data,
 output wire write_done,read_valid,memory_fault
);
 localparam integer NC=8,ML=3,DW=40;
 reg [NC:0] cv;
 reg [DW-2:0] cd[0:NC];
 reg fin_q,w_re,x_re;
 reg [15:0] w_addr,x_addr;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin cv<=0;w_re<=0;x_re<=0;fin_q<=0;f_out<=0;lane_go<=0;end
  else begin
   cv<={cv[NC-1:0],d_v};
   w_re<=cv[0]&&!cd[0][DW-2];x_re<=cv[0];
   fin_q<=f_in;f_out<=fin_q||(|lane_fault)||memory_fault;
   lane_go<=cv[1+ML];
  end
 end
 wire [5:0] nv_p=cd[ML][DW-3-:6];
 always @(posedge clk)begin
  cd[0]<={d_ss,d_nv,d_wa,d_xa};
  for(integer j=1;j<=NC;j=j+1)cd[j]<=cd[j-1];
  w_addr<=cd[0][31:16];x_addr<=cd[0][15:0];
  for(integer l=0;l<32;l=l+1)begin
   lane_valid[l]<=cv[ML]&&(l<nv_p);lane_ss[l]<=cd[ML][DW-2];
  end
 end
 assign o_v=cv[8];assign {o_ss,o_nv,o_wa,o_xa}=cd[8];
 // Production HC has nout1 and R80: wa[7] carries the existing weight slot,
 // wa[6:0] its native row. This is not a generic nout>1 address translation.
 ot_hgi_hc_bank_memory_shared_static #(.MUT_SLOT(MUT_SLOT)) memory(
  .clk(clk),.rst_n(rst_n),.expected_bank_id(expected_bank_id),.weight_ap(weight_ap),
  .x_write_v(x_write_v),.x_write_word(x_write_word),.x_write_data(x_write_data),
  .w_read_v(w_re),.x_read_v(x_re),.read_slot(w_addr[7]),.w_read_row(w_addr[6:0]),.x_read_word(x_addr[9:0]),
  .write_done(write_done),.read_valid(read_valid),.fault(memory_fault),.weight_data(weight_data),.residual_data(residual_data));
endmodule
`default_nettype wire
