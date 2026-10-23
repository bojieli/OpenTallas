(* keep_hierarchy="yes" *) module qfd_lctx_full32_and #(parameter integer ID=0)(A,B,Y);
input wire A;
input wire B;
output wire Y;
assign Y=A & B;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_dff_pn0 #(parameter integer ID=0)(C,D,Q,R);
input wire C;
input wire D;
output reg Q;
input wire R;
always @(posedge C or negedge R) if(!R) Q<=1'b0;else Q<=D;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_dff_pn1 #(parameter integer ID=0)(C,D,Q,R);
input wire C;
input wire D;
output reg Q;
input wire R;
always @(posedge C or negedge R) if(!R) Q<=1'b1;else Q<=D;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_dff_p #(parameter integer ID=0)(C,D,Q);
input wire C;
input wire D;
output reg Q;
always @(posedge C) Q<=D;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_mux #(parameter integer ID=0)(A,B,S,Y);
input wire A;
input wire B;
input wire S;
output wire Y;
assign Y=S ? B : A;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_not #(parameter integer ID=0)(A,Y);
input wire A;
output wire Y;
assign Y=~A;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_or #(parameter integer ID=0)(A,B,Y);
input wire A;
input wire B;
output wire Y;
assign Y=A | B;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_sdff_pn0 #(parameter integer ID=0)(C,D,Q,R);
input wire C;
input wire D;
output reg Q;
input wire R;
always @(posedge C) if(!R) Q<=1'b0;else Q<=D;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_sdff_pp0 #(parameter integer ID=0)(C,D,Q,R);
input wire C;
input wire D;
output reg Q;
input wire R;
always @(posedge C) if(R) Q<=1'b0;else Q<=D;
endmodule
(* keep_hierarchy="yes" *) module qfd_lctx_full32_xor #(parameter integer ID=0)(A,B,Y);
input wire A;
input wire B;
output wire Y;
assign Y=A ^ B;
endmodule
