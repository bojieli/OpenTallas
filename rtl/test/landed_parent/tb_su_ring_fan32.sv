`timescale 1ns/1ps
module ring_case #(parameter W=2448, MUT=0)(output reg done=0);
reg cw=0, cr=0, rs=0; always #0.5 cw=~cw;
initial begin #0.125; forever #0.5 cr=~cr; end
reg [W-1:0] din=0; wire [2*W-1:0] ba,bb; wire[3:0]ea,eb; wire[1:0]va;wire[2*((W+23)/24)-1:0]vb;
wire[W-1:0]oa,ob;
ot_pl_land_w #(.W(W),.D(2)) a(cw,rs,din,ba,ea,va);
ot_pl_land_n32_chunk_w #(.W(W),.D(2),.CHUNK_BITS(24)) b(cw,rs,din,bb,eb,vb);
ot_pl_land_r #(.W(W),.D(2),.K(1)) ar(cr,rs,ba,ea,va,oa);
ot_pl_land_chunk_r #(.W(W),.D(2),.K(1),.CHUNK_BITS(24)) br(cr,rs,bb,eb,vb,ob);
integer t,j,checks=0;
initial begin
for(t=0;t<2200;t=t+1) begin
@(negedge cw); rs=!(t<8||(t>=700&&t<710)||(t>=1500&&t<1510));
for(j=0;j<W;j=j+1)din[j]=$random;
end
$display("RING_FAN32_EQ PASS width%0d checks%0d",W,checks);done=1;
end
always @(negedge cr)if($time>20)begin
if(oa!==(ob ^ ((MUT!=0&&$time>80)?{{(W-1){1'b0}},1'b1}:{W{1'b0}})))$fatal(1,"RING_FAN32_MISMATCH W%0d time%0t",W,$time);
checks=checks+1;
end
endmodule
module tb #(parameter MUT=0);
wire[3:0]done;
ring_case #(.W(2448),.MUT(MUT)) c0(done[0]);
ring_case #(.W(521)) c1(done[1]);
ring_case #(.W(542)) c2(done[2]);
ring_case #(.W(164)) c3(done[3]);
initial begin wait(&done); $display("SU_RING_FAN32_PROOF PASS");$finish;end
endmodule
