`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-RTLGAP / RG-FFN (10-21, TOK.DS.BENCH.4.2): ot_s81sl_rstopt -- the slice ring stop (data plane) rebuilt structurally
// safe.  Drop-in successor of ot_s81sl_rstop: SAME ports, SAME beat formats, SAME edges (line in pin -> line out pin 2
// edges; V fragment -> assembled beat on the line 2 edges after the 4th fragment's input flop; ci / own / NX / V paths
// unchanged).  0 added data cycles.  ab64fc0bc census of ot_s81sl_rstop (mapped, kept copies): max 1,896-2,935 loads,
// 57-61 drivers > 32, raw rst_n on 2,505-2,507 flops.  What changed (behaviour of every valid beat is unchanged):
//
//  * Reset (SAFE 1): rst_n drives only an ot_rst_relay (2 sync + 1 kept leaf stage, the xr convention: release 3 edges after
//    the port).  Leaves rr[0..1] clear ONLY the control / valid state (26 flops: fragment / assembly / train counters,
//    own_v / asm_v, ro_e[0] / ro_w[0] / vo[0], g_v, dl_*v, nx*_v, fault).  The 1,104 / 276-b data words are unreset.
//  * Wide selects (SAFE 3): every select that drove a 1,104 / 1,024 / 276-b word is now a set of KEPT one-hot select
//    registers, one per <= 30 bits ("DKS" = decoded kept select).  A select whose decision is known one edge early (own /
//    assembled / train / slot writes) is registered from its next state; a select that is decided by a pin (line header,
//    ci, xfin NX valid, fragment valid) is decoded at the input and registered on the same edge as the input flops, so it
//    equals the old select every cycle.  Each copy group is fed by its own node (decode AND a kept split leaf rr[2..7],
//    which is 1 after reset release and 0 in reset), so no node drives more than 30 copies and no copy more than 30 bits.
//  * own / assembled beats: the 1,104-b own / asm_b capture registers (one enable on 1,104 flops) are gone.  The fragment
//    buffers are 4 slots (on_b / fr_b, slot 3 = the 4th fragment), written per slot under kept slot enables; in the
//    own_v / asm_v cycle the 4-slot buffer IS the old own / asm_b word (slots 0..2 are never written on the 4th-fragment
//    edge), so own / asm_b become wires.  -1,104 x 2 flops.
//  * V train: the 828-b shifter (one select on 828 flops) is a 3-slot capture under kept enables + kept phase one-hots.
//  * Line / V / gather outputs are an AND-OR of the one-hot sources.  Two sources in one cycle are the SAME sticky fault as
//    before (fault terms unchanged, taken from the master flops); the word after a fault is undefined (was: priority).
//  * Static straps (sid -> col / tier / map / line-default hops) are decoded once into static registers and fanned out
//    as kept static copies (sid is a strap, stable long before reset release).
// Bench: the ot_s81sl_rstop benches run unchanged against this module (tb_s81sl_rstop_sid, slice / L0 layer replay).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_rstopt #(
    parameter integer W = 1104,
    parameter integer V = 276
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,          // 2 * col + tier
    input  wire [W-1:0]    ri_w,
    input  wire [W-1:0]    ri_e,
    output wire [W-1:0]    ro_e,
    output wire [W-1:0]    ro_w,
    input  wire [V-1:0]    vi,
    output wire [V-1:0]    vo,
    input  wire [4:0]      xf_v,
    input  wire [4:0]      xf_s,
    input  wire [5*V-1:0]  xf,
    output wire [172:0]    nx_wi,
    output wire [172:0]    nx_ei,
    input  wire [172:0]    nx_eo,
    input  wire [172:0]    nx_wo,
    output reg  [2:0]      g_v,
    output reg  [2:0]      g_fam,
    output reg  [20:0]     g_idx,
    output reg  [3071:0]   g_d,
    output reg             dl_ev, output reg [W-1:0] dl_e,
    output reg             dl_wv, output reg [W-1:0] dl_w,
    output reg             dl_vv, output reg [V-1:0] dl_vb,
    input  wire [2:0]      ci_dir,
    input  wire [W-1:0]    ci_b,
    output reg             fault
);
    localparam [2:0] K_CTL = 3'd0, K_XQ = 3'd1, K_XB = 3'd2, K_NX = 3'd3;
    // group geometry: line words (header group 0 = bits 0..20, then 30-bit groups), V words (15-bit groups),
    // gather data (30-bit groups of the 1,024 data bits), xfin deliveries (30-bit groups of 172)
    localparam integer LG = 30, NGL = 1 + (W - 21 + LG - 1) / LG, NGLX = 1 + (180 - 21) / LG + 1;
    localparam integer VG = 15, NGV = (V + VG - 1) / VG, NGVX = 180 / VG + 1;   // V words: 15-b groups (hold enables: 2 pins / bit)
    localparam integer GG = 30, NGG = (1024 + GG - 1) / GG;
    localparam integer NG = 30, NGN = (172 + NG - 1) / NG;
    localparam integer NSP = 6;
    integer i, k, s;

    // ---------------------------------------------------------------- reset relay: rr[0..1] control clears, rr[2..7] split
    wire [7:0] rr;
    ot_rst_relay #(.REGIONS(8), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rs_a = rr[0], rs_b = rr[1];
    wire [NSP-1:0] sp = rr[7:2];

    // ---------------------------------------------------------------- input flops (data: no reset)
    reg [W-1:0] iw, ie, ci_q; reg [V-1:0] iv; reg [4:0] xfs_q; reg [5*V-1:0] xf_q; reg [172:0] neo_q, nwo_q; reg [2:0] cid_q;
    reg [3:0] sid_c;
    always @(posedge clk) begin
        iw <= ri_w; ie <= ri_e; iv <= vi; xfs_q <= xf_s; xf_q <= xf; neo_q <= nx_eo; nwo_q <= nx_wo; ci_q <= ci_b;
        cid_q <= ci_dir; sid_c <= sid;
    end
    reg [4:0] xfv_q;
    always @(posedge clk or negedge rs_a) if (!rs_a) xfv_q <= 5'd0; else xfv_q <= xf_v;

    // ---------------------------------------------------------------- static straps (level 1 decode, level 2 kept copies)
`ifdef OT_S81SL_RSTOP_MUT_TIERCOL
    wire [2:0] col_c = sid_c[2:0]; wire tier_c = sid_c[3];
