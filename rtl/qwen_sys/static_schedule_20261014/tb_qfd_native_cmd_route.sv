`timescale 1ns/1ps
module tb_qfd_native_cmd_route;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0;reg[379:0]cmd=0;
 reg[94:0]rr=95'h1234567,nr=95'h7654321;
 wire[379:0]rc,nc;wire[94:0]ret;
 ot_qfd_native_cmd_route d(.clk(clk),.rst_n(rst_n),.cmd(cmd),.rom_ret(rr),.native_ret(nr),.rom_cmd(rc),.native_cmd(nc),.ret(ret));
 task tick;begin @(posedge clk);#0.1;end endtask
 reg[379:0] actual;
 initial begin
 actual=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 repeat(3)tick();rst_n=1;@(negedge clk);cmd=actual;#0.1;
 if(nc!==actual||rc!=={actual[379:1],1'b0})$fatal(1,"native descriptor dropped or sent to ROM tree");
 tick();if(ret!==nr)$fatal(1,"actual native ret95 not returned");
 @(negedge clk);cmd=0;nr[1:0]=0;tick();
 if(ret[1:0]!==0)$fatal(1,"native completion fabricated before endpoint");
 @(negedge clk);nr[1:0]=3;tick();if(ret[1:0]!==3)$fatal(1,"native completion lost");
 @(negedge clk);cmd=actual;cmd[55]=0;#0.1;
 if(!rc[0]||nc[0]||rc[379:1]!==cmd[379:1])$fatal(1,"ROM dispatch mismatch");
 tick();if(ret!==rr)$fatal(1,"actual ROM ret95 not returned");
 @(negedge clk);cmd=0;nr[94]=1;tick();nr[94]=0;tick();
 if(!ret[94]||ret[93:0]!==rr[93:0])$fatal(1,"native fault lost across later ROM status");
 $display("PASS actual native380 preserved; ROM bypass; real ret95 completion and sticky fault");$finish;
 end
endmodule
