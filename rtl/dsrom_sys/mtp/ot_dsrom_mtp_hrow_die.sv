// dsfd_mtp_hrow on the S81 die (coordinator decision 2026-10-13 07:55): the four hardened rev-5 tiles (ing x 3, hub x 1,
// cbe x 15, cbw x 15: rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_tiles.sv, NOT edited: the closed routes stay bound to it) placed
// by the die, with die relays.  This is dsfd_mtp_hrow_tc plus UT registered relay stages on the U-turn hop of every
// part's chain (bank 4 east end -> bank 5: measured 336..509 um for 2,079 b; with the relay every hop <= 500 um).
//
// Chain order of one part p (three parts, identical):
//   ing_p --t_wc 1,039 b, WD = 2 CQ + 1 - WK = 0 relays (the head bank abuts its ing tile)--> cbe bank 0 -> 1 -> 2 -> 3 -> 4
//        (eastward, tile to tile, no relay) --UT = 1 relay: w 1,039 + r 15 + d 1,025 = 2,079 b--> cbw bank 5 -> 6 -> 7 -> 8 -> 9
//        (westward, tile to tile, no relay) --d 1,025 b, P = 2 relays--> hub f_pr<p>
//   ing_p --t_ev 21 b + t_flt 2 b, CQ - 1 = 2 relays--> hub;   hub t_rc<p> 15 b --CQ = 3 relays--> cbe bank 0 (f_r)
// Die relay flops: 3 x (21 x 2 + 2 x 2 + 15 x 3 + 1,025 x 2 + 2,079 x UT) = 6,423 + 6,237 = 12,660 at UT = 1 (+ one reset
// synchroniser).  The U-turn relay delays w, r and d by the same UT edges for banks 5..9, so the write-before-read order
// at every bank is the one of tc; a row's result reaches the hub UT edges later for every bank (bank < 5: d crosses the
// relay; bank >= 5: r does), equal for the three parts; the hub takes the result by its valid bit (no latency constant).
// Gate: tools/mtp_hrow_gate.py --tiles --uturn (bench tb_mtp_hrow.sv, define OT_HROW_DIE).
module dsfd_mtp_hrow_td #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16,
    parameter integer AW = 24, parameter integer FWD_P = 9, parameter integer RET_P = 9,
    parameter integer FWD_Q = 6, parameter integer RET_Q = 6,
    parameter integer CQ = 3, parameter integer WK = 7, parameter integer P = 2,
    parameter integer HARD_RELAYS = 0,  // opt-in fixed masters: preserves every original relay edge/reset bit
    parameter integer DISTRIBUTED_RST = 0, // default-off local two-edge release; global ck/rst delivery still required
    parameter integer UT = 1,        // die relay stages on the U-turn hop (cbe bank 4 -> cbw bank 5), w / r / d alike
    parameter integer HALF_BANKS = 0 // opt-in (S-ELEM-PQ/HROW 10-16): every bank = dsfd_mtp_hrow_cbp, two dsfd_mtp_hrow_cbh half
                                     // tiles (ot_dsrom_mtp_hrow_cbh.sv; 512 data bits each, same edges), replacing cbe / cbw
) (
    input  wire           ck, rst,
    input  wire [514:0]   f_hp0, f_hp1, f_hp2,
    output wire [2:0]     t_hpg,
    input  wire [AW:0]    f_vrq,
    output wire           t_vrq,
    output wire [1024:0]  t_vrs,
    input  wire [USER_W:0] f_clr,
    output wire [2:0]     t_flt
`ifdef OT_HROW_RESET_ACK
    ,output wire [39:0] rst_ack_leaf,
    output wire [3*(UT+2*CQ-1+P)-1:0] rst_ack_relay,
    output wire [3*(UT+2*CQ-1+P)-1:0] rst_ack_conditioner
`endif
);
    localparam integer ACK_PER_PART = UT+2*CQ-1+P;
    localparam integer WD = 2 * CQ + 1 - WK;
    initial if (CQ < 1 || WD < 0) $fatal(1, "hrow_td: CQ >= 1 and WK <= 2 CQ + 1");
    initial if (DISTRIBUTED_RST != 0 && HARD_RELAYS == 0) $fatal(1, "distributed reset requires fixed hard relays");
