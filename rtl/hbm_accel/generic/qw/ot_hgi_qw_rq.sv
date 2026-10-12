`timescale 1ns/1ps
`default_nettype none
// ot_hgi_quant_wide_h read quad (el1011-hbm-fq, 2026-10-11): hardened sub-tile, 8 per engine on the lane-group read face.
// Lanes 4q..4q+3: response pin flops, per-lane LD-deep response FIFOs, the quad's gather register (4 beat slots x 256 b,
// zero where none of its lanes pops) and the per-lane read-request output flops.  Every port is registered on the tile
// side; the centre sends registered hit vectors and per-lane sectors / one-hot slots (no shared select inside the tile);
// datapath registers carry no reset (valids / pointers only, through a local reset relay).  Production defaults only (the
// hardened view is a liberty blackbox: no parameter overrides at the instance).
module ot_hgi_qw_rq #(
    parameter integer LD = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    // lanes
    input  wire [4*257-1:0]  wrr,         // {v, sector data 256} per lane
    output reg  [4*16-1:0]   wrq,         // {v, sector 15} per lane
    input  wire [3:0]        wrq_cr,
    // centre -> tile
    input  wire [3:0]        c_hit_r,     // read request issued on lane i
    input  wire [4*15-1:0]   c_sec,       // its sector
    input  wire [3:0]        c_hit_p,     // pop lane i's FIFO head into ...
    input  wire [4*4-1:0]    c_slot,      // ... one-hot beat slot
    // tile -> centre
    output reg  [1023:0]     gq,          // gathered slots (OR-combined across quads by the centre)
    output reg  [3:0]        e_push,      // a response landed in lane i's FIFO
    output reg  [3:0]        e_rcr        // read credit returned on lane i
);
    localparam integer LW = $clog2(LD);
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    // input registers (valids reset, data free-running)
    reg [3:0] p_v, p_cr, i_hit_r, i_hit_p;
    reg [255:0] p_d [0:3];
    reg [14:0] i_sec [0:3];
    reg [3:0] i_slot [0:3];
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin p_v <= 0; p_cr <= 0; i_hit_r <= 0; i_hit_p <= 0; end
        else for (integer i = 0; i < 4; i = i + 1) begin
            p_v[i] <= wrr[i*257 + 256]; p_cr[i] <= wrq_cr[i]; i_hit_r[i] <= c_hit_r[i]; i_hit_p[i] <= c_hit_p[i];
        end
    always @(posedge clk)
        for (integer i = 0; i < 4; i = i + 1) begin
            p_d[i] <= wrr[i*257 +: 256]; i_sec[i] <= c_sec[i*15 +: 15]; i_slot[i] <= c_slot[i*4 +: 4];
        end
    // per-lane FIFOs
    reg [255:0] lf [0:3][0:LD-1];
    reg [LW-1:0] lf_h [0:3], lf_t [0:3];
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin
            for (integer i = 0; i < 4; i = i + 1) begin lf_h[i] <= 0; lf_t[i] <= 0; end
            e_push <= 0; e_rcr <= 0;
        end else begin
            for (integer i = 0; i < 4; i = i + 1) begin
                if (p_v[i]) lf_t[i] <= lf_t[i] + 1'b1;
                if (i_hit_p[i]) lf_h[i] <= lf_h[i] + 1'b1;
            end
            e_push <= p_v; e_rcr <= p_cr;
        end
    always @(posedge clk)
        for (integer i = 0; i < 4; i = i + 1) if (p_v[i]) lf[i][lf_t[i]] <= p_d[i];
    // gather (free-running): lane i's head into its one-hot slot when popped
    always @(posedge clk) begin
        reg [1023:0] a; a = '0;
        for (integer i = 0; i < 4; i = i + 1)
            for (integer s = 0; s < 4; s = s + 1)
                if (i_hit_p[i] && i_slot[i][s]) a[s*256 +: 256] = a[s*256 +: 256] | lf[i][lf_h[i]];
        gq <= a;
    end
    // read-request output flops (valid reset, sector free-running)
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) for (integer i = 0; i < 4; i = i + 1) wrq[i*16 + 15] <= 1'b0;
        else for (integer i = 0; i < 4; i = i + 1) wrq[i*16 + 15] <= i_hit_r[i];
    always @(posedge clk)
        for (integer i = 0; i < 4; i = i + 1) wrq[i*16 +: 15] <= i_sec[i];
endmodule
`default_nettype wire
