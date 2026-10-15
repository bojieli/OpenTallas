`timescale 1ns/1ps
// Second existing scatter stage. Production wsched already reserves bank k and
// packet slot8*(k%4)+k/4. Parent wires each record to its bank-local capture leaf.
// No crossbar or arbitration: rowhash mismatch is a sticky compiler-defect fault.
module dsfd_vm_static_scatter_b8_out #(parameter integer BANK_BASE=0)(
 input wire ck,rst_n,input wire [7:0] i_v,i_we,
 input wire [111:0] i_row,input wire [31:0] i_mask,
 input wire [1023:0] i_data,input wire [63:0] i_tag,
 output reg [7:0] o_v,o_we,output reg [71:0] o_addr,
 output reg [31:0] o_mask,output reg [1023:0] o_data,
 output reg [63:0] o_tag,output reg fault
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];wire [7:0] good,bad;
 genvar k;generate for(k=0;k<8;k=k+1)begin:bank
  assign good[k]=(i_row[14*k+:5]^{i_row[14*k+5+:3],2'b00})==BANK_BASE+k;
  assign bad[k]=i_v[k]&&!good[k];
  always @(posedge ck or negedge rn)if(!rn)o_v[k]<=0;else o_v[k]<=i_v[k]&&good[k];
  always @(posedge ck)begin
   o_we[k]<=i_v[k]&&good[k]?i_we[k]:1'b0;
`ifdef OT_VM_DIRECT_SCATTER_MUT_ADDR
   o_addr[9*k+:9]<=i_v[k]&&good[k]?(i_row[14*k+5+:9]^9'h1):9'd0;
`else
   o_addr[9*k+:9]<=i_v[k]&&good[k]?i_row[14*k+5+:9]:9'd0;
`endif
   o_mask[4*k+:4]<=i_v[k]&&good[k]?i_mask[4*k+:4]:4'd0;
`ifdef OT_VM_DIRECT_SCATTER_MUT_DATA
   o_data[128*k+:128]<=i_v[k]&&good[k]?i_data[128*((k+1)%8)+:128]:128'd0;
`else
   o_data[128*k+:128]<=i_v[k]&&good[k]?i_data[128*k+:128]:128'd0;
`endif
   o_tag[8*k+:8]<=i_v[k]&&good[k]?i_tag[8*k+:8]:8'd0;
  end
 end endgenerate
 always @(posedge ck or negedge rn)if(!rn)fault<=0;else fault<=fault|(|bad);
 initial if(BANK_BASE<0 || BANK_BASE>24 || BANK_BASE%8)$error("bank-local scatter base must be0,8,16,24");
endmodule
