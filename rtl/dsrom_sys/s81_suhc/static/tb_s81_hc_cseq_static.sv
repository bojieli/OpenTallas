`timescale 1ns/1ps
module tb_s81_hc_cseq_static;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,cv=0,ya=0;reg[83:0]cd=0;reg[31:0]yt=32'h12345678;reg[4:0]yr=0;
 wire dv,flt,onl,ypop,fault;wire[7:0]dt;wire[3:0]fc;
 wire[1:0]rqv;wire[27:0]rqr;wire[6:0]wv,ev,xv;wire[1167:0]wd,ed,xd;
 wire ngo,jv,fq,fy,je,jci;wire[2:0]kind;wire[13:0]base;
 integer cyc=0,t0,count=0,first=-1,last=-1,done=-1;
 ot_s81_hc_cseq_static #(.POST_FIRST(16),.CMD_LAT(2),.PD(40))u(
  .cck(clk),.crs(rn),.sk(clk),.srs(rn),.n_cmd_v(cv),.n_cmd_d(cd),.n_done_v(dv),.n_done_tag(dt),.n_inp(1'b1),
  .n_rq_v(rqv),.n_rq_row(rqr),.n_rs_v(2'd0),.n_rs_d(1024'd0),.n_flt(flt),.n_online(onl),.n_fcode(fc),
  .n_yacc(ya),.n_y_tag(yt),.n_y_row(yr),.command_y_tag(32'h12345678),.command_done_age(32'd76),.command_ss_age(32'd0),.command_scalar_age(32'd0),.n_ypop(ypop),.w_flt(1'b0),.e_flt(1'b0),
  .w_fv(wv),.e_fv(ev),.c_fv(xv),.w_fd(wd),.e_fd(ed),.c_fd(xd),.ngo(ngo),.t_ssv(1'b0),.t_ss(32'd0),.t_flt(1'b0),
  .j_v(jv),.kind(kind),.base(base),.f_q(fq),.f_y(fy),.j_end(je),.fault(fault),.j_civ(jci),
  .x_wdone(1'b0),.x_pob(1'b0),.x_f1(1'b0),.x_f4(1'b0),.c_yfl(1'b0));
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)begin
  if(ypop)begin count++;if(first<0)first=cyc-t0;last=cyc-t0;end
  if(dv)done=cyc-t0;
 end
 initial begin
  repeat(4)@(negedge clk);rn=1;repeat(6)@(negedge clk);
  cd[30:7]=24'h300000;cd[6:0]=7'd9;cv=1;t0=cyc;@(negedge clk);cv=0;
  // Command E0 -> two inputpin stages -> take E2. age0 startsE3.
  // ya is captured one edge before age16's fixed take atE19.
  repeat(17)@(negedge clk);
  for(integer row=0;row<20;row=row+1)begin
   ya=1;yr=row;yt=32'h12345678;
   if($test$plusargs("MUT_MISSING")&&row==7)ya=0;
   @(negedge clk);
  end
  ya=0;repeat(60)@(negedge clk);
  $display("HC_STATIC_CSEQ calendar count%0d first%0d last%0d done%0d fault%0d",count,first,last,done,fault);
  if(count!=20||done<0||fault)$fatal(1,"HC_STATIC_CSEQ FAIL");
  $display("HC_STATIC_CSEQ PASS");$finish;
 end
endmodule
