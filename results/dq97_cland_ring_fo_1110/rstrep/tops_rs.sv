// DIE-QC-97 RSTREP-1 LEC wrappers on the real QC ring slw_fe_v2 u_cland_dd_ei (cas W=549 DEPTH 4 WFALL WREG), at the
// pilot form (DSREP 2, WRITE_CHUNK 32, STATUS_REG 1).  Inputs: rs_d = D of the last reader-START stage, raw = its raw reset.
// gold = today: the stage is one ot_dp_landing_relay driving rst_n.
// gate = clock.landing_ring_fanout_max 32: the stage is ot_dp_landing_relay_rep #(4) (q -> rst_n, qx -> rst_xn), RSTREP 4.
// LEC_MUT_LATE: the gate's rst_xn[2] copy is one flop late (wrong D) -> must FAIL.
module lec_gold (input wire fclk, t_rst_n, clk, rs_d, raw, input wire [5:0] strap_k, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    wire rst_n;
    ot_dp_landing_relay u_s (.clk(clk), .rst_raw_n(raw), .d(rs_d), .q(rst_n));
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .STATUS_REG(1), .WFALL(1), .WREG(1), .DSREP(2), .WRITE_CHUNK(32)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module lec_gate (input wire fclk, t_rst_n, clk, rs_d, raw, input wire [5:0] strap_k, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    wire rst_n; wire [3:0] rst_x, rst_xn;
    ot_dp_landing_relay_rep #(.N(4)) u_s (.clk(clk), .rst_raw_n(raw), .d(rs_d), .q(rst_n), .qx(rst_x));
`ifdef LEC_MUT_LATE
    reg late; always @(posedge clk) late <= rst_x[2];
    assign rst_xn = {rst_x[3], late, rst_x[1:0]};
`else
    assign rst_xn = rst_x;
`endif
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .STATUS_REG(1), .WFALL(1), .WREG(1), .DSREP(2), .WRITE_CHUNK(32), .RSTREP(4)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(rst_xn), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
