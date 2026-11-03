module hfd_ep_host_vc #(parameter integer MUT = 0) (
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
     
    output reg          vc_tx_v,
    output reg  [611:0] vc_tx_frame,
    input  wire         vc_rx_v,
    input  wire [611:0] vc_rx_frame,
    input  wire         vc_up,
    input  wire [2:0]   vc_cause
);
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rn_bd, rn_o;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rn_bd <= 1'b0; rn_o <= 1'b0; end else begin rn_bd <= rs[1]; rn_o <= rs[1]; end
    reg p_arm_v, p_arm_b, p_rel_v, p_rel_b, p_slot_v, p_slot_b;
    reg [6:0] p_words; reg [5:0] p_slot_i;
    reg p_rx_v; reg [611:0] p_rx_f; reg p_up; reg [2:0] p_cause;
    always @(posedge clk) begin
        vc_tx_v <= tx_v; vc_tx_frame <= tx_frame;        
        p_arm_v <= rx_arm_v; p_arm_b <= rx_arm_bank; p_words <= rx_block_words;
        p_rel_v <= rx_release_v; p_rel_b <= rx_release_bank;
        p_slot_v <= rx_slot_v; p_slot_b <= rx_slot_bank; p_slot_i <= rx_slot_index;
        p_rx_v <= vc_rx_v; p_rx_f <= vc_rx_frame; p_up <= vc_up; p_cause <= vc_cause;
    end
    wire phy_ready, bd_fault; wire [1:0] bready; wire [6:0] bd_cause;
    ot_hep_rx_pingpong #(.MUT(MUT == 4 ? 2 : 0)) u_rxb (.clk(clk), .rst_n(rn_bd),
        .arm_v(p_arm_v), .arm_bank(p_arm_b), .block_words(p_words),
        .phy_v(p_rx_v), .phy_flit(p_rx_f), .phy_ready(phy_ready), .block_ready(bready),
        .release_v(p_rel_v), .release_bank(p_rel_b),
        .slot_v(p_slot_v), .slot_bank(p_slot_b), .slot_index(p_slot_i),
        .pin_v(rx_pin_v), .pin_flit(rx_pin_flit), .fault(bd_fault), .fault_cause(bd_cause));
    reg early;
    always @(posedge clk or negedge rn_o)
        if (!rn_o) begin
            early <= 1'b0; rx_block_ready <= 2'b00; phy_up <= 1'b0; fault <= 1'b0; fault_cause <= 11'd0;
        end else begin
            if (p_rx_v && !phy_ready) early <= 1'b1;
            rx_block_ready <= bready;
            phy_up <= p_up;
            fault_cause <= {p_cause[2], p_cause[1], early, p_cause[0], bd_cause};
            fault <= (|p_cause) | early | bd_fault;
        end
endmodule
