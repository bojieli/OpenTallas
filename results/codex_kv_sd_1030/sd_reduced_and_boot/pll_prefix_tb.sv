`timescale 1ps/1ps
module tb;
reg clk=0,refclk=0,por=0;always begin #416 clk=1;#417 clk=0;end
always #5000 refclk=~refclk;
wire locked,syncpor,q;integer ticks0;
qkd_pll_analog_model #(.CORE_HALF(0.4165)) pll(.refclk(refclk),.por_n(por),.locked(locked));
ot_dp_rsync_s2 rs(.clk(clk),.async_rst_n(por),.sync_rst_n(syncpor));
ot_dp_lockq #(.STABLE(16)) lq(.clk(clk),.d(syncpor),.locked(locked),.q(q));
initial begin #3045001;por=1;ticks0=$time;$display("PREFIX_POR ticks=%0t",$time);#150000;$fatal(1,"PLL prefix failed");end
always @(posedge locked)$display("PREFIX_LOCK ticks=%0t afterpor=%0d",$time,$time-ticks0);
always @(posedge q)begin $display("PREFIX_Q ticks=%0t afterpor=%0d ceil833=%0d",$time,$time-ticks0,($time-ticks0+832)/833);if(($time-ticks0+832)/833!=116)$fatal(1,"prefix drift");$finish;end
endmodule
