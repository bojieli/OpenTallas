`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): the slice ring stop, data plane (centre leaf, gather sub-leaf, with the x streamer).
// Topology p4c (S81-DV SPEC 0b): each tier is an 8-slice bidirectional LINE on the 1,104-b E/W ports; the per-column V
// rung (276 b) is the only tier crossing.  Straps (captured pins, never parameters): sid = {tier, col}.
//
//   line deliver  every valid line beat is delivered by kind: XQ / XB -> x streamer gather (1 = from W, 2 = from E);
//                 NX -> xfin's W / E inputs (xfin forwards NX itself); CTL / RD / SC / CL -> control plane (dl_e / dl_w).
//   line forward  non-NX beats with hops > 1 leave the other side with hops - 1.
//   V rung        a V beat is lane 0 of a ring beat (header + 255-b payload).  XQ / XB beats cross as 4 fragments, lane 0
//                 first (4 cycles, SPEC tier_cross 20 per 5 beats); the receiver re-assembles them, delivers the beat to
//                 the streamer (gather source 0, as its own) and injects it on its tier line as its own.  NX and CTL are
//                 single V beats.  NX snake (S81-DV p4c): S line W -> E, up column 7's V, N line E -> W, down column 0's V;
//                 xfin's "E" side is the snake-forward side: physical E on the S tier, physical W on the N tier; the end
//                 columns carry one xfin side on V (S: col 7 E side, col 0 W side; N: col 0 E side, col 7 W side).
//                 CTL arrives on V at column 3 from the G-unit and goes to the control plane.
//   own beats     the 5 beat leaves send their x beats as 4 x 276-b fragments (V format), one leaf's beat every 4
//                 cycles (compiled stagger, equal-latency glue).  The fragments pass straight to V (column partner);
//                 the re-assembled beat is delivered to the streamer (source 0) and injected on the line both ways
//                 (E hops 7 - col, W hops col; a zero-hop side is skipped).
//   inject        per line side ONE of: forward, xfin NX (unless V-mapped), own beat, V-assembled beat, control plane.
//                 V out: ONE of own fragments, V-mapped NX, control-plane V beat.  Two sources in a cycle = sticky fault.
//                 A control-plane line beat with hops 0 takes the line default of each side (E 7 - col, W col).
// Latency: line in pin -> line out pin 2 edges a stop; V fragment in -> assembled beat on the line 2 edges after the
// 4th fragment's input flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_rstop #(
    parameter integer W = 1104,
    parameter integer V = 276
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,          // {tier, col}
    input  wire [W-1:0]    ri_w,         // E-bound beats from the W neighbour
    input  wire [W-1:0]    ri_e,         // W-bound beats from the E neighbour
    output reg  [W-1:0]    ro_e,
    output reg  [W-1:0]    ro_w,
    input  wire [V-1:0]    vi,
    output reg  [V-1:0]    vo,
    input  wire [4:0]      xf_v,         // own x-beat fragments of the 5 beat leaves (fragment valid / fragment 0)
    input  wire [4:0]      xf_s,
    input  wire [5*V-1:0]  xf,
    output wire [172:0]    nx_wi,        // xfin side ports {v, h 4, b 8, d 160}
    output wire [172:0]    nx_ei,
    input  wire [172:0]    nx_eo,
    input  wire [172:0]    nx_wo,
    output reg  [2:0]      g_v,          // gather: 0 own / V partner, 1 from W, 2 from E
    output reg  [2:0]      g_fam,
    output reg  [20:0]     g_idx,
    output reg  [3071:0]   g_d,
    output reg             dl_ev, output reg [W-1:0] dl_e,   // control plane deliveries (line E-bound / W-bound)
    output reg             dl_wv, output reg [W-1:0] dl_w,
    output reg             dl_vv, output reg [V-1:0] dl_vb,  // control plane delivery (V: CTL / SC)
    input  wire [2:0]      ci_dir,       // control plane inject {V, W, E}
    input  wire [W-1:0]    ci_b,
    output reg             fault
);
    localparam [2:0] K_CTL = 3'd0, K_XQ = 3'd1, K_XB = 3'd2, K_NX = 3'd3;
    // ---------------------------------------------------------------- input flops
    reg [W-1:0] iw, ie, ci_q; reg [V-1:0] iv; reg [4:0] xfv_q, xfs_q; reg [5*V-1:0] xf_q; reg [172:0] neo_q, nwo_q; reg [2:0] cid_q; reg [3:0] sid_c;
    always @(posedge clk) begin
        iw <= ri_w; ie <= ri_e; iv <= vi; xfs_q <= xf_s; xf_q <= xf; neo_q <= nx_eo; nwo_q <= nx_wo; ci_q <= ci_b; cid_q <= ci_dir; sid_c <= sid;
    end
    wire [2:0] col = sid_c[2:0]; wire tier = sid_c[3];          // tier 0 = S, 1 = N
    wire map_e = tier ? col == 3'd0 : col == 3'd7;              // xfin side carried by V (snake end columns)
    wire map_w = tier ? col == 3'd7 : col == 3'd0;
    wire [4:0] h_e = 5'd7 - {2'd0, col}, h_w = {2'd0, col};
    wire iw_v = iw[0], ie_v = ie[0];
    wire [2:0] iw_k = iw[3:1], ie_k = ie[3:1];
    wire [4:0] iw_h = iw[8:4], ie_h = ie[8:4];
    // own fragments (at most one leaf a cycle): merged, passed to V, assembled into the own beat
    always @(posedge clk or negedge rst_n) if (!rst_n) xfv_q <= 5'd0; else xfv_q <= xf_v;
    reg ofv, ofs; reg [V-1:0] of; reg [2:0] nown; integer k;
    always @(*) begin
        ofv = 1'b0; ofs = 1'b0; of = {V{1'b0}}; nown = 3'd0;
        for (k = 0; k < 5; k = k + 1)
            if (xfv_q[k]) begin ofv = 1'b1; ofs = ofs | xfs_q[k]; of = of | xf_q[k * V +: V]; nown = nown + 3'd1; end
    end
    reg [1:0] on_n; reg [3 * V - 1:0] on_b; reg own_v; reg [W-1:0] own;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin on_n <= 2'd0; own_v <= 1'b0; end
        else begin
            own_v <= ofv && !ofs && on_n == 2'd3;
            if (ofv) on_n <= ofs ? 2'd1 : on_n + 2'd1;
        end
    always @(posedge clk) begin
        if (ofv && ofs) on_b[V-1:0] <= of;
        else if (ofv && on_n != 2'd3) on_b[on_n * V +: V] <= of;
        if (ofv && !ofs && on_n == 2'd3) own <= {of, on_b};
    end
    // ---------------------------------------------------------------- V receive: single beats and fragment assembly
    wire iv_v = iv[0]; wire [2:0] iv_k = iv[3:1];
    reg [1:0] fr_n; reg fr_on; reg [W-1:0] fr_b; reg asm_v; reg [W-1:0] asm_b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fr_on <= 1'b0; fr_n <= 2'd0; asm_v <= 1'b0; end
        else begin
            asm_v <= 1'b0;
            if (fr_on) begin
                fr_n <= fr_n + 2'd1;
                if (fr_n == 2'd3) begin fr_on <= 1'b0; asm_v <= 1'b1; end
            end else if (iv_v && (iv_k == K_XQ || iv_k == K_XB)) begin fr_on <= 1'b1; fr_n <= 2'd1; end
        end
    always @(posedge clk) begin
        if (!fr_on) fr_b[V-1:0] <= iv; else fr_b[fr_n * V +: V] <= iv;
        if (fr_on && fr_n == 2'd3) asm_b <= {iv, fr_b[3 * V - 1:0]};
    end
    wire v_nx = iv_v && iv_k == K_NX && !fr_on, v_cs = iv_v && iv_k != K_XQ && iv_k != K_XB && iv_k != K_NX && !fr_on;
    // ---------------------------------------------------------------- V send: own fragments, V-mapped NX, control plane
    wire nxv_out = (map_e && neo_q[172]) || (map_w && nwo_q[172]);
    wire [172:0] nxv_f = (map_e && neo_q[172]) ? neo_q : nwo_q;
    function automatic [W-1:0] hdr(input [W-1:0] b, input [4:0] h, input [3:0] s);
        begin hdr = b; hdr[8:4] = h; hdr[12:9] = s; end
    endfunction
    function automatic [W-1:0] nxb(input [172:0] f, input [3:0] s);
        begin nxb = {W{1'b0}}; nxb[0] = 1'b1; nxb[3:1] = K_NX; nxb[8:4] = {1'b0, f[171:168]}; nxb[12:9] = s;
              nxb[20:13] = f[167:160]; nxb[21 +: 160] = f[159:0]; end
    endfunction
    wire [W-1:0] nxv_b = nxb(nxv_f, sid_c);
    wire [2:0] sv = ofv + nxv_out + (ci_q[0] && cid_q[2]);
    // the leaves' fragment 0 already carries hops 1 and src (vq): the V partner delivers it and re-injects as its own
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vo <= {V{1'b0}};
        else vo <= ofv ? of : nxv_out ? nxv_b[V-1:0] : (ci_q[0] && cid_q[2]) ? ci_q[V-1:0] : {V{1'b0}};
    // ---------------------------------------------------------------- line output selection
    wire fe = iw_v && iw_k != K_NX && iw_h > 5'd1;
    wire fw = ie_v && ie_k != K_NX && ie_h > 5'd1;
    // xfin NX onto the physical line: E port carries eo on the S tier, wo on the N tier (and W port the other)
    wire [172:0] nx_pe = tier ? nwo_q : neo_q, nx_pw = tier ? neo_q : nwo_q;
    wire ne = tier ? (nwo_q[172] && !map_w) : (neo_q[172] && !map_e);
    wire nw = tier ? (neo_q[172] && !map_e) : (nwo_q[172] && !map_w);
    wire oe = own_v && h_e != 5'd0, ow = own_v && h_w != 5'd0;
    wire ae = asm_v && h_e != 5'd0, aw = asm_v && h_w != 5'd0;
    wire ce = ci_q[0] && cid_q[0], cw = ci_q[0] && cid_q[1];
    wire [2:0] se = fe + ne + oe + ae + ce, sw_ = fw + nw + ow + aw + cw;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ro_e <= {W{1'b0}}; ro_w <= {W{1'b0}}; fault <= 1'b0; end
        else begin
            ro_e <= fe ? hdr(iw, iw_h - 5'd1, iw[12:9]) : ne ? nxb(nx_pe, sid_c) : oe ? hdr(own, h_e, sid_c) :
                    ae ? hdr(asm_b, h_e, sid_c) : ce ? ((ci_q[8:4] == 5'd0) ? hdr(ci_q, h_e, sid_c) : ci_q) : {W{1'b0}};
            ro_w <= fw ? hdr(ie, ie_h - 5'd1, ie[12:9]) : nw ? nxb(nx_pw, sid_c) : ow ? hdr(own, h_w, sid_c) :
                    aw ? hdr(asm_b, h_w, sid_c) : cw ? ((ci_q[8:4] == 5'd0) ? hdr(ci_q, h_w, sid_c) : ci_q) : {W{1'b0}};
            if (se > 3'd1 || sw_ > 3'd1 || nown > 3'd1 || sv > 3'd1 || (own_v && asm_v)) fault <= 1'b1;
        end
    // ---------------------------------------------------------------- deliveries (registered)
    reg nxw_v, nxe_v; reg [171:0] nxw_d, nxe_d;
    assign nx_wi = {nxw_v, nxw_d}; assign nx_ei = {nxe_v, nxe_d};
    // xfin wi = snake-forward arrivals (from physical W on S, from physical E on N); ei the other way
    wire xw_nx = tier ? (ie_v && ie_k == K_NX) : (iw_v && iw_k == K_NX);
    wire xe_nx = tier ? (iw_v && iw_k == K_NX) : (ie_v && ie_k == K_NX);
    wire [W-1:0] xwb = tier ? ie : iw, xeb = tier ? iw : ie;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin g_v <= 3'b000; dl_ev <= 1'b0; dl_wv <= 1'b0; dl_vv <= 1'b0; nxw_v <= 1'b0; nxe_v <= 1'b0; end
        else begin
            g_v <= {ie_v && (ie_k == K_XQ || ie_k == K_XB), iw_v && (iw_k == K_XQ || iw_k == K_XB),
                    (own_v && (own[3:1] == K_XQ || own[3:1] == K_XB)) || asm_v};
            dl_ev <= iw_v && iw_k != K_XQ && iw_k != K_XB && iw_k != K_NX;
            dl_wv <= ie_v && ie_k != K_XQ && ie_k != K_XB && ie_k != K_NX;
            dl_vv <= v_cs;
            nxw_v <= map_w ? v_nx : xw_nx;
            nxe_v <= map_e ? v_nx : xe_nx;
        end
    wire [W-1:0] g0 = asm_v ? asm_b : own;
    always @(posedge clk) begin
        g_fam <= {ie_k == K_XB, iw_k == K_XB, g0[3:1] == K_XB};
        g_idx <= {ie[19:13], iw[19:13], g0[19:13]};
        g_d <= {ie[21 +: 1024], iw[21 +: 1024], g0[21 +: 1024]};
        dl_e <= iw; dl_w <= ie; dl_vb <= iv;
        nxw_d <= map_w ? {iv[7:4], iv[20:13], iv[21 +: 160]} : {xwb[7:4], xwb[20:13], xwb[21 +: 160]};
        nxe_d <= map_e ? {iv[7:4], iv[20:13], iv[21 +: 160]} : {xeb[7:4], xeb[20:13], xeb[21 +: 160]};
    end
endmodule
