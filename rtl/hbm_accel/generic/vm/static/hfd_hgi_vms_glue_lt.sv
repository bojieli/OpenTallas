`timescale 1ns/1ps
`default_nettype none
// HBM-KITS-C/VMGLUE 2026-10-18: physical successors of the VM hub-glue logic for the hardened glue tiles
// (hfd_hgi_vms_glue_{sw,e,nw}_t, gen_vms_glue_tiles.py).  Port-for-port and edge-for-edge the same behaviour as
//   ot_vms_rstop_static  -> ot_vms_rstop_lt   only valid / control state is reset; payload registers are plain flops
//   ot_vms_rcl_static    -> ot_vms_rcl_lt     (same)
//   ot_vms_hub_static    -> ot_vms_hub_lt     the bank / ring response demultiplex is a parallel tag decode + AND-OR
//                                             tree and a 10-input population count (the historical loop built a
//                                             10-deep chain of slot muxes: 24-35 levels reg->reg)
//   ot_vms_slice_static_glue -> hfd_vms_glue_core_lt   the same wiring, one tile clock, one regional reset per child
// The historical modules stay untouched (other compositions and the bench reference use them).
// Reset-light equivalence: every payload register without a reset is either overwritten on every edge from reset-held
// logic (flit / xq / rce / cco / hq / ri ... are zero while the valid and enable state is held in reset) or read only
// under a reset valid bit; after >= 5 edges of reset the port behaviour equals the fully reset original
// (tools/hbm_die_v16/vms_glue_tile_equiv.py checks it in lockstep with periodic resets).
module ot_vms_rstop_lt #(
    parameter integer PHYSICAL_RING=1,
    parameter integer COMMIT_DELAY=5,
    parameter integer MUT=0
) (
    input wire clk, rst_n,
    input wire [1:0] sid,
    input wire dir,
    input wire tx_enable,
    input wire [2:0] tx_source,
    input wire [2223:0] l_in,
    output reg [2223:0] l_out,
    input wire [289:0] pi,
    input wire [8*276-1:0] eg,
    output reg [8*276-1:0] xq,
    input wire [7:0] xq_done,
    output reg [287:0] rce,
    input wire [265:0] ri,
    output reg [2:0] wko,
    input wire [2:0] wki,
    output reg [263:0] cco,
    output reg ack_o,
    input wire ack_i,
    output reg mirror_busy,
    output reg fault
);
    // payload (plain flops) + valid bits (reset)
    reg [2222:0] in_d;  reg in_v;
    reg [288:0] pi_d;   reg pi_v;
    reg [2207:0] eg_d;  reg [7:0] eg_v;
    reg [264:0] ri_d;   reg ri_v;
    wire [2223:0] in_q={in_v,in_d};
    wire [289:0] pi_q={pi_v,pi_d};
    wire [265:0] ri_q={ri_v,ri_d};
    reg [2207:0] eg_q;
    always @* for(integer b=0;b<8;b=b+1) eg_q[b*276+:276]={eg_v[b],eg_d[b*276+:275]};
    reg [2:0] wki_q, source_q;
    reg enable_q;
    reg [1:0] me;
    reg dr;
    reg ack_q;
    reg [COMMIT_DELAY-1:0] commit_v;
    reg [7:0] commit_mask [0:COMMIT_DELAY-1];
    reg [1:0] commit_src [0:COMMIT_DELAY-1];
    reg [15:0] outstanding;
    wire [1:0] kind=in_q[2222:2221];
    wire own=in_q[2223] && in_q[2217+int'(me)];
    wire [3:0] rest=in_q[2220:2217] & ~(4'b1 << me);
    wire transit=in_q[2223] && (|rest);
    reg [7:0] lanes, ev;
    reg [2:0] bank;
    reg [274:0] lane;
    reg [2223:0] flit;
    reg [3:0] dest;
    wire [1:0] rank={me[1],me[1]^me[0]};
    wire [1:0] r1=rank+2'd1, r2=rank+2'd2, r3=rank+2'd3;
    wire [1:0] d1=(PHYSICAL_RING!=0) ? {r1[1],r1[1]^r1[0]} : me+2'd1;
    wire [1:0] d2=(PHYSICAL_RING!=0) ? {r2[1],r2[1]^r2[0]} : me+2'd2;
    wire [1:0] d3=(PHYSICAL_RING!=0) ? {r3[1],r3[1]^r3[0]} : me+2'd3;
    always @* begin
        lanes='0; ev='0; bank='0; lane='0;
        for(integer b=0;b<8;b=b+1) begin
            lanes[b]=in_q[b*276+275]; ev[b]=eg_q[b*276+275];
            if(lanes[b]) begin bank=3'(b); lane=lane | in_q[b*276+:275]; end
        end
        dest=dr ? (4'b1 << d3) : ((4'b1 << d1)|(4'b1 << d2));
        flit='0;
        if(enable_q) case(source_q)
            0: begin flit=in_q; flit[2223]=transit; flit[2220:2217]=rest; end
            1: begin
                flit[2223]=pi_q[289]; flit[2222:2221]=0;
                flit[2220:2217]=pi_q[288:285]; flit[2216:2215]=me;
                flit[2214:2211]=pi_q[284:281]; flit[2210:2209]=pi_q[280:279]; flit[2208]=pi_q[278];
                for(integer b=0;b<8;b=b+1) if(pi_q[277:275]==3'(b))
                    flit[b*276+:276]={1'b1,pi_q[274:264],pi_q[255:0],pi_q[263:256]};
            end
            2: begin flit[2223]=|ev; flit[2222:2221]=1; flit[2220:2217]=dest;
                flit[2216:2215]=me; flit[2207:0]=eg_q; end
            3: begin flit[2223]=ri_q[265]; flit[2222:2221]=2;
                flit[2220:2217]=4'b1<<ri_q[264:263]; flit[2216:2215]=me;
                flit[2214:2211]=ri_q[262:259]; flit[2210:2209]=ri_q[258:257];
                flit[2208]=ri_q[256]; flit[263:8]=ri_q[255:0]; end
            4: begin flit[2223]=wki_q[2]; flit[2222:2221]=3;
                flit[2220:2217]=4'b1<<wki_q[1:0]; flit[2216:2215]=me; end
            default: flit='0;
        endcase
        if(MUT==1 && flit[2223] && flit[2222:2221]==1) flit[8]=~flit[8];
    end
    // payload: no reset (zero while the valid / enable state below is held in reset)
    always @(posedge clk) begin
        in_d<=l_in[2222:0]; pi_d<=pi[288:0]; ri_d<=ri[264:0];
        for(integer b=0;b<8;b=b+1) eg_d[b*276+:275]<=eg[b*276+:275];
        l_out<=flit;
        xq<='0; rce<='0; cco<='0;
        if(own) case(kind)
            0: rce<={1'b1,in_q[2216:2215],in_q[2214:2211],in_q[2210:2209],in_q[2208],bank,lane[274:264],lane[7:0],lane[263:8]};
            1: xq<=in_q[2207:0];
            2: cco<={1'b1,in_q[2214:2211],in_q[2210:2209],in_q[2208],in_q[263:8]};
            default: ;
        endcase
        commit_mask[0]<=lanes; commit_src[0]<=in_q[2216:2215];
        for(integer t=1;t<COMMIT_DELAY;t=t+1) begin commit_mask[t]<=commit_mask[t-1]; commit_src[t]<=commit_src[t-1]; end
    end
    // valid / control state: regional reset
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            in_v<=0;pi_v<=0;eg_v<='0;ri_v<=0;wki_q<='0;
            source_q<=0;enable_q<=0;me<=0;dr<=0;ack_q<=0;
            ack_o<=0;wko<='0;commit_v<='0;outstanding<=0;mirror_busy<=0;fault<=0;
        end else begin
            in_v<=l_in[2223];pi_v<=pi[289];ri_v<=ri[265];wki_q<=wki;
            for(integer b=0;b<8;b=b+1) eg_v[b]<=eg[b*276+275];
            source_q<=tx_source;enable_q<=tx_enable;me<=sid;dr<=dir;ack_q<=ack_i;
            ack_o<=own && kind==3;
            if(own && kind==0 && $countones(lanes)!=1) fault<=1;
            if((transit && (!enable_q || source_q!=0)) ||
               (pi_q[289] && (!enable_q || source_q!=1)) ||
               ((|ev) && (!enable_q || source_q!=2)) ||
               (ri_q[265] && (!enable_q || source_q!=3)) ||
               (wki_q[2] && (!enable_q || source_q!=4)) ||
               (enable_q && source_q>4) ||
               (in_q[2223] && in_q[2220:2217]==0)) fault<=1;
            commit_v[0]<=own && kind==1;
            for(integer t=1;t<COMMIT_DELAY;t=t+1) commit_v[t]<=commit_v[t-1];
            wko<=0;
            if(commit_v[COMMIT_DELAY-1]) begin
                if((xq_done & commit_mask[COMMIT_DELAY-1]) != commit_mask[COMMIT_DELAY-1]) fault<=1;
                else wko<={1'b1,commit_src[COMMIT_DELAY-1]};
            end
            outstanding<=outstanding + ((flit[2223] && source_q==2)?(dr?16'd1:16'd2):16'd0) - (ack_q?16'd1:16'd0);
            mirror_busy<=outstanding!=0;
            if(ack_q && outstanding==0) fault<=1;
        end
    end
endmodule

module ot_vms_rcl_lt #(parameter integer MUT=0) (
    input wire clk,rst_n,
    input wire [1:0] sid,
    input wire rx_enable,rx_source,
    input wire [287:0] rce0,rce1,
    output wire [337:0] hq,
    input wire [273:0] hr,
    output wire [265:0] ri0,ri1,
    output reg fault
);
    reg [286:0] a_d,b_d; reg a_v,b_v;
    reg [272:0] r_d; reg r_v;
    wire [287:0] a={a_v,a_d}, b={b_v,b_d};
    wire [273:0] response={r_v,r_d};
    reg [1:0] me;
    reg select_q,enable_q;
    reg [336:0] hq_d; reg hq_v;
    reg [264:0] ri0_d,ri1_d; reg ri0_v,ri1_v;
    assign hq={hq_v,hq_d}; assign ri0={ri0_v,ri0_d}; assign ri1={ri1_v,ri1_d};
    wire [287:0] e=select_q?b:a;
    wire [14:0] sec={e[274]?2'b00:me,e[273:264],e[277:275]};
    wire [31:0] addr={11'b0,e[274],sec,5'b0};
    wire [15:0] tag={6'b0,~select_q,e[286:285],e[284:281],e[280:279],e[278]};
    wire return_port=response[266] ^ (MUT==1);
    reg [31:0] mask;
    always @* for(integer k=0;k<8;k=k+1) mask[k*4+:4]={4{e[256+k]}};
    wire [264:0] rpay={response[265:264],response[263:260],response[259:258],response[256],response[255:0]};
    always @(posedge clk) begin
        a_d<=rce0[286:0]; b_d<=rce1[286:0]; r_d<=hr[272:0];
        hq_d<={e[278],addr,e[255:0],mask,tag};
        ri0_d<=rpay; ri1_d<=rpay;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin
            a_v<=0;b_v<=0;r_v<=0;me<=0;select_q<=0;enable_q<=0;
            hq_v<=0;ri0_v<=0;ri1_v<=0;fault<=0;
        end else begin
            a_v<=rce0[287];b_v<=rce1[287];r_v<=hr[273];me<=sid;
            select_q<=rx_source;enable_q<=rx_enable;
            hq_v<=enable_q && e[287];
            ri0_v<=response[273] && !return_port;
            ri1_v<=response[273] && return_port;
            if((a[287] && (!enable_q || select_q)) ||
               (b[287] && (!enable_q || !select_q))) fault<=1;
            if(response[273] && response[272:267]!=0) fault<=1;
        end
endmodule

// ot_vms_hub_static with the response demultiplex as parallel logic (same function, same edges, same reset set).
module ot_vms_hub_lt #(
    parameter integer NC=4,
    parameter integer PHYSICAL_RING=1,
    parameter integer CW=(NC<1)?1:$clog2(NC+1)
)(
    input wire clk, rst_n,
    input wire [1:0] sid,
    input wire [(NC+1)*338-1:0] cq,
    input wire [(NC+1)*2-1:0] client_seq,
    input wire [7:0] bank_enable,
    input wire [8*CW-1:0] bank_client,
    input wire cw_enable,
    input wire [CW-1:0] cw_client,
    input wire ccw_enable,
    input wire [CW-1:0] ccw_client,
    output wire [(NC+1)*274-1:0] cr,
    output wire [8*285-1:0] pq,
    input wire [8*266-1:0] pr,
    output wire [289:0] cwi, cci,
    input wire [263:0] cco0, cco1,
    input wire [NC:0] response_enable,
    input wire [(NC+1)*2-1:0] response_seq,
    output reg [2:0] status
);
    localparam integer N=NC+1;
    localparam integer NS=10;          // response sources: 8 banks + CW / CCW ring returns
    reg [N*338-1:0] qr;
    reg [N*2-1:0] sq;
    reg [7:0] be;
    reg [8*CW-1:0] bc;
    reg ce, cce;
    reg [CW-1:0] cs, ccs;
    reg [1:0] me;
    reg [8*266-1:0] br;
    reg [263:0] rr0,rr1;
    reg [N-1:0] re;
    reg [N*2-1:0] rseq;
    reg [255:0] response_data[0:N-1][0:3];
    reg [15:0] tags[0:N-1][0:3];
    reg active[0:N-1][0:3], writes[0:N-1][0:3];
    reg [2:0] expected[0:N-1][0:3], seen[0:N-1][0:3];
    reg [N*274-1:0] cr_next;
    reg [8*285-1:0] pq_next;
    reg [289:0] cw_next,ccw_next;
    reg [2:0] fault;
    reg [N*274-1:0] cr_payload;
    reg [8*285-1:0] pq_payload;
    reg [288:0] cw_payload,ccw_payload;
    reg [N-1:0] cr_valid;
    reg [7:0] pq_valid;
    reg cw_valid,ccw_valid;
    for(genvar g=0;g<N;g=g+1) begin : client_output
        assign cr[g*274+:274]={cr_valid[g],cr_payload[g*274+:273]};
    end
    for(genvar g=0;g<8;g=g+1) begin : bank_output
        assign pq[g*285+:285]={pq_valid[g],pq_payload[g*285+:284]};
    end
    assign cwi={cw_valid,cw_payload};
    assign cci={ccw_valid,ccw_payload};
    always @(posedge clk) begin
        cr_payload<=cr_next; pq_payload<=pq_next;
        cw_payload<=cw_next[288:0]; ccw_payload<=ccw_next[288:0];
    end
    reg [N-1:0] issued_local,issued_cw,issued_ccw;
    wire [1:0] rank={me[1],me[1]^me[0]};
    wire [1:0] nr=rank+2'd1, orank=rank+2'd2, pvr=rank+2'd3;
    wire [1:0] next_sid=(PHYSICAL_RING!=0)?{nr[1],nr[1]^nr[0]}:me+2'd1;
    wire [1:0] opposite_sid=(PHYSICAL_RING!=0)?{orank[1],orank[1]^orank[0]}:me+2'd2;
    wire [1:0] previous_sid=(PHYSICAL_RING!=0)?{pvr[1],pvr[1]^pvr[0]}:me+2'd3;
    wire [3:0] cw_dest=(4'b1<<next_sid)|(4'b1<<opposite_sid);
    wire [3:0] ccw_dest=4'b1<<previous_sid;
    function automatic [2:0] bank_of(input [337:0] q);
        bank_of=q[311:309];
    endfunction
    function automatic [7:0] wordmask(input [337:0] q);
        for(integer w=0;w<8;w=w+1) wordmask[w]=&q[16+4*w+:4];
    endfunction
    function automatic local_needed(input [337:0] q,input integer c);
        local_needed=(c==NC)||q[324]||(q[323:322]==me);
    endfunction
    function automatic cw_needed(input [337:0] q,input integer c);
        cw_needed=(c!=NC)&&((q[324]&&q[336])||(!q[324]&&((4'b1<<q[323:322])&cw_dest)!=0));
    endfunction
    function automatic ccw_needed(input [337:0] q,input integer c);
        ccw_needed=(c!=NC)&&((q[324]&&q[336])||(!q[324]&&q[323:322]==previous_sid));
    endfunction
    always @(posedge clk) begin
        qr<=cq; sq<=client_seq; bc<=bank_client; cs<=cw_client;
        ccs<=ccw_client; me<=sid; br<=pr; rr0<=cco0; rr1<=cco1; rseq<=response_seq;
    end
    reg [N-1:0] qvalid;
    reg [7:0] bvalid;
    reg rvalid0,rvalid1;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            qvalid<='0; bvalid<='0; rvalid0<=0; rvalid1<=0;
            be<=0; ce<=0; cce<=0; re<=0;
        end else begin
            for(integer c=0;c<N;c=c+1) qvalid[c]<=cq[c*338+337];
            for(integer b=0;b<8;b=b+1) bvalid[b]<=pr[b*266+265];
            rvalid0<=cco0[263]; rvalid1<=cco1[263];
            be<=bank_enable; ce<=cw_enable; cce<=ccw_enable; re<=response_enable;
        end
    end
    // ---- response demultiplex (parallel): source s = {valid, client4, seq2, we, data256}
    wire [NS*264-1:0] rpf;
    for(genvar s=0;s<8;s=s+1) begin : rsp_bank
        assign rpf[s*264+:264]={bvalid[s],br[s*266+260+:4],br[s*266+256+:2],br[s*266+264],br[s*266+:256]};
    end
    assign rpf[8*264+:264]={rvalid0,rr0[262:0]};
    assign rpf[9*264+:264]={rvalid1,rr1[262:0]};
    // hit[(s*N+c)*4+k]: source s returns client c slot k this edge (a tag client >= N hits nothing: it faults)
    wire [NS*N*4-1:0] hit;
    for(genvar s=0;s<NS;s=s+1) begin : rsp_hit
        for(genvar c=0;c<N;c=c+1) begin : rsp_hit_c
            for(genvar k=0;k<4;k=k+1) begin : rsp_hit_k
                assign hit[(s*N+c)*4+k]=rpf[s*264+263] && rpf[s*264+259+:4]==4'(c) && rpf[s*264+257+:2]==2'(k);
            end
        end
    end
    wire [N*4*256-1:0] ret_f;   // returned_data[c][k]
    wire [N*4*3-1:0] arr_f;     // arrivals[c][k] (3-bit wrap, as the historical counter)
    for(genvar c=0;c<N;c=c+1) begin : rsp_slot_c
        for(genvar k=0;k<4;k=k+1) begin : rsp_slot_k
            wire [NS-1:0] h;
            for(genvar s=0;s<NS;s=s+1) begin : rsp_or
                assign h[s]=hit[(s*N+c)*4+k];
            end
            wire [255:0] t01=({256{h[0]}}&rpf[0*264+:256])|({256{h[1]}}&rpf[1*264+:256]);
            wire [255:0] t23=({256{h[2]}}&rpf[2*264+:256])|({256{h[3]}}&rpf[3*264+:256]);
            wire [255:0] t45=({256{h[4]}}&rpf[4*264+:256])|({256{h[5]}}&rpf[5*264+:256]);
            wire [255:0] t67=({256{h[6]}}&rpf[6*264+:256])|({256{h[7]}}&rpf[7*264+:256]);
            wire [255:0] t89=({256{h[8]}}&rpf[8*264+:256])|({256{h[9]}}&rpf[9*264+:256]);
            assign ret_f[(c*4+k)*256+:256]=((t01|t23)|(t45|t67))|t89;
            wire [1:0] p0=2'(h[0])+2'(h[1]), p1=2'(h[2])+2'(h[3]), p2=2'(h[4])+2'(h[5]),
                       p3=2'(h[6])+2'(h[7]), p4=2'(h[8])+2'(h[9]);
            wire [2:0] q0=3'(p0)+3'(p1), q1=3'(p2)+3'(p3);
            assign arr_f[(c*4+k)*3+:3]=(q0+q1)+3'(p4);
        end
    end
    wire [NS-1:0] src_bad;      // a valid return for a client >= N, or bank tag bits 3:2 non-zero
    for(genvar s=0;s<NS;s=s+1) begin : rsp_bad
        if(s<8) begin : g_b
            assign src_bad[s]=(rpf[s*264+263] && int'(rpf[s*264+259+:4])>=N) || (bvalid[s] && br[s*266+258+:2]!=0);
        end else begin : g_r
            assign src_bad[s]=rpf[s*264+263] && int'(rpf[s*264+259+:4])>=N;
        end
    end
    always @* begin : route
        integer c,k,b;
        reg [337:0] q;
        reg [3:0] mask;
        reg [7:0] wm;
        fault=0; pq_next=0; cw_next=0; ccw_next=0; cr_next=0;
        issued_local=0; issued_cw=0; issued_ccw=0;
        q=0; mask=0; wm=0; c=0; k=0;
        for(b=0;b<8;b=b+1) if(be[b]) begin
            c=int'(bc[b*CW+:CW]);
            if(c>=N) fault[0]=1;
            else begin
                q=qr[c*338+:338];
                if(!qvalid[c]||!local_needed(q,c)||bank_of(q)!=3'(b)) fault[0]=1;
                else begin
                    pq_next[b*285+:285]={1'b1,q[336],q[324],q[321:312],q[303:48],wordmask(q),4'(c),2'b00,sq[c*2+:2]};
                    if(issued_local[c]) fault[0]=1;
                    issued_local[c]=1;
                end
            end
        end
        for(integer dir=0;dir<2;dir=dir+1) if(dir==0?ce:cce) begin
            c=dir==0?int'(cs):int'(ccs);
            if(c>=N) fault[0]=1;
            else begin
                q=qr[c*338+:338];
                if(!qvalid[c]||!(dir==0?cw_needed(q,c):ccw_needed(q,c))) fault[0]=1;
                else begin
                    mask=q[324]?(dir==0?cw_dest:ccw_dest):(4'b1<<q[323:322]);
                    if(dir==0) begin
                        cw_next={1'b1,mask,4'(c),sq[c*2+:2],q[336],bank_of(q),q[324],q[321:312],wordmask(q),q[303:48]};
                        issued_cw[c]=1;
                    end else begin
                        ccw_next={1'b1,mask,4'(c),sq[c*2+:2],q[336],bank_of(q),q[324],q[321:312],wordmask(q),q[303:48]};
                        issued_ccw[c]=1;
                    end
                end
            end
        end
        for(c=0;c<N;c=c+1) if(qvalid[c]) begin
            q=qr[c*338+:338]; k=int'(sq[c*2+:2]); wm=wordmask(q);
            if(active[c][k]) fault[0]=1;
            if(issued_local[c]!=local_needed(q,c)||issued_cw[c]!=cw_needed(q,c)||issued_ccw[c]!=ccw_needed(q,c)) fault[0]=1;
            if(q[335:325]!=0||q[308:304]!=0||(q[324]&&q[323:322]!=0)||(c==NC&&!q[324]&&q[323:322]!=me)) fault[2]=1;
            for(integer w=0;w<8;w=w+1) if(q[336]&&q[16+4*w+:4]!={4{wm[w]}}) fault[1]=1;
        end
        if(|src_bad) fault[0]=1;
        for(integer s=0;s<NS;s=s+1) for(c=0;c<N;c=c+1) for(k=0;k<4;k=k+1)
            if(hit[(s*N+c)*4+k] && (!active[c][k] || writes[c][k]!=rpf[s*264+256])) fault[0]=1;
        for(c=0;c<N;c=c+1) begin
            for(k=0;k<4;k=k+1) if(arr_f[(c*4+k)*3+:3]!=0)
                if({1'b0,seen[c][k]}+{1'b0,arr_f[(c*4+k)*3+:3]}>{1'b0,expected[c][k]}) fault[0]=1;
            if(re[c]) begin
                k=int'(rseq[c*2+:2]);
                if(!active[c][k]||{1'b0,seen[c][k]}+{1'b0,arr_f[(c*4+k)*3+:3]}!={1'b0,expected[c][k]}) fault[0]=1;
                cr_next[c*274+:274]={1'b1,tags[c][k],writes[c][k],
                    writes[c][k]?256'd0:(response_data[c][k]|ret_f[(c*4+k)*256+:256])};
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin : state
        if(!rst_n) begin
            pq_valid<=0; cr_valid<=0; cw_valid<=0; ccw_valid<=0; status<=0;
            for(integer c=0;c<N;c=c+1) for(integer k=0;k<4;k=k+1) begin
                active[c][k]<=0; seen[c][k]<=0; expected[c][k]<=0; writes[c][k]<=0;
            end
        end else begin
            for(integer b=0;b<8;b=b+1) pq_valid[b]<=pq_next[b*285+284];
            for(integer c=0;c<N;c=c+1) cr_valid[c]<=cr_next[c*274+273];
            cw_valid<=cw_next[289]; ccw_valid<=ccw_next[289];
            status<=status|fault;
            for(integer c=0;c<N;c=c+1) begin
                for(integer k=0;k<4;k=k+1) if(arr_f[(c*4+k)*3+:3]!=0)
                    seen[c][k]<=seen[c][k]+arr_f[(c*4+k)*3+:3];
                if(re[c]) active[c][rseq[c*2+:2]]<=0;
                if(qvalid[c]) begin
                    active[c][sq[c*2+:2]]<=1;
                    seen[c][sq[c*2+:2]]<=0;
                    expected[c][sq[c*2+:2]]<=(qr[c*338+324]&&qr[c*338+336]&&c!=NC)?3'd4:3'd1;
                    writes[c][sq[c*2+:2]]<=qr[c*338+336];
                end
            end
        end
    end
    always @(posedge clk) for(integer c=0;c<N;c=c+1) begin
        for(integer k=0;k<4;k=k+1) if(arr_f[(c*4+k)*3+:3]!=0)
            response_data[c][k]<=response_data[c][k]|ret_f[(c*4+k)*256+:256];
        if(qvalid[c]) begin
            tags[c][sq[c*2+:2]]<=qr[c*338+:16];
            response_data[c][sq[c*2+:2]]<=0;
        end
    end
endmodule

// ot_vms_slice_static_glue (gen_vms_hoist.py) wiring with the _lt children, ONE tile clock and one regional reset per
// child (rst_n[0] hub, [1] CW stop, [2] CCW stop, [3] replay + status: ot_rst_relay copies in the tile top).
module hfd_vms_glue_core_lt #(
    parameter integer NC=0,
    parameter integer CW=((NC+1)>1)?$clog2(NC+1):1,
    parameter integer COMMIT_DELAY=6,
    parameter integer RMUT=0
)(
    input wire clk,
    input wire [3:0] rst_n,
    input wire [1:0] sid,
    input wire [((NC>0)?NC:1)*338-1:0] cq,
    output wire [((NC>0)?NC:1)*274-1:0] cr,
    input wire [(NC+1)*2-1:0] client_seq,
    input wire [(NC+1)-1:0] response_enable,
    input wire [(NC+1)*2-1:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [8*CW-1:0] bank_client,
    input wire [1:0] hub_ring_enable,
    input wire [2*CW-1:0] hub_ring_client,
    input wire [2223:0] cw_in,ccw_in,
    output wire [2223:0] cw_out,ccw_out,
    input wire [1:0] ring_tx_enable,
    input wire [5:0] ring_tx_source,
    input wire replay_enable,replay_source,
    input wire [143:0] bank_status,
    output wire [2207:0] bk_xq,bk_xq2,
    input wire [7:0] bk_xq_done,bk_xq2_done,
    input wire [2207:0] bk_eg,
    output wire [8*285-1:0] bk_pq,
    input wire [8*266-1:0] bk_pr,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);
    wire [(NC+1)*338-1:0] hcq;
    wire [(NC+1)*274-1:0] hcr;
    wire [337:0] hq;
    wire [273:0] hr=hcr[NC*274+:274];
    generate if(NC>0)begin:g_local
        assign hcq={hq,cq};assign cr=hcr[NC*274-1:0];
    end else begin:g_no_local
        assign hcq=hq;assign cr='0;
    end endgenerate
    wire [289:0] pi0,pi1;
    wire [263:0] cco0,cco1;
    wire [287:0] rce0,rce1;
    wire [265:0] ri0,ri1;
    wire [2:0] wk01,wk10;
    wire ack01,ack10;
    ot_vms_hub_lt #(.NC(NC),.CW(CW)) u_hub(
        .clk(clk),.rst_n(rst_n[0]),.sid(sid),.cq(hcq),.cr(hcr),
        .client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),
        .bank_enable(bank_enable),.bank_client(bank_client),
        .cw_enable(hub_ring_enable[0]),.cw_client(hub_ring_client[0+:CW]),
        .ccw_enable(hub_ring_enable[1]),.ccw_client(hub_ring_client[CW+:CW]),
        .pq(bk_pq),.pr(bk_pr),.cwi(pi0),.cci(pi1),.cco0(cco0),.cco1(cco1),.status(hub_status));
    ot_vms_rstop_lt #(.COMMIT_DELAY(COMMIT_DELAY),.MUT(RMUT)) u_cw(
        .clk(clk),.rst_n(rst_n[1]),.sid(sid),.dir(1'b0),
        .tx_enable(ring_tx_enable[0]),.tx_source(ring_tx_source[0+:3]),
        .l_in(cw_in),.l_out(cw_out),.pi(pi0),.eg(bk_eg),.xq(bk_xq),.xq_done(bk_xq_done),
        .rce(rce0),.ri(ri0),.wko(wk01),.wki(wk10),.cco(cco0),
        .ack_o(ack01),.ack_i(ack10),.mirror_busy(mirror_busy[0]),.fault(ring_fault[0]));
    ot_vms_rstop_lt #(.COMMIT_DELAY(COMMIT_DELAY),.MUT(RMUT)) u_ccw(
        .clk(clk),.rst_n(rst_n[2]),.sid(sid),.dir(1'b1),
        .tx_enable(ring_tx_enable[1]),.tx_source(ring_tx_source[3+:3]),
        .l_in(ccw_in),.l_out(ccw_out),.pi(pi1),.eg(bk_eg),.xq(bk_xq2),.xq_done(bk_xq2_done),
        .rce(rce1),.ri(ri1),.wko(wk10),.wki(wk01),.cco(cco1),
        .ack_o(ack10),.ack_i(ack01),.mirror_busy(mirror_busy[1]),.fault(ring_fault[1]));
    ot_vms_rcl_lt u_replay(.clk(clk),.rst_n(rst_n[3]),.sid(sid),
        .rx_enable(replay_enable),.rx_source(replay_source),.rce0(rce0),.rce1(rce1),
        .hq(hq),.hr(hr),.ri0(ri0),.ri1(ri1),.fault(ring_fault[2]));
    ot_vms_status_static u_status(.clk(clk),.rst_n(rst_n[3]),
        .bank_status(bank_status),.hub_status(hub_status),.ring_fault(|ring_fault),.vmstat(vmstat));
endmodule
`default_nettype wire
