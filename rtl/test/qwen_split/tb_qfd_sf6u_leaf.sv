`timescale 1ns/1ps
module tb_qfd_sf6u_leaf;
reg ck=0; always #1 ck=~ck;
reg we=0; reg[5:0] wa=0,ra=0; reg[136:0] din=0;
wire[136:0] oldq,newq;
ot_qkvd_llr_replay_sram_leaf_s a(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din),.dout(oldq));
ot_qkvd_llr_replay_sram_leaf_s6u b(.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din),.dout(newq));
reg[3:0] h0seen=0,h1seen=0; integer n,checks=0;
initial begin
for(n=0;n<6064;n=n+1) begin
 @(negedge ck);
 we=(n<64)?1:($urandom_range(0,3)!=0);
 wa=(n<64)?n:$urandom; ra=(n<64)?n:($urandom_range(0,2)==0?wa:$urandom);
 din={$urandom,$urandom,$urandom,$urandom,9'($urandom)};
 @(posedge ck);
 h0seen[{b.u_h0d.a,b.u_h0d.b}]=1;
 h1seen[{b.u_h1d.a,b.u_h1d.b}]=1;
 #0.1;
 if(n>67) begin
  checks=checks+1;
  if(oldq!==newq) $fatal(1,"SF6U_LEAF_FAIL cycle=%0d old=%h new=%h",n,oldq,newq);
 end
end
if(h0seen!==4'b1111 || h1seen!==4'b1111) $fatal(1,"SF6U_LEAF_COVER_FAIL h0=%b h1=%b",h0seen,h1seen);
$display("SF6U_LEAF_PASS checks=%0d h0=%b h1=%b full_words=64 width=137",checks,h0seen,h1seen);$finish;
end
endmodule
