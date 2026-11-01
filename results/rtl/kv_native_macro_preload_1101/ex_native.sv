module qkd_astk_ex_s (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [65:0]   xa,
    output reg  [33:0]   xe
);
    localparam integer ADD_LAT = 7, SFU_LA = 7, SFU_LM = 7;
    localparam integer XD = 7 * SFU_LM + 8 * SFU_LA + 4;
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep *) reg [65:0] xq;
    always @(posedge ck or negedge rn_q) if (!rn_q) xq[0] <= 1'b0; else xq[0] <= xa[0];
    always @(posedge ck) xq[65:1] <= xa[65:1];
    wire         pv1 = xq[0] && xq[1];
    wire         vD, posD;
    ot_hdc_delay #(.W(2), .D(ADD_LAT + XD), .RESET(1)) u_tag (.clk(ck), .rst_n(rn_q), .d(xq[1:0]), .q({posD, vD}));
    wire [31:0]  mm = xq[65:34];
    wire [31:0]  x, e;
    wire [1:0]   err;
    wire         vo, xvo, xf;
    ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_sub (.clk(ck), .rst_n(rn_q), .valid_in(pv1),
        .a(pv1 ? xq[33:2] : 32'd0), .b(pv1 ? {~mm[31], mm[30:0]} : 32'd0), .y(x), .err(err), .valid_out(vo));
    ot_qwen_nearhbm_exp_p #(.LA(SFU_LA), .LM(SFU_LM)) u_exp (.clk(ck), .rst_n(rn_q), .v(vo), .x(x), .y(e), .vo(xvo), .fault(xf));
    reg f;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin f <= 1'b0; xe[1:0] <= 2'b00; end
        else begin
            if ((vo && err != 2'd0) || (vD && posD && xf)) f <= 1'b1;
            xe[0] <= vD; xe[1] <= f;
        end
    always @(posedge ck) xe[33:2] <= e ^ ((`KVD_STMUT == 2) ? 32'd1 : 32'd0);
endmodule
