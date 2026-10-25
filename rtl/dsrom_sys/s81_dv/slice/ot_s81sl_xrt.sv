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
// S81-RTLGAP / RG-FFN (10-21, TOK.DS.BENCH.4.2): ot_s81sl_xrt = ot_s81sl_xr (XR7 + XR1F + SMWIRE, die72 base 4ee613834)
// with (1) the FFN result transport (typed V row-pair send / receive + in-XR local copy, the codex/s81-rdpair-cut-1019
// mechanism 241f7b963 that was default-off OT_S81SL_RD_PAIR, now built in) and (2) the SAFE item 3 repair the mapped
// census of XR7 asked for (kept copies: 29 / 33 drivers > 32 loads, max 148 / 513 on C1 / C3, all of them the comb
// next-state nets that fed > 32 kept copies, plus erx / v_ctl / ce / re fan-outs and the C3 bo payload clear).
//  * every kept-copy group is now fed by its own node (next state AND a kept split leaf sp[j], 1 after reset release):
//    no node drives more than 30 copies; erx gets a dedicated x_si copy; bo's payload clear is a kept registered select
//    (bog_c, one per 30 bits, from pk_go's next state).  0 cycles; reset only on valid / control (unchanged).
//  * transport (send config body[44] = s_local, new; all other fields unchanged):
//      pair send   send config dir = V only (0100) with kind RD: every lo row pair leaves at once on V as one 276-b
//                  typed word {valid, kind RD, leaf 3, even row 10, data 256, 3'b0} (row = s_row + 2 pn), no 1,104-b pack;
//                  the slice mask must name the V partner (sid ^ 1) -- else a sticky fault.
//      V receive   a V word of kind RD (delivered by the ring stop on dl_vb) writes its row pair into leaf [6:4] at
//                  row [16:7] through the existing RD classify / unpacker (one pair, rnp 0); an odd row or nonzero
//                  [275:273] is a sticky fault.
//      local copy  s_local = 1 (dir 0, kind RD, mask = own sid) turns a packed send into a registered loop-back of the
//                  ci word into the same RD classify / unpacker (any leaf, any row), never onto the ring.
//    Same edges as the 241f7b963 cut (component receipt: CTL pin -> c_v 5, lo -> V out 5, V in -> sw 6, local CI -> sw 3).
//    Faults: two RD sources in one cycle (E / W / B / V / local), the pair / local config checks above.
// ---------------------------------------------------------------------------------------------------------------------
`ifdef OT_S81SL_XR_FOREG
`define OT_S81SL_XR_FOREG_DEF 1
`else
`define OT_S81SL_XR_FOREG_DEF 0
`endif
module ot_s81sl_xrt #(
    parameter integer HB = 0,
    parameter integer FOREG = 0,          // XR6 fallback: dedicated fault output flop (+1 more fault-visibility cycle)
    parameter integer FACE_LAND = 0,      // S81-KITS-RTLB 10-24: lo / p / e leaf interface landing stage (+1 cycle, below)
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
    // RG-FFN: kept split leaves (same 3-edge release): the second input of every copy-group node, data pins only
    localparam integer NSP = 6;
    wire [NSP-1:0] sp;
    ot_rst_relay #(.REGIONS(NSP), .SYNC_STAGES(2), .TREE_STAGES(1)) u_sp (.clk(clk), .rst_n_in(rst_n), .rst_n(sp));
    integer k, i;
    // ---------------------------------------------------------------- face landing (S81-KITS-RTLB 10-24)
    // Owner rule (register every pin, in RTL; no implemented-netlist face registers): with FACE_LAND = 1 every bit of the
    // beat-leaf interface lo_v / lo_d / p_v / p_d and of the Engram interface e_v / e_c / e_d lands in exactly ONE pin
    // register before anything else.  Before, each valid bit loaded its master input flop AND its kept copies (lov_c,
    // evd_c, pvd_c, ev2_c, ev3_c: 5..17 flops per pin, face_guard 'shared').  The kept copies now copy the landing flop,
    // so their fan-out limits are unchanged.  Pure delay (reset-free, like the data pin flops; every consumer below resets
    // or is recomputed from reset state): the module = the FACE_LAND = 0 module with these 7 inputs one edge later, i.e.
    // +1 cycle on lo -> send (ci / bo / local copy), p -> xfin partials (x_sv / x_si / x_s) and e -> ENG collection, and
    // on the faults they raise.  CTL / RD / V / SC / rstd / eg paths unchanged.  Bench: tools/s81_slice/xrt_land_eq.sh
    // (FACE_LAND = 1 vs the FACE_LAND = 0 module fed the 7 inputs one edge later, every output every cycle) and
    // xrt_bench.sh with XR_LAND = 1 (the compiler issues lo / p one cycle earlier).
    wire [4:0] lo_v_i, p_v_i, e_v_i; wire [5*256-1:0] lo_d_i; wire [5*32-1:0] p_d_i; wire [5*2-1:0] e_c_i;
    wire [5*96-1:0] e_d_i;
    generate if (FACE_LAND != 0) begin : g_land
        reg [4:0] lov_l, pv_l, ev_l; reg [5*256-1:0] lod_l; reg [5*32-1:0] pd_l; reg [5*2-1:0] ec_l; reg [5*96-1:0] ed_l;
        always @(posedge clk) begin
`ifdef OT_S81SL_XRT_MUT_LAND_PV
            pv_l <= 5'd0;                                  // mutant: p_v landing stuck (partials never collected)
