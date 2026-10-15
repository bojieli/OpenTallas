`timescale 1ns/1ps
// Second existing scatter stage. Production wsched already reserves bank k and
// packet slot8*(k%4)+k/4. Parent wires each record to its bank-local capture leaf.
// No crossbar or arbitration: rowhash mismatch is a sticky compiler-defect fault.
// Native pin timing (S81 VM F6 2026-10-15): the bank-hit compare gates ONLY o_v / o_we / fault (fanout 3 per
// record); address/mask/data/tag are registered straight from the pins (as the upstream capture stage does) and are
// meaningful only with o_v.  The consumer (relay -> bank) writes only on valid, so memory state is unchanged; the
// former zero-gating put the compare + a 155-flop gate tree behind every row/valid pin (capture 316-332 ps > 190).
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
`ifdef OT_VM_DIRECT_SCATTER_MUT_VALID
  always @(posedge ck or negedge rn)if(!rn)o_v[k]<=0;else o_v[k]<=i_v[k];
`else
  always @(posedge ck or negedge rn)if(!rn)o_v[k]<=0;else o_v[k]<=i_v[k]&&good[k];
`endif
  always @(posedge ck)begin
   o_we[k]<=i_v[k]&&good[k]?i_we[k]:1'b0;
`ifdef OT_VM_DIRECT_SCATTER_MUT_ADDR
   o_addr[9*k+:9]<=i_row[14*k+5+:9]^9'h1;
`else
   o_addr[9*k+:9]<=i_row[14*k+5+:9];
`endif
   o_mask[4*k+:4]<=i_mask[4*k+:4];
`ifdef OT_VM_DIRECT_SCATTER_MUT_DATA
   o_data[128*k+:128]<=i_data[128*((k+1)%8)+:128];
`else
   o_data[128*k+:128]<=i_data[128*k+:128];
`endif
   o_tag[8*k+:8]<=i_tag[8*k+:8];
  end
 end endgenerate
 always @(posedge ck or negedge rn)if(!rn)fault<=0;else fault<=fault|(|bad);
 initial if(BANK_BASE<0 || BANK_BASE>24 || BANK_BASE%8)$error("bank-local scatter base must be0,8,16,24");
endmodule