`ifdef OT_HROW_RESET_ACK
    // Candidate ABI is sized for the actual selected fixed/distributed WD0 graph.
    initial if(!HARD_RELAYS || !DISTRIBUTED_RST || WD!=0) $fatal(1,"HROW ACK requires fixed distributed WD0 graph");
`endif
    wire rn;
    generate if (HARD_RELAYS != 0 && DISTRIBUTED_RST == 0) begin : g_hrst
        dsfd_die_rstsync u_rs (.ck(ck), .rst(rst), .rn(rn));
    end else if (HARD_RELAYS == 0) begin : g_rst
        ot_dsrom_mtp_rstsync u_rs (.clk(ck), .rst_n_async(rst), .rst_n(rn));
    end else begin : g_drst
        // No central registered rn fanout: each fixed relay samples the same original rst and ck.
        // Identical two-flop conditioners release on the same second edge in the ideal-clock model.
        assign rn = 1'b0;
    end endgenerate
    wire [514:0] fin [0:2];
    assign fin[0] = f_hp0; assign fin[1] = f_hp1; assign fin[2] = f_hp2;
    wire [20:0] ev [0:2]; wire [20:0] evh [0:2]; wire [1:0] ifl [0:2]; wire [1:0] iflh [0:2];
    wire [14:0] rc [0:2]; wire [1024:0] pp [0:2]; wire [1024:0] pph [0:2];
    genvar gp, gk;
    generate for (gp = 0; gp < 3; gp = gp + 1) begin : g_part
        wire [1038:0] wc; wire [1038:0] cw [0:10]; wire [14:0] cr [0:10]; wire [1024:0] cd [0:10];
        wire [1038:0] uw; wire [14:0] ur; wire [1024:0] ud;          // bank 4's chain outputs, before the U-turn relays
        if (HARD_RELAYS != 0) begin : g_hut
            wire [2078:0] q [0:UT];
            assign q[0]={ud,ur,uw};
            for(genvar ri=0; ri<UT; ri=ri+1) begin : g_r
                wire lrn;
                if (DISTRIBUTED_RST != 0) begin : g_rst
                    dsfd_die_rstsync
`ifdef OT_HROW_RESET_ACK
                    #(.RESET_ACK(1))
`endif
                    u_rs(.ck(ck),.rst(rst),.rn(lrn)
`ifdef OT_HROW_RESET_ACK
                        ,.rst_ack(rst_ack_conditioner[gp*ACK_PER_PART+ri])
`endif
);
                end else assign lrn=rn;
                dsfd_hrow_r2079 u_r(.ck(ck),.rn(lrn),.i(q[ri]),.o(q[ri+1])
`ifdef OT_HROW_RESET_ACK
                    ,.reset_epoch_n(rst),.rst_ack(rst_ack_relay[gp*ACK_PER_PART+ri])
`endif
);
            end
            assign {cd[5],cr[5],cw[5]}=q[UT];
        end else begin : g_ut
        ot_dsrom_mtp_hrow_rly #(.W(1039), .N(UT)) u_uw (.clk(ck), .rst_n(rn), .i(uw), .o(cw[5]));
        ot_dsrom_mtp_hrow_rly #(.W(15), .N(UT)) u_ur (.clk(ck), .rst_n(rn), .i(ur), .o(cr[5]));
        ot_dsrom_mtp_hrow_rly #(.W(1025), .N(UT)) u_ud (.clk(ck), .rst_n(rn), .i(ud), .o(cd[5]));
        end
        dsfd_mtp_hrow_ing #(.NW(NW), .USER_W(USER_W), .MAXU(MAXU), .RS(RS), .FWD_P(FWD_P), .RET_P(RET_P), .WK(WK)) u_ig (
            .ck(ck), .rst(rst), .f_hp(fin[gp]), .t_hpg(t_hpg[gp]), .f_pid(gp[1:0]), .t_wc(wc), .t_ev(ev[gp]), .t_flt(ifl[gp])
