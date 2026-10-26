`timescale 1ns/1ps
module tb_s81_hc_crooty_roots;
 reg ck=0;always #5 ck=~ck;
 reg rst=0,ya;reg[11:0]en=12'hfff;
 wire[11:0]cks={12{ck}}&en;
 reg[2815:0]y;reg[2171:0]w;reg[10:0]req;
 wire[2815:0]py0,py1;wire f0,f1;wire[2171:0]wo0,wo1;
 ot_s81_hc_crooty refroot(.sk(ck),.srs(rst),.y_s(y),.yacc(ya),.p_req(req),.p_w(w),.p_y(py0),.p_flt(f0),
 .wq_v(wo0[3:0]),.wq_row(wo0[59:4]),.wq_mask(wo0[123:60]),.wq_d(wo0[2171:124]));
 ot_s81_hc_crooty_roots dut(.sk(ck),.sk_leaf(cks),.srs(rst),.y_s(y),.yacc(ya),.p_req(req),.p_w(w),.p_y(py1),.p_flt(f1),
 .wq_v(wo1[3:0]),.wq_row(wo1[59:4]),.wq_mask(wo1[123:60]),.wq_d(wo1[2171:124]));
 integer checks=0,errors=0,stop=0;
 initial begin
  if($value$plusargs("STOP=%d",stop))begin end
  for(integer c=0;c<600;c=c+1)begin
   @(negedge ck);rst=(c>=5&&!(c>=172&&c<177));
   ya=(c%64>=8&&c%64<16);req={11{c%64>=32&&c%64<40}};
   for(integer i=0;i<88;i=i+1)y[i*32+:32]=$random;
   for(integer i=0;i<2172;i=i+1)w[i]=$random;
   if(stop>0&&c>330)en[stop-1]=0;
   @(posedge ck);#1;
   if(c>50&&!(c>=172&&c<225))begin
    checks=checks+1;
    if({py0,f0,wo0}!=={py1,f1,wo1})errors=errors+1;
   end
  end
  $display("CROOTY_ROOTS checks=%0d errors=%0d stop=%0d",checks,errors,stop);
  if(errors)$fatal(1,"CROOTY_ROOTS_FAIL");
  $display("CROOTY_ROOTS_PASS");$finish;
 end
endmodule