`else
            pv_l <= p_v;
`endif
            lov_l <= lo_v; ev_l <= e_v; lod_l <= lo_d; pd_l <= p_d; ec_l <= e_c; ed_l <= e_d;
        end
`ifdef OT_S81SL_XRT_MUT_LAND_EVPIN
        assign e_v_i = e_v;                                // mutant: e_v not landed (pre-fix timing on the ENG path)
`else
        assign e_v_i = ev_l;
`endif
        assign lo_v_i = lov_l; assign p_v_i = pv_l; assign lo_d_i = lod_l; assign p_d_i = pd_l;
        assign e_c_i = ec_l; assign e_d_i = ed_l;
    end else begin : g_pin
        assign lo_v_i = lo_v; assign p_v_i = p_v; assign e_v_i = e_v; assign lo_d_i = lo_d; assign p_d_i = p_d;
        assign e_c_i = e_c; assign e_d_i = e_d;
    end endgenerate
    // ---------------------------------------------------------------- input flops
    reg ev, wv, vv; reg [W-1:0] eb, wb, bb; reg [V-1:0] vb; reg [4:0] lov, pv; reg [5*256-1:0] lod; reg [5*32-1:0] pd;
    reg rbv; reg [31:0] rbd; reg [3:0] sid_c;
    reg [4:0] ev_c; reg [5*2-1:0] ec_c; reg [5*96-1:0] ed_c; reg egv_c; reg [1:0] egc_c; reg [31:0] egd_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin ev_c <= 5'd0; egv_c <= 1'b0; end
        else begin ev_c <= e_v_i; egv_c <= eg_v; end
    always @(posedge clk) begin ec_c <= e_c_i; ed_c <= e_d_i; egc_c <= eg_c; egd_c <= eg_d; end
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin ev <= 1'b0; wv <= 1'b0; vv <= 1'b0; lov <= 5'd0; pv <= 5'd0; rbv <= 1'b0; end
        else begin ev <= dl_ev; wv <= dl_wv; vv <= dl_vv; lov <= lo_v_i; pv <= p_v_i; rbv <= x_rbv; end
    // XR5 (S81-SAFE-FIX 10-19, checklist item 3): kept copies of the lo_v input flop for each leaf's lo_d gate (lov[k]
    // drove 256 AND gates); same D, same edge -> function and cycles unchanged.  XR7: one per 16 bits (was 32: 37 pins),
    // reset-free (data gate only).  evd_c / pvd_c: kept copies of the e_v / p_v input flops, one per 8 bits of the eqd /
    // pq capture enables (ev_c / pv drove 197 / 66 pins); the masters keep only the control decode.
    (* keep *) reg [5*16-1:0] lov_c; (* keep *) reg [5*12-1:0] evd_c; (* keep *) reg [5*4-1:0] pvd_c;
    always @(posedge clk) begin
        for (k = 0; k < 80; k = k + 1) lov_c[k] <= lo_v_i[k / 16];
        for (k = 0; k < 60; k = k + 1) evd_c[k] <= e_v_i[k / 12];
        for (k = 0; k < 20; k = k + 1) pvd_c[k] <= p_v_i[k / 4];
    end
    always @(posedge clk) begin
        eb <= dl_e; wb <= dl_w; vb <= dl_vb; bb <= (HB != 0) ? bi : {W{1'b0}}; lod <= lo_d_i; pd <= p_d_i; rbd <= x_rbd;
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
`ifndef OT_S81SL_XR_PDC
    wire [3:0] sid_t = sid_c, sid_k = sid_c;
