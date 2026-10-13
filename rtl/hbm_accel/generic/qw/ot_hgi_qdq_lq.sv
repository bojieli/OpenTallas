`timescale 1ns/1ps
`default_nettype none
// ot_hgi_qdq_q lane-response pair (el1011-hbm-sfu, 2026-10-12): hardened M5 leaf tile, 4 per QDQ B2 quarter on the
// slice read face (lanes 2p, 2p+1).  Takes the 8 x 16 x 256 lane FIFOs (32,768 flops) off the cluster clock root: the
// cluster's remote gate refused 45,992 flops on one root (> 15k).  Per tile: 2 lanes x LD 16 x 256 = 8,192 storage flops
// + 512 response pin flops + 512 head-out flops (~9.3k sinks, its own local clock tree).
// Same contract as ot_hgi_qw_rq (the closed quant_wide_h read quad), at LD 16: every port registered on the tile side;
// the centre counts lane occupancy from e_push, decides pops, and sends registered per-lane pop strobes (c_pop); the
// tile reads the popped lane's head into its own output register hq (free-running data, valid implied by the centre's
// delayed pop) -- no shared select inside the tile, the centre places lanes into beat positions.
// Latency: wrr -> p_v (1) -> FIFO write + e_push (2); c_pop -> i_pop (1) -> hq (2).
// Overrun (a push into a full lane FIFO: the centre's lf_r <= LD credit check broken) raises the sticky e_ovf.
// Production defaults only (the hardened view is a liberty blackbox: no parameter overrides at the instance).
module ot_hgi_qdq_lq #(
    parameter integer LD = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [2*257-1:0]  wrr,         // {v, sector data 256} per lane (slice read responses, in order per lane)
    input  wire [1:0]        c_pop,       // centre: pop lane i's head (registered in the centre)
    output reg  [2*256-1:0]  hq,          // popped heads, two cycles after c_pop
    output reg  [1:0]        e_push,      // a response landed in lane i's FIFO
    output reg               e_ovf        // sticky FIFO overrun
);
    localparam integer LW = $clog2(LD);
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    // input registers (valids reset, data free-running)
    reg [1:0] p_v, i_pop;
    reg [255:0] p_d [0:1];
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin p_v <= 0; i_pop <= 0; end
        else for (integer i = 0; i < 2; i = i + 1) begin p_v[i] <= wrr[i*257 + 256]; i_pop[i] <= c_pop[i]; end
    always @(posedge clk) for (integer i = 0; i < 2; i = i + 1) p_d[i] <= wrr[i*257 +: 256];
    // per-lane FIFOs (storage without reset)
    reg [255:0] lf [0:1][0:LD-1];
    reg [LW-1:0] lf_h [0:1], lf_t [0:1];
    reg [LW:0] lf_n [0:1];
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin
            for (integer i = 0; i < 2; i = i + 1) begin lf_h[i] <= 0; lf_t[i] <= 0; lf_n[i] <= 0; end
            e_push <= 0; e_ovf <= 0;
        end else begin
            for (integer i = 0; i < 2; i = i + 1) begin
                if (p_v[i]) lf_t[i] <= lf_t[i] + 1'b1;
                if (i_pop[i]) lf_h[i] <= lf_h[i] + 1'b1;
                lf_n[i] <= lf_n[i] + (LW+1)'(p_v[i]) - (LW+1)'(i_pop[i]);
                if (p_v[i] && !i_pop[i] && lf_n[i] == LD[LW:0]) e_ovf <= 1'b1;
            end
            e_push <= p_v;
        end
    always @(posedge clk)
        for (integer i = 0; i < 2; i = i + 1) if (p_v[i]) lf[i][lf_t[i]] <= p_d[i];
    // head read: 16:1 x 256 per lane, split in 8 slices of 32 b, each on its own kept copy of the read pointer (pre-route
    // gate 10-12: one lf_h bit drove 3,057 mux loads; a copy now drives ~32 x 15)
    genvar gi, gs;
    generate for (gi = 0; gi < 2; gi = gi + 1) begin : g_ln
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_sl
            (* keep *) reg [LW-1:0] hc;
            always @(posedge clk or negedge rr_n[0])
                if (!rr_n[0]) hc <= 0;
                else if (i_pop[gi]) hc <= hc + 1'b1;
            always @(posedge clk) hq[gi*256 + gs*32 +: 32] <= lf[gi][hc][gs*32 +: 32];
        end
    end endgenerate
    initial if ((LD & (LD - 1)) != 0) $fatal(1, "ot_hgi_qdq_lq: LD power of two");
endmodule
`default_nettype wire
