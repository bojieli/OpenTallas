`timescale 1ns/1ps
module tb_qcore_r17_rowen;
 reg [3:0] hit,rr; reg[7:0] row;
 wire[3:0] e0,e1,e2,eb;wire[15:0]d0,d1,d2,db;wire c0,c1,c2,cb;
 ot_hbm_su_qcore_r13_wb #(.ROW_EN(0)) legacy(.sm(hit),.wbk(12'b0),.row(row),.wd16(64'h1004200340028001),.rr_hit(rr),.rrd16(16'ha55a),.en(e0),.d(d0),.conf(c0));
 ot_hbm_su_qcore_r13_wb #(.ROW_EN(1)) sop(.sm(hit),.wbk(12'b0),.row(row),.wd16(64'h1004200340028001),.rr_hit(rr),.rrd16(16'ha55a),.en(e1),.d(d1),.conf(c1));
 ot_hbm_su_qcore_r13_wb #(.ROW_EN(2)) u_priority(.sm(hit),.wbk(12'b0),.row(row),.wd16(64'h1004200340028001),.rr_hit(rr),.rrd16(16'ha55a),.en(e2),.d(d2),.conf(c2));
 // Causal negative: actual candidate writer3 row bit misbound, all other pins identical.
 ot_hbm_su_qcore_r13_wb #(.ROW_EN(1)) wrong_row(.sm(hit),.wbk(12'b0),.row(row^8'h40),.wd16(64'h1004200340028001),.rr_hit(rr),.rrd16(16'ha55a),.en(eb),.d(db),.conf(cb));
 integer n,bad=0,negative=0;
 initial begin
  for(n=0;n<65536;n=n+1)begin
   {rr,row,hit}=16'(n);#1;
   if({e0,d0,c0}!=={e1,d1,c1} || {e0,d0,c0}!=={e2,d2,c2})bad=bad+1;
   if(e0!==eb)negative=negative+1;
  end
  if(bad!=0 || negative==0)$fatal(1,"QCORE_ROWEN FAIL bad=%0d negative=%0d",bad,negative);
  $display("QCORE_ROWEN PASS vectors=65536 variants=2 outputs_per_variant=21 negative_row_bit_caught=%0d",negative);
  $finish;
 end
endmodule
