module qfd_syslogic_and #(parameter integer ID=0)(A,B,Y);
input wire A;
input wire B;
output wire Y;
assign Y=A & B;
endmodule
module qfd_syslogic_or #(parameter integer ID=0)(A,B,Y);
input wire A;
input wire B;
output wire Y;
assign Y=A | B;
endmodule
module qfd_syslogic_xor #(parameter integer ID=0)(A,B,Y);
input wire A;
input wire B;
output wire Y;
assign Y=A ^ B;
endmodule
module qfd_syslogic_not #(parameter integer ID=0)(A,Y);
input wire A;
output wire Y;
assign Y=~A;
endmodule
module qfd_syslogic_mux #(parameter integer ID=0)(A,B,S,Y);
input wire A;
input wire B;
input wire S;
output wire Y;
assign Y=S ? B : A;
endmodule
