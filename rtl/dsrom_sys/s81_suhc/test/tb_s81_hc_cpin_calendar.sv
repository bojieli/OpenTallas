`timescale 1ns/1ps
module tb_s81_hc_cpin_calendar;
`ifndef COMMAND_POST_AGES
`define COMMAND_POST_AGES 0
`endif
 reg[639:0] post_ages,expected_post;wire[639:0]n_post_ages;
 reg ck=0;always #5 ck=~ck;
 reg rst=0,enable=1;wire dck=ck&enable;
 reg cv,yv;reg[83:0]cmd;reg[2559:0]y;
 reg[31:0]tag,ctag,doneage,ssage,scalarage;reg[4:0]row;
 wire nv,acc,aw,ae,ready;wire[83:0]nd;wire[2559:0]ny;
 wire[31:0]ntag,nctag,nda,nsa,nra;wire[4:0]nrow;
 ot_s81_hc_cpin_calendar #(.COMMAND_POST_AGES(`COMMAND_POST_AGES))dut(
 .command_post_ages(post_ages),.n_command_post_ages(n_post_ages),.cck(1'b0),.crs(rst),.sk(dck),.srs(rst),
 .c_cmd_v(cv),.c_cmd_d(cmd),.c_done_v(),.c_done_tag(),.inp(1'b1),.rq_v(),.rq_row(),
 .rs_v(2'b0),.rs_d(1024'b0),.flt(),.online(),.fcode(),.y_v(yv),.y_rdy(ready),.y_s(y),
 .yacc_w(aw),.yacc_e(ae),.n_cmd_v(nv),.n_cmd_d(nd),.n_done_v(1'b0),.n_done_tag(8'b0),
 .n_inp(),.n_rq_v(2'b0),.n_rq_row(28'b0),.n_rs_v(),.n_rs_d(),.n_flt(1'b0),.n_online(1'b1),
 .n_fcode(4'b0),.n_yacc(acc),.n_y(ny),.n_ypop(1'b0),
 .y_tag(tag),.y_row(row),.command_y_tag(ctag),.command_done_age(doneage),
 .command_ss_age(ssage),.command_scalar_age(scalarage),.n_y_tag(ntag),.n_y_row(nrow),
 .n_command_y_tag(nctag),.n_command_done_age(nda),.n_command_ss_age(nsa),.n_command_scalar_age(nra));
 integer checks=0,errors=0,mut=0;
 initial begin
  if($value$plusargs("STOP=%d",mut))begin end
  for(integer c=0;c<300;c=c+1)begin
   @(negedge ck);rst=(c>3&&!(c>=150&&c<154));
   cv=(c%4==0);yv=(c%3!=0);cmd={$random,$random,$random};
   tag=$random;ctag=$random;doneage=$random;ssage=$random;scalarage=$random;row=c%20;
   for(integer i=0;i<2560;i=i+1)y[i]=$random;
   for(integer i=0;i<20;i=i+1)post_ages[i*32+:32]=32'(c*24+i);
   if(cv)expected_post=post_ages;
   if(mut&&c>220)enable=0;
   @(posedge ck);#1;
   if(rst)begin
    checks=checks+1;
    if(`COMMAND_POST_AGES && n_post_ages!==expected_post)errors=errors+1;
    if({nv,nd,acc,aw,ae,ny,ntag,nrow,nctag,nda,nsa,nra}!=={cv,cmd,yv,yv,yv,y,tag,row,ctag,doneage,ssage,scalarage})errors=errors+1;
   end
  end
  $display("CPIN_CALENDAR checks=%0d errors=%0d",checks,errors);
  if(errors)$fatal(1,"CPIN_CALENDAR_FAIL");
  $display("CPIN_CALENDAR_PASS");$finish;
 end
endmodule
