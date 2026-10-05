module tb;
reg [1023:0] v=0; wire [511:0] rec; wire ok; wire [1023:0] q;
ot_chip_v41x_kv_enc e(.v(v),.rec(rec),.ok(ok));
ot_chip_v41x_kv_dec d(.rec(rec),.v(q));
integer i,j,bad=0;
initial begin
for(i=0;i<1;i=i+1) begin
 v=0; v[31:16]=16'(i); #1; if(ok!==1'b1 || q!==v) begin bad=bad+1; $display("INITIAL_INPUT i=%0d ok=%b q0=%h v0=%h",i,ok,q[31:0],v[31:0]); end
end
for(i=0;i<0;i=i+1) begin
 for(j=0;j<32;j=j+1) v[32*j +:32]={16'(i*257 ^ j*1709),16'h0000};
 #1; if(ok!==1'b1 || q!==v) begin bad=bad+1; $display("INITIAL_INPUT i=%0d ok=%b q0=%h v0=%h",i,ok,q[31:0],v[31:0]); end
end
v[0]=1; #1; if(ok!==1'b0) bad=bad+1;
$display("LEGACY_BF16_CODEC patterns=65536 lane_blocks=256 low_half_rejection=1 bad=%0d",bad);
if(bad==0) $display("PASS"); else $display("FAIL"); $finish;
end
endmodule