`endif
`ifdef OT_S81SL_XR_PDC
    // XR8 (STW-S81c-COLLA 10-22, xrt3 / xrt3_b NEEDS_RTL TT -117 / -83: eb -> decode -> rdv0 / rl0 / tgt0 -> 640 rwe_c +
    // 160 rwr_c kept copies, 578 paths): the kind / owner predicates are decoded from the input PINS into kept flags at
    // the SAME edge as eb / wb / vb (input-to-reg slack +365 ps).  sid_oh is a static strap, so mine_* from dl_* equals
    // mine_* from the registered words; the flags reset with ev / wv / vv (rs_c).  Same values, same edges.
    (* keep *) reg pq_ectl, pq_wctl, pq_vctl, pq_erd, pq_wrd, pq_vrd;
    // XRT3R (STW-S81c-COLLA3 10-22, xrt3p TT I2R dl_e -> pq_me -12.6): the owner match is captured as two byte halves
    // (8-bit AND-OR at the pin) and OR-ed after the flops: mine_* = l | h == |(dl[36:21] & sid_ohp), same edge.
    (* keep *) reg pq_me_l, pq_me_h, pq_mw_l, pq_mw_h, pq_mv_l, pq_mv_h;
    wire pq_me = pq_me_l | pq_me_h, pq_mw = pq_mw_l | pq_mw_h, pq_mv = pq_mv_l | pq_mv_h;
    wire pq_vrdc, pq_vrdm;   // same-D copies behind keep_hierarchy (plain keep regs were merged: 36-42 loads)
    ot_s81sl_xr_rcp #(.ID(1)) u_vrdc (.clk(clk), .rst_n(rs_c), .d(dl_vv && dl_vb[3:1] == K_RD), .q(pq_vrdc));
    ot_s81sl_xr_rcp #(.ID(2)) u_vrdm (.clk(clk), .rst_n(rs_c), .d(dl_vv && dl_vb[3:1] == K_RD), .q(pq_vrdm));
    // xrt3p census #4 (sid_c 33-36, pq_vrdm 33): row-select copy for the stage-2 regs and two more strap captures
    wire pq_vrdr; ot_s81sl_xr_rcp #(.ID(7)) u_vrdr (.clk(clk), .rst_n(rs_c), .d(dl_vv && dl_vb[3:1] == K_RD), .q(pq_vrdr));
    wire [3:0] sid_t, sid_k;
    ot_s81sl_xr_cp #(.W(4), .ID(5)) u_st (.clk(clk), .d(sid), .q(sid_t));   // transmit words (snd / so_b)
    ot_s81sl_xr_cp #(.W(4), .ID(6)) u_sk (.clk(clk), .d(sid), .q(sid_k));   // RG-FFN / local transport checks
    // own strap capture for the predecode (sid_c reached 44 loads when shared): sid is static from reset
    wire [3:0] sid_p, sid_p2; (* keep *) reg [15:0] sid_ohp;
    ot_s81sl_xr_cp #(.W(4), .ID(3)) u_sp1 (.clk(clk), .d(sid), .q(sid_p));
    ot_s81sl_xr_cp #(.W(4), .ID(4)) u_sp2 (.clk(clk), .d(sid), .q(sid_p2));
    always @(posedge clk) begin sid_ohp[7:0] <= 8'(16'd1 << sid_p); sid_ohp[15:8] <= 8'((16'd1 << sid_p2) >> 8); end
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin pq_ectl <= 1'b0; pq_wctl <= 1'b0; pq_vctl <= 1'b0; pq_erd <= 1'b0; pq_wrd <= 1'b0; pq_vrd <= 1'b0; end
        else begin
            pq_ectl <= dl_ev && dl_e[3:1] == K_CTL; pq_wctl <= dl_wv && dl_w[3:1] == K_CTL; pq_vctl <= dl_vv && dl_vb[3:1] == K_CTL;
            pq_erd <= dl_ev && (dl_e[3:1] == K_RD || dl_e[3:1] == K_CL); pq_wrd <= dl_wv && (dl_w[3:1] == K_RD || dl_w[3:1] == K_CL);
            pq_vrd <= dl_vv && dl_vb[3:1] == K_RD;
        end
    always @(posedge clk) begin
        pq_me_l <= |(dl_e[28:21] & sid_ohp[7:0]);  pq_me_h <= |(dl_e[36:29] & sid_ohp[15:8]);
        pq_mw_l <= |(dl_w[28:21] & sid_ohp[7:0]);  pq_mw_h <= |(dl_w[36:29] & sid_ohp[15:8]);
        pq_mv_l <= |(dl_vb[28:21] & sid_ohp[7:0]); pq_mv_h <= |(dl_vb[36:29] & sid_ohp[15:8]);
    end
    wire e_ctl = pq_ectl, w_ctl = pq_wctl, v_ctl = pq_vctl;
    wire e_rd = pq_erd, w_rd = pq_wrd;
`else
    wire e_ctl = ev && eb[3:1] == K_CTL, w_ctl = wv && wb[3:1] == K_CTL, v_ctl = vv && vb[3:1] == K_CTL;
    wire e_rd = ev && (eb[3:1] == K_RD || eb[3:1] == K_CL), w_rd = wv && (wb[3:1] == K_RD || wb[3:1] == K_CL);
`endif
    wire b_so = bv && bb[3:1] == 3'd2;                            // S81-SMWIRE: SO gather word (landing kind 2)
    wire b_rd = bv && !b_so;
    wire e_sc = ev && eb[3:1] == K_SC, w_sc = wv && wb[3:1] == K_SC;
    wire [185:0] pe = eb[21 +: 186], pw = wb[21 +: 186], pvv = vb[21 +: 186];
`ifdef OT_S81SL_XR_PDC
    wire mine_e = pq_me, mine_w = pq_mw, mine_v = pq_mv;
`else
    wire mine_e = |(pe[15:0] & sid_oh), mine_w = |(pw[15:0] & sid_oh), mine_v = |(pvv[15:0] & sid_oh);
`endif
    wire ce = e_ctl && mine_e, cw = w_ctl && mine_w, cv = v_ctl && mine_v;
    wire [185:0] cp = ce ? pe : cw ? pw : pvv;
    wire [4:0] tgt0 = cp[20:16], lmask0 = cp[25:21];
    wire re = e_rd && mine_e, rw_ = w_rd && mine_w;
    // RG-FFN transport (241f7b963): typed V row-pair word (partner only) and the in-XR registered ci loop-back (local copy)
    reg ci_v; reg [W-2:0] ci_r; reg s_local;
`ifdef OT_S81SL_XR_PDC
    wire v_rd = pq_vrd;
