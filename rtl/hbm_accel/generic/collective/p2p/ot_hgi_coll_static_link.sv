`timescale 1ns/1ps
`default_nettype none
// HBM545 rail specialization of source-pinned native SRAM/CRC static codec.
// No PHY model or normal retry mechanism is provided. Epoch abort requests
// exceptional recovery; compiler must drain pins and explicitly begin a new
// epoch before restarting. Slots are sequence identities 0..63, once/epoch.
// Shared codec TX3/RX1 edge contract, CW32, frame596={CRC32,body564}.
module ot_hgi_coll_static_link # (parameter integer MUT=0) (
    input wire [4:0] ck,
    input wire rst_n, epoch_begin,
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [5:0] wr_slot,
    input wire [544:0] wr_flit,
    input wire rd_v,
    input wire [5:0] rd_slot,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire phy_up,
    output wire tx_pin_v,
    output wire [595:0] tx_pin_flit,
    input wire rx_pin_v,
    input wire [595:0] rx_pin_flit,
    output wire rx_v,
    output wire [544:0] rx_flit,
    output wire epoch_abort,
    output wire retry_requested,
    output wire [9:0] fault_cause
);
    reg [6:0] tx_sequence, rx_sequence;
    reg [7:0] active_epoch;
    reg seq_fault, epoch_fault, epoch_active;
    wire core_abort;
    wire [7:0] core_fault;
    // These counters advance on compiler reservations, never observed traffic.
    // They are identity checks only; they cannot postpone a command.
    always @(posedge ck[0] or negedge rst_n) begin
        if (!rst_n) begin tx_sequence<=0; rx_sequence<=0; active_epoch<=0; epoch_active<=0; seq_fault<=0; epoch_fault<=0; end
        else if(epoch_begin) begin tx_sequence<=0; rx_sequence<=0; active_epoch<=epoch; epoch_active<=1; seq_fault<=0; epoch_fault<=0; end
        else begin
            if((epoch_active && epoch != active_epoch) || (!epoch_active && (wr_v || rd_v || rx_expect_v || rx_pin_v))) epoch_fault<=1;
            if(rd_v) begin
                if(tx_sequence[6] || rd_slot != tx_sequence[5:0]) seq_fault<=1;
                if(!tx_sequence[6]) tx_sequence<=tx_sequence+1'b1;
            end
            if(rx_expect_v) begin
                if(rx_sequence[6] || rx_expect_slot != rx_sequence[5:0]) seq_fault<=1;
                if(!rx_sequence[6]) rx_sequence<=rx_sequence+1'b1;
            end
        end
    end
    assign epoch_abort = core_abort | seq_fault | epoch_fault;
    assign retry_requested = epoch_abort;
    assign fault_cause = {epoch_fault,seq_fault,core_fault};
    wire raw_rx_v;
    assign rx_v = raw_rx_v && !seq_fault && !epoch_fault;
    ot_qwen_static_slot_link #(.FW(545),.CW(32),.MUT(MUT)) u_link (
        .ck(ck),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
        .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_slot(wr_slot),.wr_flit(wr_flit),
        .rd_v(rd_v),.rd_slot(rd_slot),.rx_expect_v(rx_expect_v),.rx_expect_slot(rx_expect_slot),
        .p_tx_up(phy_up),.p_tx_v(tx_pin_v),.p_tx_flit(tx_pin_flit),
        .p_rx_v(rx_pin_v),.p_rx_flit(rx_pin_flit),.rx_v(raw_rx_v),.rx_flit(rx_flit),
        .epoch_abort(core_abort),.fault_cause(core_fault));
endmodule
`default_nettype wire
