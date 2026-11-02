module tb;
reg [15:0] base; reg [3:0] wc;
wire [18:0] oldv={1'b1,base+16'(wc),2'b10};
wire [18:0] newv={1'b1,base+{12'd0,wc},2'b10};
wire [18:0] mutant={1'b1,base+{{12{wc[3]}},wc},2'b10};
integer a,b,n,mut;
initial begin
n=0;mut=0;
for(a=0;a<65536;a=a+1) for(b=0;b<16;b=b+1) begin
base=a;wc=b;#1;
if(oldv!==newv) $fatal(1,"mismatch");
if(oldv!==mutant) mut=mut+1;n=n+1;
end
base=16'hffff;wc=4'bx101;#1;if(oldv!==newv)$fatal(1,"X mismatch");
if(mut==0)$fatal(1,"mutant escaped");
$display("PASS %0d exact combinations; mutant caught %0d; X preserved; zero cycles",n,mut);$finish;
end
endmodule