`ifdef OT_HROW_RESET_ACK
            ,.rst_ack(rst_ack_leaf[gp*11])
`endif
);
        if (HARD_RELAYS != 0) begin : g_hev
            wire [22:0] eq[0:CQ-1]; wire [14:0] rq[0:CQ];
            assign eq[0]={ifl[gp],ev[gp]}; assign rq[0]=rc[gp];
            for(genvar ri=0; ri<CQ-1; ri=ri+1) begin : g_ev
                wire lrn;
                if (DISTRIBUTED_RST != 0) begin : g_rst
                    dsfd_die_rstsync
`ifdef OT_HROW_RESET_ACK
                    #(.RESET_ACK(1))
`endif
                    u_rs(.ck(ck),.rst(rst),.rn(lrn)
`ifdef OT_HROW_RESET_ACK
                        ,.rst_ack(rst_ack_conditioner[gp*ACK_PER_PART+UT+ri])
`endif
);
                end else assign lrn=rn;
                dsfd_hrow_r23 u_r(.ck(ck),.rn(lrn),.i(eq[ri]),.o(eq[ri+1])
`ifdef OT_HROW_RESET_ACK
                    ,.reset_epoch_n(rst),.rst_ack(rst_ack_relay[gp*ACK_PER_PART+UT+ri])
`endif
);
            end
            for(genvar ri=0; ri<CQ; ri=ri+1) begin : g_rc
                wire lrn;
                if (DISTRIBUTED_RST != 0) begin : g_rst
                    dsfd_die_rstsync
`ifdef OT_HROW_RESET_ACK
                    #(.RESET_ACK(1))
`endif
                    u_rs(.ck(ck),.rst(rst),.rn(lrn)
`ifdef OT_HROW_RESET_ACK
                        ,.rst_ack(rst_ack_conditioner[gp*ACK_PER_PART+UT+CQ-1+ri])
`endif
);
                end else assign lrn=rn;
                dsfd_hrow_r15 u_r(.ck(ck),.rn(lrn),.i(rq[ri]),.o(rq[ri+1])
`ifdef OT_HROW_RESET_ACK
                    ,.reset_epoch_n(rst),.rst_ack(rst_ack_relay[gp*ACK_PER_PART+UT+CQ-1+ri])
`endif
);
            end
            assign {iflh[gp],evh[gp]}=eq[CQ-1]; assign cr[0]=rq[CQ];
            // Default WD0 has no state. Other parameter sets retain their exact existing write-delay line.
            wire wrn;
            if (DISTRIBUTED_RST != 0 && WD > 0) begin : g_wdrst
                dsfd_die_rstsync
