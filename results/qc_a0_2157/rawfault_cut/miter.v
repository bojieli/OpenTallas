module miter(input [49:0] q,output ok);wire[8:0]a,b;reference_cone r(q,a);reconstructed_cone g(q,b);assign ok=a==b;endmodule
module mutant_miter(input [49:0]q,output ok);wire[8:0]a,b;reference_cone r(q,a);mutant_cone g(q,b);assign ok=a==b;endmodule
