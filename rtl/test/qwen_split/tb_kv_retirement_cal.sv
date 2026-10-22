`timescale 1ns/1ps
module tb_kv_retirement_cal;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,go=0;reg [13:0] ctx=1;
 wire [175:0] a,b;wire [15:0] ar,at,ae,br,bt,be;
 wire ad,av,af,bd,bv,bf;
 qkd_attn_cal_gen_b #(.STRETCH(1)) old_cal(.ck(ck),.rst_n(rst_n),.cfg_cal(24'h010000),
   .go(go),.ctx_t(ctx),.epoch(16'd1),.cal(a),.rx_cmd(ar),.tx_first(at),.end_age(ae),
   .cal_epoch(),.done(ad),.valid(av),.fault(af));
 qkd_attn_cal_gen_b #(.STRETCH(1),.STATUS_DELAY(200)) delayed_cal(.ck(ck),.rst_n(rst_n),.cfg_cal(24'h010000),
   .go(go),.ctx_t(ctx),.epoch(16'd1),.cal(b),.rx_cmd(br),.tx_first(bt),.end_age(be),
   .cal_epoch(),.done(bd),.valid(bv),.fault(bf));
 integer checks=0;
 always @(negedge ck)if(rst_n&&ad)begin
   if(!bd||!av||!bv||af||bf||a!=b||ar!=br||at!=bt||be!=ae+200)
     $fatal(1,"STATUS tail moved service/RESULT calendar or failed end pricing");
   checks=checks+1;
 end
 initial begin
   repeat(3)@(negedge ck);rst_n=1;repeat(5)@(negedge ck);
   for(integer n=1;n<=8192;n=n+1)begin ctx=14'(n);go=1;@(negedge ck);end
   go=0;repeat(20)@(negedge ck);
   if(checks!=8192)$fatal(1,"missing calendar outputs");
   $display("PASS delayed STATUS all8192 contexts identical RESULT/service, end+200");$finish;
 end
endmodule
