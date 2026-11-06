module tb;
reg ck=0; reg [5:0] d=0; reg [21:0] gold; reg [5:0] keep; wire [21:0] gate; integer n=0,bad=0;
always #5 ck=~ck;
always @(posedge ck)begin gold <= { {5{d[0]}},{4{d[1]}},{4{d[2]}},{4{d[3]}},{3{d[4]}},{2{d[5]}} };keep<=d;end
`ifdef MUTANT
assign gate={{5{~keep[0]}},{4{keep[1]}},{4{keep[2]}},{4{keep[3]}},{3{keep[4]}},{2{keep[5]}}};
`else
assign gate={{5{keep[0]}},{4{keep[1]}},{4{keep[2]}},{4{keep[3]}},{3{keep[4]}},{2{keep[5]}}};
`endif
always @(negedge ck)begin n=n+1; if(n>2 && gold!==gate)bad=bad+1; d=$random; if(n==500)begin $display("CTL_INPUT_SHARE bad=%0d",bad);if(bad)$fatal(1,"mismatch");$finish;end end
endmodule
