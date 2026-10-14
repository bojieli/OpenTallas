`timescale 1ns/1ps
module tb_qfd_cbuf_ready_join8;
 reg ck=0,rst_n=0;always #0.4166665 ck=~ck;
 reg[7:0]rdy=0,fault=0;reg[47:0]stage=0;reg[143:0]pos=0;
 wire ready,flt;wire[5:0]st;wire[17:0]tp;
 qfd_cbuf_ready_join8 dut(.ck(ck),.rst_n(rst_n),.st_rdy(rdy),.st_rdy_stage(stage),.st_rdy_tpos(pos),.fault(fault),.cb_st_rdy(ready),.cb_st_rdy_stage(st),.cb_st_rdy_tpos(tp),.cb_fault(flt));
 integer i,g,checks=0,bad=0;reg er=0,ef=0;reg[5:0]es;reg[17:0]ep;reg nr,nf;reg[5:0]ns;reg[17:0]np;
 always @(posedge ck)begin
  nr=(&rdy)&&!(|fault);nf=|fault;ns=stage[5:0];np=pos[17:0];
  for(integer k=1;k<8;k=k+1)if(stage[k*6+:6]!=ns||pos[k*18+:18]!=np)nr=0;
  #0.005;
  if(rst_n)begin checks=checks+1;if(ready!==er||flt!==ef||(ready&&(st!==es||tp!==ep)))begin bad=bad+1;if(bad<=4)$display("JOIN_MISMATCH ready=%b/%b fault=%b/%b stage=%d/%d pos=%d/%d",ready,er,flt,ef,st,es,tp,ep);end er=nr;ef=nf;es=ns;ep=np;end
  else begin er=0;ef=0;if(ready!==0||flt!==0)bad=bad+1;end
 end
 initial begin
  repeat(3)@(negedge ck);rst_n=1;
  for(i=0;i<560;i=i+1)begin
   @(negedge ck);rdy=8'hff;fault=0;
   for(g=0;g<8;g=g+1)begin stage[g*6+:6]=i%38;pos[g*18+:18]=100+i;end
   case(i%7)
    1:rdy[i%8]=0;
    2:pos[(i%8)*18+:18]=101+i;
    3:stage[(i%8)*6+:6]=(i+1)%38;
    4:fault[i%8]=1;
    5:begin pos[(i%8)*18+:18]=101+i;fault[(i+1)%8]=1;end
    default:;
   endcase
   if(i==277)begin rst_n=0;repeat(3)@(negedge ck);rst_n=1;end
  end
  repeat(4)@(negedge ck);
  if(bad==0)$display("PASS ready_join8 checks=%0d reset_epochs=2 mixed_position/stage/fault/valid=560",checks);else $display("FAIL ready_join8 checks=%0d bad=%0d",checks,bad);
  $finish;
 end
endmodule
