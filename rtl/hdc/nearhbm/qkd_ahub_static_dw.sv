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
// MUT (bench negative controls only): 1 = export one edge late, 2 = heads 0 / 1 swapped, 3 = previous pass's epoch.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ahub_static_io #(
    parameter [63:0] AP_OFS = {4{16'd2}},
    parameter integer FR_OFS = 0,
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
    output reg  [191:0]  hub_cal,             // {RZ_PUBLISH, RECIP_ISSUE, Z_START, LMAX_ISSUE, Z_IN x4, LMAX_IN x4}
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
    wire [15:0] c_lmax = hs_cal_lo[15:0],  c_z = hs_cal_lo[31:16],  c_hl = hs_cal_lo[47:32], c_hz = hs_cal_lo[63:48];
    wire [15:0] c_hr = hs_cal_lo[79:64],   c_hp = hs_cal_lo[95:80], c_pv = hs_cal_lo[111:96];
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
    wire signed [18:0] tgt_n = $signed({3'd0, c_pv}) + $signed({3'd0, hs_cal_r}) + FR_OFS + ((MUT == 1) ? 1 : 0);
    // pin stage (every input registered; start / held words ride together, so the hub samples one coherent command)
    always @(posedge ck or negedge rst_n)
        if (!rst_n) start <= 1'b0; else start <= hs_start;
    always @(posedge ck) begin
        epoch <= hs_ep; layer <= hs_layer; T <= hs_ctx; hub_cal <= cal_n;
    end
    reg signed [18:0] tgt_q;
    always @(posedge ck) if (hs_start) tgt_q <= tgt_n;
    // held si identity (the native service's held_epoch / held_layer, captured on start)
    always @(posedge ck) if (start) begin si_epoch <= {4{epoch}}; si_layer <= {4{layer}}; end
    // ---- reciprocal export: one registered word at io age tgt ---------------------------------------------------------
    reg         active, published, xf;
    reg  [15:0] age;
    reg  [15:0] prev_ep;
    wire [16:0] age_nx = start ? 17'd1 : {1'b0, age} + 17'd1;     // io age of the NEXT cycle
    wire        live   = start || active;
    wire        emit   = live && $signed({2'b0, age_nx}) == tgt_q;
    wire        bad_t  = start && (tgt_q < 19'sd1 || tgt_q > 19'sd65535);
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin active <= 1'b0; published <= 1'b0; age <= 16'd0; fr_valid <= 1'b0; xf <= 1'b0; end
        else begin
            fr_valid <= emit;
            if (start) begin active <= !bad_t; age <= 16'd1; published <= 1'b0; xf <= bad_t; end
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
        if (emit) begin
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
    parameter integer RY_RLY = 1,
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
    wire [171:0] ap = {ap3, ap2, ap1, ap0};
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
    qkd_ahub_static_io #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .MUT(MUT)) u_io (
        .ck(ck), .rst_n(rst_n), .hs_start(hs_start), .hs_ep(hs_ep), .hs_layer(hs_layer), .hs_ctx(hs_ctx),
        .hs_cal_lo(hs_cal_lo), .hs_cal_r(hs_cal_r), .start(start), .epoch(epoch), .layer(layer), .T(T),
        .hub_cal(hub_cal), .si_epoch(si_epoch), .si_layer(si_layer), .rz_publish(rz_publish), .rz_epoch(rz_epoch),
        .rz_vector(rz_vector), .hub_fault(hub_fault), .fr_valid(fr_valid), .fr_epoch(fr_epoch), .fr_rz(fr_rz),
        .fault(hf));
    // cal: {RZ_PUBLISH, RECIP_ISSUE, Z_START, LMAX_ISSUE, Z_IN x4, LMAX_IN x4}; RECIP_RETURN is the leaf+relay geometry
    ot_qkd_ahub_static_die_cal #(.Z_IN_STRIDE(Z_IN_STRIDE), .Z_LEVEL_GAP(10), .ZW_RLY(ZW_RLY), .ZR_RLY(ZR_RLY),
                                 .RX_RLY(RX_RLY), .RY_RLY(RY_RLY)) u_hub (
        .cal(hub_cal), .ck_core(ck), .ck_recip(ck), .ck_zh({4{ck}}), .rst_n(rst_n), .start(start),
        .active_layer_parity(layer[0]), .request_epoch(epoch), .active_layer(layer), .T(T),
        .si_valid(si_valid), .si_g(si_g), .si_any(si_any), .si_epoch(si_epoch), .si_layer(si_layer), .si_type(si_type),
        .si_hh(si_hh), .si_k(si_k), .si_data(si_data), .am(am), .rz_valid(rz_valid), .rz_head(rz_head),
        .rz_data(rz_data), .rz_epoch(rz_epoch), .rz_publish(rz_publish), .rz_vector(rz_vector), .fault(hub_fault));
endmodule
