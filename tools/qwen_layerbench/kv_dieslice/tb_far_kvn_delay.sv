`timescale 1ns/1ps
module e3path #(parameter E3=1)(input ck,rst_n,src, output tv, output [547:0] payload, output fault);
 wire source_pin,slot,pre; wire [523:0] px,x; wire [58:0] pi,xi; wire[1:0] pg,xg;
 // Two boundary flops, exact far-model relays, real transport and real master codec.
 kvs_dly #(1,1) p0(ck,src,source_pin);
 kvs_dly #(1,3+E3) ds(ck,source_pin,slot);
 kvs_dly #(1,3+E3-1) dp(ck,source_pin,pre);
 wire tf,kf,valid; wire[547:0] encoded;
 qfd_kvn_static_transport tr(.ck(ck),.rst_n(rst_n),.word_v(pre),.word_tag({3'd2,8'd0}),.word_data({16{32'h13acbeef}}),.word_identity({16'd4,6'd1,18'd0,13'd255,6'd0}),.word_generation(2'd0),.slot_v(slot),.word_ctl_pub(40'd0),.slot_pub(10'd0),.x3(px),.x3_identity(pi),.x3_generation(pg),.fault(tf));
 kvs_dly #(585,2) dx(ck,{px,pi,pg},{x,xi,xg});
 ot_qwen_d2d_kvn_tx tx(.ck(ck),.rst_n(rst_n),.x3(x),.x3_identity(xi),.x3_generation(xg),.tx_valid(valid),.tx_payload(encoded),.fault(kf));
 kvs_dly #(549,1) p1(ck,{valid,encoded},{tv,payload});
 assign fault=tf|kf;
endmodule
module tb;
 reg ck=0,rst_n=0,src=0; always #0.4165 ck=~ck;
 wire good,bad,gf,bf; wire[547:0] gp,bp;
 e3path #(1) g(ck,rst_n,src,good,gp,gf); e3path #(2) m(ck,rst_n,src,bad,bp,bf);
 integer cyc=0,start=-1,first_good=-1,first_bad=-1,ng=0,nb=0;
 always @(posedge ck)begin
  cyc=cyc+1;
  if(src&&start<0)start=cyc;
  #0.01;
  if(rst_n&&cyc>20)begin
   if(good)begin if(first_good<0)first_good=cyc;ng=ng+1; if(gp[511:0]!=={16{32'h13acbeef}})$fatal(1,"payload");end
   if(bad)begin if(first_bad<0)first_bad=cyc;nb=nb+1;end
   if(gf||bf)$fatal(1,"transport or codec fault");
  end
 end
 initial begin
  repeat(8)@(negedge ck);rst_n=1;
  repeat(16)@(negedge ck);src=1;
  repeat(4)@(negedge ck);src=0;
  repeat(24)@(negedge ck);
  $display("E3_MICRO source=%0d good=%0d mutant=%0d good_delay=%0d mutant_delay=%0d counts=%0d/%0d",start,first_good,first_bad,first_good-start,first_bad-start,ng,nb);
  // A pulse present before the source edge is consumed by the destination on edge+9: ten edge captures total.
  if(first_good-start!=9||first_bad-start!=10||ng!=4||nb!=4)$fatal(1,"slot law mismatch");
  $display("PASS E3=1 payload/timing; MUTANT E3=2 detected one edge late");$finish;
 end
endmodule
