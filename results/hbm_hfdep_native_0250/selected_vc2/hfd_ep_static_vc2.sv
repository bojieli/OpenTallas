module hfd_ep_static_vc2 #(parameter integer IDLE_K = 204, parameter integer HQ = 4, parameter integer HMIN = 10,
                          parameter integer MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
     
    input  wire         tx_v,
    input  wire [611:0] tx_frame,
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
     
    input  wire         h_tx_v,
    input  wire [611:0] h_tx_frame,
    output reg          h_rx_v,
    output reg  [611:0] h_rx_frame,
    output reg          h_up,
    output reg  [2:0]   h_cause,         
     
    output wire [511:0] sd_tx,
    input  wire [511:0] sd_rx,
    input  wire [1:0]   sd_st
);
    localparam integer S = 614, HW = (HQ <= 2) ? 1 : $clog2(HQ);
    initial if (HQ < 2 || (1 << HW) != HQ || HMIN < 1 || HMIN > 32) $fatal(1, "hfd_ep_static_vc2: HQ power of two >= 2, HMIN 1..32");
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rn_tx, rn_rx, rn_bd, rn_o, rn_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rn_tx <= 1'b0; rn_rx <= 1'b0; rn_bd <= 1'b0; rn_o <= 1'b0; rn_q <= 1'b0; end
        else begin rn_tx <= rs[1]; rn_rx <= rs[1]; rn_bd <= rs[1]; rn_o <= rs[1]; rn_q <= rs[1]; end
     
    reg q_tx_v; reg [611:0] q_tx_f;
    reg q_h_v; reg [611:0] q_h_f;
    reg p_arm_v, p_arm_b, p_rel_v, p_rel_b, p_slot_v, p_slot_b;
    reg [6:0] p_words; reg [5:0] p_slot_i;
    reg [511:0] p_rx; reg [1:0] p_st;
    reg [511:0] q_rx; (* keep *) reg [7:0] p_rxd;
    always @(posedge clk) begin
        q_tx_v <= tx_v; q_tx_f <= tx_frame;
        q_h_v <= h_tx_v; q_h_f <= h_tx_frame;
        p_arm_v <= rx_arm_v; p_arm_b <= rx_arm_bank; p_words <= rx_block_words;
        p_rel_v <= rx_release_v; p_rel_b <= rx_release_bank;
        p_slot_v <= rx_slot_v; p_slot_b <= rx_slot_bank; p_slot_i <= rx_slot_index;
        p_rx <= sd_rx; p_st <= sd_st;
        q_rx <= p_rx; p_rxd <= {8{!p_rx[1]}};
    end
     
    reg [611:0] hq [0:HQ-1];
    reg [HW-1:0] hwp, hrp; reg [HW:0] hcnt; reg hq_ovf;
    wire take_next;
    wire hq_ne = hcnt != 0;
    reg [4:0] hsp;                       
                                         
    wire hsel = !q_tx_v && hq_ne && (hsp == 5'd0 || MUT == 9) && ((MUT == 6) ? 1'b1 : take_next);
    wire hpush = q_h_v && hcnt != HQ[HW:0];
    always @(posedge clk or negedge rn_q)
        if (!rn_q) begin hwp <= 0; hrp <= 0; hcnt <= 0; hq_ovf <= 1'b0; hsp <= 5'd0; end
        else begin
            hsp <= hsel ? 5'(HMIN - 1) : (hsp != 5'd0 ? hsp - 5'd1 : 5'd0);
            if (hpush) hwp <= hwp + 1'b1;
            if (hsel && MUT != 8) hrp <= hrp + 1'b1;
            hcnt <= hcnt + (hpush ? 1'b1 : 1'b0) - (hsel ? 1'b1 : 1'b0);
            if (q_h_v && hcnt == HQ[HW:0]) hq_ovf <= 1'b1;
        end
    always @(posedge clk) if (hpush) hq[hwp] <= q_h_f;
     
    reg p_tx_v, p_vc; reg [611:0] p_tx_f;
    wire [611:0] hhead = hq[hrp];
    integer k;
    always @(posedge clk) begin
        p_tx_v <= q_tx_v || hsel;
        p_vc <= hsel;
        for (k = 0; k < 612; k = k + 1) p_tx_f[k] <= q_tx_v ? q_tx_f[k] : hhead[k];
    end
    wire cal_fault;
    ot_hep_tx_gbx_vc #(.IDLE_K(IDLE_K), .S(S), .MUT((MUT == 1 || MUT == 5) ? MUT : 0)) u_tx (.clk(clk), .rst_n(rn_tx),
        .tx_v(p_tx_v), .tx_frame(p_tx_f), .tx_vc(p_vc), .beat(sd_tx), .take_next(take_next), .cal_fault(cal_fault));
    wire f_v0, f_v1, locked, lock_lost; wire [611:0] f_d;
    ot_hep_rx_gbx_vc #(.S(S), .MUT((MUT == 2 || MUT == 3 || MUT == 7) ? MUT : 0)) u_rx (.clk(clk), .rst_n(rn_rx),
        .beat(q_rx), .data_r(p_rxd), .f_v0(f_v0), .f_v1(f_v1), .f_d(f_d), .locked(locked), .lock_lost(lock_lost));
    wire phy_ready, bd_fault; wire [1:0] bready; wire [6:0] bd_cause;
    ot_hep_rx_pingpong #(.MUT(MUT == 4 ? 2 : 0)) u_rxb (.clk(clk), .rst_n(rn_bd),
        .arm_v(p_arm_v), .arm_bank(p_arm_b), .block_words(p_words),
        .phy_v(f_v0), .phy_flit(f_d), .phy_ready(phy_ready), .block_ready(bready),
        .release_v(p_rel_v), .release_bank(p_rel_b),
        .slot_v(p_slot_v), .slot_bank(p_slot_b), .slot_index(p_slot_i),
        .pin_v(rx_pin_v), .pin_flit(rx_pin_flit), .fault(bd_fault), .fault_cause(bd_cause));
     
    always @(posedge clk) h_rx_frame <= f_d;
    reg early;
    always @(posedge clk or negedge rn_o)
        if (!rn_o) begin
            early <= 1'b0; rx_block_ready <= 2'b00; phy_up <= 1'b0; fault <= 1'b0; fault_cause <= 11'd0;
            h_rx_v <= 1'b0; h_up <= 1'b0; h_cause <= 3'd0;
        end else begin
            if (f_v0 && !phy_ready) early <= 1'b1;
            rx_block_ready <= bready;
            phy_up <= p_st[1] && locked;
            h_up <= p_st[1] && locked;
            h_rx_v <= f_v1;
            fault_cause <= {p_st[0], cal_fault | hq_ovf, early, lock_lost, bd_cause};
            fault <= p_st[0] | cal_fault | hq_ovf | early | lock_lost | bd_fault;
            h_cause <= {p_st[0], cal_fault | hq_ovf, lock_lost};
        end
endmodule
