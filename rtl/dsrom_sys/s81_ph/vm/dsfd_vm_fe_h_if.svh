// dsfd_vm_fe_h : FROZEN leaf interface contract (el1013-s81-vmfe, 2026-10-13).  One file; RTL, bench, pin plans and
// ref_tile specs all take widths and stage counts from here.  Flat reference = dsfd_vm_fe (dsfd_sp_vm.sv), unchanged.
// Signal names below are the flat module's; "X = in-pin flop" means the flat register X becomes the leaf's pin register.
`ifndef DSFD_VM_FE_H_IF_SVH
`define DSFD_VM_FE_H_IF_SVH
// ---- fixed shape (hard views carry NO parameters; per-instance differences are registered strap pins)
`define VMFE_NP      28          // memory ports
`define VMFE_NS      4           // bit slices
`define VMFE_PW      545         // order-register word of one port: {v, we, row 14, m 16, d 512}  (b_*)
`define VMFE_SW      148         // slice word of one port: {v, we, row 14, mask 4, d 128}          (s0 / fsr / m_*)
`define VMFE_KW      32          // counter copy of one port: {v, we, row 14, m 16}                 (kq[0])
`define VMFE_NLL     10          // landing lanes (NSVC 1): svc 0,1  coll 2..5  sel 6  col 7  hc 8,9
`define VMFE_LW      526         // landing return word {row 14, d 512} (dd_r / dr_r)
// ---- stage counts.  Flat: FRL 2, KD 1, LAL 2, LGL 2, LDL 2.  The hierarchy only ADDS uniform stages on these four
// parameterised relays, so the flat module instantiated with the same numbers is the CYCLE-EXACT reference.
`define VMFE_R       3           // bundle relay TILES in series on every b -> slice path (2 flops each).  B8 (coordinator decision 10-13 (d)): 3, was 2:
                                 // lane 0 -> slice 3 row bits are 1,682 um pin to pin with the clt row centred and 1,797 um as planned (R 2 reaches 1,500 + 65)
