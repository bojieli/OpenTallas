`timescale 1ns/1ps
`default_nettype none
// Compiler-issued ring stop. Component successor to historical ot_hgi_coll_pring.
// NO queue, arbitration, ready, credit or data-dependent issue. Every transfer,
// transit, add and publication is explicitly reserved by the compiler each edge.
// Physical order CW = 0,1,3,2. RX observes the input pin capture from the prior
// edge; TX is registered. Thus an adjacent TX -> RX reservation is two edges.
// Relay edges must be added to the compiler trace. An invalid trace faults; it
// never waits or repairs the timeline. This component is not a die qualification.
module ot_hgi_coll_pring_static #(
    parameter integer NT=8, LAT=8,
    parameter integer MUT_CARRY=0, MUT_TAG=0
)(
    input wire clk, rst_n,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output reg [279:0] cw_o, ccw_o,
    input wire lp_we,
    input wire [2:0] lp_tag,
    input wire [255:0] lp_data,
    input wire add_v,
    input wire [2:0] add_tag,
    input wire [1:0] add_src,
    input wire add_rhs_acc,
    input wire [1:0] tx_inject, tx_forward,
    input wire [2:0] tx_tag,
    input wire [1:0] tx_dst,
    input wire tx_result, tx_acc,
    input wire [1:0] rx_slot,
    input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag,
    input wire rr_local,
    input wire [2:0] rr_local_tag,
    output reg rr_v,
    output reg [2:0] rr_tag,
    output reg [255:0] rr_d,
    output reg fault
);
    // 280b historical pin encoding retained: v,kind,src,dst,ttl,tag,
    // mode(reserved),aux(reserved),data. Only CARRY=1 and RESULT=2 allowed.
    reg [279:0] pin [0:1];
    reg [255:0] local_d[0:NT-1], acc_d[0:NT-1], carry_d[0:NT-1][0:3];
    reg [NT-1:0] local_v, acc_v, pending, active;
    reg [3:0] carry_v[0:NT-1];
    wire [255:0] aa = MUT_CARRY ? 256'b0 : carry_d[add_tag][add_src];
    wire [255:0] ab = add_rhs_acc ? acc_d[add_tag] : local_d[add_tag];
    wire [255:0] ay;
    wire [7:0] av;
    reg [LAT-1:0] pv;
    reg [2:0] pt[0:LAT-1];
    generate if (NT!=8 || LAT<4 || LAT>8) begin:g_bad
        ot_hgi_static_ring_requires_NT8_LAT4_to_8 invalid_configuration();
    end endgenerate
    // One input pin stage + LAT-1 real arithmetic stages, as historical lane.
    for(genvar l=0;l<8;l=l+1)begin:g_add
        reg [31:0] ap,bp;
        reg vp;
        always @(posedge clk)begin
            ap <= aa[l*32+:32];
            bp <= ab[l*32+:32];
        end
        always @(posedge clk or negedge rst_n)
            if(!rst_n)vp<=0;else vp<=add_v;
        ot_hdc_fp32_add_lat #(.LAT(LAT-1),.DRST(0)) u_add(
            .clk(clk),.rst_n(rst_n),.valid_in(vp),.a(ap),.b(bp),
            .y(ay[l*32+:32]),.err(),.valid_out(av[l]));
    end
    function automatic [279:0] flit(input [2:0] tag,input [255:0] data);
        flit={1'b1,tx_result?2'd2:2'd1,qid,tx_dst,
              tx_result?2'd3:2'd0,MUT_TAG?(tag^3'd1):tag,1'b0,11'b0,data};
    endfunction
    always @(posedge clk or negedge rst_n) begin:step
        reg [279:0] x,outx;
        reg [2:0] tag;
        reg [1:0] src,dst,kind,ttl;
        reg [1:0] result_slots;
        if(!rst_n)begin
            pin[0]<=0;pin[1]<=0;cw_o<=0;ccw_o<=0;
            local_v<=0;acc_v<=0;pending<=0;active<=0;pv<=0;
            rr_v<=0;rr_tag<=0;rr_d<=0;fault<=0;
            for(integer t=0;t<NT;t=t+1)carry_v[t]<=0;
        end else begin
            pin[0]<=cw_i;pin[1]<=ccw_i;
            pv<={pv[LAT-2:0],add_v};pt[0]<=add_tag;
            for(integer i=1;i<LAT;i=i+1)pt[i]<=pt[i-1];
            rr_v<=rr_local;
            result_slots=0;
            if(rr_local)begin
                rr_tag<=rr_local_tag;rr_d<=acc_d[rr_local_tag];
                if(!acc_v[rr_local_tag] || pending[rr_local_tag])fault<=1;
                acc_v[rr_local_tag]<=0;active[rr_local_tag]<=0;
            end
            if(lp_we)begin
                if(local_v[lp_tag] || active[lp_tag])fault<=1;
                active[lp_tag]<=1;
                local_d[lp_tag]<=lp_data;local_v[lp_tag]<=1;
            end
            if(add_v)begin
                if(!carry_v[add_tag][add_src] || pending[add_tag] ||
                   (add_rhs_acc ? !acc_v[add_tag] : !local_v[add_tag]))fault<=1;
                if(lp_we && lp_tag==add_tag && !add_rhs_acc)fault<=1;
                carry_v[add_tag][add_src]<=0;pending[add_tag]<=1;
                if(add_rhs_acc)acc_v[add_tag]<=0;else local_v[add_tag]<=0;
            end
            if(av!={8{pv[LAT-1]}})fault<=1;
            if(pv[LAT-1])begin
                if(acc_v[pt[LAT-1]])fault<=1;
                if(add_v && add_tag==pt[LAT-1])fault<=1;
                acc_d[pt[LAT-1]]<=ay;acc_v[pt[LAT-1]]<=1;pending[pt[LAT-1]]<=0;
            end
            // Every physical arrival, including transit, must match a reservation.
            // A reservation with missing input also faults at this exact edge.
            for(integer d=0;d<2;d=d+1)begin
                x=pin[d];outx=0;
                tag=x[270:268];src=x[276:275];dst=x[274:273];
                kind=x[278:277];ttl=x[272:271];
                if(x[279]!=rx_slot[d])fault<=1;
                if(rx_slot[d])begin
                    if(kind!=rx_kind[d*2+:2] || src!=rx_src[d*2+:2] ||
                       tag!=rx_tag[d*3+:3] || (kind!=1 && kind!=2) ||
                       x[267:256]!=0)fault<=1;
                    if(!active[tag])fault<=1;
                    if(d==1 && rx_slot[0] && pin[0][279] &&
                       pin[0][270:268]==tag && pin[0][276:275]==src &&
                       pin[0][278:277]==1 && kind==1 &&
                       pin[0][274:273]==qid && dst==qid)fault<=1;
                    if(kind==1 && dst==qid)begin
                        if(carry_v[tag][src] || tx_forward[d])fault<=1;
                        if(add_v && add_tag==tag && add_src==src)fault<=1;
                        carry_d[tag][src]<=x[255:0];carry_v[tag][src]<=1;
                    end
                    if(kind==2)begin
                        if(ttl==0)fault<=1;
                        result_slots[d]=1;active[tag]<=0;
                        rr_v<=1;rr_tag<=tag;rr_d<=x[255:0];
                        if(rr_local || |(result_slots & ~(2'b1<<d)))fault<=1;
                    end
                    if((kind==1 && dst!=qid) || (kind==2 && ttl>1))begin
                        if(!tx_forward[d])fault<=1;
                    end else if(tx_forward[d])fault<=1;
                end
                if(tx_forward[d])begin
                    if(!rx_slot[d] || !x[279])fault<=1;
                    outx=x;
                    if(kind==2)outx[272:271]=ttl-1'b1;
                end
                if(tx_inject[d])begin
                    if(tx_forward[d])fault<=1;
                    if(tx_acc ? (!acc_v[tx_tag] || pending[tx_tag]) : !local_v[tx_tag])fault<=1;
                    if(tx_result && (!tx_acc || tx_dst!=qid))fault<=1;
                    outx=flit(tx_tag,tx_acc?acc_d[tx_tag]:local_d[tx_tag]);
                end
                if(d==0)cw_o<=outx;else ccw_o<=outx;
            end
            if(|tx_inject)begin
                // Copies sent simultaneously in both directions are compiler-
                // reserved, with the same payload. No runtime multicast arbiter.
                if(!tx_acc)local_v[tx_tag]<=0;
                else if(!tx_result)acc_v[tx_tag]<=0;
            end
        end
    end
endmodule
`default_nettype wire