`ifdef OT_HROW_RESET_ACK
                    #(.RESET_ACK(1))
`endif
                    u_rs(.ck(ck),.rst(rst),.rn(wrn));
            end else assign wrn=rn;
            ot_dsrom_mtp_hrow_rly #(.W(1039),.N(WD)) u_wd(.clk(ck),.rst_n(wrn),.i(wc),.o(cw[0]));
        end else begin : g_ev
        ot_dsrom_mtp_hrow_rly #(.W(21), .N(CQ - 1)) u_ev (.clk(ck), .rst_n(rn), .i(ev[gp]), .o(evh[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(2), .N(CQ - 1)) u_if (.clk(ck), .rst_n(rn), .i(ifl[gp]), .o(iflh[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(1039), .N(WD)) u_wd (.clk(ck), .rst_n(rn), .i(wc), .o(cw[0]));
        ot_dsrom_mtp_hrow_rly #(.W(15), .N(CQ)) u_rc (.clk(ck), .rst_n(rn), .i(rc[gp]), .o(cr[0]));
        end
        assign cd[0] = '0;
        if (HALF_BANKS != 0) begin : g_hb
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_c
            wire [1038:0] tw; wire [14:0] tr; wire [1024:0] td;
            dsfd_mtp_hrow_cbp u_b (.ck(ck), .rst(rst), .f_bid(4'(gk)), .f_w(cw[gk]), .t_w(tw), .f_r(cr[gk]), .t_r(tr),
                                   .f_d(cd[gk]), .t_d(td)
`ifdef OT_HROW_RESET_ACK
                                   ,.rst_ack(rst_ack_leaf[gp*11+1+gk])
`endif
);
            if (gk == 4) begin : g_u
                assign uw = tw; assign ur = tr; assign ud = td;
            end else begin : g_n
                assign cw[gk+1] = tw; assign cr[gk+1] = tr; assign cd[gk+1] = td;
            end
        end
        end else begin : g_fb
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_c
            if (gk == 4) begin : g_e
                dsfd_mtp_hrow_cbe u_b (.ck(ck), .rst(rst), .f_bid(4'(gk)), .f_w(cw[gk]), .t_w(uw), .f_r(cr[gk]),
                                       .t_r(ur), .f_d(cd[gk]), .t_d(ud)
`ifdef OT_HROW_RESET_ACK
                                       ,.rst_ack(rst_ack_leaf[gp*11+1+gk])
`endif
);
            end else if (gk < 4) begin : g_e
                dsfd_mtp_hrow_cbe u_b (.ck(ck), .rst(rst), .f_bid(4'(gk)), .f_w(cw[gk]), .t_w(cw[gk+1]), .f_r(cr[gk]),
                                       .t_r(cr[gk+1]), .f_d(cd[gk]), .t_d(cd[gk+1])
`ifdef OT_HROW_RESET_ACK
                                       ,.rst_ack(rst_ack_leaf[gp*11+1+gk])
`endif
);
            end else begin : g_w
                dsfd_mtp_hrow_cbw u_b (.ck(ck), .rst(rst), .f_bid(4'(gk)), .f_w(cw[gk]), .t_w(cw[gk+1]), .f_r(cr[gk]),
                                       .t_r(cr[gk+1]), .f_d(cd[gk]), .t_d(cd[gk+1])
`ifdef OT_HROW_RESET_ACK
                                       ,.rst_ack(rst_ack_leaf[gp*11+1+gk])
`endif
);
            end
        end
        end
        if (HARD_RELAYS != 0) begin : g_hrp
            wire [1024:0] q[0:P]; assign q[0]=cd[10];
            for(genvar ri=0; ri<P; ri=ri+1) begin : g_r
                wire lrn;
                if (DISTRIBUTED_RST != 0) begin : g_rst
                    dsfd_die_rstsync
`ifdef OT_HROW_RESET_ACK
                    #(.RESET_ACK(1))
`endif
                    u_rs(.ck(ck),.rst(rst),.rn(lrn)
`ifdef OT_HROW_RESET_ACK
                        ,.rst_ack(rst_ack_conditioner[gp*ACK_PER_PART+UT+2*CQ-1+ri])
`endif
);
                end else assign lrn=rn;
                dsfd_hrow_r1025 u_r(.ck(ck),.rn(lrn),.i(q[ri]),.o(q[ri+1])
`ifdef OT_HROW_RESET_ACK
                    ,.reset_epoch_n(rst),.rst_ack(rst_ack_relay[gp*ACK_PER_PART+UT+2*CQ-1+ri])
`endif
);
            end
            assign pph[gp]=q[P];
        end else begin : g_rp
        ot_dsrom_mtp_hrow_rly #(.W(1025), .N(P)) u_rp (.clk(ck), .rst_n(rn), .i(cd[10]), .o(pph[gp]));
        end
    end endgenerate
    dsfd_mtp_hrow_hub #(.USER_W(USER_W), .MAXU(MAXU), .RS(RS), .AW(AW), .FWD_Q(FWD_Q), .RET_Q(RET_Q)) u_hub (
        .ck(ck), .rst(rst), .f_vrq(f_vrq), .t_vrq(t_vrq), .t_vrs(t_vrs), .f_clr(f_clr), .t_flt(t_flt),
        .f_ev0(evh[0]), .f_ev1(evh[1]), .f_ev2(evh[2]), .f_if0(iflh[0]), .f_if1(iflh[1]), .f_if2(iflh[2]),
        .t_rc0(rc[0]), .t_rc1(rc[1]), .t_rc2(rc[2]), .f_pr0(pph[0]), .f_pr1(pph[1]), .f_pr2(pph[2])
`ifdef OT_HROW_RESET_ACK
        ,.rst_ack(rst_ack_leaf[39:33])
`endif
);
endmodule
