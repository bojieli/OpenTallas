`timescale 1ns/1ps
module dsfd_sstn_e0e1c0c1sinf (
    output wire [14:0] cc,
    input wire [14:0] cci,
    input wire [0:0] ck,
    input wire [0:0] nf,
    input wire [0:0] rs,
    input wire [1:0] si,
    output wire [1:0] so,
    output wire [282:0] xa,
    input wire [282:0] xai,
    output wire [265:0] xb,
    input wire [265:0] xbi,
    input wire [1:0] c0,
    input wire [1:0] e0,
    input wire [1:0] c1,
    input wire [1:0] e1
);
    reg [282:0] ra; reg [265:0] rb; reg [14:0] rc; reg [1:0] rst;
    always @(posedge ck[0]) begin ra <= xai; rb <= xbi; end
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rc <= 15'd0; else rc <= cci;
    reg xv; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) xv <= 1'b0; else xv <= xai[282];
    assign xa = {xv, ra[281:0]};                 // xs_v: column-reset flop (no gate at the pin)
    assign xb = rb;
    assign cc = rc;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rst <= 2'b00; else rst <= e0 | e1 | c0 | c1 | si | {nf[0], 1'b0};
    assign so = rst;
endmodule
