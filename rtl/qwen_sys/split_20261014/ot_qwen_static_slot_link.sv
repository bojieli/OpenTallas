`timescale 1ns/1ps
// Compiler scheduled normal transport. Writes and reads name immutable slots;
// neither PHY-up, acknowledgements, credits nor receiver arrival select issue.
// TX: slot read at edge n -> registered frame at n+2. RX: physical pin capture
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
    output reg p_tx_v,
    output reg [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output reg rx_v,
    output reg [FW-1:0] rx_flit,
    output reg epoch_abort,
    output reg [6:0] fault_cause
);
    localparam integer BW=(FW+3)/4;
    wire [4*BW-1:0] wd={{(4*BW-FW){1'b0}},wr_flit};
    wire [4*BW-1:0] rd;
    reg [63:0] written;
    reg v1,v2;
    reg [5:0] s1,s2;
    reg [7:0] e1,e2;
    wire issue_write=wr_v && !epoch_abort && !epoch_begin;
    for(genvar b=0;b<4;b=b+1)begin:g_bank
        ot_qkvd_llr_replay_sram_leaf #(.W(BW),.MUT(MUT==3 && b==0)) u_store(
            .ck(ck[b+1]),.we(issue_write),.wa(wr_slot),.ra(rd_slot),
            .din(wd[b*BW+:BW]),.dout(rd[b*BW+:BW]));
    end
    function automatic [CW-1:0] crc(input [FW+18:0] d);
        integer k;reg [CW-1:0] c;reg f;
        begin
            c={CW{1'b1}};
            for(k=FW+18;k>=0;k=k-1)begin
                f=c[CW-1]^d[k];
                c={c[CW-2:0],1'b0}^(f ? (CW==32 ? CW'(32'h04c11db7):CW'(16'h1021)):{CW{1'b0}});
            end
            crc=c;
        end
    endfunction
    wire [FW+18:0] body={1'b0,e2,1'b0,1'b1,2'b00,s2,rd[FW-1:0]};
    reg rv,ev;
    reg [5:0] es;
    reg [7:0] re;
    reg [PW-1:0] rf;
    wire crc_bad=rv && crc(rf[FW+18:0])!=rf[PW-1-:CW];
    wire slot_bad=rv && (rf[FW+7:FW]!={2'b00,es} || rf[FW+17-:8]!=re ||
                         !rf[FW+8] || rf[FW+9] || rf[FW+18]);
    wire write_collision=wr_v && ((v1 && wr_slot==s1)||(v2 && wr_slot==s2));
    wire unread_slot=rd_v && !written[rd_slot] && !(wr_v && wr_slot==rd_slot);
    wire [6:0] new_fault={write_collision,unread_slot,v2 && !p_tx_up,
                          rv && !ev,ev && !rv,slot_bad,crc_bad};
    always @(posedge ck[0] or negedge rst_n)begin
        if(!rst_n)begin
            written<=0;v1<=0;v2<=0;s1<=0;s2<=0;e1<=0;e2<=0;
            rv<=0;ev<=0;es<=0;re<=0;rf<=0;
            p_tx_v<=0;p_tx_flit<=0;rx_v<=0;rx_flit<=0;
            epoch_abort<=0;fault_cause<=0;
        end else if(epoch_begin)begin
            written<=0;v1<=0;v2<=0;rv<=0;ev<=0;
            p_tx_v<=0;rx_v<=0;epoch_abort<=0;fault_cause<=0;
        end else begin
            if(issue_write)written[wr_slot]<=1'b1;
            v1<=rd_v && !epoch_abort;v2<=v1;
            s1<=rd_slot;s2<=s1;e1<=epoch;e2<=e1;
            // Always issue at the compiled edge. PHY-up is a fault observation.
            p_tx_v<=v2 && !epoch_abort;
            if(v2)p_tx_flit<={crc(body),body};
            rv<=p_rx_v;rf<=p_rx_flit;ev<=rx_expect_v;
            es<=rx_expect_slot;re<=epoch;
            rx_v<=ev && rv && !slot_bad && !crc_bad && !epoch_abort;
            if(ev && rv)rx_flit<=rf[FW-1:0];
            fault_cause<=fault_cause|new_fault;
            if(|new_fault)epoch_abort<=1'b1;
        end
    end
endmodule
