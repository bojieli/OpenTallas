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
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_vm_wrd #(
    parameter integer LQ  = 24,           // credits a lane (the VM side queue)
    parameter integer D   = 8,            // waves outstanding (response FIFO depth a lane)
    parameter integer SW  = 15,           // sector address bits
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
    output reg  [32*16-1:0]  q,           // lane b: {v, sector15}
    input  wire [31:0]       cr,
    input  wire [32*257-1:0] rsp,         // lane b: {v, data256}
    output reg  [31:0]       d_v,
    output reg  [32*SW-1:0]  d_sec,
    output reg  [32*256-1:0] d_data
);
    localparam integer CW = $clog2(LQ + 1), DW = $clog2(D) > 0 ? $clog2(D) : 1;
    reg [CW-1:0] crd [0:31];
    reg [SW:0]   fst [0:31];              // lane b's first sector of the span
    reg [SW:0]   endx;
    reg [SW:0]   iw, ow;                  // waves issued / delivered
    reg          run;
    reg [255:0]  fq [0:31][0:D-1];        // response FIFOs
    reg [DW:0]   fn [0:31]; reg [DW-1:0] fh [0:31], ft [0:31];
    assign busy = run || req;
    integer b;
    // wave j's lanes; can wave iw issue; is wave ow complete
    reg [31:0] lw_i, lw_o; reg can_i, ful_o, home;
    always @* begin
        can_i = run && gnt && (MUT == 2 || (iw - ow) < D); ful_o = run; home = 1'b1;
        for (b = 0; b < 32; b = b + 1) begin
            lw_i[b] = (fst[b] + {iw[SW-5:0], 5'd0}) < endx;
            lw_o[b] = (fst[b] + {ow[SW-5:0], 5'd0}) < endx;
            if (lw_i[b] && crd[b] == 0) can_i = 1'b0;
            if (lw_o[b] && fn[b] == 0) ful_o = 1'b0;
            if (crd[b] != LQ[CW-1:0]) home = 1'b0;
        end
        if (lw_i == 32'd0) can_i = 1'b0;      // every wave issued
        if (lw_o == 32'd0) ful_o = 1'b0;      // every wave delivered
    end
    function automatic [SW:0] first(input [SW-1:0] s, input integer lane);
        reg [4:0] dd;
        begin dd = 5'(lane) - s[4:0]; first = {1'b0, s} + {{(SW-4){1'b0}}, dd}; end
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; req <= 1'b0; done <= 1'b0; fault <= 1'b0; q <= '0; d_v <= '0; endx <= '0; iw <= '0; ow <= '0;
            for (b = 0; b < 32; b = b + 1) begin crd[b] <= LQ[CW-1:0]; fst[b] <= '0; fn[b] <= '0; fh[b] <= '0; ft[b] <= '0; end
        end else begin : seq
            reg [DW:0] n_;
            done <= 1'b0; d_v <= '0; q <= '0;
            if (start && !run && !req) begin
                run <= 1'b1; req <= 1'b1; endx <= {1'b0, s0} + ns; iw <= '0; ow <= '0;
                for (b = 0; b < 32; b = b + 1) fst[b] <= first(s0, b);
            end else begin
                for (b = 0; b < 32; b = b + 1) begin
                    n_ = fn[b];
                    // issue (a whole wave)
                    if (can_i && lw_i[b]) q[b*16 +: 16] <= {1'b1, SW'(fst[b] + {iw[SW-5:0], 5'd0})};
                    crd[b] <= crd[b] - ((can_i && lw_i[b]) ? 1 : 0) + (cr[b] ? 1 : 0);
                    // responses into the lane FIFO
                    if (rsp[b*257 + 256]) begin
                        if (n_ == D[DW:0]) fault <= 1'b1;
                        else begin fq[b][ft[b]] <= rsp[b*257 +: 256]; ft[b] <= ft[b] + 1'b1; n_ = n_ + 1'b1; end
                    end
                    // deliver wave ow
                    if (ful_o && lw_o[b]) begin
                        d_v[b] <= 1'b1; d_sec[b*SW +: SW] <= SW'(fst[b] + {ow[SW-5:0], 5'd0});
                        d_data[b*256 +: 256] <= (MUT == 1 && b == 1 && ow != 0) ? fq[b][fh[b] - 1'b1] : fq[b][fh[b]];
                        fh[b] <= fh[b] + 1'b1; n_ = n_ - 1'b1;
                    end
                    fn[b] <= n_;
                end
                if (can_i) iw <= iw + 1'b1;
                if (ful_o) ow <= ow + 1'b1;
                if (run && !ful_o && lw_o == 32'd0 && home) begin run <= 1'b0; req <= 1'b0; done <= 1'b1; end
            end
        end
    end
endmodule
`default_nettype wire
