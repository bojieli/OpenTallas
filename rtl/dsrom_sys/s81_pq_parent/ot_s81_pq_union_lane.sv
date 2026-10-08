`timescale 1ns/1ps
// Optional W2 transport codec. Disabled preserves the entire native1633-bit
// bus byte-for-byte. Enabled sends one family over1085 bits; only the inactive
// family's payload may change. Consumer valid qualification remains mandatory.
// No registers or changed arithmetic. Register/CDC stations are separate.
module ot_s81_pq_union_lane #(
    parameter integer ENABLE = 0
) (
    input wire [1632:0] native_in,
    output wire [1084:0] lane_tx,
    input wire [1084:0] lane_rx,
    output wire [1632:0] native_out,
    output wire protocol_fault
);
    wire cfg,go,gobf,qv,bv;
    wire [8:0] ph;
    wire [2:0] np,qb,bfb,qp,bfp;
    wire [1:0] tag,sv;
    wire [7:0] p;
    wire [255:0] q0,q1;
    wire [9:0] e0,e1;
    wire [3:0] bsv;
    wire [31:0] u;
    wire [1023:0] d;
    assign {cfg,ph,np,go,gobf,tag,qv,p,qb,sv,q0,e0,q1,e1,qp,bfp,bv,bfb,bsv,u,d}=native_in;
    wire tx_bad = (qv && bv) || ((qv || bv) && ((qb != bfb) || (qp != bfp)));
    wire [24:0] fixed_fields={bv,qv,qp,qb,tag,gobf,go,np,ph,cfg};
    wire [1059:0] payload=bv ? {d,u,bsv} : {518'd0,e1,q1,e0,q0,sv,p};
    assign lane_tx=(ENABLE && !tx_bad) ? {payload,fixed_fields} : 1085'd0;

    wire r_cfg,r_go,r_gobf,r_qv,r_bv;
    wire [8:0] r_ph;
    wire [2:0] r_np,r_b,r_pos;
    wire [1:0] r_tag;
    assign {r_bv,r_qv,r_pos,r_b,r_tag,r_gobf,r_go,r_np,r_ph,r_cfg}=lane_rx[24:0];
    wire [7:0] r_p=lane_rx[32:25];
    wire [1:0] r_sv=lane_rx[34:33];
    wire [255:0] r_q0=lane_rx[290:35];
    wire [9:0] r_e0=lane_rx[300:291];
    wire [255:0] r_q1=lane_rx[556:301];
    wire [9:0] r_e1=lane_rx[566:557];
    wire [3:0] r_bsv=lane_rx[28:25];
    wire [31:0] r_u=lane_rx[60:29];
    wire [1023:0] r_d=lane_rx[1084:61];
    wire rx_bad=r_qv && r_bv;
    wire [1632:0] decoded={r_cfg,r_ph,r_np,r_go,r_gobf,r_tag,r_qv,r_p,r_b,r_sv,
        r_q0,r_e0,r_q1,r_e1,r_pos,r_pos,r_bv,r_b,r_bsv,r_u,r_d};
    assign native_out=ENABLE ? (rx_bad ? 1633'd0 : decoded) : native_in;
    assign protocol_fault=ENABLE && (tx_bad || rx_bad);
endmodule
