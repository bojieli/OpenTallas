`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;reg rst=0;reg[7:0]gl=0;reg[378:0]ib=0,cmd[0:3];wire[7:0]lr;wire[223:0]rp;
qfd_dv_s5_xhead3 h(.ck(ck),.rst_n(rst),.cid(6'd0),.fault_i(1'b0),.a_d(1567'd0),.lr_v(lr),.lr_p(rp),.lq(512'd0),.lq_v(8'd0),.lq_bad(8'd0));
integer cy,op=1,n=0;
initial begin
 force h.gl4=gl;force h.ib_q=ib;
 $readmemh("commands.hex",cmd);if($value$plusargs("op=%d",op))begin end
 repeat(16)@(negedge ck);rst=1;
 for(cy=0;cy<500;cy++)begin
 @(negedge ck);gl=cy==31?8'hff:0;ib=cmd[op];
 @(posedge ck);if(h.RD)begin n++;$display("HREAD edge%0d PH%0d IK%h RSEL%h",cy,h.PH,h.IKc[0][0],h.RSEL);end
 end
 $display("HEAD_CONTROL_DONE op%0d reads%0d",op,n);$finish;
end
endmodule
