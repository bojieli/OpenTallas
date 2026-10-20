`timescale 1ns/1ps
module tb_reset;
reg ck=0,rn=0;always #1 ck=~ck;
reg r1o=0,r1n=0;reg [5:0] qo=0,qn=0,qbad=0;
always @(posedge ck or negedge rn)if(!rn)r1o<=0;else r1o<=1;
always @(posedge ck or negedge rn)if(!rn)r1n<=0;else r1n<=1;
always @(posedge ck or negedge rn)if(!rn)qo<=0;else qo<={6{r1o}};
always @(posedge ck or negedge r1n)if(!r1n)qn<=0;else qn<=6'b111111;
always @(posedge ck or negedge rn)if(!rn)qbad<=0;else qbad<=6'b111111;
integer i,n=0,bad=0,mut=0,async_n=0;
always @(posedge ck)begin #0.001;n=n+1;if(qo!==qn)bad=bad+1;if(qo!==qbad)mut=mut+1;end
always @(negedge rn)begin #0.001;async_n=async_n+1;if(qn!==0||qo!==0)bad=bad+1;end
initial begin
 for(i=0;i<250;i=i+1)begin
  #(2.003+(i%13)*0.017);rn=1;
  #(8.011+(i%7)*0.031);rn=0;
 end
 #5;$display("SU8_RESET_STATS checks=%0d async=%0d bad=%0d bypass_mut=%0d",n,async_n,bad,mut);
 if(n>1000&&async_n>200&&bad==0&&mut>200)$display("SU8_RESET PASS");else $display("SU8_RESET FAIL");$finish;
end endmodule
