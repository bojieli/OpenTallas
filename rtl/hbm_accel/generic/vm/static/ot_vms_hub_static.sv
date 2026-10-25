`timescale 1ns/1ps
`default_nettype none
// Static successor to b2/ot_vms_hub. Historical credit tile is unchanged.
// NC local clients plus client NC for replay from the VM ring. Compiler selects
// a client independently for each bank and each ring direction, on the SAME
// edge as cq and client_seq. There is no pending-request storage or arbitration.
// cq338={v,we,addr32,data256,byte_mask32,tag16}; cr274={v,tag16,we,data256}.
// pq285={v,we,rowm11,data256,wordmask8,tag8}; pr266={v,we,tag8,data256}.
// Bank tag={client4,00,seq2}; PREQ290={v,dmask4,client4,seq2,we,bank3,
// rowm11,wmask8,data256}; PRSP264={v,client4,seq2,we,data256}.
// Requests and responses each take TWO edges through pin/output registers.
// Four tag slots per client are compiler allocated, never used for admission.
// Compiler must issue every piece of a packet together, reserve its slot until
// return, preserve client request/response order, and avoid multiple completed
// transactions for a client on one edge.
// Native mirror writes issue local+CW(next,opposite)+CCW(previous); all four
// acknowledgements must precede the compiler response calendar. Missing ones
// fault at that edge; they never delay or replay cr. Replay never rebroadcasts.
// status sticky {range/address fault, byte-mask fault, schedule/identity fault}.
// NSTOP (HBM-BIND 2026-10-24): 4 = four-stop ring, bit-exact the original. 2 = two-stop ring of the adjacent pair
// {sid, sid^1} (B2 die: NW + NE). Each hub then reaches its single peer over ONE direction (cw if the peer is the next
// physical stop, else ccw: NE cw, NW ccw), which is the direction the four-stop map already uses for that peer:
// unicast routing is unchanged; a native mirror write issues local + that one direction (mask = peer) and waits for
// TWO acknowledgements (not four); a unicast to a quadrant outside {sid, peer} is a range/address fault.
module ot_vms_hub_static #(
    parameter integer NC=4,
    parameter integer PHYSICAL_RING=1,
    parameter integer CW=(NC<1)?1:$clog2(NC+1),
    parameter integer NSTOP=4,
    parameter integer MUT=0 // 1 wrong bank; 2 wrong tag; 3 ignores select; 4 waits for missing ack;
                            // 5 NSTOP 2 mirror waits for four acks; 6 NSTOP 2 mirror needs both directions
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
    reg [2:0] arrivals[0:N-1][0:3];
    reg [255:0] returned_data[0:N-1][0:3];
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
    wire [1:0] peer_sid=me^2'b01;
    wire [3:0] cw_dest=(NSTOP==2)?((next_sid==peer_sid)?(4'b1<<peer_sid):4'b0):(4'b1<<next_sid)|(4'b1<<opposite_sid);
    wire [3:0] ccw_dest=(NSTOP==2)?((previous_sid==peer_sid)?(4'b1<<peer_sid):4'b0):4'b1<<previous_sid;
    localparam [2:0] MIRROR_ACKS=(NSTOP==2&&MUT!=5)?3'd2:3'd4;
    localparam integer MIRROR_BOTH=((NSTOP!=2)||(MUT==6))?1:0;
    function automatic [2:0] bank_of(input [337:0] q);
        bank_of=(MUT==1)?q[312:310]:q[311:309];
    endfunction
    function automatic [7:0] wordmask(input [337:0] q);
        for(integer w=0;w<8;w=w+1) wordmask[w]=&q[16+4*w+:4];
    endfunction
    function automatic local_needed(input [337:0] q,input integer c);
        local_needed=(c==NC)||q[324]||(q[323:322]==me);
    endfunction
    function automatic cw_needed(input [337:0] q,input integer c);
        cw_needed=(c!=NC)&&((q[324]&&q[336]&&(MIRROR_BOTH!=0||cw_dest!=0))||(!q[324]&&((4'b1<<q[323:322])&cw_dest)!=0));
    endfunction
    function automatic ccw_needed(input [337:0] q,input integer c);
        ccw_needed=(c!=NC)&&((q[324]&&q[336]&&(MIRROR_BOTH!=0||ccw_dest!=0))||(!q[324]&&
            ((NSTOP==2)?(((4'b1<<q[323:322])&ccw_dest)!=0):(q[323:322]==previous_sid))));
    endfunction
    // Every pin payload is captured; only validity/control flops reset.
    always @(posedge clk) begin
        qr<=cq; sq<=client_seq; bc<=bank_client; cs<=cw_client;
        ccs<=ccw_client; me<=sid; br<=pr; rr0<=cco0; rr1<=cco1; rseq<=response_seq;
    end
    // Mask pin valid bits independently of payload reset.
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
    always @* begin : route
        integer c,k,b,rc,rs,completed;
        reg [337:0] q;
        reg [3:0] mask;
        reg [263:0] rp;
        reg [7:0] wm;
        fault=0; pq_next=0; cw_next=0; ccw_next=0; cr_next=0;
        issued_local=0; issued_cw=0; issued_ccw=0;
        q=0; mask=0; rp=0; wm=0; c=0; k=0; rc=0; rs=0; completed=0;
        for(b=0;b<8;b=b+1) if(be[b]) begin
            c=(MUT==3)?0:int'(bc[b*CW+:CW]);
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
                    rp=0;
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
            if(NSTOP==2&&!q[324]&&q[323:322]!=me&&q[323:322]!=peer_sid) fault[2]=1;
            for(integer w=0;w<8;w=w+1) if(q[336]&&q[16+4*w+:4]!={4{wm[w]}}) fault[1]=1;
        end
        for(c=0;c<N;c=c+1) for(k=0;k<4;k=k+1) begin arrivals[c][k]=0; returned_data[c][k]=0; end
        // Tag-decode demultiplex only; no response priority or ready signals.
        for(b=0;b<10;b=b+1) begin
            if(b<8) begin
                rc=int'(br[b*266+260+:4]); rs=int'(br[b*266+256+:2]);
                rp={bvalid[b],br[b*266+260+:4],br[b*266+256+:2],br[b*266+264],br[b*266+:256]};
                if(bvalid[b]&&br[b*266+258+:2]!=0) fault[0]=1;
            end else begin
                rp=b==8?{rvalid0,rr0[262:0]}:{rvalid1,rr1[262:0]};
                rc=int'(rp[262:259]); rs=int'(rp[258:257]);
            end
            if(rp[263]) begin
                if(rc>=N) fault[0]=1;
                else begin
                    if(!active[rc][rs]||writes[rc][rs]!=rp[256]) fault[0]=1;
                    arrivals[rc][rs]=arrivals[rc][rs]+3'd1;
                    returned_data[rc][rs]=returned_data[rc][rs]|rp[255:0];
                end
            end
        end
        for(c=0;c<N;c=c+1) begin
            for(k=0;k<4;k=k+1) if(arrivals[c][k]!=0)
                if({1'b0,seen[c][k]}+{1'b0,arrivals[c][k]}>{1'b0,expected[c][k]}) fault[0]=1;
            // A compiler calendar entry emits on its assigned edge, even on a
            // missing-ack fault. There is no completion-driven release path.
            if(re[c]&&(MUT!=4||seen[c][rseq[c*2+:2]]+arrivals[c][rseq[c*2+:2]]==expected[c][rseq[c*2+:2]])) begin
                k=int'(rseq[c*2+:2]);
                if(!active[c][k]||{1'b0,seen[c][k]}+{1'b0,arrivals[c][k]}!={1'b0,expected[c][k]}) fault[0]=1;
                cr_next[c*274+:274]={1'b1,(MUT==2?tags[c][k]^16'd1:tags[c][k]),writes[c][k],
                    writes[c][k]?256'd0:(response_data[c][k]|returned_data[c][k])};
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
                for(integer k=0;k<4;k=k+1) if(arrivals[c][k]!=0) begin
                    seen[c][k]<=seen[c][k]+arrivals[c][k];

                end
                if(re[c]) active[c][rseq[c*2+:2]]<=0;
                if(qvalid[c]) begin
                    active[c][sq[c*2+:2]]<=1;
                    seen[c][sq[c*2+:2]]<=0;
                    expected[c][sq[c*2+:2]]<=(qr[c*338+324]&&qr[c*338+336]&&c!=NC)?MIRROR_ACKS:3'd1;
                    writes[c][sq[c*2+:2]]<=qr[c*338+336];
                end
            end
        end
    end
    always @(posedge clk) for(integer c=0;c<N;c=c+1) begin
        for(integer k=0;k<4;k=k+1) if(arrivals[c][k]!=0)
            response_data[c][k]<=response_data[c][k]|returned_data[c][k];
        if(qvalid[c]) begin
            tags[c][sq[c*2+:2]]<=qr[c*338+:16];
            response_data[c][sq[c*2+:2]]<=0;
        end
    end
endmodule
`default_nettype wire
