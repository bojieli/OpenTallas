`timescale 1ns/1ps
// DIE-HEAD-76-SERDESRF 2026-11-06: the two hard sub-core types of the hd_serdes SC form (parent: ot_s81hd_serdes_sc.sv).
// Own file so each child kit reads only its own closure (ot_s81_kp4_common/bm or enc_la + pma model).
module ot_s81hd_sc_tx #(
`ifdef OT_HEAD_TX_CH_STAGE
    parameter integer CH_STAGE = 1
`else
    parameter integer CH_STAGE = 0
`endif
    ,
    // DIE-HEAD-85/TXF 11-07: opt-in FOLD (A w_k folded into the FF slices, no l2_w cone); stream cycle-identical.
`ifdef OT_HEAD_TX_FOLD
    parameter integer FOLD = 1
`else
    parameter integer FOLD = 0
`endif
    ,
`ifdef OT_HEAD_TX_CH_REGION4
    parameter integer CH_REGION4 = 1
`else
    parameter integer CH_REGION4 = 0
`endif
    ,
`ifdef OT_HEAD_TX_CH_RELAY1
    parameter integer CH_RELAY1 = 1
`else
    parameter integer CH_RELAY1 = 0
`endif
) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [543:0]  pma_tx,
    output wire          e_flt
);
    reg [1:0] rs_t;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    wire rn_t = rs_t[1];
    wire e_v; wire [543:0] e_d;
    ot_s81_kp4_enc_la #(.MUT(0), .LA(2), .FF(1), .CH_STAGE(CH_STAGE), .FOLD(FOLD), .CH_REGION4(CH_REGION4), .CH_RELAY1(CH_RELAY1)) u_enc (.clk(clk), .rst_n(rn_t), .tx_v(rn_t), .tx_d(tx), .p_v(e_v), .p_d(e_d),
        .fault(e_flt));
    ot_s81_pma_bm #(.W(544), .LAT(4)) u_ptx (.clk(clk), .d_v(e_v), .d(e_d), .q(pma_tx));
endmodule

module ot_s81hd_sc_bmq (
    input  wire          clk,
    input  wire          rs_n,         // regional synchronous reset leaf (registered in the parent)
    input  wire [3:0]    ld_i,         // RiBM load request (parent ldr, T + 12)
    input  wire [299:0]  S_i,          // final syndromes (parent S_q)
    output wire [159:0]  lam,
    output wire [149:0]  om,
    output wire [4:0]    L,
    output wire          any,
    output wire [3:0]    done
);
    (* keep *) reg [3:0]   ldq;        // RXQ load one edge later (T + 13), with S_b
    (* keep *) reg [299:0] S_b;        // RXQ S copy, placed with the unit
    always @(posedge clk) if (!rs_n) ldq <= 4'd0; else ldq <= ld_i;
    always @(posedge clk) S_b <= S_i;
    ot_s81_kp4_bm #(.NG(4), .NCD(4), .THC(1)) u_bm (.clk(clk), .rs_n(rs_n), .ld(ldq), .S(S_b), .lam(lam), .om(om), .L(L),
        .any(any), .done(done));
endmodule

