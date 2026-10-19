`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): the slice control plane (centre leaf), one hardened sub-leaf.  No arithmetic; it
// turns the compiler's control traffic into the fixed-cycle commands of the slice's sub-leaves:
//
//   CTL decode  CTL beats delivered by the ring stop (tier line E-bound / W-bound, or the V rung at column 3, where the
//               G-unit injects) whose slice mask holds this slice.  Payload p = beat[21 +: 186]:
//               [15:0] slice mask, [20:16] target, [25:21] leaf mask, [185:26] body (160 b):
//                 0 vp command (body = c_d) to the masked beat leaves      1 xfin go (body[31:0] = eps, body[32] = mode
//                   ENG (RTL-BUILD-S81 10-18: the Engram mix exchange), body[95:64] = the Engram scale for eg)
//                 2 x streamer issuer / phase start (body = is_d)          3 capture phase config (body = cfg_d)
//                 4 send config (below)                                    5 one leaf-store row write {a 10, m 4, d 128}
//               A CTL beat from V (the G-unit) is also re-injected on the tier line both ways (hops 0 = line default)
//               so every slice of the tier gets it.  Two CTL beats in one cycle are a sticky fault.
//   RD receive  RD beats (kind 4) for this slice: payload [15:0] slice mask, [18:16] leaf, [28:19] row, [30:29] pairs - 1,
//               [31 +: 1024] up to 4 row pairs -> the leaf's row-pair write port, one pair a cycle.  A second RD to a leaf
//               whose unpacker is busy, or a collision with a CTL row write, is a sticky fault.
//   send        lo row pairs from the beat leaves (RDOUT; the compiler staggers the leaves) are packed per the send config
//               (n pairs, then one beat) and injected: line E / W / V (or B on C3) with the configured header
//               {kind, hops (0 = line default), dst mask, dst leaf, dst row}.
//   SC relay    SC beats (kind 5, router scores) delivered on the line at the relay slice (send config bit) leave on V.
//   norm        the 5 beat partials (equal-latency glue: same edge) -> xfin s port in leaf order 0..4 (xfin injects on
//               index 4); xfin's rstd -> the 5 vn rb ports.
//   ENG         the 5 leaves' Engram partial triples of copy j (vs op 14 runs in lockstep on all 5 leaves: same edge)
//               -> xfin s port, 15 words kind-major then leaf, s_i = (kind * 4 + j) * 5 + leaf (kind 0 hh, 1 kk, 2 dd);
//               eg's gates (one per copy) -> all 5 leaves' g ports.  A triple while the previous one serialises, a
//               partial leaf set or mixed copies, or an ENG triple against a norm collection is a sticky fault.
// Faults (sticky; checks only, they never reschedule): two CTLs / two RDs / two lo beats in a cycle, an RD or a row write into
// a busy leaf unpacker, a partial set that is partial or overlaps the collection, two injections in one ci slot, an RD to
// leaf > 4, a CTL target > 5, two relayed SC beats in a cycle, a lo beat in the send-config cycle (it would be dropped), the ENG faults above.
// Bench: rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xr.sv (tools/s81_slice/xr_bench.sh); mutants OT_S81SL_XR_MUT_*.
// Every input lands in a flop; every output leaves a flop.  HB = 1 builds the C3 variant (band port B, attention).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_xr #(
    parameter integer HB = 0,
    parameter integer W  = 1104,
    parameter integer V  = 276
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    // ring stop (control plane side)
    input  wire            dl_ev, input wire [W-1:0] dl_e,
    input  wire            dl_wv, input wire [W-1:0] dl_w,
    input  wire            dl_vv, input wire [V-1:0] dl_vb,
    output reg  [2:0]      ci_dir,
    output wire [W-1:0]    ci_b,
    // band port (C3 only; HB = 0 leaves it out of the netlist -- see the C1 wrapper)
    input  wire [W-1:0]    bi,
    output wire [W-1:0]    bo,
    // beat leaves
    output reg  [4:0]      c_v,
    (* keep *) output reg [159:0] c_d,       // XR3 (10-18): one copy; the slice glue fans it to the 5 leaves
    output reg  [4:0]      sw_v,
    output reg  [5*10-1:0] sw_a,
    output reg  [5*8-1:0]  sw_m,
    output reg  [5*256-1:0] sw_d,
    input  wire [4:0]      lo_v,
    input  wire [5*256-1:0] lo_d,
    input  wire [4:0]      p_v,
    input  wire [5*32-1:0] p_d,
    output reg             rb_v,              // XR3: one copy each (slice glue fan-out)
    output reg  [31:0]     rb_d,
    // Engram: leaf partial triples in, eg gates out to the leaves
    input  wire [4:0]      e_v,
    input  wire [5*2-1:0]  e_c,
    input  wire [5*96-1:0] e_d,
    input  wire            eg_v,
    input  wire [1:0]      eg_c,
    input  wire [31:0]     eg_d,
    output reg             g_v,               // XR3: one copy each (slice glue fan-out)
    output reg  [1:0]      g_c,
    output reg  [31:0]     g_d,
    // xfin
    output reg             x_go,
    output reg             x_mode,
    output reg  [31:0]     x_eps,
    output reg  [31:0]     x_scale,
    output reg             x_sv,
    output reg  [7:0]      x_si,
    output reg  [31:0]     x_s,
    input  wire            x_rbv,
    input  wire [31:0]     x_rbd,
    // x streamer, capture
    output reg             is_v,
    (* keep *) output reg [159:0] is_d,
    output reg             cfg_v,
    (* keep *) output reg [159:0] cfg_d,
    output reg             fault
);
    localparam [2:0] K_CTL = 3'd0, K_RD = 3'd4, K_SC = 3'd5, K_CL = 3'd6;
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_r = rsv[1], rs_s = rsv[2], rs_o = rsv[3];
    integer k, i;
    // ---------------------------------------------------------------- input flops
    reg ev, wv, vv; reg [W-1:0] eb, wb, bb; reg [V-1:0] vb; reg [4:0] lov, pv; reg [5*256-1:0] lod; reg [5*32-1:0] pd;
    reg rbv; reg [31:0] rbd; reg [3:0] sid_c;
    reg [4:0] ev_c; reg [5*2-1:0] ec_c; reg [5*96-1:0] ed_c; reg egv_c; reg [1:0] egc_c; reg [31:0] egd_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin ev_c <= 5'd0; egv_c <= 1'b0; end
        else begin ev_c <= e_v; egv_c <= eg_v; end
    always @(posedge clk) begin ec_c <= e_c; ed_c <= e_d; egc_c <= eg_c; egd_c <= eg_d; end
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin ev <= 1'b0; wv <= 1'b0; vv <= 1'b0; lov <= 5'd0; pv <= 5'd0; rbv <= 1'b0; end
        else begin ev <= dl_ev; wv <= dl_wv; vv <= dl_vv; lov <= lo_v; pv <= p_v; rbv <= x_rbv; end
    always @(posedge clk) begin
        eb <= dl_e; wb <= dl_w; vb <= dl_vb; bb <= (HB != 0) ? bi : {W{1'b0}}; lod <= lo_d; pd <= p_d; rbd <= x_rbd;
        sid_c <= sid;
    end
    wire bv = (HB != 0) && bb[0];
    // ---------------------------------------------------------------- stage 1: classify (S81U-XR2, +1 cycle)
    // Pure functions of the input flops, registered before any wide write: which source carries this slice's CTL / RD,
    // the selected CTL payload, the selected RD row pairs, decoded per-target / per-leaf enables, the lo row-pair select and
    // the ci word of a V re-injection / SC relay.  Everything downstream is the previous single-stage logic run one cycle
    // later on these registers, so every CTL / RD / lo / V / SC consequence moves +1 cycle (partials and rstd do not).
    reg [15:0] sid_oh;
    always @(posedge clk) sid_oh <= 16'd1 << sid_c;          // sid is a strap: static from reset
    wire e_ctl = ev && eb[3:1] == K_CTL, w_ctl = wv && wb[3:1] == K_CTL, v_ctl = vv && vb[3:1] == K_CTL;
    wire e_rd = ev && (eb[3:1] == K_RD || eb[3:1] == K_CL), w_rd = wv && (wb[3:1] == K_RD || wb[3:1] == K_CL);
    wire b_rd = bv;
    wire e_sc = ev && eb[3:1] == K_SC, w_sc = wv && wb[3:1] == K_SC;
    wire [185:0] pe = eb[21 +: 186], pw = wb[21 +: 186], pvv = vb[21 +: 186];
    wire mine_e = |(pe[15:0] & sid_oh), mine_w = |(pw[15:0] & sid_oh), mine_v = |(pvv[15:0] & sid_oh);
    wire ce = e_ctl && mine_e, cw = w_ctl && mine_w, cv = v_ctl && mine_v;
    wire [185:0] cp = ce ? pe : cw ? pw : pvv;
    wire [4:0] tgt0 = cp[20:16], lmask0 = cp[25:21];
    wire re = e_rd && mine_e, rw_ = w_rd && mine_w;
`ifdef OT_S81SL_RD_PAIR
    // Partner-only typed V word: valid1/kind3/leaf3/even-row10/data256.
    // Each word is one complete row pair; no partial-message payload buffer.
    wire v_rd = vv && vb[3:1] == K_RD;
    // Internal registered CI loopback reuses the existing RD input/classify/
    // unpack pipeline. Do not mux rstop dl_e: it unshares 1024 gather FF.
    wire local_rd = ci_v && s_local && ci_dir == 3'd0 && ci_b[3:1] == K_RD;
    wire rdv0 = re || rw_ || b_rd || v_rd || local_rd;
