`timescale 1ns/1ps
module tb_invalid;
reg ck=0;always #5 ck=~ck;reg rst_n=0,start=0;wire fault;wire[550:0]rb;integer c,ends=0;
qfd_res_train_static #(.BAND(2))dut(.ck(ck),.ck_bank({24{ck}}),.rst_n(rst_n),.train_start(start),.train_count(4'd0),.capture_stride(32'd0),.payload_write(1'b0),.rq(4425'd0),.rb(rb),.fault(fault));
initial begin repeat(4)@(negedge ck);rst_n=1;
for(c=0;c<1545;c=c+1)begin start=(c==0);@(posedge ck);#1;
if(rb[550])begin if(rb!={3'b111,548'd0})$fatal(1,"invalid config corrupt marker");ends=ends+1;end
if(c==1539&&dut.active)$fatal(1,"invalid config extended timeline");
@(negedge ck);end
if(!fault||ends!=64)$fatal(1,"invalid cfg fault=%0b markers=%0d",fault,ends);
$display("PASS invalid config fixedmaxwindow markers=%0d",ends);$finish;end
endmodule
