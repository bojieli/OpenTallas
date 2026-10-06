`timescale 1ns/1ps
// Default-OFF simultaneous protected per-PC landing lanes; inherited write/cache/ACK.
module ot_qwen_s4_parallel_protected_pc #(
    parameter integer ENABLE=0,PC_ID=0,TAGW=9,LD=64,WB=16,AD=64,SYNC=2,MEM_WORDS=36*131072,
    parameter integer LOCAL_WIRE_SPANS=0,LANDING_RSEL=0
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
    input wire h_av,input wire [TAGW-1:0] h_atag,output wire h_fault,output wire c_quiet,h_quiet
);
    generate if(ENABLE)begin:active
        localparam integer DP=$clog2(AD)+1;
        wire [DP:0] debt_state;wire debt_bad;
        wire [DP-1:0] debt=debt_state[0+:DP];
        wire local_fault=debt_bad||debt_state[DP];
        wire room_base,cf_base,hf_base,cq_base,hq_base;
        wire ack_take=wd_v&&wd_accept&&!c_fault;
        wire write_take=w_v&&w_room;
        wire [DP-1:0] debt_next=debt+DP'(write_take)-DP'(ack_take);
        ot_qwen_s4_checked_state #(.W(DP+1)) u_ack_debt(.clk(clk),.por_n(por_n),.en(!debt_bad),
            .d({debt_state[DP]||(w_v&&!w_room)||(ack_take&&debt==0),debt_next}),.q(debt_state),.qi(debt_inverse),.bad(debt_bad));
        assign w_room=room_base&&!local_fault&&(debt<AD);
        assign c_fault=cf_base||local_fault;
        assign h_fault=hf_base;
        assign c_quiet=cq_base&&!local_fault&&(debt==0);
        (* async_reg="true",keep *) reg [DP:0] d0,d1,i0,i1;
        // Observe complementary stored rails, never manufacture a complement
        // from a potentially upset primary. Disagreement inhibits quiet.
        wire [DP:0] debt_inverse;
        // u_ack_debt.qi is the actual stored inverse rail.
        always @(posedge hclk or negedge por_n)
            if(!por_n)begin d0<=0;d1<=0;i0<='1;i1<='1;end
            else begin d0<=debt_state;d1<=d0;i0<=debt_inverse;i1<=i0;end
        assign h_quiet=hq_base&&(d1==~i1)&&(d1==0);
        // Exact acceptance from the consumer (or the checked stack return
        // owner). Never map bare CDC pulse ACK to an unconditional retire.
        ot_qwen_s4_protected_pc #(.PC_ID(PC_ID),.TAGW(TAGW),.LD(LD),.WB(WB),.AD(AD),
            .SYNC(SYNC),.MEM_WORDS(MEM_WORDS),.LOCAL_WIRE_SPANS(LOCAL_WIRE_SPANS),
            .ACK_BACKPRESSURE(1),.LANDING_RSEL(0),.RAW_SECTOR_LANES(LANDING_RSEL)) u_endpoint(
            .clk(clk),.hclk(hclk),.por_n(por_n),.warm_rst_n(warm_rst_n),
            .l_v(l_v),.l_sec(l_sec),.l_row(l_row),.l_data(l_data),.l_pop(l_pop&&!c_fault),
            .w_v(write_take),.w_sec(w_sec),.w_data(w_data),.w_tag(w_tag),.w_room(room_base),
            .wd_v(wd_v),.wd_tag(wd_tag),.wd_ready(ack_take),.c_fault(cf_base),
            .h_lv(h_lv),.h_lsec(h_lsec),.h_lrow(h_lrow),.h_ldata(h_ldata),.h_cred(h_cred),
            .h_wv(h_wv),.h_wsec(h_wsec),.h_hand(h_hand),.h_wcon(h_wcon),
            .h_cv(h_cv),.h_csec(h_csec),.h_cdata(h_cdata),.h_ctag(h_ctag),
            .h_av(h_av),.h_atag(h_atag),.h_fault(hf_base),.c_quiet(cq_base),.h_quiet(hq_base));
    end else begin:off
        assign {l_v,l_sec,l_row,l_data,w_room,wd_v,wd_tag,c_fault,
            h_cred,h_wv,h_wsec,h_cv,h_csec,h_cdata,h_ctag,h_fault,c_quiet,h_quiet}='0;
    end endgenerate
endmodule
