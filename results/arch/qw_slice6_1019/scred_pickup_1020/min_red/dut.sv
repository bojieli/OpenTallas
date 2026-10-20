module qfd_dv_s5_rst2 (input wire ck, input wire rst_n, output wire rst);
    reg rs1, rs2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rs2 <= 1'b0; end
        else begin rs1 <= 1'b1; rs2 <= rs1; end
    assign rst = rs2;
endmodule
module qfd_dv_s5_red (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [7:0]     l_ov,
    input  wire [8*32-1:0] l_out,
    input  wire [1:0]     l_red0,
    input  wire           l_redsq0,
    input  wire           l_last0,
    input  wire [23:0]    l_raddr0,
    output wire           red_we,
    output wire [23:0]    red_addr,
    output wire [31:0]    red_data,
    output reg            rd_v,
    output wire           busy,
    output wire           fault
);
    localparam integer SW = 8, AW = 24;
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    reg rc;
    always @(posedge ck or negedge rst) if (!rst) rc <= 1'b0; else rc <= 1'b1;
    wire rst_c = rc;
    reg              rd_mx, rd_sq, rd_last;
    reg [AW-1:0]     rd_addr;
    reg [SW*32-1:0]  rd_x;
    integer li;
    always @(posedge ck or negedge rst_c) begin
        if (!rst_c) rd_v <= 1'b0;
        else rd_v <= l_ov[0] && l_red0 != 2'd0;
    end
    always @(posedge ck) begin
`ifdef OT_S5_RED_MUT
        rd_mx <= (l_red0 == 2'd1); rd_sq <= l_redsq0; rd_last <= l_last0; rd_addr <= l_raddr0;   // bench mutant: SUM taken as MAX (must FAIL)
`else
        rd_mx <= (l_red0 == 2'd2); rd_sq <= l_redsq0; rd_last <= l_last0; rd_addr <= l_raddr0;
`endif
        for (li = 0; li < SW; li = li + 1)
            rd_x[32*li +: 32] <= l_ov[li] ? l_out[32*li +: 32] : (l_red0 == 2'd2) ? l_out[31:0] : 32'd0;
    end
`ifdef OT_S5_RED_RING
    // fallback qfd_dv_s5_redb: the same reducer with its >= 3-deep data delay lines as flop rings (cycle-exact)
    qfd_dv_s5_vreduce_rb #(.SW(SW), .LV(4), .AW(AW)) u_red (.clk(ck), .rst_n(rst_c), .v_in(rd_v), .mx_in(rd_mx),
`else
    ot_hdc_vreduce #(.SW(SW), .LV(4), .AW(AW)) u_red (.clk(ck), .rst_n(rst_c), .v_in(rd_v), .mx_in(rd_mx),
`endif
        .sq_in(rd_sq), .last_in(rd_last), .addr_in(rd_addr), .x_in(rd_x),
        .o_we(red_we), .o_addr(red_addr), .o_data(red_data), .busy(busy), .fault(fault));
endmodule