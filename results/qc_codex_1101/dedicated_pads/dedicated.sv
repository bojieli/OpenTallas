module qfd_sigbump #(parameter integer RV = 0) (
    output wire o
);
    assign o = RV[0];
endmodule

// Driven digital package control receiver. Only explicitly declared line-side bump instances use this master;
// the binder exports pad_i as a real die input. Zero added cycles; no analog receiver/timing claim.
module qfd_sigbump_input (
    output wire o,
    input wire pad_i
);
    assign o = pad_i;
endmodule

module top(input wire i,output wire mismatch); wire a,b,c; qfd_sigbump #(.RV(0)) p0(.o(a)); qfd_sigbump #(.RV(1)) p1(.o(b));
`ifdef MUT
qfd_sigbump_input pe(.o(c),.pad_i(1'b0));
`else
qfd_sigbump_input pe(.o(c),.pad_i(i));
`endif
assign mismatch=a|~b|(c^i); endmodule
