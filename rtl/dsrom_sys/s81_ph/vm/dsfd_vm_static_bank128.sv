`timescale 1ns/1ps
// Native scheduled one-bank leaf: uses BOTH real1R1W macro ports. No queues,
// ready, credits, arbiters or retries. Addresses are physical bank-local[13:5].
// Compiler owns requests and read-before-write same-address semantics.
// Pin sample at edgeE: write commits at E+1, read appears registered at E+2.
// Commit output is observation of the very SRAM w_ce edge, never admission.
module dsfd_vm_static_bank128(
 input wire ck,rst_n,
 input wire i_rv,input wire [8:0] i_ra,input wire [7:0] i_rt,
 input wire i_wv,input wire [8:0] i_wa,input wire [127:0] i_wd,
 input wire [3:0] i_wm,input wire [7:0] i_wt,
 output reg o_rv,output reg [127:0] o_rd,output reg [7:0] o_rt,
 output reg o_commit,output reg [8:0] o_ca,
 output reg [3:0] o_cm,output reg [7:0] o_ct
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];

 reg rvq,wvq,rdue;reg [8:0] raq,waq;reg [127:0] wdq;
 reg [3:0] wmq;reg [7:0] rtq,rt1,wtq;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin rvq<=0;wvq<=0;rdue<=0;o_rv<=0;o_commit<=0;end
  else begin rvq<=i_rv;wvq<=i_wv;rdue<=rvq;o_rv<=rdue;
`ifdef OT_VM_BANK_MUT_EARLY_COMMIT
   o_commit<=i_wv;
`else
   o_commit<=wvq;
`endif
  end
 end
 always @(posedge ck)begin
  raq<=i_ra;waq<=i_wa;wdq<=i_wd;wmq<=i_wm;rtq<=i_rt;wtq<=i_wt;rt1<=rtq;
  o_rt<=rt1;o_ca<=waq;o_cm<=wmq;o_ct<=wtq;
 end
 wire [127:0] mr;
 `ifdef OT_VM_BANK_MUT_MASK
 wire [127:0] mask={128{1'b1}};
`else
 wire [127:0] mask={{32{wmq[3]}},{32{wmq[2]}},{32{wmq[1]}},{32{wmq[0]}}};
`endif
 ot_sram_1r1w_512x128_m4_r2c2 u_sram(.clk(ck),.r_ce_in(rvq),.r_addr_in(raq),.rd_out(mr),
 .w_ce_in(wvq),.w_addr_in(waq),.wd_in(wdq),.w_mask_in(mask),
 .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(14'd0));
 always @(posedge ck)o_rd<=mr;
endmodule
