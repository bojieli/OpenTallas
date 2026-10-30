`timescale 1ps/1ps
module tb;
parameter BAD=0;reg clk=0,rst=0,v=0,busy=0,lfault=0;reg[88:0]p=0;
wire rel,rb,beg,bb,fault;wire[15:0]re,be;wire[14:0]row;wire[3:0]col;
integer cyc=0,fillcyc=-100,nrel=0,nbeg=0;reg[15:0]last_epoch=0;
ot_hbm_static_load_window_calendar d(clk,rst,v,p,busy,lfault,rel,rb,re,beg,bb,be,row,col,fault);
always begin #416;clk=1;#417;clk=0;end
always @(posedge clk)begin
cyc=cyc+1;
if(rst&&v&&p[52]&&!busy&&!fault)fillcyc=cyc;
if(rst&&rel)begin nrel=nrel+1;if(re!==last_epoch)$fatal(1,"old epoch release mismatch");end
if(rst&&beg)begin
if(cyc-fillcyc!=2||row!=15'd77||col!=4'd9)$fatal(1,"begin date/metadata");
nbeg=nbeg+1;last_epoch=be;
end
end
task tick;begin @(negedge clk);end endtask
task raw(input[15:0]e);begin tick;p=0;p[0]=1;p[17:2]=e;v=1;tick;v=0;p=0;end endtask
task fill(input[15:0]e);begin tick;p=0;p[52]=1;p[69:54]=e;p[84:70]=77;p[88:85]=9;v=1;tick;v=0;p=0;end endtask
initial begin
repeat(5)tick;rst=1;tick;
raw(16'd21);fill(16'd21);repeat(4)tick;
raw(16'd22);
if(BAD==1)busy=1;
fill(BAD==2?16'd99:16'd22);repeat(4)tick;
if(BAD==0)begin if(fault||nrel!=1||nbeg!=2)$fatal(1,"baseline failure");$display("PASS WINDOW_CALENDAR 2epochs/release_old/all8_endpoint/meaningful_fillmeta/exact2edge_begin");end
else begin if(!fault)$fatal(1,"control escaped");$display("PASS CONTROL_CAUGHT bad=%0d",BAD);end
$finish;
end
endmodule
