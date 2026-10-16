`timescale 1ns/1ps
// dsfd_sp_collective (CLAUDE S81-PH, 2026-10-06): the S81 die collective slab, named and ported as the
// tools/dsrom_s81_fulldie.py r9 master WITH the contract's generator changes (f_vm 592 in, ts 3 in, t_vm 2100 out;
// results/rtl/s81_ph_20261006/collective/contract.json; ports physical/s81_ph_views/ports_ph/<die>/dsfd_sp_collective).
//   clocks: die PLL (ot_s81_pll_bb, hard IP) from refclk; pll_stream also clocks this slab; pll_serial / pll_hbm
//           pass through kept buffers.  Resets: ot_s81ph_coll_rstc (por -> lock -> stream, serial, hbm release).
//   links:  8 lanes (W0..W3 = lanes 0..3, E0..E3 = lanes 4..7): rX = the hub meso end block's {fault, live,
//           data 512, valid}; tdX = the 512-b beat, tfX its forwarded clock (= the slab clock, kept buffer; the
//           first station captures on its falling edge as for every r9 start block).
//   every die input is captured in a flop at the pin, every die output is launched from a flop (clock / reset
//   outputs: kept cells / reset flops).
// s81-ctl-1011: the VM-side core tile master (dsfd_coll_cbj with the coll command endpoint, +define+OT_S81PH_COLL_JOB)
`ifndef OT_S81PH_CB_MASTER
`ifdef OT_S81PH_COLL_JOB
`define OT_S81PH_CB_MASTER dsfd_coll_cbj
`else
`define OT_S81PH_CB_MASTER dsfd_coll_cb
`endif
`endif
module dsfd_sp_collective (
    input  wire [0:0]    refclk,
    input  wire [0:0]    por,
    input  wire [591:0]  f_vm,
    input  wire [2:0]    ts,
    input  wire [514:0]  rW0, rW1, rW2, rW3, rE0, rE1, rE2, rE3,
    output wire [0:0]    pll_stream, pll_serial, pll_hbm,
    output wire [0:0]    rst_stream, rst_serial, rst_hbm,
    output wire [2099:0] t_vm,
    output wire [511:0]  tdW0, tdW1, tdW2, tdW3, tdE0, tdE1, tdE2, tdE3,
    output wire [0:0]    tfW0, tfW1, tfW2, tfW3, tfE0, tfE1, tfE2, tfE3
`ifdef OT_S81PH_COLL_MTPL
    // mtp-colllane-1011 (ds-1010 decision: DEDICATED MTP lane, not a pass-through queue in the core): lane W4 = the
    // generator's first --mtp-links board SerDes (lk_W4: rW4 / tdW4 / tfW4), carrying the head-die sequencer's token
    // return / seed / accept word between dsfd_coll_mtp_lane adapters (rtl/dsrom_sys/s81_ph/coll/dsfd_coll_mtp_lane.sv).
    //   f_mtp  = generator bus mtp -> collective 648 = {t_acc 57, t_sd 77, t_sv, t_td 512, t_tv} of dsfd_mtp_seq_rtt
    //   t_mtp  = generator bus collective -> mtp 2 = {f_sg, f_tg} (grants, RTT-sized receivers dsfd_coll_mtp_ep 8 / 8)
    //   t_mrt / f_mrt, t_mrs / f_mrs, t_macc: what the far die's sequencer sent (grant protocol / accept event); the
    //   accept word's fault bit [56] also carries this die's MTP-lane faults (lane tile + adapter, sticky)
    ,
    input  wire [647:0]  f_mtp,
    output wire [1:0]    t_mtp,
    input  wire [514:0]  rW4,
    output wire [511:0]  tdW4,
    output wire [0:0]    tfW4,
    output wire [512:0]  t_mrt,
    input  wire [0:0]    f_mrt,
    output wire [77:0]   t_mrs,
    input  wire [0:0]    f_mrs,
    output wire [56:0]   t_macc
`endif
`ifdef OT_S81PH_COLL_P2L
    // mtp-colllane-1011, P2 variant (MD-2 P2 draft die A): the P2 selected-path traffic on two DEDICATED lanes
    // (dsfd_coll_p2_lane adapters, rtl/dsrom_sys/s81_ph/coll/dsfd_coll_p2_lane.sv): W4 = board lane to / from the DSpark
    // primary (start 101 b in, result row 594 b out, abort in, done / fault / corrected out), E4 = UCIe lane from die B
    // (lane-1 expert words 604 b in).  Die side = dsfd_coll_p2_ep (the grant-protocol end of dsfd_p2_lnk, mtp-fixlat):
    //   t_p2 = generator bus collective -> p2 709 = {f_og, abort, t_sd 101, t_sv, t_l1d 604, t_l1v}
    //   f_p2 = generator bus p2 -> collective 600 = {corrected, fault, done, f_sg, f_l1g, f_od 594, f_ov}
    ,
    output wire [708:0]  t_p2,
    input  wire [599:0]  f_p2,
    input  wire [514:0]  rW4, rE4,
    output wire [511:0]  tdW4, tdE4,
    output wire [0:0]    tfW4, tfE4,
    output wire [1:0]    t_p2flt             // {die-B lane, primary lane} sticky faults (adapter flops)
`endif
`ifdef OT_S81PH_COLL_JOB
    // s81-ctl-1011 (ADAPTER_CONTRACT_1011, engine 3): the coll command endpoint ot_s81_coll_job -- split3cr: inside dsfd_coll_cb
    // between its f_vm pin register and the seam register (+0 cycles); v2 core: the dsfd_coll_job tile in front of the
    // core (+1 on f_vm).  c_cmd = {cv[3], cd[3]} from dsfd_stage_seq, c_done = {dv, dt}, c_st = {online, fault}.
    ,
    input  wire [84:0]   c_cmd,
    output wire [8:0]    c_done,
    output wire [1:0]    c_st
`endif
);
`ifdef OT_S81PH_COLL_MTPL
`ifdef OT_S81PH_COLL_P2L
    initial $fatal(1, "dsfd_sp_collective: MTPL (head die) and P2L (draft die A) both claim lane W4");
