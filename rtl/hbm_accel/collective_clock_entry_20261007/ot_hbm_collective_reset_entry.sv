// Opt-in cold reset boundary. No context-arm or data control drives these flops.
// Async assertion and two local-clock release edges must survive technology mapping.
module ot_hbm_collective_reset_entry #(parameter integer ENABLE=0)(
    input wire clk_stream, clk_link,
    input wire por_stream, por_link,
    output wire rst_n, prst_n
);
    generate if (ENABLE) begin : g_on
        (* ASYNC_REG="TRUE" *) reg [1:0] stream_reset;
        (* ASYNC_REG="TRUE" *) reg [1:0] link_reset;
        always @(posedge clk_stream or posedge por_stream)
            if (por_stream) stream_reset <= 2'b11;
            else stream_reset <= {stream_reset[0],1'b0};
        always @(posedge clk_link or posedge por_link)
            if (por_link) link_reset <= 2'b11;
            else link_reset <= {link_reset[0],1'b0};
        assign rst_n = ~stream_reset[1];
        assign prst_n = ~link_reset[1];
    end else begin : g_off
        assign rst_n=1'b0;
        assign prst_n=1'b0;
    end endgenerate
endmodule
