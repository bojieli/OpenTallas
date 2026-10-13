`timescale 1ns/1ps
`default_nettype none
// ot_hgi_qdq_q ASSEMBLY child (q8b four-leaf partition, 2026-10-13; in the lane-pair column | decoder gap, so the 2,048
// popped-head wires and the 1,153 decode-input wires are short): issued-beat queue, lane occupancy, pop decision, the
// registered select pipeline and the 8-lane -> 4-position beat placement.  Every port is a flop at the pin:
//   in : bp (issued beats from the core leaf), e_push / e_ovf / hq from the lane-pair tiles, i_wf (one pulse a written
//        result: result-FIFO space comes back two edges after the write, conservative).
//   out: c_pop (lane-pair tiles), d_v / d_hd / d_x (decode tiles), o_pop / o_fire (core: lane and beat-queue space),
//        m {O sector 15, sectors 3, last 1} a fired beat (write leaf; the 26-cycle decode hides its two edges), sticky
//        lane-overrun fault and idle to both, reset relays for the lane-pair tiles, the decode tiles and the write leaf.
// The e_push pin flop is used as look-ahead (lf_n != 0 || f_push): the pop decision is on the same cycle as before.
// Pop pipeline: l_fire -> c_pop (1) -> tile i_pop (2) -> tile hq (3) -> hq_f (4) -> d_x (5).
// MUT (bench): 1 = assembly takes sector j from lane j ^ 1 (lane-to-sector map; must FAIL).
module ot_hgi_qdq_asm #(
    parameter integer LD  = 16,
    parameter integer NB  = 32,
    parameter integer OD  = 64,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              bp_v,
    input  wire [39:0]       bp,          // {lane 3, sectors 3, O sector 15, last, header 18}
    input  wire [511:0]      hq_p0,       // popped heads, one port a lane-pair tile (its own pin face)
    input  wire [511:0]      hq_p1,
    input  wire [511:0]      hq_p2,
    input  wire [511:0]      hq_p3,
    input  wire [7:0]        e_push,
    input  wire [3:0]        e_ovf,
    output reg  [7:0]        c_pop,
    output wire [3:0]        lq_rst_n,    // one relay flop a lane-pair tile
    output wire              dec_rst_n,
    output wire              wr_rst_n,
    output reg               d_v,
    output reg  [17:0]       d_hd,        // {unit 4, op 6, block 8}: header[127:118], header[71:64]
    output reg  [1023:0]     d_x,
    output reg  [7:0]        o_pop,
    output reg               o_fire,
    output reg               o_bad_c,
    output reg               o_idle,
    output reg               m_v,
    output reg  [18:0]       m,
    output reg               o_bad_w,
    input  wire              i_wf
);
    localparam integer SW = $clog2(NB), OW = $clog2(OD), LW = $clog2(LD);
    reg f_rst; always @(posedge clk) f_rst <= rst_n;
    wire [6:0] rr_n;                                  // 0 local, 1 decode tiles, 2 write leaf, 3-6 lane-pair tiles
    ot_rst_relay #(.REGIONS(7)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    assign lq_rst_n = rr_n[6:3]; assign dec_rst_n = rr_n[1]; assign wr_rst_n = rr_n[2];
    // pin flops
    reg f_bp_v, f_wf; reg [39:0] f_bp; reg [7:0] f_push; reg [3:0] f_ovf;
    reg [8*256-1:0] hq_f;
    always @(posedge clk) begin f_bp <= bp; hq_f <= {hq_p3, hq_p2, hq_p1, hq_p0}; end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin f_bp_v <= 0; f_wf <= 0; f_push <= 0; f_ovf <= 0; end
        else begin f_bp_v <= bp_v; f_wf <= i_wf; f_push <= e_push; f_ovf <= e_ovf; end
    // issued-beat queue
    reg [2:0] bq_l [0:NB-1], bq_n [0:NB-1]; reg [14:0] bq_o [0:NB-1]; reg bq_z [0:NB-1]; reg [17:0] bq_hd [0:NB-1];
    reg [SW-1:0] b_t, b_h; reg [SW:0] b_used;
    reg [LW:0] lf_n [0:7];                            // lane occupancy (pushes seen one edge ago and older)
    reg [OW:0] resv;                                  // fired, write not yet seen (result FIFO space)
    wire [2:0] h_l = bq_l[b_h], h_n = bq_n[b_h];
    reg [7:0] h_hit; reg h_ok; reg [1023:0] h_x;
    reg s1_lv, s2_lv, s3_lv, s4_lv; reg [2:0] s1_l, s2_l, s3_l, s4_l, s1_n, s2_n, s3_n, s4_n; reg [17:0] s1_hd, s2_hd, s3_hd, s4_hd;
    always @* begin
        h_ok = b_used != 0; h_x = '0;
        for (integer b = 0; b < 8; b = b + 1) begin
            h_hit[b] = 3'(b - h_l) < h_n;
            if (h_hit[b] && lf_n[b] == 0 && !f_push[b]) h_ok = 1'b0;
        end
        for (integer j = 0; j < 4; j = j + 1) begin
            reg [2:0] l; l = 3'(s4_l + ((MUT == 1) ? (j ^ 1) : j));
            for (integer b = 0; b < 8; b = b + 1)
                h_x[j*256 +: 256] = h_x[j*256 +: 256] | ({256{j < s4_n && l == 3'(b)}} & hq_f[b*256 +: 256]);
        end
    end
    wire l_fire = h_ok && resv != OD[OW:0];
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            b_t <= 0; b_h <= 0; b_used <= 0; resv <= 0; d_v <= 0; s1_lv <= 0; s2_lv <= 0; s3_lv <= 0; s4_lv <= 0;
            c_pop <= 0; o_pop <= 0; o_fire <= 0; m_v <= 0; o_bad_c <= 0; o_bad_w <= 0; o_idle <= 0;
            for (integer b = 0; b < 8; b = b + 1) lf_n[b] <= 0;
        end else begin
            s1_lv <= l_fire; s2_lv <= s1_lv; s3_lv <= s2_lv; s4_lv <= s3_lv; d_v <= s4_lv;
            o_fire <= l_fire; m_v <= l_fire;
            if (f_bp_v) b_t <= b_t + 1'b1;
            if (l_fire) b_h <= b_h + 1'b1;
            b_used <= b_used + (SW+1)'(f_bp_v) - (SW+1)'(l_fire);
            resv <= resv + (OW+1)'(l_fire) - (OW+1)'(f_wf);
            for (integer b = 0; b < 8; b = b + 1) begin : lanes
                reg pop; pop = l_fire && h_hit[b];
                c_pop[b] <= pop; o_pop[b] <= pop;
                lf_n[b] <= lf_n[b] + (LW+1)'(f_push[b]) - (LW+1)'(pop);
            end
            if (f_ovf != 0) begin o_bad_c <= 1'b1; o_bad_w <= 1'b1; end
            o_idle <= b_used == 0 && !f_bp_v && !s1_lv && !s2_lv && !s3_lv && !s4_lv && !d_v;
        end
    end
    always @(posedge clk) begin
        if (f_bp_v) begin
            bq_l[b_t] <= f_bp[39:37]; bq_n[b_t] <= f_bp[36:34]; bq_o[b_t] <= f_bp[33:19]; bq_z[b_t] <= f_bp[18];
            bq_hd[b_t] <= f_bp[17:0];
        end
        s1_l <= h_l; s1_n <= h_n; s1_hd <= bq_hd[b_h];
        s2_l <= s1_l; s2_n <= s1_n; s2_hd <= s1_hd; s3_l <= s2_l; s3_n <= s2_n; s3_hd <= s2_hd; s4_l <= s3_l; s4_n <= s3_n; s4_hd <= s3_hd;
        // Decoder consumes data only when d_v: no 2k-load data enable is needed.
        d_x <= h_x; d_hd <= s4_hd;
        m <= {bq_o[b_h], h_n, bq_z[b_h]};
    end
    initial if ((NB & (NB - 1)) != 0 || (OD & (OD - 1)) != 0 || (LD & (LD - 1)) != 0) $fatal(1, "ot_hgi_qdq_asm: NB / OD / LD powers of two");
endmodule
`default_nettype wire
