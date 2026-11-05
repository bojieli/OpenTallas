`default_nettype none
// HBM-BIND-5 candidate (COORD 11-05 option (a)): two FUSED lanes share the one free read/write group (rq0, wq0, rr0) of an S bank.
// Static schedule: the calendar gives each lane its own bank slots, no arbitration, no credits. A request of lane a or b reaches the
// bank pin with no added edge. The bank returns rr BANK_RR edges after the pin edge (ot_vms_bank_q0_faces_body: registered response
// n+6), so a BANK_RR-edge tag steers rr to the lane that asked; the other lane's rr_v stays 0.
// Spare bit: ot_hnx_fused_vm_native_adapter carries a mirror flag, constant 0, in native_rq[16] and native_wq[280]. FUSED addresses regular
// words only and q0 faces have no mirror input, so this module is the owner and does not generate that bit: rq {v, sector}, wq {v, sector, data, be}.
// coll flags both lanes valid on one edge: a calendar error, lane a wins; open output for benches and die STA debug only.
module ot_hnx_fused_vm_pair #(parameter integer BANK_RR = 6) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         a_rq_v,
    input  wire [15:0]  a_rq_s,
    input  wire         a_wq_v,
    input  wire [15:0]  a_wq_s,
    input  wire [255:0] a_wq_d,
    output wire         a_rr_v,
    output wire [255:0] a_rr_d,
    input  wire         b_rq_v,
    input  wire [15:0]  b_rq_s,
    input  wire         b_wq_v,
    input  wire [15:0]  b_wq_s,
    input  wire [255:0] b_wq_d,
    output wire         b_rr_v,
    output wire [255:0] b_rr_d,
    output wire [16:0]  rq0,
    output wire [280:0] wq0,
    input  wire [256:0] rr0,
    output wire         coll
);
    reg [BANK_RR-1:0] tag_b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) tag_b <= '0;
        else tag_b <= {tag_b[BANK_RR-2:0], b_rq_v};
    assign rq0 = {a_rq_v | b_rq_v, a_rq_v ? a_rq_s : b_rq_s};
    assign wq0 = {a_wq_v | b_wq_v, a_wq_v ? a_wq_s : b_wq_s, a_wq_v ? a_wq_d : b_wq_d, 8'hff};
    assign a_rr_v = rr0[256] & ~tag_b[BANK_RR-1];
    assign b_rr_v = rr0[256] &  tag_b[BANK_RR-1];
    assign a_rr_d = rr0[255:0];
    assign b_rr_d = rr0[255:0];
    assign coll = (a_rq_v & b_rq_v) | (a_wq_v & b_wq_v);
endmodule
`default_nettype wire
