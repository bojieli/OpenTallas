module qfd_bmath_dff_p #(parameter integer ID=0)(C,D,Q);
input wire C;
input wire D;
output reg Q;
always @(posedge C) Q<=D;
endmodule
