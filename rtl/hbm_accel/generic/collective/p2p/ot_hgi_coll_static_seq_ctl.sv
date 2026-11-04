`timescale 1ns/1ps
`default_nettype none
// HBM-owned FW561/CW32 specialization of the exact native slot controller.
// Qwen source stays unchanged. Native ownership, CRC, pin capture and TX3/RX1
// pipelines are retained; full16 sequence and wrapper faults suppress valid in
// its registered D cone, before publication. Exceptional abort has no recovery.
// Native source blob: 4e7c69f591dc5e6e235e444e1f40cc1f18864682
// RXPRE=1 (DIE-HBM-61/RTL-C3 RE-FORM 11-03, used by ot_hbm_host_link_capture only; default 0 = the native form): the
// one RX CRC is computed from p_rx_flit, one edge before rf (rf <= p_rx_flit on every edge), and only its mismatch bit
// is registered.  crc_bad is the same on every edge (0 added cycles); rf -> 32-bit CRC over 580 bits -> crc_bad ->
// full_fault -> p_tx_v/rx_v was the worst stage of ot_hbm_host_cp_rxs (pre-build gate TT +52).
// RXPRE=2 / TXPRE=1 (DIE-HBM-61/CUTS 11-03, opt-in, used by ot_hbm_host_link_capture CRCSPLIT=1 only; defaults = the
// forms above, unchanged): the 580-bit CRC-32 trees are split into NCH=4 registered chunk syndromes one edge earlier
// (the CRC is affine over GF(2): crc(a^b) = crc(a)^crc(b)^crc(0)), so each edge holds at most a 145-bit chunk tree or a
// 5-term combine + compare.  RXPRE=2: p_rx_flit is presented ONE EDGE EARLY (the caller skips its pin flop; rfp below
// is that pin flop): chunk syndromes of p_rx_flit and rfp land on the same edge, ne_q = (combine != rfp CRC field) and
// rf <= rfp, so ne_q / rf / every output are identical on every edge to RXPRE=1 fed from the pin flop.  TXPRE=1: the
// q_data chunk syndromes are registered beside q_pin; tx_crc = XOR(chunks) ^ crc(e3/s3 header with q zeroed).  p_tx_flit
// identical on every edge.  0 added cycles.  CMUT (bench only): 1 RX correction term dropped, 2 TX header term dropped,
// 3 RX chunk 2 one edge stale.  NCH 4 is fixed (the combines below name 4 chunks).
module ot_hgi_coll_static_seq_ctl #(parameter integer RXPRE=0, parameter integer TXPRE=0, parameter integer CMUT=0) (
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
    localparam integer NCH=4, CHW=(FW+NCH-1)/NCH;
    generate if(TXPRE!=0)begin:g_txpre
        // chunk k of q_data (bits [k*CHW, min((k+1)*CHW, FW)) at their body positions, all else 0), registered with q_pin
        for(genvar k=0;k<NCH;k=k+1)begin:g_tc
            localparam integer LO=k*CHW, HI=((k+1)*CHW<FW)?(k+1)*CHW:FW;
            wire [FW+18:0] dk={19'd0,q_data & (((561'd1<<(HI-LO))-561'd1)<<LO)};
            wire [CW-1:0] ck;
            ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_c(.d(dk),.q(ck));
            reg [CW-1:0] r;
            always @(posedge clk)r<=ck;
        end
        wire [CW-1:0] hk;
        ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_h(.d({body[FW+18:FW],{FW{1'b0}}}),.q(hk));
        // 5 affine terms (4 chunks + header): odd count, so the seed term appears once = crc(body) exactly
        assign tx_crc=g_tc[0].r^g_tc[1].r^g_tc[2].r^g_tc[3].r^((CMUT==2)?{CW{1'b0}}:hk);
    end else begin:g_txcur
        ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_tx_crc(.d(body),.q(tx_crc));
    end endgenerate
    wire rx_crc_ne;
    wire [611:0] rx_in;                               // the flit rf captures (= the caller's pin flop Q)
    generate if(RXPRE==2)begin:g_rxsplit
        reg [611:0] rfp;                              // RXPRE=2: the RX pin flop (p_rx_flit arrives one edge early)
        always @(posedge clk)rfp<=p_rx_flit;
        assign rx_in=rfp;
        reg [CW-1:0] rpp2_late;
        for(genvar k=0;k<NCH;k=k+1)begin:g_rc
            localparam integer LO=k*CHW, HI=((k+1)*CHW<FW)?(k+1)*CHW:FW;
            // chunk k of the 580-bit CRC body; the 19 header bits ride with chunk NCH-1
            localparam integer HI2=(k==NCH-1)?FW+19:HI;
            wire [FW+18:0] dk=p_rx_flit[FW+18:0] & (((580'd1<<(HI2-LO))-580'd1)<<LO);
            wire [CW-1:0] ck;
            ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_c(.d(dk),.q(ck));
            reg [CW-1:0] r;
            always @(posedge clk)r<=ck;
        end
        always @(posedge clk)rpp2_late<=g_rc[2].r;
        wire [CW-1:0] z0;   // crc(0) = the seed term: 4 chunk terms are even, so it is added once more
        ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_z(.d({(FW+19){1'b0}}),.q(z0));
        assign rx_crc=g_rc[0].r^g_rc[1].r^((CMUT==3)?rpp2_late:g_rc[2].r)^g_rc[3].r^((CMUT==1)?{CW{1'b0}}:z0);
        reg ne_q;
        always @(posedge clk)ne_q<=(rx_crc!==rfp[PW-1-:CW]);
        assign rx_crc_ne=ne_q;
    end else if(RXPRE!=0)begin:g_rxpre
        assign rx_in=p_rx_flit;
        ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(p_rx_flit[FW+18:0]
`ifdef C3MUT_RX_BIT
            ^{1'b1,{(FW+18){1'b0}}}
`endif
            ),.q(rx_crc));
        reg ne_q;
`ifdef C3MUT_RX_STALE
        always @(posedge clk)ne_q<=(rx_crc!==rf[PW-1-:CW]);
`else
        always @(posedge clk)ne_q<=(rx_crc!==p_rx_flit[PW-1-:CW]);
`endif
`ifdef C3MUT_RX_NOREG
        assign rx_crc_ne=(rx_crc!==p_rx_flit[PW-1-:CW]);
`else
        assign rx_crc_ne=ne_q;
`endif
    end else begin:g_rxcur
        assign rx_in=p_rx_flit;
        ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(rf[FW+18:0]),.q(rx_crc));
        assign rx_crc_ne=(rx_crc!==rf[PW-1-:CW]);
    end endgenerate
    // Inspect payload only for an expected present frame. An unexpected frame
    // is already its own fault; idle/aborted payload bits are not diagnostics.
    wire crc_bad=rv && ev && rx_crc_ne;
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
        rf<=rx_in;
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
