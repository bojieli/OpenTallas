`timescale 1ps/1fs
// Service-boundary ownership only. The downstream stack has the ONE bank/REF
// controller per PC. Original tags and beats are never borrowed for client IDs.
// Up to32 reserved reads plus32 unposted accesses require64 read-owner entries.
// Requests can backpressure at this finite external-HBM service boundary;
// an exclusive static reservation is still required for an Engram time bound.
module ot_hbm_native_client_mux #(
    parameter integer CLIENTS=3,
    parameter integer MUT_READ_OWNER=0,MUT_EARLY_ACK=0,MUT_BURST_COUNT=0
)(
    input wire[31:0]pc_clk,input wire rst_n,
    input wire[CLIENTS*32-1:0]c_k_v,output wire[CLIENTS*32-1:0]c_k_rdy,input wire[CLIENTS*32-1:0]c_k_we,
    input wire[CLIENTS*960-1:0]c_k_addr,input wire[CLIENTS*128-1:0]c_k_len,input wire[CLIENTS*544-1:0]c_k_tag,
    input wire[CLIENTS*8192-1:0]c_k_wdata,input wire[CLIENTS*1024-1:0]c_k_wstrb,
    output wire[CLIENTS*32-1:0]c_kr_v,input wire[CLIENTS*32-1:0]c_kr_rdy,
    output wire[CLIENTS*544-1:0]c_kr_tag,output wire[CLIENTS*128-1:0]c_kr_beat,output wire[CLIENTS*8192-1:0]c_kr_data,
    output wire[CLIENTS*32-1:0]c_k_wr_done,
    output wire[31:0]k_v,input wire[31:0]k_rdy,output wire[31:0]k_we,
    output wire[959:0]k_addr,output wire[127:0]k_len,output wire[543:0]k_tag,
    output wire[8191:0]k_wdata,output wire[1023:0]k_wstrb,
    input wire[31:0]kr_v,output wire[31:0]kr_rdy,
    input wire[543:0]kr_tag,input wire[127:0]kr_beat,input wire[8191:0]kr_data,
    input wire[31:0]k_wr_done,output wire fault
);
    localparam integer CW=(CLIENTS<2)?1:$clog2(CLIENTS);
    wire[31:0]pc_fault;assign fault=|pc_fault;
    for(genvar p=0;p<32;p=p+1)begin:g_pc
        reg[CW-1:0]read_owner[0:63],write_owner[0:31];
        reg[5:0]read_wp,read_rp;reg[4:0]write_wp,write_rp;
        reg[6:0]read_count;reg[5:0]write_count;
        reg[CW-1:0]rr,held_client;reg held,sticky;
        reg selected;reg[CW-1:0]client;
        reg ov,owe;reg[29:0]oa;reg[3:0]ol;reg[16:0]ot;
        reg[255:0]od;reg[31:0]os;reg[CLIENTS-1:0]ready_clients;
        wire[CW-1:0]read_head=read_owner[read_rp];
        wire[CW-1:0]routed_head=read_head ^ CW'(MUT_READ_OWNER);
        wire[CW-1:0]write_head=write_owner[write_rp];
        wire read_pop=kr_v[p]&&kr_rdy[p];
        wire write_pop=k_wr_done[p]&&write_count!=0;
        wire accepted=k_v[p]&&k_rdy[p];
        wire read_push=accepted&&!owe,write_push=accepted&&owe;
        wire[3:0]read_add=MUT_BURST_COUNT?4'd1:ol;
        integer pick,idx;reg credit_ok;reg[3:0]length;
        always @*begin
            selected=0;client=held_client;ov=0;owe=0;oa=0;ol=0;ot=0;od=0;os=0;ready_clients=0;
            pick=0;idx=0;credit_ok=0;length=0;
            for(integer off=0;off<CLIENTS;off=off+1)begin
                pick=integer'(rr)+off;if(pick>=CLIENTS)pick=pick-CLIENTS;
                if(held)pick=integer'(held_client);
                idx=pick*32+p;length=c_k_len[idx*4+:4];
                credit_ok=c_k_we[idx] ? (length==1 && write_count<32+write_pop) :
                    (length>=1 && length<=4 && {1'b0,read_count}+{4'b0,length}<=8'd64+8'(read_pop));
                if(!selected && c_k_v[idx] && credit_ok && !sticky)begin
                    selected=1;client=CW'(pick);ov=1;owe=c_k_we[idx];oa=c_k_addr[idx*30+:30];ol=length;
                    ot=c_k_tag[idx*17+:17];od=c_k_wdata[idx*256+:256];os=c_k_wstrb[idx*32+:32];
                    ready_clients[pick]=k_rdy[p];
                end
            end
        end
        assign k_v[p]=ov;assign k_we[p]=owe;assign k_addr[p*30+:30]=oa;assign k_len[p*4+:4]=ol;
        assign k_tag[p*17+:17]=ot;assign k_wdata[p*256+:256]=od;assign k_wstrb[p*32+:32]=os;
        assign kr_rdy[p]=read_count!=0 && routed_head<CLIENTS && !sticky ? c_kr_rdy[integer'(routed_head)*32+p] : 1'b0;
        for(genvar c=0;c<CLIENTS;c=c+1)begin:g_client
            localparam integer N=c*32+p;
            assign c_k_rdy[N]=ready_clients[c];
            assign c_kr_v[N]=kr_v[p] && read_count!=0 && routed_head==c && !sticky;
            assign c_kr_tag[N*17+:17]=kr_tag[p*17+:17];assign c_kr_beat[N*4+:4]=kr_beat[p*4+:4];
            assign c_kr_data[N*256+:256]=kr_data[p*256+:256];
            assign c_k_wr_done[N]=MUT_EARLY_ACK ? accepted&&owe&&client==c : k_wr_done[p]&&write_count!=0&&write_head==c&&!sticky;
        end
        assign pc_fault[p]=sticky;
        always @(posedge pc_clk[p] or negedge rst_n)begin
            if(!rst_n)begin
                read_wp<=0;read_rp<=0;write_wp<=0;write_rp<=0;read_count<=0;write_count<=0;
                rr<=0;held<=0;held_client<=0;sticky<=0;
            end else begin
                if(ov&&!k_rdy[p])begin held<=1;held_client<=client;end
                if(held&&!c_k_v[integer'(held_client)*32+p])sticky<=1;
                if(accepted)begin held<=0;rr<=(client==CLIENTS-1)?0:client+1'b1;end
                if(read_push)begin
                    for(integer b=0;b<4;b=b+1)if(b<ol)read_owner[6'(read_wp+b)]<=client;
                    read_wp<=read_wp+6'(read_add);
                end
                if(write_push)begin write_owner[write_wp]<=client;write_wp<=write_wp+1'b1;end
                if(read_pop)read_rp<=read_rp+1'b1;
                if(write_pop)write_rp<=write_rp+1'b1;
                read_count<=read_count+(read_push?7'(read_add):7'd0)-(read_pop?7'd1:7'd0);
                write_count<=write_count+(write_push?6'd1:6'd0)-(write_pop?6'd1:6'd0);
                if((kr_v[p]&&read_count==0)||(k_wr_done[p]&&write_count==0)||read_count>64||write_count>32)sticky<=1;
                for(integer c=0;c<CLIENTS;c=c+1)begin
                    if(c_k_v[c*32+p] && (c_k_len[(c*32+p)*4+:4]==0 || c_k_len[(c*32+p)*4+:4]>4 ||
                       (c_k_we[c*32+p] && c_k_len[(c*32+p)*4+:4]!=1)))sticky<=1;
                end
            end
        end
    end
endmodule
