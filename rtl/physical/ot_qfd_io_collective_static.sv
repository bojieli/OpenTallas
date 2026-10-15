`timescale 1ns/1ps
// qwen-coll-io r4 2026-10-14 (OWNER 0ah static cycle schedule): qfd_io_collective_static -- the Qwen TP8 compute-die
// collective master under its die name, = ot_coll_tp8_static in the production shape, no parameters: one master for
// all 8 compute dies (rank from the pkg_s / die_ps straps), each of the 8 hardened ot_coll_fold_slice children on its
// own clock entry.  NO credit / ready ports: a compiler command per message (cmd_*), producer words at their compiled
// slots, links as valid + record at fixed latencies.  LU / LS are the die's priced link latencies (compute-die lead):
// LU = UCIe up-register -> peer dp pin incl. both static CDC channels, LS = SerDes sx-register -> peer sr pin.
// r5 (composed on the real static link RTL, tools/qwen_coll_tp8_static_links_bench.py): L_min = KC 4 + KW 2 + 17 + PHY
// + 2 R (R = on-die relay stages between this master and the link face, both directions): LU = 37 (UCIe PHY 14, R 0,
// adjacent), LS = 362 + 2 R_max (board PHY 339; default R_max 7 = the compute lead's SerDes bound -> 376); faces nearer
// than R_max pad their RX read slot in the IO calendar so every port lands at the one compiled LS.
// Successor of qfd_io_collective (credit design, historical/diagnostic under 0ah).
module qfd_io_collective_static (
    input  wire          clk,                   // parent root
    input  wire          clk_pfold0, clk_pfold1, clk_pfold2, clk_pfold3,
    input  wire          clk_xfold0, clk_xfold1, clk_xfold2, clk_xfold3,
    input wire clk_pring0,clk_pring1,clk_sring0,clk_sring1,clk_sring2,clk_sring3,clk_sring4,clk_rring0,clk_rring1,
    input  wire          rst_n,
    input  wire [1:0]    pkg_s,
    input  wire          die_ps,
    input  wire          cmd_v,
    input  wire          cmd_mode,
    input  wire [15:0]   cmd_words,
    input  wire [31:0]   cmd_tag,
    input  wire          in_valid,
    input  wire [511:0]  in_data,
    input  wire          in_last,
    input  wire          in_mode,
    input  wire [31:0]   in_tag,
    output wire          up_valid,
    output wire [545:0]  up_rec,
    input  wire          dp_valid,
    input  wire [545:0]  dp_rec,
    output wire          ur_valid,
    output wire [513:0]  ur_rec,
    input  wire          dr_valid,
    input  wire [513:0]  dr_rec,
    // SerDes faces: port 0 (E, beside the UCIe face), ports 1 / 2 (W); port j <-> package (rank + 1 + j) mod 4
    output wire          sx0_valid, sx1_valid, sx2_valid,
    output wire [545:0]  sx0_rec, sx1_rec, sx2_rec,
    input  wire          sr0_valid, sr1_valid, sr2_valid,
    input  wire [545:0]  sr0_rec, sr1_rec, sr2_rec,
    output wire          out_valid,
    output wire [511:0]  out_data,
    output wire          out_last,
    output wire [2:0]    out_rank,
    output wire          out_err,
    output wire          fault,
    output wire [4:0]    fault_code,
    output wire          up_slot,               // compiled link calendar -> the IO calendar qfd_coll_link_cal
    output wire          ur_peer_slot,
    output wire          sx0_peer_slot, sx1_peer_slot, sx2_peer_slot,
    output wire          cmd_free               // -> collective command issuer (fault check only)
);
`ifndef OT_QFDS_LU
`define OT_QFDS_LU 53
`endif
`ifndef OT_QFDS_LS
`define OT_QFDS_LS 376
`endif
    initial if (`OT_QFDS_LU + 2 > 64) $error("collective direct SRAM entries require a four-bank physical profile for LU>62");
    // Command pin boundary: the compiler issues one core cycle earlier than
    // the internal collective command calendar. Payload/link calendars retain
    // their original cycles. This extra command lead is paid explicitly.
    (* keep *) reg cv_pin, cm_pin;
    (* keep *) reg [15:0] cw_pin;
    (* keep *) reg [31:0] ct_pin;
    always @(posedge clk)begin cm_pin<=cmd_mode;cw_pin<=cmd_words;ct_pin<=cmd_tag;end
    always @(posedge clk or negedge rst_n)if(!rst_n)cv_pin<=0;else cv_pin<=cmd_v;
    ot_coll_tp8_static #(.LANES(16), .TAGW(32), .ADD_LAT(7), .LU(`OT_QFDS_LU), .LS(`OT_QFDS_LS), .GC(8), .CCLK(1)) u_coll (
        .clk_mem({clk_rring1,clk_rring0,clk_sring4,clk_sring3,clk_sring2,clk_sring1,clk_sring0,clk_pring1,clk_pring0}),
        .clk(clk), .clk_pfold({clk_pfold3, clk_pfold2, clk_pfold1, clk_pfold0}),
        .clk_xfold({clk_xfold3, clk_xfold2, clk_xfold1, clk_xfold0}),
        .rst_n(rst_n), .pkg_s(pkg_s), .die_ps(die_ps),
        `ifdef OT_TP8S_MUT_CMDPIN
        .cmd_v(cmd_v), .cmd_mode(cmd_mode), .cmd_words(cmd_words), .cmd_tag(cmd_tag),
`else
        .cmd_v(cv_pin), .cmd_mode(cm_pin), .cmd_words(cw_pin), .cmd_tag(ct_pin),
`endif
        .in_valid(in_valid), .in_data(in_data), .in_last(in_last), .in_mode(in_mode), .in_tag(in_tag),
        .up_valid(up_valid), .up_rec(up_rec), .dp_valid(dp_valid), .dp_rec(dp_rec),
        .ur_valid(ur_valid), .ur_rec(ur_rec), .dr_valid(dr_valid), .dr_rec(dr_rec),
        .sx_valid({sx2_valid, sx1_valid, sx0_valid}), .sx_rec({sx2_rec, sx1_rec, sx0_rec}),
        .sr_valid({sr2_valid, sr1_valid, sr0_valid}), .sr_rec({sr2_rec, sr1_rec, sr0_rec}),
        .out_valid(out_valid), .out_data(out_data), .out_last(out_last), .out_rank(out_rank), .out_err(out_err),
        .fault(fault), .fault_code(fault_code),
        .up_slot(up_slot), .ur_peer_slot(ur_peer_slot), .sx_peer_slot({sx2_peer_slot, sx1_peer_slot, sx0_peer_slot}), .cmd_free(), .cmd_free_next(cmd_free));
endmodule
