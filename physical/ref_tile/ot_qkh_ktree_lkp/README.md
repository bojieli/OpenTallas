# ot_qkh_ktree_lkp (KV-DCAL2 10-19): pin-balanced variant of ot_qkh_ktree_lk (same RTL, same slot)

KV-DCAL2 10-19 K.STA.ECTL KPV_LOCKSTEP (ROOT: no blanket lockstep admission, apply misc_b): ot_qkh_ktree_lk = the closed ot_qkh_ktree (ot_qkh_ktree_m5, same RTL + the m5 fastfp snapshot) wrapped so all 16 lane kpv are read: lane mismatch vs lane 0 -> lane fault into the existing gf_r -> g_f path (XOR16 + OR, 2 gate levels before an existing input flop). Same outline 151.2 x 97.2 (die slot unchanged), 15 new N-face pins (544 on 151.2 um = 3.6/um). +0 cycles, +0 flops. lkp: balanced full-face pins (lk1 gate showed PPL-clustered partial-face N pins ~7/um).

Parallel with ot_qkh_ktree_lk lk2 (PPL pins, fallback). Bind whichever closes first under the checklist. Note: kp_in bit order is monotonic along the N face here (closed m5 had lane groups interleaved), so the head lane slot perm (head_lane_perm.py) should be re-derived for this view before the die plan.

## Safe-design checklist (pre-gate)
- 1_pins: fixed (gate lk1): every input lands on the existing RTL input flops (kp_r/kv_r/gf_r; kpv_in[15:1] via XOR+OR into gf_r), every output is a register; rst_n now lands in 2 RTL face stages (rst_l0/rst_l1) before the 17-region relay
- 2_reach: PASS: 151.2 x 97.2 um tile, every wire < 405 um
- 3_fanout: PASS functional (kpv_in[0] 16 loads); reset copy u_rr.rst_n[15] 369 flops (closed m5 multiplier err/valid structure, buffered reset tree, in->reg reset slack ~397 ps) = WARN kept: the closed shared ot_qkh_ktree is not modified
- 4_depth: PASS: unchanged closed adder/multiplier stages; the new logic is XOR + OR (2 levels) before gf_r; no comb in->out
- 5_storage: PASS: no storage beyond pipeline registers
- 6_floorplan: PASS (lkp): no macros; outline = closed m5 slot 151.2 x 97.2, full std-cell band; N face pins balanced (route.pin_balance): kp_in 512 over 122 um = 4.2/um, gf_in 16 over 9 um, kpv_in 16 over 10 um; S sc_d 32 over 100 um; <= 6/um everywhere (lk1 PPL groups clustered ~7/um: rejected)
- 7_clock: PASS (to verify at gate): one root clk W face, CTS centre tree as the closed m5 (spread <= 80 TT/FF); io_hold_margin 0.03
- 8_schedule: PASS: static, +0 cycles (fault latency = lane gf latency, 2 edges); new fault source handed to KV-RETIRE/KV-HEALTH (existing head g_f path, no new die port)
