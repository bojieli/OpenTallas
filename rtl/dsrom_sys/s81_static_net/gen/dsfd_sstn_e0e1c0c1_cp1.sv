`timescale 1ns/1ps
module dsfd_sstn_e0e1c0c1_cp1 (
    output wire [14:0] cc,
    input wire [14:0] cci,
    input wire [0:0] ck,
    input wire [0:0] rs,
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
    reg [14:0] rcp [0:0];
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) begin : g_cp_rst
        integer j_; for (j_ = 0; j_ < 1; j_ = j_ + 1) rcp[j_] <= 15'd0; end
    else begin : g_cp integer j_; rcp[0] <= rc; for (j_ = 1; j_ < 1; j_ = j_ + 1) rcp[j_] <= rcp[j_ - 1]; end
    assign xb = rb;
    assign cc = rcp[0];
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rst <= 2'b00; else rst <= e0 | e1 | c0 | c1;
    assign so = rst;
endmodule
