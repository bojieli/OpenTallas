`timescale 1ns/1ps
// Source-matched opt-in VM realization. Physical clock keeps running while the
// entire native source/controller clock is held. No native edge is admitted
// across unpaid masked writes. Read snapshot precedes every write of a frame.
// Existing bank4 macro service is the ONLY backing store. Never host m.vm.
module ot_qwen_finite_vm_adapter #(
    parameter integer ENABLE=0,
    parameter integer HEAD_CACHE=0,
    parameter integer NR=2256,
    parameter integer NW=1633,
    parameter integer VX0=192,
    parameter integer NVX=2048,
    parameter integer VM_WORDS=177808
)(
    input wire clk, rst_n,
    input wire source_me_wanted,
    input wire head_source_producer_go,
    input wire [NR-1:0] read_en,
    input wire [NR*24-1:0] read_addr,
    output reg [NR*32-1:0] read_q,
    input wire [NW-1:0] write_en,
    input wire [NW*24-1:0] write_addr,
    input wire [NW*32-1:0] write_data,
    output wire native_tick,
    output wire native_me_lease,
    output wire drained,
    output reg fault,
    output reg [63:0] native_epoch,
    output reg [63:0] physical_reads,physical_writes,physical_ACKs,
    output reg [63:0] held_edges,head_fill_reads,head_hit_edges
);
    import ot_gpu_w6_secded_pkg::*;
    localparam integer TAGW=227;
    localparam integer RW=$clog2(NR+1), WW=$clog2(NW+1);
    localparam [3:0] CAP=0,RSLOT=1,RISSUE=2,RWAIT=3,WSLOT=4,
        WISSUE=5,WWAIT=6,ADMIT=7,HFISSUE=8,HFWAIT=9;
    reg [3:0] state;
    // Immutable owned request/response seats retain the existing W6 code.
    // en/address/data57 fit one encoded64-bit seat; UE holds admission closed.
    reg [71:0] read_seat[0:NR-1],write_seat[0:NW-1];
    wire [NR-1:0] ren,read_ue;
    wire [NR*24-1:0] raddr;
    wire [NR*32-1:0] raw;
    wire [NW-1:0] wen,write_ue;
    wire [NW*24-1:0] waddr;
    wire [NW*32-1:0] wdata;
    genvar seat;
    generate for(seat=0;seat<NR;seat=seat+1)begin:g_read_seat
        wire [65:0] decoded=decode64(read_seat[seat]);
        assign read_ue[seat]=decoded[65];assign ren[seat]=decoded[56];
        assign raddr[seat*24+:24]=decoded[55:32];assign raw[seat*32+:32]=decoded[31:0];
    end
    for(seat=0;seat<NW;seat=seat+1)begin:g_write_seat
        wire [65:0] decoded=decode64(write_seat[seat]);
        assign write_ue[seat]=decoded[65];assign wen[seat]=decoded[56];
        assign waddr[seat*24+:24]=decoded[55:32];assign wdata[seat*32+:32]=decoded[31:0];
    end endgenerate
    wire frame_ue=(|read_ue)||(|write_ue);
    reg [RW-1:0] ri;
    reg [WW-1:0] wi;
    reg me_frame;
    reg [2047:0] last_window;
    reg [14:0] last_base;
    reg window_valid;
    reg [14:0] requested_base;
    reg [TAGW-1:0] pending_owner;
    reg [63:0] transaction;
    reg pack_valid;
    reg [14:0] pack_word;
    reg [15:0] pack_mask;
    reg [511:0] pack_data;
    reg [6:0] hf_sent,hf_received;
    reg [63:0] hf_owner_base;
    reg head_producer_owned,head_visible,cache_valid;
    reg [4095:0] head_coverage;
    reg [31:0] head_words[0:4095];
    // The existing XVM1 response holding stage advances ONLY on ME events.
    reg [NVX*32-1:0] xpipe;
    reg [NVX-1:0] xpipe_en;
    wire [23:0] ra = raddr[ri*24 +:24];
    wire [23:0] wa = waddr[wi*24 +:24];
    wire [31:0] wd = wdata[wi*32 +:32];
    wire req_enabled = (ri<NR) && ren[ri];
    wire wr_enabled = (wi<NW) && wen[wi];
    wire in_window = window_valid && ra[23:4]>=last_base && ra[23:4]<({1'b0,last_base}+16'd4);
    wire [5:0] window_lane = {ra[5:4]-last_base[1:0],ra[3:0]};
    wire head_parity = read_addr[VX0*24];
    reg head_pattern;
    integer c;
    always @* begin
        head_pattern=HEAD_CACHE && head_visible && cache_valid && source_me_wanted;
        for (integer k=0;k<NR;k=k+1) begin
            if (k>=VX0 && k<VX0+NVX) begin
                if (!read_en[k] || read_addr[k*24 +:24]!=(24'd8192+2*(k-VX0)+head_parity)) head_pattern=0;
            end else if (read_en[k]) head_pattern=0;
        end
    end
    wire fast_head=(state==CAP) && head_pattern && !(|write_en);
    wire fast_empty=(state==CAP) && !(|read_en) && !(|write_en);
`ifndef SYNTHESIS
    // Reset is not a rollback of SRAM visibility. Startup reset is allowed;
    // a live owned frame must drain before the caller may reset this unit.
    always @(negedge rst_n)
        if(ENABLE && (state!=CAP || pack_valid))
            $fatal(1,"finite VM reset with owned frame/visibility debt");
