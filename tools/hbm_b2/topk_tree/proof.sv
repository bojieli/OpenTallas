module proof(input[7:0]mask,input[63:0]words,output bad);
 wire[63:0]packed_words;wire[3:0]count;
 ot_hbm_idx_compact_tree #(.N(8),.W(8)) dut(.mask(mask),.words(words),.packed_words(packed_words),.count(count));
 reg[63:0]ref_words;integer n;
 always @*begin
  ref_words=0;n=0;
  for(integer j=0;j<8;j=j+1)if(mask[j])begin ref_words[n*8+:8]=words[j*8+:8];n=n+1;end
 end
 assign bad=(packed_words!=ref_words)||(count!=4'(n));
endmodule
