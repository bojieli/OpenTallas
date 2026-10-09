`timescale 1ps/1ps
module tb_hbm_index_prefetch #(parameter MUT=0);
 reg sc=0,hc=0,rst_n=0;always begin #416 sc=1;#417 sc=0;end always #512 hc=~hc;
 reg req_v=0,receipt_r=0,admit=0;reg[98:0]req_d=0;
 wire req_r,receipt_v,source_fault,sink_fault,ip_v;wire[72:0]receipt_frame;
 wire[98:0]ip_d;wire[106:0]rq_raw;wire[1:0]rq_epoch,rc_epoch,rc_release;
 wire[80:0]rc_raw;wire ip_take=ip_v&&admit;
 wire[106:0]rq_in=rq_raw ^ ((MUT==1)?107'd1:(MUT==2)?(107'd1<<99):(MUT==3)?107'd3:107'd0);
 wire[80:0]wrong_receipt;
 wire[72:0]wrong_frame=req_d[98:26] ^ ((MUT==7)?73'h10000:73'd1);
 ot_secded_enc #(.K(73),.R(8)) bad_enc(.clk(hc),.d(wrong_frame),.q(wrong_receipt));
 wire[80:0]rc_in=(MUT==6||MUT==7)?wrong_receipt:
  rc_raw ^ ((MUT==4)?81'd1:(MUT==5)?81'd3:81'd0);
 ot_hbm_index_prefetch_source source(.clk(sc),.rst_n(rst_n),.req_v(req_v),.req_d(req_d),.req_r(req_r),
  .receipt_v(receipt_v),.receipt_r(receipt_r),.receipt_frame(receipt_frame),.fault(source_fault),
  .rq_w(rq_raw),.rq_epoch(rq_epoch),.rc_w(rc_in),.rc_epoch(rc_epoch),.rc_fault(sink_fault),.rc_release(rc_release));
 ot_hbm_index_prefetch_sink sink(.clk(hc),.rst_n(rst_n),.rq_w(rq_in),.rq_epoch(rq_epoch),
  .ip_v(ip_v),.ip_d(ip_d),.ip_take(ip_take),.fault(sink_fault),.rc_w(rc_raw),.rc_epoch(rc_epoch),.rc_release(rc_release));
 integer accepted=0,receipts=0,t=0,rep;time sent,actual_take,returned;
 always@(posedge hc)if(rst_n&&ip_take)begin
  if(ip_d!==req_d)$fatal(1,"decoded descriptor mismatch");
  accepted=accepted+1;actual_take=$time;
 end
 initial begin
  repeat(10)@(negedge sc);rst_n=1;
  for(rep=0;rep<2;rep=rep+1)begin
   @(negedge sc);req_d={73'(73'h12ab34001200345678+((MUT==8)?0:rep)),15'(8006+rep*8),9'd342,2'd2};
   req_v=1;admit=0;sent=$time;
   repeat(70)@(negedge hc);
   if(accepted!=rep)$fatal(1,"receipt before actual admission");
   if(receipt_v)$fatal(1,"fake receipt before actual admission");
   admit=1;t=0;
   if(MUT==3||MUT==5||MUT==6||MUT==7||(MUT==8&&rep==1))begin
    while(!source_fault)begin @(negedge sc);t=t+1;if(t>3000)$fatal(1,"expected fault missing");end
    if(receipt_v)$fatal(1,"fault fabricated receipt");
    if((MUT==3||MUT==8)&&accepted!=rep)$fatal(1,"poison admitted descriptor");
    if(req_r)$fatal(1,"fault released descriptor debt");
    $display("PASS_HBM_INDEX_PREFETCH_FAULT mut=%0d accepted=%0d receipts=%0d",MUT,accepted,receipts);$finish;
   end
   while(!receipt_v)begin
    @(negedge sc);t=t+1;
    if(source_fault||sink_fault)$fatal(1,"unexpected protection fault");
    if(t>3000)$fatal(1,"receipt missing");
   end
   returned=$time;
   if(receipt_frame!==req_d[98:26])$fatal(1,"full73 identity mismatch");
   if(accepted!=rep+1)$fatal(1,"receipt lacks actual admission");
   repeat(20)begin @(negedge sc);if(!receipt_v||receipt_frame!==req_d[98:26]||req_r)$fatal(1,"held receipt changed");end
   receipt_r=1;@(negedge sc);receipt_r=0;receipts=receipts+1;
   repeat(20)@(negedge sc);
   if(req_r||accepted!=rep+1)$fatal(1,"held source valid repeated request");
   req_v=0;t=0;
   while(!req_r)begin @(negedge sc);t=t+1;if(t>3000)$fatal(1,"debt not released");end
   $display("PREFETCH_MAILBOX rep=%0d sent_ps=%0t accepted_ps=%0t receipt_ps=%0t accepted_to_receipt_ps=%0t",rep,sent,actual_take,returned,returned-actual_take);
  end
  if(accepted!=2||receipts!=2)$fatal(1,"transaction count");
  $display("PASS_HBM_INDEX_PREFETCH mut=%0d",MUT);$finish;
 end
endmodule