`else
    wire [2:0] col_c = sid_c[3:1]; wire tier_c = sid_c[0];
`endif
    reg tier, map_e, map_w, he_nz, hw_nz; reg [4:0] h_e, h_w; reg [3:0] sid1;
    always @(posedge clk) begin
        tier <= tier_c;
        map_e <= tier_c ? col_c == 3'd0 : col_c == 3'd7;
        map_w <= tier_c ? col_c == 3'd7 : col_c == 3'd0;
        h_e <= 5'd7 - {2'd0, col_c}; h_w <= {2'd0, col_c};
        he_nz <= col_c != 3'd7; hw_nz <= col_c != 3'd0;
        sid1 <= sid_c;
    end
    // xfin delivery selects (172 b): v = from V (map end), i = from ie, w = from iw (xwb = tier ? ie : iw, xeb = tier ? iw : ie)
    (* keep *) reg [NGN-1:0] dwv_c, dwi_c, dww_c, dev_c, dei_c, dew_c;
    always @(posedge clk)
        for (k = 0; k < NGN; k = k + 1) begin
            dwv_c[k] <= map_w; dwi_c[k] <= !map_w && tier;  dww_c[k] <= !map_w && !tier;
            dev_c[k] <= map_e; dei_c[k] <= !map_e && !tier; dew_c[k] <= !map_e && tier;
        end

    // ---------------------------------------------------------------- master decodes (fault terms, small loads)
    wire iw_v = iw[0], ie_v = ie[0];
    wire [2:0] iw_k = iw[3:1], ie_k = ie[3:1];
    wire [4:0] iw_h = iw[8:4], ie_h = ie[8:4];
    wire fe = iw_v && iw_k != K_NX && iw_h > 5'd1;
    wire fw = ie_v && ie_k != K_NX && ie_h > 5'd1;
    wire ne = tier ? (nwo_q[172] && !map_w) : (neo_q[172] && !map_e);
    wire nw = tier ? (neo_q[172] && !map_e) : (nwo_q[172] && !map_w);
    wire ce = ci_q[0] && cid_q[0], cw = ci_q[0] && cid_q[1], civ_m = ci_q[0] && cid_q[2];
    wire ci_xb = ci_q[0] && ci_q[3:1] == K_XB;
`ifdef OT_S81SL_RSTOP_MUT_CIXB
    wire cxo = 1'b0;
`else
    wire cxo = ci_xb && (cid_q[0] || cid_q[1]);
`endif
    wire nxv_out = (map_e && neo_q[172]) || (map_w && nwo_q[172]);
    reg ofv, ofs; reg [2:0] nown;
    always @(*) begin
        ofv = |xfv_q; ofs = |(xfv_q & xfs_q); nown = 3'd0;
        for (k = 0; k < 5; k = k + 1) nown = nown + {2'd0, xfv_q[k]};
    end

    // ---------------------------------------------------------------- control state (reset leaves rs_a / rs_b)
    reg [1:0] on_n; reg own_v; reg fr_on; reg [1:0] fr_n; reg asm_v; reg [1:0] vt_n;
    wire iv_v = iv[0]; wire [2:0] iv_k = iv[3:1];
    wire fr_start = iv_v && (iv_k == K_XQ || iv_k == K_XB);
    wire own_v_nx = ofv && !ofs && on_n == 2'd3;
    wire asm_v_nx = fr_on && fr_n == 2'd3;
    wire fr_on_nx = fr_on ? (fr_n != 2'd3) : fr_start;
    wire [1:0] fr_n_nx = fr_on ? fr_n + 2'd1 : (fr_start ? 2'd1 : fr_n);
    wire [1:0] on_n_nx = ofv ? (ofs ? 2'd1 : on_n + 2'd1) : on_n;
    wire vt_go = ci_xb && cid_q[2];
    always @(posedge clk or negedge rs_a)
        if (!rs_a) begin on_n <= 2'd0; own_v <= 1'b0; fr_on <= 1'b0; fr_n <= 2'd0; asm_v <= 1'b0; vt_n <= 2'd0; end
        else begin
            own_v <= own_v_nx; on_n <= on_n_nx;
            fr_on <= fr_on_nx; fr_n <= fr_n_nx; asm_v <= asm_v_nx;
            vt_n <= vt_go ? 2'd3 : (vt_n != 2'd0) ? vt_n - 2'd1 : 2'd0;
        end
    wire vt_on = vt_n != 2'd0;

    // ---------------------------------------------------------------- pin-decoded kept selects (same edge as the inputs)
    wire fe_p = ri_w[0] && ri_w[3:1] != K_NX && ri_w[8:4] > 5'd1;
    wire fw_p = ri_e[0] && ri_e[3:1] != K_NX && ri_e[8:4] > 5'd1;
    wire ce_p = ci_b[0] && ci_dir[0], cw_p = ci_b[0] && ci_dir[1], cv_p = ci_b[0] && ci_dir[2];
    wire hz_p = ci_b[8:4] == 5'd0;
    wire cxb_p = ci_b[0] && ci_b[3:1] == K_XB;
`ifdef OT_S81SL_RSTOP_MUT_CIXB
    wire cxo_p = 1'b0;
`else
    wire cxo_p = cxb_p && (ci_dir[0] || ci_dir[1]);
`endif
    wire vtc_p = cxb_p && ci_dir[2];
    wire nE_p = !tier && nx_eo[172] && !map_e, nW_p = tier && nx_wo[172] && !map_w;    // E line NX from eo / wo
    wire wE_p = tier && nx_eo[172] && !map_e, wW_p = !tier && nx_wo[172] && !map_w;    // W line NX from eo / wo
    wire vE_p = map_e && nx_eo[172], vW_p = !(map_e && nx_eo[172]) && map_w && nx_wo[172];  // V-mapped NX
    wire ofv_p = |xf_v, ofs_p = |(xf_v & xf_s);
    // line E / W selects (group 0 = header)
    (* keep *) reg [NGL-1:0] fe_c, fw_c, ce_c, cw_c, oe_c, ow_c, ae_c, aw_c;
    (* keep *) reg [NGLX-1:0] neE_c, neW_c, nwE_c, nwW_c;
    (* keep *) reg cze_c, czw_c, cne_c, cnw_c;
    // V selects
    (* keep *) reg [NGV-1:0] ofv_c, ofs_c, civ_c; (* keep *) reg [NGVX-1:0] vxE_c, vxW_c;
    (* keep *) reg [3*NGV-1:0] vtc_c, vph_c;     // train capture enables (slot s group g at s*NGV+g) / phase one-hots
    (* keep *) reg [5*NGV-1:0] xfv_c;            // fragment valid copies per V group (fragment merge)
    // gather selects
    (* keep *) reg [NGG-1:0] gas_c, gcs_c, gos_c;
    // slot write enables of the assembly buffer (next state) and on_n copies
    (* keep *) reg [4*NGV-1:0] frw_c; (* keep *) reg [2*NGV-1:0] onn_c;
    always @(posedge clk) begin
        for (k = 0; k < NGL; k = k + 1) begin
            fe_c[k] <= fe_p && sp[(k / 30 + 0) % NSP];
            fw_c[k] <= fw_p && sp[(k / 30 + 1) % NSP];
            ce_c[k] <= ce_p && sp[(k / 30 + 2) % NSP];
            cw_c[k] <= cw_p && sp[(k / 30 + 3) % NSP];
            oe_c[k] <= own_v_nx && he_nz && sp[(k / 30 + 4) % NSP];
            ow_c[k] <= own_v_nx && hw_nz && sp[(k / 30 + 5) % NSP];
            ae_c[k] <= asm_v_nx && he_nz && sp[(k / 30 + 0 + 2) % NSP];
            aw_c[k] <= asm_v_nx && hw_nz && sp[(k / 30 + 1 + 2) % NSP];
        end
        for (k = 0; k < NGLX; k = k + 1) begin
            neE_c[k] <= nE_p && sp[1]; neW_c[k] <= nW_p && sp[2]; nwE_c[k] <= wE_p && sp[3]; nwW_c[k] <= wW_p && sp[4];
        end
        cze_c <= ce_p && hz_p && sp[5]; cne_c <= ce_p && !hz_p && sp[5];
        czw_c <= cw_p && hz_p && sp[0]; cnw_c <= cw_p && !hz_p && sp[0];
        for (k = 0; k < NGV; k = k + 1) begin
            ofv_c[k] <= ofv_p && sp[1]; ofs_c[k] <= ofs_p && sp[2]; civ_c[k] <= cv_p && sp[3];
        end
        for (k = 0; k < NGVX; k = k + 1) begin vxE_c[k] <= vE_p && sp[4]; vxW_c[k] <= vW_p && sp[5]; end
        for (k = 0; k < 3 * NGV; k = k + 1) vtc_c[k] <= vtc_p && sp[(k / 30 + 0) % NSP];
        for (k = 0; k < NGV; k = k + 1) begin                       // train phases: 1 on the edge after the ci edge
            vph_c[k] <= vt_go && sp[(k / 30 + 3) % NSP];
            vph_c[NGV + k] <= vph_c[k];
            vph_c[2 * NGV + k] <= vph_c[NGV + k];
        end
        for (k = 0; k < 5 * NGV; k = k + 1) xfv_c[k] <= xf_v[k / NGV];
        for (k = 0; k < NGG; k = k + 1) begin
            gas_c[k] <= asm_v_nx && sp[(k / 30 + 1) % NSP];
            gcs_c[k] <= cxo_p && sp[(k / 30 + 4) % NSP];
            gos_c[k] <= own_v_nx && sp[(k / 30 + 5) % NSP];
        end
        for (k = 0; k < NGV; k = k + 1) begin
            frw_c[k]           <= !fr_on_nx && sp[0];
            frw_c[NGV + k]     <= fr_on_nx && fr_n_nx == 2'd1 && sp[1];
            frw_c[2 * NGV + k] <= fr_on_nx && fr_n_nx == 2'd2 && sp[2];
            frw_c[3 * NGV + k] <= fr_on_nx && fr_n_nx == 2'd3 && sp[3];
            onn_c[2 * k +: 2]  <= on_n_nx;
        end
    end
    function automatic integer gl(input integer b); gl = (b < 21) ? 0 : 1 + (b - 21) / LG; endfunction
    function automatic integer gvf(input integer b); gvf = b / VG; endfunction

    // ---------------------------------------------------------------- own fragments: per-group merge + 4-slot buffer
    reg [V-1:0] of; reg [4 * V - 1:0] on_b;
    always @(*)
        for (i = 0; i < V; i = i + 1) begin
            of[i] = 1'b0;
            for (k = 0; k < 5; k = k + 1) of[i] = of[i] | (xfv_c[k * NGV + gvf(i)] & xf_q[k * V + i]);
        end
    always @(posedge clk)
        for (i = 0; i < V; i = i + 1) begin
            // slot 0: a start fragment (any count) or count 0; slot s = 1..3: count s without start
            if (ofv_c[gvf(i)] && (ofs_c[gvf(i)] || onn_c[2 * gvf(i) +: 2] == 2'd0)) on_b[i] <= of[i];
            for (s = 1; s < 4; s = s + 1)
                if (ofv_c[gvf(i)] && !ofs_c[gvf(i)] && onn_c[2 * gvf(i) +: 2] == s) on_b[s * V + i] <= of[i];
        end
    wire [W-1:0] own = on_b;                     // == the old own register in the own_v cycle

    // ---------------------------------------------------------------- V receive: 4-slot assembly buffer
    reg [4 * V - 1:0] fr_b;
    always @(posedge clk)
        for (i = 0; i < V; i = i + 1)
            for (s = 0; s < 4; s = s + 1) if (frw_c[s * NGV + gvf(i)]) fr_b[s * V + i] <= iv[i];
    wire [W-1:0] asm_b = fr_b;                   // == the old asm_b register in the asm_v cycle
    wire v_nx = iv_v && iv_k == K_NX && !fr_on, v_cs = iv_v && iv_k != K_XQ && iv_k != K_XB && iv_k != K_NX && !fr_on;

    // ---------------------------------------------------------------- V train capture (fragments 1..3 of a ci XB beat)
    reg [3 * V - 1:0] vts;
    always @(posedge clk)
        for (i = 0; i < V; i = i + 1)
            for (s = 0; s < 3; s = s + 1) if (vtc_c[s * NGV + gvf(i)]) vts[s * V + i] <= ci_q[V + s * V + i];

    // ---------------------------------------------------------------- source words
    function automatic [W-1:0] hdr(input [W-1:0] b, input [4:0] h, input [3:0] sd);
        begin hdr = b; hdr[8:4] = h; hdr[12:9] = sd; end
    endfunction
    function automatic [W-1:0] nxb(input [172:0] f, input [3:0] sd);
        begin nxb = {W{1'b0}}; nxb[0] = 1'b1; nxb[3:1] = K_NX; nxb[8:4] = {1'b0, f[171:168]}; nxb[12:9] = sd;
              nxb[20:13] = f[167:160]; nxb[21 +: 160] = f[159:0]; end
    endfunction
    wire [W-1:0] fwe = hdr(iw, iw_h - 5'd1, iw[12:9]), fww = hdr(ie, ie_h - 5'd1, ie[12:9]);
    wire [W-1:0] nbE = nxb(neo_q, sid1), nbW = nxb(nwo_q, sid1);
    wire [W-1:0] oee = hdr(own, h_e, sid1), oew = hdr(own, h_w, sid1);
    wire [W-1:0] aee = hdr(asm_b, h_e, sid1), aew = hdr(asm_b, h_w, sid1);
    wire [W-1:0] cze = hdr(ci_q, h_e, sid1), czw = hdr(ci_q, h_w, sid1);

    // ---------------------------------------------------------------- line outputs (AND-OR of one-hot kept selects)
    reg [W-1:0] e_nx, w_nx;
    always @(*)
        for (i = 0; i < W; i = i + 1) begin
            if (i < 21) begin
                e_nx[i] = (fe_c[0] & fwe[i]) | (neE_c[0] & nbE[i]) | (neW_c[0] & nbW[i]) | (oe_c[0] & oee[i]) |
                          (ae_c[0] & aee[i]) | (cze_c & cze[i]) | (cne_c & ci_q[i]);
                w_nx[i] = (fw_c[0] & fww[i]) | (nwE_c[0] & nbE[i]) | (nwW_c[0] & nbW[i]) | (ow_c[0] & oew[i]) |
                          (aw_c[0] & aew[i]) | (czw_c & czw[i]) | (cnw_c & ci_q[i]);
            end else begin
                e_nx[i] = (fe_c[gl(i)] & iw[i]) | (oe_c[gl(i)] & own[i]) | (ae_c[gl(i)] & asm_b[i]) | (ce_c[gl(i)] & ci_q[i]);
                w_nx[i] = (fw_c[gl(i)] & ie[i]) | (ow_c[gl(i)] & own[i]) | (aw_c[gl(i)] & asm_b[i]) | (cw_c[gl(i)] & ci_q[i]);
                if (i <= 180) begin
                    e_nx[i] = e_nx[i] | (neE_c[gl(i)] & nbE[i]) | (neW_c[gl(i)] & nbW[i]);
                    w_nx[i] = w_nx[i] | (nwE_c[gl(i)] & nbE[i]) | (nwW_c[gl(i)] & nbW[i]);
                end
            end
        end
    reg roe0, row0; reg [W-1:1] roe_d, row_d;
    always @(posedge clk or negedge rs_b)
        if (!rs_b) begin roe0 <= 1'b0; row0 <= 1'b0; end
        else begin roe0 <= e_nx[0]; row0 <= w_nx[0]; end
    always @(posedge clk) begin roe_d <= e_nx[W-1:1]; row_d <= w_nx[W-1:1]; end
    assign ro_e = {roe_d, roe0}; assign ro_w = {row_d, row0};

    // ---------------------------------------------------------------- V output
    reg [V-1:0] v_nxw;
    always @(*)
        for (i = 0; i < V; i = i + 1) begin
            v_nxw[i] = (ofv_c[gvf(i)] & of[i]) | (civ_c[gvf(i)] & ci_q[i]);
            for (s = 0; s < 3; s = s + 1) v_nxw[i] = v_nxw[i] | (vph_c[s * NGV + gvf(i)] & vts[s * V + i]);
            if (i <= 180) v_nxw[i] = v_nxw[i] | (vxE_c[gvf(i)] & nbE[i]) | (vxW_c[gvf(i)] & nbW[i]);
        end
    reg vo0; reg [V-1:1] vo_d;
    always @(posedge clk or negedge rs_b) if (!rs_b) vo0 <= 1'b0; else vo0 <= v_nxw[0];
    always @(posedge clk) vo_d <= v_nxw[V-1:1];
    assign vo = {vo_d, vo0};

    // ---------------------------------------------------------------- faults (master terms, unchanged)
    wire oe = own_v && he_nz, ow = own_v && hw_nz, ae = asm_v && he_nz, aw = asm_v && hw_nz;
    wire [2:0] se = fe + ne + oe + ae + ce, sw_ = fw + nw + ow + aw + cw;
    wire [2:0] sv = ofv + nxv_out + civ_m + vt_on;
    always @(posedge clk or negedge rs_b)
        if (!rs_b) fault <= 1'b0;
        else if (se > 3'd1 || sw_ > 3'd1 || nown > 3'd1 || sv > 3'd1 || (own_v && asm_v) || (cxo && (own_v || asm_v)))
            fault <= 1'b1;

    // ---------------------------------------------------------------- deliveries
    reg nxw_v, nxe_v; reg [171:0] nxw_d, nxe_d;
    assign nx_wi = {nxw_v, nxw_d}; assign nx_ei = {nxe_v, nxe_d};
    wire xw_nx = tier ? (ie_v && ie_k == K_NX) : (iw_v && iw_k == K_NX);
    wire xe_nx = tier ? (iw_v && iw_k == K_NX) : (ie_v && ie_k == K_NX);
    always @(posedge clk or negedge rs_b)
        if (!rs_b) begin g_v <= 3'b000; dl_ev <= 1'b0; dl_wv <= 1'b0; dl_vv <= 1'b0; nxw_v <= 1'b0; nxe_v <= 1'b0; end
        else begin
            g_v <= {ie_v && (ie_k == K_XQ || ie_k == K_XB), iw_v && (iw_k == K_XQ || iw_k == K_XB),
                    (own_v && (own[3:1] == K_XQ || own[3:1] == K_XB)) || asm_v || cxo};
            dl_ev <= iw_v && iw_k != K_XQ && iw_k != K_XB && iw_k != K_NX;
            dl_wv <= ie_v && ie_k != K_XQ && ie_k != K_XB && ie_k != K_NX;
            dl_vv <= v_cs;
            nxw_v <= map_w ? v_nx : xw_nx;
            nxe_v <= map_e ? v_nx : xe_nx;
        end
    // xfin delivery word {h 4 = [7:4], b 8 = [20:13], d 160 = [21 +: 160]} of a source beat
    function automatic [171:0] nxf(input [W-1:0] b); nxf = {b[7:4], b[20:13], b[21 +: 160]}; endfunction
    wire [171:0] fv = {iv[7:4], iv[20:13], iv[21 +: 160]}, fi = nxf(ie), fwd = nxf(iw);
    wire [W-1:0] g0h = asm_v ? asm_b : cxo ? ci_q : own;              // header fields only (g_fam / g_idx)
    always @(posedge clk) begin
        for (i = 0; i < 1024; i = i + 1)
            g_d[i] <= (gas_c[i / GG] & asm_b[21 + i]) | (gcs_c[i / GG] & ci_q[21 + i]) | (gos_c[i / GG] & own[21 + i]);
        g_d[3071:1024] <= {ie[21 +: 1024], iw[21 +: 1024]};
        g_fam <= {ie_k == K_XB, iw_k == K_XB, g0h[3:1] == K_XB};
        g_idx <= {ie[19:13], iw[19:13], g0h[19:13]};
        dl_e <= iw; dl_w <= ie; dl_vb <= iv;
        for (i = 0; i < 172; i = i + 1) begin
            nxw_d[i] <= (dwv_c[i / NG] & fv[i]) | (dwi_c[i / NG] & fi[i]) | (dww_c[i / NG] & fwd[i]);
            nxe_d[i] <= (dev_c[i / NG] & fv[i]) | (dei_c[i / NG] & fi[i]) | (dew_c[i / NG] & fwd[i]);
        end
    end
endmodule
