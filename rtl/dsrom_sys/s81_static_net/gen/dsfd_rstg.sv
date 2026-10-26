`timescale 1ns/1ps
module dsfd_rstg (
    input wire [0:0] ck,
    input wire [65:0] i,
    output wire [65:0] o,
    input wire [0:0] rs
);
    // S81-KITS-RTLC 10-24 (owner: register every partition pin, in RTL): input pin register stage (l / lv) before the
    // output stage (r / v): 2 flops per bit, +1 cycle per return stage; the valid bit is a column-reset flop in both.
    reg [65:1] l; always @(posedge ck[0]) l <= i[65:1];
    reg lv; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) lv <= 1'b0; else lv <= i[0];
    reg [65:1] r; always @(posedge ck[0]) r <= l;
    reg v; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) v <= 1'b0; else v <= lv;
    assign o = {r, v};                            // return valid: column-reset flop (no gate at the pin)
endmodule
