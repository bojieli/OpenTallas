`timescale 1ns/1ps
module tb_result_v_cone;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,launch=0;wire rv_native,rv_rtl;
native_result_v_cone n(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(768'd0),.bases(768'd0),.scales(96'd0),.result_v(rv_native));
ot_hbm_hc_tail_child_static r(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(768'd0),.bases(768'd0),.scales(96'd0),.result_v(rv_rtl),.result(),.fault());
integer cyc=0,errors=0,nv=0,rv=0,pulse=0,init_errors=0;
always @(posedge clk)begin
 #0.001; // Observe settled output pins on EVERY edge, including all reset edges.
 $display("RV_CONE_TRACE time=%0t clk=%b cyc=%0d reset=%b launch=%b native=%b rtl=%b",$time,clk,cyc,rst_n,launch,rv_native,rv_rtl);
 if(rv_native!==rv_rtl)begin errors=errors+1;$display("RV_CONE_MISMATCH cyc=%0d",cyc);end
 if(rv_native)nv=nv+1;if(rv_rtl)rv=rv+1;cyc=cyc+1;
end
initial begin
 #0.001; $display("PRE_CLOCK time=%0t clk=%b reset=%b native=%b rtl=%b",$time,clk,rst_n,rv_native,rv_rtl);
 if(!rst_n && (rv_native!==0 || rv_rtl!==0))init_errors=init_errors+1;
 #0.100; $display("PRE_CLOCK time=%0t clk=%b reset=%b native=%b rtl=%b",$time,clk,rst_n,rv_native,rv_rtl);
 if(!rst_n && (rv_native!==0 || rv_rtl!==0))init_errors=init_errors+1;
 #0.800; $display("PRE_CLOCK time=%0t clk=%b reset=%b native=%b rtl=%b",$time,clk,rst_n,rv_native,rv_rtl);
 if(!rst_n && (rv_native!==0 || rv_rtl!==0))init_errors=init_errors+1;
end
initial begin
if(!$value$plusargs("PULSE=%d",pulse))pulse=0;
if(pulse!=0)begin rst_n=1;#0.1;rst_n=0;end
repeat(5)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
launch=1;@(negedge clk);launch=0;repeat(530)@(negedge clk);
if(errors==0 && init_errors==0)$display("RV_CONE PASS errors=0 native_count=%0d rtl_count=%0d",nv,rv);
else $display("RV_CONE FAIL errors=%0d init_errors=%0d native_count=%0d rtl_count=%0d",errors,init_errors,nv,rv);$finish;
end
endmodule
