// Smallest sequential vehicle containing the compaction + residual carry mechanism.
// Arbitrary masks/data, clear and ingest from reset; no calendar/data assumptions.
module carry_proof #(parameter MUT=0)(input clk,rst_n,clear,ingest,
 input [7:0] mask,input[63:0]words,output bad);
 reg[87:0]serial_carry;
 reg[23:0]tree_carry;
 reg[1:0]sf,tf;
 wire[63:0]compacted;wire[3:0]count;
 wire[7:0]tree_mask=MUT ? {1'b0,mask[6:0]} : mask;
 ot_hbm_idx_compact_tree #(.N(8),.W(8)) compact(.mask(tree_mask),.words(words),.packed_words(compacted),.count(count));
 reg[87:0]serial_packed;reg[3:0]n;
 always @* begin
  serial_packed=serial_carry;n=4'(sf);
  if(ingest)for(integer j=0;j<8;j=j+1)if(mask[j])begin
   serial_packed[n*8+:8]=words[j*8+:8];n=n+1;
  end
 end
 reg[23:0]live_carry;
 always @*begin
  live_carry=0;
  for(integer r=0;r<3;r=r+1)if(r<int'(tf))live_carry[r*8+:8]=tree_carry[r*8+:8];
 end
 wire[3:0]tn=4'(tf)+(ingest?count:4'd0);
 wire[1:0]nf=tn[3:2];
 wire[87:0]tree_packed=({24'd0,(ingest?compacted:64'd0)} << {tf,3'b0})|{64'd0,live_carry};
 reg[23:0]tree_next;
 always @*begin
  tree_next=0;
  for(integer f=0;f<=2;f=f+1)if(nf==2'(f))
   for(integer r=0;r<3;r=r+1)tree_next[r*8+:8]=tree_packed[(f*4+r)*8+:8];
 end
 always @(posedge clk)begin
  if(!rst_n)begin serial_carry<=0;sf<=0;tf<=0;end
  else begin
   if(clear)begin serial_carry<=0;sf<=0;tf<=0;end
   if(ingest)begin
    serial_carry<=serial_packed >> (n[3:2]*32);sf<=n[1:0];
    tree_carry<=tree_next;tf<=tn[1:0];
   end
  end
 end
 assign bad=rst_n&&((serial_carry!={64'd0,live_carry})||(sf!=tf)||(ingest&&((serial_packed!=tree_packed)||(4'(n)!=tn))));
endmodule
