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
// Faults (sticky; checks only, they never reschedule; XR6: terms registered, flag visible 1 cycle after the event): two CTLs / two RDs / two lo beats in a cycle, an RD or a row write into
// a busy leaf unpacker, a partial set that is partial or overlaps the collection, two injections in one ci slot, an RD to
// leaf > 4, a CTL target > 5, two relayed SC beats in a cycle, a lo beat in the send-config cycle (it would be dropped), the ENG faults above.
// Bench: rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_xr.sv (tools/s81_slice/xr_bench.sh); mutants OT_S81SL_XR_MUT_*
// (XHOLD, XR1F-PIN 10-19: the x_eps / x_scale / x_mode output copies do not hold between config writes).
// Every input lands in a flop; every output leaves a flop.  HB = 1 builds the C3 variant (band port B, attention).
// XR7 (LEAD2-S81/SLICE2 10-19, SAFE items 1/3 after the 67954d13c census: 348 FF + 9 comb roots > 32 loads): 0 data cycles.
//  * reset only on valid / control state; every kept copy is reset-free (it is recomputed every edge from reset state, so
//    it is 0 one clock into reset) -> the relay drives <= 32 loads per region (8 regions instead of 4).
//  * the wide classify muxes (RD payload 1024 b, CTL body 160 b, V/SC cix 275 b) are no longer behind the input-flop
//    classifier: the stage-1 registers hold the raw words (eb2 / wb2 / vb2 / bb2) and KEPT registered one-hot selects
//    (one per 8 bits) pick them.  The classifier's comb fan-out now ends only on D pins of kept copies.
//  * kept-copy granularity follows the mapped pins per bit (~3 for enabled flops / 2:1 muxes, ~4.4 for the 4:1 unpacker read):
//    8 bits per copy for enables / selects, 16 bits for 2-pin selects -> <= ~32 pins per register.
// Band port B (BIND mu4 10-19): B is point-to-point to the svc_rs ENTRY q port, which consumes {pk[511:0], valid} only, so
// bo is 513 b = {pk[511:0], 1'b1} (no header, no upper pack words: they had no consumer anywhere).  A send config with
// dir B and pairs > 2 (body[42] = 1) cannot be carried and is a sticky fault (the compiler must never emit one).
// S81-SMWIRE (10-19): SO gather words on B (C3 only).  The svc entry's P.V lane also carries, in the compiler's booked
// gather window, the SO target beats as 3 words each (lo 512, hi 512, header {magic 5A, owner, head, group, idx}); the
// landing dsfd_dvland_pvrd hands them over as B words of kind 2 (o[4] header flag, o[6:5] route).  xr assembles one XB
// ring beat {v, kind XB, hops 0, src sid, idx [19:13], data [21 +: 1024]} and injects it on ci on the edge after the
// header: route 1 = tier line E + W (line default hops; ot_s81sl_rstop also delivers it to its own x streamer), route 2
// = V (rstop sends it as the 4-fragment V train; the column partner delivers it and fans it out on its line).  Faults
// (sticky): a word out of order (lo / hi with the header flag, a header without it), a bad magic, route 0 / 3, an SO
// injection in the same ci slot as a CTL re-injection / send / SC relay.
// ---------------------------------------------------------------------------------------------------------------------
`ifdef OT_S81SL_XR_FOREG
`define OT_S81SL_XR_FOREG_DEF 1
`else
`define OT_S81SL_XR_FOREG_DEF 0
`endif
module ot_s81sl_xr #(
    parameter integer HB = 0,
    parameter integer FOREG = 0,          // XR6 fallback: dedicated fault output flop (+1 more fault-visibility cycle)
    parameter integer W  = 1104,
    parameter integer V  = 276,
    parameter integer BW = 513           // band port B word (BIND mu4 10-19): {pk[511:0], valid}, point-to-point to the entry q
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
    output wire [BW-1:0]   bo,
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
    output wire            x_mode,
    output wire [31:0]     x_eps,
    output wire [31:0]     x_scale,
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
    // XR7: 8 relay regions, each <= 32 reset loads (r0 input valids, r1/r2 stage-1 control, r3 unpacker, r4 send, r5 outputs,
    // r6 ENG word one-hot, r7 partial one-hot / run copies / faults).
    wire [7:0] rsv;
    ot_rst_relay #(.REGIONS(8), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_c1 = rsv[1], rs_c2 = rsv[2], rs_r = rsv[3], rs_s = rsv[4], rs_o = rsv[5], rs_e = rsv[6],
         rs_f = rsv[7];
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
    // XR5 (S81-SAFE-FIX 10-19, checklist item 3): kept copies of the lo_v input flop for each leaf's lo_d gate (lov[k]
    // drove 256 AND gates); same D, same edge -> function and cycles unchanged.  XR7: one per 16 bits (was 32: 37 pins),
    // reset-free (data gate only).  evd_c / pvd_c: kept copies of the e_v / p_v input flops, one per 8 bits of the eqd /
    // pq capture enables (ev_c / pv drove 197 / 66 pins); the masters keep only the control decode.
    (* keep *) reg [5*16-1:0] lov_c; (* keep *) reg [5*12-1:0] evd_c; (* keep *) reg [5*4-1:0] pvd_c;
    always @(posedge clk) begin
        for (k = 0; k < 80; k = k + 1) lov_c[k] <= lo_v[k / 16];
        for (k = 0; k < 60; k = k + 1) evd_c[k] <= e_v[k / 12];
        for (k = 0; k < 20; k = k + 1) pvd_c[k] <= p_v[k / 4];
    end
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
    wire b_so = bv && bb[3:1] == 3'd2;                            // S81-SMWIRE: SO gather word (landing kind 2)
    wire b_rd = bv && !b_so;
    wire e_sc = ev && eb[3:1] == K_SC, w_sc = wv && wb[3:1] == K_SC;
    wire [185:0] pe = eb[21 +: 186], pw = wb[21 +: 186], pvv = vb[21 +: 186];
    wire mine_e = |(pe[15:0] & sid_oh), mine_w = |(pw[15:0] & sid_oh), mine_v = |(pvv[15:0] & sid_oh);
    wire ce = e_ctl && mine_e, cw = w_ctl && mine_w, cv = v_ctl && mine_v;
    wire [185:0] cp = ce ? pe : cw ? pw : pvv;
    wire [4:0] tgt0 = cp[20:16], lmask0 = cp[25:21];
    wire re = e_rd && mine_e, rw_ = w_rd && mine_w;
    wire rdv0 = re || rw_ || b_rd;
    wire [W-1:0] rdb0 = re ? eb : rw_ ? wb : bb;
    wire [2:0] rl0 = rdb0[37 +: 3];
    reg [2:0] nlo0; reg [255:0] lo_sel0;
    always @(*) begin
        nlo0 = 3'd0; lo_sel0 = 256'd0;
        for (k = 0; k < 5; k = k + 1) nlo0 = nlo0 + lov[k];
        for (k = 0; k < 80; k = k + 1) if (lov_c[k]) lo_sel0[16 * (k % 16) +: 16] = lo_sel0[16 * (k % 16) +: 16] | lod[16 * k +: 16];
    end
    wire [V-1:0] sc_b0 = e_sc ? eb[V-1:0] : wb[V-1:0];
    // stage-1 registers
    reg cvld, vct, esc, wsc, rdv, f1; reg [5:0] tg; reg [4:0] lmask, rwe, rwr, lov1;
    reg [1:0] rnp; reg [9:0] rrow; reg [255:0] lo_sel;
    // XR7: raw words for the wide selects (data only: no reset, no enable) + KEPT registered one-hot selects, one per 8 bits
    //   rdat = rse ? eb : rsw ? wb : bb  (rdb0[52 +: 1024]),  body = bse ? pe : bsw ? pw : pvv  (cp[185:26]),
    //   cix  = cvc ? V re-inject word : cse ? eb : wb  (old stage-1 cix).  Same values on the same edge as the XR6 registers.
    reg [W-2:0] eb2, wb2; reg [V-2:0] vb2; reg [1023:0] bb2;
    (* keep *) reg [127:0] rse_c, rsw_c; (* keep *) reg [19:0] bse_c, bsw_c; (* keep *) reg [34:0] cvc_c, cse_c;
    // XR5/XR7 (checklist item 3): registered selects replicated as KEPT, reset-free copies, <= ~32 mapped pins each:
    // rwe_c = rwe per 8 bits of a leaf's 1024-b unpacker, rwr_c = rwr per 8 bits of a leaf's 256-b sw_d, tg1_c = tg[1] per
    // 8 bits of x_eps / x_scale, tg4_c = tg[4] per 8 bits of the send config.  Same D as the masters -> function unchanged.
    (* keep *) reg [5*128-1:0] rwe_c; (* keep *) reg [5*32-1:0] rwr_c; (* keep *) reg [7:0] tg1_c; (* keep *) reg [5:0] tg4_c;
    // XR3-CLS (S81-XR3 10-20, SAFE items 2 / 3 / 4 after the first xr3 route s81sl_xr3-6585bf71d: TT -144.7, 913 reg->reg D
    // pins; worst eb[25] -> 3 wire buffers -> mine_e -> ce -> cp mux -> tgt0 / lmask0 decode -> wire -> rwr[2]: the C3
    // outline is 570 um wide (band port B pins), so the one-cycle stage-1 classify spans E face -> W face = REACH + DEPTH).
    // C3 (HB != 0) splits the classify into two registered stages; C1 (HB == 0, closed s81sl_xr1f) keeps the single stage
    // (CLS = 0: every d_* below is the XR7 expression, the C1 netlist is unchanged).
    //   stage 1a (per SOURCE, beside its input flops; KEPT copies, reset-free): a source's own one-hot flags only --
    //     mine CTL / mine RD / SC / V-CTL, the target one-hot (target 0..5, > 5), leaf mask, the per-leaf row-write and RD
    //     enables (rwr / rwe one-hot per leaf), RD leaf > 4, RD pairs / row; the raw words (eb1 / wb1 / vb1 / bb1, and the
    //     B header bits for the SO assembler); a per-source sid one-hot (sid strap copied per face, 2 hops).  No
    //     cross-source logic.
    //   stage 1b (the XR7 stage-1 registers): OR / priority of the three sources' registered one-hots (<= 3 levels), so
    //     the long E -> W wires carry registered one-hots only.  Legal programs have at most one mine CTL and one RD per
    //     cycle (two are the sticky f1 fault), so the wide enables are the OR of the source one-hots; the word selects keep
    //     the XR7 priority (rse ? eb : rsw ? wb : bb).
    // Cycles (one contract): C3 == C1 with every RING / V / BAND input (dl_e, dl_w, dl_vb, bi incl. the SO gather words)
    // landing ONE edge later.  The leaf-side inputs (lo, partials, ENG, rstd) are NOT delayed: they are consequences of CTL
    // commands this xr issued, so the whole C3 slice timeline moves +1 edge and every compiled relative timing (send
    // config vs its lo beats, V re-inject / send / SC / SO ci slots) is unchanged.  Handed to the die schedule (C3 entry
    // s_4S: V CTL inject 8 edges vs 7 on C1) and priced in results/rtl/s81_xr3_1020/SCHEDULE.json.
    localparam integer CLS = (HB != 0) ? 1 : 0;
    wire d_cvld, d_vct, d_esc, d_wsc, d_rdv, d_f1; wire [5:0] d_tg; wire [4:0] d_rwe, d_rwr, d_lov1;
    wire [5*128-1:0] d_rwe_c; wire [5*32-1:0] d_rwr_c; wire [7:0] d_tg1_c; wire [5:0] d_tg4_c;
    wire [127:0] d_rse, d_rsw; wire [19:0] d_bse, d_bsw; wire [34:0] d_cvc, d_cse;
    wire [4:0] d_lmask; wire [1:0] d_rnp; wire [9:0] d_rrow; wire [255:0] d_lo_sel;
    wire [W-2:0] s_eb, s_wb; wire [V-2:0] s_vb; wire [1023:0] s_bb;
    wire nx_lov, nx_vct, nx_sc;                // next-state terms of the stage-1 registers (kept-copy D's below)
    wire so_x_v; wire [6:0] so_x_h; wire [511:0] so_x_d;   // the SO assembler's B word: valid kind 2, header bits [6:0], lo 512
    // XR3-CLS census (pre-gate native census of d7dad8450: 19 drivers > 32 loads, C3 only below; C1 keeps the XR7 nets):
    // per-group copies so that no driver feeds more than 32 pins -- cis / sos select groups (3 x <= 24 of NCI 69) take
    // their own V-CTL copy, the SO lo / hi enables (3 x <= 22 of 64) their own B-valid copy.
    wire [2:0] cisv_c, sosv_c, so_xv_c;
    generate if (CLS == 0) begin : g_cls1
        wire any_c = ce || cw || cv;
        genvar g;
        for (g = 0; g < 6; g = g + 1) begin : g_tg assign d_tg[g] = any_c && tgt0 == g; end
        for (g = 0; g < 5; g = g + 1) begin : g_lf
            assign d_rwe[g] = rdv0 && rl0 == g;
            assign d_rwr[g] = any_c && tgt0 == 5'd5 && lmask0[g];
        end
        for (g = 0; g < 640; g = g + 1) begin : g_rwec assign d_rwe_c[g] = rdv0 && rl0 == g / 128; end
        for (g = 0; g < 160; g = g + 1) begin : g_rwrc assign d_rwr_c[g] = any_c && tgt0 == 5'd5 && lmask0[g / 32]; end
        assign d_cvld = any_c; assign d_vct = v_ctl; assign d_esc = e_sc; assign d_wsc = w_sc; assign d_rdv = rdv0;
        assign d_f1 = ((ce + cw + cv) > 2'd1) || ((re + rw_ + b_rd) > 2'd1) || (nlo0 > 3'd1) || (rdv0 && rl0 > 3'd4) ||
                      (any_c && tgt0 > 5'd5);
        assign d_lov1 = lov;
        assign d_tg1_c = {8{any_c && tgt0 == 5'd1}}; assign d_tg4_c = {6{any_c && tgt0 == 5'd4}};
        assign d_rse = {128{re}}; assign d_rsw = {128{!re && rw_}};
        assign d_bse = {20{ce}}; assign d_bsw = {20{!ce && cw}};
        assign d_cvc = {35{v_ctl}}; assign d_cse = {35{!v_ctl && e_sc}};
        assign d_lmask = lmask0; assign d_rnp = rdb0[50 +: 2]; assign d_rrow = rdb0[40 +: 10]; assign d_lo_sel = lo_sel0;
        assign s_eb = eb[W-1:1]; assign s_wb = wb[W-1:1]; assign s_vb = vb[V-1:1];
        assign s_bb = (HB != 0) ? bb[52 +: 1024] : 1024'd0;
        assign nx_lov = |lov; assign nx_vct = v_ctl; assign nx_sc = e_sc || w_sc;
        assign so_x_v = b_so; assign so_x_h = bb[6:0]; assign so_x_d = bb[52 +: 512];
        assign cisv_c = {3{v_ctl}}; assign sosv_c = {3{v_ctl}}; assign so_xv_c = {3{b_so}};
    end else begin : g_cls2
        // ---- stage 1a: per-source sid one-hot (strap; 2 hops so no single-cycle wire crosses the tile)
        (* keep *) reg [3:0] sid_e, sid_w, sid_v; (* keep *) reg [15:0] soh_e, soh_w, soh_v;
        always @(posedge clk) begin
            sid_e <= sid_c; sid_w <= sid_c; sid_v <= sid_c;
            soh_e <= 16'd1 << sid_e; soh_w <= 16'd1 << sid_w; soh_v <= 16'd1 << sid_v;
        end
        wire me = |(pe[15:0] & soh_e), mw = |(pw[15:0] & soh_w), mv = |(pvv[15:0] & soh_v);
        wire ce3 = e_ctl && me, cw3 = w_ctl && mw, cv3 = v_ctl && mv;
        wire re3 = e_rd && me, rw3 = w_rd && mw;
        // flags (KEPT copies sized for <= ~17 stage-1b loads each; reset-free: the valids they decode are reset input
        // flops, so every flag is 0 one clock into reset)
        (* keep *) reg [1:0] ce_a, cw_a, cv_a, scw_a; (* keep *) reg [2:0] sce_a; (* keep *) reg [8:0] re_a, rw_a;
        (* keep *) reg [10:0] vct_a;            // [0] vct, [4:1] cvc_c groups, [5] cis/sos master-next, [7:6]+[5] cis, [10:8] sos
        (* keep *) reg [2:0] bbv1;              // B valid copies for the SO lo / hi enable groups
        reg brd_a;
        reg [5:0] tge_a, tgw_a, tgv_a; reg tbe_a, tbw_a, tbv_a; reg [4:0] lme_a, lmw_a, lmv_a;
        (* keep *) reg [9:0] rwre_a, rwrw_a, rwrv_a;             // [2 k + j]: leaf k row write, copy j (16 rwr_c each)
        (* keep *) reg [39:0] rwee_a, rwew_a, rweb_a;            // [8 k + j]: leaf k RD enable, copy j (16 rwe_c each)
        reg rbe_a, rbw_a, rbb_a; reg [1:0] npe_a, npw_a, npb_a; reg [9:0] rowe_a, roww_a, rowb_a;
        reg nlo2_a;
        reg [W-2:0] eb1, wb1; reg [V-2:0] vb1; reg [1023:0] bb1; reg [6:0] bbh1;
        integer q, j;
        always @(posedge clk) begin
            ce_a <= {2{ce3}}; cw_a <= {2{cw3}}; cv_a <= {2{cv3}}; sce_a <= {3{e_sc}}; scw_a <= {2{w_sc}};
            re_a <= {9{re3}}; rw_a <= {9{rw3}}; vct_a <= {11{v_ctl}}; brd_a <= b_rd; bbv1 <= {3{bb[0]}};
            for (q = 0; q < 6; q = q + 1) begin
                tge_a[q] <= ce3 && pe[20:16] == q; tgw_a[q] <= cw3 && pw[20:16] == q; tgv_a[q] <= cv3 && pvv[20:16] == q;
            end
            tbe_a <= ce3 && pe[20:16] > 5'd5; tbw_a <= cw3 && pw[20:16] > 5'd5; tbv_a <= cv3 && pvv[20:16] > 5'd5;
            lme_a <= pe[25:21]; lmw_a <= pw[25:21]; lmv_a <= pvv[25:21];
            for (q = 0; q < 5; q = q + 1) for (j = 0; j < 2; j = j + 1) begin
                rwre_a[2 * q + j] <= ce3 && pe[20:16] == 5'd5 && pe[21 + q];
                rwrw_a[2 * q + j] <= cw3 && pw[20:16] == 5'd5 && pw[21 + q];
                rwrv_a[2 * q + j] <= cv3 && pvv[20:16] == 5'd5 && pvv[21 + q];
            end
            for (q = 0; q < 5; q = q + 1) for (j = 0; j < 8; j = j + 1) begin
                rwee_a[8 * q + j] <= re3 && eb[39:37] == q;
                rwew_a[8 * q + j] <= rw3 && wb[39:37] == q;
                rweb_a[8 * q + j] <= b_rd && bb[39:37] == q;
            end
            rbe_a <= re3 && eb[39:37] > 3'd4; rbw_a <= rw3 && wb[39:37] > 3'd4; rbb_a <= b_rd && bb[39:37] > 3'd4;
            npe_a <= eb[51:50]; npw_a <= wb[51:50]; npb_a <= bb[51:50];
            rowe_a <= eb[49:40]; roww_a <= wb[49:40]; rowb_a <= bb[49:40];
            nlo2_a <= nlo0 > 3'd1;                   // two lo beats in a cycle (sticky fault; visible 1 edge later)
            eb1 <= eb[W-1:1]; wb1 <= wb[W-1:1]; vb1 <= vb[V-1:1]; bb1 <= bb[52 +: 1024]; bbh1 <= bb[6:0];
        end
        // ---- stage 1b D's: OR / priority of the registered source one-hots
        genvar g;
        for (g = 0; g < 6; g = g + 1) begin : g_tg assign d_tg[g] = tge_a[g] | tgw_a[g] | tgv_a[g]; end
        for (g = 0; g < 5; g = g + 1) begin : g_lf
            assign d_rwe[g] = rwee_a[8 * g] | rwew_a[8 * g] | rweb_a[8 * g];
            assign d_rwr[g] = rwre_a[2 * g] | rwrw_a[2 * g] | rwrv_a[2 * g];
        end
        for (g = 0; g < 640; g = g + 1) begin : g_rwec           // leaf g / 128, copy (g % 128) / 16
`ifdef OT_S81SL_XR_MUT_CLS
            // mutant: the leaf-2 copy-5 RD enables take only the E source (W / B RDs lose 8 B of their row pair)
            if (g / 128 == 2 && (g % 128) / 16 == 5) begin : g_m assign d_rwe_c[g] = rwee_a[8 * 2 + 5]; end
            else begin : g_n
