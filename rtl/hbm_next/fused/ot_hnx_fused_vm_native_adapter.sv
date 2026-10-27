`default_nettype none
// Zero-cycle bridge from one FUSED lane to one independent native VM bank port.
// FUSED addresses regular VM words only. Its 16-bit sector addresses all 2^19
// regular words (8 words/sector); native sector[16] is the mirror flag and is 0.
// Native write payload is {256 data bits, 8 word-enable bits}; FUSED writes all
// eight words. Slot ownership and the bank's real return latency remain the
// static programme's responsibility. This bridge does not arbitrate bank ports.
module ot_hnx_fused_vm_native_adapter (
    input  wire         fused_rq_v,
    input  wire [15:0]  fused_rq_sector,
    output wire [17:0]  native_rq,
    input  wire         fused_wq_v,
    input  wire [15:0]  fused_wq_sector,
    input  wire [255:0] fused_wq_data,
    output wire [281:0] native_wq,
    input  wire [256:0] native_rr,
    output wire         fused_rr_v,
    output wire [255:0] fused_rr_data
);
    assign native_rq = {fused_rq_v, 1'b0, fused_rq_sector};
    assign native_wq = {fused_wq_v, 1'b0, fused_wq_sector, fused_wq_data, 8'hff};
    assign fused_rr_v = native_rr[256];
    assign fused_rr_data = native_rr[255:0];
endmodule
`default_nettype wire
