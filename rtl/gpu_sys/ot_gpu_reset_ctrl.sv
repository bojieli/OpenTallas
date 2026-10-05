`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_reset_ctrl: power-on reset distribution of the GPU-organised HBM
// comparator system.  One asynchronous power-on reset (por_n) is asserted
// into every clock domain at once and released per domain through a SYNC-flop
// synchroniser (asynchronous assert, synchronous deassert), in a fixed order:
// the memory service and links first, then the SM domain, then the host
// interface -- so no request can leave an SM or the host before the domain
// that answers it is out of reset.  Each later domain waits for the earlier
// domain's synchronised release (crossed by its own synchroniser) plus HOLD
// cycles of its own clock.
// ENABLE = 0: inert, every reset held asserted (0).
// ---------------------------------------------------------------------------
module ot_gpu_reset_ctrl #(
    parameter integer ENABLE = 0,
    parameter integer SYNC   = 2,
    parameter integer HOLD   = 4
) (
    input  wire por_n,
    input  wire clk_mem,
    input  wire clk_link,
    input  wire clk_sm,
    input  wire clk_host,
    output wire rst_mem_n,
    output wire rst_link_n,
    output wire rst_sm_n,
    output wire rst_host_n
);
generate if (ENABLE == 0) begin : g_off
    assign rst_mem_n = 1'b0; assign rst_link_n = 1'b0; assign rst_sm_n = 1'b0; assign rst_host_n = 1'b0;
end else begin : g_on
    // first: memory service and links, released by por_n alone
    wire mem_q, link_q, sm_q, host_q;
    ot_gpu_rst_stage #(.SYNC(SYNC), .HOLD(HOLD)) u_mem  (.clk(clk_mem),  .arst_n(por_n), .go(1'b1), .rst_n(mem_q));
    ot_gpu_rst_stage #(.SYNC(SYNC), .HOLD(HOLD)) u_link (.clk(clk_link), .arst_n(por_n), .go(1'b1), .rst_n(link_q));
    // then the SM domain, after both have released (each crossed into clk_sm)
    wire mem_in_sm, link_in_sm, sm_in_host;
    ot_gpu_rst_sync #(.SYNC(SYNC)) u_x0 (.clk(clk_sm), .arst_n(por_n), .d(mem_q), .q(mem_in_sm));
    ot_gpu_rst_sync #(.SYNC(SYNC)) u_x1 (.clk(clk_sm), .arst_n(por_n), .d(link_q), .q(link_in_sm));
    ot_gpu_rst_stage #(.SYNC(SYNC), .HOLD(HOLD)) u_sm (.clk(clk_sm), .arst_n(por_n), .go(mem_in_sm && link_in_sm),
                                                      .rst_n(sm_q));
    // last the host interface
    ot_gpu_rst_sync #(.SYNC(SYNC)) u_x2 (.clk(clk_host), .arst_n(por_n), .d(sm_q), .q(sm_in_host));
    ot_gpu_rst_stage #(.SYNC(SYNC), .HOLD(HOLD)) u_host (.clk(clk_host), .arst_n(por_n), .go(sm_in_host),
                                                        .rst_n(host_q));
    assign rst_mem_n = mem_q; assign rst_link_n = link_q; assign rst_sm_n = sm_q; assign rst_host_n = host_q;
end endgenerate
endmodule

// a SYNC-flop synchroniser with asynchronous clear
module ot_gpu_rst_sync #(
    parameter integer SYNC = 2
) (
    input  wire clk,
    input  wire arst_n,
    input  wire d,
    output wire q
);
    reg [SYNC-1:0] s;
    always @(posedge clk or negedge arst_n)
        if (!arst_n) s <= {SYNC{1'b0}};
        else s <= {s[SYNC-2:0], d};
    assign q = s[SYNC-1];
endmodule

// one domain's reset: asynchronous assert, release HOLD cycles after `go` is seen through the synchroniser
module ot_gpu_rst_stage #(
    parameter integer SYNC = 2,
    parameter integer HOLD = 4
) (
    input  wire clk,
    input  wire arst_n,
    input  wire go,
    output reg  rst_n
);
    wire g;
    ot_gpu_rst_sync #(.SYNC(SYNC)) u_s (.clk(clk), .arst_n(arst_n), .d(go), .q(g));
    reg [$clog2(HOLD + 1):0] n;
    always @(posedge clk or negedge arst_n) begin
        if (!arst_n) begin n <= 0; rst_n <= 1'b0; end
        else if (g && !rst_n) begin
            if (n == HOLD) rst_n <= 1'b1;
            else n <= n + 1'b1;
        end
    end
endmodule
