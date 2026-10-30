`timescale 1ps/1ps
module tb;
parameter BAD=0;reg clk=0,rst=0,v=0,done=0,cf=0;reg[307:0]cmd=0;reg[31:0]cyc=0;
wire cv,ctx,busy,fault;wire[307:0]co,cx;integer admits=0;reg[31:0]wanted=0;
ot_hbm_static_load_dated_cmd_hold d(clk,rst,v,cmd,cyc,done,cf,cv,co,ctx,cx,busy,fault);
always begin #416;clk=1;#417;clk=0;end
always @(posedge clk)begin
if(!rst)cyc<=0;else cyc<=cyc+1;
if(rst&&cv)begin if(cyc!=wanted||co!==cmd)$fatal(1,"dated/payload mismatch");admits=admits+1;end
end
task tick;begin @(negedge clk);end endtask
task command(input integer delta);begin
 tick;cmd=0;cmd[158:157]=1;cmd[269:250]=1;cmd[290:270]=8;cmd[31:0]=cyc+delta;cmd[63:32]=cyc+delta+30;
 cmd[307:292]=16'h4321;cmd[291]=1;wanted=cmd[31:0]-2;v=1;
 tick;v=0;
end endtask
initial begin repeat(5)tick;rst=1;
command(2);repeat(4)tick;done=1;tick;done=0;repeat(2)tick;
command(12);
if(BAD==1)begin v=1;tick;v=0;end
if(BAD==2)begin force cyc=32'd1000;tick;release cyc;end
if(BAD==3)begin done=1;tick;done=0;end
repeat(15)tick;done=1;tick;done=0;repeat(2)tick;
if(BAD==0)begin if(fault||busy||admits!=2)$fatal(1,"baseline fail admits=%d",admits);$display("PASS DATED_CMD_HOLD original+2bypass/futureissue-minus2/full308/realcompletioncontext");end
else begin if(!fault)$fatal(1,"control escaped");$display("PASS CONTROL_CAUGHT bad=%0d",BAD);end
$finish;end
endmodule
