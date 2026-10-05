`timescale 1ps/1fs
// Selected STREAM4 record wire. This is a finite protected transport seat,
// not the controller or a generic ownership service. Default OFF.
// All wire hops use tx_clk; rx_clk is the real receiving root. The existing
// SYNC2/checked decoder is the CDC cut. No generated phase/clock alias.
// Forward WIDTH296: {PC5,kind2,payload289}; reverse WIDTH288:
// {PC5,kind2,payload281}. Forward kinds: write, descriptor, GO, reserved.
// Reverse kinds: landing, actual WR ACK, consumed-descriptor ACK, status.
// Descriptor payload {ordinal3,row19,count11}, GO/descACK ordinal3;
// unused payload bits are zero. Write/landing/tag packing matches STREAM4.
// A descriptor ACK means actual controller consumption, not wire delivery.
// WR ACK means actual WR completion with its original tag, never handoff.
// rx_take transfers to a finite checked consumer; rx_retire is that consumer's
// ordered retirement callback. Taking a record does NOT return its credit.
// Cold POR erases. Warm only closes fresh tx admission. Accepted work drains
// or remains held; it is neither replayed nor dropped. link_quiet must be
// composed with actual controller/cache/PHY quiet before system warm release.
module ot_qwen_s4_packet_link #(
    parameter integer ENABLE=0, WIDTH=296, DEPTH=128,
    parameter integer STACK=0, KIND=5, WIRE_SPANS=55,
    parameter integer P=$clog2(DEPTH)+1
)(
    input wire tx_clk,rx_clk,cold_por_n,warm_rst_n,
    input wire tx_valid,output wire tx_ready,input wire [WIDTH-1:0] tx_frame,
    output wire rx_valid,input wire rx_take,output wire [WIDTH-1:0] rx_frame,
    output wire [P-1:0] rx_owner,input wire rx_retire,
    output wire [P-1:0] tx_debt,rx_retired,
    output wire tx_fault,rx_fault,link_quiet
);
    generate if(ENABLE)begin:active
        wire warm0,warm1;
        ot_reset_sync u_warm0(.clk(tx_clk),.async_rst_n(warm_rst_n),.sync_rst_n(warm0));
        ot_reset_sync u_warm1(.clk(tx_clk),.async_rst_n(warm_rst_n),.sync_rst_n(warm1));
        ot_qwen_s4_protected_ring #(.WIDTH(WIDTH),.DEPTH(DEPTH),.PC_ID(STACK),.KIND(KIND),.WIRE_STAGES(WIRE_SPANS)) u_ring(
            .wr_clk(tx_clk),.rd_clk(rx_clk),.por_n(cold_por_n),.allow_new(warm0&&warm1),
            .wr_valid(tx_valid),.wr_ready(tx_ready),.wr_data(tx_frame),.wr_occupancy(tx_debt),.wr_fault(tx_fault),
            .retired_source(),.retired_source_valid(),
            .rd_valid(rx_valid),.rd_ready(rx_take),.rd_data(rx_frame),.rd_owner(rx_owner),
            .retire(rx_retire),.retired(rx_retired),.rd_fault(rx_fault));
        assign link_quiet=cold_por_n&&!tx_fault&&!rx_fault&&(tx_debt==0)&&!rx_valid;
    end else begin:off
        assign {tx_ready,rx_valid,rx_frame,rx_owner,tx_debt,rx_retired,tx_fault,rx_fault,link_quiet}='0;
    end endgenerate
endmodule
