module ot_qfd_rst_stn #(parameter integer D = 1) (
    input  wire clk,
    input  wire rst_n,
    output wire rst_q
);
    generate if (D == 0) begin : g_w
        assign rst_q = rst_n;
    end else begin : g_r
        reg [D-1:0] r;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) r <= {D{1'b0}};
            else r <= {r, 1'b1};
        assign rst_q = r[D-1];
    end endgenerate
endmodule
