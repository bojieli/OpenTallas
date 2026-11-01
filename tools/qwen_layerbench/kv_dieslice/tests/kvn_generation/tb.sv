`timescale 1ps/1ps
module tb;
reg ck=0;always begin #416 ck=1;#417 ck=0;end
reg rst_n=0;reg[523:0]x3=0;reg slot=0;reg[1:0]index=0;integer count[0:3];integer wrong_count=0;
localparam[58:0]ID={16'd4,6'd1,18'd1,13'd8191,6'd0};
wire[3:0]tv,tf,valid,rf;wire[547:0]p[0:3];wire[511:0]d[0:3];wire[1:0]wi[0:3];wire[10:0]tag[0:3];wire[58:0]ident[0:3];wire[1:0]gen[0:3];wire badvalid,badfault;
genvar g;
generate for(g=0;g<4;g=g+1)begin:GEN
 ot_qwen_d2d_kvn_tx tx(.ck(ck),.rst_n(rst_n),.x3(x3),.x3_identity(ID),.x3_generation(2'(g)),.tx_valid(tv[g]),.tx_payload(p[g]),.fault(tf[g]));
 ot_qwen_d2d_kvn_rx rx(.ck(ck),.rst_n(rst_n),.rx_event(tv[g]),.rx_slot(slot),.rx_beat({3'd0,index}),.rx_payload(p[g]),.compiled_identity(ID),.compiled_generation(2'(g)),.word_valid(valid[g]),.word_tag(tag[g]),.word_data(d[g]),.word_identity(ident[g]),.word_generation(gen[g]),.word_slot(),.word_index(wi[g]),.fault(rf[g]));
end endgenerate
// Old fixture always emitted0 while HOST_TOKEN_GEN was1: this must be rejected.
ot_qwen_d2d_kvn_rx WRONG(.ck(ck),.rst_n(rst_n),.rx_event(tv[0]),.rx_slot(slot),.rx_beat({3'd0,index}),.rx_payload(p[0]),.compiled_identity(ID),.compiled_generation(2'd1),.word_valid(badvalid),.word_tag(),.word_data(),.word_identity(),.word_generation(),.word_slot(),.word_index(),.fault(badfault));
reg[1:0]src_index=0;always @(posedge ck)begin slot<=x3[523];index<=src_index;end
function automatic[511:0]word(input integer j);for(integer k=0;k<16;k=k+1)word[k*32+:32]=32'h64000000+32'(16*j+k);endfunction
integer j,k;
always @(posedge ck)begin
 #1;
 if(rst_n)begin
  for(integer q=0;q<4;q=q+1)if(valid[q])begin
   if(d[q]!==word(count[q])||gen[q]!==2'(q)||ident[q]!==ID||wi[q]!==2'(count[q]))$fatal(1,"decode mismatch gen%0d idx%0d",q,count[q]);
   count[q]=count[q]+1;
  end
  if(badvalid)wrong_count=wrong_count+1;
 end
end
initial begin
 for(k=0;k<4;k=k+1)count[k]=0;
 repeat(3)@(negedge ck);rst_n=1;repeat(2)@(negedge ck);
 for(j=0;j<4;j=j+1)begin src_index=2'(j);x3={1'b1,3'b010,5'd0,1'(j>>1),1'b0,1'(j&1),word(j)};@(negedge ck);end
 x3=0;repeat(5)@(negedge ck);
 for(k=0;k<4;k=k+1)if(count[k]!=4||tf[k]||rf[k])$fatal(1,"positive failed gen%0d words%0d fault%0d/%0d",k,count[k],tf[k],rf[k]);
 if(!badfault||wrong_count!=0)$fatal(1,"oldgen0/newexpected1 not rejected");
 $display("PASS producer/receiver generations0..3, four512bit words each; oldfixture gen0 vs HOSTgen1 caught fault1 valid0;833ps");$finish;
end
endmodule