`define VMFE_FRL     (2 + 2*`VMFE_R)   // order register -> slice pins: s0, [fxr in, fxr out] x R, fsr v1, fsr o
`define VMFE_KD      3           // B8: 3 (was 2) = source out pin -> ONE mid-hop relay tile (dsfd_vm_frm u_kl / u_kr in the parent) -> fcn in pin
                                 // (the 16 lanes' copies span 1,212 um); ARM ops and fcn's own ports delayed alike inside fcn (KP = KD - 2)
// STAGE OWNERS (coordinator decision 2026-10-13: LGL 3, LDL 3, LAL 3; B6: LVX 1; the parent holds 0 cells): first stage =
// out-pin flop of the source leaf, LAST stage = in-pin flop of the receiving leaf, the mid-hop stage of all four lane
// relays = ONE relay tile a lane, dsfd_vm_frm (546 b, a single flop a bit, placed mid-way, no reset pin):
//   relay  stage 0 (owner)                 mid stage                  last stage (owner)                  wires
//   LGL 3  g_r[0]   fld  out pin g         frm g   1 b                g_r[2]  flt in pin g_q              2
//   LAL 3  ra_v/rb[0] fcn out pin arm_*    frm a  15 b                [2]     flt in pin ra_q/rb_q        2
//   LDL 3  dd_r/dr_r[0] flt out pin ret    frm r 526 b                [2]     fld in pin dd_r/dr_r        2
//   LVX 1  av / ok / ovf / sflt flt out    frm f   4 b                av_r / ok_q / ov_q / sf_q  fld in   2
//   KD 2   kq[0]    source leaf out pin k_o  (no mid stage)           kq[1]   fcn in pin                  1
//   FRL 6  s0 source leaf out pin, [relay in, relay out] x R (bundle relay masters, S2 below), fsr v1 / fsr o   R + 1
// The lane's own row relay (flat dsfd_vm_ll rv / rd_, AL = LAL stages) stays inside flt.
`define VMFE_LGL     3           // grant
`define VMFE_LDL     3           // lane return data (the drain selects on the grant delayed LGL + 2 + LDL = 8)
`define VMFE_LAL     3           // LARM arm (and the lane's row relay)
`define VMFE_LVX     1           // mid-hop stage (in dsfd_vm_frm) on av / ok / ovf / sflt lane -> fld: 2 wires, as g / arm / ret (flat LVX 1)
`define VMFE_RTH     18          // landing room threshold = the flat 14 + LAL + LVX (+1 row in flight per input / flag stage)
`define VMFE_XRT     1           // B8: fcn engine adapter = one reset synchroniser a clock domain at the pin + registered reset tree (flat XRT 1)
`define VMFE_CCA     1           // B8: fcc ctrl VM crossing = Gray-pointer 2-flop-synchroniser FIFO, DEPTH 16 (flat CCA 1: +2 serial cycles a ctrl VM op)
`define VMFE_DVR     1           // engine done dv / dt on a stream-domain pin register in fcn (flat DVR 1: +1 stream cycle on a done)
// ---- leaves (each: own ck root <= 15,000 sinks MEASURED by yosys, every pin registered, hop <= 500 um)
// ---- S2 / S3 (coordinator decision 2026-10-13 14:00, el1013-s81-vmfe/B6; ports FROZEN again after them)
//  S2  a slice word carries ONLY its non-constant bits from the source pin to the dsfd_vm_fsr pin; constants (we of a
//      one-way port, mask 4'hf of a full-row port, zero data of a read port) are tied at the fsr pins by the parent:
//        ports 12 .. 27 (fxs)  147 = {v, row 14, mask 4, d 128}          we = 1
//        ports 0, 3, 4         144 = {v, we, row 14, d 128}               mask = f
//        ports 10, 11 (fld)    143 = {v, row 14, d 128}                   we = 1, mask = f
//        ports 1, 2, 5 .. 9     15 = {v, row 14}                          we = 0, mask = f, d = 0 except the slice-0 tag
//        slice-0 tags (fcn x_o) 112 = p2 4, p5 92, p6 .. p9 4 each        (in the bundle-5 tiles of slice 0)
//      relay masters: dsfd_vm_fxr 588 b x32 (capture), fxa 447 b x8 (bundle 4: ports 0, 1, 3, 4), fxb 489 b x8 (bundle 5:
//      ports 2, 5 .. 11, rf and the tags; the tag pins of the slice 1 .. 3 instances are strapped at the tile).
//      Mid cut 8,288 -> 6,464 b.  Stage counts unchanged (FRL 6): no cycle delta.
//  S3  dsfd_vm_clt is re-routed at M5 (M6 over the clt row is the parent's).  Its KEY -> AGE stage (24-26 levels, -113 ps
//      at M5) is cut by forming the tag compare and both touch vectors from registers one cycle ahead (dsfd_vm_cl RT 1):
//      bit-exact and cycle-exact to the closed clt8a RTL (bench tb_dsfd_vm_cl_rt), so NO cycle is added and the flat
//      reference needs no parameter for it.
//  fcn dv / dt leave a stream-domain pin register (VMFE_DVR 1; flat reference DVR 1): +1 stream cycle on every done.
//  dsfd_vm_clt x16  RT 1 (S3).  pins: ck rn sok gid[3:0] f_c[831:0] | w_v w_row[13:0] w_m[15:0] w_d[511:0] flt[3:0]
//  dsfd_vm_fsr x4   UNCHANGED RTL.  i_* = 28 x SW slice-major fields, i_rf[3:0] | o_* -> m_* of slice s
//  dsfd_vm_fxs x4   order tile of 4 capture lanes (ports 12+4i .. 15+4i).  in: 4 x clt w_* (b = in-pin flop, v reset),
//                   clt flt 4x4 -> OR -> clf_o[3:0] (out flop);  out: s_o[4*4*147] LANE-major (lane j, slice s at
//                   [(4j + s)*147]; u_s0 kept copies = out-pin flops, one per slice, NEVER merged), k_o[4*KW] (kept copy
//                   of b {v,we,row,m} at a pin, 1 cycle after b)
//  dsfd_vm_fxr x32 / fxa x8 / fxb x8   relay tile of the port words of one slice of one bundle: i_v, i[payload] in-pin flop
//                   -> out-pin flop; valid bits reset by its own rni pin flop.  6 bundles x 4 slices x R tiles = 48 at R 2.
//                   Bundles: 0..3 = capture ports 12+4b..15+4b (fxr), 4 = ports 0,1,3,4 (fxa), 5 = ports 2,5..11 + rf + tags (fxb).
//  dsfd_vm_flt x10  landing lane: q_* pin flops of ITS producer bits + decode + dsfd_vm_ll + rr_ll.
//                   pins in: p_v p_t[1:0] p_m p_d[511:0] p_flt (non-collective producers strap t=0 m=1), stride[2:0] off[1:0]
//                   straps, g (g_r[LGL-1] in-pin), arm_v arm_base[13:0] (LAL-1 in-pin);  out: av (flop), ret[LW-1:0]
//                   (dd_r[0]; NO ret_v: the drain selects on its own delayed grant, as the flat module), ok (flop),
//                   ovf (flop), sflt (flop: l_src_flt term)
//  dsfd_vm_fld x1   drain: av_r (in-pin), lc, ll_ptr, arbiter, g_r[0] (out), sd_*, dd_r[LDL-1] (in), lp_*, b of ports
//                   10,11 + their 4 s0 copies + k_o; cts: ok_q <= ok pins, t_cts <= {0,1,&ok_q[5:2]}; ll_ovr, l_src_flt
//  dsfd_vm_fcc x1   ctrl CDC (the ONLY two-clock leaf with fcn): s_* pin flops (cks), u_cc0/1, pop, b of ports 3,4 + s0
//                   + k_o, s_ovf -> so_s
//  dsfd_vm_fcw x1   u_wfc (WNQ 1) + rbad, b of ports 0,1 + s0 + k_o.  NO macro, no split: the write receiver's 30 x 527
//                   slots of the flat module are DEAD STORAGE (dsfd_vm_wfc_ep ties the write consumer ready, so every
//                   flit is taken from the pin flop and no slot is ever read); fcw uses ot_dsrom_mtp_lrx_rtt_ar
//                   (pin flops + one grant flop; fatal if its consumer ever stalls).  The flat reference KEEPS the
//                   slots: lockstep proves the two bit-exact at 0 cycles.  The read receiver's 30 x 31 queue stays.
//  dsfd_vm_frm x10  the lane's mid-hop relay tile (table above; replaces frg / fra / frr of 693940a56)
//  dsfd_vm_fcn x1   u_rs/u_rss, u_ad (cv_p/cd_p), command decode, id_r, cq, P2RD, 5 X streamers, b of ports 2,5,6,7,8,9
//                   + s0 + k_o, kq[KD-1] in-pin of all 28 k copies, K/K2/slots, done mux, c_w*, t_rdy, cq_p, fe_flt,
//                   rf_o = |fe_flt (out flop, to the 4 fsr i_rf[3] through the same fxr chain: sticky, +1 + 2R cycles)
//  dsfd_vm_fe_h     parent = wires + leaf instances only (yosys stat with leaves black-boxed must show 0 cells).
// ---- rules every leaf obeys
//  1 b_* of a port is the OUT-side register of the leaf that sources it; its 4 slice copies s0 (kept, ID-distinct) are
//    one cycle later in the SAME leaf and leave on a pin; all 28 ports therefore keep ONE op order (the 4 slices and the
//    counter see the same order).  No leaf may add a stage between b and s0 or between b and k_o for one port only.
//  2 reset (AS BUILT, proven in lockstep): rn0 is produced in fcn and leaves on 8 kept out flops rn_o; every leaf takes
//    its reset on the in-pin flop of pin `rni` (= its internal rn) and forwards kept out-flop copies rn_o.  The TREE is
//    parent wiring only (re-routable without touching a leaf): fcn.rn_o -> fld, fcc, fcw, fxs 0..3 (DIRECT children:
//    release on the flat module's cycle, rn0 + 2); fld -> flt 0 -> .. -> flt 9 (2 cycles a hop: flt 9 releases 21
//    cycles after the flat lane); fxs -> its 4 clt; bundle source -> fxr chain -> fsr.  fld MUST be a direct child
//    (ll_ptr rotates from release).  fcc and fcw STAY direct children (decision 2026-10-13): fcc's serial-side CDC
//    pointers (u_cc0 / u_cc1) and its pop cadence start from rn, and a later release would shift every ctrl op against
//    the flat order; fcw's kit endpoint is released by its own rst synchroniser, so only err_o and the b valid bits
//    hang on rni there, but fcn has the kept copy and the hop is short, so nothing is gained by chaining it.
//    The bench holds stimulus idle for LK_IDLE = 28 cycles after release (checked: no op may leave either FE in the
//    window) and the flat reference gets the same window.
//  3 faults are sticky; inter-leaf fault wires are flop -> wire -> flop and may add cycles to fe_flt / m_rf only.
//  4 mutants OT_SPVM_MUT_STALE / _DROPW / _NP16 / _LSMALL / _EARLY keep their flat meaning inside the leaf that owns
//    the logic (STALE: fcc port 3 between b and s0; NP16: sok generated in the fxs that feeds the lane pair).
//  5 lockstep reference: flat dsfd_vm_fe under `OT_SPVM_REF_FRL at FRL `VMFE_FRL / KD `VMFE_KD / LDL `VMFE_LDL (dsfd_sp_vm_m
//    takes them, LGL and LAL from this file); +define+OT_SPVM_FE_H = hierarchy as a shadow, +OT_SPVM_FE_H_SUBST = hierarchy drives.
//    Hierarchy-only mutants: OT_VMFE_MUT_FXR1 (one fxr stage fewer, port 16 slice 2), OT_VMFE_MUT_GBYP (flt grant pin
//    flop bypassed), OT_VMFE_MUT_KQSKIP (ARM ops skip their kq stage), OT_VMFE_MUT_WNQDROP (the slot-less write
//    receiver drops every 8th flit).
`endif