`else
            begin : g_n
`endif
            assign d_rwe_c[g] = rwee_a[8 * (g / 128) + (g % 128) / 16] | rwew_a[8 * (g / 128) + (g % 128) / 16] |
                                rweb_a[8 * (g / 128) + (g % 128) / 16];
            end
        end
        for (g = 0; g < 160; g = g + 1) begin : g_rwrc           // leaf g / 32, copy (g % 32) / 16
            assign d_rwr_c[g] = rwre_a[2 * (g / 32) + (g % 32) / 16] | rwrw_a[2 * (g / 32) + (g % 32) / 16] |
                                rwrv_a[2 * (g / 32) + (g % 32) / 16];
        end
        for (g = 0; g < 128; g = g + 1) begin : g_rs assign d_rse[g] = re_a[1 + g / 16]; assign d_rsw[g] = rw_a[1 + g / 16]; end
        for (g = 0; g < 35; g = g + 1) begin : g_cx assign d_cvc[g] = vct_a[1 + g / 9]; end
        assign d_cvld = ce_a[0] | cw_a[0] | cv_a[0]; assign d_vct = vct_a[0]; assign d_esc = sce_a[0]; assign d_wsc = scw_a[0];
        assign d_rdv = re_a[0] | rw_a[0] | brd_a;
        assign d_f1 = ((ce_a[0] + cw_a[0] + cv_a[0]) > 2'd1) || ((re_a[0] + rw_a[0] + brd_a) > 2'd1) || nlo2_a ||
                      rbe_a || rbw_a || rbb_a || tbe_a || tbw_a || tbv_a;
        assign d_lov1 = lov;                                               // lo is not delayed (see above)
        assign d_tg1_c = {8{tge_a[1] | tgw_a[1] | tgv_a[1]}}; assign d_tg4_c = {6{tge_a[4] | tgw_a[4] | tgv_a[4]}};
        assign d_bse = {20{ce_a[1]}}; assign d_bsw = {20{cw_a[1]}};        // word priority kept by the body mux (bse first)
        for (g = 0; g < 35; g = g + 1) begin : g_cs assign d_cse[g] = sce_a[1 + g / 18]; end   // cix priority: cvc, then cse
        assign d_lmask = ce_a[0] ? lme_a : cw_a[0] ? lmw_a : lmv_a;
        assign d_rnp = re_a[0] ? npe_a : rw_a[0] ? npw_a : npb_a; assign d_rrow = re_a[0] ? rowe_a : rw_a[0] ? roww_a : rowb_a;
        assign d_lo_sel = lo_sel0;
        assign s_eb = eb1; assign s_wb = wb1; assign s_vb = vb1; assign s_bb = bb1;
        assign nx_lov = |lov; assign nx_vct = vct_a[5]; assign nx_sc = sce_a[0] | scw_a[0];
        assign so_x_v = bbh1[0] && bbh1[3:1] == 3'd2; assign so_x_h = bbh1; assign so_x_d = bb1[511:0];   // SO +1 edge
        assign cisv_c = {vct_a[7:6], vct_a[5]}; assign sosv_c = vct_a[10:8];
        for (g = 0; g < 3; g = g + 1) begin : g_sov assign so_xv_c[g] = bbv1[g] && bbh1[3:1] == 3'd2; end
    end endgenerate
    always @(posedge clk or negedge rs_c1)
        if (!rs_c1) begin cvld <= 1'b0; vct <= 1'b0; esc <= 1'b0; wsc <= 1'b0; rdv <= 1'b0; f1 <= 1'b0; tg <= 6'd0; end
        else begin
            cvld <= d_cvld; vct <= d_vct; esc <= d_esc; wsc <= d_wsc; rdv <= d_rdv;
            tg <= d_tg;
            // input-only faults: two CTLs / two RDs / two lo beats in a cycle, an RD to leaf > 4, a CTL target > 5
            f1 <= d_f1;
        end
    always @(posedge clk or negedge rs_c2)
        if (!rs_c2) begin rwe <= 5'd0; rwr <= 5'd0; lov1 <= 5'd0; end
        else begin
            lov1 <= d_lov1;
            rwe <= d_rwe;
            rwr <= d_rwr;
        end
    always @(posedge clk) begin
        rwe_c <= d_rwe_c;
        rwr_c <= d_rwr_c;
        tg1_c <= d_tg1_c;
        tg4_c <= d_tg4_c;
        rse_c <= d_rse; rsw_c <= d_rsw;
        bse_c <= d_bse; bsw_c <= d_bsw;
        cvc_c <= d_cvc; cse_c <= d_cse;
        eb2 <= s_eb; wb2 <= s_wb; vb2 <= s_vb; bb2 <= s_bb;
        lmask <= d_lmask; rnp <= d_rnp; rrow <= d_rrow;
        lo_sel <= d_lo_sel;
    end
    reg [1023:0] rdat; reg [159:0] body; reg [V-2:0] cix;
    always @(*) begin
        for (k = 0; k < 1024; k = k + 1)
            rdat[k] = rse_c[k / 8] ? eb2[51 + k] : rsw_c[k / 8] ? wb2[51 + k] : bb2[k];
        for (k = 0; k < 160; k = k + 1)
            body[k] = bse_c[k / 8] ? eb2[46 + k] : bsw_c[k / 8] ? wb2[46 + k] : vb2[46 + k];
        for (k = 0; k < V - 1; k = k + 1)
