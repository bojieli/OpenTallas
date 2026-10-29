`default_nettype none
module old_local #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld,
    output wire x_rq, output wire [AW:0] x_wc, output wire [D-1:0] x_woh
);
    reg rq;
    reg [AW:0] wc;
    (* keep *) reg [D-1:0] write_oh;
    reg [D-1:0] valid;
    reg [W-1:0] data [0:D-1];
    reg [AW:0] epoch [0:D-1];
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin wc <= 0; write_oh <= {{(D-1){1'b0}},1'b1}; valid <= 0; end
        else begin
            wc <= wc + 1'b1;
            write_oh <= {write_oh[D-2:0], write_oh[D-1]};
            valid <= valid | write_oh;
        end
    genvar s;
    generate for (s=0;s<D;s=s+1) begin:g_slot
        always @(posedge ck) if (write_oh[s]) begin data[s] <= i; epoch[s] <= wc; end
        assign bank[s*W+:W] = data[s];
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
    assign vld = valid;
assign x_rq = rq; assign x_wc = wc; assign x_woh = write_oh;
endmodule
module new_local #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld,
    output wire x_rq, output wire [AW:0] x_wc, output wire [D-1:0] x_woh
);
    generate if (D != (1 << AW)) begin:g_invalid_depth
        OT_S81HD_LAND_LOCAL_DW_REQUIRES_POW2_DEPTH u_bad();
    end endgenerate
    reg rq;
    reg [AW:0] wc;
    (* keep *) reg [D-1:0] write_oh;
    reg [D-1:0] valid;
    reg [W-1:0] data [0:D-1];
    reg [AW:0] epoch [0:D-1];
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin wc <= 0; write_oh <= {{(D-1){1'b0}},1'b1}; valid <= 0; end
        else begin
            wc <= wc + 1'b1;
            write_oh <= {write_oh[D-2:0], write_oh[D-1]};
            valid <= valid | write_oh;
        end
    genvar s;
    generate for (s=0;s<D;s=s+1) begin:g_slot
        wire we = (wc[AW-1:0] == s);
        always @(posedge ck) if (we) begin data[s] <= i; epoch[s] <= wc; end
        assign bank[s*W+:W] = data[s];
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
    assign vld = valid;
assign x_rq = rq; assign x_wc = wc; assign x_woh = write_oh;
endmodule
`default_nettype wire
