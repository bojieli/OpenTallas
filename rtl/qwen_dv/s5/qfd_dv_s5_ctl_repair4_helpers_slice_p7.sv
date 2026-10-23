// Exact original helper definitions not already provided by the selected p7 math file.

(* keep_hierarchy="yes" *) module qfd_bmath_and #(parameter integer ID=0)(A,B,Y);
input wire A;
input wire B;
output wire Y;
assign Y=A & B;
endmodule

(* keep_hierarchy="yes" *) module qfd_bmath_ao21 #(parameter integer ID=0)(A,B,X,Y);
input wire A;
input wire B;
input wire X;
output wire Y;
assign Y=(A & B) | X;
endmodule

(* keep_hierarchy="yes" *) module qfd_bmath_dff_pn0 #(parameter integer ID=0)(C,D,Q,R);
input wire C;
input wire D;
output reg Q;
input wire R;
always @(posedge C or negedge R) if(!R) Q<=1'b0;else Q<=D;
endmodule

(* keep_hierarchy="yes" *) module qfd_bmath_mux #(parameter integer ID=0)(A,B,S,Y);
input wire A;
input wire B;
input wire S;
output wire Y;
assign Y=S ? B : A;
endmodule

(* keep_hierarchy="yes" *) module qfd_bmath_oa21 #(parameter integer ID=0)(A,B,X,Y);
input wire A;
input wire B;
input wire X;
output wire Y;
assign Y=(A | B) & X;
endmodule

(* keep_hierarchy="yes" *) module qfd_bmath_xor #(parameter integer ID=0)(A,B,Y);
input wire A;
input wire B;
output wire Y;
assign Y=A ^ B;
endmodule
