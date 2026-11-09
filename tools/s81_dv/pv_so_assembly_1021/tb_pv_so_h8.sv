`timescale 1ns/1ps
module tb_pv_so_h8;
 reg clk=0;always #0.4165 clk=~clk;reg rst=0,cv=0,pp=0,launch=0;
 reg[19:0]owner=20'h92345;reg[7:0]se=8'h31,so=8'h67;reg[2:0]pr=0;reg[511:0]par=0;
 reg[561:0]lp=0,pvpeer=0;wire jv,jf;wire[1:0]jq;wire[512:0]jd;
 integer mut=0;
 dsdv_pv_half_join_h8 join_(.clk(clk),.rst_n(rst),.cfg_v(cv),.local_first(16'd20),.peer_first(mut==4?16'd21:16'd360),
  .local_first1(16'd700),.peer_first1(16'd1040),.local_pv(lp),.peer_pv(pvpeer),.pv_v(jv),.pv_quarter(jq),.pv_d(jd),.fault(jf));
 wire qv,ready,done,fault;wire[511:0]qd;wire[11:0]fc;
 dsdv_pv_so_ingress_h8 #(.ENABLE(1),.HEADER_DEN(1)) dut(.clk(clk),.rst_n(rst),.cfg_v(cv),.cfg_owner(owner),.cfg_position(21'd777),
 .cfg_se_jid(se),.cfg_so_jid(so),.pv_v(jv),.pv_quarter(jq),.pv_d(jd),.param_v(pp),.param_row(pr),.param_owner(owner),.param_position(21'd777),.param_d(par),
 .den_v(1'b0),.den_mask(16'd0),.den_owner(20'd0),.den_jid(8'd0),.launch(launch),.q_v(qv),.q_d(qd),.ready(ready),.done(done),.fault(fault),.fault_code(fc));
 reg[32:0]jcmd=0;wire[1:0]jdn;wire[514:0]core_q;
 ot_s81_svc_job gate_(.ck(clk),.rs_n(rst),.j_cmd(jcmd),.j_dn(jdn),.q({2'd0,qd,qv}),.core_q(core_q),.ad(1026'd0),.xd(514'd0),.od(514'd0));
 function automatic[31:0]val(input integer h,d);val=32'h3f000000^(32'(h)<<17)^32'(d*101);endfunction
 function automatic[511:0]param(input integer r);for(integer l=0;l<16;l=l+1)param[32*l+:32]=32'h40000000^32'(r*1000+l);endfunction
 function automatic[511:0]hdr(input bit op,input integer h);
 reg[511:0]x;begin x=0;x[511:508]=9;x[503]=1;x[502:495]=owner[7:0];x[479:459]=777;x[491:480]=op?32:5;x[458:449]=owner[17:8];x[0]=!op;x[4:1]=5;x[12:5]=so;x[13]=op;if(op)x[29:14]=16'd1<<h;hdr=x;end endfunction
 integer edge_n=0,cfg_edge=-1,n=0,first=-1,last=-1,errors=0;
 always @(posedge clk)begin edge_n=edge_n+1;if(cv)cfg_edge=edge_n;end
 reg[511:0]expected;integer ordinal,hh,rr,off;
 always @(negedge clk)if(qv)begin
  if(core_q!=={2'd0,qd,1'b1} || jdn[1])$fatal(1,"H8_JOB_GATE");
  if(first<0)first=edge_n;last=edge_n;
  if(n==0)begin expected=hdr(0,0);off=0;end
  else if(n<=5)begin expected=param(n-1);off=n;end
  else begin
   ordinal=(n-6)/33;hh=(ordinal%2)*8+ordinal/2;rr=(n-6)%33;
   off=45+65*ordinal+(rr==0?0:1+2*(rr-1));
   if(rr==0)expected=hdr(1,hh);
   else for(integer l=0;l<16;l=l+1)expected[32*l+:32]=val(hh,16*(rr-1)+l);
  end
  if(qd!==expected)errors=errors+1;
  if(edge_n-first!=off)$fatal(1,"H8_CADENCE word%0d got%0d expected%0d",n,edge_n-first,off);
  n=n+1;
 end
 task tick;@(negedge clk);endtask
 integer age_,window_,w,tile_,beat_,wi_,pass_,actualpass_,dim_,h;
 reg[512:0]word_;
 initial begin
  if($value$plusargs("mut=%d",mut));
  repeat(4)tick();rst=1;repeat(5)tick();
  tick();cv=1;jcmd={1'b1,24'((17<<7)|1),owner[7:0]};tick();cv=0;jcmd=0;
  for(integer p=0;p<5;p=p+1)begin tick();pp=1;pr=3'(p);par=param(p);end
  tick();pp=0;
  while(edge_n-cfg_edge<1380)begin
   tick();age_=edge_n+1-cfg_edge;window_=-1;
   if(age_>=20 && age_<340)begin window_=0;w=age_-20;end
   if(age_>=360 && age_<680)begin window_=1;w=age_-360;end
   if(age_>=700 && age_<1020)begin window_=2;w=age_-700;end
   if(age_>=1040 && age_<1360)begin window_=3;w=age_-1040;end
   lp=0;pvpeer=0;
   if(window_>=0 && !(mut==3 && window_>=2))begin
    pass_=window_/2;actualpass_=pass_;
    tile_=(window_%2)*8+w/40;beat_=(w%40)/5;wi_=w%5;word_=0;
    if(wi_==0)begin
     word_[512]=1;word_[98]=1;word_[97:94]=4'(tile_);word_[93:92]=2'(tile_/4);word_[91:72]=owner;
     word_[119:99]=777;word_[71:64]=8'(beat_);word_[32]=1'(actualpass_);
     if(tile_/8==pass_)begin word_[120]=1;word_[128:121]=se;end
     if(mut==5 && window_==2 && w==0)word_[32]=0;
    end else begin
     dim_=32*tile_+8*(wi_-1)+beat_;
     for(h=0;h<8;h=h+1)word_[32*h+:32]=val(8*((mut==1)?1-pass_:pass_)+h,dim_);
     if(mut==2 && window_==0 && w==1)word_[300]=1;
    end
    if(window_%2==0)lp={48'd0,word_,1'b1};else pvpeer={48'd0,word_,1'b1};
   end
  end
  tick();lp=0;pvpeer=0;repeat(4)tick();
  if(mut==2 || mut==4 || mut==5)begin
   if(!(fault||jf))$fatal(1,"H8_MUTANT_NOT_CAUGHT %0d",mut);
   $display("H8_PVSO_CAUGHT mut%0d fc%h join%0d",mut,fc,jf);$finish;
  end
  if(mut==3)begin tick();launch=1;tick();launch=0;repeat(4)tick();if(!fault)$fatal(1,"H8_DROP_NOT_CAUGHT");$display("H8_PVSO_CAUGHT mut3 fc%h",fc);$finish;end
  if(!ready || fault || jf)$fatal(1,"H8_NOT_READY ready%0d fc%h join%0d",ready,fc,jf);
  tick();launch=1;tick();launch=0;
  wait(done);repeat(3)tick();
  if(mut==1)begin if(errors==0)$fatal(1,"H8_SWAP_NOT_CAUGHT");$display("H8_PVSO_CAUGHT mut1 errors%0d",errors);end
  else begin
  if(n!=534 || last-first!=1083 || errors!=0 || fault || jf)$fatal(1,"H8_RESULT words%0d span%0d errors%0d fc%h join%0d",n,last-first,errors,fc,jf);
  $display("H8_PVSO_PASS words%0d span%0d exact8192FP32 all16heads 2passes",n,last-first);end
  $finish;
 end
 initial begin #10000;$fatal(1,"H8_TIMEOUT");end
endmodule
