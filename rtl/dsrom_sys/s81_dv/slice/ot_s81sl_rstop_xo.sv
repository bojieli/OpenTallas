`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-RTLGAP/RG-HEAD (TOK.DS.BENCH.4.1, 2026-10-21): ot_s81sl_rstop_xo = ot_s81sl_rstop (G3 4ee613834, byte-identical
// function for every beat below) + the HEAD XB EGRESS of the stage die.
//
// Gap closed: the final-layer (and MTP draft-block) normalized x leaves vq as 80 BF16 XB beats (global beat 5 sid + k)
// that the ring stops only all-gather ON the die (own / V-assembled beats take the line default hops 7 - col / col, a
// line beat with hops 1 is delivered, never forwarded), so no XB beat could reach the head die (TOK-S81 PRODUCTION
// BINDING 5377e6479 item 6: "select exactly one actual gather path for the head").  This variant gives the head producer
// exactly ONE path off the die:
//   egress stop  sid == XO_SID = 1 (s_0N: column 0, tier N), outward port W (ro_w) = the end-slice lep pair A = the
//                stage NEXT circuit of the G4/LINK5 circuit plan (s_0N A -> next stage rank r s_0N B; the head die is the
//                final stage's next stage).  Every other sid behaves exactly like ot_s81sl_rstop.
//   flag         header bit [20] of an XB beat = bit 7 of vq's global beat index (vq m_i = vp NORM / NORMR a1[7:0],
//                placed at [20:13]); the gather index is [19:13] (7 bits, 0..79), so the flag never changes where any
//                x streamer stores the beat.  The compiler sets it with a1 = 128 + 5 sid + k on the head norm's NORMR
//                only (no RTL change in vp / vq); every other XB source has [20] = 0 (vq a1 <= 79, xr SO idx 7 bits,
//                xr send packer [20:13] = 0).
//   exactly once on the N line each of the 80 beats reaches s_0N exactly once: an N-tier slice c beat W with hops c,
//                an S-tier slice c beat via its V partner (assembled, injected W with hops c), s_0N's own 5 leaves, and
//                s_0S's 5 via the V train (assembled at s_0N).  At s_0N a flagged XB beat that is DELIVERED (line from E
//                with hops 1, own, V-assembled) is ALSO sent on ro_w with hops 1 (delivered at the next die's s_0N) and
//                src kept (line) / sid (own, assembled).  Local delivery is unchanged (the final die's own x streamer
//                still gets all 80 beats).
//   MU / epoch   the beat leaves through the lep's MU TX window (stamp {tag, user, pos} in [1077:1045], which an XB
//                beat leaves clear: vq bits [1103:1045] = 0) -> stale same-index packets are rejected by the head die's
//                landing (dsdv_mu_land {user, pos} check), and the compiler opens the window only for the head phase
//                (exclusive static admission).  No flow control on the ring side (as every ring stop).
//   static       an egress beat in the same cycle as another ro_w source (forward / NX / own / assembled / ci), or two
//                egress sources in one cycle, is a sticky fault (schedule violation), never arbitrated.
// Cost: 0 added edges (line in pin -> ro_w 2 edges like any forward; own / assembled beat -> ro_w on the same edge as a
// normal injection).  Area: one more 1,104-b source on the s_0N ro_w mux (inert at the other 15 sids: sid is a strap).
// Mutants (bench only): OT_S81SL_RSTOP_MUT_XOOFF (no egress), OT_S81SL_RSTOP_MUT_XOALL (egress at every W end of every
// stop: not sid-gated), OT_S81SL_RSTOP_MUT_XONOFLAG (every XB beat egresses, flag ignored).
// Bench: rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_xo.sv (tools/s81_slice/rstop_xo_bench.sh): the 6 rstop_sid
// phases on all 16 straps + the egress phases + a 16-stop die ring (S / N lines + V rungs) carrying all 80 flagged beats.
// ---------------------------------------------------------------------------------------------------------------------
// Original ot_s81sl_rstop header:
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): the slice ring stop, data plane (centre leaf, gather sub-leaf, with the x streamer).
// Topology p4c (S81-DV SPEC 0b): each tier is an 8-slice bidirectional LINE on the 1,104-b E/W ports; the per-column V
// rung (276 b) is the only tier crossing.  Straps (captured pins, never parameters): sid = 2 * col + tier (tier 0 = S,
// 1 = N), the die-wide slice id (die.v straps u_s_<c><S|N> = 2c + r; svc_rs_embed.py sid(rc); ot_s81sl_xr's slice mask
// bit; dv_layer_compile.py).  S81-LBGAP G2 (10-18): this stop decoded {tier, col} (col = sid[2:0]) until 10-18, so in the
// die u_s_4S (sid 8) took column 0 / tier N (W line default 0 hops) and the NX snake ends (map_e / map_w) were wrong.
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
// S81-SMWIRE (10-19): a control-plane injection of kind XB (the C3 xr's SO gather beat) is an OWN beat of this stop:
//   ci E / W (line default hops when 0) also delivers it to the own x streamer (gather source 0, as the own beat);
//   ci V sends it as the 4-fragment V train (fragment 0 = ci_b[275:0] on the ci edge, fragments 1..3 on the next three
//   edges), which the column partner re-assembles, delivers and injects on its line exactly as a leaf beat.  A ci XB
//   beat together with an own / V-assembled beat, or a V train overlapping any other V source, is a sticky fault.
// Latency: line in pin -> line out pin 2 edges a stop; V fragment in -> assembled beat on the line 2 edges after the
// 4th fragment's input flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_rstop_xo #(
    parameter integer W = 1104,
    parameter integer V = 276
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,          // 2 * col + tier
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
`ifdef OT_S81SL_RSTOP_MUT_TIERCOL
    // NEGATIVE CONTROL (S81-LBGAP G2): the pre-10-18 {tier, col} decode
    wire [2:0] col = sid_c[2:0]; wire tier = sid_c[3];
