`timescale 1ns/1ps
`default_nettype none
// Distinct captured-state compiler-issued ring stop. Component successor to historical ot_hgi_coll_pring.
// NO queue, arbitration, ready, credit or data-dependent issue. Every transfer,
// transit, add and publication is explicitly reserved by the compiler each edge.
// Physical order CW = 0,1,3,2. RX observes the input pin capture from the prior
// edge; TX is registered. Thus an adjacent TX -> RX reservation is two edges.
// Relay edges must be added to the compiler trace. An invalid trace faults; it
// never waits or repairs the timeline. This component is not a die qualification.
module ot_hgi_coll_pring_captured_static #
    parameter integer NT=8, LAT=8, SPLIT_CLOCKS=0,
    parameter integer MUT_CARRY=0, MUT_TAG=0
)(
    input wire clk, rst_n,
    input wire [7:0] clk_state, clk_add,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output reg [279:0] cw_o, ccw_o,
    input wire lp_we,
    input wire [2:0] lp_tag,
    input wire [255:0] lp_data,
    input wire state_read_add, state_read_tx, state_read_rr,
    input wire [2:0] state_add_tag, state_tx_tag, state_rr_tag,
    input wire [1:0] state_add_src,
    input wire state_add_rhs_acc, state_tx_acc,
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
    wire [255:0] rhs_add, carry_add, state_tx, acc_rr;
    wire [1:0] carry_write;
    for(genvar d=0;d<2;d=d+1)begin:g_carry_write
        assign carry_write[d]=rx_slot[d] && pin[d][278:277]==1 && pin[d][274:273]==qid;
    end
    reg [NT-1:0] local_v, acc_v, pending, active;
    reg [3:0] carry_v[0:NT-1];
    wire [255:0] aa = MUT_CARRY ? 256'b0 : carry_add;
    wire [255:0] ab = rhs_add;
    wire [255:0] ay;
    wire [7:0] av;
    reg read_add_v,read_tx_v,read_rr_v;
    reg [2:0] read_add_tag,read_tx_tag,read_rr_tag;
    reg [1:0] read_add_src;
    reg read_add_rhs,read_tx_acc;
    // Stage zero mirrors the exact state face input capture; stage one
    // aligns the returned state Qs with their consuming ADD/TX/RR edge.
    reg prep_add_v,prep_tx_v,prep_rr_v;
    reg [2:0] prep_add_tag,prep_tx_tag,prep_rr_tag;
    reg [1:0] prep_add_src;
    reg prep_add_rhs,prep_tx_acc;
    reg [LAT-1:0] pv;
    reg [2:0] pt[0:LAT-1];
    generate if (NT!=8 || LAT<4 || LAT>8) begin:g_bad
        ot_hgi_static_ring_requires_NT8_LAT4_to_8 invalid_configuration();
    end endgenerate
    // Payload and arithmetic are actual leaf modules, with one clock entry per
    // 32b lane. All roots have synchronous edge/phase semantics; SPLIT_CLOCKS
    // changes physical clock delivery only, never the compiler cycle price.
    // State leaf: 1,536 payload flops + 128 registered read face bits.
    // Each read is explicitly reserved TWO edges before add/TX/publication.
    // State input capture also shifts every write visibility by one edge.
    for(genvar l=0;l<8;l=l+1)begin:g_lane
        ot_hgi_coll_pring_static_state_capture_lane u_state(
            .clk(SPLIT_CLOCKS?clk_state[l]:clk),
            .lp_we(lp_we),.lp_tag(lp_tag),.lp_data(lp_data[l*32+:32]),
            .acc_we(pv[LAT-1]),.acc_tag(pt[LAT-1]),.acc_data(ay[l*32+:32]),
            .carry_we(carry_write),.carry0_tag(pin[0][270:268]),.carry0_src(pin[0][276:275]),
            .carry1_tag(pin[1][270:268]),.carry1_src(pin[1][276:275]),
            .carry0_data(pin[0][l*32+:32]),.carry1_data(pin[1][l*32+:32]),
            .read_add(state_read_add),.read_tx(state_read_tx),.read_rr(state_read_rr),
            .read_rhs_acc(state_add_rhs_acc),.read_tx_acc(state_tx_acc),
            .add_tag(state_add_tag),.add_src(state_add_src),.tx_tag(state_tx_tag),.rr_tag(state_rr_tag),
            .rhs_add(rhs_add[l*32+:32]),.carry_add(carry_add[l*32+:32]),
            .tx_data(state_tx[l*32+:32]),.acc_rr(acc_rr[l*32+:32]));
        ot_hgi_coll_pring_static_add_lane #(.LAT(LAT)) u_add(
            .clk(SPLIT_CLOCKS?clk_add[l]:clk),.rst_n(rst_n),.valid_in(add_v),
            .a(aa[l*32+:32]),.b(ab[l*32+:32]),.y(ay[l*32+:32]),.valid_out(av[l]));
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
            read_add_v<=0;read_tx_v<=0;read_rr_v<=0;
            prep_add_v<=0;prep_tx_v<=0;prep_rr_v<=0;
            for(integer t=0;t<NT;t=t+1)carry_v[t]<=0;
        end else begin
            pin[0]<=cw_i;pin[1]<=ccw_i;
            // Read reservations precede their consuming operation by exactly
            // two edges. These checks report faults, never gate issue or wait.
            prep_add_v<=state_read_add;prep_tx_v<=state_read_tx;prep_rr_v<=state_read_rr;
            prep_add_tag<=state_add_tag;prep_add_src<=state_add_src;prep_add_rhs<=state_add_rhs_acc;
            prep_tx_tag<=state_tx_tag;prep_tx_acc<=state_tx_acc;prep_rr_tag<=state_rr_tag;
            read_add_v<=prep_add_v;read_tx_v<=prep_tx_v;read_rr_v<=prep_rr_v;
            read_add_tag<=prep_add_tag;read_add_src<=prep_add_src;read_add_rhs<=prep_add_rhs;
            read_tx_tag<=prep_tx_tag;read_tx_acc<=prep_tx_acc;read_rr_tag<=prep_rr_tag;
            if(add_v!=read_add_v || (|tx_inject)!=read_tx_v || rr_local!=read_rr_v)fault<=1;
            if(add_v && (add_tag!=read_add_tag || add_src!=read_add_src || add_rhs_acc!=read_add_rhs))fault<=1;
            if((|tx_inject) && (tx_tag!=read_tx_tag || tx_acc!=read_tx_acc))fault<=1;
            if(rr_local && rr_local_tag!=read_rr_tag)fault<=1;
            if(state_read_add && (!carry_v[state_add_tag][state_add_src] || pending[state_add_tag] ||
               (state_add_rhs_acc ? !acc_v[state_add_tag] : !local_v[state_add_tag])))fault<=1;
            if(state_read_tx && (state_tx_acc ? (!acc_v[state_tx_tag] || pending[state_tx_tag]) : !local_v[state_tx_tag]))fault<=1;
            if(state_read_rr && (!acc_v[state_rr_tag] || pending[state_rr_tag]))fault<=1;
            if(state_read_add && !state_add_rhs_acc && lp_we && lp_tag==state_add_tag)fault<=1;
            if(state_read_tx && !state_tx_acc && lp_we && lp_tag==state_tx_tag)fault<=1;
            pv<={pv[LAT-2:0],add_v};pt[0]<=add_tag;
            for(integer i=1;i<LAT;i=i+1)pt[i]<=pt[i-1];
            rr_v<=rr_local;
            result_slots=0;
            if(rr_local)begin
                rr_tag<=rr_local_tag;rr_d<=acc_rr;
                if(!acc_v[rr_local_tag] || pending[rr_local_tag])fault<=1;
                acc_v[rr_local_tag]<=0;active[rr_local_tag]<=0;
            end
            if(lp_we)begin
                if(local_v[lp_tag] || active[lp_tag])fault<=1;
                active[lp_tag]<=1;
                local_v[lp_tag]<=1;
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
                acc_v[pt[LAT-1]]<=1;pending[pt[LAT-1]]<=0;
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
                        carry_v[tag][src]<=1;
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
                    outx=flit(tx_tag,state_tx);
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
