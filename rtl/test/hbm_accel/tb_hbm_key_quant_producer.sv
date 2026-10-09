`timescale 1ns/1ps
module tb_hbm_key_quant_producer;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,start=0,bv=0,kr=0;wire sr,br,kv,done,fault;
 reg[19:0] idx;reg[5:0] layer;reg[1:0] bn;reg[1023:0] bd;
 wire[543:0] kd;wire[19:0] oi;wire[5:0] ol;
 ot_hbm_key_quant_producer #(.ENABLE(1)) dut(.clk(clk),.por_n(por_n),
 .start(start),.start_ready(sr),.key_index(idx),.layer(layer),
 .block_v(bv),.block_r(br),.block_number(bn),.block_data(bd),
 .key_v(kv),.key_r(kr),.key_data(kd),.out_key_index(oi),.out_layer(ol),.done(done),.fault(fault));
 reg[1023:0] inputs[0:127];reg[543:0] expected[0:31];
 string ip,ep;integer key,b,n,checks=0;reg[569:0] held;
 initial begin
  if(!$value$plusargs("INPUT=%s",ip)||!$value$plusargs("EXPECTED=%s",ep))$fatal(1,"paths required");
  $readmemh(ip,inputs);$readmemh(ep,expected);
  repeat(3)@(negedge clk);por_n=1;
  for(key=0;key<32;key=key+1)begin
   if(!sr)$fatal(1,"missing start capacity");
   idx=20'(key*768+7);layer=6'(key%40);start=1;
   @(negedge clk);start=0;
   // Source metadata may move after acceptance; retained route must not.
   idx=20'hfffff;layer=39;
   for(b=0;b<4;b=b+1)begin
    if(!br)$fatal(1,"prepaid input missing");
    bn=2'(b);bd=inputs[4*key+b];bv=1;
    @(negedge clk);bv=0;
    repeat(key%3)@(negedge clk);
   end
   while(!kv)begin @(negedge clk);if(fault)$fatal(1,"quant fault");end
   if(kd!==expected[key]||oi!==20'(key*768+7)||ol!==6'(key%40))$fatal(1,"key mismatch %0d",key);
   held={ol,oi,kd};
   repeat(19)begin
    @(negedge clk);
    if(!kv||{ol,oi,kd}!==held||sr||br)$fatal(1,"key retention changed");
   end
   kr=1;@(negedge clk);kr=0;
   if(!done||kv||!sr)$fatal(1,"append acceptance missing");checks=checks+1;
  end
  start=1;idx=0;layer=2;@(negedge clk);start=0;
  bn=1;bd=inputs[0];bv=1;@(negedge clk);bv=0;
  if(!fault||kv||br||sr)$fatal(1,"wrong block order accepted");
  $display("PASS_KEY_QUANT keys=%0d finite68byte_hold=1 order_negative=1 fullchain_qualified=0",checks);
  $finish;
 end
endmodule
