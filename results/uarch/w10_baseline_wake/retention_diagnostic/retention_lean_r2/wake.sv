module wake_diag(input clk,rst_n,go,go_e,walk_busy, input [7:0] drain, output [7:0] leaf_clk);
genvar wg; generate begin : g_wake
        for (wg = 0; wg < 8; wg = wg + 1) begin : g_leaf
            (* keep = 1, dont_touch = 1 *) reg wake;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) wake <= 1'b1;
                else wake <= go || go_e || walk_busy || drain != 8'd0;
            assign leaf_clk[wg] = wake;
        end
end endgenerate
endmodule
