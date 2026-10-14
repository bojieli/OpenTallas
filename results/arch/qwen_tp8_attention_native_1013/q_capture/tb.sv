module tb;
reg clk=0; always #5 clk=~clk;
reg rn=0,qv=0;reg[5:0] qb=0;reg[511:0] qd=0;
reg[31:0] raw[0:511];reg[15:0] golden[0:511];integer b,i,bad=0;
ot_qwen_nearhbm_head_h #(.HD(128),.H(2)) dut(.clk(clk),.rst_n(rn),.c_in(4'd0),.row_in(1024'd0),.e_in(16'd0),.lt_in(12'd0),.hid(2'd2),.q_valid_in(qv),.q_beat_in(qb),.q_data_in(qd));
initial begin
$readmemh("raw.hex",raw);$readmemh("rounded.hex",golden);
repeat(5) @(negedge clk);rn=1;repeat(8) @(negedge clk);
for(b=0;b<32;b=b+1) begin qv=1;qb=b;for(i=0;i<16;i=i+1) qd[32*i+:32]=raw[16*b+i];@(negedge clk);end
qv=0;repeat(6) @(negedge clk);
for(i=0;i<128;i=i+1) if(dut.q0[16*i+:16]!==golden[256+i]) begin bad=bad+1;$display("bad %0d got=%h expected=%h",i,dut.q0[16*i+:16],golden[256+i]);end
if(bad) $fatal(1,"native capture failed");$display("PASS native FP32 Q transport / canonical BF16 rounding 128/128, tie/negative/subnormal probes");$finish;
end
endmodule
