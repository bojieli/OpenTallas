`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-20-EPA 2026-10-29 (COORD 13:38 hfd_ep_static plan change, variant (a), OPT-IN, die-local): hfd_ep_static split
// into a TX core and an RX core on natural boundaries.  Bodies are hfd_ep_static__fcore line for line, cut at the only
// TX->RX dependency (cal_fault, a sticky status bit).  ot_hep_tx_gbx / ot_hep_rx_gbx / ot_hep_rx_pingpong unchanged.
// Each core has its own 2-flop reset synchroniser from the same rst_n (same depth as the original: rs[1] -> rn_*).
// Composition vs hfd_ep_static (face-shelled): every output bit is cycle-identical except fault_cause[9] and fault,
// whose cal_fault term arrives +2 edges later (tx out face reg + rx in face reg); cal_fault is sticky, so after the
// first 2 edges of a calendar fault the values are identical again.
// GEOM-61 root cause addressed: the TX gearbox (1,225 frame/beat flops + 510 5-way selects) no longer shares the 31-um
// strips beside the 4 SRAM column; the TX core is SRAM-free.
module hfd_ep_static_tx__fcore #(parameter integer IDLE_K = 204, parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         tx_v,
    input  wire [611:0] tx_frame,
    output wire [511:0] sd_tx,
    output wire         tx_cal_fault
);
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rn_tx;
    always @(posedge clk or negedge rst_n) if (!rst_n) rn_tx <= 1'b0; else rn_tx <= rs[1];
    reg p_tx_v; reg [611:0] p_tx_f;
    always @(posedge clk) begin p_tx_v <= tx_v; p_tx_f <= tx_frame; end
    ot_hep_tx_gbx #(.IDLE_K(IDLE_K), .MUT(MUT == 1 ? 1 : 0)) u_tx (.clk(clk), .rst_n(rn_tx), .tx_v(p_tx_v),
        .tx_frame(p_tx_f), .beat(sd_tx), .cal_fault(tx_cal_fault));
endmodule

module hfd_ep_static_rx__fcore #(parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         tx_cal_fault,   // from hfd_ep_static_tx (registered there; face-registered here)
    input  wire         rx_arm_v,
    input  wire         rx_arm_bank,
    input  wire [6:0]   rx_block_words,
    input  wire         rx_release_v,
    input  wire         rx_release_bank,
    input  wire         rx_slot_v,
    input  wire         rx_slot_bank,
    input  wire [5:0]   rx_slot_index,
    output wire         rx_pin_v,
    output wire [611:0] rx_pin_flit,
    output reg  [1:0]   rx_block_ready,
    output reg          phy_up,
    output reg          fault,
    output reg  [10:0]  fault_cause,
    input  wire [511:0] sd_rx,
    input  wire [1:0]   sd_st
);
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rn_rx, rn_bd, rn_o;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rn_rx <= 1'b0; rn_bd <= 1'b0; rn_o <= 1'b0; end
        else begin rn_rx <= rs[1]; rn_bd <= rs[1]; rn_o <= rs[1]; end
    reg p_arm_v, p_arm_b, p_rel_v, p_rel_b, p_slot_v, p_slot_b;
    reg [6:0] p_words; reg [5:0] p_slot_i;
    reg [511:0] p_rx; reg [1:0] p_st;
    reg [511:0] q_rx; (* keep *) reg [7:0] p_rxd;
    always @(posedge clk) begin
        p_arm_v <= rx_arm_v; p_arm_b <= rx_arm_bank; p_words <= rx_block_words;
        p_rel_v <= rx_release_v; p_rel_b <= rx_release_bank;
        p_slot_v <= rx_slot_v; p_slot_b <= rx_slot_bank; p_slot_i <= rx_slot_index;
        p_rx <= sd_rx; p_st <= sd_st;
        q_rx <= p_rx; p_rxd <= {8{!p_rx[1]}};
    end
    wire f_v, locked, lock_lost; wire [611:0] f_d;
    ot_hep_rx_gbx #(.MUT((MUT == 2 || MUT == 3) ? MUT : 0)) u_rx (.clk(clk), .rst_n(rn_rx), .beat(q_rx), .data_r(p_rxd),
        .f_v(f_v), .f_d(f_d), .locked(locked), .lock_lost(lock_lost));
    wire phy_ready, bd_fault; wire [1:0] bready; wire [6:0] bd_cause;
    ot_hep_rx_pingpong #(.MUT(MUT == 4 ? 2 : 0)) u_rxb (.clk(clk), .rst_n(rn_bd),
        .arm_v(p_arm_v), .arm_bank(p_arm_b), .block_words(p_words),
        .phy_v(f_v), .phy_flit(f_d), .phy_ready(phy_ready), .block_ready(bready),
        .release_v(p_rel_v), .release_bank(p_rel_b),
        .slot_v(p_slot_v), .slot_bank(p_slot_b), .slot_index(p_slot_i),
        .pin_v(rx_pin_v), .pin_flit(rx_pin_flit), .fault(bd_fault), .fault_cause(bd_cause));
    reg early;
    always @(posedge clk or negedge rn_o)
        if (!rn_o) begin
            early <= 1'b0; rx_block_ready <= 2'b00; phy_up <= 1'b0; fault <= 1'b0; fault_cause <= 11'd0;
        end else begin
            if (f_v && !phy_ready) early <= 1'b1;
            rx_block_ready <= bready;
            phy_up <= p_st[1] && locked;
            fault_cause <= {p_st[0], tx_cal_fault, early, lock_lost, bd_cause};
            fault <= p_st[0] | tx_cal_fault | early | lock_lost | bd_fault;
        end
endmodule

// face shells (same form as face_shell.py output: every signal pin bit its own flop, clk/rst pass through)
module hfd_ep_static_tx (
    input  wire clk, input wire rst_n,
    input  wire tx_v, input wire [611:0] tx_frame,
    output wire [511:0] sd_tx, output wire tx_cal_fault
);
    wire [0:0] tx_v__fq; wire [611:0] tx_frame__fq; wire [511:0] sd_tx__fc; wire [0:0] cf__fc;
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bin_tx_v     (.clk(clk), .d(tx_v), .q(tx_v__fq));
    (* keep *) ot_hbm_face_reg #(.W(612)) u_bin_tx_frame (.clk(clk), .d(tx_frame), .q(tx_frame__fq));
    (* keep *) ot_hbm_face_reg #(.W(512)) u_bout_sd_tx   (.clk(clk), .d(sd_tx__fc), .q(sd_tx));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bout_tx_cal_fault (.clk(clk), .d(cf__fc), .q(tx_cal_fault));
    hfd_ep_static_tx__fcore u_fcore (.clk(clk), .rst_n(rst_n), .tx_v(tx_v__fq), .tx_frame(tx_frame__fq),
        .sd_tx(sd_tx__fc), .tx_cal_fault(cf__fc));
endmodule

module hfd_ep_static_rx (
    input wire clk, input wire rst_n, input wire tx_cal_fault,
    input wire rx_arm_v, input wire rx_arm_bank, input wire [6:0] rx_block_words,
    input wire rx_release_v, input wire rx_release_bank, input wire rx_slot_v, input wire rx_slot_bank,
    input wire [5:0] rx_slot_index,
    output wire rx_pin_v, output wire [611:0] rx_pin_flit, output wire [1:0] rx_block_ready,
    output wire phy_up, output wire fault, output wire [10:0] fault_cause,
    input wire [511:0] sd_rx, input wire [1:0] sd_st
);
    wire cf__fq, av__fq, ab__fq, rv__fq, rb__fq, sv__fq, sb__fq; wire [6:0] bw__fq; wire [5:0] si__fq;
    wire [511:0] sd_rx__fq; wire [1:0] sd_st__fq;
    wire pv__fc, pu__fc, f__fc; wire [611:0] pf__fc; wire [1:0] br__fc; wire [10:0] fc__fc;
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bin_tx_cal_fault  (.clk(clk), .d(tx_cal_fault), .q(cf__fq));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bin_rx_arm_v      (.clk(clk), .d(rx_arm_v), .q(av__fq));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bin_rx_arm_bank   (.clk(clk), .d(rx_arm_bank), .q(ab__fq));
    (* keep *) ot_hbm_face_reg #(.W(7))   u_bin_rx_block_words(.clk(clk), .d(rx_block_words), .q(bw__fq));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bin_rx_release_v  (.clk(clk), .d(rx_release_v), .q(rv__fq));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bin_rx_release_bank(.clk(clk), .d(rx_release_bank), .q(rb__fq));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bin_rx_slot_v     (.clk(clk), .d(rx_slot_v), .q(sv__fq));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bin_rx_slot_bank  (.clk(clk), .d(rx_slot_bank), .q(sb__fq));
    (* keep *) ot_hbm_face_reg #(.W(6))   u_bin_rx_slot_index (.clk(clk), .d(rx_slot_index), .q(si__fq));
    (* keep *) ot_hbm_face_reg #(.W(512)) u_bin_sd_rx         (.clk(clk), .d(sd_rx), .q(sd_rx__fq));
    (* keep *) ot_hbm_face_reg #(.W(2))   u_bin_sd_st         (.clk(clk), .d(sd_st), .q(sd_st__fq));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bout_rx_pin_v     (.clk(clk), .d(pv__fc), .q(rx_pin_v));
    (* keep *) ot_hbm_face_reg #(.W(612)) u_bout_rx_pin_flit  (.clk(clk), .d(pf__fc), .q(rx_pin_flit));
    (* keep *) ot_hbm_face_reg #(.W(2))   u_bout_rx_block_ready(.clk(clk), .d(br__fc), .q(rx_block_ready));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bout_phy_up       (.clk(clk), .d(pu__fc), .q(phy_up));
    (* keep *) ot_hbm_face_reg #(.W(1))   u_bout_fault        (.clk(clk), .d(f__fc), .q(fault));
    (* keep *) ot_hbm_face_reg #(.W(11))  u_bout_fault_cause  (.clk(clk), .d(fc__fc), .q(fault_cause));
    hfd_ep_static_rx__fcore u_fcore (.clk(clk), .rst_n(rst_n), .tx_cal_fault(cf__fq),
        .rx_arm_v(av__fq), .rx_arm_bank(ab__fq), .rx_block_words(bw__fq), .rx_release_v(rv__fq),
        .rx_release_bank(rb__fq), .rx_slot_v(sv__fq), .rx_slot_bank(sb__fq), .rx_slot_index(si__fq),
        .rx_pin_v(pv__fc), .rx_pin_flit(pf__fc), .rx_block_ready(br__fc), .phy_up(pu__fc), .fault(f__fc),
        .fault_cause(fc__fc), .sd_rx(sd_rx__fq), .sd_st(sd_st__fq));
endmodule

// composition used only by the equivalence bench (the parent wires these two nets; no logic in the parent)
module hfd_ep_static_pair (
    input wire clk, input wire rst_n, input wire tx_v, input wire [611:0] tx_frame,
    input wire rx_arm_v, input wire rx_arm_bank, input wire [6:0] rx_block_words,
    input wire rx_release_v, input wire rx_release_bank, input wire rx_slot_v, input wire rx_slot_bank,
    input wire [5:0] rx_slot_index,
    output wire rx_pin_v, output wire [611:0] rx_pin_flit, output wire [1:0] rx_block_ready,
    output wire phy_up, output wire fault, output wire [10:0] fault_cause,
    output wire [511:0] sd_tx, input wire [511:0] sd_rx, input wire [1:0] sd_st
);
    wire cf;
    hfd_ep_static_tx u_tx_core (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_frame(tx_frame), .sd_tx(sd_tx), .tx_cal_fault(cf));
    hfd_ep_static_rx u_rx_core (.clk(clk), .rst_n(rst_n), .tx_cal_fault(cf), .rx_arm_v(rx_arm_v), .rx_arm_bank(rx_arm_bank),
        .rx_block_words(rx_block_words), .rx_release_v(rx_release_v), .rx_release_bank(rx_release_bank),
        .rx_slot_v(rx_slot_v), .rx_slot_bank(rx_slot_bank), .rx_slot_index(rx_slot_index), .rx_pin_v(rx_pin_v),
        .rx_pin_flit(rx_pin_flit), .rx_block_ready(rx_block_ready), .phy_up(phy_up), .fault(fault),
        .fault_cause(fault_cause), .sd_rx(sd_rx), .sd_st(sd_st));
endmodule
`default_nettype wire
