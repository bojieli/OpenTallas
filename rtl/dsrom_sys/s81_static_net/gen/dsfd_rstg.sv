`timescale 1ns/1ps
module dsfd_rstg (
    input wire [0:0] ck,
    input wire [65:0] i,
    output wire [65:0] o,
    input wire [0:0] rs
);
    reg [65:1] r; always @(posedge ck[0]) r <= i[65:1];
    reg v; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) v <= 1'b0; else v <= i[0];
    assign o = {r, v};                            // return valid: column-reset flop (no gate at the pin)
endmodule
