`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SMWIRE (10-19): the die wiring of the per-head SO target dsdv_sm_so_target inside every dsdv_svc_rs_c.
// Three small leaves of the svc_rs slice (all static, no ready / credit; every violation is a sticky fault, never a
// stall or a reschedule):
//
//   dsdv_svc_sot  the target's CONFIG SOURCE.  The compiler emits one SOT frame (svc frame type 14, len 2) on the
//                 half's q stream right after the job's WIN_LOAD: the authority comes from the job descriptor (owner
//                 tag / user = the WIN_LOAD's, checked here; epoch = the host allocation epoch) and the static calendar
//                 (per-head SO write window, read and retire edges, the entry's gather window).  It rides the existing
//                 dn tree (5 edges a hop, the same per-slice age as every SMJ frame of the job), so config and SMJ rows
//                 keep equal paid ages at every slice.  Header [83:0]:
//                   [19:0] owner {epoch 2, user 10, tag 8}  [27:20] SE jid  [35:28] SO jid  [49:36] obase
//                   [51:50] route of this half's gather beats at the C3 band slice (1 = tier line E+W + own XS,
//                           2 = V rung: 4 fragments to the column partner, which delivers and fans out on its line)
//                   [67:52] entry gather window first edge  [83:68] last edge (entry slice only; cycles after install)
//                 payload word 0: head t's {SO-write last 16, first 16} at [32 t +: 32]
//                 payload word 1: head t's {retire 16, read 16} at [32 t +: 32]
//                 cfg_v pulses on the edge after payload word 1 (the target's pin flop captures it one edge later).
//   dsdv_sm_gw    the GATHER WORD serializer: one 1024-b target beat (g_v, every 4 edges, 8 a head) -> 3 words of the
//                 half's P.V return tree (513 b, the existing child -> parent lanes, 5 edges a hop, compiled windows):
//                   lo {0, d[511:0]}, hi {0, d[1023:512]}, hdr {1, 473'd0, magic 8'h5A, owner 20, head 4, group, idx 7}
//                 on the 3 edges after g_v.  A beat while the previous one is still serialising is a fault.
//   dsdv_sm_gx    the ENTRY STAMP: marks the entry's pv words inside the booked gather window as SO gather words in the
//                 48 spare bits of the existing 562-b pv lane (pv_x[47] = SO, pv_x[44:43] = route), so the landing
//                 (dsfd_dvland_pvrd) passes them to the C3 slice's band port unchanged instead of counting them as P.V.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_sot #(parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,          // landed slice reset (rn)
    input  wire [3:0]   tile,           // the slice's head (role tile, static)
    input  wire         q_v,
    input  wire [511:0] q_d,
    output reg          cfg_v,
    output reg  [19:0]  cfg_owner,
    output reg  [7:0]   cfg_se_jid, cfg_so_jid,
    output reg  [13:0]  cfg_obase,
    output reg  [15:0]  cfg_first, cfg_last, cfg_read, cfg_retire,
    output reg  [1:0]   route,
    output reg  [15:0]  gw_first, gw_last,
    output reg  [2:0]   fault_code
);
    // frame parser (svc frame protocol v1.1 header, as dsdv_svc_att)
    wire [3:0]  h_type = q_d[511:508];
    wire        h_mine = q_d[503];
    wire [11:0] h_len  = q_d[491:480];
    reg in_frame, f_sot; reg [11:0] left; reg [1:0] f_idx;
    wire is_hdr = q_v && !in_frame, is_pay = q_v && in_frame;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin in_frame <= 1'b0; left <= 12'd0; f_sot <= 1'b0; f_idx <= 2'd0; end
        else if (is_hdr) begin
            in_frame <= h_len != 12'd0; left <= h_len; f_sot <= h_mine && h_type == 4'd14; f_idx <= 2'd0;
        end else if (is_pay) begin
            left <= left - 12'd1; if (left == 12'd1) in_frame <= 1'b0;
            if (f_idx != 2'd3) f_idx <= f_idx + 2'd1;
        end
    wire sot_hdr = is_hdr && h_mine && h_type == 4'd14;
    // the job descriptor's owner: the last WIN_LOAD (type 2) tag / user
    reg wl_seen; reg [7:0] wl_tag; reg [9:0] wl_user;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wl_seen <= 1'b0; wl_tag <= 8'd0; wl_user <= 10'd0; end
        else if (is_hdr && h_mine && h_type == 4'd2) begin wl_seen <= 1'b1; wl_tag <= q_d[502:495]; wl_user <= q_d[458:449]; end
    // header fields, then the head's two payload fields (fixed 32-b select by the static tile strap)
    reg [83:0] hd; reg [31:0] p0; reg pend0, pend1;
    wire [31:0] mine = q_d[32 * tile +: 32];
    wire own_bad = !wl_seen || q_d[7:0] != wl_tag || q_d[17:8] != wl_user;
    always @(posedge clk) begin
        if (sot_hdr) hd <= q_d[83:0];
        if (is_pay && f_sot && f_idx == 2'd0) p0 <= mine;
        if (is_pay && f_sot && f_idx == 2'd1) begin
            cfg_owner <= hd[19:0]; cfg_se_jid <= hd[27:20]; cfg_so_jid <= hd[35:28]; cfg_obase <= hd[49:36];
            route <= hd[51:50]; gw_first <= hd[67:52]; gw_last <= hd[83:68];
            cfg_first <= p0[15:0]; cfg_last <= p0[31:16]; cfg_read <= mine[15:0]; cfg_retire <= mine[31:16];
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cfg_v <= 1'b0; fault_code <= 3'd0; end
        else begin
            cfg_v <= is_pay && f_sot && f_idx == 2'd1 && !(|fault_code);
            if (sot_hdr && h_len != 12'd2) fault_code[0] <= 1'b1;   // SOT is exactly header + 2 words
            if (sot_hdr && own_bad) fault_code[1] <= 1'b1;          // config owner is not the accepted descriptor's
            if (sot_hdr && (q_d[51:50] == 2'd0 || q_d[51:50] == 2'd3)) fault_code[2] <= 1'b1;   // no / two routes
        end
endmodule

module dsdv_sm_gw (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    head,
    input  wire          g_v,
    input  wire [6:0]    g_idx,
    input  wire [1023:0] g_d,
    input  wire [19:0]   g_owner,
    input  wire          g_group,
    output reg           gw_v,
    output reg  [512:0]  gw_d,
    output reg           fault
);
    reg [1:0] n;                        // 0 idle, 1 hi next, 2 hdr next
    reg [511:0] hi; reg [31:0] h;
    always @(posedge clk) if (g_v) begin hi <= g_d[1023:512]; h <= {g_owner, head, g_group, g_idx}; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin n <= 2'd0; gw_v <= 1'b0; fault <= 1'b0; end
        else begin
            gw_v <= g_v || n != 2'd0;
            if (g_v && n != 2'd0) fault <= 1'b1;
            n <= g_v ? 2'd1 : (n == 2'd1) ? 2'd2 : 2'd0;
        end
    always @(posedge clk)
`ifdef OT_SMWIRE_MUT_ORDER
        gw_d <= g_v ? {1'b0, hi} : (n == 2'd1) ? {1'b0, g_d[511:0]} : {1'b1, 473'd0, 8'h5A, h};   // mutant: lo / hi swap
