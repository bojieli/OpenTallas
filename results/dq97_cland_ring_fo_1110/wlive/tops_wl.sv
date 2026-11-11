// DIE-QC-97 WLIVE-1 LEC: old ot_dp_clk_landing_ca.sv (gold) vs WLIVE-1 (gate) at the pilot ring form (DSREP 2,
// WRITE_CHUNK 32, STATUS_REG 1, WFALL, WREG): W=33 (its last 32-bit write chunk is padding only: the enable flop that
// face_guard rejected) and W=549 (slw_fe_v2 u_cland_dd_ei, no padding-only chunk).
module lec_top (input wire fclk, t_rst_n, clk, rst_n, input wire [5:0] strap_k, input wire [548:0] d, input wire [32:0] d2,
                output wire [548:0] q, output wire ready, fault, output wire [32:0] q2, output wire ready2, fault2);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .STATUS_REG(1), .WFALL(1), .WREG(1), .DSREP(2), .WRITE_CHUNK(32)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
    ot_dp_clk_landing_cas #(.W(33), .DEPTH(4), .STATUS_REG(1), .WFALL(1), .WREG(1), .DSREP(2), .WRITE_CHUNK(32)) u2 (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d2), .q(q2), .ready(ready2), .fault(fault2));
endmodule