`endif
`endif
`ifndef S81PH_COLL_V1
    // CLAUDE S81-PH coll v2 (redesign pass, coll_m1 7 h in timing-driven placement at ~1M nets): the slab is a
    // composition of tiles: dsfd_coll_ck (PLL, reset sequencer), dsfd_coll_core (engine, VM queues, packer) and 8
    // lane tiles (dsfd_coll_lane_w: W0..W3 = lanes 0..3, dsfd_coll_lane_w mirrored MY: E0..E3 = lanes 4..7), joined by registered
    // 2-slot skid interfaces (physical/s81_ph_views/collective/composition.json).  S81PH_COLL_V1 = the v1 flat slab.
    dsfd_coll_ck u_ck (.refclk(refclk), .por(por), .pll_stream(pll_stream), .pll_serial(pll_serial), .pll_hbm(pll_hbm),
        .rst_stream(rst_stream), .rst_serial(rst_serial), .rst_hbm(rst_hbm));
    wire [7:0] lo_v, lo_r, li_v, li_r;
    wire [8*553-1:0] lo_d, li_d;
    wire [23:0] flt;
`ifdef OT_S81PH_COLL_SPLIT
    // redesign-ds 2026-10-09: the core column as three abutted tiles (rtl/dsrom_sys/s81_ph/coll/dsfd_coll_split.sv):
    // bottom dsfd_coll_cb (VM interface, output queue, lanes 0 / 4), middle dsfd_coll_ce (engine, queues, packer,
    // lanes 1, 2, 5, 6), top dsfd_coll_ct (lanes 3 / 7); seams of registered skids / pin registers.
    wire [591:0] s_fvm; wire [5:0] s_fltu, s_fltd;
    wire s_lo0_v, s_lo0_r, s_li0_v, s_li0_r, s_lo4_v, s_lo4_r, s_li4_v, s_li4_r;
    wire s_lo3_v, s_lo3_r, s_li3_v, s_li3_r, s_lo7_v, s_lo7_r, s_li7_v, s_li7_r;
    wire [552:0] s_lo0_d, s_li0_d, s_lo4_d, s_li4_d, s_lo3_d, s_li3_d, s_lo7_d, s_li7_d;
    wire s_bw_v, s_bw_cr, s_bw_flt; wire [2099:1] s_bw_d;
    `OT_S81PH_CB_MASTER #(.CR(`ifdef OT_S81PH_COLL_CR 1 `else 0 `endif)) u_cb (.ck(pll_stream), .rs(rst_stream), .f_vm(f_vm), .ts(ts), .t_vm(t_vm),
`ifdef OT_S81PH_COLL_JOB
        .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
`endif
        .wlo_v(lo_v[0]), .wlo_r(lo_r[0]), .wlo_d(lo_d[0*553 +: 553]), .wli_v(li_v[0]), .wli_r(li_r[0]), .wli_d(li_d[0*553 +: 553]), .wflt(flt[0 +: 3]),
        .elo_v(lo_v[4]), .elo_r(lo_r[4]), .elo_d(lo_d[4*553 +: 553]), .eli_v(li_v[4]), .eli_r(li_r[4]), .eli_d(li_d[4*553 +: 553]), .eflt(flt[12 +: 3]),
        .fvm_u(s_fvm), .flt_u(s_fltu),
        .lo0_v(s_lo0_v), .lo0_r(s_lo0_r), .lo0_d(s_lo0_d), .li0_v(s_li0_v), .li0_r(s_li0_r), .li0_d(s_li0_d),
        .lo4_v(s_lo4_v), .lo4_r(s_lo4_r), .lo4_d(s_lo4_d), .li4_v(s_li4_v), .li4_r(s_li4_r), .li4_d(s_li4_d),
        .bw_v(s_bw_v), .bw_d(s_bw_d), .bw_cr(s_bw_cr), .bw_flt(s_bw_flt));
    dsfd_coll_ce #(.CR(`ifdef OT_S81PH_COLL_CR 1 `else 0 `endif)) u_ce (.ck(pll_stream), .rs(rst_stream),
        .wlo_v(lo_v[2:1]), .wlo_r(lo_r[2:1]), .wlo_d(lo_d[1*553 +: 2*553]), .wli_v(li_v[2:1]), .wli_r(li_r[2:1]), .wli_d(li_d[1*553 +: 2*553]), .wflt(flt[3 +: 6]),
        .elo_v(lo_v[6:5]), .elo_r(lo_r[6:5]), .elo_d(lo_d[5*553 +: 2*553]), .eli_v(li_v[6:5]), .eli_r(li_r[6:5]), .eli_d(li_d[5*553 +: 2*553]), .eflt(flt[15 +: 6]),
        .fvm_u(s_fvm), .flt_u(s_fltu),
        .lo0_v(s_lo0_v), .lo0_r(s_lo0_r), .lo0_d(s_lo0_d), .li0_v(s_li0_v), .li0_r(s_li0_r), .li0_d(s_li0_d),
        .lo4_v(s_lo4_v), .lo4_r(s_lo4_r), .lo4_d(s_lo4_d), .li4_v(s_li4_v), .li4_r(s_li4_r), .li4_d(s_li4_d),
        .bw_v(s_bw_v), .bw_d(s_bw_d), .bw_cr(s_bw_cr), .bw_flt(s_bw_flt),
        .lo3_v(s_lo3_v), .lo3_r(s_lo3_r), .lo3_d(s_lo3_d), .li3_v(s_li3_v), .li3_r(s_li3_r), .li3_d(s_li3_d),
        .lo7_v(s_lo7_v), .lo7_r(s_lo7_r), .lo7_d(s_lo7_d), .li7_v(s_li7_v), .li7_r(s_li7_r), .li7_d(s_li7_d), .flt_d(s_fltd));
    dsfd_coll_ct #(.LR(`ifdef OT_S81PH_COLL_CTLR 1 `else 0 `endif), .CR(`ifdef OT_S81PH_COLL_CR 1 `else 0 `endif)) u_ct (.ck(pll_stream), .rs(rst_stream),
        .wlo_v(lo_v[3]), .wlo_r(lo_r[3]), .wlo_d(lo_d[3*553 +: 553]), .wli_v(li_v[3]), .wli_r(li_r[3]), .wli_d(li_d[3*553 +: 553]), .wflt(flt[9 +: 3]),
        .elo_v(lo_v[7]), .elo_r(lo_r[7]), .elo_d(lo_d[7*553 +: 553]), .eli_v(li_v[7]), .eli_r(li_r[7]), .eli_d(li_d[7*553 +: 553]), .eflt(flt[21 +: 3]),
        .lo3_v(s_lo3_v), .lo3_r(s_lo3_r), .lo3_d(s_lo3_d), .li3_v(s_li3_v), .li3_r(s_li3_r), .li3_d(s_li3_d),
        .lo7_v(s_lo7_v), .lo7_r(s_lo7_r), .lo7_d(s_lo7_d), .li7_v(s_li7_v), .li7_r(s_li7_r), .li7_d(s_li7_d), .flt_d(s_fltd));
