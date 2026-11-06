module helper_tb;reg clk=0;always #5 clk=~clk;reg[31:0]a;reg[15:0]b;wire[31:0]gold,d;reg[31:0]candidate;off32_old o(clk,a,b,gold);ot_bodyctl_off32_split_d n(clk,a,b,d);always@(posedge clk)candidate<=d;
integer i,bad=0;reg[63:0]rng=64'h123456789abcdef1;
initial begin a=0;b=0;repeat(5)@(negedge clk);for(i=0;i<200040;i=i+1)begin
if(i<8)begin a=32'hffffffff>>i;b=16'hffff;end
else if(i<24)begin a=32'hffffffff;b=16'h1<<(i-8);end
else if(i<40)begin a=32'h1<<(i-24);b=16'hffff;end
else begin rng=rng^(rng<<13);rng=rng^(rng>>7);rng=rng^(rng<<17);a=rng[31:0];b=rng[63:48];end
@(negedge clk);if(gold!==candidate)bad=bad+1;end
$display("HELPER_EXTERNAL_EDGE3 samples=%0d mismatch=%0d",i,bad);if(bad)$fatal;$finish;end endmodule
