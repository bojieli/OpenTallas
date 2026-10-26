`timescale 1ns/1ps
`default_nettype none
// ot_hgi_quant_wide_h write quad (el1011-hbm-fq, 2026-10-11): hardened sub-tile, 8 per engine on the lane-group write face.
// Takes the registered result beat (32 x 16 b) and per-lane {valid, one-hot slot, sector} from the centre and drives the
// 4 lanes' write-request output flops ({v, sector 15, data 256 = 8 words {y16, 16'h0}, mask 8'hff}); returns write
// credits and write-done events through registered outputs.  Valids reset, data free-running; production defaults only.
module ot_hgi_qw_wq (
    input  wire              clk,
    input  wire              rst_n,
    // lanes
    output reg  [4*280-1:0]  wwq,
    input  wire [3:0]        wwq_cr,
    input  wire [3:0]        wwq_done,
    // centre -> tile
    input  wire [511:0]      c_y,
    input  wire [3:0]        c_v,
    input  wire [4*4-1:0]    c_slot,
    input  wire [4*15-1:0]   c_sec,
    // tile -> centre
    output reg  [3:0]        e_wcr,
    output reg  [3:0]        e_done
);
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg [511:0] i_y; reg [3:0] i_v, p_cr, p_done; reg [3:0] i_slot [0:3]; reg [14:0] i_sec [0:3];
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin i_v <= 0; p_cr <= 0; p_done <= 0; e_wcr <= 0; e_done <= 0; end
        else begin i_v <= c_v; p_cr <= wwq_cr; p_done <= wwq_done; e_wcr <= p_cr; e_done <= p_done; end
    always @(posedge clk) begin
        i_y <= c_y;
        for (integer i = 0; i < 4; i = i + 1) begin i_slot[i] <= c_slot[i*4 +: 4]; i_sec[i] <= c_sec[i*15 +: 15]; end
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) for (integer i = 0; i < 4; i = i + 1) wwq[i*280 + 279] <= 1'b0;
        else for (integer i = 0; i < 4; i = i + 1) wwq[i*280 + 279] <= i_v[i];
    always @(posedge clk)
        for (integer i = 0; i < 4; i = i + 1) begin
            reg [255:0] d; d = '0;
            for (integer s = 0; s < 4; s = s + 1)
                if (i_slot[i][s])
                    for (integer k = 0; k < 8; k = k + 1) d[k*32 +: 32] = d[k*32 +: 32] | {i_y[(s*8 + k)*16 +: 16], 16'd0};
            wwq[i*280 +: 279] <= {i_sec[i], d, 8'hff};
        end
endmodule
`default_nettype wire
