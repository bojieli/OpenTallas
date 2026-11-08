`timescale 1ns/1ps
module tb_fifo_local3;
 parameter MUT=0;
 reg wc=0,rc=0,wrn=0,rrn=0,pending=0,rdy=0;
 reg [95:0] data=0;
 wire gr,gv,go,gu,nr,nv,no,nu;
 wire [95:0] gd,nd;
 integer wh=3,rh=5,seed=17,checks=0,errors=0,wcount=0;
 always begin #(wh) wc=~wc; end
 always begin #(rh) rc=~rc; end
 fifo_gold #(.WIDTH(96),.DEPTH(8)) g(wc,wrn,pending&&gr,gr,data,go,rc,rrn,gv,rdy,gd,gu);
 ot_hbm_svc_async_fifo_local3 #(.WIDTH(96),.DEPTH(8),.MUT(MUT)) n(wc,wrn,pending&&gr,pending,nr,data,no,rc,rrn,nv,rdy,nd,nu);
 always @(negedge wc) begin
  wcount=wcount+1;
  pending <= wcount%31<24;
  data <= {32'hface0000^wcount,32'hdeadbeef+wcount,32'h12345678-wcount};
 end
 always @(negedge rc) rdy <= $random(seed)%4!=0;
 task chk;
 begin
  checks=checks+1;
  if ({gr,gv,go,gu} !== {nr,nv,no,nu} || (gv && gd!==nd)) begin
   errors=errors+1;
   if(errors<4)$display("DIFF t=%0t ready=%b/%b valid=%b/%b data=%h/%h",$time,gr,nr,gv,nv,gd,nd);
  end
 end
 endtask
 always @(negedge wc) #1 chk();
 always @(negedge rc) #1 chk();
 initial begin
  if($value$plusargs("WH=%d",wh))begin end
  if($value$plusargs("RH=%d",rh))begin end
  #17 wrn=1;#9 rrn=1;
  repeat(8) begin
   #3301 wrn=0; #17 rrn=0; #23 wrn=1; #13 rrn=1;
  end
  #3301;
  if(errors==0)$display("PASS MUT=%0d checks=%0d",MUT,checks);
  else $display("FAIL MUT=%0d errors=%0d checks=%0d",MUT,errors,checks);
  $finish;
 end
endmodule