`else
    wire v_rd = vv && vb[3:1] == K_RD;
`endif
    wire local_rd = ci_v && s_local && ci_dir == 3'd0 && ci_r[2:0] == K_RD;
    wire rdv0 = re || rw_ || b_rd || v_rd || local_rd;
    wire [W-1:0] rdb0 = local_rd ? {ci_r, ci_v} : re ? eb : rw_ ? wb : bb;
`ifdef OT_S81SL_XR_PDC
    wire [2:0] rl0 = pq_vrdm ? vb[6:4] : rdb0[37 +: 3];
`else
    wire [2:0] rl0 = v_rd ? vb[6:4] : rdb0[37 +: 3];
`endif
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
    // RG-FFN: rsv_c = V RD word select per 8 bits of the 256-b pair (rdat), lcl_c = local-copy load of bb2 per 30 bits
    // (written in the send section, from the ci next state)
    // lcl_c granularity: 30 b on C1 (bb2 = local word or 0: 1 pin / bit), 15 b on C3 (2:1 with the B word: 2 pins / bit)
    localparam integer LCG = (HB != 0) ? 15 : 30, NLC = (1024 + LCG - 1) / LCG;
    (* keep *) reg [31:0] rsv_c; (* keep *) reg [NLC-1:0] lcl_c;
    always @(posedge clk or negedge rs_c1)
        if (!rs_c1) begin cvld <= 1'b0; vct <= 1'b0; esc <= 1'b0; wsc <= 1'b0; rdv <= 1'b0; f1 <= 1'b0; tg <= 6'd0; end
        else begin
            cvld <= ce || cw || cv; vct <= v_ctl; esc <= e_sc; wsc <= w_sc; rdv <= rdv0;
            for (k = 0; k < 6; k = k + 1) tg[k] <= (ce || cw || cv) && tgt0 == k;
            // input-only faults: two CTLs / two RDs / two lo beats in a cycle, an RD to leaf > 4, a CTL target > 5
            f1 <= ((ce + cw + cv) > 2'd1) || ((re + rw_ + b_rd + v_rd + local_rd) > 3'd1) || (nlo0 > 3'd1) ||
                  (rdv0 && rl0 > 3'd4) || ((ce || cw || cv) && tgt0 > 5'd5) || (v_rd && (vb[7] || |vb[275:273]));
        end
    always @(posedge clk or negedge rs_c2)
        if (!rs_c2) begin rwe <= 5'd0; rwr <= 5'd0; lov1 <= 5'd0; end
        else begin
            lov1 <= lov;
            for (k = 0; k < 5; k = k + 1) begin
                rwe[k] <= rdv0 && rl0 == k;
                rwr[k] <= (ce || cw || cv) && tgt0 == 5'd5 && lmask0[k];
            end
        end
    always @(posedge clk) begin
        // RG-FFN: each copy group's D is (next state AND sp[j]); copies k of one decode in sub-groups of 30 take distinct
        // leaves, so every node feeds <= 30 copies (sp is 1 after reset release: same value as the master next state)
        for (k = 0; k < 640; k = k + 1) rwe_c[k] <= rdv0 && rl0 == k / 128 && sp[((k % 128) / 30 + k / 128) % NSP];
        for (k = 0; k < 160; k = k + 1)
            rwr_c[k] <= (ce || cw || cv) && tgt0 == 5'd5 && lmask0[k / 32] && sp[((k % 32) / 30 + 2 * (k / 32)) % NSP];
        for (k = 0; k < 8; k = k + 1) tg1_c[k] <= (ce || cw || cv) && tgt0 == 5'd1;
        for (k = 0; k < 6; k = k + 1) tg4_c[k] <= (ce || cw || cv) && tgt0 == 5'd4;
        for (k = 0; k < 128; k = k + 1) begin
            rse_c[k] <= re && sp[(k / 30) % NSP]; rsw_c[k] <= !re && rw_ && sp[(k / 30 + 1) % NSP];
        end
        for (k = 0; k < 20; k = k + 1) begin bse_c[k] <= ce && sp[2]; bsw_c[k] <= !ce && cw && sp[3]; end
        for (k = 0; k < 35; k = k + 1) begin
            cvc_c[k] <= v_ctl && sp[(k / 30 + 4) % NSP]; cse_c[k] <= !v_ctl && e_sc && sp[(k / 30 + 0) % NSP];
        end
`ifdef OT_S81SL_XR_PDC
        for (k = 0; k < 32; k = k + 1) rsv_c[k] <= pq_vrdc && sp[(k / 30 + 2) % NSP];
`else
        for (k = 0; k < 32; k = k + 1) rsv_c[k] <= v_rd && sp[(k / 30 + 2) % NSP];
`endif
        eb2 <= eb[W-1:1]; wb2 <= wb[W-1:1]; vb2 <= vb[V-1:1];
        // local copy: the ci loop-back word rides the B raw word (bb2 is only the RD-from-B source; a B RD and a local
        // RD in one cycle are the two-RD fault).  C1 (HB = 0) has no B port: bb2 is the local word only.
        for (k = 0; k < 1024; k = k + 1)
            bb2[k] <= lcl_c[k / LCG] ? ci_r[51 + k] : (HB != 0) ? bb[52 + k] : 1'b0;