`else
        gw_d <= g_v ? {1'b0, g_d[511:0]} : (n == 2'd1) ? {1'b0, hi} : {1'b1, 473'd0, 8'h5A, h};
`endif
endmodule

// entry stamp: pv_x for the pv word leaving on the same edge (registered beside pv_v / pv_d)
module dsdv_sm_gx (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        cfg_v,          // SOT config of this (entry) slice
    input  wire [1:0]  route,
    input  wire [15:0] gw_first, gw_last,
    input  wire        w_v,            // the pv word of this edge (registered into pv_v on the same edge)
    output reg  [47:0] pv_x
);
    reg on; reg [15:0] cyc, f0, f1; reg [1:0] rt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin on <= 1'b0; cyc <= 16'd0; end
        else if (cfg_v) begin on <= 1'b1; cyc <= 16'd0; end
        else if (on) begin cyc <= cyc + 16'd1; if (cyc == f1) on <= 1'b0; end
    always @(posedge clk) if (cfg_v) begin f0 <= gw_first; f1 <= gw_last; rt <= route; end
    wire in_w = on && cyc >= f0 && cyc <= f1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) pv_x <= 48'd0;
        else pv_x <= (w_v && in_w) ? {1'b1, 2'b00, rt, 43'd0} : 48'd0;
endmodule
