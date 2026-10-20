`timescale 1ns/1ps
module tb_stream #(parameter integer MUT=0, STATIC=1);
 reg ck=0,rst=0;always #5 ck=~ck;
 reg cfg=0;reg[1087:0] sw=0,se=0;reg[7:0] we=0;reg[191:0] addr=0;reg[255:0] data=0;
 wire[1087:0] le,lw,qe,qw;wire lv,qv,lbad,qbad,lf,qf,ltw,qtw;
 wire[1:0] lk,qk;wire[23:0] la,qa,lxa,qxa;wire[1023:0] ld,qd,lxd,qxd;
 qfd_dv_stream u_l(.ck(ck),.rst_n(rst),.sid(4'd3),.cfg_v(cfg),.cfg_dir(2'd3),.cfg_tag(28'h1234567),
 .sw_i(sw),.se_i(se),.so_e(le),.so_w(lw),.xw_we(we),.xw_addr(addr),.xw_data(data),
 .tw_we(ltw),.tw_kind(lk),.tw_addr(la),.tw_data(ld),.xt_v(lv),.xt_a(lxa),.xt_d(lxd),.xt_bad(lbad),.fault(lf));
 qfd_dv_stream_packer #(.MUT(MUT),.STATIC_PACKER(STATIC)) u_q(.ck(ck),.rst_n(rst),.sid(4'd3),.cfg_v(cfg),.cfg_dir(2'd3),.cfg_tag(28'h1234567),
 .sw_i(sw),.se_i(se),.so_e(qe),.so_w(qw),.xw_we(we),.xw_addr(addr),.xw_data(data),
 .tw_we(qtw),.tw_kind(qk),.tw_addr(qa),.tw_data(qd),.xt_v(qv),.xt_a(qxa),.xt_d(qxd),.xt_bad(qbad),.fault(qf));
 reg[31:0] seed=32'h76dc563a;integer cycle=0,age=0;
 function automatic[31:0] step(input[31:0] x);
  reg[31:0] y;begin y=x^(x<<13);y=y^(y>>17);step=y^(y<<5);end
 endfunction
 always @(negedge ck) begin
  rst=!(cycle<8||(cycle>=700&&cycle<708));cfg=rst&&age==17;
  for(integer b=0;b<1088;b=b+1) begin
   if(b%32==0) seed=step(seed);sw[b]=seed[b%32];seed=step(seed);se[b]=seed[b%32];
  end
  sw[1087]=rst&&age>=20&&cycle%5==0;se[1087]=rst&&age>=20&&cycle%7==0;
  sw[1086:1084]=3'(cycle%4);se[1086:1084]=3'((cycle+1)%4);
  sw[1083:1080]=15;se[1083:1080]=15;
  we=(rst&&age>=20)?((cycle%256<192)?8'hff:8'(seed)):0;
  for(integer l=0;l<8;l=l+1) begin
   addr[24*l+:24]=24'((((age-20)/8)<<6)|(((age-20)%8)*8+l));
   if(cycle%256>=192) begin seed=step(seed);addr[24*l+:6]=seed[5:0];end
   seed=step(seed);data[32*l+:32]=seed;
  end
 end
 always @(posedge ck) begin
  cycle=cycle+1;if(!rst) age=0;else age=age+1;
  #1;
  if(age>=20 && {u_l.nm,u_l.nb,u_l.pbad} !== {u_q.nm,u_q.nb,u_q.pbad}) $fatal(1,"PACKER_INTERNAL_MISMATCH cycle%0d MUT%0d",cycle,MUT);
  if(age>=20&&{le,lw,ltw,lk,la,ld,lv,lxa,lxd,lbad,lf}!=={qe,qw,qtw,qk,qa,qd,qv,qxa,qxd,qbad,qf})
   $fatal(1,"STREAM_EQ_MISMATCH cycle%0d MUT%0d",cycle,MUT);
  if(cycle==10000) begin $display("STATIC_STREAM_EQ PASS words10000 resets2 ownpack/pass/taps/faults alloutputs");$finish;end
 end
endmodule