`endif
    // source_me_wanted includes the actual weight-window readiness. A stalled
    // weight path cannot be admitted merely because the activation cache hit.
    // A response must be consumed on a held physical edge, including a stray
    // pulse on the empty-frame fast path. Gate on bounded event reduction;
    // the owned FSM checks identity without a227-bit comparator on the gate.
    assign native_tick = ENABLE ? (rst_n && !fault && !frame_ue && !service_event && native_epoch!=64'hffffffffffffffff && ((state==ADMIT && (!me_frame||source_me_wanted))||fast_head||fast_empty)) : 1'b1;
    assign native_me_lease = ENABLE ? (native_tick && ((state==ADMIT)?me_frame:source_me_wanted)) : source_me_wanted;
    assign drained = ENABLE ? (state==CAP && !pack_valid && !fault) : 1'b1;

    wire rd_accept,rd_valid,rd_fault;
    wire [1:0] rd_rot;
    wire [2047:0] rd_words;
    wire [TAGW-1:0] rd_owner;
    wire [3:0] wr_accept,wr_ACK;
    wire [4*TAGW-1:0] wr_ACK_owner;
    wire [59:0] wr_ACK_addr;
    wire [63:0] wr_ACK_mask;
    wire wr_fault,rw_fault;
    wire service_event=rd_valid || (|wr_ACK) || rd_fault || wr_fault || rw_fault;
    wire rd_issue = ENABLE && rst_n && !fault && !frame_ue && (state==RISSUE || (state==HFISSUE && hf_sent<64));
    wire [14:0] rd_base = state==HFISSUE ? (15'd512+{hf_sent[5:0],2'b00}) : requested_base;
    wire wr_issue = ENABLE && rst_n && !fault && !frame_ue && state==WISSUE;
    wire [1:0] wb=pack_word[1:0];
    reg [3:0] bank_we;
    reg [59:0] bank_wa;
    reg [2047:0] bank_wd;
    reg [63:0] bank_mask;
    reg [4*TAGW-1:0] bank_owner;
    always @* begin
        bank_we=0;bank_wa=0;bank_wd=0;bank_mask=0;bank_owner=0;
        if(wr_issue) begin
            bank_we[wb]=1;
            bank_wa[wb*15+:15]=pack_word;
            bank_wd[wb*512+:512]=pack_data;
            bank_mask[wb*16+:16]=pack_mask;
            bank_owner[wb*TAGW+:TAGW]=pending_owner;
        end
    end
    generate if(ENABLE) begin:g_bound
        ot_qwen_checked_vm_bank #(.TAG_W(TAGW)) u_bank(
            .clk(clk),.rst_n(rst_n),.rd_v(rd_issue),.rd_base_word(rd_base),
            .rd_owner(state==HFISSUE ? owner(hf_owner_base+hf_sent,0) : pending_owner),.rd_accept_v(rd_accept),.rd_out_v(rd_valid),
            .rd_out_rot(rd_rot),.rd_out_bank_words(rd_words),.rd_out_owner(rd_owner),.rd_fault(rd_fault),
            .wr_v(bank_we),.wr_word_addr(bank_wa),.wr_word_data(bank_wd),
            .wr_lane_mask(bank_mask),.wr_owner(bank_owner),.wr_accept_v(wr_accept),
            .wr_ack_v(wr_ACK),.wr_ack_owner(wr_ACK_owner),.wr_ack_word_addr(wr_ACK_addr),
            .wr_ack_lane_mask(wr_ACK_mask),.wr_fault(wr_fault),.rw_collision_fault(rw_fault));
    end else begin:g_off
        assign rd_accept=0;assign rd_valid=0;assign rd_words=0;assign rd_rot=0;assign rd_owner=0;
        assign wr_accept=0;assign wr_ACK=0;assign wr_ACK_owner=0;assign wr_ACK_addr=0;assign wr_ACK_mask=0;
        assign rd_fault=0;assign wr_fault=0;assign rw_fault=0;
    end endgenerate
    // Internal physical transaction identity: native epoch + monotonically
    // allocated physical command. Opaque DS tag port is echoed, not a new ISA.
    function automatic [TAGW-1:0] owner(input [63:0] serial,input kind);
        owner={98'b0,native_epoch,serial,kind};
    endfunction
    task automatic publish;
        begin
            for(integer k=0;k<NR;k=k+1)
                if(k<VX0||k>=VX0+NVX) begin
                    if(ren[k])read_q[k*32+:32]<=raw[k*32+:32];
                end
            if(me_frame)begin
                for(integer k=0;k<NVX;k=k+1)begin
                    if(xpipe_en[k])read_q[(VX0+k)*32+:32]<=xpipe[k*32+:32];
                    xpipe[k*32+:32]<=raw[(VX0+k)*32+:32];
                end
                xpipe_en<=ren[VX0+:NVX];
            end
        end
    endtask
    always @(posedge clk) begin
        if(!rst_n)begin
            state<=CAP;ri<=0;wi<=0;fault<=0;native_epoch<=0;transaction<=1;
            physical_reads<=0;physical_writes<=0;physical_ACKs<=0;held_edges<=0;
            head_fill_reads<=0;head_hit_edges<=0;
            pack_valid<=0;pack_mask<=0;pack_data<=0;pack_word<=0;
            window_valid<=0;last_window<=0;last_base<=0;requested_base<=0;pending_owner<=0;
            for(integer k=0;k<NR;k=k+1)read_seat[k]<=encode64(64'b0);
            for(integer k=0;k<NW;k=k+1)write_seat[k]<=encode64(64'b0);
            me_frame<=0;
            xpipe<=0;xpipe_en<=0;read_q<=0;
            cache_valid<=0;head_visible<=0;head_coverage<=0;head_producer_owned<=0;hf_sent<=0;hf_received<=0;hf_owner_base<=0;
        end else if(ENABLE && !fault)begin
            if(rd_fault||wr_fault||rw_fault||frame_ue)fault<=1;
            if(rd_valid && state!=RWAIT && state!=HFISSUE)fault<=1;
            if((|wr_ACK) && state!=WWAIT)fault<=1;
            if(!native_tick)held_edges<=held_edges+1;
            if(native_tick && head_source_producer_go)begin
                head_producer_owned<=1;head_coverage<=0;head_visible<=0;cache_valid<=0;
            end
            case(state)
            CAP:begin
                if(fast_head)begin
                    for(integer k=0;k<NVX;k=k+1)begin
                        if(xpipe_en[k])read_q[(VX0+k)*32+:32]<=xpipe[k*32+:32];
                        xpipe[k*32+:32]<=head_words[2*k+head_parity];
                    end
                    xpipe_en<={NVX{1'b1}};
                    native_epoch<=native_epoch+1;head_hit_edges<=head_hit_edges+1;
                end else if(fast_empty)begin
                    if(source_me_wanted)begin
                        for(integer k=0;k<NVX;k=k+1)
                            if(xpipe_en[k])read_q[(VX0+k)*32+:32]<=xpipe[k*32+:32];
                        xpipe_en<=0;
                    end
                    native_epoch<=native_epoch+1;
                end else begin
                    for(integer k=0;k<NR;k=k+1)
                        read_seat[k]<=encode64({7'b0,read_en[k],read_addr[k*24+:24],32'b0});
                    for(integer k=0;k<NW;k=k+1)
                        write_seat[k]<=encode64({7'b0,write_en[k],write_addr[k*24+:24],write_data[k*32+:32]});
                    me_frame<=source_me_wanted;ri<=0;wi<=0;window_valid<=0;
                    if(HEAD_CACHE && head_visible && !cache_valid && (|read_en[VX0+:NVX]))begin
                        if(transaction>64'hffffffffffffffbf)fault<=1;
                        else begin hf_sent<=0;hf_received<=0;hf_owner_base<=transaction;transaction<=transaction+64;state<=HFISSUE;end
                    end else state<=RSLOT;
                end
            end
            RSLOT:begin
                if(ri==NR)begin wi<=0;state<=WSLOT;end
                else if(!req_enabled)ri<=ri+1;
                else if(ra>=VM_WORDS)fault<=1;
                else if(HEAD_CACHE && cache_valid && ri>=VX0 && ri<VX0+NVX && ra>=8192 && ra<12288)begin
                    read_seat[ri]<=encode64({7'b0,ren[ri],ra,head_words[ra-8192]});ri<=ri+1;
                end else if(in_window)begin read_seat[ri]<=encode64({7'b0,ren[ri],ra,last_window[window_lane*32+:32]});ri<=ri+1;end
                else begin
                    if(transaction==64'hffffffffffffffff)fault<=1;
                    else begin requested_base<={ra[18:6],2'b00};pending_owner<=owner(transaction,0);
                    transaction<=transaction+1;state<=RISSUE;end
                end
            end
            RISSUE:begin
                if(!rd_accept)fault<=1;
                else begin physical_reads<=physical_reads+1;state<=RWAIT;end
            end
            RWAIT:begin
                if(rd_valid)begin
                    if(rd_owner!=pending_owner||rd_rot!=requested_base[1:0])fault<=1;
                    else begin
                        // Rotate physical-bank output back to logical word order.
                        for(integer k=0;k<4;k=k+1)last_window[k*512+:512]<=rd_words[((requested_base[1:0]+k)%4)*512+:512];
                        last_base<=requested_base;window_valid<=1;state<=RSLOT;
                    end
                end
            end
            WSLOT:begin
                if(wi==NW || (wr_enabled && pack_valid && wa[23:4]!=pack_word))begin
                    if(pack_valid)begin
                        if(transaction==64'hffffffffffffffff)fault<=1;
                        else begin pending_owner<=owner(transaction,1);transaction<=transaction+1;state<=WISSUE;end
                    end
                    else state<=ADMIT;
                end else if(!wr_enabled)wi<=wi+1;
                else if(wa>=VM_WORDS)fault<=1;
                else begin
                    if(!pack_valid)begin
                        pack_word<=wa[18:4];pack_mask<=16'b1<<wa[3:0];
                        pack_data<=({480'b0,wd} << (wa[3:0]*32));
                    end else begin pack_mask[wa[3:0]]<=1;pack_data[wa[3:0]*32+:32]<=wd;end
                    pack_valid<=1;wi<=wi+1;
                end
            end
            WISSUE:begin
                if(wr_accept!=bank_we || !(|bank_we))fault<=1;
                else begin physical_writes<=physical_writes+1;state<=WWAIT;end
            end
            WWAIT:begin
                if(|wr_ACK)begin
                    if(wr_ACK!=(4'b1<<wb)||wr_ACK_owner[wb*TAGW+:TAGW]!=pending_owner ||
                        wr_ACK_addr[wb*15+:15]!=pack_word ||wr_ACK_mask[wb*16+:16]!=pack_mask)fault<=1;
                    else begin
                        physical_ACKs<=physical_ACKs+1;pack_valid<=0;pack_mask<=0;state<=WSLOT;
                        if(HEAD_CACHE && pack_word>=512 && pack_word<768)begin
                            cache_valid<=0;
                            if(head_producer_owned && !head_visible)begin
                                for(integer k=0;k<16;k=k+1)if(pack_mask[k])head_coverage[(pack_word-512)*16+k]<=1;
                            end else begin head_visible<=0;head_coverage<=0;head_producer_owned<=0;end
                        end
                    end
                end
            end
            ADMIT:if(native_tick)begin publish();native_epoch<=native_epoch+1;state<=CAP;end
            HFISSUE:begin
                if(hf_sent<64)begin
                    if(rd_accept)begin
                        hf_sent<=hf_sent+1;physical_reads<=physical_reads+1;
                        head_fill_reads<=head_fill_reads+1;
                    end
                end
                if(rd_valid)begin
                    if(hf_received>=64 || rd_owner!=owner(hf_owner_base+hf_received,0) || rd_rot!=0)fault<=1;
                    else begin
                        for(integer k=0;k<64;k=k+1)head_words[hf_received*64+k]<=rd_words[k*32+:32];
                        hf_received<=hf_received+1;
                        if(hf_received==63)begin cache_valid<=1;state<=RSLOT;end
                    end
                end
            end
            default:fault<=1;
            endcase
            if(HEAD_CACHE && (&head_coverage))head_visible<=1;
            if(native_tick && native_epoch==64'hffffffffffffffff)fault<=1;
        end
    end
endmodule
