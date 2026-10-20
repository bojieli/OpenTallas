`timescale 1ns/1ps
`default_nettype none
// HBM-AGSM8 (10-20): STATIC segment GO calendar for the DS expert-intermediate gather train -> w2 SM chain.
//
// Today every `expert slot k w2` SM.MATVEC waits on the COLL unit bit: the CP holds it until EVERY dispatched COLL
// record has retired (unit-granular drain), so the 7 per-layer expert-intermediate gathers run as 7 serial CP records and
// the w2 of slot k cannot start before the last gather dispatched ahead of it.  With the train form the compiler puts
// the 7 segments in ONE gather-master launch (7 descriptor rows, t_start(k) = k * SP, ot_hgi_coll_gq) and the w2 of
// slot k is started by this calendar at a COMPILED edge after the launch: off(k) = t_start(k) + span(F, R)
// (tools/hgi_sim/agsm8_chain_vectors_1020.py), i.e. the first edge whose bank image holds every word of segment k.
// The SM x-load of slot k issues on go_v / go_seg (segment-granular RAW resolved by the compiler: no credit, ready,
// wait bit or data-dependent timing).  Armed by the same launch broadcast the gather masters sample.
//
// Timing (edges after the launch sample edge L): launch pin @L+1 -> counter 0 @L+2 -> compare t == off(cur) @L+2+off
// -> go register -> go pin: go_v visible @L+4+off (GO_LAT 4).  Offsets are written through cfg_* (one row an edge) and
// must be strictly increasing, the last row is cfg_n - 1.  Faults (sticky, never change timing): a launch while armed,
// a non-increasing offset, a row index >= NSEG, cfg written while armed, cfg_n == 0.
// SAFE-DESIGN: every input / output pin registered; reset lands through ot_rst_relay (2 sync + 1 relay stage);
// storage NSEG x OW = 128 b of flops (< 2 kb); the next offset is preloaded into a register through a one-hot AND-OR
// select (no runtime-indexed mux; compare path = 16-b equality); fanout of every register / the hit term <= 32.
// Offsets must be >= 2 edges apart (fault otherwise), which the >= 129-edge train spacing always meets.
module ot_hgi_coll_seg_go #(
    parameter integer NSEG = 8,
    parameter integer OW   = 16
)(
    input  wire          clk, rst_n,
    input  wire          cfg_we,
    input  wire [2:0]    cfg_seg,
    input  wire [OW-1:0] cfg_off,
    input  wire [3:0]    cfg_n,          // segments in the train (sampled with every cfg write)
    input  wire          launch_v,
    output reg           go_v,
    output reg  [2:0]    go_seg,
    output reg           armed,
    output reg           fault
);
    wire [0:0] rl;
    ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rn = rl[0];
    // ---------------------------------------------------------------- input pin registers
    reg we_q, l_q; reg [2:0] seg_q; reg [OW-1:0] off_q; reg [3:0] n_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin we_q <= 1'b0; l_q <= 1'b0; end
        else begin we_q <= cfg_we; l_q <= launch_v; end
    always @(posedge clk) begin seg_q <= cfg_seg; off_q <= cfg_off; n_q <= cfg_n; end
    // ---------------------------------------------------------------- offset rows
    reg [OW-1:0] off [0:NSEG-1];
    reg [OW-1:0] last_off;                   // offset of the previous row written (monotonic check)
    reg [3:0] nseg;
    reg [OW-1:0] t, nx;
    reg [NSEG-1:0] oh;                       // one-hot of the NEXT segment to fire (no runtime index on any path)
    reg [OW-1:0] nx_n;                       // offset of the segment after `oh` (registered AND-OR select)
    reg [2:0] cur;
    reg g; reg [2:0] g_seg; reg flt;
    wire hit = armed && !l_q && t == nx;     // loads: nx 16 + oh 8 + cur 3 + g/g_seg/armed 5 = 32 max
    always @(posedge clk) if (we_q && !armed && {1'b0, seg_q} < 4'(NSEG)) off[seg_q] <= off_q;
    // next-next offset: one-hot AND-OR over the rows (each one-hot bit drives OW = 16 AND gates); GOs are >= 2 edges
    // apart (offsets strictly increasing, checked at cfg) and `oh` is stable >= 1 edge before the next hit
    wire [NSEG-1:0] oh_nx = {oh[NSEG-2:0], 1'b0};
    always @(posedge clk) begin : nb_nx
        reg [OW-1:0] v; v = '0;
        for (integer k = 0; k < NSEG; k = k + 1) v = v | ({OW{oh_nx[k]}} & off[k]);
        nx_n <= v;
    end
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            armed <= 1'b0; t <= '0; nx <= '0; oh <= '0; cur <= 3'd0; g <= 1'b0; g_seg <= 3'd0; flt <= 1'b0; nseg <= 4'd0;
            last_off <= '0;
        end else begin
            g <= 1'b0;
            if (we_q) begin
                if (armed || {1'b0, seg_q} >= 4'(NSEG) || n_q == 4'd0 || (seg_q != 3'd0 && off_q <= last_off + 1'b1)) flt <= 1'b1;
                last_off <= off_q; nseg <= n_q;
            end
            if (l_q) begin
                if (armed) flt <= 1'b1;
                armed <= 1'b1; t <= '0; cur <= 3'd0; nx <= off[0]; oh <= NSEG'(1);
            end else if (armed) begin
                t <= t + 1'b1;
                if (hit) begin
                    g <= 1'b1; g_seg <= cur;
                    cur <= cur + 3'd1;
                    nx <= nx_n; oh <= oh_nx;
                    if ({1'b0, cur} + 4'd1 == nseg) armed <= 1'b0;
                end
            end
        end
    end
    // ---------------------------------------------------------------- output pin registers
    always @(posedge clk or negedge rn)
        if (!rn) begin go_v <= 1'b0; go_seg <= 3'd0; fault <= 1'b0; end
        else begin go_v <= g; go_seg <= g_seg; fault <= flt; end
endmodule
`default_nettype wire
