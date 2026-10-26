`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KV-INTEG/AHUB 2026-10-18 (RTL-BUILD-KV M2 + P6): the STATIC attention hub as the KV die element qkd_ahub.
//
// Why not ot_qkd_ahub_die (qkd_ahub_core hd4 + 13 tiles): that composition is the LEGACY hub_t organisation. Its P.V
// half (4 ot_nhb_pbst + 4 ot_nhb_pvlg, pi_valid / pi_g / pi_beat / pi_data = 2,084 input bits) has no producer on the
// static die (P.V runs in the PV16 pairs + qkd_pv_fin_s; the static ASTK hub word is 43 b), its reciprocals leave only
// through pl_rz, one head per P.V beat and gated by p_ready (counts of pi_valid), and its issue is count-triggered with
// no epoch / layer identity.  Binding it would leave 2,084 functional inputs open (or tied) and pvfin.fr without a
// producer.  The qualified native attention service (ot_qwen_tp8_attention_native_service_w16[_g3s2]) binds the static
// six-root hub ot_qkd_ahub_static_die_cal (4 ot_nhb_zh + ot_qkh_recip_leaf, the same closed children, compiler calendar
// carried with the command, epoch / layer / slot checks), and the static programme's calendar has its fields
// (HUB_LMAX / HUB_Z / HUB_RECIP / HUB_PUB).  This element is that hub, unchanged, plus ONE small registered leaf.
//
//   qkd_ahub_static_dw (wires only)
//     u_io  : qkd_ahub_static_io   pin registers of the attention-root word hs, the hub calendar (per-stack input ages
//                                  = the root's LMAX_START / Z_START + AP_OFS[s], the die skew of stack s's ap word),
//                                  held si epoch / layer, and the reciprocal export fr to pvfin (below)
//     u_hub : ot_qkd_ahub_static_die_cal  (generated sealed master, NOT edited)
//
// Export fr (pvfin.fr, 145 b = {rz 4 x 32, rz_epoch 16, rz_valid}, LSB first): once per pass, registered, no ready.
// fr_valid is high for exactly ONE edge, at io age PV_START + R + FR_OFS (io age 0 = the cycle u_io's start register is
// high; PV_START = cal[127:112], R = cal[175:160] of the same command).  FR_OFS is plan-priced (kv_static_die
// ahub_ages): FR_OFS = D(pvfst) - PV_LEAD - D(fr) - D(hs) - 1, D = registered die relay stages of the bus, so fr lands on
// pvfin's R slot.  fr_rz / fr_epoch are captured on that edge from the hub's rz_vector / rz_epoch (final after
// rz_publish; published-before-export is checked, never waited for).
// Faults (sticky until the next start, OR-ed into hf): export slot not after rz_publish (rz late), rz_publish outside a
// pass, an unmeetable slot (target < 1 or beyond the 16-bit age), and the hub's own fault.
// AP_OFS[16 s +: 16] (two's complement): hub input age of stack s = root age + AP_OFS - 2 relative to the native
// service (= 2 there: start skew + ap pin flop).  On the die: AP_OFS_s = 2 + L_s + D(ap_s) - D(hs) - 1, L_s = the
// stack's start lag behind the attention root's start_qk (compiler).
// MUT (bench negative controls only): 1 = export one edge late, 2 = heads 0 / 1 swapped, 3 = previous pass's epoch,
// 4 = the core's calendar decodes registered one edge late (not ahead; KV-AHUBDW2 look-ahead negative control).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ahub_static_io #(
    parameter [63:0] AP_OFS = {4{16'd2}},
    parameter integer FR_OFS = 0,
    parameter integer WF_RLY = 0,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    // attention root word (kvs_attn attn_root {start_qk, ep, layer, ctx, cal[127:16], cal[175:160]})
    input  wire          hs_start,
    input  wire [15:0]   hs_ep,
    input  wire [5:0]    hs_layer,
    input  wire [13:0]   hs_ctx,
    input  wire [111:0]  hs_cal_lo,           // cal[127:16]: LMAX_START, Z_START, HUB_LMAX, HUB_Z, HUB_RECIP, HUB_PUB, PV_START
    input  wire [15:0]   hs_cal_r,            // cal[175:160]: R
    // to the hub
    output reg           start,
    output reg  [15:0]   epoch,
    output reg  [5:0]    layer,
    output reg  [13:0]   T,
    output wire [191:0]  hub_cal,             // {RZ_PUBLISH, RECIP_ISSUE, Z_START, LMAX_ISSUE, Z_IN x4, LMAX_IN x4}
    output reg  [63:0]   si_epoch,
    output reg  [23:0]   si_layer,
    // from the hub
    input  wire          rz_publish,
    input  wire [15:0]   rz_epoch,
    input  wire [127:0]  rz_vector,
    input  wire          hub_fault,
    // export to pvfin.fr and the die hub fault
    output reg           fr_valid,
    output reg  [15:0]   fr_epoch,
    output reg  [127:0]  fr_rz,
    output reg           fault
);
    // KV-AHUBDW 10-18 (pin rule: flop-first pins): every hs bit lands in a pin flop first (cal_q / cal_r_q beside start /
    // epoch / layer / T); the calendar adds (constant AP_OFS) and the export target are computed from the pin flops in the
    // same cycle start is high, so the hub still samples hub_cal on start (no added edge, behaviour unchanged).
    reg  [111:0] cal_q;  reg [15:0] cal_r_q;
    always @(posedge ck) begin cal_q <= hs_cal_lo; cal_r_q <= hs_cal_r; end
    wire [15:0] c_lmax = cal_q[15:0],  c_z = cal_q[31:16],  c_hl = cal_q[47:32], c_hz = cal_q[63:48];
    wire [15:0] c_hr = cal_q[79:64],   c_hp = cal_q[95:80], c_pv = cal_q[111:96];
    reg  [191:0] cal_n;
    integer s_;
    always @* begin
        cal_n = {c_hp, c_hr, c_hz, c_hl, 128'd0};
        for (s_ = 0; s_ < 4; s_ = s_ + 1) begin
            cal_n[16*s_ +: 16]      = c_lmax + AP_OFS[16*s_ +: 16];
            cal_n[64 + 16*s_ +: 16] = c_z + AP_OFS[16*s_ +: 16];
        end
    end
    // export target from the same command's PV_START + R (17-bit + sign: never wraps into a reachable age)
    // KV-AHUB7 10-19 (COORD 17:00): the export leaves WF_RLY registered relay edges before the W-face pins, so u_io emits
    // WF_RLY edges earlier; FR_OFS keeps its die meaning (fr still lands on pvfin's R slot, no die re-binding).
    wire signed [18:0] tgt_n = $signed({3'd0, c_pv}) + $signed({3'd0, cal_r_q}) + FR_OFS - WF_RLY + ((MUT == 1) ? 1 : 0);
    // pin stage (every input registered; start / held words ride together, so the hub samples one coherent command)
    always @(posedge ck or negedge rst_n)
        if (!rst_n) start <= 1'b0; else start <= hs_start;
    // KV-AHUBDW2 10-18: T is HELD with the command (captured with hs_start, as the core holds epoch / layer) so the core
    // can register nblk(T) and its calendar decodes one edge ahead (qkd_ahub_static_core_la).
    // T_p is the pin flop; T_h holds the start cycle's T; T = start ? T_p : T_h (flops first, then the mux).
    reg  [13:0] T_p, T_h;
    always @(posedge ck) begin
        epoch <= hs_ep; layer <= hs_layer; T_p <= hs_ctx;
        if (start) T_h <= T_p;
    end
    always @* T = start ? T_p : T_h;
    assign hub_cal = cal_n;
    reg signed [18:0] tgt_q;
    always @(posedge ck) if (start) tgt_q <= tgt_n;
    // held si identity (the native service's held_epoch / held_layer, captured on start)
    always @(posedge ck) if (start) begin si_epoch <= {4{epoch}}; si_layer <= {4{layer}}; end
    // ---- reciprocal export: one registered word at io age tgt ---------------------------------------------------------
    reg         active, published, xf;
    reg  [15:0] age;
    reg  [15:0] prev_ep;
    wire [16:0] age_nx = start ? 17'd1 : {1'b0, age} + 17'd1;     // io age of the NEXT cycle
    // KV-AHUBDW2 10-18 (route a1: u_io.cal_r_q -> PV_START + R adder -> age compare -> 145 export enables at the W face,
    // -412 ps): the export edge is decided ONE EDGE AHEAD into em_q from the latched target tgt_q (a 19-bit equality of
    // flops), so the export flops' enable is one flop.  Same export edge as before for every meetable slot; a slot < 3
    // (export on the start edge or the one after, never a compiled slot: PV_START + R is hundreds of cycles) is now an
    // unmeetable-slot fault, and a start on a pending export edge (the next command colliding with the export) faults.
    reg         em_q;
    wire        emit   = em_q;
    // KV-AHUBDW2 a2e 10-18 (gate a2d: u_io.em_q (397,531) -> W-face fr_rz / fr_epoch export flops -11.1 ps, 16 levels over
    // ~660 um): em_w is a kept copy of em_q (same D, same reset) that drives only the W-face export (fr_valid, fr_rz,
    // fr_epoch, prev_ep), so it places beside the fr flops and em_q keeps the local io bookkeeping.  Same edges.
    (* keep *) reg em_w;
    wire        bad_t  = start && (tgt_n < 19'sd3 || tgt_n > 19'sd65535);
    wire        em_d   = !start && active && !em_q && ($signed({3'b0, 16'(age + 16'd1)}) + 19'sd1 == tgt_q);
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin active <= 1'b0; published <= 1'b0; age <= 16'd0; fr_valid <= 1'b0; xf <= 1'b0; em_q <= 1'b0; em_w <= 1'b0; end
        else begin
            fr_valid <= em_w;
            em_q <= em_d;
            em_w <= em_d;
            if (start) begin active <= !bad_t; age <= 16'd1; published <= 1'b0; xf <= bad_t || em_q; end
            else begin
                if (active) age <= age_nx[15:0];
                if (active && rz_publish) published <= 1'b1;
                if (rz_publish && !active) xf <= 1'b1;                           // a publication outside any pass
                if (emit) active <= 1'b0;                                          // once per pass
            end
            if (emit && !published) xf <= 1'b1;                                   // rz late: export before publication
            if (active && age_nx[16]) xf <= 1'b1;                                  // slot beyond the age range
        end
    end
    always @(posedge ck)
        if (em_w) begin
            fr_rz    <= (MUT == 2) ? {rz_vector[127:64], rz_vector[31:0], rz_vector[63:32]} : rz_vector;
            fr_epoch <= (MUT == 3) ? prev_ep : rz_epoch;
            prev_ep  <= rz_epoch;
        end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0; else fault <= xf || hub_fault;
endmodule

// ---- the die element: wires only (u_io leaf + the sealed static hub composition) ------------------------------------
// Die ports (kv_static_die AHUB binding): hs <- kvs_attn ahs (165 b), ap<s> <- astk_<STACKS[s]>.ap (43 b: {data 32, any,
// k 4, hh 2, g, type 2, valid}, LSB first), am<s> -> astk_<STACKS[s]>.am (36 b: {data 32, hh 2, g, valid}), fr -> pvfin.fr,
// hf -> seq.hf / the attention fault tree.  ONE clock entry ck (the parent builds its own tree over its children).
module qkd_ahub_static_dw #(
    parameter [63:0] AP_OFS = {4{16'd2}},
    parameter integer FR_OFS = 0,
    parameter integer Z_IN_STRIDE = 16,
    parameter integer ZW_RLY = 0,
    parameter integer ZR_RLY = 0,
    parameter integer RX_RLY = 1,
    parameter integer RY_RLY = 2,
    parameter integer RS_RLY = 1,
    parameter integer WF_RLY = 1,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          hs_start,
    input  wire [15:0]   hs_ep,
    input  wire [5:0]    hs_layer,
    input  wire [13:0]   hs_ctx,
    input  wire [111:0]  hs_cal_lo,
    input  wire [15:0]   hs_cal_r,
    input  wire [42:0]   ap0,
    input  wire [42:0]   ap1,
    input  wire [42:0]   ap2,
    input  wire [42:0]   ap3,
    output wire [35:0]   am0,
    output wire [35:0]   am1,
    output wire [35:0]   am2,
    output wire [35:0]   am3,
    output wire          fr_valid,
    output wire [15:0]   fr_epoch,
    output wire [127:0]  fr_rz,
    output wire          hf
);
    wire start;  wire [15:0] epoch;  wire [5:0] layer;  wire [13:0] T;  wire [191:0] hub_cal;
    wire [63:0] si_epoch;  wire [23:0] si_layer;
    wire [143:0] am;  wire rz_valid, rz_publish, hub_fault;  wire [1:0] rz_head;  wire [31:0] rz_data;
    wire [15:0] rz_epoch;  wire [127:0] rz_vector;
    // KV-AHUBDW 10-18 (pin rules): (a) synced regional resets: the rst_n port drives ONLY the 2-flop synchroniser of
    // u_rr (ot_rst_pipe, the relay form of ot_rst_relay for a cluster this size); each region is its own flop chain
    // placed by its loads: 0 io leaf + ap pin flops, 1 core (its own 4-region pipe inside), 2..5 the four Z trees'
    // rst_n pins, 6 the reciprocal leaf's rst_n pin.  Release = 2 + 2 edges after the port (no consumer counts from it).
    // (b) flop-first pins: the four stack words ap_s land in pin flops ap_q (+1 edge on the hub input ages: the plan's
    // AP_OFS_s = 2 + L_s + D(ap_s) - D(ks_ahs), kv_static_die.ahub_ages); hs lands in u_io's pin flops; every output
    // (am, fr, hf) leaves a flop.  (c) the sealed ot_qkd_ahub_static_die_cal is composed here child by child (same
    // core / relays / Z trees / reciprocal leaf, same parameters, RECIP_RETURN = R_ISSUE + 67 + RX + RY) so each hard
    // child gets its own reset region; tb_qkd_ahub_static_dw checks it edge-exact against the sealed master.
    wire [6:0] rr;
    ot_rst_pipe #(.REGIONS(7), .STAGES(2)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    reg  [171:0] ap_q;
    always @(posedge ck) ap_q <= {ap3, ap2, ap1, ap0};
    wire [171:0] ap = ap_q;
    wire [3:0] si_valid, si_g, si_any;  wire [7:0] si_type, si_hh;  wire [15:0] si_k;  wire [127:0] si_data;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_si
        wire [42:0] a = ap[43*s +: 43];
        assign si_valid[s] = a[0];  assign si_type[2*s +: 2] = a[2:1];  assign si_g[s] = a[3];
        assign si_hh[2*s +: 2] = a[5:4];  assign si_k[4*s +: 4] = a[9:6];  assign si_any[s] = a[10];
        assign si_data[32*s +: 32] = a[42:11];
    end endgenerate
    // hub am copy s = {valid 35, g 34, hh 33:32, data 31:0} -> the ASTK am order {data, hh, g, valid} (LSB first)
    function automatic [35:0] am_astk(input [35:0] h);
        am_astk = {h[31:0], h[33:32], h[34], h[35]};
    endfunction
    assign am0 = am_astk(am[35:0]);    assign am1 = am_astk(am[71:36]);
    assign am2 = am_astk(am[107:72]);  assign am3 = am_astk(am[143:108]);
    // KV-AHUB7 10-19 (COORD 17:00 review of a6: every leg > 405 um gets one registered relay stage; pins / macros as a6):
    //   (1) tree selects: rc_x = OR of four per-tree relay words rt_q[a] = q_rs[a] & root_a (RS_RLY, u_core; +1 edge);
    //   (2) reciprocal y -> core rz[]: RY_RLY 2 (u_ry stage 0 anchored at the leaf pins, stage 1 on the way; +1 edge);
    //   (3) W-face export: u_io's export flops -> u_rw (WF_RLY 1) -> fr pins; u_io emits WF_RLY edges earlier, so fr lands
    //       on the same die edge (FR_OFS unchanged).
    // Recip loop: RECIP_RETURN = R_ISSUE + 67 + RS + RX + RY = R_ISSUE + 71 (a6: + 69); the compiler's HUB_PUB law moves
    // to HUB_RECIP + 75 (attn_calendar.hub: pub = recip + 67 + 2 + 2 + 4), handed to MU-DIE-KV.
    // MUT 5 (bench): tree-select relay bypassed (data one edge early against the counted RECIP_RETURN); MUT 6: W-face relay
    // bypassed (fr one edge before pvfin's R slot).  Both must FAIL.
    wire fr_valid_i;  wire [15:0] fr_epoch_i;  wire [127:0] fr_rz_i;
    ot_qkd_drly #(.W(145), .N((MUT == 6) ? 0 : WF_RLY)) u_rw (.clk(ck), .d({fr_rz_i, fr_epoch_i, fr_valid_i}),
        .q({fr_rz, fr_epoch, fr_valid}));
    qkd_ahub_static_io #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .WF_RLY(WF_RLY), .MUT(MUT)) u_io (
        .ck(ck), .rst_n(rr[0]), .hs_start(hs_start), .hs_ep(hs_ep), .hs_layer(hs_layer), .hs_ctx(hs_ctx),
        .hs_cal_lo(hs_cal_lo), .hs_cal_r(hs_cal_r), .start(start), .epoch(epoch), .layer(layer), .T(T),
        .hub_cal(hub_cal), .si_epoch(si_epoch), .si_layer(si_layer), .rz_publish(rz_publish), .rz_epoch(rz_epoch),
        .rz_vector(rz_vector), .hub_fault(hub_fault), .fr_valid(fr_valid_i), .fr_epoch(fr_epoch_i), .fr_rz(fr_rz_i),
        .fault(hf));
    // ---- the static hub (= ot_qkd_ahub_static_die_cal, cal {RZ_PUBLISH, RECIP_ISSUE, Z_START, LMAX_ISSUE, Z_IN x4,
    // LMAX_IN x4}; RECIP_RETURN is the leaf + relay geometry) ----
    wire [3:0] zh_start, zh_g;  wire [511:0] zh_we, zh_sid;  wire [15:0] zh_iv, zh_err;
    wire [23:0] zh_p;  wire [255:0] zh_root;
    // KV-AHUBDW2 10-18: the Z trees' zerr outputs are registered beside each tree (zh_err_q, +1 edge on that fault input
    // only; the child zerr -> core fault OR tree was -273 ps across the cluster)
    reg  [15:0] zh_err_q;
    always @(posedge ck) zh_err_q <= zh_err;
    wire rc_v, rc_vo, rc_fault;  wire [31:0] rc_x, rc_y;
    wire [15:0] recip_return = hub_cal[175:160] + 16'(67 + RS_RLY + RX_RLY + RY_RLY);
    // KV-AHUBDW2 10-18: the look-ahead core (decodes registered one edge ahead, edge-exact; see below)
    qkd_ahub_static_core_la #(.Z_IN_STRIDE(Z_IN_STRIDE), .Z_LEVEL_GAP(10), .RS_RLY(RS_RLY), .MUT(MUT)) u_core (
        .cal({hub_cal[191:176], recip_return, hub_cal[175:0]}),
        .clk(ck), .rst_n(rr[1]), .start(start), .active_layer_parity(layer[0]), .request_epoch(epoch),
        .active_layer(layer), .T(T),
        .si_valid(si_valid), .si_type(si_type), .si_g(si_g), .si_hh(si_hh), .si_k(si_k), .si_any(si_any),
        .si_epoch(si_epoch), .si_layer(si_layer), .si_data(si_data),
        .am(am), .zh_start(zh_start), .zh_we(zh_we), .zh_sid(zh_sid), .zh_iv(zh_iv), .zh_g(zh_g), .zh_p(zh_p),
        .zh_root(zh_root), .zh_err(zh_err_q), .rc_v(rc_v), .rc_x(rc_x), .rc_y(rc_y), .rc_vo(rc_vo), .rc_fault(rc_fault),
        .rz_valid(rz_valid), .rz_head(rz_head), .rz_data(rz_data), .rz_epoch(rz_epoch), .rz_publish(rz_publish),
        .rz4(rz_vector), .fault(hub_fault));
    genvar a;
    generate for (a = 0; a < 4; a = a + 1) begin : g_zh
        wire [267:0] zi;  wire [67:0] zo, zot;
        ot_qkd_drly #(.W(268), .N(ZW_RLY)) u_ri (.clk(ck),
            .d({zh_start[a], zh_we[128*a +: 128], zh_sid[128*a +: 128], zh_iv[4*a +: 4], zh_g[a], zh_p[6*a +: 6]}), .q(zi));
        ot_nhb_zh u_zh (.clk(ck), .rst_n(rr[2 + a]), .start(zi[267]), .zs_we(zi[266:139]), .sid(zi[138:11]),
                        .ziv(zi[10:7]), .zg(zi[6]), .zp(zi[5:0]), .root(zot[63:0]), .zerr(zot[67:64]));
        ot_qkd_drly #(.W(68), .N(ZR_RLY)) u_ro (.clk(ck), .d(zot), .q(zo));
        assign zh_root[64*a +: 64] = zo[63:0];  assign zh_err[4*a +: 4] = zo[67:64];
    end endgenerate
    wire [32:0] rx;  wire [33:0] ry, ryt;
    ot_qkd_drly #(.W(33), .N(RX_RLY)) u_rx (.clk(ck), .d({rc_v, rc_x}), .q(rx));
    ot_qkh_recip_leaf u_recip (.clk(ck), .rst_n(rr[6]), .v(rx[32]), .x(rx[31:0]), .y(ryt[31:0]), .vo(ryt[32]),
                               .fault(ryt[33]));
    ot_qkd_drly #(.W(34), .N(RY_RLY)) u_ry (.clk(ck), .d(ryt), .q(ry));
    assign rc_y = ry[31:0];  assign rc_vo = ry[32];  assign rc_fault = ry[33];
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// KV-AHUBDW2 10-18: qkd_ahub_static_core_la = qkd_ahub_static_core_cal (generated, sealed) with every calendar decode
// REGISTERED one edge ahead (route a1 EARLY_FAIL_SETUP -412 ps: u_core.age -> rz / rc_x / zh_p / zh_iv / ma_x and
// T -> hh_b / k_b / z_b were 19-24 levels of age-window adders + compares + the 4:1 head muxes + the 128-flop enables).
// The decodes are a function of (edge age, active, the calendar latched at start, nblk(T)).  For cycle c they are
// computed at c-1 from the NEXT edge age (age's D input + 1) and registered (u_dn -> dq); the one cycle whose calendar
// is not yet latched at c-1 is the first cycle after a start / reset (age == 0, edge age 1), which uses the same decode
// at the constant edge age 1 (u_d1: compares of latched registers against constants, shallow).  first_q == (age == 0).
// Edge-exact with the sealed core when T is held for the pass (u_io holds T with the command, as epoch / layer);
// nblk(T) is registered (nblk_q) from that held T.  Two documented differences, both calendar violations that now FAULT:
//   * a start while an LMAX result is leaving (mo_v): the sealed core drops that am word (am valid = mo_v && !start, a
//     u_io.start -> am pin path across the cluster); here the word leaves and the core faults at the start edge;
//   * zh_err arrives one edge later (registered at the Z tree outputs in the dw, the child -> fault path was -273 ps);
//   * fault itself is the sealed core's fault one edge later (terms registered per stack first, gate a2b -77 ps).
// No other latency changes: am / rz / rc / zh issue on the same edges as the sealed core (tb_qkd_ahub_static_dw).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ahub_static_dec #(
    parameter integer Z_IN_STRIDE=16,
    parameter integer Z_LEVEL_GAP=10
)(
    input wire [16:0] edge_age,
    input wire active,
    input wire [63:0] LMAX_IN_AGE,Z_IN_AGE,
    input wire [15:0] LMAX_ISSUE_AGE,Z_START_AGE,RECIP_ISSUE_AGE,RECIP_RETURN_AGE,RZ_PUBLISH_AGE,
    input wire [19:0] nblk_v,
    output reg [3:0] lm_slot,z_slot,done_slot,
    output reg [7:0] slot_h,
    output reg [15:0] slot_k,
    output wire m_issue,
    output wire [1:0] mh,
    output reg [3:0] issue,
    output reg [5:0] pair_base,
    output wire recip_issue,recip_return,
    output wire [1:0] recip_head,return_head,
    output wire pub_hit
);
    // KV-AHUBDW3 a3 10-18 (route a2 b698f22ab TT -55.2 / -26.5): every window is decoded from ONE subtraction
    // d = edge_age - START (17 b) compared against constants / nblk, not START + width added and compared (two carry
    // chains).  Exact: for d >= 0, edge_age < START + c <=> d < c; edge_age < Z + 16 n <=> d / 16 < n; edge_age == Z + 16 n
    // <=> d % 16 == 0 && d / 16 == n; (edge_age - Z) % 16 = d % 16; 2'(edge_age - X) = d[1:0].  The Z-tree issue levels
    // l = 1..6 start at Z_START_AGE + B_l with B_l elaboration constants (B_1 = 0, B_l+1 = B_l + burst_l + Z_LEVEL_GAP).
    wire [4:0] nblk[0:3];
    for(genvar s=0;s<4;s=s+1)assign nblk[s]=nblk_v[5*s+:5];
    wire [17:0] dl[0:3], dz[0:3];
    for(genvar s=0;s<4;s=s+1)begin:g_d
        assign dl[s]={1'b0,edge_age}-{2'b0,LMAX_IN_AGE[16*s+:16]};
        assign dz[s]={1'b0,edge_age}-{2'b0,Z_IN_AGE[16*s+:16]};
    end
    wire [17:0] dmi={1'b0,edge_age}-{2'b0,LMAX_ISSUE_AGE}, dzs={1'b0,edge_age}-{2'b0,Z_START_AGE},
                dri={1'b0,edge_age}-{2'b0,RECIP_ISSUE_AGE}, drr={1'b0,edge_age}-{2'b0,RECIP_RETURN_AGE};
    integer base,np,burst;
    always @* begin
        lm_slot=0;z_slot=0;done_slot=0;slot_h=0;slot_k=0;
        for(integer s=0;s<4;s=s+1)begin
            if(active && !dl[s][17] && dl[s][16:0]<4)begin
                lm_slot[s]=1;slot_h[2*s+:2]=dl[s][1:0];
            end
            if(active && !dz[s][17] && (dz[s][16:0]/Z_IN_STRIDE)<nblk[s])begin
                if(dz[s][16:0]%Z_IN_STRIDE<4)begin
                    z_slot[s]=1;slot_h[2*s+:2]=2'(dz[s][16:0]%Z_IN_STRIDE);
                    slot_k[4*s+:4]=4'(dz[s][16:0]/Z_IN_STRIDE);
                end
            end
            done_slot[s]=active && !dz[s][17] && dz[s][16:0]%Z_IN_STRIDE==0 && (dz[s][16:0]/Z_IN_STRIDE)==nblk[s];
        end
    end
    assign m_issue=active && !dmi[17] && dmi[16:0]<4;
    assign mh=dmi[1:0];
    always @*begin
        issue=0;pair_base=0;base=0;
        for(integer l=1;l<=6;l=l+1)begin
            np=64>>l;burst=(np+3)/4;
            if(active && !dzs[17] && dzs[16:0]>=base && dzs[16:0]<base+burst)begin
                pair_base=6'((dzs[16:0]-base)*4);
                for(integer a=0;a<4;a=a+1)issue[a]=((dzs[16:0]-base)*4+a)<np;
            end
            base=base+burst+Z_LEVEL_GAP;
        end
    end
    assign recip_issue=active && !dri[17] && dri[16:0]<4;
    assign recip_return=active && !drr[17] && drr[16:0]<4;
    assign recip_head=dri[1:0];
    assign return_head=drr[1:0];
    assign pub_hit=edge_age==RZ_PUBLISH_AGE;
endmodule

module qkd_ahub_static_core_la #(
    parameter integer Z_IN_STRIDE=16,
    parameter integer Z_LEVEL_GAP=10,
    parameter integer RS_RLY=0,                         // KV-AHUB7: per-tree relay stage on the reciprocal root select
    parameter integer MUT=0                             // 4 (bench negative control): decodes registered NOT ahead; 5: RS relay bypassed
)(
    input wire [207:0] cal,
    input wire clk,rst_n,start,active_layer_parity,
    input wire [15:0] request_epoch,input wire [5:0] active_layer,
    input wire [13:0] T,
    input wire [3:0] si_valid,si_g,si_any,input wire [63:0] si_epoch,input wire [23:0] si_layer,
    input wire [7:0] si_type,si_hh,
    input wire [15:0] si_k,
    input wire [127:0] si_data,
    (* keep *) output reg [143:0] am,   // KV-CORES 10-25: four per-stack am copies stay four pin register sets (no opt_merge; face_guard shared/ft); 0 cycles
    output reg [3:0] zh_start,
    output reg [511:0] zh_we,zh_sid,
    output reg [15:0] zh_iv,
    output reg [3:0] zh_g,
    output reg [23:0] zh_p,
    input wire [255:0] zh_root,
    input wire [15:0] zh_err,
    output reg rc_v,
    output reg [31:0] rc_x,
    input wire [31:0] rc_y,
    input wire rc_vo,rc_fault,
    output reg rz_valid,
    output reg [1:0] rz_head,
    output reg [31:0] rz_data,
    output reg [15:0] rz_epoch,output reg rz_publish,
    output wire [127:0] rz4,
    output reg fault
);
    // KV-AHUB7 10-19 (gate a6 textbook.high_fanout: rn[1] 296 loads): region 4 carries zseen[2..3] (two ~150-load copies)
    wire [4:0] rn;
    ot_rst_pipe #(.REGIONS(5),.STAGES(2)) u_rr (.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
    reg active,parity;reg [15:0] epoch;reg [5:0] layer;
    reg [63:0] LMAX_IN_AGE,Z_IN_AGE;reg [15:0] LMAX_ISSUE_AGE,Z_START_AGE,RECIP_ISSUE_AGE,RECIP_RETURN_AGE,RZ_PUBLISH_AGE;
    always @(posedge clk)if(start)
        {RZ_PUBLISH_AGE,RECIP_RETURN_AGE,RECIP_ISSUE_AGE,Z_START_AGE,LMAX_ISSUE_AGE,Z_IN_AGE,LMAX_IN_AGE}<=cal;
    wire [15:0] c_rzp,c_rra,c_ria,c_zsa,c_lis;wire [63:0] c_zin,c_lin;
    assign {c_rzp,c_rra,c_ria,c_zsa,c_lis,c_zin,c_lin}=cal;
    // nblk(T) registered from the held command T (u_io); zmask from it
    reg [19:0] nblk_q;
    always @(posedge clk)
        for(integer s=0;s<4;s=s+1)
            nblk_q[5*s+:5]<=(T>14'(128*s))?5'(((T-14'(128*s)-14'd1)>>9)+14'd1):5'd0;
    reg [63:0] zmask;
    always @*begin
        zmask=0;
        for(integer s=0;s<4;s=s+1)for(integer k=0;k<16;k=k+1)if(k<nblk_q[5*s+:5])zmask[4*k+s]=1'b1;
    end
    reg [15:0] age;
    reg first_q;                                        // == (age == 0): edge age 1 this cycle
    // KV-AHUBDW2 a2e 10-18 (gate a2d: u_core.first_q (396,517) -> W-side rz[1] -5 ps): first_r is a kept copy of first_q
    // (same D, same reset) selecting only recip_return / return_head, so it places beside the rz registers.  Same edges.
    (* keep *) reg first_r;
    // ---- decodes: registered look-ahead (dq, from the next edge age) or, on the first cycle, at edge age 1 (d1) ----
    wire [16:0] e_next=(MUT==4)?{1'b0,age}+17'd1:(active && age!=16'hffff)?{1'b0,age}+17'd2:{1'b0,age}+17'd1;
    wire [3:0] n_lm,n_z,n_dn,n_is,o_lm,o_z,o_dn,o_is;wire [7:0] n_sh,o_sh;wire [15:0] n_sk,o_sk;
    wire n_mi,n_ri,n_rr,n_pb,o_mi,o_ri,o_rr,o_pb;wire [1:0] n_mh,n_rh,n_th,o_mh,o_rh,o_th;wire [5:0] n_pa,o_pa;
    qkd_ahub_static_dec #(.Z_IN_STRIDE(Z_IN_STRIDE),.Z_LEVEL_GAP(Z_LEVEL_GAP)) u_dn (.edge_age(e_next),.active(active),
        .LMAX_IN_AGE(LMAX_IN_AGE),.Z_IN_AGE(Z_IN_AGE),.LMAX_ISSUE_AGE(LMAX_ISSUE_AGE),.Z_START_AGE(Z_START_AGE),
        .RECIP_ISSUE_AGE(RECIP_ISSUE_AGE),.RECIP_RETURN_AGE(RECIP_RETURN_AGE),.RZ_PUBLISH_AGE(RZ_PUBLISH_AGE),.nblk_v(nblk_q),
        .lm_slot(n_lm),.z_slot(n_z),.done_slot(n_dn),.slot_h(n_sh),.slot_k(n_sk),.m_issue(n_mi),.mh(n_mh),.issue(n_is),
        .pair_base(n_pa),.recip_issue(n_ri),.recip_return(n_rr),.recip_head(n_rh),.return_head(n_th),.pub_hit(n_pb));
    qkd_ahub_static_dec #(.Z_IN_STRIDE(Z_IN_STRIDE),.Z_LEVEL_GAP(Z_LEVEL_GAP)) u_d1 (.edge_age(17'd1),.active(active),
        .LMAX_IN_AGE(LMAX_IN_AGE),.Z_IN_AGE(Z_IN_AGE),.LMAX_ISSUE_AGE(LMAX_ISSUE_AGE),.Z_START_AGE(Z_START_AGE),
        .RECIP_ISSUE_AGE(RECIP_ISSUE_AGE),.RECIP_RETURN_AGE(RECIP_RETURN_AGE),.RZ_PUBLISH_AGE(RZ_PUBLISH_AGE),.nblk_v(nblk_q),
        .lm_slot(o_lm),.z_slot(o_z),.done_slot(o_dn),.slot_h(o_sh),.slot_k(o_sk),.m_issue(o_mi),.mh(o_mh),.issue(o_is),
        .pair_base(o_pa),.recip_issue(o_ri),.recip_return(o_rr),.recip_head(o_rh),.return_head(o_th),.pub_hit(o_pb));
    reg [3:0] q_lm,q_z,q_dn,q_is;reg [7:0] q_sh;reg [15:0] q_sk;reg q_mi,q_ri,q_rr,q_pb;reg [1:0] q_mh,q_rh,q_th;
    reg [5:0] q_pa;
    always @(posedge clk)begin
        q_lm<=n_lm;q_z<=n_z;q_dn<=n_dn;q_sh<=n_sh;q_sk<=n_sk;q_mi<=n_mi;q_is<=n_is;q_pa<=n_pa;
        q_ri<=n_ri;q_rr<=n_rr;q_pb<=n_pb;
        // KV-AHUBDW3 a3: the three 2-bit heads that select wide muxes (mh: 16 lm words -> ma_x; recip_head: 4 roots ->
        // rc_x; return_head: rz[] / rz_head) are registered for EVERY cycle, the first one included: on a start edge they
        // load the edge-age-1 head of the calendar being latched (2'(1 - X) of cal, exactly u_d1's head once X <= cal), so
        // no first_q mux and no calendar-register subtract sits in front of the 64-load selects (route a2: RECIP_ISSUE_AGE
        // -> u_d1 -> first_q mux -> 32 x 4:1 -> rc_x, TT -55.2 ps).  Same values on every edge as before.
        q_mh<=start?2'(2'd1-c_lis[1:0]):n_mh;
        q_rh<=start?2'(2'd1-c_ria[1:0]):n_rh;
        q_th<=start?2'(2'd1-c_rra[1:0]):n_th;
    end
    // KV-AHUB6 10-19 (route a5 74c87116c TT -357.4: u_core.q_rh[0] -> 32 rc_x, 2 AO21 + ~650 ps of buffered wire: the
    // 2-bit head reached a 4:1 mux spread between the four Z trees): the reciprocal root select is a REGISTERED ONE-HOT,
    // one flop per Z tree (q_rs[a] == (q_rh == a), same D source, same edge), and rc_x is an AND-OR of the four roots, so
    // each select flop drives only its own tree's 32 AND gates.  Edge-exact (q_rs == 4'b1 << q_rh on every edge).
    (* keep *) reg [3:0] q_rs;
    always @(posedge clk) q_rs<=4'd1<<(start?2'(2'd1-c_ria[1:0]):n_rh);
    wire [3:0] lm_slot=first_q?o_lm:q_lm, z_slot=first_q?o_z:q_z, done_slot=first_q?o_dn:q_dn, issue=first_q?o_is:q_is;
    wire [7:0] slot_h=first_q?o_sh:q_sh;
    wire [15:0] slot_k=first_q?o_sk:q_sk;
    wire m_issue=first_q?o_mi:q_mi, recip_issue=first_q?o_ri:q_ri, recip_return=first_r?o_rr:q_rr, pub_hit=first_q?o_pb:q_pb;
    wire [1:0] mh=q_mh, recip_head=q_rh, return_head=q_th;
    wire [5:0] pair_base=first_q?o_pa:q_pa;
    reg [3:0] lm_b,z_b,any_b;
    reg [7:0] hh_b;
    reg [15:0] k_b;
    reg [127:0] data_b;
    reg start_b;
    always @(posedge clk or negedge rn[0])
        if(!rn[0])begin active<=0;age<=0;first_q<=1;first_r<=1;epoch<=0;parity<=0;layer<=0;start_b<=0;lm_b<=0;z_b<=0;end
        else begin
            start_b<=start;lm_b<=lm_slot;z_b<=z_slot;
            first_q<=start || (first_q && !active);
            first_r<=start || (first_r && !active);
            if(start)begin active<=1;age<=0;epoch<=request_epoch;parity<=active_layer_parity;layer<=active_layer;lm_b<=0;z_b<=0;end
            else if(active && age!=16'hffff)age<=age+1'b1;
        end
    always @(posedge clk)begin any_b<=si_any;hh_b<=slot_h;k_b<=slot_k;data_b<=si_data;end
    reg [31:0] lm[0:15];
    reg [15:0] lany;
    reg [127:0] zseen[0:3];
    reg [15:0] lm_seen;
    reg [3:0] done_seen;
    always @(posedge clk or negedge rn[1])
        if(!rn[1])begin lany<=0;lm_seen<=0;done_seen<=0;zseen[0]<=0;zseen[1]<=0;end
        else if(start_b)begin lany<=0;lm_seen<=0;done_seen<=0;zseen[0]<=0;zseen[1]<=0;end
        else begin
            for(integer a=0;a<4;a=a+1)begin
                if(lm_b[a])begin lany[4*a+hh_b[2*a+:2]]<=any_b[a];lm_seen[4*a+hh_b[2*a+:2]]<=1;end
                if(done_slot[a])done_seen[a]<=1;
                if(z_b[a] && !hh_b[2*a+1])zseen[hh_b[2*a+:2]][{1'b0,k_b[4*a+:4],2'(a)}]<=1;
            end
        end
    always @(posedge clk or negedge rn[4])
        if(!rn[4])begin zseen[2]<=0;zseen[3]<=0;end
        else if(start_b)begin zseen[2]<=0;zseen[3]<=0;end
        else for(integer a=0;a<4;a=a+1)if(z_b[a] && hh_b[2*a+1])zseen[hh_b[2*a+:2]][{1'b0,k_b[4*a+:4],2'(a)}]<=1;
    always @(posedge clk)for(integer a=0;a<4;a=a+1)if(lm_b[a])lm[4*a+hh_b[2*a+:2]]<=data_b[32*a+:32];
    always @(posedge clk or negedge rn[0])if(!rn[0])zh_start<=0;else zh_start<={4{start_b}};
    always @(posedge clk)begin
        zh_we<=0;zh_sid<={4{data_b}};
        for(integer a=0;a<4;a=a+1)if(z_b[a])zh_we[128*hh_b[2*a+:2]+{1'b0,k_b[4*a+:4],2'(a)}]<=1;
    end
    function automatic fgt(input [31:0] a,input [31:0] b);
        fgt=(a[31]!=b[31])?!a[31]:(!a[31]?(a[30:0]>b[30:0]):(a[30:0]<b[30:0]));
    endfunction
    function automatic [32:0] fmax2(input [31:0] x,input ax,input [31:0] y,input ay);
        fmax2=!ax?{ay,y}:(!ay?{1'b1,x}:{1'b1,(fgt(y,x)?y:x)});
    endfunction
    reg ma_v,mb_v,mo_v;
    reg [1:0] ma_h,mb_h,mo_h;
    reg [127:0] ma_x;
    reg [3:0] ma_a;
    reg [63:0] mb_x;
    reg [1:0] mb_a;
    reg [31:0] mo_data;
    wire [32:0] m01=fmax2(ma_x[31:0],ma_a[0],ma_x[63:32],ma_a[1]);
    wire [32:0] m23=fmax2(ma_x[95:64],ma_a[2],ma_x[127:96],ma_a[3]);
    wire [32:0] mfin=fmax2(mb_x[31:0],mb_a[0],mb_x[63:32],mb_a[1]);
    // am valid leaves on mo_v (no u_io.start term on the am pin flops: a start on that edge is a calendar fault below)
    always @(posedge clk or negedge rn[1])
        if(!rn[1])begin ma_v<=0;mb_v<=0;mo_v<=0;for(integer a=0;a<4;a=a+1)am[36*a+35]<=0;end
        else begin ma_v<=m_issue&&!start;mb_v<=ma_v&&!start;mo_v<=mb_v&&!start;
            for(integer a=0;a<4;a=a+1)am[36*a+35]<=mo_v;end
    always @(posedge clk)begin
        ma_h<=mh;mb_h<=ma_h;mo_h<=mb_h;
        for(integer a=0;a<4;a=a+1)begin ma_x[32*a+:32]<=lm[4*a+mh];ma_a[a]<=lany[4*a+mh];end
        mb_x<={m23[31:0],m01[31:0]};mb_a<={m23[32],m01[32]};mo_data<=mfin[31:0];
        for(integer a=0;a<4;a=a+1)am[36*a+:35]<={1'b0,mo_h,mo_data};
    end
    always @(posedge clk or negedge rn[2])if(!rn[2])zh_iv<=0;else zh_iv<=start?16'd0:{4{issue}};
    always @(posedge clk)begin zh_g<=0;zh_p<={4{pair_base}};end
    reg [255:0] zroot_q;
    always @(posedge clk)zroot_q<=zh_root;
    reg [31:0] rz[0:3];
    reg [3:0] rz_seen;
    for(genvar a=0;a<4;a=a+1)assign rz4[32*a+:32]=rz[a];
    // KV-AHUB7 10-19 (COORD 17:00): the tree-select leg gets a registered relay stage: rt_q[a] = q_rs[a] & root_a, one
    // 32-flop word beside each Z tree (its select flop drives only those 32 ANDs), rc_x = OR of the four words one edge
    // later; rc_v follows one edge later too (rc_vp), and RECIP_RETURN counts RS_RLY (dw).  MUT 5 bypasses the stage.
    reg [31:0] rt_q[0:3];
    always @(posedge clk)for(integer a=0;a<4;a=a+1)rt_q[a]<={32{q_rs[a]}}&zroot_q[64*a+:32];
    wire [31:0] rc_sel=({32{q_rs[0]}}&zroot_q[31:0])|({32{q_rs[1]}}&zroot_q[95:64])|
                       ({32{q_rs[2]}}&zroot_q[159:128])|({32{q_rs[3]}}&zroot_q[223:192]);
    wire [31:0] rc_rly=rt_q[0]|rt_q[1]|rt_q[2]|rt_q[3];
    reg rc_vp;
    always @(posedge clk or negedge rn[3])
        if(!rn[3])begin rc_v<=0;rc_vp<=0;rz_valid<=0;rz_publish<=0;rz_seen<=0;rz_epoch<=0;end
        else begin
            rc_vp<=recip_issue&&!start;
            rc_v<=(RS_RLY!=0)?rc_vp:(recip_issue&&!start);rz_valid<=recip_return&&!start;
            rz_publish<=active && pub_hit && !start;
            rz_epoch<=epoch;
            if(start)rz_seen<=0;else if(recip_return)rz_seen[return_head]<=1;
        end
    always @(posedge clk)begin
        rc_x<=(RS_RLY!=0 && MUT!=5)?rc_rly:rc_sel;
        rz_head<=return_head;rz_data<=rc_y;
        if(recip_return)rz[return_head]<=rc_y;
    end
    // KV-AHUBDW2 10-18 (gate a2b: u_core.fault D -77 ps, the stack checks of the W (ap0/1) and E (ap2/3) faces into one
    // flop): the fault terms are registered first -- one flop per stack (tq, beside that stack's ap pin flops), one for the
    // global terms (gq), the start-edge value (sq) -- and fault replays the sealed core's fault update one edge later
    // (fault here == the sealed core's fault delayed by exactly one edge; hf +1 edge, fault reporting only).
    // KV-AHUBDW2 10-18 gate a2c: the single gq flop was one deep AND chain from the Z-tree zh_err_q flops (y~43) to the
    // core (y~485): -278.5 ps.  gq is now five flops, one per term group (same edge, gq == |gqv): gqv[1] (Z/recip
    // errors) sits by the trees, the others by the core; fault ORs five flop outputs (one gate level, no added edge).
    // KV-AHUB6 10-19 (route a5 TT -59.4: zh_err_q -> gqv[1], an OR of 16 bits from the four trees): the Z-tree error term
    // of gqv[1] is one flop per tree (gz[a] = |zh_err[4a+:4], beside that tree's zh_err_q); fault ORs gz with gqv / tq on
    // the same edge as before (gqv[1] | |gz == the former gqv[1]).
    reg [3:0] tq;reg [4:0] gqv;reg [3:0] gz;reg sq,start_q,act_q;
    always @(posedge clk or negedge rn[3])
        if(!rn[3])begin tq<=0;gqv<=0;gz<=0;sq<=0;start_q<=0;act_q<=0;end
        else begin
            for(integer a=0;a<4;a=a+1)gz[a]<=|zh_err[4*a+:4];
            start_q<=start;act_q<=active;
            sq<=(T==0)||(T>8192)||(active_layer_parity!=active_layer[0])||mo_v;
            gqv[0]<=active_layer_parity!=parity || active_layer!=layer || request_epoch!=epoch;
            gqv[1]<=rc_fault || (rc_vo!=recip_return);
            gqv[2]<=(m_issue && lm_seen!=16'hffff) ||
                ((|issue) && (done_seen!=4'hf || zseen[0][63:0]!=zmask || zseen[1][63:0]!=zmask ||
                    zseen[2][63:0]!=zmask || zseen[3][63:0]!=zmask));
            gqv[3]<=first_q && (LMAX_IN_AGE==0 || Z_IN_AGE==0 || LMAX_ISSUE_AGE<1 || Z_START_AGE<1 ||
                    RECIP_ISSUE_AGE<=Z_START_AGE+77 || RECIP_RETURN_AGE<=RECIP_ISSUE_AGE || RZ_PUBLISH_AGE<RECIP_RETURN_AGE+4);
            gqv[4]<=pub_hit && rz_seen!=4'hf;
            for(integer a=0;a<4;a=a+1)
                tq[a]<=(si_valid[a]!=(lm_slot[a]||z_slot[a]||done_slot[a])) ||
                    (si_valid[a] && (si_epoch[16*a+:16]!=epoch || si_layer[6*a+:6]!=layer || si_g[a] ||
                    si_type[2*a+:2]!=(lm_slot[a]?0:z_slot[a]?1:2) ||
                    ((lm_slot[a]||z_slot[a]) && si_hh[2*a+:2]!=slot_h[2*a+:2]) ||
                    (z_slot[a] && si_k[4*a+:4]!=slot_k[4*a+:4])));
        end
    always @(posedge clk or negedge rn[3])
        if(!rn[3])fault<=0;
        else if(start_q)fault<=sq;
        else if(act_q && (|gqv || |gz || |tq))fault<=1;
    initial if(Z_LEVEL_GAP<10 || Z_IN_STRIDE<4)$fatal(1,"invalid static AHUB geometry");
endmodule