`else
`ifdef OT_S81PH_COLL_JOB
    wire [591:0] j_fvm; wire [2099:0] j_tvm;
    dsfd_coll_job u_job (.ck(pll_stream), .rs(rst_stream), .f_vm(f_vm), .cf_vm(j_fvm), .ct_vm(j_tvm), .t_vm(t_vm),
        .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
    dsfd_coll_core u_core (.ck(pll_stream), .rs(rst_stream), .f_vm(j_fvm), .ts(ts), .t_vm(j_tvm), .lo_v(lo_v), .lo_r(lo_r),
        .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .flt(flt));
`else
    dsfd_coll_core u_core (.ck(pll_stream), .rs(rst_stream), .f_vm(f_vm), .ts(ts), .t_vm(t_vm), .lo_v(lo_v), .lo_r(lo_r),
        .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .flt(flt));
`endif
`endif
    wire [514:0] rxl [0:7];
    wire [511:0] txl [0:7];
    wire [7:0] tfl;
    assign rxl[0] = rW0; assign rxl[1] = rW1; assign rxl[2] = rW2; assign rxl[3] = rW3;
    assign rxl[4] = rE0; assign rxl[5] = rE1; assign rxl[6] = rE2; assign rxl[7] = rE3;
    assign {tdE3, tdE2, tdE1, tdE0, tdW3, tdW2, tdW1, tdW0} = {txl[7], txl[6], txl[5], txl[4], txl[3], txl[2], txl[1], txl[0]};
    assign {tfE3[0], tfE2[0], tfE1[0], tfE0[0], tfW3[0], tfW2[0], tfW1[0], tfW0[0]} = tfl;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_lane
        wire chb = !(g == 0 || g == 4);                 // lanes 0 (W0) and 4 (E0): UCIe ACK timeout
        if (g < 4) begin : g_w
            dsfd_coll_lane_w u_l (.ck(pll_stream), .rs(rst_stream), .chb(chb), .rx(rxl[g]), .tx(txl[g]), .tf(tfl[g]),
                .lo_v(lo_v[g]), .lo_r(lo_r[g]), .lo_d(lo_d[g*553 +: 553]), .li_v(li_v[g]), .li_r(li_r[g]),
                .li_d(li_d[g*553 +: 553]), .flt(flt[3*g +: 3]));
        end else begin : g_e
            dsfd_coll_lane_w u_l (.ck(pll_stream), .rs(rst_stream), .chb(chb), .rx(rxl[g]), .tx(txl[g]), .tf(tfl[g]),
                .lo_v(lo_v[g]), .lo_r(lo_r[g]), .lo_d(lo_d[g*553 +: 553]), .li_v(li_v[g]), .li_r(li_r[g]),
                .li_d(li_d[g*553 +: 553]), .flt(flt[3*g +: 3]));
        end
    end endgenerate
`ifdef OT_S81PH_COLL_MTPL
    // the dedicated MTP lane: one more closed lane tile (credit seams, LCR 1; board lane: ch_b 1) + the MTP adapter.
    // Nothing here touches the core tiles or lanes 0..7: collective traffic and MTP traffic share no queue.
    wire m_lo_v, m_lo_r, m_li_v, m_li_r; wire [552:0] m_lo_d, m_li_d; wire [2:0] m_lflt;
    dsfd_coll_lane_w #(.LCR(1)) u_ml (.ck(pll_stream), .rs(rst_stream), .chb(1'b1), .rx(rW4), .tx(tdW4), .tf(tfW4),
        .lo_v(m_lo_v), .lo_r(m_lo_r), .lo_d(m_lo_d), .li_v(m_li_v), .li_r(m_li_r), .li_d(m_li_d), .flt(m_lflt));
    dsfd_coll_mtp_lane u_ma (.ck(pll_stream), .rs(rst_stream),
        .f_tv(f_mtp[0]), .f_td(f_mtp[512:1]), .t_tg(t_mtp[0]), .f_sv(f_mtp[513]), .f_sd(f_mtp[590:514]), .t_sg(t_mtp[1]),
        .f_acc(f_mtp[647:591]),
        .lo_v(m_lo_v), .lo_r(m_lo_r), .lo_d(m_lo_d), .li_v(m_li_v), .li_r(m_li_r), .li_d(m_li_d),
        .t_rtv(t_mrt[0]), .t_rtd(t_mrt[512:1]), .f_rtg(f_mrt), .t_rsv(t_mrs[0]), .t_rsd(t_mrs[77:1]), .f_rsg(f_mrs),
        .t_racc(t_macc), .f_lflt(m_lflt));
