// Unconstrained full-width combinational equivalence. No protocol-range premise.
module prefix_equiv(input wire [9:0] a,b,limit,output wire bad);
 wire gt; wire [9:0] difference=a-b;
 ot_s81ph_diff_gt_prefix #(.W(10)) u(.a(a),.b(b),.limit(limit),.gt(gt));
 assign bad=(gt != (limit > difference));
endmodule
