module ot_d2d_rst_tree_s7 #(parameter integer NR = 36) (
    input  wire          clk,
    input  wire          rst_n_in,
    output wire [NR-1:0] rst_n
);
    (* keep = "true", dont_touch = "true" *) reg s0, s1;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) begin s0 <= 1'b0; s1 <= 1'b0; end
        else begin s0 <= 1'b1; s1 <= s0; end
    wire [3:0] a;
    genvar t;
    for (t = 0; t < 4; t = t + 1) begin : g_a
        ot_d2d_kff u_a (.ck(clk), .d(s1), .q(a[t]));
    end
    for (t = 0; t < NR; t = t + 1) begin : g_b
        ot_d2d_kff u_b (.ck(clk), .d(a[t % 4]), .q(rst_n[t]));
    end
endmodule
