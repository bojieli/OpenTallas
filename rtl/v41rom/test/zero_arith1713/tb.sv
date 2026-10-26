`timescale 1ns/1ps
module tb;
reg clk=0;always #1 clk=~clk;
reg rn=0,v=0;reg[31:0]a=0,b=0;
wire[31:0] y,yr;wire[1:0]e,er;wire vo,vor;
ot_v41_fadd #(.CUT(9'h1ff),.SPLIT9(1))dut(clk,rn,v,a,b,y,e,vo);
ot_v41_fadd_ref #(.CUT(9'h1ff),.SPLIT9(1))refd(clk,rn,v,a,b,yr,er,vor);
function automatic[63:0] xs(input[63:0]x);reg[63:0]t;begin t=x^(x<<13);t=t^(t>>7);xs=t^(t<<17);end endfunction
function automatic[31:0]sp(input integer i);begin case(i%32)
0:sp=0;1:sp=32'h80000000;2:sp=1;3:sp=32'h80000001;4:sp=32'h007fffff;5:sp=32'h807fffff;
6:sp=32'h00800000;7:sp=32'h80800000;8:sp=32'h3f800000;9:sp=32'hbf800000;10:sp=32'h7f7fffff;11:sp=32'hff7fffff;
12:sp=32'h7f800000;13:sp=32'hff800000;14:sp=32'h7fc12345;15:sp=32'hffc12345;16:sp=32'h7f800001;17:sp=32'hff800001;
18:sp=32'h3f000000;19:sp=32'hbf000000;20:sp=32'h3fffffff;21:sp=32'hbfffffff;22:sp=32'h00800001;23:sp=32'h80800001;
24:sp=32'h00010000;25:sp=32'h80010000;26:sp=32'h01000000;27:sp=32'h81000000;28:sp=32'h7effffff;29:sp=32'hfeffffff;30:sp=32'h00400000;default:sp=32'h80400000;endcase end endfunction
integer seed=1,cycles=100000,c,mis=0,z=0,nf=0;reg[63:0]s;reg[31:0]aa,bb;
initial begin
if($value$plusargs("seed=%d",seed))begin end
if($value$plusargs("cycles=%d",cycles))begin end
s=64'h13579abcdef02468^64'(seed);
for(c=0;c<cycles;c=c+1)begin
 @(negedge clk);s=xs(s);rn=!(c<5 || c%25000<3);v=s[9:8]!=0;
 if(c<1024)begin aa=sp(c/32);bb=sp(c%32);end
 else begin aa=s[31:0];s=xs(s);bb=s[31:0];
 case(c%8)0:aa=32'd0;1:aa=32'h80000000;2:aa={s[63],8'd0,s[22:0]};3:bb=sp(c/8);4:bb=32'd0;5:bb=32'h80000000;default:begin end endcase end
 a=aa;b=bb;if(aa[30:0]==0 || bb[30:0]==0)z=z+1;if(aa[30:23]==255 || bb[30:23]==255)nf=nf+1;
 @(posedge clk);#0.1;
 if({y,e,vo}!=={yr,er,vor})begin if(mis<8)$display("DIFF c=%0d y=%h/%h e=%h/%h v=%b/%b",c,y,yr,e,er,vo,vor);mis=mis+1;end
end
$display("ZERO_ARITH %s seed=%0d cycles=%0d mis=%0d zero=%0d nonfinite=%0d",mis==0?"PASS":"FAIL",seed,cycles,mis,z,nf);$finish;
end
endmodule
