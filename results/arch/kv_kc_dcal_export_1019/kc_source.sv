module qkd_ctrl_kc #(
    parameter integer MUT = 0
) (
    input  wire        ck,
    input  wire        rsi,
    input  wire        pll_hbm,
    input  wire        hrst,
    input  wire [32:0] kc,
    output reg  [32:0] ko,
    input  wire        fi,
    output reg         kf
);
    (* keep *) reg hr_q;
    (* keep *) reg rs_q;
    always @(posedge pll_hbm) hr_q <= hrst;
    always @(posedge ck)      rs_q <= rsi;
    (* keep *) reg        kv_q;
    (* keep *) reg [31:0] kd_q;
    always @(posedge ck or negedge rs_q) if (!rs_q) kv_q <= 1'b0; else kv_q <= kc[0];
    always @(posedge ck) kd_q <= kc[32:1];
    wire        w_rdy, r_v;
    wire [31:0] r_d;
    ot_async_fifo #(.WIDTH(32), .DEPTH(8)) u_x (
        .wr_clk(ck), .wr_rst_n(rs_q), .wr_valid(kv_q), .wr_ready(w_rdy), .wr_data(kd_q), .wr_overflow(),
        .rd_clk(pll_hbm), .rd_rst_n(hr_q), .rd_valid(r_v), .rd_ready(1'b1), .rd_data(r_d), .rd_underflow());
    always @(posedge pll_hbm or negedge hr_q) if (!hr_q) ko[0] <= 1'b0; else ko[0] <= r_v;
    always @(posedge pll_hbm) ko[32:1] <= (MUT == 1) ? (r_d ^ 32'h0000_4000) : r_d;
    reg f_ovf;
    (* async_reg = "true" *) reg f1, f2;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin f_ovf <= 1'b0; f1 <= 1'b0; f2 <= 1'b0; kf <= 1'b0; end
        else begin
            if (kv_q && !w_rdy) f_ovf <= 1'b1;
            f1 <= fi; f2 <= f1; kf <= f2 | f_ovf;
        end
endmodule
