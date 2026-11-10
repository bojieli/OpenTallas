// DIE-QC-97 ring LEC wrappers: one real QC ring (slw_fe_v2 u_cland_dd_ei: cas W=549 DEPTH 4 WFALL 1 WREG 1)
// gold = as built today (DSREP 1, WRITE_CHUNK 64); gate = clock.landing_ring_fanout_max 32 (DSREP 2, WRITE_CHUNK 32)
module lec_gold (input wire fclk, t_rst_n, clk, rst_n, input wire [5:0] strap_k, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .DSREP(1)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
module lec_gate (input wire fclk, t_rst_n, clk, rst_n, input wire [5:0] strap_k, input wire [548:0] d,
                 output wire [548:0] q, output wire ready, fault);
    ot_dp_clk_landing_cas #(.W(549), .DEPTH(4), .WFALL(1), .WREG(1), .DSREP(2), .WRITE_CHUNK(32)) u (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q), .ready(ready), .fault(fault));
endmodule
