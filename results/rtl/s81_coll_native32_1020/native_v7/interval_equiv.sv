// Full 31-input combinational relation, no protocol/range assumptions.
module interval_equiv(input wire [9:0] a,b,limit,input wire inc,output wire bad);
 wire gt;
 wire [9:0] next_a=inc?(a+1'b1):a;
 wire [9:0] next_difference=next_a-b;
 ot_s81ph_skip_interval #(.W(10)) u(.a(a),.b(b),.limit(limit),.inc(inc),.gt(gt));
 assign bad=(gt != (limit>next_difference));
endmodule
