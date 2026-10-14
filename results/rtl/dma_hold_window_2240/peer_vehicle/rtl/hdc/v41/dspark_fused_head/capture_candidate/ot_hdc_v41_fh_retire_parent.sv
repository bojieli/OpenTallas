`timescale 1ns/1ps
// Head-owned retirement/debt owner. Commit receipts come from the actual
// memory write, carrying the emitted identity, word address and lane mask.
// A wrong receipt quarantines debt until reset; emission never clears debt.
module ot_hdc_v41_fh_retire_parent #(
    parameter integer ENABLE=0, PAYLOAD_BITS=5512,
    parameter integer MARGIN=0,  // ot_hdc_v41_fh_fault_retire MARGIN (+2 retirement cycles)
    // SAFE (default 0; needs MARGIN): +1 retirement stage (fault_retire SAFE), the receipt compare is registered (+1
    // on the warm ACK), the sink busy is registered and the drain busy covers the two cycles after retirement
    parameter integer SAFE=0
)(
    input wire clk,rst_n,
    input wire packet_v, warm,
    input wire [PAYLOAD_BITS-1:0] packet,
    input wire [23:0] warm_word,
    input wire [15:0] warm_mask,
    input wire [63:0] poison,
    input wire [3:0] address_fault,
    input wire arithmetic_fault,
    input wire [3:0] group_fault,
    input wire sink_busy,ack_v,
    input wire [7:0] ack_id,
    input wire [23:0] ack_word,
    input wire [15:0] ack_mask,
    output wire retired_v,retired_warm,
    output wire [PAYLOAD_BITS-1:0] retired_packet,
    output wire [7:0] retired_id,
    output wire [63:0] lane_veto,
    output wire [63:0] lane_veto_pre,
    output wire [3:0] write_veto,
    output wire busy,warm_ack,
    output wire fault,
    output wire warm_debt,
    // OREG support: next-edge values of retired_v / retired_packet / retired_warm / write_veto (see fault_retire)
    output wire retired_v_nx, retired_warm_nx,
    output wire [PAYLOAD_BITS-1:0] retired_packet_nx,
    output wire [3:0] write_veto_nx
);
    generate if(!ENABLE) begin : g_original
        wire f=(|poison)||(|address_fault)||arithmetic_fault||(|group_fault);
        assign retired_v=packet_v;
        assign retired_packet=packet;
        assign retired_warm=warm;
        assign retired_id=0;
        assign lane_veto={64{f}};
        assign lane_veto_pre={64{f}};
        assign write_veto={4{f}};
        assign busy=0;
        assign warm_debt=0;
        assign warm_ack=warm;
        assign fault=f;
        assign retired_v_nx=packet_v; assign retired_warm_nx=warm; assign retired_packet_nx=packet; assign write_veto_nx={4{f}};
    end else begin : g_commit
        reg [7:0] next_id,expected_id;
        reg [23:0] expected_word;
        reg [15:0] expected_mask;
        reg debt,sent,protocol_fault;
        wire pipe_busy,pipe_fault;
        wire [PAYLOAD_BITS+8-1:0] retired, retired_nx;
        wire matching_ack, ack_seen;
        if(SAFE>=2) begin : g_ack_split
            // Same receipt edge as SAFE=1; no pin sees the full 48-bit compare.
            // All slices sample the same expected tuple and av masks idle data.
            reg av;
            (* keep=1,dont_touch=1 *) reg [5:0] match_slice;
            wire [47:0] received={ack_id,ack_word,ack_mask};
            wire [47:0] expected={expected_id,expected_word,expected_mask};
            always @(posedge clk or negedge rst_n)
                if(!rst_n) av<=0; else av<=ack_v;
            for(genvar k=0;k<6;k=k+1) begin : g_slice
                always @(posedge clk or negedge rst_n)
                    if(!rst_n) match_slice[k]<=0;
                    else match_slice[k]<=received[k*8+:8]==expected[k*8+:8];
            end
            assign ack_seen=av;
            assign matching_ack=av&&(&match_slice)&&debt&&sent;
        end else if(SAFE) begin : g_ack_reg
            reg av,am;
            always @(posedge clk or negedge rst_n)
                if(!rst_n) begin av<=0;am<=0; end
                else begin av<=ack_v; am<=ack_v&&ack_id==expected_id&&ack_word==expected_word&&ack_mask==expected_mask; end
            assign ack_seen=av; assign matching_ack=av&&am&&debt&&sent;
        end else begin : g_ack_direct
            assign ack_seen=ack_v;
            assign matching_ack=ack_v&&debt&&sent&&ack_id==expected_id&&
                ack_word==expected_word&&ack_mask==expected_mask;
        end
        assign warm_ack=matching_ack&&!fault;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin
                next_id<=0;expected_id<=0;expected_word<=0;expected_mask<=0;
                debt<=0;sent<=0;protocol_fault<=0;
            end else begin
                if(packet_v) next_id<=next_id+1'b1;
                if(packet_v&&warm) begin
                    if(debt) protocol_fault<=1;
                    else begin
                        debt<=1;sent<=0;expected_id<=next_id;
                        expected_word<=warm_word;expected_mask<=warm_mask;
                    end
                end else if(warm_ack) begin debt<=0;sent<=0;end
                if(retired_warm&&!fault) sent<=1;
                if(ack_seen&&(!debt||!matching_ack)) protocol_fault<=1;
            end
        ot_hdc_v41_fh_fault_retire #(.ENABLE(1),.PACKET_BITS(PAYLOAD_BITS+8),.MARGIN(MARGIN),.SAFE(SAFE)) u_cut (
            .clk(clk),.rst_n(rst_n),.packet_v(packet_v),.packet({next_id,packet}),
            .poison(poison),.address_fault(address_fault),
            .arithmetic_fault(arithmetic_fault||protocol_fault),.group_fault(group_fault),
            .retired_v(retired_v),.retired_packet(retired),
            .lane_veto(lane_veto),.lane_veto_pre(lane_veto_pre),.write_veto(write_veto),
            .fault(pipe_fault),.busy(pipe_busy),
            .retired_v_nx(retired_v_nx),.retired_packet_nx(retired_nx),.write_veto_nx(write_veto_nx));
        assign retired_packet_nx=retired_nx[PAYLOAD_BITS-1:0];
        assign retired_warm_nx=retired_v_nx&&retired_nx[0];
        assign retired_id=retired[PAYLOAD_BITS+:8];
        assign retired_packet=retired[PAYLOAD_BITS-1:0];
        assign retired_warm=retired_v&&retired[0];
        // Commit pipelines remain part of drain even after output retirement.
        if(SAFE) begin : g_busy_reg
            reg pb1,pb2,sb1;
            always @(posedge clk or negedge rst_n)
                if(!rst_n) begin pb1<=0;pb2<=0;sb1<=0; end
                else begin pb1<=pipe_busy;pb2<=pb1;sb1<=sink_busy; end
            assign busy=pipe_busy||pb1||pb2||sb1;
        end else begin : g_busy_direct
            assign busy=pipe_busy||sink_busy;
        end
        assign warm_debt=debt;
        assign fault=pipe_fault||protocol_fault;
    end endgenerate
endmodule