`ifdef OT_S81SL_XR_PDC
        lmask <= lmask0; rnp <= pq_vrdr ? 2'd0 : rdb0[50 +: 2]; rrow <= pq_vrdr ? vb[16:7] : rdb0[40 +: 10];
`else
        lmask <= lmask0; rnp <= v_rd ? 2'd0 : rdb0[50 +: 2]; rrow <= v_rd ? vb[16:7] : rdb0[40 +: 10];
`endif
        lo_sel <= lo_sel0;
    end
    // XRT3R (STW-S81c-COLLA3 10-22, xrt3p/xrt3q NEEDS_RTL TT -40.1/-32.3: bsw_c/bse_c -> body mux -> 4 repeaters ->
    // x_eps / x_scale / x_mode at the S face; one body bit fed c_d (W), is_d / cfg_d (N), sw_* and x_* (S)): the S-face
    // consumers get their OWN stage-1 raw-word copies (ebx/wbx/vbx = eb2/wb2/vb2 bits 46+{0..32, 64..95}, KEPT, same D)
    // and their own one-hot select copies (bsex_c/bswx_c = bse_c/bsw_c, same D), so the 3:1 select sits beside the
    // x flops and the long hop is the zero-logic pin-flop -> copy wire.  bodyx == body on those bits every cycle.
    (* keep *) reg [32:0] ebx_l, wbx_l, vbx_l; (* keep *) reg [31:0] ebx_h, wbx_h, vbx_h; (* keep *) reg [8:0] bsex_c, bswx_c;
    always @(posedge clk) begin
        ebx_l <= eb[47 +: 33]; wbx_l <= wb[47 +: 33]; vbx_l <= vb[47 +: 33];
        ebx_h <= eb[111 +: 32]; wbx_h <= wb[111 +: 32]; vbx_h <= vb[111 +: 32];
        for (k = 0; k < 9; k = k + 1) begin bsex_c[k] <= ce && sp[2]; bswx_c[k] <= !ce && cw && sp[3]; end
    end
    reg [32:0] bx_l; reg [31:0] bx_h;
    always @(*) begin
        for (k = 0; k < 33; k = k + 1) bx_l[k] = bsex_c[k / 8] ? ebx_l[k] : bswx_c[k / 8] ? wbx_l[k] : vbx_l[k];
        for (k = 0; k < 32; k = k + 1) bx_h[k] = bsex_c[5 + k / 8] ? ebx_h[k] : bswx_c[5 + k / 8] ? wbx_h[k] : vbx_h[k];
    end
    reg [1023:0] rdat; reg [159:0] body; reg [V-2:0] cix;
    always @(*) begin
        for (k = 0; k < 1024; k = k + 1)
            rdat[k] = (k < 256 && rsv_c[k / 8]) ? vb2[16 + k] : rse_c[k / 8] ? eb2[51 + k] : rsw_c[k / 8] ? wb2[51 + k] : bb2[k];
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
    // RG-FFN pair send: dir V only + kind RD = every lo row pair leaves on V as one typed 276-b word (no 1,104-b pack)
    wire pair_mode = s_dir == 4'b0100 && s_kind == K_RD;
    wire pair_mode_nx = tg[4] ? (body[3:0] == 4'b0100 && body[6:4] == K_RD) : pair_mode;
    wire pair_v = (|lov1) && pair_mode, pair_v_nx = (|lov) && pair_mode_nx;
    wire [9:0] pair_row = s_row + {7'd0, pn, 1'b0};
    wire [V-1:0] pair_word = {3'd0, lo_sel, pair_row, s_leaf, K_RD, 1'b1};
    localparam integer NPV = (V - 1 + 15) / 16;
    (* keep *) reg [NPV-1:0] pvs_c;
    always @(posedge clk) begin
        for (k = 0; k < 128; k = k + 1) pkw_c[k] <= (|lov) && pn_nx == k / 32 && sp[((k % 32) / 30 + k / 32) % NSP];
        for (k = 0; k < NCI; k = k + 1) cis_c[k] <= pk_go_nx && !v_ctl && !pair_mode_nx && sp[(k / 30 + 3) % NSP];
        for (k = 0; k < NPV; k = k + 1) pvs_c[k] <= pair_v_nx && !v_ctl && sp[5];
    end
    // S81-SMWIRE x XR7: sos_c[g] = so_go && !vct && !sc_rel && !pk_go (the SO beat owns ci_r), registered from next state;
    // reset-free (so_n is reset, so so_go_nx is 0 one clock into reset).
    // C1 (HB = 0) has no B port, so no SO beat: no sos_c flops there (the C1 netlist keeps its closed XR7 structure).
    wire [NCI-1:0] sos_c;
    wire so_go_nx;
    wire sc_rel_nx = (tg[4] ? body[43] : s_scv) && (e_sc || w_sc);
    generate if (HB != 0) begin : g_sos
        (* keep *) reg [NCI-1:0] sos_r;
        always @(posedge clk)
            for (k = 0; k < NCI; k = k + 1)
                sos_r[k] <= so_go_nx && !v_ctl && !sc_rel_nx && !(pk_go_nx && !pair_mode_nx) && !pair_v_nx &&
                            sp[(k / 30 + 0) % NSP];
        assign sos_c = sos_r;
    end else begin : g_nosos
        assign sos_c = {NCI{1'b0}};
    end endgenerate
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin s_dir <= 4'd0; pn <= 2'd0; pk_go <= 1'b0; s_scv <= 1'b0; s_local <= 1'b0; end
        else begin
            pk_go <= 1'b0;
            if (tg[4]) begin
                s_dir <= body[3:0]; s_scv <= body[43]; pn <= 2'd0; s_local <= body[44];
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
        snd[0] = 1'b1; snd[3:1] = s_kind; snd[8:4] = s_hops; snd[12:9] = sid_t; snd[20:13] = 8'd0;
        snd[21 +: 16] = s_mask; snd[37 +: 3] = s_leaf; snd[40 +: 10] = s_row; snd[50 +: 2] = s_np; snd[52 +: 1024] = pk;
    end
    // S81-SMWIRE: SO gather words -> one XB ring beat (assembled from the B input flops; injected on the next edge)
    reg [1:0] so_n; wire [511:0] so_lo, so_hi; reg so_go, so_f; reg [6:0] so_idx; reg [1:0] so_rt;
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin so_n <= 2'd0; so_go <= 1'b0; so_f <= 1'b0; end
        else begin
            so_go <= 1'b0;
            if (b_so) begin
                if (so_n == 2'd2) begin
                    so_n <= 2'd0;
                    if (!bb[4] || bb[52 + 32 +: 8] != 8'h5A || bb[6:5] == 2'd0 || bb[6:5] == 2'd3) so_f <= 1'b1;
                    else so_go <= 1'b1;
                end else begin
                    so_n <= so_n + 2'd1;
                    if (bb[4]) so_f <= 1'b1;
                end
            end
        end
    always @(posedge clk) if (b_so && so_n == 2'd2) begin so_idx <= bb[52 +: 7]; so_rt <= bb[6:5]; end
    // ROOT4-S81POST (10-19, SAFE item 3): the lo / hi capture enables (b_so && so_n == 0 / 1) drove 512 loads each.  Now the
    // word is staged one edge (so_w, no enable) and so_lo / so_hi capture so_w under KEPT registered enable copies, one per
    // 8 bits (64 + 64 flops, D = the decode's next state, <= ~24 pins each).  lo is captured one edge after its B word,
    // hi one edge after its B word = on the header edge, so both are valid in the so_go cycle exactly as before:
    // so_b, ci_r and every SO cycle are unchanged (0 cycles).  C1 (HB = 0) has no B port: none of these flops there.
    generate if (HB != 0) begin : g_soc
        reg [511:0] so_w, so_lo_r, so_hi_r;
        (* keep *) reg [63:0] sol_c; (* keep *) reg [63:0] soh_c;
        always @(posedge clk) begin
            so_w <= bb[52 +: 512];
`ifdef OT_S81SL_XR_MUT_SOEN
            for (k = 0; k < 64; k = k + 1) begin
                sol_c[k] <= b_so && so_n == 2'd0 && sp[(k / 30) % NSP]; soh_c[k] <= b_so && so_n == 2'd0 && sp[(k / 30 + 3) % NSP];
            end
