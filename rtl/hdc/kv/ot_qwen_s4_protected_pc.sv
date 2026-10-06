`timescale 1ns/1ps
// Full-size selected element: no ROM protection, finite mutable owned rings.
// Cold POR is distinct from warm admission pause. Returns and completions
// drain through a warm pause; accepted pipeline/cache records are never reset.
module ot_qwen_s4_protected_pc #(
    parameter integer PC_ID=0,TAGW=9,LD=64,WB=16,AD=64,SYNC=2,MEM_WORDS=3*131072,
    parameter integer LOCAL_WIRE_SPANS=0,ACK_BACKPRESSURE=0,LANDING_RSEL=0
)(
    input wire clk,hclk,por_n,warm_rst_n,
    output wire l_v,output wire [16:0] l_sec,output wire [7:0] l_row,
    output wire [255:0] l_data,input wire l_pop,
    input wire w_v,input wire [23:0] w_sec,input wire [255:0] w_data,input wire [TAGW-1:0] w_tag,
    output wire w_room,wd_v,output wire [TAGW-1:0] wd_tag,output wire c_fault,
    input wire wd_ready,
    input wire h_lv,input wire [16:0] h_lsec,input wire [7:0] h_lrow,input wire [255:0] h_ldata,
    output wire [2:0] h_cred,output wire h_wv,output wire [23:0] h_wsec,
    input wire h_hand,h_wcon,output wire h_cv,output wire [23:0] h_csec,
    output wire [255:0] h_cdata,output wire [TAGW-1:0] h_ctag,
    input wire h_av,input wire [TAGW-1:0] h_atag,output wire h_fault
);
    localparam integer LP=$clog2(LD)+1,WP=$clog2(WB)+1,WW=24+256+TAGW,CW=WW+WP+1;
    wire warm0,warm1;
    ot_reset_sync u_warm0(.clk(clk),.async_rst_n(warm_rst_n),.sync_rst_n(warm0));
    ot_reset_sync u_warm1(.clk(clk),.async_rst_n(warm_rst_n),.sync_rst_n(warm1));
    wire warm_ok=warm0&&warm1;
    wire write_identity_ok=({w_sec[1:0],w_sec[15],w_sec[5:2]}==7'(PC_ID))&&(w_sec<MEM_WORDS);
    wire landing_identity_ok=({h_lsec[1:0],h_lsec[15],h_lsec[5:2]}==7'(PC_ID))&&(h_lrow<MEM_WORDS/131072);
    wire lwr,awr,wwr,lv,av,wvalid,lwb,lrb,awb,arb,wwb,wrb;
    wire [280:0] ld;wire [TAGW-1:0] ad;wire [WW-1:0] wd;
    wire [LP-1:0] locc,lowner,lret;
    wire [LP-1:0] synced_ret;
    wire synced_ret_valid;
    wire [$clog2(AD):0] aocc,aowner,aret;
    wire [WP-1:0] wocc,wowner,wret;
    wire cs,hs,cb,hb;
    assign c_fault=cb||cs||lrb||arb||wwb||room_bad;
    assign h_fault=hb||hs||lwb||awb||wrb||cache_fault||head_bad||completion_bad||credit_bad||ptr_bad;
    wire take_l=lv&&l_pop&&!c_fault;
    assign l_v=lv&&!c_fault;assign {l_sec,l_row,l_data}=ld;
    assign wd_v=av&&!c_fault;assign wd_tag=ad;
    ot_qwen_s4_protected_ring #(.WIDTH(281),.DEPTH(LD),.PC_ID(PC_ID),.KIND(0),.SYNC(SYNC),.WIRE_STAGES(LOCAL_WIRE_SPANS),.READ_RSEL(LANDING_RSEL)) u_l(
        .wr_clk(hclk),.rd_clk(clk),.por_n(por_n),.allow_new(1'b1),
        .wr_valid(h_lv&&landing_identity_ok),.wr_ready(lwr),.wr_data({h_lsec,h_lrow,h_ldata}),.wr_occupancy(locc),.wr_fault(lwb),
        .retired_source(synced_ret),.retired_source_valid(synced_ret_valid),
        .rd_valid(lv),.rd_ready(take_l),.rd_data(ld),.rd_owner(lowner),.retire(take_l),.retired(lret),.rd_fault(lrb));
    // A stack return mux must explicitly accept a real WR ACK before the
    // existing AD64 owner retires. Default pulse ABI remains unchanged.
    wire ack_take=av&&!c_fault&&(ACK_BACKPRESSURE?wd_ready:1'b1);
    ot_qwen_s4_protected_ring #(.WIDTH(TAGW),.DEPTH(AD),.PC_ID(PC_ID),.KIND(2),.SYNC(SYNC),.WIRE_STAGES(LOCAL_WIRE_SPANS)) u_a(
        .wr_clk(hclk),.rd_clk(clk),.por_n(por_n),.allow_new(1'b1),
        .wr_valid(h_av),.wr_ready(awr),.wr_data(h_atag),.wr_occupancy(aocc),.wr_fault(awb),
        .rd_valid(av),.rd_ready(ACK_BACKPRESSURE?ack_take:!c_fault),.rd_data(ad),.rd_owner(aowner),
        .retire(ack_take),.retired(aret),.rd_fault(arb));
    wire [LP+2:0] credit;
    wire credit_bad;
    wire [LP-1:0] credit_delta=synced_ret-credit[LP-1:0];
    // Fewer than eight core consumptions can occur per HCLK edge at 3:4.
    // Never truncate an invalid larger advance into a false credit.
    // This checked registered credit belongs to an earlier valid pointer pair.
    // A newer transient receiving-rail disagreement must not erase that debt.
    assign h_cred=credit_bad||h_fault ? 3'b0 : credit[LP+:3];
    ot_qwen_s4_checked_state #(.W(LP+3)) u_credit(.clk(hclk),.por_n(por_n),
        .en(!credit_bad&&!h_fault),
        .d({synced_ret_valid?3'(credit_delta):3'b0,synced_ret_valid?synced_ret:credit[LP-1:0]}),.q(credit),.bad(credit_bad));
    wire room_q,room_bad;
    assign w_room=room_q&&wwr&&warm_ok&&!c_fault;
    ot_qwen_s4_checked_state u_room(.clk(clk),.por_n(por_n),.en(!c_fault),
        .d(warm_ok&&(WB-(wocc+WP'(w_v&&wwr)))>=3),.q(room_q),.bad(room_bad));
    wire cache_take,complete_take;
    ot_qwen_s4_protected_ring #(.WIDTH(WW),.DEPTH(WB),.PC_ID(PC_ID),.KIND(1),.SYNC(SYNC),.WIRE_STAGES(LOCAL_WIRE_SPANS)) u_w(
        .wr_clk(clk),.rd_clk(hclk),.por_n(por_n),.allow_new(warm_ok&&!c_fault),
        .wr_valid(w_v&&write_identity_ok),.wr_ready(wwr),.wr_data({w_sec,w_data,w_tag}),.wr_occupancy(wocc),.wr_fault(wwb),
        .rd_valid(wvalid),.rd_ready(cache_take),.rd_data(wd),.rd_owner(wowner),
        .retire(complete_take),.retired(wret),.rd_fault(wrb));
    wire [CW-1:0] cache [0:WB-1];wire [WB-1:0] cache_bad;
    wire cache_fault=|cache_bad;
    wire [2*WP-1:0] ptr;
    wire ptr_bad;
    wire [WP-1:0] hand=ptr[0+:WP],completed=ptr[WP+:WP];
    wire [CW-1:0] head_entry=cache[hand[WP-2:0]],completion_entry=cache[completed[WP-2:0]];
    wire completion_match=completion_entry[CW-1]&&(completion_entry[WW+:WP]==completed)&&(completed!=hand);
    assign complete_take=h_wcon&&completion_match&&!h_fault;
    wire [WP-1:0] hand_next=hand+WP'(h_hand&&h_wv),completed_next=completed+WP'(complete_take);
    assign cache_take=wvalid&&!h_fault&&!cache[wowner[WP-2:0]][CW-1];
    for(genvar s=0;s<WB;s=s+1)begin:slot
        wire fill=cache_take&&(wowner[WP-2:0]==s);
        wire clear=complete_take&&(completed[WP-2:0]==s);
        ot_qwen_s4_checked_state #(.W(CW)) u_cache(.clk(hclk),.por_n(por_n),
            .en((fill||clear)&&!h_fault),.d(fill?{1'b1,wowner,wd}:{CW{1'b0}}),
            .q(cache[s]),.bad(cache_bad[s]));
    end
    ot_qwen_s4_checked_state #(.W(2*WP)) u_ptr(.clk(hclk),.por_n(por_n),.en(!h_fault),
        .d({completed_next,hand_next}),.q(ptr),.bad(ptr_bad));
    wire [CW-1:0] next_head=cache[hand_next[WP-2:0]];
    wire next_head_valid=next_head[CW-1]&&(next_head[WW+:WP]==hand_next);
    wire [24:0] head;
    wire head_bad;
    ot_qwen_s4_checked_state #(.W(25)) u_head(.clk(hclk),.por_n(por_n),.en(!h_fault),
        .d({next_head_valid,next_head_valid?next_head[WW-1-:24]:24'b0}),.q(head),.bad(head_bad));
    assign h_wv=head[24]&&!h_fault&&head_entry[CW-1]&&(head_entry[WW+:WP]==hand);
    assign h_wsec=head[23:0];
    wire [WW:0] completion;
    wire completion_bad;
    ot_qwen_s4_checked_state #(.W(WW+1)) u_completion(.clk(hclk),.por_n(por_n),.en(!h_fault),
        .d({complete_take,complete_take?completion_entry[WW-1:0]:{WW{1'b0}}}),
        .q(completion),.bad(completion_bad));
    assign h_cv=completion[WW]&&!h_fault;
    assign {h_csec,h_cdata,h_ctag}=completion[WW-1:0];
    ot_qwen_s4_checked_state u_cs(.clk(clk),.por_n(por_n),.en(!cb),
        .d(cs||(w_v&&(!wwr||!write_identity_ok))||(l_pop&&!l_v)),.q(cs),.bad(cb));
    ot_qwen_s4_checked_state u_hs(.clk(hclk),.por_n(por_n),.en(!hb),
        .d(hs||(h_lv&&(!lwr||!landing_identity_ok))||(h_av&&!awr)||(h_hand&&!h_wv)||(h_wcon&&!completion_match)||
           (synced_ret_valid&&(credit_delta>7))),.q(hs),.bad(hb));
endmodule
