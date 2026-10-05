`timescale 1ns/1ps
// Additive, default-off canonical REAL_MEM row client. No arithmetic/reordering.
// K coalesces 16 positions/64 sectors. V coalesces four positions/16 sectors.
// Input credit is the existing engine DQ; every accepted row has a finite queue
// entry and retires in that engine's request order. HBM returns are tagged and
// may reorder across PCs. Cache and mutable queue/control state use SECDED72.
module ot_qwen_nearhbm_row_sectors #(
    parameter integer ENABLE=0, S=0, R=8, DQ=32, NPC=32,
    parameter integer KS=32, VS=R*16, NS=KS+VS,
    parameter integer SIW=$clog2(NS), TAGW=2+SIW+2,
    parameter integer QW=$clog2(DQ), CW=$clog2(DQ+1)
)(
    input wire clk, rst_n, start,
    input wire [17:0] pos,
    input wire [7:0] layer,
    input wire memory_ready,
    input wire [R-1:0] row_valid, row_v, row_g,
    input wire [R*13-1:0] row_t,
    output reg [R-1:0] row_rsp_valid,
    output reg [R*1024-1:0] row_rsp_data,
    output wire req_v,
    input wire req_ready,
    input wire [NPC-1:0] pc_room,
    output wire [23:0] req_addr,
    output wire [4:0] req_len,
    output wire [TAGW-1:0] req_tag,
    input wire [NPC-1:0] rsp_v, rsp_wr,
    output wire [NPC-1:0] rsp_ready,
    input wire [NPC*TAGW-1:0] rsp_tag,
    input wire [NPC*4-1:0] rsp_beat,
    input wire [NPC*256-1:0] rsp_data,
    output reg fault,
    output reg [15:0] fault_code,
    output wire drained,
    output reg [31:0] rows_retired, read_bursts
);
    import ot_gpu_w6_secded_pkg::*;
    // Metadata raw64: key[14:0], valid15, refs[24:16], issued[28:25], gen[30:29].
    reg [71:0] meta[0:NS-1], received[0:NS-1];
    reg [287:0] landing[0:KS*64+VS*16-1];
    // Queue raw64: t[12:0], g13, v14, cache slot starting at15.
    reg [71:0] queue[0:R*DQ-1], qctl[0:R-1], vctl[0:R-1];
    // Context: P[17:0], layer[25:18], generation[27:26], active28.
    reg [71:0] context_code, request_code;
    wire [65:0] cx=decode64(context_code), rq=decode64(request_code);
    assign req_v=ENABLE && rq[0] && !fault;
    assign req_addr=rq[24:1]; assign req_len=5'd16;
    assign req_tag=rq[24+TAGW:25];
    assign rsp_ready={NPC{ENABLE && !fault}};
    reg empty_all;
    integer z;
    reg [65:0] empty_ctl;
    always @* begin
        empty_all=!rq[0];
        for(integer e=0;e<R;e=e+1) begin
            empty_ctl=decode64(qctl[e]);
            if(empty_ctl[2*QW +: CW]!=0 || empty_ctl[65]) empty_all=0;
        end
    end
    assign drained=ENABLE && empty_all && !fault;
    function automatic integer loc(input integer slot,input integer sector);
        loc=(slot<KS)?slot*64+sector:KS*64+(slot-KS)*16+sector;
    endfunction
    function automatic [287:0] enc256(input [255:0] d);
        enc256={encode64(d[255:192]),encode64(d[191:128]),encode64(d[127:64]),encode64(d[63:0])};
    endfunction
    function automatic integer pc(input [23:0] a);
        pc=((a>>2)^(a>>(2+$clog2(NPC)))^(a>>(2+2*$clog2(NPC))))&(NPC-1);
    endfunction
    reg [63:0] m[0:NS-1], bm[0:NS-1];
    reg [63:0] cc, qq, vv, payload;
    reg [65:0] dec, md, rd;
    reg [14:0] key;
    reg [TAGW-1:0] tg;
    reg [23:0] addr;
    integer e,p,c,b,t,sl,sec,word,dim,head,qread,qwrite,nq,sub,pick,rr,base,idx,nret;
    reg ok, done_cache, req_free;
    reg [1:0] generation;
    reg [71:0] sched_ctl; // round-robin scan cursor is protected too
    initial begin
        if(R!=8 || DQ!=32 || KS!=32 || VS!=R*16)
            $fatal(1,"Only sized full HD128/R8/DQ32 geometry is qualified");
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            context_code<=encode64(0); request_code<=encode64(0); sched_ctl<=encode64(0);
            fault<=0; fault_code<=0; row_rsp_valid<=0; rows_retired<=0; read_bursts<=0;
            for(c=0;c<NS;c=c+1) begin meta[c]<=encode64(0); received[c]<=encode64(0); end
            for(e=0;e<R;e=e+1) begin qctl[e]<=encode64(0);vctl[e]<=encode64(0); end
        end else if(ENABLE && !fault) begin
            row_rsp_valid<=0;
            cc=cx[63:0]; payload=rq[63:0];nret=0;
            dec=decode64(sched_ctl);rr=dec[SIW-1:0];
            if(cx[65] || rq[65] || dec[65]) begin fault<=1;fault_code[0]<=1;end
            for(c=0;c<NS;c=c+1) begin
                md=decode64(meta[c]); rd=decode64(received[c]);m[c]=md[63:0];bm[c]=rd[63:0];
                if(md[65] || rd[65]) begin fault<=1;fault_code[0]<=1;end
            end
            if(start) begin
                if(!empty_all || pos>=8192) begin fault<=1;fault_code[1]<=1;end
                else begin
                    generation=cc[27:26]+2'd1;cc=0;cc[17:0]=pos;cc[25:18]=layer;cc[27:26]=generation;cc[28]=1;
                    for(c=0;c<NS;c=c+1) begin m[c]=0;bm[c]=0;end
                    for(e=0;e<R;e=e+1) begin qctl[e]<=encode64(0);vctl[e]<=encode64(0);end
                end
            end else begin
                // Land all simultaneously returned PC beats. A duplicate sector faults.
                for(p=0;p<NPC;p=p+1) if(rsp_v[p]) begin
                    tg=rsp_tag[p*TAGW +: TAGW];sl=tg[2 +: SIW];sub=tg[1:0];b=rsp_beat[p*4 +: 4];sec=sub*16+b;
                    if(sl>=NS) begin fault<=1;fault_code[2]<=1;end
                    else if(rsp_wr[p] || tg[TAGW-1 -: 2]!=cc[27:26] || !m[sl][15] ||
                            m[sl][30:29]!=cc[27:26] || !m[sl][25+sub] ||
                            (sl>=KS && sub!=0) || bm[sl][sec]) begin fault<=1;fault_code[2]<=1;end
                    else begin
                        landing[loc(sl,sec)]=enc256(rsp_data[p*256 +: 256]);bm[sl][sec]=1;
                    end
                end
                for(e=0;e<R;e=e+1) begin
                    dec=decode64(qctl[e]);qq=dec[63:0];
                    if(dec[65]) begin fault<=1;fault_code[0]<=1;end
                    qread=qq[QW-1:0];qwrite=qq[QW +: QW];nq=qq[2*QW +: CW];
                    dec=decode64(vctl[e]);vv=dec[63:0];
                    if(dec[65]) begin fault<=1;fault_code[0]<=1;end
                    // Deliver only the oldest row of each engine, after all tile sectors land.
                    if(nq!=0 && memory_ready) begin
                        dec=decode64(queue[e*DQ+qread]);sl=dec[15 +: SIW];t=dec[12:0];head=dec[13];
                        if(dec[65] || sl>=NS) begin fault<=1;fault_code[0]<=1;end
                        else begin
                            key={dec[14],dec[13],dec[14]?(dec[12:0]&13'h1ffc):(dec[12:0]&13'h1ff0)};
                            done_cache=(sl<KS)?(&bm[sl]):(&bm[sl][15:0]);
                            if(!m[sl][15] || m[sl][14:0]!=key || m[sl][24:16]==0) begin fault<=1;fault_code[3]<=1;end
                            else if(done_cache) begin
                                for(dim=0;dim<128;dim=dim+1) begin
                                    sec=(sl<KS)?dim/2:(t&3)*4+dim/32;
                                    word=(sl<KS)?((dim&1)*16+(t&15))/8:(dim%32)/8;
                                    dec=decode64(landing[loc(sl,sec)][word*72 +: 72]);
                                    if(dec[65]) begin fault<=1;fault_code[0]<=1;end
                                    row_rsp_data[(e*128+dim)*8 +: 8]<=dec[8*((sl<KS)?(t&7):(dim&7)) +: 8];
                                end
                                row_rsp_valid[e]<=1;m[sl][24:16]=m[sl][24:16]-1;
                                qread=(qread+1)%DQ;nq=nq-1;nret=nret+1;
                            end
                        end
                    end
                    if(row_valid[e]) begin
                        t=row_t[e*13 +: 13];key={row_v[e],row_g[e],row_v[e]?(13'(t)&13'h1ffc):(13'(t)&13'h1ff0)};
                        ok=cc[28] && t<=cc[17:0] && ((t>>7)&3)==S && nq<DQ;
                        if(!row_v[e]) sl=(row_g[e]?16:0)+(((t>>9)*8+((t&127)>>4))&15);
                        else if(vv[15] && vv[14:0]==key) sl=vv[16 +: SIW];
                        else begin
                            sl=KS+e*16+vv[16+SIW +: 4];vv[16+SIW +: 4]=vv[16+SIW +: 4]+1'b1;
                            vv[15]=1;vv[14:0]=key;vv[16 +: SIW]=SIW'(sl);
                        end
                        if(!ok) begin fault<=1;fault_code[4]<=1;end
                        else if(m[sl][15] && m[sl][14:0]!=key && (m[sl][24:16]!=0 ||
                                (m[sl][28:25]!=0 && !((sl<KS)?(&bm[sl]):(&bm[sl][15:0]))))) begin fault<=1;fault_code[5]<=1;end
                        else begin
                            if(!m[sl][15] || m[sl][14:0]!=key) begin
                                m[sl]=0;bm[sl]=0;m[sl][15]=1;m[sl][14:0]=key;m[sl][30:29]=cc[27:26];
                            end
                            m[sl][24:16]=m[sl][24:16]+1;
                            queue[e*DQ+qwrite]<=encode64({{(49-SIW){1'b0}},SIW'(sl),row_v[e],row_g[e],13'(t)});
                            qwrite=(qwrite+1)%DQ;nq=nq+1;
                        end
                    end
                    qq=0;qq[QW-1:0]=QW'(qread);qq[QW +: QW]=QW'(qwrite);qq[2*QW +: CW]=CW'(nq);
                    qctl[e]<=encode64(qq);vctl[e]<=encode64(vv);
                end
                req_free=!payload[0] || req_ready;
                if(req_free) payload=0;
                // One held, tagged descriptor; target PC room is only advisory, ready is authoritative.
                pick=-1;sub=0;
                if(req_free && memory_ready && cc[28]) begin
                    for(c=NS-1;c>=0;c=c-1) begin
                        idx=(rr+c)%NS;
                        if(m[idx][15] && m[idx][24:16]!=0) begin
                            for(b=3;b>=0;b=b-1) if((idx<KS || b==0) && !m[idx][25+b]) begin
                                addr=(24'(cc[25:18])<<17)+(m[idx][13]?24'd32768:0)+
                                     (m[idx][14]?(24'd65536+24'(m[idx][12:0])*4):24'(m[idx][12:4])*64)+b*16;
                                ok=1;for(p=0;p<4;p=p+1) if(!pc_room[pc(addr+p*4)])ok=0;
                                if(ok) begin pick=idx;sub=b;end
                            end
                        end
                    end
                    if(pick>=0) begin
                        addr=(24'(cc[25:18])<<17)+(m[pick][13]?24'd32768:0)+
                             (m[pick][14]?(24'd65536+24'(m[pick][12:0])*4):24'(m[pick][12:4])*64)+sub*16;
                        tg={cc[27:26],SIW'(pick),2'(sub)};
                        payload[0]=1;payload[24:1]=addr;payload[24+TAGW:25]=tg;
                        m[pick][25+sub]=1;rr=(pick+1)%NS;read_bursts<=read_bursts+1;
                    end
                end
            end
            rows_retired<=rows_retired+nret;
            context_code<=encode64(cc);request_code<=encode64(payload);sched_ctl<=encode64(64'(rr));
            for(c=0;c<NS;c=c+1) begin meta[c]<=encode64(m[c]);received[c]<=encode64(bm[c]);end
        end else row_rsp_valid<=0;
    end
endmodule
