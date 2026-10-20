`timescale 1ns/1ps
module tb_kvba_codec_ba3;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,tx_event=0,tx_expected=0,rx_event=0,rx_expected=0;
 reg [3:0] tx_kind=3,tx_expected_kind=3,rx_expected_kind=1;
 reg [15:0] tx_epoch=7,tx_expected_epoch=7,rx_expected_epoch=7;
 reg [5:0] tx_layer=2,tx_expected_layer=2,rx_expected_layer=2;
 reg [4:0] tx_beat=0,tx_expected_beat=0,rx_expected_beat=0;
 reg [511:0] tx_data=0;
 reg [547:0] rx_payload=0;
 wire tv[0:1],rv[0:1],fault[0:1];wire [547:0] tp[0:1];
 wire [3:0] rk[0:1],fc[0:1];wire [15:0] re[0:1];wire [5:0] rl[0:1];wire [4:0] rb[0:1];wire [511:0] rd[0:1];
 `define PORTS(I) .ck(ck),.rst_n(rst_n),.tx_event(tx_event),.tx_expected(tx_expected),.tx_kind(tx_kind),.tx_expected_kind(tx_expected_kind),.tx_epoch(tx_epoch),.tx_expected_epoch(tx_expected_epoch),.tx_layer(tx_layer),.tx_expected_layer(tx_expected_layer),.tx_beat(tx_beat),.tx_expected_beat(tx_expected_beat),.tx_data(tx_data),.tx_valid(tv[I]),.tx_payload(tp[I]),.rx_event(rx_event),.rx_expected(rx_expected),.rx_payload(rx_payload),.rx_expected_kind(rx_expected_kind),.rx_expected_epoch(rx_expected_epoch),.rx_expected_layer(rx_expected_layer),.rx_expected_beat(rx_expected_beat),.rx_valid(rv[I]),.rx_kind(rk[I]),.rx_epoch(re[I]),.rx_layer(rl[I]),.rx_beat(rb[I]),.rx_data(rd[I]),.fault(fault[I]),.fault_cause(fc[I])
 qkd_native_attention_record_ld ref_d(`PORTS(0));
 qkd_native_attention_record_ld_ba3 #(.MUT(MUT)) new_d(`PORTS(1));
 integer checks=0,errors=0,accepted=0,rejected=0;
 task check;begin
  #1;checks++;
  if({tv[0],rv[0],fault[0],fc[0]}!=={tv[1],rv[1],fault[1],fc[1]} ||
    (tv[0] && tp[0]!==tp[1]) || (rv[0] && {rk[0],re[0],rl[0],rb[0],rd[0]}!=={rk[1],re[1],rl[1],rb[1],rd[1]}))begin
    errors++;if(errors<5)$display("CODEC_BA3_MISMATCH check=%0d ref=%b/%h new=%b/%h",checks,{tv[0],rv[0],fault[0]},fc[0],{tv[1],rv[1],fault[1]},fc[1]);end
 end endtask
 initial begin
 for(integer c=0;c<2200;c++)begin
  @(negedge ck);rst_n=0;tx_event=0;rx_event=0;tx_expected=0;rx_expected=0;
  @(posedge ck);check();@(negedge ck);rst_n=1;
  rx_expected_kind=(c%3==0)?1:2;rx_expected_epoch=16'(c);rx_expected_layer=6'(c%36);rx_expected_beat=(rx_expected_kind==1)?0:5'(c%32);
  rx_payload={5'd0,rx_expected_kind,rx_expected_layer,rx_expected_epoch,rx_expected_beat,512'd0};
  if(rx_expected_kind==2)for(integer j=0;j<16;j++)rx_payload[j*32+:32]=$urandom;
  else rx_payload[18:1]=18'(c%8192);
  // Exercise every forbidden CMD data bit, plus headers, expected mismatches and time mismatches.
  if(c>=600 && c<1093)begin rx_expected_kind=1;rx_expected_beat=0;rx_payload={5'd0,4'd1,rx_expected_layer,rx_expected_epoch,5'd0,512'd0};rx_payload[19+c-600]=1;end
  if(c>=1100 && c<1136)rx_payload[512+c-1100]=~rx_payload[512+c-1100];
  rx_event=1;rx_expected=(c%29!=0);
  tx_event=(c%4==0);tx_expected=tx_event;tx_kind=3;tx_expected_kind=3;
  tx_epoch=16'(c);tx_expected_epoch=tx_epoch;tx_layer=6'(c%36);tx_expected_layer=tx_layer;tx_beat=5'(c%32);tx_expected_beat=tx_beat;
  for(integer j=0;j<16;j++)tx_data[j*32+:32]=$urandom;
  if(c%31==0)tx_expected_epoch=tx_epoch^1;
  @(posedge ck);check();if(rv[0])accepted++;if(fault[0])rejected++;
  @(negedge ck);rx_event=0;rx_expected=0;tx_event=0;tx_expected=0;
  repeat(2)begin @(posedge ck);check();end
 end
 if(errors||accepted<500||rejected<500)begin $display("KVBA_CODEC_BA3 FAIL checks=%0d errors=%0d accepted=%0d rejected=%0d",checks,errors,accepted,rejected);$fatal(1);end
 $display("KVBA_CODEC_BA3 PASS checks=%0d accepted=%0d rejected=%0d",checks,accepted,rejected);$finish;
 end
endmodule