`endif
`ifdef OT_S81PH_COLL_P2L
    // P2 lanes: two closed lane tiles (LCR 1; W4 board ch_b 1, E4 UCIe ch_b 0) + two P2 adapters + dsfd_coll_p2_ep
    wire p_lo_v, p_lo_r, p_li_v, p_li_r, b_lo_v, b_lo_r, b_li_v, b_li_r; wire [552:0] p_lo_d, p_li_d, b_lo_d, b_li_d;
    wire [2:0] p_lflt, b_lflt; wire p_flt, b_flt;
    dsfd_coll_lane_w #(.LCR(1)) u_pl (.ck(pll_stream), .rs(rst_stream), .chb(1'b1), .rx(rW4), .tx(tdW4), .tf(tfW4),
        .lo_v(p_lo_v), .lo_r(p_lo_r), .lo_d(p_lo_d), .li_v(p_li_v), .li_r(p_li_r), .li_d(p_li_d), .flt(p_lflt));
    dsfd_coll_lane_w #(.LCR(1)) u_bl (.ck(pll_stream), .rs(rst_stream), .chb(1'b0), .rx(rE4), .tx(tdE4), .tf(tfE4),
        .lo_v(b_lo_v), .lo_r(b_lo_r), .lo_d(b_lo_d), .li_v(b_li_v), .li_r(b_li_r), .li_d(b_li_d), .flt(b_lflt));
    wire c_sv, c_sr, c_ov, c_or; wire [100:0] c_sd; wire [593:0] c_od; wire [0:0] p_abort;
    dsfd_coll_p2_ep u_pe (.ck(pll_stream), .rst(rst_stream),
        // lane 1 has no port here: u_ba (dsfd_coll_p2_lane_ba OGRANT) is its die-bus grant sender
        .c_sv(c_sv), .c_sr(c_sr), .c_sd(c_sd), .t_sv(t_p2[605]), .t_sd(t_p2[706:606]), .f_sg(f_p2[596]),
        .f_ov(f_p2[0]), .f_od(f_p2[594:1]), .t_og(t_p2[708]), .c_ov(c_ov), .c_or(c_or), .c_od(c_od));
    dsfd_coll_p2_lane_pa u_pa (
        .ck(pll_stream), .rs(rst_stream), .x_v(c_ov), .x_r(c_or), .x_d(c_od), .r_v(c_sv), .r_r(c_sr), .r_d(c_sd),
        .x_ev(f_p2[599:597]), .r_ev(p_abort),
        .lo_v(p_lo_v), .lo_r(p_lo_r), .lo_d(p_lo_d), .li_v(p_li_v), .li_r(p_li_r), .li_d(p_li_d), .f_lflt(p_lflt), .t_flt(p_flt));
    dsfd_coll_p2_lane_ba u_ba (
        .ck(pll_stream), .rs(rst_stream), .r_v(t_p2[0]), .r_r(f_p2[595]), .r_d(t_p2[604:1]),
        .lo_v(b_lo_v), .lo_r(b_lo_r), .lo_d(b_lo_d), .li_v(b_li_v), .li_r(b_li_r), .li_d(b_li_d), .f_lflt(b_lflt), .t_flt(b_flt));
    assign t_p2[707] = p_abort[0];
    assign t_p2flt = {b_flt, p_flt};