`else
            for (k = 0; k < 64; k = k + 1) begin
                sol_c[k] <= b_so && so_n == 2'd0 && sp[(k / 30) % NSP]; soh_c[k] <= b_so && so_n == 2'd1 && sp[(k / 30 + 3) % NSP];
            end
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
    assign so_go_nx = b_so && so_n == 2'd2 && bb[4] && bb[52 + 32 +: 8] == 8'h5A && bb[6:5] != 2'd0 && bb[6:5] != 2'd3;
    wire [W-1:0] so_b = {{(W - 1045){1'b0}}, so_hi, so_lo, 1'b0, so_idx, sid_t, 5'd0, 3'd2, 1'b1};
    // V-from-G-unit CTL re-injection on the tier line (both sides, hops 0 = line default), SC relay to V
    wire sc_rel = s_scv && (esc || wsc);
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin ci_dir <= 3'd0; ci_v <= 1'b0; end
        else begin
            ci_dir <= vct ? 3'b011 : pair_v ? 3'b100 : (pk_go && !pair_mode) ? (s_local ? 3'b000 : s_dir[2:0]) :
                      sc_rel ? 3'b100 : so_go ? ((so_rt == 2'd1) ? 3'b011 : 3'b100) : 3'b000;
            ci_v <= vct || pair_v || (pk_go && !pair_mode && ((|s_dir[2:0]) || s_local)) || sc_rel || so_go;
        end
    // local copy: lcl_c = local_rd's next state (the ci word is a local RD loop-back on the next edge), per 30 bits of bb2
    wire s_local_nx = tg[4] ? body[44] : s_local;
    wire lcl_nx = !vct && !pair_v && pk_go && !pair_mode && s_local && s_kind == K_RD && s_local_nx;
    always @(posedge clk) for (k = 0; k < NLC; k = k + 1) lcl_c[k] <= lcl_nx && sp[(k / 30 + 1) % NSP];
    assign ci_b = {ci_r, ci_v};
    // S81-SMWIRE x XR7 (ROOT4 merge 10-19): the SO beat select is a KEPT registered copy per 16 bits, like cis_c; its D is
    // so_go's next state with the same priority as before the merge (send first; no SO beat beside a CTL re-injection /
    // SC relay), so ci_r is unchanged: (pk_go && !vct) ? snd : (so_go && !vct && !sc_rel) ? so_b : cix.
    wire [W-2:0] cixw = {{(W - V){1'b0}}, cix};
    always @(posedge clk) for (i = 0; i < W - 1; i = i + 1)
        ci_r[i] <= (i < V - 1 && pvs_c[i / 16]) ? pair_word[i + 1] : cis_c[i / 16] ? snd[i + 1] : sos_c[i / 16] ? so_b[i + 1] :
                   cixw[i];
    generate if (HB != 0) begin : g_bo
        reg [BW-1:0] bo_r;
        // XR7: only the valid bit bo_r[0] is reset; the payload is cleared every idle edge (0 one clock into reset).
        // BIND mu4: bo = {pk[511:0], valid} (513 b).
        always @(posedge clk or negedge rs_s) if (!rs_s) bo_r[0] <= 1'b0; else bo_r[0] <= pk_go && s_dir[3];
        // RG-FFN: the payload clear select (512 loads) is a kept registered copy per 30 bits (pk_go's next state; s_dir
        // cannot change on a pk_go edge)
        (* keep *) reg [(BW - 1 + 29) / 30 - 1:0] bog_c;
        always @(posedge clk) for (k = 0; k < (BW - 1 + 29) / 30; k = k + 1) bog_c[k] <= pk_go_nx && s_dir[3] && sp[4];
        always @(posedge clk) for (i = 1; i < BW; i = i + 1) bo_r[i] <= bog_c[(i - 1) / 30] ? pk[i - 1] : 1'b0;
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
    always @(posedge clk)                                        // RG-FFN: <= 30 copies per node (sp split)
        for (k = 0; k < 160; k = k + 1) un_c[2 * k +: 2] <= un_nx[k / 32] & {2{sp[((k % 32) / 30 + 2 * (k / 32)) % NSP]}};
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
                                                              : ud[k][256 * un_c[64 * k + 2 * i +: 2] + 8 * i +: 8];
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
            x_mode_m <= tg[1] ? bx_l[32] : x_mode_m;
`ifdef OT_S81SL_XR_MUT_XHOLD
            x_mode_q <= tg[1] ? bx_l[32] : 1'b0;                    // mutant: output copy does not hold
