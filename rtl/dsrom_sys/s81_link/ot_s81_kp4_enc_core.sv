`timescale 1ns/1ps
// FAM-S81-SERDES-R4 11-21: hard-core wrapper of the KP4 encoder for the serdes__t4 split (OT_S81_SERDES_DEC_CORE form).
// Wiring only, no logic, 0 cycles: ot_s81_kp4_enc with H0_SEQ_ONLY=1, the form RCK RE-FORM already signs (ot_s81_rck_reform).
// Why: the default H0_SEQ_ONLY=0 keeps 12 never-reset header flops h0_r[19:8] whose D is the constant 12'hA5C.  Synthesis
// folds them, and LEC takes their pre-load value as free, so ch_q[448..471] differ (24 points; enc_j6a routed LEC 11-21,
// as TX vC/vD on 11-08).  h0 is only read when sk[*][0] marks a beat-0 chunk, which is after a load, so the outputs are
// identical.  With the constant part a wire, the routed core is provable.
module ot_s81_kp4_enc_core #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          tx_v,
    input  wire [511:0]  tx_d,
    output wire          p_v,
    output wire [543:0]  p_d,
    output wire          fault
);
    ot_s81_kp4_enc #(.MUT(MUT), .H0_SEQ_ONLY(1)) u_enc (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d),
        .p_v(p_v), .p_d(p_d), .fault(fault));
endmodule