`else
    wire [2:0] col = sid_c[3:1]; wire tier = sid_c[0];          // sid = 2 * col + tier; tier 0 = S, 1 = N
`endif
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
    // S81-SMWIRE: ci XB beats (own delivery on E / W; V train on V)
    wire ci_xb = ci_q[0] && ci_q[3:1] == K_XB;
`ifdef OT_S81SL_RSTOP_MUT_CIXB
    wire cxo = 1'b0;                                              // mutant: no own delivery of a ci XB line beat
`else
    wire cxo = ci_xb && (cid_q[0] || cid_q[1]);
`endif
    reg [1:0] vt_n; reg [3 * V - 1:0] vt_b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vt_n <= 2'd0;
        else vt_n <= (ci_xb && cid_q[2]) ? 2'd3 : (vt_n != 2'd0) ? vt_n - 2'd1 : 2'd0;
    always @(posedge clk) vt_b <= (ci_xb && cid_q[2]) ? ci_q[W-1:V] : (vt_b >> V);
    wire vt_on = vt_n != 2'd0;
    wire [2:0] sv = ofv + nxv_out + (ci_q[0] && cid_q[2]) + vt_on;
    // the leaves' fragment 0 already carries hops 1 and src (vq): the V partner delivers it and re-injects as its own
    always @(posedge clk or negedge rst_n)
        if (!rst_n) vo <= {V{1'b0}};
        else vo <= ofv ? of : nxv_out ? nxv_b[V-1:0] : (ci_q[0] && cid_q[2]) ? ci_q[V-1:0] : vt_on ? vt_b[V-1:0] :
                   {V{1'b0}};
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
    // ---------------------------------------------------------------- RG-HEAD: head XB egress (s_0N -> ro_w, hops 1)
    localparam [3:0] XO_SID = 4'd1;                              // s_0N: column 0, tier N (stage NEXT circuit, pair A)
`ifdef OT_S81SL_RSTOP_MUT_XOOFF
    wire xo_here = 1'b0;                                          // mutant: no egress
