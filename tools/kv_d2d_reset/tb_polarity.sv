`timescale 1ns/1ps
module tb;
reg ck=0; always #5 ck=~ck;
reg d=1'bx; wire qn,q; reg copy_q;
DFFHQNx1_ASAP7_75t_R ff(qn,d,ck);
INVx1_ASAP7_75t_R inv(.Y(q),.A(qn));
always @(posedge ck) copy_q<=d;
integer i; integer mut=0; integer errors=0;
initial begin
 if($value$plusargs("MUT=%d",mut))begin end
 for(i=0;i<100;i=i+1) begin
 @(negedge ck); case(i%3) 0:d=0;1:d=1;2:d=1'bx;endcase
 @(posedge ck); #1;
 if(q !== (mut==1 ? ~copy_q : copy_q))errors=errors+1;
 end
 if(errors) $fatal(1,"POLARITY_MISMATCH %0d",errors);
 $display("POLARITY_PASS 100 edges incl X, native UDP QN plus native INV");$finish;end
endmodule
