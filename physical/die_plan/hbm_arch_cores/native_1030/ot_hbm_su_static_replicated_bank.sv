// One independently hardened bank, six read replicas, one canonical write.
// The caller supplies compiler-assigned bank slots. No queues/arbitration or
// producer handshakes exist. All replicas see identical writes, including
// masked-word semantics inside the REAL provider SRAM. Read address conflicts
// between consumers must be resolved by the compiler before this boundary.
module ot_hbm_su_static_replicated_bank #(
 parameter integer READERS=6,RB=9,MUT_COHERENCE=0
)(
 input wire clk, // word-select flops stay on the boundary register root
 input wire[READERS-1:0]clk_macro,
 input wire[READERS-1:0]read_v,
 input wire[READERS*RB-1:0]read_addr,
 output wire[READERS*32-1:0]read_data,
 input wire write_v,input wire[RB-1:0]write_addr,input wire[31:0]write_data
);
 // Exact RB9 provider geometry of ot_hgi_su_lbank:512 words in64
 // active rows of the actual128x256 SRAM. Word mask and read-before-write
 // semantics are unchanged. Only the SRAM pin gets its own raw clock entry.
 initial if(RB!=9)$fatal(1,"static replicated bank requires RB9 actual128x256 provider");
 for(genvar r=0;r<READERS;r=r+1)begin:g_read
  reg[2:0]ks;
  always @(posedge clk)if(read_v[r])ks<=read_addr[r*RB+:3];
  wire[255:0]raw;
  wire[255:0]mask={224'd0,32'hffffffff} << {write_addr[2:0],5'd0};
  ot_sram_1r1w_128x256_m1_r2c2 u_m(
   .clk(clk_macro[r]),.r_ce_in(read_v[r]),.r_addr_in({1'b0,read_addr[r*RB+3+:6]}),.rd_out(raw),
   .w_ce_in(write_v&&!(MUT_COHERENCE!=0&&r==READERS-1)),.w_addr_in({1'b0,write_addr[8:3]}),
   .wd_in({8{write_data}}),.w_mask_in(mask),.rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
  assign read_data[r*32+:32]=raw[{ks,5'd0}+:32];
 end
endmodule
