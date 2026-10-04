`timescale 1ns/1ps
// Canonical REAL_MEM service + four nearHBM row clients, all in this service
// clock domain. The enclosing system owns clock crossings and actual tile SRAM
// capture. No ready/visibility inputs are fabricated; KV fill/write/ACK semantics
// are exactly ot_qwen_rt_kv_fill_service, KV_IDEAL permanently zero when enabled.
// Requests route by canonical sector owner[10:9] (position[8:7]). Tagged ACKs
// return to the original service through protected owner/beat tracking.
module ot_qwen_nearhbm_realmem_service #(
    parameter integer ENABLE=0,G=6144,SW=64,AW=24,NW=18,NPC=32,R=8,DQ=32,
    parameter integer NRD=256,NWR=64,FILL_LAT=8,LKA=512,
    parameter integer IDW=$clog2(NRD>NWR?NRD:NWR), KTAGW=3+IDW,
    parameter integer RTAGW=12, MTAGW=RTAGW+1
)(
    input wire clk,rst_n,start,
    input wire [NW-1:0] pos,input wire [7:0] layer,
    input wire kvd_v,kvd_kindk,input wire [NW-1:0] kvd_pos,
    input wire [SW-1:0] kv_we,input wire [SW*AW-1:0] kv_waddr,input wire [SW*32-1:0] kv_wdata,
    output wire kv_ok,kv_write_drained,
    output wire [G/4-1:0] kvw_ce,
    output wire [G/4*7-1:0] kvw_addr,
    output wire [G/4*512-1:0] kvw_data,kvw_mask,
    input wire [4*R-1:0] row_valid,row_v,row_g,input wire [4*R*13-1:0] row_t,
    output wire [4*R-1:0] row_rsp_valid,output wire [4*R*1024-1:0] row_rsp_data,
    output wire [3:0] m_req_v,m_req_we,input wire [3:0] m_req_ready,
    output wire [4*24-1:0] m_req_addr,output wire [4*5-1:0] m_req_len,
    output wire [4*MTAGW-1:0] m_req_tag,output wire [4*256-1:0] m_req_wdata,
    input wire [4*NPC-1:0] m_pc_room,m_rsp_v,m_rsp_wr,
    output wire [4*NPC-1:0] m_rsp_ready,
    input wire [4*NPC*MTAGW-1:0] m_rsp_tag,
    input wire [4*NPC*4-1:0] m_rsp_beat,input wire [4*NPC*256-1:0] m_rsp_data,
    output wire fault,output wire [15:0] kv_fault_code,
    output wire row_drained,output wire [127:0] rows_retired,read_bursts,
    output wire [31:0] st_fill_cycles,st_fill_sectors,st_wr_sectors,st_rsp_stall,
    output wire [31:0] st_kvok_low_desc,st_drain_low,st_wr_lat_max
);
    import ot_gpu_w6_secded_pkg::*;
    generate if(ENABLE) begin:g_on
        wire kv_fault;
        wire k_v,k_ready,k_we;wire [23:0] k_addr;wire [4:0] k_len;
        wire [KTAGW-1:0] k_tag;wire [255:0] k_data;
        reg [NPC-1:0] k_rsp_v,k_rsp_wr;wire [NPC-1:0] k_rsp_ready;
        reg [NPC*KTAGW-1:0] k_rsp_tag;reg [NPC*4-1:0] k_rsp_beat;reg [NPC*256-1:0] k_rsp_data;
        wire [NPC-1:0] k_room=m_pc_room[0 +: NPC]&m_pc_room[NPC +: NPC]&m_pc_room[2*NPC +: NPC]&m_pc_room[3*NPC +: NPC];
        ot_qwen_rt_kv_fill_service #(.G(G),.SW(SW),.AW(AW),.NW(NW),.NPC(NPC),.NRD(NRD),.NWR(NWR),.LKA(LKA),.FILL_LAT(FILL_LAT),.KV_IDEAL(0)) kv(
            .clk(clk),.rst_n(rst_n),.start(start),.ideal_in(1'b0),.pos(pos),.layer(layer),
            .kvd_v(kvd_v),.kvd_pos(kvd_pos),.kvd_kindk(kvd_kindk),.kv_ok(kv_ok),
            .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.kv_write_drained(kv_write_drained),
            .kvw_ce(kvw_ce),.kvw_addr(kvw_addr),.kvw_data(kvw_data),.kvw_mask(kvw_mask),
            .h_req_v(k_v),.h_req_rdy(k_ready),.h_pc_room(k_room),.h_req_we(k_we),.h_req_addr(k_addr),.h_req_len(k_len),.h_req_tag(k_tag),.h_req_wdata(k_data),
            .h_rsp_v(k_rsp_v),.h_rsp_rdy(k_rsp_ready),.h_rsp_tag(k_rsp_tag),.h_rsp_beat(k_rsp_beat),.h_rsp_data(k_rsp_data),.h_rsp_wr(k_rsp_wr),
            .fault(kv_fault),.fault_code(kv_fault_code),.st_fill_cycles(st_fill_cycles),.st_fill_sectors(st_fill_sectors),.st_wr_sectors(st_wr_sectors),.st_rsp_stall(st_rsp_stall),
            .st_kvok_low_desc(st_kvok_low_desc),.st_drain_low(st_drain_low),.st_wr_lat_max(st_wr_lat_max));
        wire [3:0] r_v,r_ready,r_fault,r_empty;wire [95:0] r_addr;wire [19:0] r_len;wire [4*RTAGW-1:0] r_tag;
        wire [4*NPC-1:0] r_rsp_ready;
        reg arb_fault;
        reg bad_return;reg [65:0] comb_owner;
        integer comb_id,comb_beat,comb_len;reg [KTAGW-1:0] comb_tag;
        reg [71:0] locks,rotation;
        // Outstanding REAL_MEM request owner records, indexed by {write,id}.
        reg [71:0] owner[0:2*(1<<IDW)-1];
        wire [65:0] lk=decode64(locks),rot=decode64(rotation);
        reg [3:0] sel_k,sel_r,req_valid;
        reg [4*NPC-1:0] rsp_ready;
        reg [4*MTAGW-1:0] req_tag;
        reg [95:0] req_addr;reg [19:0] req_len;reg [3:0] req_we;reg [1023:0] req_data;
        integer pick[0:NPC-1];
        integer s,p,x,off,kind;
        reg [MTAGW-1:0] mt;
        always @* begin
            sel_k=0;sel_r=0;req_valid=0;req_we=0;req_addr=0;req_len=0;req_tag=0;req_data=0;
            for(integer j=0;j<4;j=j+1) begin
                if(lk[j]) begin if(lk[4+j])sel_k[j]=k_v;else sel_r[j]=r_v[j];end
                else if(k_v && k_addr[10:9]==j)sel_k[j]=1;
                else sel_r[j]=r_v[j];
                req_valid[j]=(sel_k[j]||sel_r[j]) && !arb_fault && !lk[65];
                if(sel_k[j])begin req_we[j]=k_we;req_addr[j*24 +: 24]=k_addr;req_len[j*5 +: 5]=k_len;req_tag[j*MTAGW +: MTAGW]={{(MTAGW-KTAGW){1'b0}},k_tag};req_data[j*256 +: 256]=k_data;end
                else begin req_addr[j*24 +: 24]=r_addr[j*24 +: 24];req_len[j*5 +: 5]=r_len[j*5 +: 5];req_tag[j*MTAGW +: MTAGW]={1'b1,r_tag[j*RTAGW +: RTAGW]};end
            end
            k_rsp_v=0;k_rsp_wr=0;k_rsp_tag=0;k_rsp_beat=0;k_rsp_data=0;rsp_ready=0;bad_return=0;comb_owner=0;comb_id=0;comb_beat=0;comb_len=0;comb_tag=0;
            for(integer q=0;q<NPC;q=q+1)begin
                pick[q]=-1;
                for(integer k=3;k>=0;k=k-1)begin
                    off=(rot[2*q +: 2]+k)%4;x=off*NPC+q;
                    if(m_rsp_v[x] && !m_rsp_tag[x*MTAGW+MTAGW-1])pick[q]=off;
                end
                if(pick[q]>=0)begin
                    x=pick[q]*NPC+q;
                    comb_tag=m_rsp_tag[x*MTAGW +: KTAGW];
                    comb_id=(comb_tag[KTAGW-1]?(1<<IDW):0)+comb_tag[IDW-1:0];
                    comb_owner=decode64(owner[comb_id]);comb_beat=m_rsp_beat[x*4 +: 4];comb_len=comb_owner[KTAGW+2 +: 5];
                    if(comb_owner[65] || !comb_owner[34] || comb_owner[KTAGW-1:0]!=comb_tag ||
                       comb_owner[KTAGW +: 2]!=pick[q] || comb_beat>=comb_len || comb_owner[KTAGW+7+comb_beat] ||
                       m_rsp_wr[x]!=comb_tag[KTAGW-1] || m_rsp_tag[x*MTAGW+KTAGW +: MTAGW-KTAGW]!=0)bad_return=1;
                    else k_rsp_v[q]=m_rsp_v[x];
                    k_rsp_wr[q]=m_rsp_wr[x];
                    k_rsp_tag[q*KTAGW +: KTAGW]=m_rsp_tag[x*MTAGW +: KTAGW];
                    k_rsp_beat[q*4 +: 4]=m_rsp_beat[x*4 +: 4];k_rsp_data[q*256 +: 256]=m_rsp_data[x*256 +: 256];
                    rsp_ready[x]=k_rsp_ready[q] && k_rsp_v[q] && !arb_fault;
                end
            end
            for(integer j=0;j<4*NPC;j=j+1)
                if(m_rsp_tag[j*MTAGW+MTAGW-1])rsp_ready[j]=r_rsp_ready[j];
        end
        assign m_req_v=req_valid;assign m_req_we=req_we;assign m_req_addr=req_addr;assign m_req_len=req_len;assign m_req_tag=req_tag;assign m_req_wdata=req_data;
        assign m_rsp_ready=rsp_ready & {4*NPC{!fault}};
        assign k_ready=|(sel_k&m_req_ready&req_valid);
        assign r_ready=sel_r&m_req_ready&req_valid;
        assign row_drained=&r_empty;
        assign fault=kv_fault|(|r_fault)|arb_fault;
        genvar st,pc;
        for(st=0;st<4;st=st+1)begin:g_stack
            wire [NPC-1:0] rv;
            for(pc=0;pc<NPC;pc=pc+1)begin:g_pc
                assign rv[pc]=m_rsp_v[st*NPC+pc] && m_rsp_tag[(st*NPC+pc)*MTAGW+MTAGW-1];
            end
            wire [NPC*RTAGW-1:0] rt;
            for(pc=0;pc<NPC;pc=pc+1)begin:g_tag
                assign rt[pc*RTAGW +: RTAGW]=m_rsp_tag[(st*NPC+pc)*MTAGW +: RTAGW];
            end
            ot_qwen_nearhbm_row_sectors #(.ENABLE(1),.S(st),.R(R),.DQ(DQ),.NPC(NPC),.TAGW(RTAGW)) rows(
                .clk(clk),.rst_n(rst_n),.start(start),.pos(pos),.layer(layer),.memory_ready(kv_ok&&kv_write_drained&&!kv_fault&&!arb_fault),
                .row_valid(row_valid[st*R +: R]),.row_v(row_v[st*R +: R]),.row_g(row_g[st*R +: R]),.row_t(row_t[st*R*13 +: R*13]),
                .row_rsp_valid(row_rsp_valid[st*R +: R]),.row_rsp_data(row_rsp_data[st*R*1024 +: R*1024]),
                .req_v(r_v[st]),.req_ready(r_ready[st]),.pc_room(m_pc_room[st*NPC +: NPC]),.req_addr(r_addr[st*24 +: 24]),.req_len(r_len[st*5 +: 5]),.req_tag(r_tag[st*RTAGW +: RTAGW]),
                .rsp_v(rv),.rsp_wr(m_rsp_wr[st*NPC +: NPC]),.rsp_ready(r_rsp_ready[st*NPC +: NPC]),.rsp_tag(rt),.rsp_beat(m_rsp_beat[st*NPC*4 +: NPC*4]),.rsp_data(m_rsp_data[st*NPC*256 +: NPC*256]),
                .fault(r_fault[st]),.fault_code(),.drained(r_empty[st]),.rows_retired(rows_retired[st*32 +: 32]),.read_bursts(read_bursts[st*32 +: 32]));
        end
        reg [63:0] ll,rr,oo;
        reg [65:0] od;
        reg [KTAGW-1:0] kt;
        integer oi,bt,ln,prior;
        reg [15:0] seen,need;
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin
                arb_fault<=0;locks<=encode64(0);rotation<=encode64(0);
                for(oi=0;oi<2*(1<<IDW);oi=oi+1)owner[oi]<=encode64(0);
            end else if(!arb_fault)begin
                ll=lk[63:0];rr=rot[63:0];
                if(lk[65]||rot[65]||bad_return)arb_fault<=1;
                for(s=0;s<4;s=s+1)begin
                    if(lk[s] && !(sel_k[s]||sel_r[s]))arb_fault<=1;
                    if(req_valid[s])begin
                        ll[s]=!m_req_ready[s];ll[4+s]=sel_k[s];
                        if(req_addr[s*24+9 +: 2]!=s)arb_fault<=1;
                        if(sel_k[s] && m_req_ready[s])begin
                            oi=(k_tag[KTAGW-1]?(1<<IDW):0)+k_tag[IDW-1:0];od=decode64(owner[oi]);
                            if(od[65]||od[34])arb_fault<=1;
                            oo=0;oo[KTAGW-1:0]=k_tag;oo[KTAGW +: 2]=2'(s);oo[KTAGW+2 +: 5]=k_len;oo[34]=1;
                            owner[oi]<=encode64(oo);
                        end
                    end else ll[s]=0;
                end
                for(p=0;p<NPC;p=p+1)if(pick[p]>=0 && k_rsp_v[p] && k_rsp_ready[p])begin
                    kt=k_rsp_tag[p*KTAGW +: KTAGW];oi=(kt[KTAGW-1]?(1<<IDW):0)+kt[IDW-1:0];
                    // Keep the offered response/ready stable through the sampling edge.
                    // State commits after all receivers have sampled their handshake.
                    // Earlier PC beats are folded into this descriptor locally, so
                    // the last NBA write retains every simultaneous accepted beat.
                    od=decode64(owner[oi]);oo=od[63:0];bt=k_rsp_beat[p*4 +: 4];ln=oo[KTAGW+2 +: 5];
                    seen=oo[KTAGW+7 +: 16];need=(17'd1<<ln)-1;
                    for(prior=0;prior<p;prior=prior+1)
                        if(pick[prior]>=0 && k_rsp_v[prior] && k_rsp_ready[prior] &&
                           k_rsp_tag[prior*KTAGW +: KTAGW]==kt)
                            seen[k_rsp_beat[prior*4 +: 4]]=1;
                    if(od[65]||!oo[34]||oo[KTAGW-1:0]!=kt||oo[KTAGW +: 2]!=pick[p]||bt>=ln||seen[bt]||
                        k_rsp_wr[p]!=kt[KTAGW-1])arb_fault<=1;
                    else begin seen[bt]=1;oo[KTAGW+7 +: 16]=seen;if(seen==need)oo[34]=0;owner[oi]<=encode64(oo);end
                    rr[2*p +: 2]=2'((pick[p]+1)%4);
                end
                locks<=encode64(ll);rotation<=encode64(rr);
            end
        end
    end else begin:g_off
        assign kv_ok=0;assign kv_write_drained=0;assign kvw_ce=0;assign kvw_addr=0;assign kvw_data=0;assign kvw_mask=0;
        assign row_rsp_valid=0;assign row_rsp_data=0;assign m_req_v=0;assign m_req_we=0;assign m_req_addr=0;assign m_req_len=0;assign m_req_tag=0;assign m_req_wdata=0;assign m_rsp_ready=0;
        assign fault=0;assign kv_fault_code=0;assign row_drained=0;assign rows_retired=0;assign read_bursts=0;
        assign st_fill_cycles=0;assign st_fill_sectors=0;assign st_wr_sectors=0;assign st_rsp_stall=0;assign st_kvok_low_desc=0;assign st_drain_low=0;assign st_wr_lat_max=0;
    end endgenerate
endmodule
