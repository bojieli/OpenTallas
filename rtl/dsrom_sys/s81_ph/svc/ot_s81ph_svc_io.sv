`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_svc_io -- S81 scan service (dsfd_svc) IO hub, CLAUDE S81-PH 2026-10-06 (DESIGN SIMPLIFICATION RULES).
// Contract: results/rtl/s81_ph_20261006/svc/contract.json.  The scan service is a hierarchical slab (8.5 x 1.58 mm):
// NQ quadrant compute blocks (attention tiles + index reader, their owners' hardened views), this IO hub at the N-E
// pin group (q / od / xd / ad, <= 1 mm) and ot_s81ph_svc_rd at the S rd pin group.  The hub has no arithmetic:
//   q   (515: [0] v, [512:1] data, [513] live, [514] fault)  pin register -> kept replicas -> one registered copy per
//       quadrant (fanout <= 32 per stage).  No ready (the VM paces queries; the die lane has none).
//   od  (514 vr: [0] rst_n, [1] v, [513:2] data)  NQ quadrant frame streams merged FRAME-ATOMICALLY (hub framing:
//       header word, then len = data[491:480] raw words), round-robin at frame boundaries, one word a cycle.
//   a0  (ad[512:0]: [0] v, [512:1] data)  attention results, NQ quadrant frame streams merged the same way.
//   a1  (ad[1025:513]) / xd: index frames / index-score stream from the index reader (one source each): skid -> pin.
// Every internal source interface is valid/ready through a 2-slot skid (latency-insensitive); every output is
// launched from a flop at its pin; the reset is synchronised (rst_s[1], the margin SDC's rst_mcp2 cell).
// Order guarantees: per source, words leave in arrival order; a frame's words leave contiguously; nothing is dropped
// or duplicated.  fault: a header whose len > LMAX (malformed) raises the sticky fault output, frames keep flowing.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_skid #(parameter integer W = 8) (
    input  wire         clk, rst_n,
    input  wire         i_v, input wire [W-1:0] i_d, output wire i_r,
    output wire         o_v, output wire [W-1:0] o_d, input wire o_r
);
    // 2-slot skid: i_r is a register (no combinational ready path through the block)
    reg v0, v1, up; reg [W-1:0] d0, d1;
    assign i_r = up && !v1;                 // not ready while in reset
    always @(posedge clk or negedge rst_n) if (!rst_n) up <= 1'b0; else up <= 1'b1;
    assign o_v = v0; assign o_d = d0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v0 <= 1'b0; v1 <= 1'b0; end
        else begin
            if (o_r || !v0) begin
                v0 <= v1 || (i_v && i_r);
                v1 <= 1'b0;
            end else if (i_v && i_r) v1 <= 1'b1;
        end
    always @(posedge clk) begin
        if (o_r || !v0) d0 <= v1 ? d1 : i_d;
`ifdef S81PH_SVC_MUT_SKID
        if (1'b0) d1 <= i_d;                                                 // MUTANT: second slot never written
`else
        if (!(o_r || !v0) && i_v && i_r) d1 <= i_d;
`endif
    end
endmodule

// frame-atomic round-robin merge of N valid/ready frame streams into one registered valid-only output
module ot_s81ph_fmerge #(parameter integer N = 4, parameter integer LMAX = 255) (   // LMAX: the collector's frame buffer
    input  wire           clk, rst_n,
    input  wire [N-1:0]   s_v, input wire [512*N-1:0] s_d, output wire [N-1:0] s_r,
    output reg            o_v, output reg [511:0] o_d,
    output reg            bad
);
    wire [N-1:0] k_v; wire [512*N-1:0] k_d; reg [N-1:0] k_r;
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_s
        ot_s81ph_skid #(.W(512)) u_k (.clk(clk), .rst_n(rst_n), .i_v(s_v[g]), .i_d(s_d[512*g +: 512]), .i_r(s_r[g]),
            .o_v(k_v[g]), .o_d(k_d[512*g +: 512]), .o_r(k_r[g]));
    end endgenerate
    localparam integer SW = (N > 1) ? $clog2(N) : 1;
    reg busy, hdr; reg [SW-1:0] cur; reg [11:0] rem; reg [SW-1:0] rr;
    // next source: registered round-robin pick among valid skid heads (only at a frame boundary)
    reg [SW-1:0] pick; reg pick_v; integer j;
    always @* begin
        pick = rr; pick_v = 1'b0;
        for (j = N - 1; j >= 0; j = j - 1)
            if (k_v[(rr + j) % N]) begin pick = (rr + j) % N; pick_v = 1'b1; end
    end
    wire [511:0] cd = k_d[512*cur +: 512];
    always @* begin k_r = {N{1'b0}}; if (busy) k_r[cur] = 1'b1; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin busy <= 1'b0; hdr <= 1'b0; cur <= 0; rem <= 0; rr <= 0; o_v <= 1'b0; bad <= 1'b0; end
        else begin
            o_v <= 1'b0;
            if (!busy) begin
                if (pick_v) begin busy <= 1'b1; hdr <= 1'b1; cur <= pick; end   // header next
            end else if (k_v[cur]) begin
                o_v <= 1'b1;
                if (hdr) begin                                                    // header word
                    hdr <= 1'b0; rem <= cd[491:480];
                    if (cd[491:480] > LMAX) bad <= 1'b1;
                    if (cd[491:480] == 12'd0) begin busy <= 1'b0; rr <= (cur == N - 1) ? 0 : cur + 1'b1; end
                end else begin
                    rem <= rem - 1'b1;
`ifdef S81PH_SVC_MUT_NOATOM
                    if (1'b1) begin busy <= 1'b0;                            // MUTANT: re-arbitrate every word
`else
                    if (rem == 12'd1) begin busy <= 1'b0;
`endif rr <= (cur == N - 1) ? 0 : cur + 1'b1; end
                end
            end
        end
    always @(posedge clk) o_d <= cd;
endmodule

module ot_s81ph_svc_io #(
    parameter integer NQ = 4,
    parameter integer SYNC = 1               // 0: rst is already the synchronised reset (the view top owns rst_s)
) (
    input  wire              ck, rst,
    input  wire [514:0]      q,
    output reg  [513:0]      od,
    output reg  [513:0]      xd,
    output reg  [1025:0]     ad,
    output wire              fault,
    // quadrant side
    output reg  [515*NQ-1:0] q_q,
    input  wire [NQ-1:0]     od_v, input wire [512*NQ-1:0] od_d, output wire [NQ-1:0] od_r,
    input  wire [NQ-1:0]     a0_v, input wire [512*NQ-1:0] a0_d, output wire [NQ-1:0] a0_r,
    input  wire              a1_v, input wire [511:0] a1_d, output wire a1_r,
    input  wire              x_v,  input wire [511:0] x_d,  output wire x_r
);
    reg [1:0] rst_s;
    always @(posedge ck or negedge rst) if (!rst) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rn = SYNC ? rst_s[1] : rst;
    // q: pin register, kept replicas (one per quadrant), quadrant registers
    reg [514:0] q_p;
    (* keep *) reg [514:0] q_rep [0:NQ-1];
    integer g;
    always @(posedge ck) begin
        q_p <= q;
        for (g = 0; g < NQ; g = g + 1) begin q_rep[g] <= q_p; q_q[515*g +: 515] <= q_rep[g]; end
    end
    // od / a0: frame-atomic merges
    wire m_od_v, m_a0_v; wire [511:0] m_od_d, m_a0_d; wire bad_od, bad_a0;
    ot_s81ph_fmerge #(.N(NQ)) u_mod (.clk(ck), .rst_n(rn), .s_v(od_v), .s_d(od_d), .s_r(od_r),
        .o_v(m_od_v), .o_d(m_od_d), .bad(bad_od));
    ot_s81ph_fmerge #(.N(NQ)) u_ma0 (.clk(ck), .rst_n(rn), .s_v(a0_v), .s_d(a0_d), .s_r(a0_r),
        .o_v(m_a0_v), .o_d(m_a0_d), .bad(bad_a0));
    // a1 / xd: single source, skid -> pin (always drained)
    wire k1_v, kx_v; wire [511:0] k1_d, kx_d;
    ot_s81ph_skid #(.W(512)) u_k1 (.clk(ck), .rst_n(rn), .i_v(a1_v), .i_d(a1_d), .i_r(a1_r), .o_v(k1_v), .o_d(k1_d), .o_r(1'b1));
    ot_s81ph_skid #(.W(512)) u_kx (.clk(ck), .rst_n(rn), .i_v(x_v), .i_d(x_d), .i_r(x_r), .o_v(kx_v), .o_d(kx_d), .o_r(1'b1));
    reg flt;
    always @(posedge ck or negedge rn) if (!rn) flt <= 1'b0; else if (bad_od || bad_a0) flt <= 1'b1;
    assign fault = flt;
    always @(posedge ck) begin
        od <= {m_od_d, m_od_v & rn, rn};
        xd <= {kx_d, kx_v & rn, rn};
        ad <= {k1_d, k1_v & rn, m_a0_d, m_a0_v & rn};
    end
endmodule
