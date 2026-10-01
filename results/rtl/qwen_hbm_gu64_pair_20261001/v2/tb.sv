
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,v=0,first=0,last=0;
reg [1023:0] w,x;reg [35:0] rows;reg [5:0] slots;
wire [1:0] ov;wire [63:0] sums;wire [35:0] rr;wire [5:0] rs;wire fault;
reg [1023:0] wm[0:511],xm[0:511]; integer i,n=0,cycle=0;
ot_gpu_qwen_gu64_pair #(.ENABLE_GU64(1)) d(.clk(clk),.rst_n(rst_n),
.v(v),.first(first),.last(last),.weights_i8(w),.x_bf16(x),
.global_rows(rows),.slots(slots),.ov(ov),.sums(sums),
.result_rows(rr),.result_slots(rs),.fault(fault));
always @(posedge clk) begin
#1;cycle=cycle+1;
if(rst_n && fault) $fatal(1,"arithmetic/tag fault");
if(ov[0]) begin $display("RESULT %d %d %h %d",rr[17:0],rs[2:0],sums[31:0],cycle);n=n+1;end
if(ov[1]) begin $display("RESULT %d %d %h %d",rr[35:18],rs[5:3],sums[63:32],cycle);n=n+1;end
end
initial begin
$readmemh("weights.hex",wm);$readmemh("x.hex",xm);
repeat(4) @(negedge clk);rst_n=1;
for(i=0;i<512;i=i+1) begin
v=1;first=i<8;last=i>=504;w=wm[i];x=xm[i];
rows[17:0]=250+2*(i%8);rows[35:18]=251+2*(i%8);
slots[2:0]=i%8;slots[5:3]=i%8;@(negedge clk);
end
v=0;first=0;last=0;repeat(160) @(negedge clk);
if(n!=16) $fatal(1,"missing rows %d",n);
if(fault) $fatal(1,"late arithmetic/tag fault");
$display("COMPLETE GU64 rows=16 trailing=160 fault=0");
$finish;
end
initial begin #20000;$fatal(1,"TIMEOUT");end
endmodule
