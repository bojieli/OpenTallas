module ot_meso_dsel #(parameter int W = 64, parameter int DEPTH = 4, parameter bit REG = 0, parameter bit SPLIT = 0,
                      // DSREP-1 (DIE-HEAD-58 TURNB): SREP kept copies of the one-hot select di, copy s drives bits
                      // [s*W/SREP, (s+1)*W/SREP); same align/on/place, so every copy equals di.  1 = identical logic.
                      parameter int SREP = 1) (
    input  logic                    clk,
    input  logic                    align,
    input  logic                    on,
    input  logic [$clog2(DEPTH)-1:0] place,
    input  logic [DEPTH*W-1:0]      sd,
    output logic [W-1:0]            y
);
    logic [DEPTH-1:0] di;
    always_ff @(posedge clk) begin
        if (align) di <= DEPTH'(1) << place;
        else if (on) di <= {di[DEPTH-2:0], di[DEPTH-1]};
    end
    logic [W-1:0] y_c;
    if (SREP > 1) begin : g_srep
        localparam int SW = W / SREP;
        if (SW * SREP != W) begin : g_bad $error("ot_meso_dsel: W %% SREP != 0"); end
        wire [DEPTH-1:0] dr [SREP];
        for (genvar r = 0; r < SREP; r++) begin : sr
            (* keep = "true" *) ot_meso_dsel_sel #(.DEPTH(DEPTH)) u_sel (.clk(clk), .align(align), .on(on), .place(place),
                                                                   .di(dr[r]));
        end
        always_comb begin
            y_c = '0;
            for (int i = 0; i < DEPTH; i++)
                for (int b = 0; b < W; b++)
                    y_c[b] = y_c[b] | (sd[i*W + b] & dr[b / SW][i]);
        end
    end else begin : g_s1
        always_comb begin
            y_c = '0;
            for (int i = 0; i < DEPTH; i++) y_c = y_c | (sd[i*W +: W] & {W{di[i]}});
        end
    end
    if (REG && SPLIT) begin : g_split
        // SPLIT: the crossing arc is slot -> one AO22 level -> a half-select flop (mcast_r6 Q1: m -> AO22 -> AO221 ->
        // y_q -63.9 ps against the 356.667 ps crossing bound); the two halves are ORed in rclk after the flops, the
        // same edge the single readout flop would present (one-hot di: at most one half is non-zero)
        logic [W-1:0] ya_c, yb_c, ya_q, yb_q;
        always_comb begin
            ya_c = '0; yb_c = '0;
            for (int i = 0; i < DEPTH / 2; i++) ya_c = ya_c | (sd[i*W +: W] & {W{di[i]}});
            for (int i = DEPTH / 2; i < DEPTH; i++) yb_c = yb_c | (sd[i*W +: W] & {W{di[i]}});
        end
        always_ff @(posedge clk) begin ya_q <= ya_c; yb_q <= yb_c; end
`ifdef OT_MESO_MUTANT_RSPLIT
        assign y = ya_q;                                    // MUTANT: upper half-select dropped
`else
        assign y = ya_q | yb_q;
`endif
    end else if (REG) begin : g_reg
        // the crossing's capture flop sits next to the select (RDREG): the arc is slot -> AND-OR -> this flop
        logic [W-1:0] y_q;
        always_ff @(posedge clk) y_q <= y_c;
        assign y = y_q;
    end else begin : g_comb
        assign y = y_c;
    end
endmodule
module ot_meso_dsel_sel #(parameter int DEPTH = 4) (
    input  logic                     clk,
    input  logic                     align,
    input  logic                     on,
    input  logic [$clog2(DEPTH)-1:0] place,
    (* keep *) output logic [DEPTH-1:0] di
);
    always_ff @(posedge clk) begin
        if (align) di <= DEPTH'(1) << place;
        else if (on) di <= {di[DEPTH-2:0], di[DEPTH-1]};
    end
endmodule
module miter(input logic clk,align,on,input logic[1:0]place,input logic[255:0]sd,output logic mismatch);
wire[63:0]gold,gate;
ot_meso_dsel #(.W(64),.DEPTH(4),.REG(1),.SREP(1)) u_gold(.*,.y(gold));
ot_meso_dsel #(.W(64),.DEPTH(4),.REG(1),.SREP(8)) u_gate(.*,.y(gate));
assign mismatch = gold != {gate[63:2],gate[0],gate[1]};
endmodule
