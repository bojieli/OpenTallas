`timescale 1ns/1ps
// Standalone native phase extraction, not a new stream/service controller.
// Source: rtl/chip/window_owner_safe/ot_chip_v41x_die_owner_safe.sv
// lines 684..724, SHA256 e2f5c60e214ed75c13f63b573667ea2c4782158ce7da3bcb3ab5115ad7b58643.
// The C8 selected parent contains the same phase/mux logic. Borrow its actual
// ot_chip_v41x_ckv_die_service_c8 job/stream/own_pending ports; the caller
// retains selected-ID VM reads, native QE writes, HBM commit and TP4 AG wiring.
// No service is instantiated/duplicated here. Its K=512 merger supplies the
// 128 CKV beats; this extracted counter counts ONLY 32 accepted WINDOW beats.
// No new cycles: one original combinational mux and 8 original state bits.
// Default CKV_SELECTED=0 retains the unselected source configuration. The
// full640 caller selects CKV_SELECTED=1 and clocks this native unit ONCE at
// each shared edge. Service job_done is not own-write visibility or retirement.
module ot_dsrom_s81_native_kv_phase #(
    parameter bit CKV_SELECTED = 1'b0
) (
    input  wire clk,
    input  wire rn,
    input  wire window_source_start,
    input  wire wsrc_v,
    input  wire [3:0] wsrc_m,
    input  wire [4*16*265-1:0] wsrc_w,
    output wire wsrc_ready,
    input  wire tile_packed_ready,
    input  wire svc_kv_v,
    input  wire [3:0] svc_kv_m,
    input  wire [4*16*265-1:0] svc_kv_w,
    input  wire svc_job_ready,
    input  wire svc_job_done,
    input  wire svc_own_pending,
    output wire svc_job_v,
    output wire svc_kv_ready,
    output wire c8_own_pending,
    output wire win_service_v,
    output wire [3:0] win_service_m,
    output wire [4*16*265-1:0] win_service_w,
    output reg ckv_ph,
    output reg [5:0] ckv_wbeats,
    output reg ckv_job_pend
);
    assign win_service_v = (CKV_SELECTED && ckv_ph) ? svc_kv_v : wsrc_v;
    assign win_service_m = (CKV_SELECTED && ckv_ph) ? svc_kv_m : wsrc_m;
    assign win_service_w = (CKV_SELECTED && ckv_ph) ? svc_kv_w : wsrc_w;
    assign wsrc_ready = !(CKV_SELECTED && ckv_ph) && tile_packed_ready;

    always @(posedge clk or negedge rn)
        if (!rn) begin ckv_ph <= 1'b0; ckv_wbeats <= 6'd0; ckv_job_pend <= 1'b0; end
        else if (window_source_start) begin ckv_ph <= 1'b0; ckv_wbeats <= 6'd0; ckv_job_pend <= CKV_SELECTED; end
        else begin
            if (ckv_job_pend && svc_job_ready) ckv_job_pend <= 1'b0;
            if (wsrc_v && wsrc_ready) begin
                ckv_wbeats <= ckv_wbeats + 1'b1;
                if (CKV_SELECTED && ckv_wbeats == 6'd31) ckv_ph <= 1'b1;
            end
            if (svc_job_done) ckv_ph <= 1'b0;
        end

    // Exact native service hookup (C8 parent's own_pending is borrowed, not
    // recreated from WINDOW.done, phase, job_done, or local stream acceptance).
    assign svc_job_v = ckv_job_pend;
    assign svc_kv_ready = ckv_ph && tile_packed_ready;
    assign c8_own_pending = CKV_SELECTED ? svc_own_pending : 1'b0;
endmodule
