`timescale 1ns/1ps
// Additive per-PC consumer port join. No new FIFO/controller/protection state.
// Explicit ENABLE=0: actual warm pause, checked row+sector+tag and accepted
// WR ACK are provided by the existing fully sized protected endpoint.
// This source is not Claude's r8 RSEL CDC. Its physical binding remains OPEN;
// never qualify this endpoint using the bare ot_qwen_stream4_cdc_pc route.
module ot_qwen_s4_protected_cdc_consumer_join #(
    parameter integer ENABLE=0,PC_ID=0,TAGW=9,LD=64,WB=16,AD=64,SYNC=2,MEM_WORDS=36*131072,
    parameter integer LOCAL_WIRE_SPANS=0
)(
    input wire clk,hclk,por_n,warm_rst_n,
    output wire l_v,output wire [16:0] l_sec,output wire [7:0] l_row,
    output wire [255:0] l_data,input wire l_pop,
    input wire w_v,input wire [23:0] w_sec,input wire [255:0] w_data,input wire [TAGW-1:0] w_tag,
    output wire w_room,wd_v,output wire [TAGW-1:0] wd_tag,output wire c_fault,
    input wire wd_accept,
    input wire h_lv,input wire [16:0] h_lsec,input wire [7:0] h_lrow,input wire [255:0] h_ldata,
    output wire [2:0] h_cred,output wire h_wv,output wire [23:0] h_wsec,
    input wire h_hand,h_wcon,output wire h_cv,output wire [23:0] h_csec,
    output wire [255:0] h_cdata,output wire [TAGW-1:0] h_ctag,
    input wire h_av,input wire [TAGW-1:0] h_atag,output wire h_fault
);
    generate if(ENABLE)begin:active
        // Exact acceptance from the consumer (or the checked stack return
        // owner). Never map bare CDC pulse ACK to an unconditional retire.
        ot_qwen_s4_protected_pc #(.PC_ID(PC_ID),.TAGW(TAGW),.LD(LD),.WB(WB),.AD(AD),
            .SYNC(SYNC),.MEM_WORDS(MEM_WORDS),.LOCAL_WIRE_SPANS(LOCAL_WIRE_SPANS),
            .ACK_BACKPRESSURE(1)) u_endpoint(
            .clk(clk),.hclk(hclk),.por_n(por_n),.warm_rst_n(warm_rst_n),
            .l_v(l_v),.l_sec(l_sec),.l_row(l_row),.l_data(l_data),.l_pop(l_pop),
            .w_v(w_v),.w_sec(w_sec),.w_data(w_data),.w_tag(w_tag),.w_room(w_room),
            .wd_v(wd_v),.wd_tag(wd_tag),.wd_ready(wd_accept),.c_fault(c_fault),
            .h_lv(h_lv),.h_lsec(h_lsec),.h_lrow(h_lrow),.h_ldata(h_ldata),.h_cred(h_cred),
            .h_wv(h_wv),.h_wsec(h_wsec),.h_hand(h_hand),.h_wcon(h_wcon),
            .h_cv(h_cv),.h_csec(h_csec),.h_cdata(h_cdata),.h_ctag(h_ctag),
            .h_av(h_av),.h_atag(h_atag),.h_fault(h_fault));
    end else begin:off
        assign {l_v,l_sec,l_row,l_data,w_room,wd_v,wd_tag,c_fault,
            h_cred,h_wv,h_wsec,h_cv,h_csec,h_cdata,h_ctag,h_fault}='0;
    end endgenerate
endmodule
