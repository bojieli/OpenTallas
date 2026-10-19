`timescale 1ns/1ps
// RTL-BUILD-KV/FAULT 2026-10-18 (lanes/RTL-BUILD-KV.md P7): the root of the attention service-unit fault tree, beside the
// result face in the attention control tile (kvs_attn).  It drives qkd_attn_result_face_s.unit_fault[NF-1:0]
// (NF = ND + NC/2 = 10), which the face folds as |unit_fault into service_fault (sticky per its sources, never a stall).
//
// Static die sources (kv_static_die.py, OT_KV_STATIC_DIE=1) -- every one a registered fault flop of a real unit:
//   d[0..3]  astk_<WS|WN|ES|EN>.af   ASTK stack faults (fork of the existing af_<st> bus to the sequencer)
//   d[4]     ahub.hf                  attention hub fault (fork of the hf bus to the sequencer)
//   d[5..6]  pvw_<0|1>.pf            PV pair faults (qkd_pvw_die_t fault)
//   d[7]     pvfin.ff                 PV final join fault (slot / beat / epoch / rz-late window, adder / multiplier flags)
//   c[0..3]  chain end of stack <WS|WN|ES|EN>: the registered neighbour chain through the stack's 8 landing groups
//            (qkd_kv_cfault_node af in each qkd_kvs_grp / _h: {up, vport f, ECTL kiss kf}, slot 0 -> 7), i.e. the
//            32 ECTL K-issuer identity faults + the 16 V-port faults
// Output lanes (LSB first): unit_fault = {|c[3:2] (E stacks K/V), |c[1:0] (W stacks K/V), d[7:0]}.
// Every input is registered once here (the pin stage); the two chain pairs are OR-ed into that register.  Latency to
// the face = 1 edge + the die relay stages of the lane's bus (+ the group chain for c); no ready, no credit, no event:
// a pure level OR pipeline, so a sticky source stays visible and a fixed-slot source is seen a fixed number of edges
// later (kv_static_die.record attn_fault: per-lane latency for the compiler).
// MUT (bench negative controls): 1 = c[0] dropped from the W pair; 2 = d bypasses the pin register (one edge early);
// 3 = d[5] and d[6] swapped (lane map).
module qkd_attn_fault_root #(parameter integer ND = 8, parameter integer NC = 4, parameter integer MUT = 0) (
    input  wire                  ck,
    input  wire                  rst_n,
    input  wire [ND-1:0]         d,
    input  wire [NC-1:0]         c,
    output wire [ND+NC/2-1:0]    unit_fault
);
    generate if (NC % 2 != 0 || ND < 7) begin : g_bad
        initial $fatal(1, "qkd_attn_fault_root: ND %0d NC %0d", ND, NC);
    end endgenerate
    wire [ND-1:0] dm = (MUT == 3) ? {d[ND-1:7], d[5], d[6], d[4:0]} : d;
    wire [NC-1:0] cm = (MUT == 1) ? {c[NC-1:1], 1'b0} : c;
    reg  [ND-1:0]   dq;
    reg  [NC/2-1:0] cq;
    integer j;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin dq <= 0; cq <= 0; end
        else begin
            dq <= dm;
            for (j = 0; j < NC / 2; j = j + 1) cq[j] <= cm[2*j] | cm[2*j+1];
        end
    assign unit_fault = {cq, (MUT == 2) ? dm : dq};
endmodule
