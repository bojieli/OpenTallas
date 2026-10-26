`timescale 1ns/1ps
`default_nettype none
// Opt-in successor of ot_s81_land for dedicated pin capture.
// The input drives ONE unconditional forwarded-clock FF. Ring writes use its
// previous word and previous write epoch; read K is extended and increased by1.
// Relative to ot_s81_land, o/fault move by exactly ONE ck edge in the same
// qualified static landing window. K=7 ->8 is represented without overflow.
// The parent must price that cycle and requalify actual clock/face/timing gates.
module ot_s81_land_pin_capture #(
    parameter integer W=276,
    parameter integer D=4,
    parameter integer AW=(D<=2)?1:$clog2(D),
    parameter integer KW=AW+1
) (
    input wire [KW-1:0] k,
    input wire ck_f,
    input wire [W-1:0] i,
    input wire ck,
    input wire rs,
    output reg [W-1:0] o,
    output reg fault
);
    localparam integer RW=KW+1;
    wire [RW-1:0] k_read={1'b0,k}+{{(RW-1){1'b0}},1'b1};
    (* keep=1 *) reg [W-1:0] pin_q;
    reg [AW:0] pin_epoch;
    reg pin_valid;
    reg [AW:0] wc;
    reg [W-1:0] bank[0:D-1];
    reg [AW:0] epo[0:D-1];
    reg [RW-1:0] rc;
    reg warm;
    always @(posedge ck_f) begin
        pin_q<=i;
        pin_epoch<=wc;
    end
    always @(posedge ck_f or negedge rs)
        if(!rs) begin wc<={(AW+1){1'b0}}; pin_valid<=1'b0; end
        else begin wc<=wc+1'b1; pin_valid<=1'b1; end
    genvar s;
    generate for(s=0;s<D;s=s+1) begin:g_slot
`ifdef OT_S81_LAND_CAPTURE_MUT_POINTER
        wire selected=(wc[AW-1:0]==s);
`else
        wire selected=(pin_epoch[AW-1:0]==s);
`endif
        always @(posedge ck_f)
            if(pin_valid && selected) begin bank[s]<=pin_q; epo[s]<=pin_epoch; end
    end endgenerate
    wire [RW-1:0] expw=rc-k_read;
    wire [AW:0] exp_=expw[AW:0];
    always @(posedge ck or negedge rs)
        if(!rs) begin rc<={RW{1'b0}}; warm<=1'b0; fault<=1'b0; end
        else begin
            rc<=rc+1'b1;
            if(rc==k_read-1'b1) warm<=1'b1;
            if(warm && epo[exp_[AW-1:0]]!=exp_) fault<=1'b1;
        end
    always @(posedge ck) o<=warm?bank[exp_[AW-1:0]]:{W{1'b0}};
`ifndef SYNTHESIS
    initial begin
        if(D<2 || (D&(D-1))!=0) $fatal(1,"D must be power of two >=2");
        if(KW<AW+1) $fatal(1,"KW must be >=AW+1");
    end
    always @(posedge ck) if(warm && k==0) $fatal(1,"K must be >=1");
`endif
endmodule
`default_nettype wire