`ifdef OT_S81SL_XR_MUT_HOPS
            cix[k] = cvc_c[k / 8] ? vb2[k] :                                // mutant: re-injected CTL keeps the V hops
`else
            cix[k] = cvc_c[k / 8] ? ((k >= 3 && k < 8) ? 1'b0 : vb2[k]) :
`endif
                     cse_c[k / 8] ? eb2[k] : wb2[k];
    end

    // ---------------------------------------------------------------- send config, packing, injection
    // body: [3:0] dir {B, V, W, E}, [6:4] kind, [11:7] hops, [27:12] dst slice mask, [30:28] dst leaf, [40:31] dst row,
    //       [42:41] pairs - 1, [43] SC relay to V
    reg [3:0] s_dir; reg [2:0] s_kind; reg [4:0] s_hops; reg [15:0] s_mask; reg [2:0] s_leaf; reg [9:0] s_row; reg [1:0] s_np;
    reg s_scv;
    reg [1023:0] pk; reg [1:0] pn; reg pk_go;
    reg [W-1:0] snd;
    // XR5: pkw_c[8 p + g] = (|lov1) && pn == p for 32-bit word g of pair p, and cis_c[g] = pk_go && !vct for the 32-bit
    // word g of ci_r, both registered from the next-state of their masters (KEPT copies; equal to the old decode every
    // cycle, the relay regions rs_c / rs_s release on the same edge).
    // XR7: pkw_c one per 8 bits (was 32: 64 pins), cis_c one per 16 bits (was 32: 64 pins); both reset-free.
    localparam integer NCI = (W + 14) / 16;
    (* keep *) reg [4*32-1:0] pkw_c; (* keep *) reg [NCI-1:0] cis_c;
    wire [1:0] pn_nx = tg[4] ? 2'd0 : (|lov1) ? ((pn == s_np) ? 2'd0 : pn + 2'd1) : pn;
    wire pk_go_nx = !tg[4] && (|lov1) && pn == s_np;
    always @(posedge clk) begin
        for (k = 0; k < 128; k = k + 1) pkw_c[k] <= nx_lov && pn_nx == k / 32;
        for (k = 0; k < NCI; k = k + 1) cis_c[k] <= pk_go_nx && !cisv_c[k / 24];
    end
    // S81-SMWIRE x XR7: sos_c[g] = so_go && !vct && !sc_rel && !pk_go (the SO beat owns ci_r), registered from next state;
    // reset-free (so_n is reset, so so_go_nx is 0 one clock into reset).
    // C1 (HB = 0) has no B port, so no SO beat: no sos_c flops there (the C1 netlist keeps its closed XR7 structure).
    wire [NCI-1:0] sos_c;
    wire so_go_nx;
    wire sc_rel_nx = (tg[4] ? body[43] : s_scv) && nx_sc;
    generate if (HB != 0) begin : g_sos
        (* keep *) reg [NCI-1:0] sos_r;
        always @(posedge clk)
            for (k = 0; k < NCI; k = k + 1) sos_r[k] <= so_go_nx && !sosv_c[k / 24] && !sc_rel_nx && !pk_go_nx;
        assign sos_c = sos_r;
    end else begin : g_nosos
        assign sos_c = {NCI{1'b0}};
    end endgenerate
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin s_dir <= 4'd0; pn <= 2'd0; pk_go <= 1'b0; s_scv <= 1'b0; end
        else begin
            pk_go <= 1'b0;
            if (tg[4]) begin
                s_dir <= body[3:0]; s_scv <= body[43]; pn <= 2'd0;
            end else if (|lov1) begin
                pn <= (pn == s_np) ? 2'd0 : pn + 2'd1;
                pk_go <= pn == s_np;
            end
        end
    always @(posedge clk) begin                                  // send-config data fields: tg4_c copies (data, no reset)
        if (tg4_c[0]) begin s_kind <= body[6:4]; s_hops <= body[11:7]; end
        if (tg4_c[1]) s_mask[7:0] <= body[19:12];
        if (tg4_c[2]) s_mask[15:8] <= body[27:20];
        if (tg4_c[3]) s_leaf <= body[30:28];
        if (tg4_c[4]) s_row <= body[40:31];
        if (tg4_c[5]) s_np <= body[42:41];
    end
    always @(posedge clk)                                        // fixed-index pair writes (decoded pn, kept copies)
        for (k = 0; k < 128; k = k + 1) if (pkw_c[k]) pk[8 * k +: 8] <= lo_sel[8 * (k % 32) +: 8];
    always @(*) begin
        snd = {W{1'b0}};
        snd[0] = 1'b1; snd[3:1] = s_kind; snd[8:4] = s_hops; snd[12:9] = sid_c; snd[20:13] = 8'd0;
        snd[21 +: 16] = s_mask; snd[37 +: 3] = s_leaf; snd[40 +: 10] = s_row; snd[50 +: 2] = s_np; snd[52 +: 1024] = pk;
    end
    // S81-SMWIRE: SO gather words -> one XB ring beat (assembled from the B input flops; injected on the next edge)
    reg [1:0] so_n; wire [511:0] so_lo, so_hi; reg so_go, so_f; reg [6:0] so_idx; reg [1:0] so_rt;
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin so_n <= 2'd0; so_go <= 1'b0; so_f <= 1'b0; end
        else begin
            so_go <= 1'b0;
            if (so_x_v) begin
                if (so_n == 2'd2) begin
                    so_n <= 2'd0;
                    if (!so_x_h[4] || so_x_d[32 +: 8] != 8'h5A || so_x_h[6:5] == 2'd0 || so_x_h[6:5] == 2'd3) so_f <= 1'b1;
                    else so_go <= 1'b1;
                end else begin
                    so_n <= so_n + 2'd1;
                    if (so_x_h[4]) so_f <= 1'b1;
                end
            end
        end
    always @(posedge clk) if (so_x_v && so_n == 2'd2) begin so_idx <= so_x_d[6:0]; so_rt <= so_x_h[6:5]; end
    // ROOT4-S81POST (10-19, SAFE item 3): the lo / hi capture enables (b_so && so_n == 0 / 1) drove 512 loads each.  Now the
    // word is staged one edge (so_w, no enable) and so_lo / so_hi capture so_w under KEPT registered enable copies, one per
    // 8 bits (64 + 64 flops, D = the decode's next state, <= ~24 pins each).  lo is captured one edge after its B word,
    // hi one edge after its B word = on the header edge, so both are valid in the so_go cycle exactly as before:
    // so_b, ci_r and every SO cycle are unchanged (0 cycles).  C1 (HB = 0) has no B port: none of these flops there.
    generate if (HB != 0) begin : g_soc
        reg [511:0] so_w, so_lo_r, so_hi_r;
        (* keep *) reg [63:0] sol_c; (* keep *) reg [63:0] soh_c;
        always @(posedge clk) begin
            so_w <= so_x_d;
`ifdef OT_S81SL_XR_MUT_SOEN
            for (k = 0; k < 64; k = k + 1) begin sol_c[k] <= so_xv_c[k / 22] && so_n == 2'd0; soh_c[k] <= so_xv_c[k / 22] && so_n == 2'd0; end
`else
            for (k = 0; k < 64; k = k + 1) begin sol_c[k] <= so_xv_c[k / 22] && so_n == 2'd0; soh_c[k] <= so_xv_c[k / 22] && so_n == 2'd1; end
`endif
            for (i = 0; i < 512; i = i + 1) begin
                if (sol_c[i / 8]) so_lo_r[i] <= so_w[i];
                if (soh_c[i / 8]) so_hi_r[i] <= so_w[i];
            end
        end
        assign so_lo = so_lo_r; assign so_hi = so_hi_r;
    end else begin : g_nosoc
        assign so_lo = 512'd0; assign so_hi = 512'd0;
    end endgenerate
    assign so_go_nx = so_x_v && so_n == 2'd2 && so_x_h[4] && so_x_d[32 +: 8] == 8'h5A && so_x_h[6:5] != 2'd0 &&
                      so_x_h[6:5] != 2'd3;
    wire [W-1:0] so_b = {{(W - 1045){1'b0}}, so_hi, so_lo, 1'b0, so_idx, sid_c, 5'd0, 3'd2, 1'b1};
    // V-from-G-unit CTL re-injection on the tier line (both sides, hops 0 = line default), SC relay to V
    wire sc_rel = s_scv && (esc || wsc);
    reg ci_v; reg [W-2:0] ci_r;
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin ci_dir <= 3'd0; ci_v <= 1'b0; end
        else begin
            ci_dir <= vct ? 3'b011 : pk_go ? s_dir[2:0] : sc_rel ? 3'b100 : so_go ? ((so_rt == 2'd1) ? 3'b011 : 3'b100) :
                      3'b000;
            ci_v <= vct || (pk_go && |s_dir[2:0]) || sc_rel || so_go;
        end
    assign ci_b = {ci_r, ci_v};
    // S81-SMWIRE x XR7 (ROOT4 merge 10-19): the SO beat select is a KEPT registered copy per 16 bits, like cis_c; its D is
    // so_go's next state with the same priority as before the merge (send first; no SO beat beside a CTL re-injection /
    // SC relay), so ci_r is unchanged: (pk_go && !vct) ? snd : (so_go && !vct && !sc_rel) ? so_b : cix.
    wire [W-2:0] cixw = {{(W - V){1'b0}}, cix};
    always @(posedge clk) for (i = 0; i < W - 1; i = i + 1)
        ci_r[i] <= cis_c[i / 16] ? snd[i + 1] : sos_c[i / 16] ? so_b[i + 1] : cixw[i];
    generate if (HB != 0) begin : g_bo
        reg [BW-1:0] bo_r;
        // XR7: only the valid bit bo_r[0] is reset; the payload is cleared every idle edge (0 one clock into reset).
        // BIND mu4: bo = {pk[511:0], valid} (513 b).
        always @(posedge clk or negedge rs_s) if (!rs_s) bo_r[0] <= 1'b0; else bo_r[0] <= pk_go && s_dir[3];
        // XR3-CLS census: the payload select (pk_go && s_dir[3]) drove 513 pins -> KEPT copies, one per 16 bits, registered
        // from its next state (pk_go_nx implies no send config this edge, so s_dir holds): same value every cycle.
        (* keep *) reg [(BW - 1) / 16 - 1:0] bos_c;
        always @(posedge clk) for (k = 0; k < (BW - 1) / 16; k = k + 1) bos_c[k] <= pk_go_nx && s_dir[3];
        always @(posedge clk) for (k = 0; k < BW - 1; k = k + 1) bo_r[1 + k] <= bos_c[k / 16] && pk[k];
        assign bo = bo_r;
    end else begin : g_nobo
        assign bo = {BW{1'b0}};                     // C1: no band port (the C1 wrapper does not expose it)
    end endgenerate

    // ---------------------------------------------------------------- RD receive: per-leaf unpackers
    reg [4:0] ub; reg [1:0] un [0:4]; reg [1:0] ul [0:4]; reg [9:0] ur [0:4]; reg [1023:0] ud [0:4];
    reg ucol;
    // XR5: un_c[32 k + 2 g +: 2] = un[k] per 16-bit half-word g of leaf k's sw_d read (the 4:1 row-pair select drove ~512
    // mux loads per bit; now <= 32); KEPT copies registered from un's next state.
    // XR7: one copy per 8 bits (was 16: 70 pins), reset-free (un_nx is a function of reset state).
    (* keep *) reg [5*32*2-1:0] un_c; reg [1:0] un_nx [0:4];
    always @(*)
        for (k = 0; k < 5; k = k + 1) begin
            un_nx[k] = un[k];
            if (ub[k]) un_nx[k] = un[k] + 2'd1;
            if (rwe[k]) un_nx[k] = 2'd0;
        end
    always @(posedge clk) for (k = 0; k < 160; k = k + 1) if (CLS == 0 || k % 32 != 31) un_c[2 * k +: 2] <= un_nx[k / 32];
    // XR3-CLS census (C3): un_nx drove 32 copies + the master = 33 pins -> the master un[k] serves the last 8-bit word.
    wire [5*32*2-1:0] un_r;
    genvar gu, gi;
    generate for (gu = 0; gu < 5; gu = gu + 1) begin : g_unr
        for (gi = 0; gi < 32; gi = gi + 1) begin : g_w
            if (CLS != 0 && gi == 31) begin : g_m assign un_r[64 * gu + 2 * gi +: 2] = un[gu]; end
            else begin : g_c assign un_r[64 * gu + 2 * gi +: 2] = un_c[64 * gu + 2 * gi +: 2]; end
        end
    end endgenerate
    always @(posedge clk or negedge rs_r)
        if (!rs_r) begin ub <= 5'd0; sw_v <= 5'd0; ucol <= 1'b0; for (k = 0; k < 5; k = k + 1) un[k] <= 2'd0; end
        else begin
            ucol <= 1'b0;
            for (k = 0; k < 5; k = k + 1) begin
                sw_v[k] <= 1'b0;
                un[k] <= un_nx[k];
                if (ub[k]) begin
                    sw_v[k] <= 1'b1;
                    if (un[k] == ul[k]) ub[k] <= 1'b0;
                end
                if (rwe[k]) begin
`ifndef OT_S81SL_XR_MUT_NOCOL
                    if (ub[k] && un[k] != ul[k]) ucol <= 1'b1;
`endif
                    ub[k] <= 1'b1;
                end
                if (rwr[k]) begin
                    sw_v[k] <= 1'b1;
                    if (ub[k]) ucol <= 1'b1;
                end
            end
        end
    wire [255:0] rwb = {128'd0, body[141:14]};
    always @(posedge clk)
        for (k = 0; k < 5; k = k + 1) begin
            if (rwe[k]) begin ul[k] <= rnp; ur[k] <= rrow; end
            for (i = 0; i < 128; i = i + 1) if (rwe_c[128 * k + i]) ud[k][8 * i +: 8] <= rdat[8 * i +: 8];
            for (i = 0; i < 32; i = i + 1)
                sw_d[256 * k + 8 * i +: 8] <= rwr_c[32 * k + i] ? rwb[8 * i +: 8]
                                                              : ud[k][256 * un_r[64 * k + 2 * i +: 2] + 8 * i +: 8];
            if (rwr[k]) begin
                sw_a[10 * k +: 10] <= body[9:0]; sw_m[8 * k +: 8] <= {4'd0, body[13:10]};
            end else begin
`ifdef OT_S81SL_XR_MUT_ROW
                sw_a[10 * k +: 10] <= ur[k] + {8'd0, un[k]};          // mutant: row-pair stride 1 instead of 2
`else
                sw_a[10 * k +: 10] <= ur[k] + {7'd0, un[k], 1'b0};
`endif
                sw_m[8 * k +: 8] <= 8'hff;
            end
        end

    // ---------------------------------------------------------------- command fan-out, xfin, streamer, capture
    // c_d / is_d / cfg_d are (* keep *) port registers: one flop per pin (synthesis otherwise folds the equal-D copies into
    // one flop that drives pins on two faces).  XR3 (10-18): c_d / rb_* / g_* leave as ONE copy; ot_s81sl_slice fans them
    // out to the 5 leaves in its glue (the leaf relays), so the tile no longer carries 5 equal 160 / 32 / 35-b pin copies.
    // XR1F-PIN (S81-SLICE3-XR1F 10-19, native audit of closed 12b616b54: launch 286 ps > 220 on 42 pins, all x_eps /
    // x_scale / x_mode; other outputs median 142): these were enable-hold flops (DFFE -> DFFHQN + QN -> NAND2 -> OA21 -> D),
    // so the port net's flop also fed its own hold mux through a gate whose output is NOT the D net -- io_flop_at_pins.tcl
    // (ot_of_fbonly) skipped them and they placed in the core.  Now the KEPT masters x_*_m hold the value and the pins leave
    // DEDICATED KEPT output copies x_*_q with the master's next state as D (tg ? body : master): their Q drives only the
    // pin, so they are anchored at the S face.  x_*_q == x_*_m every cycle -> same function, 0 cycles.
    (* keep *) reg [31:0] x_eps_m, x_scale_m, x_eps_q, x_scale_q; (* keep *) reg x_mode_m, x_mode_q;
    assign x_eps = x_eps_q; assign x_scale = x_scale_q; assign x_mode = x_mode_q;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin c_v <= 5'd0; x_go <= 1'b0; is_v <= 1'b0; cfg_v <= 1'b0; x_mode_m <= 1'b0; x_mode_q <= 1'b0; end
        else begin
            c_v <= tg[0] ? lmask : 5'd0;
            x_go <= tg[1];
            x_mode_m <= tg[1] ? body[32] : x_mode_m;
`ifdef OT_S81SL_XR_MUT_XHOLD
            x_mode_q <= tg[1] ? body[32] : 1'b0;                    // mutant: output copy does not hold
`else
            x_mode_q <= tg[1] ? body[32] : x_mode_m;
`endif
            is_v <= tg[2];
            cfg_v <= tg[3];
        end
    always @(posedge clk) begin
        c_d <= body;
        for (k = 0; k < 4; k = k + 1) begin
            x_eps_m[8 * k +: 8] <= tg1_c[k] ? body[8 * k +: 8] : x_eps_m[8 * k +: 8];
            x_scale_m[8 * k +: 8] <= tg1_c[4 + k] ? body[64 + 8 * k +: 8] : x_scale_m[8 * k +: 8];
`ifdef OT_S81SL_XR_MUT_XHOLD
            x_eps_q[8 * k +: 8] <= tg1_c[k] ? body[8 * k +: 8] : 8'd0;  // mutant: output copies do not hold
            x_scale_q[8 * k +: 8] <= tg1_c[4 + k] ? body[64 + 8 * k +: 8] : 8'd0;
`else
            x_eps_q[8 * k +: 8] <= tg1_c[k] ? body[8 * k +: 8] : x_eps_m[8 * k +: 8];
            x_scale_q[8 * k +: 8] <= tg1_c[4 + k] ? body[64 + 8 * k +: 8] : x_scale_m[8 * k +: 8];
`endif
        end
        is_d <= body; cfg_d <= body;
    end
    // partial collector: the 5 partials arrive on one edge; xfin takes them in leaf order 0..4 (input timing unchanged)
    reg [31:0] pq [0:4]; reg [2:0] pi; reg prun;
    // ENG collector: 5 triples of one copy -> 15 words (t = 5 kind + leaf)
    reg [95:0] eqd [0:4]; reg [1:0] ecp; reg [3:0] et; reg [2:0] el; reg [1:0] ekd; reg erun; reg ebad;
    // XR5: registered one-hot word selects for x_s (el / ekd / pi drove 480 / 160 / 160 mux loads): eoh[t] = erun &&
    // et == t (word t = kind * 5 + leaf -> eqd[t % 5][32 (t / 5) +: 32]), poh[i] = (pi == i).  Same values every cycle.
    // XR7: eoh / poh / erun as KEPT lock-step copies (h = 0 / 1 picks the low / high 16 bits of x_s; erx drives the x_s /
    // x_si select, the masters keep the run control) -- each <= ~32 pins (was 34 / 34 / 115).
    (* keep *) reg [14:0] eoh, eoh1; (* keep *) reg [4:0] poh, poh1; (* keep *) reg [3:0] erx; reg [31:0] xs_e, xs_p;
    always @(*) begin
        xs_e = 32'd0; xs_p = 32'd0;
        for (k = 0; k < 15; k = k + 1) begin
            if (eoh[k])  xs_e[15:0]  = xs_e[15:0]  | eqd[k % 5][32 * (k / 5) +: 16];
            if (eoh1[k]) xs_e[31:16] = xs_e[31:16] | eqd[k % 5][32 * (k / 5) + 16 +: 16];
        end
`ifdef OT_S81SL_XR_MUT_PORDER
        for (k = 0; k < 5; k = k + 1) begin                                  // mutant: partials in reverse order
            if (poh[k])  xs_p[15:0]  = xs_p[15:0]  | pq[4 - k][15:0];
            if (poh1[k]) xs_p[31:16] = xs_p[31:16] | pq[4 - k][31:16];
        end
`else
        for (k = 0; k < 5; k = k + 1) begin
            if (poh[k])  xs_p[15:0]  = xs_p[15:0]  | pq[k][15:0];
            if (poh1[k]) xs_p[31:16] = xs_p[31:16] | pq[k][31:16];
        end
`endif
    end
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
    // XR3-CLS census (C3): the ENG start |ev_c drove 50 pins (eoh 15 + eoh1 15 + run control) -> eoh / eoh1 start from
    // their own KEPT copies of the e_v pin flops (reset region rs_c, 19 + 10 loads); erx (x_si + x_s, 43 / 33 pins) gets
    // KEPT lock-step copies erx_x for x_si and the x_s high bytes.  C1: every one of these is the XR7 net.
    wire ev_s0, ev_s1; wire [2:0] erx_x;
    generate if (CLS != 0) begin : g_evc
        (* keep *) reg [4:0] ev_k0, ev_k1; (* keep *) reg [2:0] erx_c;
        always @(posedge clk or negedge rs_c)
            if (!rs_c) begin ev_k0 <= 5'd0; ev_k1 <= 5'd0; end else begin ev_k0 <= e_v; ev_k1 <= e_v; end
        always @(posedge clk or negedge rs_f)
            if (!rs_f) erx_c <= 3'd0;
            else if (|ev_c) erx_c <= 3'h7;
            else if (erun && et == 4'd14) erx_c <= 3'd0;
        assign ev_s0 = |ev_k0; assign ev_s1 = |ev_k1; assign erx_x = erx_c;
    end else begin : g_evn
        assign ev_s0 = |ev_c; assign ev_s1 = |ev_c; assign erx_x = {erx[1], erx[0], erx[0]};
    end endgenerate
    always @(posedge clk or negedge rs_e)                      // ENG word one-hot, two lock-step copies
        if (!rs_e) begin eoh <= 15'd0; eoh1 <= 15'd0; end
        else begin
            if (ev_s0) eoh <= 15'd1; else if (erx[2]) eoh <= {eoh[13:0], 1'b0};
            if (ev_s1) eoh1 <= 15'd1; else if (erx[3]) eoh1 <= {eoh1[13:0], 1'b0};
        end
    always @(posedge clk or negedge rs_f)                      // partial one-hot copies + erun copies (same update as erun)
        if (!rs_f) begin poh <= 5'd1; poh1 <= 5'd1; erx <= 4'd0; end
        else begin
            if (|pv) begin poh <= 5'd1; poh1 <= 5'd1; end
            else if (prun) begin poh <= {poh[3:0], 1'b0}; poh1 <= {poh1[3:0], 1'b0}; end
            if (|ev_c) erx <= 4'hf;
            else if (erun && et == 4'd14) erx <= 4'd0;
        end
    always @(posedge clk) begin
        for (k = 0; k < 20; k = k + 1) if (pvd_c[k]) pq[k / 4][8 * (k % 4) +: 8] <= pd[8 * k +: 8];
        for (k = 0; k < 60; k = k + 1) if (evd_c[k]) eqd[k / 12][8 * (k % 12) +: 8] <= ed_c[8 * k +: 8];
        if (|ev_c) ecp <= ec_c[1:0];
        x_si <= erx_x[0] ? ({6'd0, ekd} * 8'd4 + {6'd0, ecp}) * 8'd5 + {5'd0, el} : {5'd0, pi};
        x_s[7:0]   <= erx[0]   ? xs_e[7:0]   : xs_p[7:0];
        x_s[15:8]  <= erx_x[1] ? xs_e[15:8]  : xs_p[15:8];
        x_s[23:16] <= erx[1]   ? xs_e[23:16] : xs_p[23:16];
        x_s[31:24] <= erx_x[2] ? xs_e[31:24] : xs_p[31:24];
        rb_d <= rbd;
        g_c <= egc_c; g_d <= egd_c;
    end
    // ---------------------------------------------------------------- faults
    // B-wide (BIND mu4): a dir-B send config with pairs > 2 (body[42]) on C3 -- the 513-b B word carries 2 pairs only.
`ifdef OT_S81SL_XR_MUT_BWIDE
    wire f_bw = 1'b0;                                              // mutant: the over-wide B send is silently truncated
`else
    wire f_bw = (HB != 0) && tg[4] && body[3] && body[42];
`endif
    // XR6 (S81-SAFE-FIX/XR1 10-19, SAFE item 4): the 297c9bfab --cts gate failed TT setup -110.6 ps on erun -> the
    // one-cycle 20-term fault OR -> fault / its pin_reg_split launch copy (~470 ps of wire across the pin-bound 311x395
    // outline).  The terms are now registered per source region (fa input/RD, fb partial/ENG collector, fc send/inject;
    // KEPT, each beside its own sources) and the sticky flag ORs three flops: fault is visible 1 cycle later
    // (FOREG = 1: one more dedicated output flop, +2; no pin_reg_split needed).  Fault is a sticky check, never a
    // schedule input (header): 0 data cycles, 0 token-rate change.
    (* keep *) reg fa; (* keep *) reg fb; (* keep *) reg fc; reg fcore;
    always @(posedge clk or negedge rs_f)
        if (!rs_f) begin fa <= 1'b0; fb <= 1'b0; fc <= 1'b0; end
        else begin
            fa <= f1 | ucol;
            fb <= ((|pv) && pv != 5'b11111) | ((|pv) && prun) | ebad | ((|ev_c) && (erun || prun || (|pv))) |
                  ((|pv) && erun);
            fc <= (vct && (pk_go || sc_rel)) | (pk_go && sc_rel) | (s_scv && esc && wsc) | (tg[4] && (|lov1)) | f_bw |
                  so_f | (so_go && (vct || pk_go || sc_rel));     // S81-SMWIRE / BIND mu4 terms (send/inject region)
        end
    generate if (FOREG != 0) begin : g_foreg
        always @(posedge clk or negedge rs_f)
            if (!rs_f) begin fcore <= 1'b0; fault <= 1'b0; end
            else begin fcore <= fcore | fa | fb | fc; fault <= fcore; end
    end else begin : g_fdirect
        always @(posedge clk or negedge rs_f)
            if (!rs_f) fault <= 1'b0;
            else fault <= fault | fa | fb | fc;
        always @(*) fcore = 1'b0;
    end endgenerate
endmodule

// C1 (14 slices): ring E/W + V.  C3 (s_1S, s_6S): + band port B (attention q / P.V).  Hardened masters, no parameters.
module ot_s81sl_xr1 #(parameter integer FOREG = `OT_S81SL_XR_FOREG_DEF) (
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
    wire [512:0] bo_unused;
    ot_s81sl_xr #(.HB(0), .FOREG(FOREG)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi({1104{1'b0}}), .bo(bo_unused), .c_v(c_v), .c_d(c_d),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d), .rb_v(rb_v),
        .rb_d(rb_d), .e_v(e_v), .e_c(e_c), .e_d(e_d), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), .g_v(g_v), .g_c(g_c),
        .g_d(g_d), .x_go(x_go), .x_mode(x_mode), .x_eps(x_eps), .x_scale(x_scale), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd),
        .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
endmodule

module ot_s81sl_xr3 #(parameter integer FOREG = `OT_S81SL_XR_FOREG_DEF) (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire dl_ev, input wire [1103:0] dl_e, input wire dl_wv, input wire [1103:0] dl_w,
    input  wire dl_vv, input wire [275:0] dl_vb, output wire [2:0] ci_dir, output wire [1103:0] ci_b,
    input  wire [1103:0] bi, output wire [512:0] bo,
    output wire [4:0] c_v, output wire [159:0] c_d, output wire [4:0] sw_v, output wire [49:0] sw_a, output wire [39:0] sw_m,
    output wire [1279:0] sw_d, input wire [4:0] lo_v, input wire [1279:0] lo_d, input wire [4:0] p_v, input wire [159:0] p_d,
    output wire rb_v, output wire [31:0] rb_d,
    input  wire [4:0] e_v, input wire [9:0] e_c, input wire [479:0] e_d, input wire eg_v, input wire [1:0] eg_c,
    input  wire [31:0] eg_d, output wire g_v, output wire [1:0] g_c, output wire [31:0] g_d,
    output wire x_go, output wire x_mode, output wire [31:0] x_eps, output wire [31:0] x_scale, output wire x_sv,
    output wire [7:0] x_si, output wire [31:0] x_s, input wire x_rbv, input wire [31:0] x_rbd,
    output wire is_v, output wire [159:0] is_d, output wire cfg_v, output wire [159:0] cfg_d, output wire fault
);
    ot_s81sl_xr #(.HB(1), .FOREG(FOREG)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi(bi), .bo(bo), .c_v(c_v), .c_d(c_d),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d), .rb_v(rb_v),
        .rb_d(rb_d), .e_v(e_v), .e_c(e_c), .e_d(e_d), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), .g_v(g_v), .g_c(g_c),
        .g_d(g_d), .x_go(x_go), .x_mode(x_mode), .x_eps(x_eps), .x_scale(x_scale), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd),
        .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
endmodule
