// DIE-KV-9 10-28 (COORD 07:05 ruling (d)): hard-core ring type = one count-aligned landing ring, verbatim
// ot_dp_clk_landing_cas #(.W(1045), .DEPTH(4)) with default guards/ARM/TIMEOUT, as used by every W>=1000 KV landing
// (template replicas; K per instance stays the strap_k pin tied at the parent).  No logic added.
module kv_ring_w1045d4 (
    input  wire          fclk,
    input  wire          t_rst_n,
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]   strap_k,
    input  wire [1044:0] d,
    output wire [1044:0] q,
    output wire          ready,
    output wire          fault
);
    ot_dp_clk_landing_cas #(.W(1045), .DEPTH(4)) u_ring (
        .fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .strap_k(strap_k), .d(d), .q(q),
        .ready(ready), .fault(fault));
endmodule
