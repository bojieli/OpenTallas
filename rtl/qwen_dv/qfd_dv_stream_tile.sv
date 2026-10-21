`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_stream_tile -- the Q-DV slice stream face (qfd_dv_stream) as a structurally safe hard tile.
// QW-STREAM3 2026-10-20: native-32 successor of the QW-STREAM2 t2 packer (both CLOSED t2 / t2c routes failed the
// actual mapped native census: 211 drivers > 32 loads, max 69, packet 0017710ea).  Every wide select is now a kept
// LEAF copy that drives at most G = 14 bits (<= 28 mapped mux pins), and every leaf family is fed by a bank of kept
// ROOT registers so that no root, pin or combinational predicate drives more than ~30 leaf pins:
//   pass side  : pins -> face ROOT bank (v / kind / dst / sid copies) -> LEAF bank (pe/pw relay, te/tw table tap,
//                xe/xw x tap, ubad) -> relay / tap registers.  The payload is carried one extra edge (sw_q0 -> sw_q1)
//                so header and payload stay coherent.  (+1 edge on every pass / tap path against t2.)
//   own writes : face (we / addr in four decoder copies / data / write-any root) -> P1 (BF16 RNE into 4 kept lane
//                copies, registered slot x lane one-hot select, per-tree slot-hit copies, partial faults) -> P2: the
//                beat assembly xb and NK = 9 independent "complete" trees, each on its own kept copy of the mask xm,
//                the open bit op and the slot hit, each tree driving <= 27 kept P2 leaves (relay insertion E / W,
//                eword enable groups, ebeat, x-tap emit).  Insertion reads the assembly xb directly on the edge after
//                completion (eword only holds the x-tap fall-back), so the own path is ONE edge SHORTER than t2.
// Static schedule against the unchanged reference qfd_dv_stream (no credits, no backpressure):
//   sw_i / se_i / sid / cfg_* : reference inputs delayed DP = 2 edges (face root + leaf), relay outputs on the
//                               reference edge, taps one more edge (interior tap relay)
//   xw_* (SU own x writes)    : delayed DX = 2 edges (face + P1); the completion fault pbad is combinational at P2
//   reset                     : the kit lands rst_n in 2 registered stages (+2 edges, constant)
// Price vs t2 (DP 1, DX 3): pass relay / table tap / x tap +1 edge per tile, own write -> emitted word / own x tap /
// beat fault -1 edge; cfg and sid follow the pass stream (+1).
// Reset: roots, leaves and control state (op, directions, tag, valids, faults).  Derived pipeline words (selq, slot
// hits, xm copies, P1 partial faults, payload, the held-word enables cm_e / cm_b) carry no reset: they are pure functions of reset roots one edge later
// (op = 0 masks xm), and the 2-stage landing holds reset for >= 2 running clock edges.
// Storage: 1,024-bit assembly + 1,024-bit held x-tap word + mask copies; no runtime-indexed array, no delay line >= 3.
// MUT (negative controls, must FAIL the bench): 2 BF16 truncation, 21 no lane priority, 22 no duplicate fault,
// 31 relay leaf 17 selects on the E valid, 32 table-tap leaf 5 drops the SID match, 33 insertion leaf E 9 stuck 0,
// 34 tree 3 write-any copy stuck 0, 35 tree 5 mask copy never updates, 37 eword enable leaf 7 stuck 0,
// 38 tag high-half config leaf never enables.
// =====================================================================================================================
module qfd_dv_stream_tile #(
    parameter integer MUT = 0
) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [3:0]     sid,
    input  wire           cfg_v,
    input  wire [1:0]     cfg_dir,
    input  wire [27:0]    cfg_tag,
    input  wire [543:0]   sw_lo,
    input  wire           sw_v,
    input  wire [542:0]   sw_hi,
    input  wire [543:0]   se_lo,
    input  wire           se_v,
    input  wire [542:0]   se_hi,
    output reg  [1087:0]  so_e,
    output reg  [1087:0]  so_w,
    input  wire [7:0]     xw_we,
    input  wire [8*24-1:0] xw_addr,
    input  wire [8*32-1:0] xw_data,
    output reg            tw_we,
    output reg  [1:0]     tw_kind,
    output reg  [23:0]    tw_addr,
    output reg  [511:0]   tw_data_lo,
    output reg  [511:0]   tw_data_hi,
    output reg            xt_v,
    output reg  [23:0]    xt_a,
    output reg  [511:0]   xt_d_lo,
    output reg  [511:0]   xt_d_hi,
    output reg            xt_bad,
    output reg            fault
);
    localparam integer G   = 14;                 // bits per select leaf (2 mapped mux pins per bit -> <= 28 loads)
    localparam integer NGR = 78;                 // relay groups: bits 0..1086 (bit 1087 = the valid leaf)
    localparam integer NGT = 75;                 // table tap vector 1,050 b / x tap vector 1,048 b
    localparam integer NGB = 74;                 // 1,024-bit word
    localparam integer NRT = 3;                  // root copies per 79 / 76-leaf family (<= 27 leaves per root)
    localparam integer NK  = 9;                  // complete trees
    localparam integer NL2 = 2 * (NGR + 1) + NGB + 3;   // P2 leaves: ie_E 79, ie_W 79, cm_e 74, cm_b 2, cm_x 1 = 235
    localparam integer LPT = (NL2 + NK - 1) / NK;      // P2 leaves per tree (27)
    wire [1087:0] sw_i = {sw_v, sw_hi, sw_lo};
    wire [1087:0] se_i = {se_v, se_hi, se_lo};
    integer gi, li, qi;
    // ================================================================================================ face: roots
    reg [1086:0] sw_q0, se_q0, sw_q1, se_q1;   // payload + header, carried two edges (no reset)
    reg [3:0]    sid_q0, sid_q1;
    reg [1:0]    cdir_q;
    reg [27:0]   ctag_q, ctag_q1;
    (* keep = "true" *) reg [NRT-1:0] vpe_r, vpw_r;          // relay valid roots
    (* keep = "true" *) reg [8*NRT-1:0] hte_r;               // table tap roots E: {v, kind[2:0], dst[3:0]}
    (* keep = "true" *) reg [4*NRT-1:0] ste_r;               // sid copies for hte_r
    (* keep = "true" *) reg [7:0] htw_r;                     // table tap root W (only r_tw_we / fault)
    (* keep = "true" *) reg [3:0] stw_r;
    (* keep = "true" *) reg [4*NRT-1:0] hxe_r, hxw_r;        // x tap roots: {v, kind[2:0]}
    (* keep = "true" *) reg       ub_r;                      // undefined kind 4..7 on a valid pass word
    (* keep = "true" *) reg [2:0] cv_r;                      // config-enable roots: [0] east dirs, [1] west dirs, [2] tag
    always @(posedge ck) begin
        sw_q0 <= sw_i[1086:0]; se_q0 <= se_i[1086:0]; sw_q1 <= sw_q0; se_q1 <= se_q0;
        sid_q0 <= sid; sid_q1 <= sid_q0;
        cdir_q <= cfg_dir; ctag_q <= cfg_tag; ctag_q1 <= ctag_q;
        for (gi = 0; gi < NRT; gi = gi + 1) begin ste_r[4*gi +: 4] <= sid; end
        stw_r <= sid;
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            vpe_r <= 0; vpw_r <= 0; hte_r <= 0; htw_r <= 0; hxe_r <= 0; hxw_r <= 0; ub_r <= 1'b0; cv_r <= 3'd0;
        end else begin
            vpe_r <= {NRT{sw_i[1087]}}; vpw_r <= {NRT{se_i[1087]}};
            for (gi = 0; gi < NRT; gi = gi + 1) begin
                hte_r[8*gi +: 8] <= sw_i[1087:1080];
                hxe_r[4*gi +: 4] <= sw_i[1087:1084];
                hxw_r[4*gi +: 4] <= se_i[1087:1084];
            end
            htw_r <= se_i[1087:1080];
            ub_r <= (sw_i[1087] && sw_i[1086]) || (se_i[1087] && se_i[1086]);
            cv_r <= {3{cfg_v}};
        end
    // ================================================================================================ pass leaves
    function automatic thit(input [7:0] h, input [3:0] s);   // valid, kind != 0, dst == sid or broadcast
        thit = h[7] && h[6:4] != 3'd0 && (h[3:0] == s || h[3:0] == 4'hF);
    endfunction
    function automatic xhit(input [3:0] h);                  // valid x word
        xhit = h[3] && h[2:0] == 3'd0;
    endfunction
    function automatic thit_nosid(input [7:0] h);            // MUT 32
        thit_nosid = h[7] && h[6:4] != 3'd0;
    endfunction
    (* keep = "true" *) reg [NGR:0] pe_l, pw_l;              // [NGR] = valid leaf
    (* keep = "true" *) reg [NGT:0] te_l, xe_l, xw_l;        // [NGT] = valid / fault leaf
    (* keep = "true" *) reg         tw_x;
    (* keep = "true" *) reg         ub_l;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin pe_l <= 0; pw_l <= 0; te_l <= 0; xe_l <= 0; xw_l <= 0; tw_x <= 1'b0; ub_l <= 1'b0; end
        else begin
            for (gi = 0; gi <= NGR; gi = gi + 1) begin
                pe_l[gi] <= (MUT == 31 && gi == 17) ? vpw_r[gi * NRT / (NGR + 1)] : vpe_r[gi * NRT / (NGR + 1)];
                pw_l[gi] <= vpw_r[gi * NRT / (NGR + 1)];
            end
            for (gi = 0; gi <= NGT; gi = gi + 1) begin
                te_l[gi] <= (MUT == 32 && gi == 5) ? thit_nosid(hte_r[8*(gi * NRT / (NGT + 1)) +: 8])
                                                   : thit(hte_r[8*(gi * NRT / (NGT + 1)) +: 8], ste_r[4*(gi * NRT / (NGT + 1)) +: 4]);
                xe_l[gi] <= xhit(hxe_r[4*(gi * NRT / (NGT + 1)) +: 4]);
                xw_l[gi] <= xhit(hxw_r[4*(gi * NRT / (NGT + 1)) +: 4]);
            end
            tw_x <= thit(htw_r, stw_r);
            ub_l <= ub_r;
        end
    // ================================================================================================ configuration
    (* keep = "true" *) reg [NK-1:0] de_k, dw_k;              // direction copies, one per complete tree
    (* keep = "true" *) reg [1:0]    cv_l;                    // tag-enable leaves (14 bits each)
    reg [27:0] tag;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin de_k <= 0; dw_k <= 0; cv_l <= 2'd0; tag <= 28'd0; end
        else begin
            for (gi = 0; gi < NK; gi = gi + 1) begin
                if (cv_r[0]) de_k[gi] <= cdir_q[0];
                if (cv_r[1]) dw_k[gi] <= cdir_q[1];
            end
            cv_l <= {cv_r[2] && (MUT != 38), cv_r[2]};
            if (cv_l[0]) tag[13:0] <= ctag_q1[13:0];
            if (cv_l[1]) tag[27:14] <= ctag_q1[27:14];
        end
    // ================================================================================================ own x writes
    function automatic [15:0] bf16(input [31:0] b);
        reg [32:0] r;
        begin
            r = {1'b0, b} + 33'h7FFF + {32'd0, b[16]};
            bf16 = (MUT == 2) ? b[31:16] : r[31:16];
        end
    endfunction
    // ---------------------------------------------------------------------------------------------- face
    // decoder copy c = 2 * (s / 32) + (s % 8) / 4 serves 16 slots (each digit term -> 4 slots)
    (* keep = "true" *) reg [31:0]  we_c;                    // lane enables per decoder copy: [8c + l]
    (* keep = "true" *) reg [191:0] wd_c;                    // lane slot digits addr[5:0] per copy: [48c + 6l +: 6]
    reg [127:0] wb_q;                                         // lane beat addresses addr[21:6]
    reg [255:0] wd_q;
    (* keep = "true" *) reg        wy_r;                     // write-any root
    always @(posedge ck) begin
        for (gi = 0; gi < 8; gi = gi + 1) begin
            for (qi = 0; qi < 4; qi = qi + 1) wd_c[48*qi + 6*gi +: 6] <= xw_addr[24*gi +: 6];
            wb_q[16*gi +: 16] <= xw_addr[24*gi + 6 +: 16];
        end
        wd_q <= xw_data;
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin we_c <= 32'd0; wy_r <= 1'b0; end
        else begin we_c <= {4{xw_we}}; wy_r <= xw_we != 8'd0; end
    // ---------------------------------------------------------------------------------------------- P1 (comb)
    genvar l, d, s, b, k;
    wire [511:0] sel_n;                                       // [8*s + l]: lane l writes slot s (highest lane wins)
    wire [63:0]  sh_n, dup_n;
    wire [7:0]   beat_bad;
    wire [255:0] lo_c, hi_c;                                  // [64c + 8l + d]
    generate
        for (l = 0; l < 8; l = l + 1) begin: g_bb
            assign beat_bad[l] = we_c[l] && (!we_c[0] || wb_q[16*l +: 16] != wb_q[0 +: 16]);
        end
        // two-level decode per lane and per copy: low digit addr[2:0], high digit addr[5:3] with the lane enable;
        // a copy uses 4 low and 4 high terms, each term -> 4 slots (x the ~4 priority / duplicate uses of a hit)
        for (k = 0; k < 4; k = k + 1) begin: g_copy
            for (l = 0; l < 8; l = l + 1) begin: g_decode
                for (d = 0; d < 8; d = d + 1) begin: g_digit
                    assign lo_c[64*k + 8*l + d] = (wd_c[48*k + 6*l +: 3] == d);
                    assign hi_c[64*k + 8*l + d] = we_c[8*k + l] && (wd_c[48*k + 6*l + 3 +: 3] == d);
                end
            end
        end
        for (s = 0; s < 64; s = s + 1) begin: g_slot1
            wire [7:0] hit;
            for (l = 0; l < 8; l = l + 1) begin: g_lane
                assign hit[l] = lo_c[64*(2*(s/32) + (s%8)/4) + 8*l + s % 8] && hi_c[64*(2*(s/32) + (s%8)/4) + 8*l + s / 8];
                if (l == 7) begin: g_top
                    assign sel_n[8*s+l] = hit[l];
                end else begin: g_low
                    assign sel_n[8*s+l] = hit[l] && ((MUT == 21) || !(|hit[7:l+1]));
                end
            end
            assign sh_n[s] = |hit;
            assign dup_n[s] = (hit[1] && hit[0]) || (hit[2] && |hit[1:0]) || (hit[3] && |hit[2:0]) ||
                              (hit[4] && |hit[3:0]) || (hit[5] && |hit[4:0]) || (hit[6] && |hit[5:0]) ||
                              (hit[7] && |hit[6:0]);
        end
    endgenerate
    // ---------------------------------------------------------------------------------------------- P1 (regs)
    reg [511:0] selq;                                         // one-hot select, each bit -> 16 AND terms
    (* keep = "true" *) reg [64*NK-1:0] shq_t;               // slot-hit copy per complete tree
    (* keep = "true" *) reg [127:0] shq_b;                   // slot-hit copies for the xb write: [64*h + s], bits 8h..8h+7
    (* keep = "true" *) reg [511:0] lane_c;                  // BF16 lane data, copy q serves slots 16q..16q+15
    (* keep = "true" *) reg [NK+1:0] wa1;                    // write-any leaves: [k] tree k op update, [NK+h] xbeat half h
    reg         dupq, bbq, w0q;
    reg [15:0]  abq;

    always @(posedge ck) begin
        selq <= sel_n; dupq <= |dup_n; bbq <= |beat_bad; w0q <= we_c[0]; abq <= wb_q[0 +: 16];
        for (qi = 0; qi < NK; qi = qi + 1) shq_t[64*qi +: 64] <= sh_n;
        shq_b <= {sh_n, sh_n};
        for (qi = 0; qi < 4; qi = qi + 1)
            for (li = 0; li < 8; li = li + 1)
                lane_c[128*qi + 16*li +: 16] <= bf16(wd_q[32*li +: 32]);
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) wa1 <= 0;
        else for (gi = 0; gi < NK + 2; gi = gi + 1) wa1[gi] <= (MUT == 34 && gi == 3) ? 1'b0 : wy_r;
    // ---------------------------------------------------------------------------------------------- P2
    reg [1023:0] xb;                                          // beat assembly (no reset; written only on slot hits)
    reg [15:0]   xbeat;
    reg [64*NK-1:0] xm_k;                                     // mask copy per tree (no reset: op = 0 masks it)
    (* keep = "true" *) reg [3*NK-1:0] op_k;                 // open-beat copies per tree: [3k + j] slots 22j..
    wire [NK-1:0] complete_k;
    wire [1023:0] nb;
    generate
        for (s = 0; s < 64; s = s + 1) begin: g_slot
            wire [127:0] lane = lane_c[128*(s / 16) +: 128];
            for (b = 0; b < 16; b = b + 1) begin: g_bit
                wire [7:0] terms;
                for (l = 0; l < 8; l = l + 1) begin: g_term
                    assign terms[l] = lane[16*l + b] && selq[8*s+l];
                end
                assign nb[16*s + b] = shq_b[64*(b / 8) + s] ? (|terms) : xb[16*s + b];
            end
        end
        for (k = 0; k < NK; k = k + 1) begin: g_tree
            wire [63:0] xmk = xm_k[64*k +: 64];
            wire [63:0] shk = shq_t[64*k +: 64];
            wire [63:0] nmk;
            for (s = 0; s < 64; s = s + 1) begin: g_nm
                assign nmk[s] = (op_k[3*k + s / 22] && xmk[s]) || shk[s];
            end
            // &nm = op ? &(xm | sh) : &sh  (op drives one select instead of 64 AND terms)
            assign complete_k[k] = op_k[3*k] ? &(xmk | shk) : &shk;
            always @(posedge ck) xm_k[64*k +: 64] <= (MUT == 35 && k == 5) ? xmk : nmk;
            always @(posedge ck or negedge rst_n)
                if (!rst_n) op_k[3*k +: 3] <= 3'd0;
                else if (wa1[k]) op_k[3*k +: 3] <= {3{!complete_k[k]}};
        end
    endgenerate
    always @(posedge ck) begin
        xb <= nb;
        for (gi = 0; gi < 16; gi = gi + 1) if (wa1[NK + gi / 8]) xbeat[gi] <= abq[gi];
    end
    // completion fault (combinational on the P2 cycle = the reference's pbad cycle), from tree 0's copies
    wire sbad = (MUT == 22) ? 1'b0 : ((op_k[0] && |(xm_k[63:0] & shq_t[63:0])) || dupq);
    wire pbad = sbad || bbq || (w0q && op_k[0] && abq != xbeat);
    // P2 leaves: complete is only ever 1 on a write edge (op = 1 holds a not-complete mask), so no write-any term
    // The held-word enables cm_e / cm_b carry no reset: like the reference eword (captured on the completion edge
    // itself, never reset), a word completed just before reset is still taken; complete is 0 under reset (op = 0).
    (* keep = "true" *) reg [NL2-1:0] p2l;
    localparam integer L2E0 = 2 * (NGR + 1);           // first cm_e leaf
    localparam integer L2X  = NL2 - 1;                 // cm_x (x-tap emit valid, reset)
    function automatic p2d(input integer i, input [NK-1:0] c, input [NK-1:0] de, input [NK-1:0] dw);
        p2d = (MUT == 33 && i == 9) ? 1'b0 : (MUT == 37 && i == L2E0 + 7) ? 1'b0 :
              c[i / LPT] && (i <= NGR ? de[i / LPT] : i < L2E0 ? dw[i / LPT] : 1'b1);
    endfunction
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin p2l[L2E0-1:0] <= 0; p2l[L2X] <= 1'b0; end
        else begin
            for (gi = 0; gi < L2E0; gi = gi + 1) p2l[gi] <= p2d(gi, complete_k, de_k, dw_k);
            p2l[L2X] <= p2d(L2X, complete_k, de_k, dw_k);
        end
    always @(posedge ck)
        for (gi = L2E0; gi < L2X; gi = gi + 1) p2l[gi] <= p2d(gi, complete_k, de_k, dw_k);
    wire [NGR:0] ie_e = p2l[NGR:0];
    wire [NGR:0] ie_w = p2l[2*NGR+1:NGR+1];
    wire [NGB-1:0] cm_e = p2l[2*NGR+1+NGB:2*NGR+2];
    wire [1:0]   cm_b = p2l[2*NGR+3+NGB:2*NGR+2+NGB];
    wire         cm_x = p2l[2*NGR+4+NGB];
    // ---------------------------------------------------------------------------------------------- P3: held x-tap word
    reg [1023:0] eword;
    reg [15:0]   ebeat;
    wire [1023:0] eword_n;
    wire [15:0]   ebeat_n;
    generate
        for (b = 0; b < 1024; b = b + 1) begin: g_ew
            assign eword_n[b] = cm_e[b / G] ? xb[b] : eword[b];
        end
        for (b = 0; b < 16; b = b + 1) begin: g_eb
            assign ebeat_n[b] = cm_b[b / 8] ? xbeat[b] : ebeat[b];
        end
    endgenerate
    always @(posedge ck) begin eword <= eword_n; ebeat <= ebeat_n; end
    // ================================================================================================ relay + insertion
    wire [1087:0] own = {1'b1, 3'd0, 4'hF, sid_q1, 2'b00, xbeat, 6'd0, tag, xb};
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin so_e[1087] <= 1'b0; so_w[1087] <= 1'b0; end
        else begin
            so_e[1087] <= pe_l[NGR] || ie_e[NGR];
            so_w[1087] <= pw_l[NGR] || ie_w[NGR];
        end
    always @(posedge ck)
        for (gi = 0; gi < 1087; gi = gi + 1) begin
            so_e[gi] <= pe_l[gi / G] ? sw_q1[gi] : ie_e[gi / G] ? own[gi] : 1'b0;
            so_w[gi] <= pw_l[gi / G] ? se_q1[gi] : ie_w[gi / G] ? own[gi] : 1'b0;
        end
    // ================================================================================================ taps (interior relay)
    wire [1049:0] tv_e = {sw_q1[1085:1084], sw_q1[1075:1052], sw_q1[1023:0]};
    wire [1049:0] tv_w = {se_q1[1085:1084], se_q1[1075:1052], se_q1[1023:0]};
    wire [1047:0] xv_e = {sw_q1[1075:1052], sw_q1[1023:0]};
    wire [1047:0] xv_w = {se_q1[1075:1052], se_q1[1023:0]};
    wire [1047:0] xv_o = {2'b00, ebeat_n, 6'd0, eword_n};
    reg          r_tw_we, r_xt_v, r_xt_bad;
    reg [1049:0] r_tw;
    reg [1047:0] r_xt;
    always @(posedge ck) begin
        for (gi = 0; gi < 1050; gi = gi + 1) r_tw[gi] <= te_l[gi / G] ? tv_e[gi] : tv_w[gi];
        for (gi = 0; gi < 1048; gi = gi + 1) r_xt[gi] <= xe_l[gi / G] ? xv_e[gi] : xw_l[gi / G] ? xv_w[gi] : xv_o[gi];
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin r_tw_we <= 1'b0; r_xt_v <= 1'b0; r_xt_bad <= 1'b0; end
        else begin
            r_tw_we <= te_l[NGT] || tw_x;
            r_xt_v <= xe_l[NGT] || xw_l[NGT] || cm_x;
            r_xt_bad <= r_xt_bad | ((xe_l[NGT] ? 2'd1 : 2'd0) + (xw_l[NGT] ? 2'd1 : 2'd0) + (cm_x ? 2'd1 : 2'd0) > 2'd1);
        end
    always @(posedge ck) begin
        tw_kind <= r_tw[1049:1048]; tw_addr <= r_tw[1047:1024]; tw_data_lo <= r_tw[511:0]; tw_data_hi <= r_tw[1023:512];
        xt_a <= r_xt[1047:1024]; xt_d_lo <= r_xt[511:0]; xt_d_hi <= r_xt[1023:512];
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tw_we <= 1'b0; xt_v <= 1'b0; xt_bad <= 1'b0; end
        else begin tw_we <= r_tw_we; xt_v <= r_xt_v; xt_bad <= r_xt_bad; end
    // ================================================================================================ fault (sticky)
    wire bad = pbad || (pe_l[NGR] && ie_e[NGR]) || (pw_l[NGR] && ie_w[NGR]) || (te_l[NGT] && tw_x) || ub_l;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | bad;
endmodule
