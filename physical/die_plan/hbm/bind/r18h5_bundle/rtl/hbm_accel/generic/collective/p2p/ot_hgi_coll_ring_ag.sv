`timescale 1ns/1ps
`default_nettype none
// HBM-B-RTL3 (d4g plan b, 10-17): COLL ring stop with an on-die ALL-GATHER (kind GATHER = 3).
// Successor of ot_hgi_coll_pring_captured_static (ring_v5). With AG=0 it is cycle- and
// bit-identical to ring_v5 (bench: the unchanged ring_v5 suite runs through an adapter).
// d4g: each quadrant COLL engine writes ONLY its own quadrant's VM banks, so every quadrant's
// slice of x is replicated to the other three quadrants over this ring (the XQ fat lane).
// GATHER flit = {v=1, kind=3, src=qid, dst=qid, ttl, tag, 0, 0, payload}. The compiler
// reserves, for every edge: the injection (tx_inject[d] & tx_gather, ttl tx_ttl[2d+:2] per
// direction, payload = local lp or acc state read two edges earlier), every transit
// (tx_forward[d] while ttl>1; the stop decrements ttl), and every arrival (rx_slot/kind/src/tag).
// Each arrival is published on the per-direction port ag_*[d] one edge later (registered),
// so two gathers (CW and CCW) can land in the same edge: 64 B/edge into a stop.
// NO queue, arbitration, ready, credit or data-dependent issue; a GATHER needs no tag state at
// the receiver. A mismatching trace raises the sticky fault and never stalls/repairs timing.
// Price: a hop = 2 edges + the die relay stages of the ring lane; balanced split
// (even flits CW ttl2 + CCW ttl1, odd flits CW ttl1 + CCW ttl2) -> 1.5 link slots a flit,
// i.e. a quadrant slice of F flits is all-gathered in ceil(1.5 F) + 4 + 2 r edges (r = relays/hop).
// The control root is a separate hardenable leaf (ot_hgi_coll_ring_ag_ctl); the stop is
// wires only around it + the unchanged CLOSED state-capture lanes + the add lanes.
module ot_hgi_coll_ring_ag_ctl #(
    parameter integer NT=8, LAT=8, AG=1,
    parameter integer MUT_TAG=0, MUT_TTL=0, MUT_SRC=0
)(
    input wire clk, rst_n,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output wire [279:0] cw_o, ccw_o,
    input wire lp_we,
    input wire [2:0] lp_tag,
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
    input wire tx_gather,
    input wire [3:0] tx_ttl,
    input wire [1:0] rx_slot,
    input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag,
    input wire rr_local,
    input wire [2:0] rr_local_tag,
    // lane faces (state-capture lanes + add lanes)
    output wire [279:0] pin0_q, pin1_q,
    output wire [1:0] carry_write,
    output wire acc_we,
    output wire [2:0] acc_tag,
    input wire [255:0] state_tx, acc_rr,
    input wire [7:0] av,
    output reg rr_v,
    output reg [2:0] rr_tag,
    output reg [255:0] rr_d,
    output reg [1:0] ag_v,
    output reg [3:0] ag_src,
    output reg [5:0] ag_tag,
    output reg [511:0] ag_d,
    output reg fault
);
    // RTL3c (review 10-17): async reset only on CONTROL state. Data registers (ring pin / output
    // payloads, rr_d/rr_tag, ag_d/ag_src/ag_tag) are plain flops in a separate block; every one is
    // qualified by a reset valid bit (pin/cw_o/ccw_o bit 279, rr_v, ag_v), so behaviour is unchanged.
    reg [1:0] pin_v, out_v;
    reg [278:0] pin_p [0:1];
    reg [278:0] out_p [0:1];
    wire [279:0] pin [0:1];
    assign pin[0]={pin_v[0],pin_p[0]};assign pin[1]={pin_v[1],pin_p[1]};
    assign cw_o={out_v[0],out_p[0]};assign ccw_o={out_v[1],out_p[1]};
    assign pin0_q=pin[0];assign pin1_q=pin[1];
    for(genvar d=0;d<2;d=d+1)begin:g_carry_write
        assign carry_write[d]=rx_slot[d] && pin[d][278:277]==1 && pin[d][274:273]==qid;
    end
    reg [NT-1:0] local_v, acc_v, pending, active;
    reg [3:0] carry_v[0:NT-1];
    reg read_add_v,read_tx_v,read_rr_v;
    reg [2:0] read_add_tag,read_tx_tag,read_rr_tag;
    reg [1:0] read_add_src;
    reg read_add_rhs,read_tx_acc;
    reg prep_add_v,prep_tx_v,prep_rr_v;
    reg [2:0] prep_add_tag,prep_tx_tag,prep_rr_tag;
    reg [1:0] prep_add_src;
    reg prep_add_rhs,prep_tx_acc;
    reg [LAT-1:0] pv;
    reg [2:0] pt[0:LAT-1];
    assign acc_we=pv[LAT-1];assign acc_tag=pt[LAT-1];
    generate if (NT!=8 || LAT<4 || LAT>8) begin:g_bad
        ot_hgi_static_ring_requires_NT8_LAT4_to_8 invalid_configuration();
    end endgenerate
    wire gath = AG!=0 && tx_gather;
    function automatic [279:0] flit(input integer d,input [2:0] tag,input [255:0] data);
        flit={1'b1,gath?2'd3:(tx_result?2'd2:2'd1),qid,gath?qid:tx_dst,
              gath?tx_ttl[d*2+:2]:(tx_result?2'd3:2'd0),MUT_TAG?(tag^3'd1):tag,1'b0,11'b0,data};
    endfunction
    // ring outputs (combinational next value; valid bit reset-registered, payload plain-registered)
    reg [279:0] nx_out [0:1];
    always @* begin:outs
        reg [279:0] x;
        for(integer d=0;d<2;d=d+1)begin
            x=pin[d];nx_out[d]=0;
            if(tx_forward[d])begin
                nx_out[d]=x;
                if(x[278:277]==2)nx_out[d][272:271]=x[272:271]-1'b1;
                if(x[278:277]==3)nx_out[d][272:271]=x[272:271]-(MUT_TTL?2'd2:2'd1);
            end
            if(tx_inject[d])nx_out[d]=flit(d,tx_tag,state_tx);
        end
    end
    // data registers: no reset (loads of rst_n = control state only)
    always @(posedge clk) begin:data
        reg [279:0] x;
        pin_p[0]<=cw_i[278:0];pin_p[1]<=ccw_i[278:0];
        out_p[0]<=nx_out[0][278:0];out_p[1]<=nx_out[1][278:0];
        if(rr_local)begin rr_tag<=rr_local_tag;rr_d<=acc_rr;end
        for(integer d=0;d<2;d=d+1)begin
            x=pin[d];
            if(rx_slot[d] && x[278:277]==2)begin rr_tag<=x[270:268];rr_d<=x[255:0];end
            if(AG!=0 && rx_slot[d] && x[278:277]==3)begin
                ag_src[d*2+:2]<=MUT_SRC?qid:x[276:275];ag_tag[d*3+:3]<=x[270:268];ag_d[d*256+:256]<=x[255:0];
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin:step
        reg [279:0] x;
        reg [2:0] tag;
        reg [1:0] src,dst,kind,ttl;
        reg [1:0] result_slots;
        if(!rst_n)begin
            pin_v<=0;out_v<=0;
            local_v<=0;acc_v<=0;pending<=0;active<=0;pv<=0;
            rr_v<=0;fault<=0;ag_v<=0;
            read_add_v<=0;read_tx_v<=0;read_rr_v<=0;
            prep_add_v<=0;prep_tx_v<=0;prep_rr_v<=0;
            for(integer t=0;t<NT;t=t+1)carry_v[t]<=0;
        end else begin
            pin_v<={ccw_i[279],cw_i[279]};out_v<={nx_out[1][279],nx_out[0][279]};
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
            ag_v<=0;
            result_slots=0;
            if(rr_local)begin
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
                x=pin[d];
                tag=x[270:268];src=x[276:275];dst=x[274:273];
                kind=x[278:277];ttl=x[272:271];
                if(x[279]!=rx_slot[d])fault<=1;
                if(rx_slot[d])begin
                    if(kind!=rx_kind[d*2+:2] || src!=rx_src[d*2+:2] ||
                       tag!=rx_tag[d*3+:3] || (kind!=1 && kind!=2 && !(AG!=0 && kind==3)) ||
                       x[267:256]!=0)fault<=1;
                    if(kind!=3 && !active[tag])fault<=1;
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
                        rr_v<=1;
                        if(rr_local || |(result_slots & ~(2'b1<<d)))fault<=1;
                    end
                    if(AG!=0 && kind==3)begin
                        // GATHER arrival: publish on this direction's port; no tag state.
                        if(ttl==0 || src==qid)fault<=1;
                        ag_v[d]<=1;
                    end
                    if((kind==1 && dst!=qid) || ((kind==2 || kind==3) && ttl>1))begin
                        if(!tx_forward[d])fault<=1;
                    end else if(tx_forward[d])fault<=1;
                end
                if(tx_forward[d])begin
                    if(!rx_slot[d] || !x[279])fault<=1;
                end
                if(tx_inject[d])begin
                    if(tx_forward[d])fault<=1;
                    if(tx_acc ? (!acc_v[tx_tag] || pending[tx_tag]) : !local_v[tx_tag])fault<=1;
                    if(tx_result && (!tx_acc || tx_dst!=qid))fault<=1;
                    if(gath && (tx_result || tx_ttl[d*2+:2]==0))fault<=1;
                end
            end
            if(|tx_inject)begin
                // Copies sent simultaneously in both directions are compiler-
                // reserved, with the same payload. No runtime multicast arbiter.
                // A GATHER from local state ends the tag's lifetime; one from acc keeps
                // acc_v so the local publication (rr_local) can follow, as a RESULT does.
                if(!tx_acc)begin local_v[tx_tag]<=0;if(gath)active[tx_tag]<=0;end
                else if(!tx_result && !gath)acc_v[tx_tag]<=0;
            end
        end
    end
endmodule

// Ring stop: wires only around the control root, 8 CLOSED state-capture lanes and 8 add lanes.
module ot_hgi_coll_ring_ag #(
    parameter integer NT=8, LAT=8, SPLIT_CLOCKS=0, AG=1,
    parameter integer MUT_CARRY=0, MUT_TAG=0, MUT_TTL=0, MUT_SRC=0
)(
    input wire clk, rst_n, clk_ctl,
    input wire [7:0] clk_state, clk_add,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output wire [279:0] cw_o, ccw_o,
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
    input wire tx_gather,
    input wire [3:0] tx_ttl,
    input wire [1:0] rx_slot,
    input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag,
    input wire rr_local,
    input wire [2:0] rr_local_tag,
    output wire rr_v,
    output wire [2:0] rr_tag,
    output wire [255:0] rr_d,
    output wire [1:0] ag_v,
    output wire [3:0] ag_src,
    output wire [5:0] ag_tag,
    output wire [511:0] ag_d,
    output wire fault
);
    wire [279:0] pin0,pin1;wire [1:0] carry_write;wire acc_we;wire [2:0] acc_tag;
    wire [255:0] rhs_add,carry_add,state_tx,acc_rr,ay;wire [7:0] av;
    wire [255:0] aa = MUT_CARRY ? 256'b0 : carry_add;
    ot_hgi_coll_ring_ag_ctl #(.NT(NT),.LAT(LAT),.AG(AG),.MUT_TAG(MUT_TAG),.MUT_TTL(MUT_TTL),.MUT_SRC(MUT_SRC)) u_ctl(
        .clk(SPLIT_CLOCKS?clk_ctl:clk),.rst_n(rst_n),.qid(qid),.cw_i(cw_i),.ccw_i(ccw_i),.cw_o(cw_o),.ccw_o(ccw_o),
        .lp_we(lp_we),.lp_tag(lp_tag),
        .state_read_add(state_read_add),.state_read_tx(state_read_tx),.state_read_rr(state_read_rr),
        .state_add_tag(state_add_tag),.state_tx_tag(state_tx_tag),.state_rr_tag(state_rr_tag),
        .state_add_src(state_add_src),.state_add_rhs_acc(state_add_rhs_acc),.state_tx_acc(state_tx_acc),
        .add_v(add_v),.add_tag(add_tag),.add_src(add_src),.add_rhs_acc(add_rhs_acc),
        .tx_inject(tx_inject),.tx_forward(tx_forward),.tx_tag(tx_tag),.tx_dst(tx_dst),.tx_result(tx_result),.tx_acc(tx_acc),
        .tx_gather(tx_gather),.tx_ttl(tx_ttl),.rx_slot(rx_slot),.rx_kind(rx_kind),.rx_src(rx_src),.rx_tag(rx_tag),
        .rr_local(rr_local),.rr_local_tag(rr_local_tag),
        .pin0_q(pin0),.pin1_q(pin1),.carry_write(carry_write),.acc_we(acc_we),.acc_tag(acc_tag),
        .state_tx(state_tx),.acc_rr(acc_rr),.av(av),
        .rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.ag_v(ag_v),.ag_src(ag_src),.ag_tag(ag_tag),.ag_d(ag_d),.fault(fault));
    for(genvar l=0;l<8;l=l+1)begin:g_lane
        ot_hgi_coll_pring_static_state_capture_lane u_state(
            .clk(SPLIT_CLOCKS?clk_state[l]:clk),
            .lp_we(lp_we),.lp_tag(lp_tag),.lp_data(lp_data[l*32+:32]),
            .acc_we(acc_we),.acc_tag(acc_tag),.acc_data(ay[l*32+:32]),
            .carry_we(carry_write),.carry0_tag(pin0[270:268]),.carry0_src(pin0[276:275]),
            .carry1_tag(pin1[270:268]),.carry1_src(pin1[276:275]),
            .carry0_data(pin0[l*32+:32]),.carry1_data(pin1[l*32+:32]),
            .read_add(state_read_add),.read_tx(state_read_tx),.read_rr(state_read_rr),
            .read_rhs_acc(state_add_rhs_acc),.read_tx_acc(state_tx_acc),
            .add_tag(state_add_tag),.add_src(state_add_src),.tx_tag(state_tx_tag),.rr_tag(state_rr_tag),
            .rhs_add(rhs_add[l*32+:32]),.carry_add(carry_add[l*32+:32]),
            .tx_data(state_tx[l*32+:32]),.acc_rr(acc_rr[l*32+:32]));
        ot_hgi_coll_pring_static_add_lane #(.LAT(LAT)) u_add(
            .clk(SPLIT_CLOCKS?clk_add[l]:clk),.rst_n(rst_n),.valid_in(add_v),
            .a(aa[l*32+:32]),.b(rhs_add[l*32+:32]),.y(ay[l*32+:32]),.valid_out(av[l]));
    end
endmodule
`default_nettype wire
