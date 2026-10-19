`timescale 1ns/1ps
module tb_stream; integer MUT=0; initial if(!$value$plusargs("MUT=%d",MUT)) MUT=0;
 reg diag_logged=0;reg ck=0,rst=0;always #5 ck=~ck;
 reg[3:0] prior_sid=0;reg[3:0] sid=0;reg[1:0] dir=0;reg[27:0] tag=0;reg cfg=0;reg[1087:0] sw=0,se=0;reg[7:0] we=0;reg[191:0] addr=0;reg[255:0] data=0;
 wire[1087:0] le,lw,qe,qw;wire lv,qv,lbad,qbad,lf,qf,ltw,qtw;
 wire[1:0] lk,qk;wire[23:0] la,qa,lxa,qxa;wire[1023:0] ld,qd,lxd,qxd;
 qfd_dv_stream u_l(.ck(ck),.rst_n(rst),.sid(sid),.cfg_v(cfg),.cfg_dir(dir),.cfg_tag(tag),
 .sw_i(sw),.se_i(se),.so_e(le),.so_w(lw),.xw_we(we),.xw_addr(addr),.xw_data(data),
 .tw_we(ltw),.tw_kind(lk),.tw_addr(la),.tw_data(ld),.xt_v(lv),.xt_a(lxa),.xt_d(lxd),.xt_bad(lbad),.fault(lf));
 qfd_dv_stream_controls u_q(.rst_n_copies({(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst)}),.cfg_v_copies({cfg,cfg}),.sw_i_copies({(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),(sw[1087] ^ (MUT==1)),sw[1086],sw[1086],sw[1085],sw[1085],sw[1084],sw[1084]}),.se_i_copies({se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087],se[1087]}),.xw_we_copies({we[7],we[7],we[6],we[6],we[5],we[5],we[4],we[4],we[7],we[6],we[5],we[4],we[3],we[2],we[1],we[7],we[7],we[6],we[6],we[5],we[5],we[4],we[4],we[2],we[0]}),.xw_addr_copies({addr[170],addr[98],addr[74],addr[50],addr[26],addr[2]}),.ck(ck),.rst_n(rst),.sid(MUT==4 ? prior_sid : (sid ^ (MUT==2 ? 4'd1 : 4'd0))),.cfg_v(cfg),.cfg_dir(dir),.cfg_tag(tag),
 .sw_i(sw),.se_i(se),.so_e(qe),.so_w(qw),.xw_we(we),.xw_addr(addr),.xw_data(data),
 .tw_we(qtw),.tw_kind(qk),.tw_addr(qa),.tw_data(qd),.xt_v(qv),.xt_a(qxa),.xt_d(qxd),.xt_bad(qbad),.fault(qf));
 reg[31:0] seed=32'h76dc563a;integer cycle=0,age=0;
 function automatic[31:0] step(input[31:0] x);
  reg[31:0] y;begin y=x^(x<<13);y=y^(y>>17);step=y^(y<<5);end
 endfunction
 always @(negedge ck) begin
  rst=!(cycle<8||(cycle>=700&&cycle<708));cfg=rst&&(age==17||cycle%31==0);prior_sid=sid;sid=4'(cycle%16);dir=2'(cycle%4);tag=28'(cycle*12345);
  for(integer b=0;b<1088;b=b+1) begin
   if(b%32==0) seed=step(seed);sw[b]=seed[b%32];seed=step(seed);se[b]=seed[b%32];
  end
  sw[1087]=rst&&age>=20&&cycle%5==0;se[1087]=rst&&age>=20&&cycle%7==0;
  sw[1086:1084]=3'(cycle%4);se[1086:1084]=3'((cycle+1)%4);
  sw[1083:1080]=4'(cycle%16);se[1083:1080]=4'((cycle+5)%16);
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

  if(!rst && {qe[1087],qw[1087],qtw,qv,qbad,qf} !== {le[1087],lw[1087],ltw,lv,lbad,lf}) $fatal(1,"STREAM_RESET_MISMATCH cycle%0d MUT%0d",cycle,MUT);
  if(age>=20 && !diag_logged && {le,lw,ltw,lk,la,ld,lv,lxa,lxd,lbad,lf}!=={qe,qw,qtw,qk,qa,qd,qv,qxa,qxd,qbad,qf}) begin
   diag_logged=1;
   $display("STRICT_INITIAL_DIAGNOSTIC cycle%0d tw_v%0b/%0b x_v%0b/%0b relaydiff%0b controldiff%0b twdatadiff%0b xdatadiff%0b MUT%0d",cycle,ltw,qtw,lv,qv,{le,lw}!=={qe,qw},{ltw,lv,lbad,lf}!=={qtw,qv,qbad,qf},{lk,la,ld}!=={qk,qa,qd},{lxa,lxd}!=={qxa,qxd},MUT);
  end
  if(age>=20 && ({le,lw,ltw,lv,lbad,lf}!=={qe,qw,qtw,qv,qbad,qf} ||
     (ltw && {lk,la,ld}!=={qk,qa,qd}) || (lv && {lxa,lxd}!=={qxa,qxd})))
   $fatal(1,"STREAM_EQ_MISMATCH cycle%0d MUT%0d",cycle,MUT);
  if(cycle==10000) begin $display("STREAM_NATIVE_QUALIFIED_EQ PASS edges10000 resets2 varyingSID/config concurrentrelay/taps/fullcompletion controls+allvalidpayload");$finish;end
 end
endmodule