`else
    wire rdv0 = re || rw_ || b_rd;
`endif
`ifdef OT_S81SL_RD_PAIR
    wire [W-1:0] rdb0 = local_rd ? ci_b : re ? eb : rw_ ? wb : bb;
`else
    wire [W-1:0] rdb0 = re ? eb : rw_ ? wb : bb;
`endif
`ifdef OT_S81SL_RD_PAIR
    wire [2:0] rl0 = v_rd ? vb[6:4] : rdb0[37 +: 3];
`else
    wire [2:0] rl0 = rdb0[37 +: 3];
`endif
    reg [2:0] nlo0; reg [255:0] lo_sel0;
    always @(*) begin
        nlo0 = 3'd0; lo_sel0 = 256'd0;
        for (k = 0; k < 5; k = k + 1) begin nlo0 = nlo0 + lov[k]; if (lov[k]) lo_sel0 = lo_sel0 | lod[256 * k +: 256]; end
    end
    wire [V-1:0] sc_b0 = e_sc ? eb[V-1:0] : wb[V-1:0];
    // stage-1 registers
    reg cvld, vct, esc, wsc, rdv, f1; reg [5:0] tg; reg [4:0] lmask, rwe, rwr, lov1; reg [159:0] body;
    reg [1:0] rnp; reg [9:0] rrow; reg [1023:0] rdat; reg [255:0] lo_sel; reg [V-2:0] cix;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin cvld <= 1'b0; vct <= 1'b0; esc <= 1'b0; wsc <= 1'b0; rdv <= 1'b0; f1 <= 1'b0; tg <= 6'd0;
                         rwe <= 5'd0; rwr <= 5'd0; lov1 <= 5'd0; end
        else begin
            cvld <= ce || cw || cv; vct <= v_ctl; esc <= e_sc; wsc <= w_sc; rdv <= rdv0; lov1 <= lov;
            for (k = 0; k < 6; k = k + 1) tg[k] <= (ce || cw || cv) && tgt0 == k;
            for (k = 0; k < 5; k = k + 1) begin
                rwe[k] <= rdv0 && rl0 == k;
                rwr[k] <= (ce || cw || cv) && tgt0 == 5'd5 && lmask0[k];
            end
            // input-only faults: two CTLs / two RDs / two lo beats in a cycle, an RD to leaf > 4, a CTL target > 5
            f1 <= ((ce + cw + cv) > 2'd1) || ((re + rw_ + b_rd
`ifdef OT_S81SL_RD_PAIR
                     + v_rd + local_rd
`endif
                    ) > 2'd1) || (nlo0 > 3'd1) || (rdv0 && rl0 > 3'd4) ||
                  ((ce || cw || cv) && tgt0 > 5'd5)
`ifdef OT_S81SL_RD_PAIR
                  || (v_rd && (vb[7] || |vb[275:273]))
`endif
                  ;
        end
    always @(posedge clk) begin
        lmask <= lmask0; body <= cp[185:26];
`ifdef OT_S81SL_RD_PAIR
        rnp <= v_rd ? 2'd0 : rdb0[50 +: 2];
        rrow <= v_rd ? vb[16:7] : rdb0[40 +: 10];
        rdat <= v_rd ? {768'd0,vb[272:17]} : rdb0[52 +: 1024];
`else
        rnp <= rdb0[50 +: 2]; rrow <= rdb0[40 +: 10]; rdat <= rdb0[52 +: 1024];
`endif
        lo_sel <= lo_sel0;
`ifdef OT_S81SL_XR_MUT_HOPS
        cix <= v_ctl ? vb[V-1:1] :                                       // mutant: re-injected CTL keeps the V hops
`else
        cix <= v_ctl ? {vb[V-1:9], 5'd0, vb[3:1]} :
`endif
                       sc_b0[V-1:1];
    end

    // ---------------------------------------------------------------- send config, packing, injection
    // body: [3:0] dir {B, V, W, E}, [6:4] kind, [11:7] hops, [27:12] dst slice mask, [30:28] dst leaf, [40:31] dst row,
    //       [42:41] pairs - 1, [43] SC relay to V
    reg [3:0] s_dir; reg [2:0] s_kind; reg [4:0] s_hops; reg [15:0] s_mask; reg [2:0] s_leaf; reg [9:0] s_row; reg [1:0] s_np;
    reg s_scv;
`ifdef OT_S81SL_RD_PAIR
    reg s_local;
    wire pair_mode = s_dir == 4'b0100 && s_kind == K_RD;
    wire pair_v = (|lov1) && pair_mode;
    wire [9:0] pair_row = s_row + {7'd0,pn,1'b0};
    wire [V-1:0] pair_word = {3'd0,lo_sel,pair_row,s_leaf,K_RD,1'b1};
`endif
    reg [1023:0] pk; reg [1:0] pn; reg pk_go;
    reg [W-1:0] snd;
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin s_dir <= 4'd0; pn <= 2'd0; pk_go <= 1'b0; s_scv <= 1'b0;
`ifdef OT_S81SL_RD_PAIR
            s_local <= 1'b0;
`endif
        end
        else begin
            pk_go <= 1'b0;
            if (tg[4]) begin
                s_dir <= body[3:0]; s_kind <= body[6:4]; s_hops <= body[11:7]; s_mask <= body[27:12];
                s_leaf <= body[30:28]; s_row <= body[40:31]; s_np <= body[42:41]; s_scv <= body[43]; pn <= 2'd0;
`ifdef OT_S81SL_RD_PAIR
                s_local <= body[44];
`endif
            end else if (|lov1) begin
                pn <= (pn == s_np) ? 2'd0 : pn + 2'd1;
                pk_go <= pn == s_np;
            end
        end
    always @(posedge clk)                                        // fixed-index pair writes (decoded pn)
        for (k = 0; k < 4; k = k + 1) if ((|lov1) && pn == k) pk[256 * k +: 256] <= lo_sel;
    always @(*) begin
        snd = {W{1'b0}};
        snd[0] = 1'b1; snd[3:1] = s_kind; snd[8:4] = s_hops; snd[12:9] = sid_c; snd[20:13] = 8'd0;
        snd[21 +: 16] = s_mask; snd[37 +: 3] = s_leaf; snd[40 +: 10] = s_row; snd[50 +: 2] = s_np; snd[52 +: 1024] = pk;
    end
    // V-from-G-unit CTL re-injection on the tier line (both sides, hops 0 = line default), SC relay to V
    wire sc_rel = s_scv && (esc || wsc);
    reg ci_v; reg [W-2:0] ci_r;
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin ci_dir <= 3'd0; ci_v <= 1'b0; end
        else begin
`ifdef OT_S81SL_RD_PAIR
            ci_dir <= vct ? 3'b011 : pair_v ? 3'b100 :
                      (pk_go && !pair_mode) ? (s_local ? 3'b000 : s_dir[2:0]) : sc_rel ? 3'b100 : 3'b000;
            ci_v <= vct || pair_v || (pk_go && !pair_mode && ((|s_dir[2:0]) || s_local)) || sc_rel;
`else
            ci_dir <= vct ? 3'b011 : pk_go ? s_dir[2:0] : sc_rel ? 3'b100 : 3'b000;
            ci_v <= vct || (pk_go && |s_dir[2:0]) || sc_rel;
`endif
        end
    assign ci_b = {ci_r, ci_v};
`ifdef OT_S81SL_RD_PAIR
    always @(posedge clk) ci_r <= (pair_v && !vct) ? {{(W-V){1'b0}},pair_word[V-1:1]} :
                                 (pk_go && !vct) ? snd[W-1:1] : {{(W - V){1'b0}}, cix};
`else
    always @(posedge clk) ci_r <= (pk_go && !vct) ? snd[W-1:1] : {{(W - V){1'b0}}, cix};
`endif
    generate if (HB != 0) begin : g_bo
        reg [W-1:0] bo_r;
        always @(posedge clk or negedge rs_s) if (!rs_s) bo_r <= {W{1'b0}}; else bo_r <= (pk_go && s_dir[3]) ? snd : {W{1'b0}};
        assign bo = bo_r;
    end else begin : g_nobo
        assign bo = {W{1'b0}};                      // C1: no band port (the C1 wrapper does not expose it)
    end endgenerate

    // ---------------------------------------------------------------- RD receive: per-leaf unpackers
    reg [4:0] ub; reg [1:0] un [0:4]; reg [1:0] ul [0:4]; reg [9:0] ur [0:4]; reg [1023:0] ud [0:4];
    reg ucol;
    always @(posedge clk or negedge rs_r)
        if (!rs_r) begin ub <= 5'd0; sw_v <= 5'd0; ucol <= 1'b0; for (k = 0; k < 5; k = k + 1) un[k] <= 2'd0; end
        else begin
            ucol <= 1'b0;
            for (k = 0; k < 5; k = k + 1) begin
                sw_v[k] <= 1'b0;
                if (ub[k]) begin
                    sw_v[k] <= 1'b1; un[k] <= un[k] + 2'd1;
                    if (un[k] == ul[k]) ub[k] <= 1'b0;
                end
                if (rwe[k]) begin
`ifndef OT_S81SL_XR_MUT_NOCOL
                    if (ub[k] && un[k] != ul[k]) ucol <= 1'b1;
`endif
                    ub[k] <= 1'b1; un[k] <= 2'd0;
                end
                if (rwr[k]) begin
                    sw_v[k] <= 1'b1;
                    if (ub[k]) ucol <= 1'b1;
                end
            end
        end
    always @(posedge clk)
        for (k = 0; k < 5; k = k + 1) begin
            if (rwe[k]) begin ul[k] <= rnp; ur[k] <= rrow; ud[k] <= rdat; end
            if (rwr[k]) begin
                sw_a[10 * k +: 10] <= body[9:0]; sw_m[8 * k +: 8] <= {4'd0, body[13:10]};
                sw_d[256 * k +: 256] <= {128'd0, body[141:14]};
            end else begin
`ifdef OT_S81SL_XR_MUT_ROW
                sw_a[10 * k +: 10] <= ur[k] + {8'd0, un[k]};          // mutant: row-pair stride 1 instead of 2
`else
                sw_a[10 * k +: 10] <= ur[k] + {7'd0, un[k], 1'b0};
`endif
                sw_m[8 * k +: 8] <= 8'hff;
                sw_d[256 * k +: 256] <= ud[k][256 * un[k] +: 256];
            end
        end

    // ---------------------------------------------------------------- command fan-out, xfin, streamer, capture
    // c_d / is_d / cfg_d are (* keep *) port registers: one flop per pin (synthesis otherwise folds the equal-D copies into
    // one flop that drives pins on two faces).  XR3 (10-18): c_d / rb_* / g_* leave as ONE copy; ot_s81sl_slice fans them
    // out to the 5 leaves in its glue (the leaf relays), so the tile no longer carries 5 equal 160 / 32 / 35-b pin copies.
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin c_v <= 5'd0; x_go <= 1'b0; is_v <= 1'b0; cfg_v <= 1'b0; x_mode <= 1'b0; end
        else begin
            c_v <= tg[0] ? lmask : 5'd0;
            x_go <= tg[1];
            if (tg[1]) x_mode <= body[32];
            is_v <= tg[2];
            cfg_v <= tg[3];
        end
    always @(posedge clk) begin
        c_d <= body;
        if (tg[1]) begin x_eps <= body[31:0]; x_scale <= body[95:64]; end
        is_d <= body; cfg_d <= body;
    end
    // partial collector: the 5 partials arrive on one edge; xfin takes them in leaf order 0..4 (input timing unchanged)
    reg [31:0] pq [0:4]; reg [2:0] pi; reg prun;
    // ENG collector: 5 triples of one copy -> 15 words (t = 5 kind + leaf)
    reg [95:0] eqd [0:4]; reg [1:0] ecp; reg [3:0] et; reg [2:0] el; reg [1:0] ekd; reg erun; reg ebad;
    always @(*) begin
        ebad = (|ev_c) && (ev_c != 5'b11111);
        for (k = 1; k < 5; k = k + 1) if (ev_c[k] && ec_c[2 * k +: 2] != ec_c[1:0]) ebad = 1'b1;
    end
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin prun <= 1'b0; pi <= 3'd0; x_sv <= 1'b0; rb_v <= 1'b0; erun <= 1'b0; et <= 4'd0; el <= 3'd0;
                         ekd <= 2'd0; g_v <= 1'b0; end
        else begin
            x_sv <= prun || erun;
            if (|pv) begin prun <= 1'b1; pi <= 3'd0; end
            else if (prun) begin pi <= pi + 3'd1; if (pi == 3'd4) prun <= 1'b0; end
            if (|ev_c) begin erun <= 1'b1; et <= 4'd0; el <= 3'd0; ekd <= 2'd0; end
            else if (erun) begin
                et <= et + 4'd1;
                if (el == 3'd4) begin el <= 3'd0; ekd <= ekd + 2'd1; end else el <= el + 3'd1;
                if (et == 4'd14) erun <= 1'b0;
            end
            rb_v <= rbv;
            g_v <= egv_c;
        end
    always @(posedge clk) begin
        for (k = 0; k < 5; k = k + 1) if (pv[k]) pq[k] <= pd[32 * k +: 32];
        for (k = 0; k < 5; k = k + 1) if (ev_c[k]) eqd[k] <= ed_c[96 * k +: 96];
        if (|ev_c) ecp <= ec_c[1:0];
        if (erun) begin x_si <= ({6'd0, ekd} * 8'd4 + {6'd0, ecp}) * 8'd5 + {5'd0, el}; x_s <= eqd[el][32 * ekd +: 32]; end
`ifdef OT_S81SL_XR_MUT_PORDER
        else begin x_si <= {5'd0, pi}; x_s <= pq[3'd4 - pi]; end      // mutant: partials handed to xfin in reverse order
`else
        else begin x_si <= {5'd0, pi}; x_s <= pq[pi]; end
`endif
        rb_d <= rbd;
        g_c <= egc_c; g_d <= egd_c;
    end
    // ---------------------------------------------------------------- faults
    always @(posedge clk or negedge rs_o)
        if (!rs_o) fault <= 1'b0;
        else fault <= fault
`ifdef OT_S81SL_RD_PAIR
                      | (pair_v && (vct || sc_rel || s_mask != (16'd1 << (sid_c ^ 4'd1))))
                      | (s_local && ((|s_dir) || s_kind != K_RD || s_mask != (16'd1 << sid_c)))
`endif
                      | f1 | ucol | ((|pv) && pv != 5'b11111) | ((|pv) && prun) | (vct && (pk_go || sc_rel)) |
                      (pk_go && sc_rel) | (s_scv && esc && wsc) | (tg[4] && (|lov1)) |
                      ebad | ((|ev_c) && (erun || prun || (|pv))) | ((|pv) && erun);
endmodule

// C1 (14 slices): ring E/W + V.  C3 (s_1S, s_6S): + band port B (attention q / P.V).  Hardened masters, no parameters.
module ot_s81sl_xr1 (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1103:0] dl_e, input wire dl_wv, input wire [1103:0] dl_w,
    input  wire dl_vv, input wire [275:0] dl_vb, output wire [2:0] ci_dir, output wire [1103:0] ci_b,
    output wire [4:0] c_v, output wire [159:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire rb_v, output wire [31:0] rb_d,
    input  wire [4:0] e_v, input wire [9:0] e_c, input wire [479:0] e_d, input wire eg_v, input wire [1:0] eg_c,
    input  wire [31:0] eg_d, output wire g_v, output wire [1:0] g_c, output wire [31:0] g_d,
    output wire x_go, output wire x_mode, output wire [31:0] x_eps, output wire [31:0] x_scale, output wire x_sv,
    output wire [7:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);
    wire [1103:0] bo_unused;
    ot_s81sl_xr #(.HB(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi({1104{1'b0}}), .bo(bo_unused), .c_v(c_v), .c_d(c_d),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d), .rb_v(rb_v),
        .rb_d(rb_d), .e_v(e_v), .e_c(e_c), .e_d(e_d), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), .g_v(g_v), .g_c(g_c),
        .g_d(g_d), .x_go(x_go), .x_mode(x_mode), .x_eps(x_eps), .x_scale(x_scale), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd),
        .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
endmodule

module ot_s81sl_xr3 (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1103:0] dl_e, input wire dl_wv, input wire [1103:0] dl_w,
    input  wire dl_vv, input wire [275:0] dl_vb, output wire [2:0] ci_dir, output wire [1103:0] ci_b,
    input  wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4:0] c_v, output wire [159:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire rb_v, output wire [31:0] rb_d,
    input  wire [4:0] e_v, input wire [9:0] e_c, input wire [479:0] e_d, input wire eg_v, input wire [1:0] eg_c,
    input  wire [31:0] eg_d, output wire g_v, output wire [1:0] g_c, output wire [31:0] g_d,
    output wire x_go, output wire x_mode, output wire [31:0] x_eps, output wire [31:0] x_scale, output wire x_sv,
    output wire [7:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);
    ot_s81sl_xr #(.HB(1)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi(bi), .bo(bo), .c_v(c_v), .c_d(c_d),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d), .rb_v(rb_v),
        .rb_d(rb_d), .e_v(e_v), .e_c(e_c), .e_d(e_d), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), .g_v(g_v), .g_c(g_c),
        .g_d(g_d), .x_go(x_go), .x_mode(x_mode), .x_eps(x_eps), .x_scale(x_scale), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd),
        .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
endmodule
