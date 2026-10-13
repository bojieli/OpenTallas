// el1011-q-kvd 2026-10-11: blackbox views of the hardened link-buffer tiles (ot_qkvd_buf_tiles.sv) for the parent route.
(* blackbox *)
module ot_qkvd_sbuf (input wire clk, input wire rst_n, input wire push, input wire [527:0] din, input wire pop,
    output wire [527:0] dout, output wire empty);
endmodule
(* blackbox *)
module ot_qkvd_fbuf8 (input wire clk, input wire rst_n, input wire push, input wire [527:0] din, input wire pop,
    output wire [527:0] dout, output wire empty);
endmodule
(* blackbox *)
module ot_qkvd_sbufp (input wire clk, input wire rst_n, input wire push, input wire [527:0] din, input wire pop,
    output wire [527:0] dout, output wire empty);
endmodule
(* blackbox *)
module ot_qkvd_fbuf8p (input wire clk, input wire rst_n, input wire push, input wire [527:0] din, input wire pop,
    output wire [527:0] dout, output wire empty);
endmodule