`elsif OT_S81SL_RSTOP_MUT_XOALL
    wire xo_here = 1'b1;                                          // mutant: egress at every stop
`else
    wire xo_here = sid_c == XO_SID;
`endif
`ifdef OT_S81SL_RSTOP_MUT_XONOFLAG
    wire fl_l = 1'b1, fl_o = 1'b1, fl_a = 1'b1;                   // mutant: the flag is ignored
`else
    wire fl_l = ie[20], fl_o = own[20], fl_a = asm_b[20];
`endif
    wire xl = xo_here && ie_v && ie_k == K_XB && ie_h == 5'd1 && fl_l;   // line beat from E, delivered here
    wire xo = xo_here && own_v && own[3:1] == K_XB && fl_o;              // own beat (h_w = 0 at column 0)
    wire xa = xo_here && asm_v && asm_b[3:1] == K_XB && fl_a;            // V-assembled beat (from s_0S)
    wire [1:0] sx = xl + xo + xa;
    wire [2:0] se = fe + ne + oe + ae + ce, sw_ = fw + nw + ow + aw + cw + (|sx);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ro_e <= {W{1'b0}}; ro_w <= {W{1'b0}}; fault <= 1'b0; end
        else begin
            ro_e <= fe ? hdr(iw, iw_h - 5'd1, iw[12:9]) : ne ? nxb(nx_pe, sid_c) : oe ? hdr(own, h_e, sid_c) :
                    ae ? hdr(asm_b, h_e, sid_c) : ce ? ((ci_q[8:4] == 5'd0) ? hdr(ci_q, h_e, sid_c) : ci_q) : {W{1'b0}};
            ro_w <= fw ? hdr(ie, ie_h - 5'd1, ie[12:9]) : nw ? nxb(nx_pw, sid_c) : ow ? hdr(own, h_w, sid_c) :
                    aw ? hdr(asm_b, h_w, sid_c) : cw ? ((ci_q[8:4] == 5'd0) ? hdr(ci_q, h_w, sid_c) : ci_q) :
                    xl ? hdr(ie, 5'd1, ie[12:9]) : xo ? hdr(own, 5'd1, sid_c) : xa ? hdr(asm_b, 5'd1, sid_c) : {W{1'b0}};
            if (se > 3'd1 || sw_ > 3'd1 || sx > 2'd1 || nown > 3'd1 || sv > 3'd1 || (own_v && asm_v) || (cxo && (own_v || asm_v)))
                fault <= 1'b1;
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
                    (own_v && (own[3:1] == K_XQ || own[3:1] == K_XB)) || asm_v || cxo};
            dl_ev <= iw_v && iw_k != K_XQ && iw_k != K_XB && iw_k != K_NX;
            dl_wv <= ie_v && ie_k != K_XQ && ie_k != K_XB && ie_k != K_NX;
            dl_vv <= v_cs;
            nxw_v <= map_w ? v_nx : xw_nx;
            nxe_v <= map_e ? v_nx : xe_nx;
        end
    wire [W-1:0] g0 = asm_v ? asm_b : cxo ? ci_q : own;
    always @(posedge clk) begin
        g_fam <= {ie_k == K_XB, iw_k == K_XB, g0[3:1] == K_XB};
        g_idx <= {ie[19:13], iw[19:13], g0[19:13]};
        g_d <= {ie[21 +: 1024], iw[21 +: 1024], g0[21 +: 1024]};
        dl_e <= iw; dl_w <= ie; dl_vb <= iv;
        nxw_d <= map_w ? {iv[7:4], iv[20:13], iv[21 +: 160]} : {xwb[7:4], xwb[20:13], xwb[21 +: 160]};
        nxe_d <= map_e ? {iv[7:4], iv[20:13], iv[21 +: 160]} : {xeb[7:4], xeb[20:13], xeb[21 +: 160]};
    end
endmodule
