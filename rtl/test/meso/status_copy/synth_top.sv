module status_copy_synth (
    input wire fclk,clk,t_rst_n,r_rst_n,
    input wire [63:0] d,
    input wire [5:0] k,
    output wire [63:0] q,
    output wire [3:0] flags
);
    ot_meso_ring_ca #(.W(64),.DEPTH(4),.CONTROL_STATUS_COPY(1)) u_ring (
        .tclk(fclk),.t_rst_n(t_rst_n),.t_d(d),.rclk(clk),.r_rst_n(r_rst_n),.k_s(k),
        .r_d(q),.r_v(flags[0]),.r_lap_ok(flags[1]),.r_glo_ok(flags[2]),.r_ghi_ok(flags[3]));
endmodule
