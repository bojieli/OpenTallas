`timescale 1ns/1ps
`default_nettype none
// ELEM-GAPS/HBMN1 (10-18): NATIVE ring all-gather control root ot_hgi_coll_ring_ag_ctln + stop ot_hgi_coll_ring_ag_n.
// The CLOSED ot_hgi_coll_ring_ag_ctl (rc1-2d4d79dd8) fails the die native rule: command inputs reach the fault /
// state / flit logic before any flop (capture up to 483 > 190 ps on 329 pins), pin0_q/pin1_q leave from the ring pin
// registers that also feed the whole stop (launch 360 > 220 on 460 pins), carry_write = rx_slot & pin is a pin-to-pin
// combinational arc, rst_n is a raw async fanout.  This wrapper keeps the closed control body UNCHANGED (u_core, so its
// benches stay the proof of the protocol) and moves every boundary onto flops:
//   * every command input is a pure pin flop (compiler LEAD 1: issue one edge before the v1 effect edge);
//   * the tx-read group (state_read_tx, state_tx_tag, state_tx_acc) has LEAD 2: its pin flop drives the state lanes one
//     edge early, so the lanes' tx_data is pin-flopped here (state_tx capture) and the inject edge is unchanged;
//     legality: the tx tag's lane state must be stable from inject-3 (v1: inject-2) -> two extra fault checks at the
//     lane read edge (lp write / acc write of the same tag in that edge);
//   * the state / add lanes take their commands from dedicated registered copies (cmd_*_o), at the v1 lane timing;
//   * pin0_q / pin1_q / acc_we / acc_tag are dedicated output flops (same values as v1, no internal fanout);
//   * carry_write is computed one edge ahead from rx_slot (lead input) and the arriving ring word (r5b: AND2 of two flops);
//   r2 (10-18): pin0_q/pin1_q copies are ot_hgi_coll_ring_cp_ff leaves (keep_hierarchy): in n1 yosys opt_merge folded
//     each copy into the core's pin_p register of the same D, so pin0_q/pin1_q again left from the shared stop register
//     (CTS probe launch 286).  carry_write / rx_slot are split per ring direction (carry_write0/rx_slot0 = cw at the NW
//     corner beside cw_i's kind bits, carry_write1/rx_slot1 = ccw at the NE corner) -- n1 capture 254 was rx_slot on
//     the S face -> carry flop on the N face.  Same values, same edges as n1 (port split only; the stop _n is unchanged).
//   r5 (10-18): acc_rr (lane rr read data) is pin-flopped (acc_rr_q): r4 probe capture acc_rr 201 ps = acc_rr pin -> 4 mux
//     levels of the closed core -> rr_d.  The rr-read group (state_read_rr, state_rr_tag) gets LEAD 2 like the tx-read group:
//     its pin flop drives the lanes one edge early (cmd_read_rr_o/cmd_rr_tag_o from the raw pin), acc_rr_q re-aligns the data,
//     so rr_d is unchanged in value and edge.  Legality: no acc write of the rr tag at the lane read edge (rr_local-3) ->
//     fault check hz_rr.  carry_write0's ring-bit inputs: rx_slot0 moves to the W face beside cw_i[278:273] (kit only).
//   * av (add lanes' valid_out) is pin-flopped; its check moves one edge later; fault is an output flop (+1 edge);
//   * rst_n drives only ot_rst_relay (release +3 edges); rn_o resets the add lanes with the same release.
// Ring ports cw_i/ccw_i/cw_o/ccw_o, lp_data, rr_*, ag_* keep their v1 absolute timing (hop = 2 edges).
// Compiler record: results/rtl/eg_hbmn1_1018/ring_ag_n_latency_record.json.
module ot_hgi_coll_ring_ag_ctln #(
    parameter integer NT=8, LAT=8, AG=1,
    parameter integer MUT_TAG=0, MUT_TTL=0, MUT_SRC=0,
    parameter integer MUT_TXLEAD=0, MUT_CW=0, MUT_HZ=0, MUT_RRLEAD=0
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
    input wire rx_slot0, rx_slot1,
    input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag,
    input wire rr_local,
    input wire [2:0] rr_local_tag,
    // lane faces (state-capture lanes + add lanes)
    output wire [279:0] pin0_q, pin1_q,
    output wire carry_write0, carry_write1,
    output wire acc_we,  // = acc_we_o
    output wire [2:0] acc_tag,
    input wire [255:0] state_tx, acc_rr,
    input wire [7:0] av,
    // registered lane command copies (v1 lane timing)
    output reg cmd_lp_we_o,
    output reg [2:0] cmd_lp_tag_o,
    output reg cmd_read_add_o, cmd_read_tx_o, cmd_read_rr_o,
    output reg [2:0] cmd_add_tag_o, cmd_tx_tag_o, cmd_rr_tag_o,
    output reg [1:0] cmd_add_src_o,
    output reg cmd_rhs_acc_o, cmd_tx_acc_o,
    output reg cmd_add_v_o,
    output wire rn_o,
    output wire rr_v,
    output wire [2:0] rr_tag,
    output wire [255:0] rr_d,
    output wire [1:0] ag_v,
    output wire [3:0] ag_src,
    output wire [5:0] ag_tag,
    output wire [511:0] ag_d,
    output reg fault
);
    wire [1:0] rn;
    ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
    assign rn_o = rn[1];
    // ---- pin flops (pure; no reset: every one is qualified downstream by the reset control state) ----
    (* keep = "true" *) reg [1:0] qid_q;
    (* keep = "true" *) reg lp_we_q; (* keep = "true" *) reg [2:0] lp_tag_q;
    (* keep = "true" *) reg rd_add_q; (* keep = "true" *) reg [2:0] add_tag_rq;
    (* keep = "true" *) reg rd_rr_l; (* keep = "true" *) reg [2:0] rr_tag_l;                                 // rr lane frame (lead 2)
    reg rd_rr_q; reg [2:0] rr_tag_rq;                                                                          // core frame
    (* keep = "true" *) reg [1:0] add_src_rq; (* keep = "true" *) reg add_rhs_rq;
    (* keep = "true" *) reg rd_tx_l; (* keep = "true" *) reg [2:0] tx_tag_l; (* keep = "true" *) reg tx_acc_l; // lane frame (lead 2)
    reg rd_tx_q; reg [2:0] tx_tag_rq; reg tx_acc_rq;                                                            // core frame
    (* keep = "true" *) reg add_v_q; (* keep = "true" *) reg [2:0] add_tag_q; (* keep = "true" *) reg [1:0] add_src_q;
    (* keep = "true" *) reg add_rhs_q;
    (* keep = "true" *) reg [1:0] inj_q, fwd_q; (* keep = "true" *) reg [2:0] txt_q; (* keep = "true" *) reg [1:0] dst_q;
    (* keep = "true" *) reg res_q, txacc_q, gath_q; (* keep = "true" *) reg [3:0] ttl_q;
    (* keep = "true" *) reg [1:0] rx_q; (* keep = "true" *) reg [3:0] kind_q, src_q; (* keep = "true" *) reg [5:0] rxtag_q;
    (* keep = "true" *) reg rrl_q; (* keep = "true" *) reg [2:0] rrlt_q;
    (* keep = "true" *) reg [255:0] st_q;
    (* keep = "true" *) reg [255:0] acc_rr_q;
    (* keep = "true" *) reg [7:0] av_q;
    // r5b: carry_write = (slot & kind 1) flop AND (dst == qid) flop; r5 probe: cw_i[273] -> in-buf 66 + XOR 43 + AND5 60 ps
    // into one flop (capture 213, pure logic, 6 um of wire).  Two flops halve the capture logic; the AND2 is on the launch side.
    (* keep = "true" *) reg cw_a0, cw_b0, cw_a1, cw_b1;
    assign carry_write0 = cw_a0 & cw_b0;
    assign carry_write1 = cw_a1 & cw_b1;
    always @(posedge clk) begin
        qid_q<=qid;
        lp_we_q<=lp_we;lp_tag_q<=lp_tag;
        rd_add_q<=state_read_add;add_tag_rq<=state_add_tag;
        rd_rr_l<=state_read_rr;rr_tag_l<=state_rr_tag;rd_rr_q<=rd_rr_l;rr_tag_rq<=rr_tag_l;
        add_src_rq<=state_add_src;add_rhs_rq<=state_add_rhs_acc;
        rd_tx_l<=state_read_tx;tx_tag_l<=state_tx_tag;tx_acc_l<=state_tx_acc;
        rd_tx_q<=rd_tx_l;tx_tag_rq<=tx_tag_l;tx_acc_rq<=tx_acc_l;
        add_v_q<=add_v;add_tag_q<=add_tag;add_src_q<=add_src;add_rhs_q<=add_rhs_acc;
        inj_q<=tx_inject;fwd_q<=tx_forward;txt_q<=tx_tag;dst_q<=tx_dst;res_q<=tx_result;txacc_q<=tx_acc;gath_q<=tx_gather;ttl_q<=tx_ttl;
        rx_q<={rx_slot1,rx_slot0};kind_q<=rx_kind;src_q<=rx_src;rxtag_q<=rx_tag;
        rrl_q<=rr_local;rrlt_q<=rr_local_tag;
        st_q<=state_tx;
        acc_rr_q<=acc_rr;
        av_q<=av;
        // dedicated output copies: lane commands (lane frame), ring pin words, carry write (one edge ahead)
        cmd_lp_we_o<=lp_we;cmd_lp_tag_o<=lp_tag;
        cmd_read_add_o<=state_read_add;cmd_add_tag_o<=state_add_tag;
        if(MUT_RRLEAD!=0)begin cmd_read_rr_o<=rd_rr_l;cmd_rr_tag_o<=rr_tag_l;end
        else begin cmd_read_rr_o<=state_read_rr;cmd_rr_tag_o<=state_rr_tag;end
        cmd_add_src_o<=state_add_src;cmd_rhs_acc_o<=state_add_rhs_acc;
        if(MUT_TXLEAD!=0)begin cmd_read_tx_o<=rd_tx_l;cmd_tx_tag_o<=tx_tag_l;cmd_tx_acc_o<=tx_acc_l;end
        else begin cmd_read_tx_o<=state_read_tx;cmd_tx_tag_o<=state_tx_tag;cmd_tx_acc_o<=state_tx_acc;end
        cmd_add_v_o<=add_v;
        if(MUT_CW!=0)begin
            cw_a0<=rx_q[0] && pin0_q[278:277]==1; cw_b0<=pin0_q[274:273]==qid_q;
            cw_a1<=rx_q[1] && pin1_q[278:277]==1; cw_b1<=pin1_q[274:273]==qid_q;
        end else begin
            cw_a0<=rx_slot0 && cw_i[278:277]==1; cw_b0<=cw_i[274:273]==qid_q;
            cw_a1<=rx_slot1 && ccw_i[278:277]==1; cw_b1<=ccw_i[274:273]==qid_q;
        end
    end
    // ring pin-word copies: one keep_hierarchy leaf per bit (never merged with the core's pin_p register)
    for(genvar b=0;b<280;b=b+1)begin:g_cp
        ot_hgi_coll_ring_cp_ff u_p0(.clk(clk),.d(cw_i[b]),.q(pin0_q[b]));
        ot_hgi_coll_ring_cp_ff u_p1(.clk(clk),.d(ccw_i[b]),.q(pin1_q[b]));
    end
    // acc write timeline (dedicated copy of the core's pv/pt shift: v1 acc_we/acc_tag values)
    (* keep = "true" *) reg [LAT-1:0] aw;
    wire acc_we_o; assign acc_we = acc_we_o;
    (* keep = "true" *) reg [2:0] at [0:LAT-1];
    always @(posedge clk or negedge rn[1]) begin
        if(!rn[1])aw<=0;else aw<={aw[LAT-2:0],add_v_q};
    end
    always @(posedge clk) begin at[0]<=add_tag_q;for(integer i=1;i<LAT;i=i+1)at[i]<=at[i-1];end
    // r5b: acc_we pin = a dedicated copy flop of aw[LAT-1] (r5b probe: launch 233, the shared flop also feeds hz/hz_rr/aw_d)
    wire aw_last=aw[LAT-1];
    ot_hgi_coll_ring_cp_ff u_awo(.clk(clk),.d(aw[LAT-2]),.q(acc_we_o));
    assign acc_tag=at[LAT-1];
    // ---- unchanged closed control body in the core frame ----
    wire core_fault;wire [279:0] p0_unused,p1_unused;wire [1:0] cw_unused;wire aw_unused;wire [2:0] at_unused;
    ot_hgi_coll_ring_ag_ctl #(.NT(NT),.LAT(LAT),.AG(AG),.MUT_TAG(MUT_TAG),.MUT_TTL(MUT_TTL),.MUT_SRC(MUT_SRC)) u_core(
        .clk(clk),.rst_n(rn[0]),.qid(qid_q),.cw_i(cw_i),.ccw_i(ccw_i),.cw_o(cw_o),.ccw_o(ccw_o),
        .lp_we(lp_we_q),.lp_tag(lp_tag_q),
        .state_read_add(rd_add_q),.state_read_tx(rd_tx_q),.state_read_rr(rd_rr_q),
        .state_add_tag(add_tag_rq),.state_tx_tag(tx_tag_rq),.state_rr_tag(rr_tag_rq),
        .state_add_src(add_src_rq),.state_add_rhs_acc(add_rhs_rq),.state_tx_acc(tx_acc_rq),
        .add_v(add_v_q),.add_tag(add_tag_q),.add_src(add_src_q),.add_rhs_acc(add_rhs_q),
        .tx_inject(inj_q),.tx_forward(fwd_q),.tx_tag(txt_q),.tx_dst(dst_q),.tx_result(res_q),.tx_acc(txacc_q),
        .tx_gather(gath_q),.tx_ttl(ttl_q),.rx_slot(rx_q),.rx_kind(kind_q),.rx_src(src_q),.rx_tag(rxtag_q),
        .rr_local(rrl_q),.rr_local_tag(rrlt_q),
        .pin0_q(p0_unused),.pin1_q(p1_unused),.carry_write(cw_unused),.acc_we(aw_unused),.acc_tag(at_unused),
        .state_tx(st_q),.acc_rr(acc_rr_q),.av({8{aw_unused}}),
        .rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.ag_v(ag_v),.ag_src(ag_src),.ag_tag(ag_tag),.ag_d(ag_d),.fault(core_fault));
    // ---- boundary checks moved here (fault only; never gate or repair timing) ----
    reg aw_d;
    wire hz = MUT_HZ!=1 && rd_tx_l && (tx_acc_l ? (aw_last && acc_tag==tx_tag_l) : (lp_we_q && lp_tag_q==tx_tag_l));
    wire hz_rr = MUT_HZ!=2 && rd_rr_l && aw_last && acc_tag==rr_tag_l;   // r5: acc write of the rr tag at the lane read edge
    always @(posedge clk or negedge rn[1]) begin
        if(!rn[1])begin fault<=0;aw_d<=0;end
        else begin
            aw_d<=aw_last;
            if(core_fault || hz || hz_rr || av_q!={8{aw_d}})fault<=1;
        end
    end
