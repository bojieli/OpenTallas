module hfd_ep_static_fc9 #(parameter integer IDLE_K = 204, parameter integer MUT = 0) (
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
    output reg  [8:0]   fault_cause,
     
    output wire [511:0] sd_tx,
    input  wire [511:0] sd_rx,
    input  wire [1:0]   sd_st
);
     
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rn_tx, rn_rx, rn_bd, rn_o;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rn_tx <= 1'b0; rn_rx <= 1'b0; rn_bd <= 1'b0; rn_o <= 1'b0; end
        else begin rn_tx <= rs[1]; rn_rx <= rs[1]; rn_bd <= rs[1]; rn_o <= rs[1]; end
     
    reg p_tx_v; reg [611:0] p_tx_f;
    reg p_arm_v, p_arm_b, p_rel_v, p_rel_b, p_slot_v, p_slot_b;
    reg [6:0] p_words; reg [5:0] p_slot_i;
    reg [511:0] p_rx; reg [1:0] p_st;
     
     
    reg [511:0] q_rx; (* keep *) reg [7:0] p_rxd;
    always @(posedge clk) begin
        p_tx_v <= tx_v; p_tx_f <= tx_frame;
        p_arm_v <= rx_arm_v; p_arm_b <= rx_arm_bank; p_words <= rx_block_words;
        p_rel_v <= rx_release_v; p_rel_b <= rx_release_bank;
        p_slot_v <= rx_slot_v; p_slot_b <= rx_slot_bank; p_slot_i <= rx_slot_index;
        p_rx <= sd_rx; p_st <= sd_st;
        q_rx <= p_rx; p_rxd <= {8{!p_rx[1]}};
    end
    wire cal_fault;
    ot_hep_tx_gbx #(.IDLE_K(IDLE_K), .MUT(MUT == 1 ? 1 : 0)) u_tx (.clk(clk), .rst_n(rn_tx), .tx_v(p_tx_v),
        .tx_frame(p_tx_f), .beat(sd_tx), .cal_fault(cal_fault));
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
            early <= 1'b0; rx_block_ready <= 2'b00; phy_up <= 1'b0; fault <= 1'b0; fault_cause <= 9'd0;
        end else begin
            if (f_v && !phy_ready) early <= 1'b1;
            rx_block_ready <= bready;
            phy_up <= p_st[1] && locked;
            fault_cause <= {p_st[0], cal_fault, early, lock_lost, bd_cause[6:5], bd_cause[2:0]};
            fault <= p_st[0] | cal_fault | early | lock_lost | bd_fault;
        end
endmodule