`else
            x_mode_q <= tg[1] ? bx_l[32] : x_mode_m;
`endif
            is_v <= tg[2];
            cfg_v <= tg[3];
        end
    always @(posedge clk) begin
        c_d <= body;
        for (k = 0; k < 4; k = k + 1) begin
            x_eps_m[8 * k +: 8] <= tg1_c[k] ? bx_l[8 * k +: 8] : x_eps_m[8 * k +: 8];
            x_scale_m[8 * k +: 8] <= tg1_c[4 + k] ? bx_h[8 * k +: 8] : x_scale_m[8 * k +: 8];
`ifdef OT_S81SL_XR_MUT_XHOLD
            x_eps_q[8 * k +: 8] <= tg1_c[k] ? bx_l[8 * k +: 8] : 8'd0;  // mutant: output copies do not hold
            x_scale_q[8 * k +: 8] <= tg1_c[4 + k] ? bx_h[8 * k +: 8] : 8'd0;
`else
            x_eps_q[8 * k +: 8] <= tg1_c[k] ? bx_l[8 * k +: 8] : x_eps_m[8 * k +: 8];
            x_scale_q[8 * k +: 8] <= tg1_c[4 + k] ? bx_h[8 * k +: 8] : x_scale_m[8 * k +: 8];
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
    (* keep *) reg [14:0] eoh, eoh1; (* keep *) reg [4:0] poh, poh1; (* keep *) reg [6:0] erx;
    // RG-FFN: |ev_c (ENG start) drove 43 pins: eoh / eoh1 restart and erx take their own kept copies of the e_v input flop
    // (D = e_v AND a split leaf: 0 in reset, e_v after release, like the reset master ev_c)
    (* keep *) reg [4:0] ev2_c, ev3_c;
    always @(posedge clk) begin ev2_c <= e_v_i & {5{sp[0]}}; ev3_c <= e_v_i & {5{sp[1]}}; end reg [31:0] xs_e, xs_p;
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
    always @(posedge clk or negedge rs_e)                      // ENG word one-hot, two lock-step copies
        if (!rs_e) begin eoh <= 15'd0; eoh1 <= 15'd0; end
        else if (|ev2_c) begin eoh <= 15'd1; eoh1 <= 15'd1; end
        else begin
            if (erx[2]) eoh <= {eoh[13:0], 1'b0};
            if (erx[3]) eoh1 <= {eoh1[13:0], 1'b0};
        end
    always @(posedge clk or negedge rs_f)                      // partial one-hot copies + erun copies (same update as erun)
        if (!rs_f) begin poh <= 5'd1; poh1 <= 5'd1; erx <= 7'd0; end
        else begin
            if (|pv) begin poh <= 5'd1; poh1 <= 5'd1; end
            else if (prun) begin poh <= {poh[3:0], 1'b0}; poh1 <= {poh1[3:0], 1'b0}; end
            if (|ev3_c) erx <= 7'h7f;                           // RG-FFN: erx[4] x_si, erx[5] / erx[6] x_s[15:8] / [31:24]
            else if (erun && et == 4'd14) erx <= 7'd0;
        end
    always @(posedge clk) begin
        for (k = 0; k < 20; k = k + 1) if (pvd_c[k]) pq[k / 4][8 * (k % 4) +: 8] <= pd[8 * k +: 8];
        for (k = 0; k < 60; k = k + 1) if (evd_c[k]) eqd[k / 12][8 * (k % 12) +: 8] <= ed_c[8 * k +: 8];
        if (|ev_c) ecp <= ec_c[1:0];
        x_si <= erx[4] ? ({6'd0, ekd} * 8'd4 + {6'd0, ecp}) * 8'd5 + {5'd0, el} : {5'd0, pi};
        x_s[7:0]   <= erx[0] ? xs_e[7:0]   : xs_p[7:0];
        x_s[15:8]  <= erx[5] ? xs_e[15:8]  : xs_p[15:8];
        x_s[23:16] <= erx[1] ? xs_e[23:16] : xs_p[23:16];
        x_s[31:24] <= erx[6] ? xs_e[31:24] : xs_p[31:24];
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
    // XRT3R census (gate 14:14: u_sk q[1] / q[3] 34 loads = two 4:16 shift-compares on sid_k): sid is a strap (static
    // from reset), so its one-hot is captured once in kept flops and the pair-partner mask is the same flops with adjacent
    // bits swapped (1 << (k ^ 1) == pair-swap of 1 << k): wiring only, same values, same edges.
    (* keep *) reg [15:0] sk_oh;
    always @(posedge clk) sk_oh <= 16'd1 << sid_k;
    wire [15:0] sk_ohx;
    genvar skx;
    generate for (skx = 0; skx < 16; skx = skx + 1) begin : g_skx assign sk_ohx[skx] = sk_oh[skx ^ 1]; end endgenerate
    always @(posedge clk or negedge rs_f)
        if (!rs_f) begin fa <= 1'b0; fb <= 1'b0; fc <= 1'b0; end
        else begin
            fa <= f1 | ucol;
            fb <= ((|pv) && pv != 5'b11111) | ((|pv) && prun) | ebad | ((|ev_c) && (erun || prun || (|pv))) |
                  ((|pv) && erun);
            fc <= (vct && (pk_go || sc_rel)) | (pk_go && sc_rel) | (s_scv && esc && wsc) | (tg[4] && (|lov1)) | f_bw |
                  so_f | (so_go && (vct || pk_go || sc_rel))      // S81-SMWIRE / BIND mu4 terms (send/inject region)
                  | (pair_v && (vct || sc_rel || so_go || s_mask != sk_ohx))   // RG-FFN transport
                  | (s_local && ((|s_dir) || s_kind != K_RD || s_mask != sk_oh));
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
module ot_s81sl_xrt1 #(parameter integer FOREG = `OT_S81SL_XR_FOREG_DEF, parameter integer FACE_LAND = 0) (
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
    ot_s81sl_xrt #(.HB(0), .FOREG(FOREG), .FACE_LAND(FACE_LAND)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi({1104{1'b0}}), .bo(bo_unused), .c_v(c_v), .c_d(c_d),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d), .rb_v(rb_v),
        .rb_d(rb_d), .e_v(e_v), .e_c(e_c), .e_d(e_d), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), .g_v(g_v), .g_c(g_c),
        .g_d(g_d), .x_go(x_go), .x_mode(x_mode), .x_eps(x_eps), .x_scale(x_scale), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd),
        .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
endmodule

module ot_s81sl_xrt3 #(parameter integer FOREG = `OT_S81SL_XR_FOREG_DEF, parameter integer FACE_LAND = 0) (
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
    ot_s81sl_xrt #(.HB(1), .FOREG(FOREG), .FACE_LAND(FACE_LAND)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi(bi), .bo(bo), .c_v(c_v), .c_d(c_d),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v), .lo_d(lo_d), .p_v(p_v), .p_d(p_d), .rb_v(rb_v),
        .rb_d(rb_d), .e_v(e_v), .e_c(e_c), .e_d(e_d), .eg_v(eg_v), .eg_c(eg_c), .eg_d(eg_d), .g_v(g_v), .g_c(g_c),
        .g_d(g_d), .x_go(x_go), .x_mode(x_mode), .x_eps(x_eps), .x_scale(x_scale), .x_sv(x_sv), .x_si(x_si), .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd),
        .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(fault));
endmodule

`ifdef OT_S81SL_XR_PDC
// XR8 copy cells: distinct-ID keep_hierarchy registers so synthesis keeps same-D copies apart
(* keep_hierarchy="yes" *)
module ot_s81sl_xr_cp #(parameter integer W=1, ID=0)(input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
 (* keep *) reg [W-1:0] r; always @(posedge clk) r<=d; assign q=r;
endmodule
(* keep_hierarchy="yes" *)
module ot_s81sl_xr_rcp #(parameter integer ID=0)(input wire clk, rst_n, d, output wire q);
 (* keep *) reg r; always @(posedge clk or negedge rst_n) if(!rst_n) r<=1'b0; else r<=d; assign q=r;
endmodule
`endif
