`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE s81die-1011/ctrl svch: latency-insensitive SEAM primitives of the hierarchical scan-service slab
// (dsfd_svc_c = 4 x dsfd_svc_quad + dsfd_svc_idx).  Every inter-tile signal is a flop at both tile pins and is
// carried between tiles by relay stages (one register per <= ~450 um, the ASAP7 1.2 GHz SS repeated-wire reach),
// so no single-cycle path crosses a tile boundary and no handshake is combinational across a seam:
//   ot_s81_svch_ctx  credit SENDER  : valid/ready in (tile-internal), valid-only registered out; DEPTH credits
//                                     (= the far receiver's FIFO), +1 per returned credit pulse.
//   ot_s81_svch_rly  RELAY chain    : NR registers (valid reset, data not), one direction.  NR = 0 is wires.
//   ot_s81_svch_crx  RECEIVER FIFO  : valid-only in (never refused: the sender's credits / the issuer's landing
//                                     reservation bound the occupancy; overflow is a sticky fault), valid/ready out,
//                                     one registered credit pulse per pop.
// Full rate needs DEPTH >= 2 NR + 4 (credit round trip).  Values are moved, never transformed.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_svch_ctx #(parameter integer W = 8, parameter integer DEPTH = 8) (
    input  wire          clk, rst_n,
    input  wire          i_v,
    output wire          i_r,
    input  wire [W-1:0]  i_d,
    output reg           o_v,
    output reg  [W-1:0]  o_d,
    input  wire          c_in
);
    localparam integer CW = $clog2(DEPTH + 1);
    reg [CW-1:0] cred;
    assign i_r = cred != 0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cred <= CW'(DEPTH); o_v <= 1'b0; end
        else begin
            o_v <= i_v && i_r;
            cred <= cred - CW'(i_v && i_r) + CW'(c_in);
        end
    always @(posedge clk) o_d <= i_d;
endmodule

module ot_s81_svch_rly #(parameter integer W = 8, parameter integer NR = 1, parameter integer V = 1) (
    input  wire          clk, rst_n,
    input  wire [V-1:0]  i_v,
    input  wire [W-1:0]  i_d,
    output wire [V-1:0]  o_v,
    output wire [W-1:0]  o_d
);
    generate if (NR == 0) begin : g_w
        assign o_v = i_v; assign o_d = i_d;
    end else begin : g_r
        reg [V-1:0] v [0:NR-1];
        reg [W-1:0] d [0:NR-1];
        integer k, kd;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) for (k = 0; k < NR; k = k + 1) v[k] <= '0;
`ifdef SVCH_MUT_RLY_DROP
            else begin v[0] <= i_v & ~{V{i_d[0]}}; for (k = 1; k < NR; k = k + 1) v[k] <= v[k-1]; end   // MUTANT: beats with data bit 0 lost
`else
            else begin v[0] <= i_v; for (k = 1; k < NR; k = k + 1) v[k] <= v[k-1]; end
`endif
        always @(posedge clk) begin d[0] <= i_d; for (kd = 1; kd < NR; kd = kd + 1) d[kd] <= d[kd-1]; end
        assign o_v = v[NR-1]; assign o_d = d[NR-1];
    end endgenerate
endmodule

module ot_s81_svch_crx #(parameter integer W = 8, parameter integer DEPTH = 8) (
    input  wire          clk, rst_n,
    input  wire          i_v,
    input  wire [W-1:0]  i_d,
    output wire          o_v,
    input  wire          o_r,
    output wire [W-1:0]  o_d,
    output reg           c_out,
    output reg           ovf
);
    localparam integer AW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    reg [W-1:0] mem [0:DEPTH-1];
    reg [AW:0] cnt;
    reg [AW-1:0] wp, rp;
    assign o_v = cnt != 0;
    assign o_d = mem[rp];
    wire pop = o_v && o_r;
    always @(posedge clk) if (i_v) mem[wp] <= i_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cnt <= 0; wp <= 0; rp <= 0; c_out <= 1'b0; ovf <= 1'b0; end
        else begin
            c_out <= pop;
            if (i_v) wp <= (32'(wp) == DEPTH - 1) ? '0 : wp + 1'b1;
            if (pop) rp <= (32'(rp) == DEPTH - 1) ? '0 : rp + 1'b1;
            cnt <= cnt + (AW+1)'(i_v) - (AW+1)'(pop);
            if (i_v && !pop && 32'(cnt) >= DEPTH) ovf <= 1'b1;
        end
endmodule

// Relay STATION tile of the hierarchical slab's seams (dsfd_svc_c): NR registers on a bundle of V valid bits + W
// data bits, its own synchronised reset (valid flops only).  The slab generator places one station per <= ~450 um
// along the seam path; here a chain of NR stages is one instance.
module dsfd_svch_rly #(parameter integer W = 8, parameter integer NR = 1, parameter integer V = 1) (
    input  wire [0:0]    ck,
    input  wire [0:0]    rst,
    input  wire [V-1:0]  i_v,
    input  wire [W-1:0]  i_d,
    output wire [V-1:0]  o_v,
    output wire [W-1:0]  o_d
);
    reg [1:0] rs;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    ot_s81_svch_rly #(.W(W), .NR(NR), .V(V)) u_r (.clk(ck[0]), .rst_n(rs[1]), .i_v(i_v), .i_d(i_d), .o_v(o_v), .o_d(o_d));
endmodule

// Valid/ready relay STATION (2-slot skid, registered valid / data / ready) for the index reader's x stream.
module dsfd_svch_xstn (
    input  wire [0:0]    ck,
    input  wire [0:0]    rst,
    input  wire [0:0]    i_v, input wire [511:0] i_d, output wire [0:0] i_r,
    output wire [0:0]    o_v, output wire [511:0] o_d, input wire [0:0] o_r
);
    reg [1:0] rs;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    ot_s81ph_skid #(.W(512)) u_s (.clk(ck[0]), .rst_n(rs[1]), .i_v(i_v[0]), .i_d(i_d), .i_r(i_r[0]),
        .o_v(o_v[0]), .o_d(o_d), .o_r(o_r[0]));
endmodule

// Hold-delay stage: N inverter PAIRS per bit, each inverter its own keep_hierarchy cell (logically identity; synthesis
// cannot cancel the chain).  N = 0 is wires.  Used only where a hold-only miss on a structurally sound tile was measured.
module ot_s81_svch_hdly #(parameter integer W = 1, parameter integer N = 0) (input wire [W-1:0] a, output wire [W-1:0] y);
    generate if (N == 0) begin : g_w
        assign y = a;
    end else begin : g_d
        wire [W-1:0] st [0:2*N];
        assign st[0] = a; assign y = st[2*N];
        genvar b, n;
        for (b = 0; b < W; b = b + 1) begin : g_b
            for (n = 0; n < 2 * N; n = n + 1) begin : g_n
                ot_s81_svch_hinv u_i (.a(st[n][b]), .y(st[n+1][b]));
            end
        end
    end endgenerate
endmodule
(* keep_hierarchy = 1 *)
module ot_s81_svch_hinv (input wire a, output wire y);
    assign y = ~a;
endmodule
