`timescale 1ns/1ps
`default_nettype none
// Compiler scheduled successor of the historical B2 ring stop. The flit ABI
// stays 2224 bits. Every injected, forwarded, replayed and committed beat has
// an assigned cycle; there are no credits, queues, retries or dynamic picks.
// tx source 0 transit, 1 hub PREQ, 2 bank mirror egress, 3 replay PRSP,
// 4 opposite-stop WACK. A local eject and transit may share the same cycle.
module ot_vms_rstop_static #(
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
    reg [2223:0] in_q;
    reg [289:0] pi_q;
    reg [2207:0] eg_q;
    reg [265:0] ri_q;
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
    // Only valid state resets. All outputs are registered face pins.
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            in_q<='0;pi_q<='0;eg_q<='0;ri_q<='0;wki_q<='0;
            source_q<=0;enable_q<=0;me<=0;dr<=0;ack_q<=0;
            l_out<='0;xq<='0;rce<='0;cco<='0;ack_o<=0;wko<='0;
            commit_v<='0;outstanding<=0;mirror_busy<=0;fault<=0;
            for(integer t=0;t<COMMIT_DELAY;t=t+1) begin commit_mask[t]<=0;commit_src[t]<=0;end
        end else begin
            in_q<=l_in;pi_q<=pi;eg_q<=eg;ri_q<=ri;wki_q<=wki;
            source_q<=tx_source;enable_q<=tx_enable;me<=sid;dr<=dir;ack_q<=ack_i;
            l_out<=flit;
            xq<='0;rce<='0;cco<='0;ack_o<=0;
            if(own) case(kind)
                0: begin
                    rce<={1'b1,in_q[2216:2215],in_q[2214:2211],in_q[2210:2209],in_q[2208],bank,lane[274:264],lane[7:0],lane[263:8]};
                    if($countones(lanes)!=1) fault<=1;
                end
                1: xq<=in_q[2207:0];
                2: cco<={1'b1,in_q[2214:2211],in_q[2210:2209],in_q[2208],in_q[263:8]};
                3: ack_o<=1;
            endcase
            // The compiler cannot silently discard any arriving work.
            if((transit && (!enable_q || source_q!=0)) ||
               (pi_q[289] && (!enable_q || source_q!=1)) ||
               ((|ev) && (!enable_q || source_q!=2)) ||
               (ri_q[265] && (!enable_q || source_q!=3)) ||
               (wki_q[2] && (!enable_q || source_q!=4)) ||
               (enable_q && source_q>4) ||
               (in_q[2223] && in_q[2220:2217]==0)) fault<=1;
            commit_v[0]<=own && kind==1;
            commit_mask[0]<=lanes;commit_src[0]<=in_q[2216:2215];
            for(integer t=1;t<COMMIT_DELAY;t=t+1) begin
                commit_v[t]<=commit_v[t-1];commit_mask[t]<=commit_mask[t-1];commit_src[t]<=commit_src[t-1];
            end
            wko<=0;
            if(commit_v[COMMIT_DELAY-1]) begin
                if((xq_done & commit_mask[COMMIT_DELAY-1]) != commit_mask[COMMIT_DELAY-1]) fault<=1;
                else wko<={1'b1,commit_src[COMMIT_DELAY-1]};
            end
            // Outstanding is observation only: it never gates any datapath.
            outstanding<=outstanding + ((flit[2223] && source_q==2)?(dr?16'd1:16'd2):16'd0) - (ack_q?16'd1:16'd0);
            mirror_busy<=outstanding!=0;
            if(ack_q && outstanding==0) fault<=1;
        end
    end
endmodule
`default_nettype wire