`endif
`else
    wire ck_s, ck_v, ck_h, lock, pd;
    ot_s81_pll_bb u_pll (.refclk(refclk[0]), .pd(pd), .ck_stream(ck_s), .ck_serial(ck_v), .ck_hbm(ck_h), .lock(lock));
    wire clk = ck_s;
    ot_s81ph_ckbuf u_ob_s (.a(ck_s), .y(pll_stream[0]));
    ot_s81ph_ckbuf u_ob_v (.a(ck_v), .y(pll_serial[0]));
    ot_s81ph_ckbuf u_ob_h (.a(ck_h), .y(pll_hbm[0]));
    wire rs_n, rv_n, rh_n;
    ot_s81ph_coll_rstc u_rstc (.refclk(refclk[0]), .por_n(por[0]), .lock(lock), .pll_pd(pd),
        .rst_stream_n(rs_n), .rst_serial_n(rv_n), .rst_hbm_n(rh_n), .seq_state());
    assign rst_stream[0] = rs_n;
    assign rst_serial[0] = rv_n;
    assign rst_hbm[0] = rh_n;
    // this slab's own stream-domain reset (2-flop synchronised release)
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs_n) if (!rs_n) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // pin registers
    reg [8*515-1:0] lr;
    reg [591:0] fv_r;
    reg [2:0] ts_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lr <= 0; fv_r <= 0; ts_r <= 0; end
        else begin lr <= {rE3, rE2, rE1, rE0, rW3, rW2, rW1, rW0}; fv_r <= f_vm; ts_r <= ts; end
    wire [8*512-1:0] lt;
    ot_s81ph_coll_core u_core (.clk(clk), .rst_n(rst_n), .lane_rx(lr), .lane_tx(lt), .f_vm(fv_r), .ts(ts_r),
        .t_vm(t_vm), .fault(), .rank(), .eng_en());
    assign {tdE3, tdE2, tdE1, tdE0, tdW3, tdW2, tdW1, tdW0} = lt;
    ot_s81ph_ckbuf u_f0 (.a(clk), .y(tfW0[0]));
    ot_s81ph_ckbuf u_f1 (.a(clk), .y(tfW1[0]));
    ot_s81ph_ckbuf u_f2 (.a(clk), .y(tfW2[0]));
    ot_s81ph_ckbuf u_f3 (.a(clk), .y(tfW3[0]));
    ot_s81ph_ckbuf u_f4 (.a(clk), .y(tfE0[0]));
    ot_s81ph_ckbuf u_f5 (.a(clk), .y(tfE1[0]));
    ot_s81ph_ckbuf u_f6 (.a(clk), .y(tfE2[0]));
    ot_s81ph_ckbuf u_f7 (.a(clk), .y(tfE3[0]));
`endif
endmodule
// ot_s81ph_ckbuf: rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
