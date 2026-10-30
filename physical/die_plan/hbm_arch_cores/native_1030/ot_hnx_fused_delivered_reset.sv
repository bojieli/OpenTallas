
// one tree node (hardened once: hnx_fused_tnode_1019, x28 on the die; straps tied by the die binder)
// The input is already the die's synchronously delivered reset. Three timed
// local relay edges preserve the legacy two-sync-plus-one-tree RELEASE date.
// Assertion is pipelined too: clock runs at boot; START/job_v waits for every
// delivered/local reset and pad warm-up. No local CDC or false path is legal.
module ot_hnx_fused_delivered_reset #(parameter integer REGIONS = 4) (
    input wire clk, rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    for (genvar r = 0; r < REGIONS; r = r + 1) begin : g_region
        (* keep = "true", dont_touch = "true" *) reg [2:0] pipe;
        always @(posedge clk) pipe <= {pipe[1:0], rst_n_in};
        assign rst_n[r] = pipe[2];
    end
endmodule
