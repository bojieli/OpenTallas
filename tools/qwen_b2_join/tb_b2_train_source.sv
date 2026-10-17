`timescale 1ns/1ps
module tb_b2_train_source;
parameter integer MUT=0;
reg head=0,tree=0,rs=0;always #1 head=~head;always #1.5 tree=~tree;
reg[379:0]ib=0;reg[340:0]tc=0;wire go,oe,tv,tl;wire[17:0]tiles;wire[23:0]ts;wire[3:0]split;
qfd_b2_train_source #(.MUT(MUT))dut(.ck_head(head),.ck_tree(tree),.rst_n(rs),.ib(ib),.tc2(tc),.me_go(go),.me_tiles(tiles),.me_ts(ts),.me_split(split),.me_oen(oe),.tag_v(tv),.tag_last(tl));
reg[47:0]want_head;reg[1:0]want_tree;integer heads=0,trees=0;
always @(posedge head)begin
 want_head=rs?{ib[0],ib[36:19],ib[103:80],ib[254:251],ib[353]}:48'd0;
 #0.01;if({go,tiles,ts,split,oe}!==want_head)$fatal(1,"registered native command copy mismatch");if(rs)heads=heads+1;
end
always @(posedge tree)begin
 want_tree=rs?{tc[26],tc[139]}:2'd0;
 #0.01;if({tv,tl}!==want_tree)$fatal(1,"registered native tag copy mismatch");if(rs)trees=trees+1;
end
initial begin
 #4.1;rs=1;
 for(integer k=0;k<256;k=k+1)begin
  #0.2;
  for(integer b=0;b<380;b=b+1)ib[b]=$random;
  for(integer b=0;b<341;b=b+1)tc[b]=$random;
  #2.8;
 end
 if(heads<256||trees<256)$fatal(1,"insufficient source clocks");
 $display("PASS native b2 train source50FF head%0d tree%0d independentphases",heads,trees);$finish;
end
endmodule
