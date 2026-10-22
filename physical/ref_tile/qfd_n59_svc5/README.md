# qfd_n59_svc5 (SQ-C2-N59, 10-21) -- MAIN: 2 regional clock roots W/E

Bound master: the Q die's Q.native59 = qfd_native59_dv_headprep_obs1 (codex/q-headprep-1021, sha256 b8f883e7; ASSEMBLY_CANONICAL
params HEAD_PREP 1 NU 4 ROPE 1 USER_BIND 1 MCTX 1 EMB_RELAY 1) instantiates u_svc = qfd_native59_svc_obs1 (sha256 c1b1ae37).
This kit hardens qfd_native59_svc_obs1 with those params + RECV_INPUTS 1 LOCAL32 1 (the svc3/svc4 physical form).
DIE NOTICE: the parent must pass SVC_RECV=1 SVC_LOCAL32=1 to qfd_native59_dv_headprep_obs1 (same source, parameter only).
RTL files under rtl/qwen_split + ot_qfd_su_kv_static_posted / qkd_native_attention_record are byte-identical to
codex/q-headprep-1021 (overlaid on main; main had not changed them since the merge-base).

Predecessor qfd_n59_svc4: module qfd_native59_svc (wrong master), one clock root 21,950 sinks, TT pin-flop spread 84.6 ps
closed only under a coordinator waiver.  Owner PD-AUDIT 10-21: no waiver, no outline shrink, regional roots + landed seam.
Generator: results/arch/sqc2_n59_1021/gen_specs.py (from the svc4 spec).

## SAFE-DESIGN 8-point review (SQ-C2-N59, 10-21, before the first gate)
1 Pins: PASS -- RECV_INPUTS=1: every legacy input lands in a g_recv face register then a p_* pin register; the head-prepare
  inputs land directly in hp_v/hp_u0/hp_t0/hp_p0 flops; outputs are flops (head_descriptor_*, native_ret, dr_o, emb_*) or
  the r1 2-slot select of slot flops (native_tx / completed; completed_tag = kept last_slot copy selecting obs hold-chunk
  flops).  rst_n: 2 landing stages x 32 copies.  Face pins/um: MAIN N 3.54 / E 4.78 / W 3.21 / S 2.08 (E = the svc4 face,
  routed DRC 0 in svc4; > ~4 is a CHECK); FALLBACK moves dr_o (520 b) E -> S: E 2.37 / S 3.08 (all faces <= ~4).
2 Reach: PASS by flow -- svc4 reach_reloc hooks kept (pre-DPL register-stage relocation, residual stage span > 405 um FAILS
  the flow); outline 518.4 x 216 (regions 259 x 216 W/E; 259 x 108 quadrants).
3 Fanout: CHECK at the gate's pre-gate native census (limit 32, data AND reset) -- LOCAL32=1 = the R3k publication copies
  (svc3/svc4 strict census PASS, max 32); obs1 adds 4 completed_tag hold chunks (<= 15 bits per local enable, kept
  last_slot copies) and the head-prepare path (2-edge 39-bit pipe, 4 x 14-bit fseq).
4 Depth: CHECK at gate -- svc3 census lint depth 393.4 ps; obs1/headprep additions: hp_host_match (~50-bit equality of
  registered fields + AND) and the fseq[hp_u1] 4:1 read + 14-bit increment, both register -> register.
5 Storage: PASS -- no SRAM, no runtime-indexed array > 2 kb (fseq 4 x 14 flops; formatter seat hits are pipeline regs).
6 Floorplan: PASS (owner rule) -- slot-driven 518.4 x 216 (N part of the 518.4 x 648 native59 slot), std-cell only,
  ~13 % fill, pin-bound; NO shrink (PD-AUDIT 10-21), full-width rows.
7 Clock: CHANGED (the PD-AUDIT must-do) -- physical/common_flow/clock_regions_2lvl.tcl: MAIN 2 regional roots (W/E halves,
  seam x 259.2 directly under the N-face ck pin 257.7-260.7 = equal trunks) x 6 k-means leaf roots per region; FALLBACK 4
  regional roots (NW/NE/SW/SE, seams x 259.2 / y 108) x 4 leaves.  No leaf cluster and no CTS subtree crosses a seam;
  seam crossings are flop -> flop between regional trees of one synchronous clock (fixed latency, 1 edge, no elastic
  stage); per-region insertion + root arrivals recorded after CTS (CLOCK_REGIONS lines, logs/clock_regions.json).
  Rule = pin-flop spread <= 80 ps at TT AND FF measured by the --cts gate; NO clock_rule_waiver in either job.
8 Reset: PASS (inherited) -- rst_n landed 2 stages x 32 copies, then the kept per-region reset forest (rst_cp_fmt/x3/svc/
  rec/ctx/land/pin/top, each copy <= ~28 loads); assertion async, release synchronous.  Note: the bound legacy source
  also clears its p_* data pin registers (not only control/valid) -- unchanged source of the bound master.
Benches (results/arch/sqc2_n59_1021/bench.sh, tb_n59_svc_obs1_hp, Verilator 5.050): lockstep vs the legacy
qfd_native59_svc at the same parameters (every shared output, every edge, 6,000 random edges + random resets) + an
independent head-prepare scoreboard (18 directed descriptors: 15 filler fills users 1..3 with per-user seq, 2 host
prepares with matching epoch, exact edge + tag); s1 / s2 PASS; mutants m_hpseq (seq +2), m_hpdrop (user-2 prepares
dropped), m_ret (native_ret bit flip), m_hosttag (host descriptor field) REJECTED; receipts results/arch/sqc2_n59_1021/receipts.
