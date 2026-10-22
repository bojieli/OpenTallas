`timescale 1ns/1ps
`default_nettype none
// HBM-owned FW561/CW32 specialization of the exact native slot controller.
// Qwen source stays unchanged. Native ownership, CRC, pin capture and TX3/RX1
// pipelines are retained; full16 sequence and wrapper faults suppress valid in
// its registered D cone, before publication. Exceptional abort has no recovery.
// Native source blob: 4e7c69f591dc5e6e235e444e1f40cc1f18864682
module ot_hgi_coll_static_seq_ctl (
    input wire clk,
    input wire rst_n, epoch_begin,
    input wire abort_in,
    input wire [1:0] abort_cause,
    input wire [15:0] rd_seq,rx_expect_seq,
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [5:0] wr_slot,
    input wire [560:0] q_data,
    input wire rd_v,
    input wire [5:0] rd_slot,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire p_tx_up,
    output reg p_tx_v,
    output reg [611:0] p_tx_flit,
    input wire p_rx_v,
    input wire [611:0] p_rx_flit,
    output reg rx_v,
    output reg [560:0] rx_flit,
    output reg epoch_abort,
    output reg [10:0] fault_cause
);
    localparam integer FW=561,CW=32,PW=612;
    reg [15:0] ts1,ts2,ts3,rs;
    reg [63:0] written;
    reg v1,v2,v3,v4,cmd_wv;
    reg cmd_ov;
    reg [5:0] cmd_ws;
    reg [5:0] s1,s2,s3,s4;
    reg [7:0] e1,e2,e3;
    wire issue_write=wr_v && !epoch_abort && !epoch_begin;
    reg [560:0] q_pin;
    wire [FW+18:0] body={1'b0,e3,1'b0,1'b1,2'b00,s3,q_pin};
    reg rv,ev;
    reg [5:0] es;
    reg [7:0] re;
    reg [611:0] rf;
    wire [CW-1:0] tx_crc, rx_crc;
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_tx_crc(.d(body),.q(tx_crc));
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(rf[FW+18:0]),.q(rx_crc));
    // Inspect payload only for an expected present frame. An unexpected frame
    // is already its own fault; idle/aborted payload bits are not diagnostics.
    wire crc_bad=rv && ev && (rx_crc!==rf[PW-1-:CW]);
    wire slot_bad=rv && ev && (rf[FW+7:FW]!=={2'b00,es} || rf[FW+17-:8]!==re ||
                         rf[FW+8]!==1'b1 || rf[FW+9]!==1'b0 || rf[FW+18]!==1'b0);
    // Full-sequence checks are in the D cones of the output valid flops.
    // No post-register suppression or duplicate CRC is permitted.
    wire tx_seq_bad=v3 && (q_pin[560:545]!==ts3);
    wire rx_seq_bad=rv && ev && (rf[560:545]!==rs);
    // Ownership checks use pin-captured metadata. The written map follows the
    // same captured commands, one edge behind physical bank issue; faults are
    // still known before the earliest TX3 frame can leave. No calendar gating.
    wire write_collision=cmd_wv && ((v2 && cmd_ws==s2)||(v3 && cmd_ws==s3)||(v4 && cmd_ws==s4)||
        (written[cmd_ws] && !(v1 && s1==cmd_ws)));
    wire unread_slot=v1 && !written[s1] && !(cmd_wv && cmd_ws==s1);
    wire [7:0] new_fault={cmd_wv && (cmd_ov!==1'b1),write_collision,unread_slot,v3 && !p_tx_up,
                          rv && !ev,ev && !rv,slot_bad,crc_bad};
    wire [10:0] full_fault={rx_seq_bad,abort_cause[1],
        tx_seq_bad|abort_cause[0]|(abort_in && !(|abort_cause)),new_fault};
    // Payload registers have no reset/epoch enable. Validity controls their
    // observation; clocked pin registers stay real while reset fanout is small.
    always @(posedge clk)begin
        cmd_ws<=wr_slot;cmd_ov<=wr_observed_v;
        ts1<=rd_seq;ts2<=ts1;ts3<=ts2;rs<=rx_expect_seq;
        q_pin<=q_data;
        rf<=p_rx_flit;
        p_tx_flit<={tx_crc,body};
        rx_flit<=rf[560:0];
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            written<=0;cmd_wv<=0;v1<=0;v2<=0;v3<=0;v4<=0;s1<=0;s2<=0;s3<=0;s4<=0;e1<=0;e2<=0;e3<=0;
            rv<=0;ev<=0;es<=0;re<=0;
            p_tx_v<=0;rx_v<=0;
            epoch_abort<=0;fault_cause<=0;
        end else if(epoch_begin)begin
            written<=0;cmd_wv<=0;v1<=0;v2<=0;v3<=0;v4<=0;rv<=0;ev<=0;
            p_tx_v<=0;rx_v<=0;epoch_abort<=0;fault_cause<=0;
        end else begin
            cmd_wv<=wr_v && !epoch_abort;
            if(cmd_wv && !epoch_abort)written[cmd_ws]<=1'b1;
            // Every compiled read consumes exactly one publication, including
            // a concurrent write/read of an empty slot. A later lap requires
            // another write; stale contents with a good CRC cannot qualify.
            if(v1 && !epoch_abort)written[s1]<=1'b0;
            v1<=rd_v && !epoch_abort;v2<=v1;v3<=v2;v4<=v3;
            s1<=rd_slot;s2<=s1;s3<=s2;s4<=s3;e1<=epoch;e2<=e1;e3<=e2;
            // Always issue at the compiled edge. PHY-up is a fault observation.
            p_tx_v<=v3 && !epoch_abort && !abort_in && !(|full_fault);
            rv<=p_rx_v;ev<=rx_expect_v;
            es<=rx_expect_slot;re<=epoch;
            rx_v<=ev && rv && !slot_bad && !crc_bad && !rx_seq_bad && !epoch_abort && !abort_in && !(|full_fault);
            // Latch the first failing boundary. Later traffic belongs to an
            // aborted epoch and cannot poison its already established cause.
            if(!epoch_abort)begin
                fault_cause<=fault_cause|full_fault;
                if(abort_in || |full_fault)epoch_abort<=1'b1;
            end
        end
    end
endmodule
`default_nettype wire
