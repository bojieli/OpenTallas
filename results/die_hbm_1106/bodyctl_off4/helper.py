from pathlib import Path
p=Path(__file__).parent
leaf=(p/'leaf.v').read_text();body=leaf.split('module split2(',1)[1].split(');',1)[1].split('endmodule',1)[0]
pairs=[(i,j) for j in range(4) for i in range(8) if i+j<8]
s='''// Exactly two internal captures. Parent retains its existing third-edge output capture.
module ot_bodyctl_off32_split_d(input clk,input[31:0]iteration,input[15:0]step,output[31:0]out_d);
reg[7:0] '''+','.join('p%d'%n for n in range(26))+''';
always@(posedge clk)begin
'''+''.join('p%d<=iteration[%d+:4]*step[%d+:4];\n'%(n,4*i,4*j) for n,(i,j) in enumerate(pairs))+'''end
wire[15:0]lo,h0,h1;wire carry;
'''+body+'''
reg[15:0]low_q,h0_q,h1_q;reg carry_q;
always@(posedge clk)begin low_q<=lo;h0_q<=h0;h1_q<=h1;carry_q<=carry;end
wire[15:0]high_sum=h0_q+h1_q+carry_q;
assign out_d={high_sum,low_q};
endmodule
'''
(p/'ot_bodyctl_off32_split_d.sv').write_text(s)
(p/'helper_tb.sv').write_text('''module helper_tb;reg clk=0;always #5 clk=~clk;reg[31:0]a;reg[15:0]b;wire[31:0]gold,d;reg[31:0]candidate;off32_old o(clk,a,b,gold);ot_bodyctl_off32_split_d n(clk,a,b,d);always@(posedge clk)candidate<=d;
integer i,bad=0;reg[63:0]rng=64'h123456789abcdef1;
initial begin a=0;b=0;repeat(5)@(negedge clk);for(i=0;i<200040;i=i+1)begin
if(i<8)begin a=32'hffffffff>>i;b=16'hffff;end
else if(i<24)begin a=32'hffffffff;b=16'h1<<(i-8);end
else if(i<40)begin a=32'h1<<(i-24);b=16'hffff;end
else begin rng=rng^(rng<<13);rng=rng^(rng>>7);rng=rng^(rng<<17);a=rng[31:0];b=rng[63:48];end
@(negedge clk);if(gold!==candidate)bad=bad+1;end
$display("HELPER_EXTERNAL_EDGE3 samples=%0d mismatch=%0d",i,bad);if(bad)$fatal;$finish;end endmodule
''')
