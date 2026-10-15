`timescale 1ns/1ps
// Second existing scatter stage. Production wsched already reserves bank k and
// packet slot8*(k%4)+k/4. Parent wires each record to its bank-local capture leaf.
// No crossbar or arbitration: rowhash mismatch is a sticky compiler-defect fault.
// Native pin timing (S81 VM F6 2026-10-15): the bank-hit compare drives ONLY o_v (fanout 1 per record);
// we/address/mask/data/tag are registered straight from the pins (as the upstream capture stage does) and are
// meaningful only with o_v.  The consumer (relay -> bank) writes only on valid, so memory state is unchanged; the
// former zero-gating put the compare + a 155-flop gate tree behind every row/valid pin (capture 316-332 ps > 190).
// PIPE=1 (S81 VM S-ELEM-A 2026-10-15, candidate, default off): every input is pin-registered first and the bank-hit
// compare runs flop-to-flop in the second stage (cb3 routed views: native capture 191.2/206.1/194.6 ps > 190 on i_row
// hash pins feeding the compare -> o_v).  All outputs and the fault move one write edge later (compiler write calendar +1).
module dsfd_vm_static_scatter_b8_out #(parameter integer BANK_BASE=0, parameter integer PIPE=0)(
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
 wire rn=reset_release[1];wire [7:0] good;
 wire [7:0] x_v,x_we;wire [111:0] x_row;wire [31:0] x_mask;wire [1023:0] x_data;wire [63:0] x_tag;
 generate if(PIPE!=0)begin:pin
  reg [7:0] p_v,p_we;reg [111:0] p_row;reg [31:0] p_mask;reg [1023:0] p_data;reg [63:0] p_tag;
  always @(posedge ck or negedge rn)if(!rn)p_v<=0;else p_v<=i_v;
  always @(posedge ck)begin p_we<=i_we;p_row<=i_row;p_mask<=i_mask;p_data<=i_data;p_tag<=i_tag;end
  assign x_v=p_v;assign x_we=p_we;assign x_row=p_row;assign x_mask=p_mask;assign x_data=p_data;assign x_tag=p_tag;
 end else begin:direct
  assign x_v=i_v;assign x_we=i_we;assign x_row=i_row;assign x_mask=i_mask;assign x_data=i_data;assign x_tag=i_tag;
 end endgenerate
 genvar k;generate for(k=0;k<8;k=k+1)begin:bank
  assign good[k]=(x_row[14*k+:5]^{x_row[14*k+5+:3],2'b00})==BANK_BASE+k;
`ifdef OT_VM_DIRECT_SCATTER_MUT_VALID
  always @(posedge ck or negedge rn)if(!rn)o_v[k]<=0;else o_v[k]<=x_v[k];
`else
  always @(posedge ck or negedge rn)if(!rn)o_v[k]<=0;else o_v[k]<=x_v[k]&&good[k];
`endif
  always @(posedge ck)begin
   o_we[k]<=x_we[k];
`ifdef OT_VM_DIRECT_SCATTER_MUT_ADDR
   o_addr[9*k+:9]<=x_row[14*k+5+:9]^9'h1;
`else
   o_addr[9*k+:9]<=x_row[14*k+5+:9];
`endif
   o_mask[4*k+:4]<=x_mask[4*k+:4];
`ifdef OT_VM_DIRECT_SCATTER_MUT_DATA
   o_data[128*k+:128]<=x_data[128*((k+1)%8)+:128];
`else
   o_data[128*k+:128]<=x_data[128*k+:128];
`endif
   o_tag[8*k+:8]<=x_tag[8*k+:8];
  end
 end endgenerate
 // Sticky compiler-defect fault, FAULT_AGE 3 edges (one after o_v), flop-to-flop: a raw valid pin flop beside each
 // record and the registered o_v give the mismatch (v_q & !o_v == registered x_v & !good) without a second load
 // on the compare cone.  Exceptional indicator only: o_v suppression stays on the same edge.
 reg [7:0] v_q;
 always @(posedge ck or negedge rn)if(!rn)v_q<=0;else v_q<=x_v;
 always @(posedge ck or negedge rn)if(!rn)fault<=0;else fault<=fault|(|(v_q&~o_v));
 initial if(BANK_BASE<0 || BANK_BASE>24 || BANK_BASE%8)$error("bank-local scatter base must be0,8,16,24");
endmodule
