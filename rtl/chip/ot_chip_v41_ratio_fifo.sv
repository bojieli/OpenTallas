// ot_chip_v41_ratio_fifo -- synchronous-ratio clock-domain crossing of the V4.1 ROM die (W18).
//
// Die clock plan (root, AGENTS.md c0894b1c): one PLL per die, VCO 3.6 GHz; /3 -> 1.2 GHz streaming domain
// (ROM field, index and attention tiles, VM, collective, links, HBM service), /4 -> 0.9 GHz serial-chain
// domain (SU, SFU, softplus, Sinkhorn/mHC, reducers).  Both dividers come off the same VCO, so the two
// clocks are phase-related: their edges coincide every 3.333 ns (4 fast = 3 slow cycles), and the tightest
// launch-to-capture spacing between a fast and a slow edge is 278 ps (1.111 - 0.833 ns) in either direction.
//
// This FIFO crosses without synchronisers (the clocks are not asynchronous) and without a timing exception:
//   * the source writes an entry of a DEPTH-deep register file and, ONE source cycle later, advances its
//     write pointer (Gray not needed: the pointer register is sampled on related edges, STA times it);
//   * the destination compares the source pointer (one flop-to-flop crossing, placed at the domain edge, so
//     278 ps covers clk->q + wire + setup + 60 ps uncertainty) with its read pointer, and reads the entry
//     into an output register -- the data path from the register file therefore has >= 278 + one source
//     period before it is read;
//   * the read pointer crosses back the same way for the full/credit check.
// Latency: one source cycle (pointer delay) + the wait for the next destination edge + one destination
// cycle (output register); tb_chip_v41_ratio_fifo measures it in both directions.
module ot_chip_v41_ratio_fifo #(
    parameter int W     = 64,
    parameter int DEPTH = 4                  // entries (power of 2)
) (
    input  logic         wclk,
    input  logic         wrst_n,
    input  logic         w_v,
    output logic         w_rdy,
    input  logic [W-1:0] w_d,
    input  logic         rclk,
    input  logic         rrst_n,
    output logic         r_v,
    input  logic         r_rdy,
    output logic [W-1:0] r_d
);
    localparam int AW = $clog2(DEPTH);
    logic [W-1:0] mem [DEPTH];
    logic [AW:0]  wp, wp_pub;                // wp_pub: the pointer the reader sees (one write cycle late)
    logic [AW:0]  rp, rp_pub;
    logic [AW:0]  rp_w;                      // reader pointer seen in the write domain
    logic [AW:0]  wp_r;                      // writer pointer seen in the read domain
    // ---------------- write domain ----------------
    assign w_rdy = (wp - rp_w) < (AW+1)'(DEPTH);
    always_ff @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin wp <= '0; wp_pub <= '0; rp_w <= '0; end
        else begin
            if (w_v && w_rdy) wp <= wp + 1'b1;
            wp_pub <= wp;                    // publish one write cycle after the entry is written
            rp_w <= rp_pub;                  // related-clock crossing (timed by STA)
        end
    end
    always_ff @(posedge wclk) if (w_v && w_rdy) mem[wp[AW-1:0]] <= w_d;
    // ---------------- read domain ----------------
    logic take;
    assign take = (wp_r != rp) && (!r_v || r_rdy);
    always_ff @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin rp <= '0; rp_pub <= '0; wp_r <= '0; r_v <= 1'b0; end
        else begin
            wp_r <= wp_pub;                  // related-clock crossing (timed by STA)
            if (take) begin rp <= rp + 1'b1; r_v <= 1'b1; end
            else if (r_v && r_rdy) r_v <= 1'b0;
            rp_pub <= take ? rp + 1'b1 : rp;
        end
    end
    always_ff @(posedge rclk) if (take) r_d <= mem[rp[AW-1:0]];
endmodule
