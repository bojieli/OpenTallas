`timescale 1ps/1fs
// One actual STREAM4 stack: 32 PCs, finite shared forward/return pools.
// Root and stack anchor use the real free service clock. Local protected PC
// rings and controller control cross to independent HCLK outside this cut.
// Backend warm must stay released: all backend traffic already owns a root
// reservation. Only fresh root advertisements/descriptor reservations pause.
// No DRAM model, numerical provider, phase alias, or PHY is inside this cut.
module ot_qwen_s4_stack_transport #(
    parameter integer ENABLE=0,STACK=0,MEM_ROWS=36,WIRE_SPANS=41
)(
    input wire clk,cold_por_n,warm_rst_n,
    input wire d_v,go,input wire [18:0] d_row,input wire [10:0] d_n,
    output wire d_ready,
    input wire [31:0] w_v,input wire [32*24-1:0] w_sec,
    input wire [32*256-1:0] w_data,input wire [32*9-1:0] w_tag,
    output wire [31:0] w_room,wd_v,output wire [32*9-1:0] wd_tag,
    input wire [31:0] wd_accept,
    output wire [31:0] l_v,output wire [32*17-1:0] l_sec,
    output wire [32*8-1:0] l_row,output wire [32*256-1:0] l_data,
    input wire [31:0] l_pop,
    output wire b_desc_v,b_go,output wire [18:0] b_desc_row,
    output wire [10:0] b_desc_n,input wire b_desc_ready,b_go_ready,
    output wire [31:0] b_w_v,output wire [32*24-1:0] b_w_sec,
    output wire [32*256-1:0] b_w_data,output wire [32*9-1:0] b_w_tag,
    input wire [31:0] b_w_room,b_wd_v,input wire [32*9-1:0] b_wd_tag,
    output wire [31:0] b_wd_ready,
    input wire [31:0] b_l_v,input wire [32*17-1:0] b_l_sec,
    input wire [32*8-1:0] b_l_row,input wire [32*256-1:0] b_l_data,
    output wire [31:0] b_l_pop,
    // These events must be the sealed HCLK->CLK callback of actual controller
    // desc_v&&desc_r or h_go, never acceptance at b_desc_v/b_go above.
    input wire b_desc_done,b_go_done,input wire [2:0] b_done_ordinal,
    output wire b_done_ready,input wire b_external_fault,b_busy,
    output wire c_fault,b_fault,quiet,
    output wire [7:0] forward_debt,return_debt
);
generate if(ENABLE)begin:active
    wire warm0,warm1;
    ot_reset_sync u_w0(.clk(clk),.async_rst_n(warm_rst_n),.sync_rst_n(warm0));
    ot_reset_sync u_w1(.clk(clk),.async_rst_n(warm_rst_n),.sync_rst_n(warm1));
    wire warm_ok=warm0&&warm1;
    // Root42: descriptor33, active,desc pending,GO pending,desc sent,GO sent,
    // descriptor acknowledged,next ordinal3. Fresh GO consumes the reservation
    // made with its descriptor, including while warm admission is paused.
    wire [41:0] root;reg [41:0] root_next;wire root_bad;
    wire [19:0] cs;reg [19:0] cs_next;wire cs_bad;
    // CS: RR5,advertisedPC5+valid,priorPC5+valid,prior descriptor grant,
    // sticky fault,one reserved bit. Service w_v is registered one edge after
    // seeing w_room; it must be compared to the PRIOR advertisement.
    wire [4:0] grant=cs[9:5],prior=cs[15:11];
    wire [19:0] bs;reg [19:0] bs_next;wire bs_bad;
    // BS: return RR5,desc ACK pending+ordinal3,GO ACK pending+ordinal3,
    // sticky fault,fault-report sent; remaining bits reserved.
    wire [28:0] fm[0:127];wire [127:0] fm_bad;
    wire [9:0] rm[0:127];wire [127:0] rm_bad;
    wire [14:0] ticket[0:63];wire [63:0] ticket_bad;
    wire [3:0] ptr[0:31];wire [31:0] ptr_bad;
    wire [289:0] cache[0:63];wire [63:0] cache_bad;
    wire [7:0] fr_owner,fr_ret,rr_owner,rr_ret;
    wire ft_ready,fr_valid,fr_take,fr_release,ft_fault,fr_fault,fq;
    wire rt_ready,rr_valid,rr_take,rr_release,rt_fault,rr_fault,rq;
    wire [295:0] fr_frame;reg [295:0] ft_frame;
    wire [287:0] rr_frame;reg [287:0] rt_frame;
    reg ft_valid,rt_valid;
    wire [4:0] fpc=fr_frame[295:291],rpc=rr_frame[287:283];
    wire [1:0] fkind=fr_frame[290:289],rkind=rr_frame[282:281];
    wire [288:0] fp=fr_frame[288:0];wire [280:0] rp=rr_frame[280:0];
    wire [2:0] ford=fkind==1?fp[32:30]:fp[2:0];
    wire [6:0] expected_pc={2'(STACK),fpc};
    wire write_ok=({fp[266:265],fp[280],fp[270:267]}==expected_pc)&&
        (fp[288:265]<MEM_ROWS*131072)&&fp[8];
    wire desc_ok=fpc==0&&fp[288:33]==0&&fp[29:11]<MEM_ROWS&&fp[10:0]>0&&fp[10:0]<=1024;
    wire go_ok=fpc==0&&fp[288:3]==0;
    wire fmeta_free=!fm[fr_owner[6:0]][28];
    wire fsemantic=(fkind==0?write_ok:fkind==1?desc_ok:fkind==2?go_ok:1'b0);
    wire fdispatch=fr_valid&&!b_fault&&fmeta_free&&fsemantic;
    assign b_desc_v=fdispatch&&fkind==1;
    assign b_desc_row=fp[29:11];assign b_desc_n=fp[10:0];
    assign b_go=fdispatch&&fkind==2&&b_go_ready;
    assign b_w_v=fdispatch&&fkind==0&&b_w_room[fpc]?(32'b1<<fpc):32'b0;
    assign fr_take=fdispatch&&(fkind==0?b_w_room[fpc]:fkind==1?b_desc_ready:b_go_ready);
    assign fr_release=!b_fault&&fm[fr_ret[6:0]][28]&&fm[fr_ret[6:0]][27]&&fm[fr_ret[6:0]][26:19]==fr_ret;
    assign rr_release=!c_fault&&rm[rr_ret[6:0]][9]&&rm[rr_ret[6:0]][8]&&rm[rr_ret[6:0]][7:0]==rr_ret;
    for(genvar p=0;p<32;p=p+1)begin:backend_data
        assign b_w_sec[p*24+:24]=fp[288:265];
        assign b_w_data[p*256+:256]=fp[264:9];assign b_w_tag[p*9+:9]=fp[8:0];
    end
    wire iq_ready,iq_valid,iq_take,iq_wbad,iq_rbad;
    wire [4:0] iq_occ;wire [295:0] iq_frame;
    wire input_any=|w_v;
    wire input_one=(w_v==(32'b1<<prior))&&cs[16];
    wire [8:0] in_tag=w_tag[prior*9+:9];
    wire input_identity=in_tag[8]&&!ticket[in_tag[5:0]][14];
    wire input_take=input_any&&input_one&&input_identity&&!c_fault&&iq_ready;
    wire [295:0] in_frame={prior,2'b00,w_sec[prior*24+:24],w_data[prior*256+:256],in_tag};
    ot_qwen_s4_protected_ring #(.WIDTH(296),.DEPTH(16),.PC_ID(STACK),.KIND(5)) u_ingress(
        .wr_clk(clk),.rd_clk(clk),.por_n(cold_por_n),.allow_new(1'b1),
        .wr_valid(input_take),.wr_ready(iq_ready),.wr_data(in_frame),.wr_occupancy(iq_occ),.wr_fault(iq_wbad),
        .rd_valid(iq_valid),.rd_ready(iq_take),.rd_data(iq_frame),.rd_owner(),.retire(iq_take),.retired(),.rd_fault(iq_rbad),
        .retired_source(),.retired_source_valid());
    wire descriptor_accept=d_v&&!root[33]&&(d_ready||cs[17]);
    wire cfg_ok=d_row<MEM_ROWS&&d_n>0&&d_n<=1024;
    wire go_accept=go&&(root[33]||descriptor_accept)&&!root[35]&&!root[37];
    assign d_ready=warm_ok&&!root[33]&&!c_fault;
    assign w_room=cs[10]&&!c_fault?(32'b1<<grant):32'b0;
    always @* begin
        ft_valid=0;ft_frame=0;
        if(!c_fault)begin
            if(root[34])begin ft_valid=1;ft_frame={5'b0,2'b01,256'b0,root[32:0]};end
            else if(root[35]&&root[36])begin ft_valid=1;ft_frame={5'b0,2'b10,286'b0,root[32:30]};end
            else if(iq_valid&&forward_debt<124)begin ft_valid=1;ft_frame=iq_frame;end
        end
    end
    wire ft_accept=ft_valid&&ft_ready;
    assign iq_take=ft_accept&&ft_frame[290:289]==0;
    ot_qwen_s4_packet_link #(.ENABLE(1),.WIDTH(296),.STACK(STACK),.KIND(5),.WIRE_SPANS(WIRE_SPANS)) u_forward(
        .tx_clk(clk),.rx_clk(clk),.cold_por_n(cold_por_n),.warm_rst_n(1'b1),
        .tx_valid(ft_valid),.tx_ready(ft_ready),.tx_frame(ft_frame),
        .rx_valid(fr_valid),.rx_take(fr_take),.rx_frame(fr_frame),.rx_owner(fr_owner),.rx_retire(fr_release),
        .tx_debt(forward_debt),.rx_retired(fr_ret),.tx_fault(ft_fault),.rx_fault(fr_fault),.link_quiet(fq));
    reg [31:0] wr_match;
    reg desc_match,go_match;
    always @* begin
        wr_match=0;desc_match=0;go_match=0;
        for(integer i=0;i<128;i=i+1)if(fm[i][28]&&!fm[i][27])begin
            if(fm[i][18:17]==0&&fm[i][11:3]==b_wd_tag[fm[i][16:12]*9+:9])wr_match[fm[i][16:12]]=1;
            if(fm[i][18:17]==1&&fm[i][2:0]==b_done_ordinal)desc_match=1;
            if(fm[i][18:17]==2&&fm[i][2:0]==b_done_ordinal)go_match=1;
        end
    end
    assign b_done_ready=!b_fault&&(b_desc_done?!bs[5]:b_go_done?!bs[9]:1'b0);
    wire callback_take=b_done_ready&&(b_desc_done||b_go_done);
    wire callback_bad=(b_desc_done&&b_go_done)||(callback_take&&(b_desc_done?!desc_match:!go_match));
    reg return_found;reg [4:0] return_pc;reg return_ACK;
    always @* begin
        return_found=0;return_pc=0;return_ACK=0;
        for(integer k=0;k<32;k=k+1)begin
            if(!return_found&&b_wd_v[5'(bs[4:0]+k)])begin
                return_found=1;return_pc=5'(bs[4:0]+k);return_ACK=1;
            end
        end
        for(integer k=0;k<32;k=k+1)begin
            if(!return_found&&b_l_v[5'(bs[4:0]+k)])begin
                return_found=1;return_pc=5'(bs[4:0]+k);
            end
        end
        rt_valid=0;rt_frame=0;
        if(!b_fault)begin
            if(bs[5])begin rt_valid=1;rt_frame={5'b0,2'b10,278'b0,bs[8:6]};end
            else if(bs[9])begin rt_valid=1;rt_frame={5'b0,2'b11,274'b0,bs[12:10],1'b0,1'b1,b_busy,1'b1};end
            else if(return_found&&return_debt<124)begin
                rt_valid=1;
                if(return_ACK)begin rt_valid=wr_match[return_pc];rt_frame={return_pc,2'b01,272'b0,b_wd_tag[return_pc*9+:9]};end
                else rt_frame={return_pc,2'b00,b_l_sec[return_pc*17+:17],b_l_row[return_pc*8+:8],b_l_data[return_pc*256+:256]};
            end
        end else if(!bs[14]&&!rt_fault)begin
            // Fault report owns its reserved control seat. It never carries
            // a descriptor/GO or WR retirement authority.
            rt_valid=1;rt_frame={5'b0,2'b11,272'b0,9'b000001000};
        end
    end
    wire rt_accept=rt_valid&&rt_ready;
    assign b_wd_ready=rt_accept&&rt_frame[282:281]==1&&wr_match[return_pc]?(32'b1<<return_pc):0;
    assign b_l_pop=rt_accept&&rt_frame[282:281]==0?(32'b1<<return_pc):0;
    ot_qwen_s4_packet_link #(.ENABLE(1),.WIDTH(288),.STACK(STACK),.KIND(6),.WIRE_SPANS(WIRE_SPANS)) u_return(
        .tx_clk(clk),.rx_clk(clk),.cold_por_n(cold_por_n),.warm_rst_n(1'b1),
        .tx_valid(rt_valid),.tx_ready(rt_ready),.tx_frame(rt_frame),
        .rx_valid(rr_valid),.rx_take(rr_take),.rx_frame(rr_frame),.rx_owner(rr_owner),.rx_retire(rr_release),
        .tx_debt(return_debt),.rx_retired(rr_ret),.tx_fault(rt_fault),.rx_fault(rr_fault),.link_quiet(rq));
    wire [14:0] reply_ticket=ticket[rp[5:0]];
    wire ack_ok=rp[280:9]==0&&rp[8]&&reply_ticket[14]&&reply_ticket[13:9]==rpc&&reply_ticket[8:0]==rp[8:0];
    wire row_ok=({rp[265:264],rp[279],rp[269:266]}=={2'(STACK),rpc})&&rp[263:256]<MEM_ROWS;
    wire desc_reply_ok=rpc==0&&rp[280:3]==0&&root[33]&&root[36]&&!root[38]&&rp[2:0]==root[32:30];
    wire go_reply_ok=rpc==0&&rp[280:7]==0&&!rp[3]&&rp[2]&&rp[0]&&root[33]&&root[37]&&rp[6:4]==root[32:30];
    wire rmeta_free=!rm[rr_owner[6:0]][9];
    wire [1:0] rpc_occ=ptr[rpc][1:0]-ptr[rpc][3:2];
    wire landing_room=rpc_occ<2||l_pop[rpc]&&l_v[rpc];
    assign wd_v=rr_valid&&!c_fault&&rmeta_free&&rkind==1&&ack_ok?(32'b1<<rpc):0;
    for(genvar p=0;p<32;p=p+1)begin:root_data
        assign wd_tag[p*9+:9]=rp[8:0];
        wire [1:0] head=ptr[p][3:2],tail=ptr[p][1:0];
        wire [1:0] occ=tail-head;
        wire [289:0] entry=cache[p*2+head[0]];
        assign l_v[p]=occ!=0&&entry[289]&&!c_fault;
        assign {l_sec[p*17+:17],l_row[p*8+:8],l_data[p*256+:256]}=entry[280:0];
        wire pop=l_pop[p]&&l_v[p];
        wire fill=rr_take&&rkind==0&&rpc==p;
        ot_qwen_s4_checked_state #(.W(4)) u_ptr(.clk(clk),.por_n(cold_por_n),.en(!c_fault),
            .d({head+2'(pop),tail+2'(fill)}),.q(ptr[p]),.bad(ptr_bad[p]));
        for(genvar j=0;j<2;j=j+1)begin:seat
            wire put=fill&&tail[0]==j,clear=pop&&head[0]==j;
            ot_qwen_s4_checked_state #(.W(290)) u_cache(.clk(clk),.por_n(cold_por_n),.en((put||clear)&&!c_fault),
                .d(put?{1'b1,rr_owner,rp}:290'b0),.q(cache[p*2+j]),.bad(cache_bad[p*2+j]));
        end
    end
    wire reply_semantic=rkind==0?row_ok:rkind==1?ack_ok:rkind==2?desc_reply_ok:go_reply_ok;
    assign rr_take=rr_valid&&!c_fault&&rmeta_free&&reply_semantic&&
        (rkind==0?landing_room:rkind==1?wd_accept[rpc]:1'b1);
    wire root_protocol_bad=(d_v&&(!descriptor_accept||!cfg_ok))||(go&&!go_accept)||
        (input_any&&(!input_one||!input_identity||!iq_ready))||
        (rr_valid&&(!rmeta_free||!reply_semantic))||(|(wd_v&~wd_accept));
    assign c_fault=cs_bad||cs[18]||root_bad||(|ticket_bad)||(|rm_bad)||(|ptr_bad)||(|cache_bad)||ft_fault||rr_fault||iq_wbad||iq_rbad;
    wire backend_protocol_bad=callback_bad||(fr_valid&&(!fmeta_free||!fsemantic))||
        (|(b_wd_v&~wr_match));
    assign b_fault=bs_bad||bs[13]||(|fm_bad)||fr_fault||rt_fault||b_external_fault;
    always @* begin
        cs_next=cs;cs_next[4:0]=cs[4:0]+1'b1;
        cs_next[9:5]=cs[4:0];cs_next[10]=warm_ok&&!c_fault&&iq_ready&&iq_occ<=12;
        cs_next[15:11]=grant;cs_next[16]=cs[10];cs_next[17]=d_ready;
        cs_next[18]=cs[18]||root_protocol_bad;
        root_next=root;
        if(descriptor_accept&&cfg_ok)begin
            root_next={root[41:39]+3'b1,1'b0,1'b0,1'b0,1'b0,1'b1,1'b1,root[41:39],d_row,d_n};
        end
        if(go_accept)root_next[35]=1;
        if(ft_accept&&ft_frame[290:289]==1)begin root_next[34]=0;root_next[36]=1;end
        if(ft_accept&&ft_frame[290:289]==2)begin root_next[35]=0;root_next[37]=1;end
        if(rr_take&&rkind==2)root_next[38]=1;
        if(rr_take&&rkind==3)root_next[33]=0;
        bs_next=bs;
        bs_next[13]=bs[13]||backend_protocol_bad||b_external_fault;
        if(callback_take&&!callback_bad)begin
            if(b_desc_done)begin bs_next[5]=1;bs_next[8:6]=b_done_ordinal;end
            else begin bs_next[9]=1;bs_next[12:10]=b_done_ordinal;end
        end
        if(rt_accept)begin
            if(rt_frame[282:281]==2)bs_next[5]=0;
            else if(rt_frame[282:281]==3)begin
                if(rt_frame[3])bs_next[14]=1;else bs_next[9]=0;
            end
            else bs_next[4:0]=return_pc+1'b1;
        end
    end
    ot_qwen_s4_checked_state #(.W(20)) u_cs(.clk(clk),.por_n(cold_por_n),.en(!cs_bad),.d(cs_next),.q(cs),.bad(cs_bad));
    ot_qwen_s4_checked_state #(.W(42)) u_root(.clk(clk),.por_n(cold_por_n),.en(!c_fault),.d(root_next),.q(root),.bad(root_bad));
    ot_qwen_s4_checked_state #(.W(20)) u_bs(.clk(clk),.por_n(cold_por_n),.en(!bs_bad),.d(bs_next),.q(bs),.bad(bs_bad));
    for(genvar i=0;i<64;i=i+1)begin:source_identity
        wire fill=input_take&&in_tag[5:0]==i;
        wire clear=rr_take&&rkind==1&&rp[5:0]==i;
        ot_qwen_s4_checked_state #(.W(15)) u_ticket(.clk(clk),.por_n(cold_por_n),.en((fill||clear)&&!c_fault),
            .d(fill?{1'b1,prior,in_tag}:15'b0),.q(ticket[i]),.bad(ticket_bad[i]));
    end
    for(genvar i=0;i<128;i=i+1)begin:callbacks
        wire ff=fr_take&&fr_owner[6:0]==i;
        wire fc=fr_release&&fr_ret[6:0]==i;
        wire fdone=fm[i][28]&&!fm[i][27]&&
            (fm[i][18:17]==0?(b_wd_v[fm[i][16:12]]&&b_wd_ready[fm[i][16:12]]&&fm[i][11:3]==b_wd_tag[fm[i][16:12]*9+:9]):
             callback_take&&!callback_bad&&fm[i][2:0]==b_done_ordinal&&
             (fm[i][18:17]==1?b_desc_done:b_go_done));
        ot_qwen_s4_checked_state #(.W(29)) u_forward_meta(.clk(clk),.por_n(cold_por_n),.en((ff||fc||fdone)&&!b_fault),
            .d(ff?{1'b1,1'b0,fr_owner,fkind,fpc,fp[8:0],ford}:fc?29'b0:{fm[i][28],1'b1,fm[i][26:0]}),
            .q(fm[i]),.bad(fm_bad[i]));
        wire rf=rr_take&&rr_owner[6:0]==i;
        wire rc=rr_release&&rr_ret[6:0]==i;
        reg rdone;
        always @* begin
            rdone=0;
            for(integer p=0;p<32;p=p+1)
                if(l_pop[p]&&l_v[p]&&cache[p*2+ptr[p][2]][288:281]==rm[i][7:0])rdone=1;
        end
        ot_qwen_s4_checked_state #(.W(10)) u_return_meta(.clk(clk),.por_n(cold_por_n),.en((rf||rc||rdone)&&!c_fault),
            .d(rf?{1'b1,rkind!=0,rr_owner}:rc?10'b0:{rm[i][9],1'b1,rm[i][7:0]}),.q(rm[i]),.bad(rm_bad[i]));
    end
    reg tickets_empty,caches_empty;
    always @* begin
        tickets_empty=1;caches_empty=1;
        for(integer i=0;i<64;i=i+1)if(ticket[i][14])tickets_empty=0;
        for(integer p=0;p<32;p=p+1)if(ptr[p][1:0]!=ptr[p][3:2])caches_empty=0;
    end
    assign quiet=cold_por_n&&!c_fault&&!b_fault&&fq&&rq&&iq_occ==0&&!iq_valid&&
        tickets_empty&&caches_empty&&!root[33]&&!bs[5]&&!bs[9]&&!b_busy&&!(|b_l_v)&&!(|b_wd_v)&&!b_desc_done&&!b_go_done;
end else begin:off
    assign {d_ready,w_room,wd_v,wd_tag,l_v,l_sec,l_row,l_data,b_desc_v,b_go,b_desc_row,b_desc_n,
        b_w_v,b_w_sec,b_w_data,b_w_tag,b_wd_ready,b_l_pop,b_done_ready,c_fault,b_fault,quiet,forward_debt,return_debt}='0;
end endgenerate
endmodule
