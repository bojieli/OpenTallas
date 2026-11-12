// CLAND-QREG-1 EQ wrappers: gold = the QREG=0 ring followed by ONE declared rclk register on q (the declared +1 data
// cycle); gate = the QREG=1 ring.  Same ports; the ring hierarchy u_dut is identical in both.
module eq_gold_cas #(parameter integer W = 2, parameter integer DEPTH = 4, parameter bit SR = 0, parameter bit WF = 0, parameter bit WR = 0) (
    input wire fclk, t_rst_n, clk, rst_n, input wire [$clog2(DEPTH)+3:0] strap_k, input wire [W-1:0] d,
    output wire [W-1:0] q, output wire ready, fault);
    wire [W-1:0] q0;
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(DEPTH), .CONTROL_STATUS_COPY(SR), .STATUS_REG(SR), .WFALL(WF), .WREG(WR), .QREG(0)) u_dut (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q0), .ready(ready), .fault(fault));
    reg [W-1:0] declared_q; always @(posedge clk) declared_q <= q0;   // the declared +1 cycle (not the mutable stage)
    assign q = declared_q;
endmodule
module eq_gate_cas #(parameter integer W = 2, parameter integer DEPTH = 4, parameter bit SR = 0, parameter bit WF = 0, parameter bit WR = 0) (
    input wire fclk, t_rst_n, clk, rst_n, input wire [$clog2(DEPTH)+3:0] strap_k, input wire [W-1:0] d,
    output wire [W-1:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(DEPTH), .CONTROL_STATUS_COPY(SR), .STATUS_REG(SR), .WFALL(WF), .WREG(WR), .QREG(1)) u_dut (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module eq_gold_plain #(parameter integer W = 2, parameter bit WN = 0) (
    input wire fclk, clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q, output wire ready, fault);
    wire [W-1:0] q0;
    ot_dp_clk_landing #(.W(W), .WNEG(WN), .QREG(0)) u_dut (.fclk(fclk), .clk(clk), .rst_n(rst_n), .d(d), .q(q0), .ready(ready), .fault(fault));
    reg [W-1:0] declared_q; always @(posedge clk) declared_q <= q0;   // the declared +1 cycle (not the mutable stage)
    assign q = declared_q;
endmodule
module eq_gate_plain #(parameter integer W = 2, parameter bit WN = 0) (
    input wire fclk, clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q, output wire ready, fault);
    ot_dp_clk_landing #(.W(W), .WNEG(WN), .QREG(1)) u_dut (.fclk(fclk), .clk(clk), .rst_n(rst_n), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
