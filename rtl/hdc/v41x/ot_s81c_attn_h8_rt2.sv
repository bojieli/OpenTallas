`timescale 1ns/1ps
// R5 conservative H8 candidate: serialize each RT4/PWORDS2 input into two
// original RT2/PWORDS2 loads, preserving the signed H16 head macro unchanged.
// Valid SVC calendar: P loads every2clocks, no other load in the replay slot.
// Generic inter-job ILV Q/P load collisions need an explicitly priced queue;
// they are detected here. The original scalar32-term reduction is unchanged.
module ot_s81c_h8_rt2_load (
 input wire clk,rst_n,ld_v,ld_mode,input wire[2:0]ld_bank,input wire[7:0]ld_grp,
 input wire[1023:0]ld_w,input wire ld_w2v,
 output wire out_v,out_mode,
 output wire[2:0]out_bank,output wire[7:0]out_grp,output wire[1023:0]out_w,
 output wire out_w2v,output reg fault
);
 reg pending;reg[511:0]second;reg[2:0]bank;reg[7:0]group_second;
 // One H8word contains4rows×8heads. Expand to two old H16words, each2rows×16heads.
 // Only original head macros0..7 are instantiated; empty upper-head fields stayinternal.
 function automatic[1023:0]expand(input[511:0]x);
  expand=0;
  for(integer row=0;row<4;row++)for(integer h=0;h<8;h++)
   expand[16*(16*row+h)+:16]=x[16*(8*row+h)+:16];
 endfunction
 wire bad_group=ld_mode&&(ld_grp[0]||ld_grp>8'd6);
 assign out_v=pending||(ld_v&&!bad_group);
 assign out_mode=pending||ld_mode;
 assign out_bank=pending?bank:ld_bank;
 assign out_grp=pending?group_second:(ld_mode?{ld_grp[6:0],1'b0}:ld_grp);
 assign out_w=pending?expand(second):(ld_mode?expand(ld_w[511:0]):ld_w);
 // Every live H8word expands into two complete old2row words. Invalid tail
 // rows remain masked by the native V-row pad bits, as before.
 assign out_w2v=(pending||ld_mode)?1'b1:ld_w2v;
 always@(posedge clk)begin
  if(!rst_n)begin pending<=0;fault<=0;end
  else begin
   if(ld_v&&(pending||bad_group))fault<=1;
   pending<=!pending&&ld_v&&ld_mode&&!bad_group&&ld_w2v;
  end
  if(ld_v&&ld_mode&&!pending)begin second<=ld_w[1023:512];bank<=ld_bank;group_second<={ld_grp[6:0],1'b0}+8'd2;end
 end
endmodule

module ot_s81c_attn_tile_hc_h8_rt2 (
 input wire clk,rst_n,ld_v,ld_mode,input wire[2:0]ld_bank,input wire[7:0]ld_grp,
 input wire[1023:0]ld_w,input wire ld_w2v,iv,input wire[2:0]ibank,input wire[575:0]ib,
 output wire ov,output wire[255:0]oy,output wire[7:0]oflt
);
 wire av,am,a2,af;wire[2:0]ab;wire[7:0]ag;wire[1023:0]aw;
 ot_s81c_h8_rt2_load u_expand(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.out_v(av),.out_mode(am),.out_bank(ab),.out_grp(ag),.out_w(aw),.out_w2v(a2),.fault(af));
 wire sv,sm,s2;wire[2:0]sb;wire[7:0]sg;wire[1023:0]sw;
 // Exactly the existing CTLA sender. No modification of the signed head macro.
 ot_s81c_hcore_load_stage u_load_stage(.clk(clk),.rst_n(rst_n),.ld_v(av),.ld_mode(am),.ld_bank(ab),.ld_grp(ag),.ld_w(aw),.ld_w2v(a2),.out_v(sv),.out_mode(sm),.out_bank(sb),.out_grp(sg),.out_w(sw),.out_w2v(s2));
 wire[7:0]hv,hf;
 for(genvar g=0;g<8;g++)begin:g_h
  wire[63:0]wp;
  for(genvar w=0;w<2;w++)for(genvar j=0;j<2;j++)begin:g_wp
   assign wp[16*(2*w+j)+:16]=sw[w*512+16*(16*j+g)+:16];
  end
  ot_s81c_attn_hcore u_c(.clk(clk),.rst_n(rst_n),.gid(8'(g)),.ld_v(sv),.ld_mode(sm),.ld_bank(sb),.ld_grp(sg),.ld_w(sw[511:0]),.ld_wp(wp),.ld_w2v(s2),.iv(iv),.ibank(ibank),.ib(ib),.ov(hv[g]),.oy(oy[32*g+:32]),.oflt(hf[g]));
 end
 assign ov=hv[0];assign oflt=hf|{8{af}};
endmodule
