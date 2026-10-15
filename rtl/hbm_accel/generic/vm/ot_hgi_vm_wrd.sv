`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 VM wide READ client (hgi-1010/d, 2026-10-10): one client of a 32-lane VM lane group (ot_hgi_vm_lanearb,
// LANE-GROUP DIE CONTRACT in hgi-1010.log).  Reads a contiguous sector span [s0, s0 + ns) through the 32 lanes; lane b
// carries the sectors == b (mod 32) in ascending order (lane b <-> VM bank b).  Wave j = the j-th sector of every lane
// = chunks 32 j .. 32 j + 31 of the span (chunk c = sector - s0 sits on lane (s0 + c) mod 32).
//   Ownership: req rises at start and is held for the whole burst; lanes issue only while gnt; req drops when every
//   response landed and every credit is home (the arbiter's per-burst rule).
//   Credits: LQ a lane, spent at issue, returned by cr (bank acceptance).  Responses: rsp lane b {v, data256}, in
//   order per lane, any latency, any skew between lanes: each response is matched to its lane's oldest outstanding
//   sector by order, never by a cycle count.
//   Issue: in WAVES -- wave j goes out on every lane of the wave in the same edge, only while every such lane holds a
//   credit and fewer than D waves are outstanding (issued, not delivered).
//   Delivery: wave by wave -- per lane a D-entry response FIFO; wave j is delivered (d_v = its lanes, d_sec, d_data) in
//   ONE edge once every lane of the wave has its response, so a consumer writes whole rows (e.g. SRAM macro rows).
//   No back pressure on the consumer (it takes a wave an edge); throughput = min(1, D / round trip) waves an edge.
// NL (smmv-b BDW8, 2026-10-12): lane count (default 32 = the r25gq lane group; 8 = a B2 LOCAL slice group, lane b <->
//   local bank b = sector[2:0]).  GATHER = 1: per-WAVE base instead of one contiguous span -- the burst opens at start
//   (s0 / ns ignored) and takes waves on g_v / g_rdy: wave = NL consecutive chunks c of sectors g_s0 + c, chunk c
//   enabled by g_m[c], on lane (g_s0 + c) mod NL (every lane at most once a wave); the burst closes once g_fin is
//   high, every taken wave is delivered and every credit is home.  Delivery as above plus d_w (the wave) / d_s0 (its
//   base) / d_m (its chunk mask).  GATHER = 0 (default) is unchanged.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_vm_wrd #(
    parameter integer LQ  = 24,           // credits a lane (the VM side queue)
    parameter integer D   = 8,            // waves outstanding (response FIFO depth a lane)
    parameter integer SW  = 15,           // sector address bits
    parameter integer NL  = 32,           // lanes (power of two, 8 or 32)
    parameter integer GATHER = 0,         // 1 = per-wave base (g_* port); 0 = one contiguous span a burst
    parameter integer MUT = 0             // bench mutants: 1 = lane 1's response FIFO pops one wave late (skew ignored:
                                          //   lane 1 delivers wave j - 1's data with wave j), 2 = no D bound (FIFO overrun)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,       // one burst: sectors [s0, s0 + ns), ns >= 1
    input  wire [SW-1:0]     s0,
    input  wire [SW:0]       ns,
    output wire              busy,
    output reg               done,        // pulse: the burst's last wave delivered and every credit home
    output reg               fault,       // sticky: a response with no outstanding sector / a FIFO overrun
    output reg               req,
    input  wire              gnt,
    output reg  [NL*16-1:0]  q,           // lane b: {v, sector15}
    input  wire [NL-1:0]     cr,
    input  wire [NL*257-1:0] rsp,         // lane b: {v, data256}
    output reg  [NL-1:0]     d_v,
    output reg  [NL*SW-1:0]  d_sec,
    output reg  [NL*256-1:0] d_data,
    // GATHER = 1 only
    input  wire              g_v,
    input  wire [SW-1:0]     g_s0,
    input  wire [NL-1:0]     g_m,
    output wire              g_rdy,       // the wave on g_* issues this edge (g_v && g_rdy)
    input  wire              g_fin,       // no further wave in this burst
    output reg               d_w,
    output reg  [SW-1:0]     d_s0,
    output reg  [NL-1:0]     d_m
);
    localparam integer CW = $clog2(LQ + 1), DW = $clog2(D) > 0 ? $clog2(D) : 1, LG = $clog2(NL);
    reg [CW-1:0] crd [0:NL-1];
    reg [SW:0]   fst [0:NL-1];            // lane b's first sector of the span
    reg [SW:0]   endx;
    reg [SW:0]   iw, ow;                  // waves issued / delivered
    reg          run;
    reg [255:0]  fq [0:NL-1][0:D-1];      // response FIFOs
    reg [DW:0]   fn [0:NL-1]; reg [DW-1:0] fh [0:NL-1], ft [0:NL-1];
    // GATHER: the issued waves' {base, chunk mask} in order (delivery side)
    reg [SW-1:0] gq_s0 [0:D-1]; reg [NL-1:0] gq_m [0:D-1]; reg [DW-1:0] gqh, gqt;
    assign busy = run || req;
    integer b;
    function automatic [LG-1:0] chunk(input [SW-1:0] s, input integer lane);   // lane's chunk in a wave based at s
        chunk = LG'(lane) - s[LG-1:0];
    endfunction
    // wave j's lanes; can wave iw issue; is wave ow complete
    reg [NL-1:0] lw_i, lw_o; reg can_i, ful_o, home;
    always @* begin
        can_i = run && gnt && (MUT == 2 || (iw - ow) < D) && (GATHER == 0 || g_v); ful_o = run; home = 1'b1;
        for (b = 0; b < NL; b = b + 1) begin
            if (GATHER != 0) begin
                lw_i[b] = g_m[chunk(g_s0, b)];
                lw_o[b] = (iw != ow) && gq_m[gqh][chunk(gq_s0[gqh], b)];
            end else begin
                lw_i[b] = (fst[b] + (iw << LG)) < endx;
                lw_o[b] = (fst[b] + (ow << LG)) < endx;
            end
            if (lw_i[b] && crd[b] == 0) can_i = 1'b0;
            if (lw_o[b] && fn[b] == 0) ful_o = 1'b0;
            if (crd[b] != LQ[CW-1:0]) home = 1'b0;
        end
        if (lw_i == {NL{1'b0}}) can_i = 1'b0;      // every wave issued (GATHER: an empty wave never issues)
        if (lw_o == {NL{1'b0}}) ful_o = 1'b0;      // every wave delivered
    end
    assign g_rdy = (GATHER != 0) && can_i;
    function automatic [SW:0] first(input [SW-1:0] s, input integer lane);
        reg [LG-1:0] dd;
        begin dd = LG'(lane) - s[LG-1:0]; first = {1'b0, s} + (SW+1)'(dd); end
    endfunction
    wire fin_ok = (GATHER != 0) ? (g_fin && iw == ow) : (lw_o == {NL{1'b0}});
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; req <= 1'b0; done <= 1'b0; fault <= 1'b0; q <= '0; d_v <= '0; endx <= '0; iw <= '0; ow <= '0;
            d_w <= 1'b0; gqh <= '0; gqt <= '0;
            for (b = 0; b < NL; b = b + 1) begin crd[b] <= LQ[CW-1:0]; fst[b] <= '0; fn[b] <= '0; fh[b] <= '0; ft[b] <= '0; end
        end else begin : seq
            reg [DW:0] n_;
            done <= 1'b0; d_v <= '0; q <= '0; d_w <= 1'b0;
            if (start && !run && !req) begin
                run <= 1'b1; req <= 1'b1; endx <= {1'b0, s0} + ns; iw <= '0; ow <= '0; gqh <= '0; gqt <= '0;
                for (b = 0; b < NL; b = b + 1) fst[b] <= first(s0, b);
            end else begin
                for (b = 0; b < NL; b = b + 1) begin
                    n_ = fn[b];
                    // issue (a whole wave)
                    if (can_i && lw_i[b])
                        q[b*16 +: 16] <= {1'b1, (GATHER != 0) ? SW'(g_s0 + SW'(chunk(g_s0, b))) : SW'(fst[b] + (iw << LG))};
                    crd[b] <= crd[b] - ((can_i && lw_i[b]) ? 1 : 0) + (cr[b] ? 1 : 0);
                    // responses into the lane FIFO
                    if (rsp[b*257 + 256]) begin
                        if (n_ == D[DW:0]) fault <= 1'b1;
                        else begin fq[b][ft[b]] <= rsp[b*257 +: 256]; ft[b] <= ft[b] + 1'b1; n_ = n_ + 1'b1; end
                    end
                    // deliver wave ow
                    if (ful_o && lw_o[b]) begin
                        d_v[b] <= 1'b1;
                        d_sec[b*SW +: SW] <= (GATHER != 0) ? SW'(gq_s0[gqh] + SW'(chunk(gq_s0[gqh], b))) : SW'(fst[b] + (ow << LG));
                        d_data[b*256 +: 256] <= (MUT == 1 && b == 1 && ow != 0) ? fq[b][fh[b] - 1'b1] : fq[b][fh[b]];
                        fh[b] <= fh[b] + 1'b1; n_ = n_ - 1'b1;
                    end
                    fn[b] <= n_;
                end
                if (can_i) begin
                    iw <= iw + 1'b1;
                    if (GATHER != 0) begin gq_s0[gqt] <= g_s0; gq_m[gqt] <= g_m; gqt <= gqt + 1'b1; end
                end
                if (ful_o) begin
                    ow <= ow + 1'b1;
                    if (GATHER != 0) begin d_w <= 1'b1; d_s0 <= gq_s0[gqh]; d_m <= gq_m[gqh]; gqh <= gqh + 1'b1; end
                end
                if (run && !ful_o && fin_ok && home) begin run <= 1'b0; req <= 1'b0; done <= 1'b1; end
            end
        end
    end
endmodule
`default_nettype wire
