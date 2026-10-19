`timescale 1ns/1ps
`default_nettype none
// VM-GLUE2 2026-10-18: ot_vms_rstop_static with VALID-ONLY reset (the hub's own rule: "every pin payload is captured;
// only validity/control flops reset").  The original resets ~10k payload flops a stop (in_q / eg_q / l_out / xq / ...),
// which made the hub-glue tile's rst_n a 19k-load net (textbook high_fanout REFUSE) and its recovery path -450 ps.
// Here only the state that gates behaviour resets: in_q valid (2223), pi_q valid (289), the 8 eg lane valids (ev),
// ri_q valid (265), wki_q, the tx controls, me / dr / ack_q, commit_v, outstanding, mirror_busy, fault.  Payload
// registers and the registered outputs (l_out / xq / rce / cco / ack_o / wko) are plain flops: their next value is a
// function of reset state that forces them to 0 (enable_q = 0 -> flit = 0; own = 0 -> xq / rce / cco / ack_o = 0;
// commit_v = 0 -> wko = 0), so one clock edge inside reset flushes them and every edge after release is identical to
// ot_vms_rstop_static (tile equivalence bench: same random inputs, every output every edge).  Logic otherwise verbatim.
module ot_vms_rstop_static_vr #(
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
    // payload (no reset) and valid (reset) halves of the input registers
    reg [2222:0] in_p; reg in_v;
    reg [288:0] pi_p;  reg pi_v;
    reg [2207:0] eg_p; reg [7:0] eg_v;
    reg [264:0] ri_p;  reg ri_v;
    wire [2223:0] in_q={in_v,in_p};
    wire [289:0] pi_q={pi_v,pi_p};
    reg [2207:0] eg_q;
    always @* begin
        eg_q=eg_p;
        for(integer b=0;b<8;b=b+1) eg_q[b*276+275]=eg_v[b];
    end
    wire [265:0] ri_q={ri_v,ri_p};
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
    // payload capture and registered face outputs: no reset (flushed to 0 by the reset state, see header)
    always @(posedge clk) begin
        in_p<=l_in[2222:0]; pi_p<=pi[288:0]; eg_p<=eg; ri_p<=ri[264:0];
        l_out<=flit;
        xq<='0;rce<='0;cco<='0;ack_o<=0;
        if(own) case(kind)
            0: rce<={1'b1,in_q[2216:2215],in_q[2214:2211],in_q[2210:2209],in_q[2208],bank,lane[274:264],lane[7:0],lane[263:8]};
            1: xq<=in_q[2207:0];
            2: cco<={1'b1,in_q[2214:2211],in_q[2210:2209],in_q[2208],in_q[263:8]};
            3: ack_o<=1;
        endcase
        commit_mask[0]<=lanes;commit_src[0]<=in_q[2216:2215];
        for(integer t=1;t<COMMIT_DELAY;t=t+1) begin
            commit_mask[t]<=commit_mask[t-1];commit_src[t]<=commit_src[t-1];
        end
        wko<=0;
        if(commit_v[COMMIT_DELAY-1] && (xq_done & commit_mask[COMMIT_DELAY-1]) == commit_mask[COMMIT_DELAY-1])
            wko<={1'b1,commit_src[COMMIT_DELAY-1]};
    end
    // valid / control state: asynchronous reset (as the original)
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            in_v<=0;pi_v<=0;eg_v<='0;ri_v<=0;wki_q<='0;
            source_q<=0;enable_q<=0;me<=0;dr<=0;ack_q<=0;
            commit_v<='0;outstanding<=0;mirror_busy<=0;fault<=0;
        end else begin
            in_v<=l_in[2223];pi_v<=pi[289];ri_v<=ri[265];wki_q<=wki;
            for(integer b=0;b<8;b=b+1) eg_v[b]<=eg[b*276+275];
            source_q<=tx_source;enable_q<=tx_enable;me<=sid;dr<=dir;ack_q<=ack_i;
            if(own && kind==0 && $countones(lanes)!=1) fault<=1;
            // The compiler cannot silently discard any arriving work.
            if((transit && (!enable_q || source_q!=0)) ||
               (pi_q[289] && (!enable_q || source_q!=1)) ||
               ((|ev) && (!enable_q || source_q!=2)) ||
               (ri_q[265] && (!enable_q || source_q!=3)) ||
               (wki_q[2] && (!enable_q || source_q!=4)) ||
               (enable_q && source_q>4) ||
               (in_q[2223] && in_q[2220:2217]==0)) fault<=1;
            commit_v[0]<=own && kind==1;
            for(integer t=1;t<COMMIT_DELAY;t=t+1) commit_v[t]<=commit_v[t-1];
            if(commit_v[COMMIT_DELAY-1] && (xq_done & commit_mask[COMMIT_DELAY-1]) != commit_mask[COMMIT_DELAY-1]) fault<=1;
            // Outstanding is observation only: it never gates any datapath.
            outstanding<=outstanding + ((flit[2223] && source_q==2)?(dr?16'd1:16'd2):16'd0) - (ack_q?16'd1:16'd0);
            mirror_busy<=outstanding!=0;
            if(ack_q && outstanding==0) fault<=1;
        end
    end
endmodule
`default_nettype wire
