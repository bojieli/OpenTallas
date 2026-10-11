`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_eng_half (s81-svceng-1011, 2026-10-11): one HBM-stack HALF of the Engram table service of an S81 layer1e die.
// The Engram tables span both stacks of the home die (row parity = stack: rowstripe req_pc = (row % 2) * 32 + ...;
// boot stack = (atom / 9) % 2).  Each stack's client hosts one half: eng_SE (SE, STACK 1, inside dsfd_engram_c) and
// svc_SW (SW, STACK 0, inside dsfd_svc_c on layer1e dies), so no 64-PC bus crosses the die: the halves talk to the
// Engram core over narrow pairs.
//   boot  b_* from the core's boot dispatcher (ot_dsrom_engram_boot_dispatch, one for both stacks):
//         b_type 1 = boot write {atom 29 (stack-stripped), tag 3, d 256} -> ot_dsrom_engram_boot_ctrl_map (its stack);
//         b_type 2 = aperture CSR word (d: see dsfd_engram_c) -> this half's copy of ot_s81_engram_aperture (every half
//         holds the whole 2-stack / 64-PC aperture: the canonical maps index pc_base / pc_limit by global PC);
//         b_type 3 = BOOT READY (the dispatcher loaded every sector): the half leaves its boot phase.
//         bd_* = the boot write completions of this stack (true controller wd), to the dispatcher.
//   read  hq_* (one row request, credit) -> ot_dsrom_engram_rowstripe_service (its stack's PCs only), hr_* (push)
//         back; the service is held in reset until BOOT READY (as ot_dsrom_engram_hbm_backend).
//   PCs   rq / wd / rd of its 32 PCs (dsfd_ctrl per-PC API; rd = {rv 32, r_beat 32 x 4, r_tag 32 x 17, r_data 32 x 256}).
//         One registered rq stage (as the backend).  Boot owns the PCs before READY, the read service after.
// Faults (sticky): aperture, boot map, read service, a read request before READY, a boot word after READY.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_eng_half #(parameter integer STACK = 0) (
    input  wire              ck, rst_n,
    input  wire              b_v,
    input  wire [1:0]        b_type,
    input  wire [28:0]       b_atom,
    input  wire [2:0]        b_tag,
    input  wire [255:0]      b_d,
    output wire              bd_v,
    output wire [2:0]        bd_tag,
    input  wire              hq_v,
    input  wire [30:0]       hq_atom,
    input  wire [2:0]        hq_tag,
    output reg               hq_cred,
    output reg               hr_v,
    output reg  [2:0]        hr_tag,
    output reg  [3:0]        hr_idx,
    output reg  [255:0]      hr_d,
    output wire [32*341-1:0] rq,
    input  wire [31:0]       wd,
    input  wire [8895:0]     rd,
    output wire              ready,
    output wire              fault
);
    // ---- control words (pin-registered by the caller's tile pins: registered here once)
    reg bv_q; reg [1:0] bt_q; reg [28:0] ba_q; reg [2:0] bg_q; reg [255:0] bdq;
    always @(posedge ck or negedge rst_n) if (!rst_n) bv_q <= 1'b0; else bv_q <= b_v;
    always @(posedge ck) begin bt_q <= b_type; ba_q <= b_atom; bg_q <= b_tag; bdq <= b_d; end
    reg rdy, pfault;
    // ---- aperture copy (CSR words: bdq[254:253] kind 1 stack / 2 pc / 3 commit)
    wire csr = bv_q && bt_q == 2'd2;
    wire ap_valid, ap_corr, ap_fault; wire [1919:0] pc_base, pc_limit;
    ot_s81_engram_aperture #(.ENABLE(1)) u_ap (.ck(ck), .rst_n(rst_n),
        .stack_v(csr && bdq[254:253] == 2'd1), .stack_sel(bdq[66]), .usable(bdq[96:67]), .rsv(bdq[126:97]),
        .plain(bdq[156:127]), .yarn(bdq[186:157]), .span(bdq[216:187]),
        .pc_v(csr && bdq[254:253] == 2'd2), .pc(bdq[72:67]), .base(bdq[102:73]), .limit(bdq[132:103]),
        .commit(csr && bdq[254:253] == 2'd3), .aperture_valid(ap_valid), .pc_base(pc_base), .pc_limit(pc_limit),
        .corrected(ap_corr), .fault(ap_fault));
    // ---- boot writes of this stack
    wire [64*341-1:0] brq; wire [1:0] bdv; wire [5:0] bdt; wire bm_fault;
    wire [63:0] wd64 = (STACK == 0) ? {32'd0, wd & {32{!rdy}}} : {wd & {32{!rdy}}, 32'd0};
    ot_dsrom_engram_boot_ctrl_map #(.ROWSTRIPE(1), .CANONICAL(1), .APERTURE(1)) u_bm (.ck(ck), .rst_n(rst_n),
        .aperture_valid(ap_valid), .pc_base(pc_base), .pc_limit(pc_limit),
        .i_v((bv_q && bt_q == 2'd1) ? (2'b01 << STACK) : 2'b00), .i_atom(ba_q), .i_tag(bg_q), .i_d(bdq),
        .rq(brq), .wd(wd64), .done_v(bdv), .done_tag(bdt), .fault(bm_fault));
    assign bd_v = bdv[STACK]; assign bd_tag = bdt[3*STACK +: 3];
    // ---- read service (held in reset until BOOT READY)
    wire [64*341-1:0] rrq; wire s_hrv; wire [2:0] s_hrt; wire [3:0] s_hri; wire [255:0] s_hrd; wire s_cred, rs_fault;
    wire [2*8896-1:0] rd2 = (STACK == 0) ? {8896'd0, rd} : {rd, 8896'd0};
    wire [63:0] unused_w, unused_h, unused_c, unused_r;
    ot_dsrom_engram_rowstripe_service #(.CANONICAL(1), .APERTURE(1), .USE_LEASE(0)) u_rs (
        .pc_available(64'd0), .pc_want(unused_w), .pc_held(unused_h), .pc_claim(unused_c), .pc_release(unused_r),
        .aperture_valid(ap_valid), .pc_base(pc_base), .pc_limit(pc_limit),
        .ck(ck), .rst_n(rst_n && rdy), .hq_v(hq_v && rdy), .hq_atom(hq_atom), .hq_tag(hq_tag), .hq_cred(s_cred),
        .rq(rrq), .rd(rd2), .hr_v(s_hrv), .hr_tag(s_hrt), .hr_idx(s_hri), .hr_d(s_hrd), .fault(rs_fault));
    // ---- phase mux + one rq register stage (this stack's 32 PCs)
    reg [339:0] of_q [0:31]; reg [31:0] ov_q;
    wire [32*341-1:0] srq = rdy ? rrq[STACK*32*341 +: 32*341] : brq[STACK*32*341 +: 32*341];
    genvar p;
    generate for (p = 0; p < 32; p = p + 1) begin : g_rq
        assign rq[341*p +: 341] = {of_q[p], ov_q[p]};
        always @(posedge ck) of_q[p] <= srq[341*p + 1 +: 340];
    end endgenerate
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin ov_q <= 32'd0; rdy <= 1'b0; pfault <= 1'b0; hq_cred <= 1'b0; hr_v <= 1'b0; end
        else begin
            for (integer k = 0; k < 32; k = k + 1) ov_q[k] <= srq[341*k] && !fault;
            if (bv_q && bt_q == 2'd3) rdy <= 1'b1;
            if ((hq_v && !rdy) || (bv_q && rdy) || (bv_q && bt_q == 2'd0)) pfault <= 1'b1;
            hq_cred <= s_cred && !fault;
            hr_v <= s_hrv && !fault;
        end
    always @(posedge ck) begin hr_tag <= s_hrt; hr_idx <= s_hri; hr_d <= s_hrd; end
    assign ready = rdy && ap_valid && !fault;
    assign fault = ap_fault | bm_fault | (rs_fault && rdy) | pfault;
endmodule
