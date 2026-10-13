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
`define VMFE_R       2           // fxr relay TILES in series on every b -> slice path (2 flops each)  [R 1 needs a 2nd H layer]
`define VMFE_FRL     (2 + 2*`VMFE_R)   // order register -> slice pins: s0, [fxr in, fxr out] x R, fsr v1, fsr o
`define VMFE_KD      2           // b (leaf out-pin) -> [relay] -> kq in-pin of fcn; ARM ops delayed alike (kq_arm*)
`define VMFE_LGL     2           // grant: g_r[0] = fld out-pin flop, g_r[LGL-1] = flt in-pin flop
`define VMFE_LDL     2           // data:  dd_r[0]/dr_r[0] = flt out-pin flop, dd_r[LDL-1] = fld in-pin flop
`define VMFE_LAL     2           // LARM:  ra_v[0]/rb[0] = fcn out-pin flop, [LAL-1] = flt in-pin flop
`define VMFE_RTH     16          // landing room threshold; +1 per stage added to the ll_ok -> t_cts path
// ---- leaves (each: own ck root <= 15,000 sinks MEASURED by yosys, every pin registered, hop <= 500 um)
//  dsfd_vm_clt x16  UNCHANGED RTL.  pins: ck rn sok gid[3:0] f_c[831:0] | w_v w_row[13:0] w_m[15:0] w_d[511:0] flt[3:0]
//  dsfd_vm_fsr x4   UNCHANGED RTL.  i_* = 28 x SW slice-major fields, i_rf[3:0] | o_* -> m_* of slice s
//  dsfd_vm_fxs x4   order tile of 4 capture lanes (ports 12+4i .. 15+4i).  in: 4 x clt w_* (b = in-pin flop, v reset),
//                   clt flt 4x4 -> OR -> clf_o[3:0] (out flop);  out: s_o[NS*4*SW] (u_s0 kept copies = out-pin flops,
//                   one per slice, NEVER merged), k_o[4*KW] (kept copy of b {v,we,row,m} at a pin, 1 cycle after b)
//  dsfd_vm_fxr      relay tile: i[4*SW*K] in-pin flop -> out-pin flop o; valid bits reset by its own rn pin flop;
//                   one view (K ports of one slice bundle; K fixed after the cut measurement), mirrored for westward
//  dsfd_vm_flt x10  landing lane: q_* pin flops of ITS producer bits + decode + dsfd_vm_ll + rr_ll.
//                   pins in: p_v p_t[1:0] p_m p_d[511:0] p_flt (non-collective producers strap t=0 m=1), stride[2:0] off[1:0]
//                   straps, g (g_r[LGL-1] in-pin), arm_v arm_base[13:0] (LAL-1 in-pin);  out: av (flop), ret[LW-1:0]+ret_v
//                   (dd_r[0]), ok (flop), ovf (flop), sflt (flop: l_src_flt term)
//  dsfd_vm_fld x1   drain: av_r (in-pin), lc, ll_ptr, arbiter, g_r[0] (out), sd_*, dd_r[LDL-1] (in), lp_*, b of ports
//                   10,11 + their 4 s0 copies + k_o; cts: ok_q <= ok pins, t_cts <= {0,1,&ok_q[5:2]}; ll_ovr, l_src_flt
//  dsfd_vm_fcc x1   ctrl CDC (the ONLY two-clock leaf with fcn): s_* pin flops (cks), u_cc0/1, pop, b of ports 3,4 + s0
//                   + k_o, s_ovf -> so_s
//  dsfd_vm_fcw x1   u_wfc + rbad, b of ports 0,1 + s0 + k_o   (split along the 512-b flit if > 15k sinks)
//  dsfd_vm_fcn x1   u_rs/u_rss, u_ad (cv_p/cd_p), command decode, id_r, cq, P2RD, 5 X streamers, b of ports 2,5,6,7,8,9
//                   + s0 + k_o, kq[KD-1] in-pin of all 28 k copies, K/K2/slots, done mux, c_w*, t_rdy, cq_p, fe_flt,
//                   rf_o = |fe_flt (out flop, to the 4 fsr i_rf[3] through the same fxr chain: sticky, +1 + 2R cycles)
//  dsfd_vm_fe_h     parent = wires + leaf instances only (yosys stat with leaves black-boxed must show 0 cells).
// ---- rules every leaf obeys
//  1 b_* of a port is the OUT-side register of the leaf that sources it; its 4 slice copies s0 (kept, ID-distinct) are
//    one cycle later in the SAME leaf and leave on a pin; all 28 ports therefore keep ONE op order (the 4 slices and the
//    counter see the same order).  No leaf may add a stage between b and s0 or between b and k_o for one port only.
//  2 reset: rn0 is produced in fcn and leaves on an out flop; every leaf takes rn on an in-pin flop and passes rn_o on
//    an out flop to the next leaf (chain, <= 500 um a hop).  Release is skewed by chain position; the bench holds
//    stimulus idle for the chain length after release and SAYS so.  The flat reference gets the same idle window.
//  3 faults are sticky; inter-leaf fault wires are flop -> wire -> flop and may add cycles to fe_flt / m_rf only.
//  4 mutants OT_SPVM_MUT_STALE / _DROPW / _NP16 / _LSMALL / _EARLY keep their flat meaning inside the leaf that owns
//    the logic (STALE: fcc port 3 between b and s0; NP16: sok generated in the fxs that feeds the lane pair).
`endif
