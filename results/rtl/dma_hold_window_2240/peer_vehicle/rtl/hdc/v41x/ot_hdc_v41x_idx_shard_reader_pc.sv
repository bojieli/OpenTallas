`timescale 1ns/1ps
// Two-beat, tagged per-PC compact index-key reader. Each output beat has 192
// descriptor positions: scale, code-low, code-high for each of 64 keys. Only
// the first key of an eight-key group issues the scale-sector descriptor.
// Independent pseudo-channels issue one sector/cycle; returned tags place
// sectors into either beat's reorder storage. The older complete beat drains
// first. This is a correctness/performance prototype: the wide descriptor
// arbiters and output mux still require physical closure.
module ot_hdc_v41x_idx_shard_reader_pc #(
    parameter integer NPC=32, HAW=28, TAGW=16, LENW=4, BEATW=4
) (
    input wire clk,rst_n,cmd_v,
    input wire [HAW-1:0] cmd_base_sec,
    input wire [29:0] cmd_nkeys,
    output wire busy,
    output reg fault,
    output reg [4*NPC-1:0] req_v,
    input wire [4*NPC-1:0] req_rdy,
    output reg [4*NPC*HAW-1:0] req_addr,
    output wire [4*NPC*LENW-1:0] req_len,
    output reg [4*NPC*TAGW-1:0] req_tag,
    input wire [4*NPC-1:0] rsp_v,
    output wire [4*NPC-1:0] rsp_rdy,
    input wire [4*NPC*TAGW-1:0] rsp_tag,
    input wire [4*NPC*BEATW-1:0] rsp_beat,
    input wire [4*NPC*256-1:0] rsp_data,
    output wire o_valid,
    input wire o_ready,
    output reg [63:0] o_kv,
    output reg [3:0] o_last,
    output reg [64*544-1:0] o_key,
    output reg [63:0] o_ref,
    output reg [47:0] cnt_keys_streamed,cnt_hbm_beats,cnt_refused
);
    localparam integer NP=4*NPC, LPC=$clog2(NPC), D=192;
    reg [29:0] n,qs,total_beats,next_beat,beat_id[0:1];
    reg [HAW-1:0] base_sec;
    reg [1:0] active;
    reg drain;
    reg [8:0] pending[0:1];
    reg [D-1:0] valid_desc[0:1],sent_desc[0:1];
    reg [HAW-1:0] daddr[0:1][0:D-1];
    reg [$clog2(NP)-1:0] dport[0:1][0:D-1];
    reg [255:0] scales[0:1][0:7];
    reg [255:0] code_lo[0:1][0:63],code_hi[0:1][0:63];
    assign busy=|active;
    assign o_valid=active[drain] && pending[drain]==0;
    assign rsp_rdy={NP{1'b1}};
    genvar gp;
    generate for(gp=0;gp<NP;gp=gp+1) begin:g_len
        assign req_len[gp*LENW +: LENW]=LENW'(1);
    end endgenerate
    function automatic [LPC-1:0] pc_of(input [HAW-1:0] a);
        pc_of=LPC'((a>>2) ^ (a>>(2+LPC)) ^ (a>>(2+2*LPC)));
    endfunction
    function automatic ref_key(input [31:0] scale_word);
        ref_key=(scale_word[7:0]>=8'd253 || scale_word[15:8]>=8'd253 ||
                 scale_word[23:16]>=8'd253 || scale_word[31:24]>=8'd253);
    endfunction
    task automatic launch(input integer si,input [29:0] bi,
                          input [29:0] nk,input [HAW-1:0] bs);
        integer q,l,ki,d,glob,loc,sb,w,stack,port,need;
        reg [HAW-1:0] sec0,sec1;
        reg [29:0] qsize,qlen;
        begin
            qsize=8*(nk>>5);need=0;
            beat_id[si]<=bi;active[si]<=1'b1;sent_desc[si]<='0;
            for(q=0;q<4;q=q+1) begin
                qlen=q==3 ? nk-3*qsize : qsize;
                for(l=0;l<16;l=l+1) begin
                    ki=16*q+l;d=3*ki;
                    glob=q*qsize+16*bi+l;
                    loc=(glob>>6)*16+(glob&15);
                    stack=(glob>>4)&3;
                    sb=loc>>10;w=loc&1023;
                    sec0=bs+HAW'(2176*sb+(w>>3));
                    sec1=bs+HAW'(2176*sb+128+2*w);
                    valid_desc[si][d]=(16*bi+l<qlen) && ((l&7)==0);
                    valid_desc[si][d+1]=(16*bi+l<qlen);
                    valid_desc[si][d+2]=(16*bi+l<qlen);
                    daddr[si][d]=sec0;
                    daddr[si][d+1]=sec1;
                    daddr[si][d+2]=sec1+HAW'(1);
                    port=stack*NPC+pc_of(sec0);
                    dport[si][d]=$clog2(NP)'(port);
                    port=stack*NPC+pc_of(sec1);
                    dport[si][d+1]=$clog2(NP)'(port);
                    port=stack*NPC+pc_of(sec1+HAW'(1));
                    dport[si][d+2]=$clog2(NP)'(port);
                    if(16*bi+l<qlen) need=need+2+((l&7)==0);
                end
            end
            pending[si]<=9'(need);
        end
    endtask

    // Each pseudo-channel selects its oldest unissued descriptor. The mask is
    // updated only on ready, so the selected address and tag hold under stall.
    reg [D-1:0] accepted[0:1];
    reg [7:0] selected_idx[0:NP-1];
    reg selected_slot[0:NP-1],selected_valid[0:NP-1];
    integer p,d,si,oi,chosen;
    always @* begin
        req_v='0;req_addr='0;req_tag='0;
        accepted[0]='0;accepted[1]='0;
        for(p=0;p<NP;p=p+1) begin
            chosen=-1;si=drain;
            for(d=0;d<D;d=d+1)
                if(chosen<0 && active[si] && valid_desc[si][d] &&
                   !sent_desc[si][d] && dport[si][d]==p) chosen=d;
            if(chosen<0) begin
                si=!drain;
                for(d=0;d<D;d=d+1)
                    if(chosen<0 && active[si] && valid_desc[si][d] &&
                       !sent_desc[si][d] && dport[si][d]==p) chosen=d;
            end
            selected_valid[p]=chosen>=0;
            selected_slot[p]=si[0];
            selected_idx[p]=8'(chosen);
            if(chosen>=0) begin
                req_v[p]=1'b1;
                req_addr[p*HAW +: HAW]=daddr[si][chosen];
                req_tag[p*TAGW +: TAGW]=TAGW'((si<<8)|chosen);
                if(req_rdy[p]) accepted[si][chosen]=1'b1;
            end
        end
    end

    // Tags are (slot, descriptor index). A response can arrive on any PC in
    // any cycle; descriptor index recovers quarter/lane and scale/code half.
    reg [8:0] ret_count[0:1];
    integer rp,rs,rd;
    always @* begin
        ret_count[0]=0;ret_count[1]=0;
        for(rp=0;rp<NP;rp=rp+1) if(rsp_v[rp]) begin
            rs=rsp_tag[rp*TAGW+8];
            ret_count[rs]=ret_count[rs]+1'b1;
        end
    end
    integer r,slot,idx,key,group;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            active<=0;drain<=0;n<=0;qs<=0;total_beats<=0;next_beat<=0;
            base_sec<=0;pending[0]<=0;pending[1]<=0;
            sent_desc[0]<=0;sent_desc[1]<=0;
            fault<=0;cnt_keys_streamed<=0;cnt_hbm_beats<=0;cnt_refused<=0;
        end else begin
            sent_desc[0]<=sent_desc[0]|accepted[0];
            sent_desc[1]<=sent_desc[1]|accepted[1];
            if(ret_count[0]!=0) pending[0]<=pending[0]-ret_count[0];
            if(ret_count[1]!=0) pending[1]<=pending[1]-ret_count[1];
            cnt_hbm_beats<=cnt_hbm_beats+ret_count[0]+ret_count[1];
            for(r=0;r<NP;r=r+1) if(rsp_v[r]) begin
                slot=rsp_tag[r*TAGW+8];idx=rsp_tag[r*TAGW +: 8];
                key=idx/3;group=(key/16)*2+((key%16)>>3);
                if(slot>1 || idx>=D || !active[slot] ||
                   !valid_desc[slot][idx] || !sent_desc[slot][idx] ||
                   dport[slot][idx]!=r ||
                   rsp_beat[r*BEATW +: BEATW]!=0) fault<=1'b1;
                else case(idx%3)
                    0: scales[slot][group]=rsp_data[r*256 +: 256];
                    1: code_lo[slot][key]=rsp_data[r*256 +: 256];
                    2: code_hi[slot][key]=rsp_data[r*256 +: 256];
                endcase
            end
            if(!busy && cmd_v) begin
                fault<=cmd_nkeys==0;
                n<=cmd_nkeys;qs<=8*(cmd_nkeys>>5);base_sec<=cmd_base_sec;
                total_beats<=(cmd_nkeys-3*(8*(cmd_nkeys>>5))+15)>>4;
                drain<=0;
                if(cmd_nkeys!=0) begin
                    launch(0,0,cmd_nkeys,cmd_base_sec);
                    if(((cmd_nkeys-3*(8*(cmd_nkeys>>5))+15)>>4)>1) begin
                        launch(1,1,cmd_nkeys,cmd_base_sec);next_beat<=2;
                    end else begin active[1]<=0;next_beat<=1;end
                end
            end else if(o_valid && o_ready) begin
                cnt_keys_streamed<=cnt_keys_streamed+48'(pop_keys);
                cnt_refused<=cnt_refused+48'(pop_refs);
                if(next_beat<total_beats) begin
                    launch(drain,next_beat,n,base_sec);
                    next_beat<=next_beat+1'b1;
                end else active[drain]<=0;
                drain<=!drain;
            end
        end
    end

    integer q,l,k,glob,qlen,pop_keys,pop_refs;
    reg [31:0] sw;
    always @* begin
        o_key='0;o_kv='0;o_ref='0;o_last='0;
        pop_keys=0;pop_refs=0;sw=0;glob=0;qlen=0;k=0;
        for(q=0;q<4;q=q+1) begin
            qlen=q==3 ? n-3*qs : qs;
            o_last[q]=(qlen==0) ? (beat_id[drain]==0) :
                      (beat_id[drain]==((qlen-1)>>4));
            for(l=0;l<16;l=l+1) begin
                k=16*q+l;glob=q*qs+16*beat_id[drain]+l;
                if(16*beat_id[drain]+l<qlen) begin
                    sw=scales[drain][2*q+(l>>3)][32*(glob&7) +: 32];
                    o_key[544*k +: 544]={sw,code_hi[drain][k],code_lo[drain][k]};
                    o_kv[k]=1'b1;
                    o_ref[k]=ref_key(sw);
                    pop_keys=pop_keys+1;
                    pop_refs=pop_refs+ref_key(sw);
                end
            end
        end
    end
endmodule