endmodule

// Ring stop on the native control root: wires only around ctln + the 8 CLOSED state-capture lanes + 8 add lanes.
// Port list = ot_hgi_coll_ring_ag; timing per the header (commands lead 1, tx-read and rr-read groups lead 2, rest unchanged).
module ot_hgi_coll_ring_ag_n #(
    parameter integer NT=8, LAT=8, SPLIT_CLOCKS=0, AG=1,
    parameter integer MUT_CARRY=0, MUT_TAG=0, MUT_TTL=0, MUT_SRC=0,
    parameter integer MUT_TXLEAD=0, MUT_CW=0, MUT_HZ=0, MUT_RRLEAD=0
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
    wire c_lp_we,c_rd_add,c_rd_tx,c_rd_rr,c_rhs,c_txacc,c_add_v,rn;
    wire [2:0] c_lp_tag,c_add_tag,c_tx_tag,c_rr_tag;wire [1:0] c_add_src;
    ot_hgi_coll_ring_ag_ctln #(.NT(NT),.LAT(LAT),.AG(AG),.MUT_TAG(MUT_TAG),.MUT_TTL(MUT_TTL),.MUT_SRC(MUT_SRC),
        .MUT_TXLEAD(MUT_TXLEAD),.MUT_CW(MUT_CW),.MUT_HZ(MUT_HZ),.MUT_RRLEAD(MUT_RRLEAD)) u_ctl(
        .clk(SPLIT_CLOCKS?clk_ctl:clk),.rst_n(rst_n),.qid(qid),.cw_i(cw_i),.ccw_i(ccw_i),.cw_o(cw_o),.ccw_o(ccw_o),
        .lp_we(lp_we),.lp_tag(lp_tag),
        .state_read_add(state_read_add),.state_read_tx(state_read_tx),.state_read_rr(state_read_rr),
        .state_add_tag(state_add_tag),.state_tx_tag(state_tx_tag),.state_rr_tag(state_rr_tag),
        .state_add_src(state_add_src),.state_add_rhs_acc(state_add_rhs_acc),.state_tx_acc(state_tx_acc),
        .add_v(add_v),.add_tag(add_tag),.add_src(add_src),.add_rhs_acc(add_rhs_acc),
        .tx_inject(tx_inject),.tx_forward(tx_forward),.tx_tag(tx_tag),.tx_dst(tx_dst),.tx_result(tx_result),.tx_acc(tx_acc),
        .tx_gather(tx_gather),.tx_ttl(tx_ttl),.rx_slot0(rx_slot[0]),.rx_slot1(rx_slot[1]),.rx_kind(rx_kind),.rx_src(rx_src),.rx_tag(rx_tag),
        .rr_local(rr_local),.rr_local_tag(rr_local_tag),
        .pin0_q(pin0),.pin1_q(pin1),.carry_write0(carry_write[0]),.carry_write1(carry_write[1]),.acc_we(acc_we),.acc_tag(acc_tag),
        .state_tx(state_tx),.acc_rr(acc_rr),.av(av),
        .cmd_lp_we_o(c_lp_we),.cmd_lp_tag_o(c_lp_tag),.cmd_read_add_o(c_rd_add),.cmd_read_tx_o(c_rd_tx),.cmd_read_rr_o(c_rd_rr),
        .cmd_add_tag_o(c_add_tag),.cmd_tx_tag_o(c_tx_tag),.cmd_rr_tag_o(c_rr_tag),.cmd_add_src_o(c_add_src),
        .cmd_rhs_acc_o(c_rhs),.cmd_tx_acc_o(c_txacc),.cmd_add_v_o(c_add_v),.rn_o(rn),
        .rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.ag_v(ag_v),.ag_src(ag_src),.ag_tag(ag_tag),.ag_d(ag_d),.fault(fault));
    for(genvar l=0;l<8;l=l+1)begin:g_lane
        ot_hgi_coll_pring_static_state_capture_lane u_state(
            .clk(SPLIT_CLOCKS?clk_state[l]:clk),
            .lp_we(c_lp_we),.lp_tag(c_lp_tag),.lp_data(lp_data[l*32+:32]),
            .acc_we(acc_we),.acc_tag(acc_tag),.acc_data(ay[l*32+:32]),
            .carry_we(carry_write),.carry0_tag(pin0[270:268]),.carry0_src(pin0[276:275]),
            .carry1_tag(pin1[270:268]),.carry1_src(pin1[276:275]),
            .carry0_data(pin0[l*32+:32]),.carry1_data(pin1[l*32+:32]),
            .read_add(c_rd_add),.read_tx(c_rd_tx),.read_rr(c_rd_rr),
            .read_rhs_acc(c_rhs),.read_tx_acc(c_txacc),
            .add_tag(c_add_tag),.add_src(c_add_src),.tx_tag(c_tx_tag),.rr_tag(c_rr_tag),
            .rhs_add(rhs_add[l*32+:32]),.carry_add(carry_add[l*32+:32]),
            .tx_data(state_tx[l*32+:32]),.acc_rr(acc_rr[l*32+:32]));
        ot_hgi_coll_pring_static_add_lane #(.LAT(LAT)) u_add(
            .clk(SPLIT_CLOCKS?clk_add[l]:clk),.rst_n(rn),.valid_in(c_add_v),
            .a(aa[l*32+:32]),.b(rhs_add[l*32+:32]),.y(ay[l*32+:32]),.valid_out(av[l]));
    end
endmodule

// One ring-word copy flop (r2).  keep_hierarchy: opt_merge cannot fold it into another register with the same D (the
// core's pin_p); not parameterised, so the module name survives elaboration.
(* keep_hierarchy *)
module ot_hgi_coll_ring_cp_ff(input wire clk, input wire d, output reg q);
    always @(posedge clk) q<=d;
endmodule
`default_nettype wire
