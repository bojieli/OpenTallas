`timescale 1ns/1ps
// Compiler scheduled normal transport. Writes and reads name immutable slots;
// neither PHY-up, acknowledgements, credits nor receiver arrival select issue.
// TX: slot read at edge n -> registered frame at n+3. RX: physical pin capture
// at n -> checked payload at n+1. The PHY/package latency is a separate fixed
// compiler offset. A violation aborts the epoch; restart requires an explicit
// epoch_begin after the compiler's link-drain interval. No transparent retries.
// Frame: {CRC, 0, epoch8, 0, data-valid1, slot8, payloadFW}; slot8 < 64.
// CRC16/CCITT or CRC32/IEEE, MSB first, all-ones seed, no final complement.
module ot_qwen_static_slot_ctl #(
    parameter integer FW=548, CW=16, PW=FW+19+CW, MUT=0
)(
    input wire clk,
    input wire rst_n, epoch_begin,
    input wire [7:0] epoch,
    input wire wr_v,
    input wire [5:0] wr_slot,
    input wire [FW-1:0] q_data,
    input wire rd_v,
    input wire [5:0] rd_slot,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire p_tx_up,
    output reg p_tx_v,
    output reg [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output reg rx_v,
    output reg [FW-1:0] rx_flit,
    output reg epoch_abort,
    output reg [6:0] fault_cause
);
    reg [63:0] written;
    reg v1,v2,v3;
    reg [5:0] s1,s2,s3;
    reg [7:0] e1,e2,e3;
    wire issue_write=wr_v && !epoch_abort && !epoch_begin;
    reg [FW-1:0] q_pin;
    wire [FW+18:0] body={1'b0,e3,1'b0,1'b1,2'b00,s3,q_pin};
    reg rv,ev;
    reg [5:0] es;
    reg [7:0] re;
    reg [PW-1:0] rf;
    wire [CW-1:0] tx_crc, rx_crc;
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_tx_crc(.d(body),.q(tx_crc));
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(rf[FW+18:0]),.q(rx_crc));
    // Inspect payload only for an expected present frame. An unexpected frame
    // is already its own fault; idle/aborted payload bits are not diagnostics.
    wire crc_bad=rv && ev && (rx_crc!==rf[PW-1-:CW]);
    wire slot_bad=rv && ev && (rf[FW+7:FW]!=={2'b00,es} || rf[FW+17-:8]!==re ||
                         rf[FW+8]!==1'b1 || rf[FW+9]!==1'b0 || rf[FW+18]!==1'b0);
    wire write_collision=wr_v && ((v1 && wr_slot==s1)||(v2 && wr_slot==s2)||(v3 && wr_slot==s3)||
        (written[wr_slot] && !(rd_v && rd_slot==wr_slot)));
    wire unread_slot=rd_v && !written[rd_slot] && !(wr_v && wr_slot==rd_slot);
    wire [6:0] new_fault={write_collision,unread_slot,v3 && !p_tx_up,
                          rv && !ev,ev && !rv,slot_bad,crc_bad};
    // Payload registers have no reset/epoch enable. Validity controls their
    // observation; clocked pin registers stay real while reset fanout is small.
    always @(posedge clk)begin
        q_pin<=q_data;
        rf<=p_rx_flit;
        p_tx_flit<={tx_crc,body};
        rx_flit<=rf[FW-1:0];
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            written<=0;v1<=0;v2<=0;v3<=0;s1<=0;s2<=0;s3<=0;e1<=0;e2<=0;e3<=0;
            rv<=0;ev<=0;es<=0;re<=0;
            p_tx_v<=0;rx_v<=0;
            epoch_abort<=0;fault_cause<=0;
        end else if(epoch_begin)begin
            written<=0;v1<=0;v2<=0;v3<=0;rv<=0;ev<=0;
            p_tx_v<=0;rx_v<=0;epoch_abort<=0;fault_cause<=0;
        end else begin
            if(issue_write)written[wr_slot]<=1'b1;
            // Every compiled read consumes exactly one publication, including
            // a concurrent write/read of an empty slot. A later lap requires
            // another write; stale contents with a good CRC cannot qualify.
            if(rd_v && !epoch_abort)written[rd_slot]<=1'b0;
            v1<=rd_v && !epoch_abort;v2<=v1;v3<=v2;
            s1<=rd_slot;s2<=s1;s3<=s2;e1<=epoch;e2<=e1;e3<=e2;
            // Always issue at the compiled edge. PHY-up is a fault observation.
            p_tx_v<=v3 && !epoch_abort;
            rv<=p_rx_v;ev<=rx_expect_v;
            es<=rx_expect_slot;re<=epoch;
            rx_v<=ev && rv && !slot_bad && !crc_bad && !epoch_abort;
            // Latch the first failing boundary. Later traffic belongs to an
            // aborted epoch and cannot poison its already established cause.
            if(!epoch_abort)begin
                fault_cause<=fault_cause|new_fault;
                if(|new_fault)epoch_abort<=1'b1;
            end
        end
    end
endmodule

// Wires-only native composition: one control entry and four SRAM-store entries.
`timescale 1ns/1ps
// Compiler scheduled normal transport. Writes and reads name immutable slots;
// neither PHY-up, acknowledgements, credits nor receiver arrival select issue.
// TX: slot read at edge n -> registered frame at n+3. RX: physical pin capture
// at n -> checked payload at n+1. The PHY/package latency is a separate fixed
// compiler offset. A violation aborts the epoch; restart requires an explicit
// epoch_begin after the compiler's link-drain interval. No transparent retries.
// Frame: {CRC, 0, epoch8, 0, data-valid1, slot8, payloadFW}; slot8 < 64.
// CRC16/CCITT or CRC32/IEEE, MSB first, all-ones seed, no final complement.
module ot_qwen_static_slot_link #(
    parameter integer FW=548, CW=16, PW=FW+19+CW, MUT=0
)(
    input wire [4:0] ck,
    input wire rst_n, epoch_begin,
    input wire [7:0] epoch,
    input wire wr_v,
    input wire [5:0] wr_slot,
    input wire [FW-1:0] wr_flit,
    input wire rd_v,
    input wire [5:0] rd_slot,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire p_tx_up,
    output wire p_tx_v,
    output wire [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output wire rx_v,
    output wire [FW-1:0] rx_flit,
    output wire epoch_abort,
    output wire [6:0] fault_cause
);
    // Canonical physical store width is137 for548/546/514-bit payloads.
    // The smaller board words pad unused high bits, sharing the same leaf view.
    localparam integer BW=137;
    wire [4*BW-1:0] wd={{(4*BW-FW){1'b0}},wr_flit};
    wire [4*BW-1:0] rd;
    wire issue_write=wr_v && !epoch_abort && !epoch_begin;
    for(genvar b=0;b<4;b=b+1)begin:g_bank
        ot_qkvd_llr_replay_sram_leaf #(.W(BW),.MUT(MUT==3 && b==0)) u_store(
            .ck(ck[b+1]),.we(issue_write),.wa(wr_slot),.ra(rd_slot),
            .din(wd[b*BW+:BW]),.dout(rd[b*BW+:BW]));
    end
    ot_qwen_static_slot_ctl #(.FW(FW),.CW(CW),.PW(PW)) u_ctl (
        .clk(ck[0]),.q_data(rd[FW-1:0]),
        .rst_n(rst_n), .epoch_begin(epoch_begin), .epoch(epoch), .wr_v(wr_v), .wr_slot(wr_slot), .rd_v(rd_v), .rd_slot(rd_slot), .rx_expect_v(rx_expect_v), .rx_expect_slot(rx_expect_slot), .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit), .rx_v(rx_v), .rx_flit(rx_flit), .epoch_abort(epoch_abort), .fault_cause(fault_cause));
endmodule
