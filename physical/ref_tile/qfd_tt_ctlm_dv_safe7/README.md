# qfd_tt_ctlm_dv_safe7 (+ fallback qfd_tt_ctlm_dv_safe7c) — QW-SUVM8/CTLM7, 10-20

Branch claude/qw-ctlm7-1020 (base: Codex codex/qw-ctlm6-recovery-1020 d54a9f7ef, candidate6 = bounded native32
netlist from tools/qwen_dv/ctlm6_bound_macro.py). Kit = safe5 floorplan / pins / clock domains with the generated
bounded netlist as the top (qfd_tt_ctlm_dv_np_lp, rtl/qwen_dv/lp7_np). safe7c = safe5c pins (ck_core / rst_n on the
S face, centre of the core S pin band). Not on critical_tiles.txt.

## What changed vs candidate6 (all exact: 0 added schedule edges, outputs bit-identical every edge)
| # | Change | Proof |
|---|--------|-------|
| 0 | 1-bit ports declared scalar in the committed netlist (generated [0:0] -> scalar; every use is the bare name, so behaviour-neutral) so the safe5 hand pin file binds | - |
| 1 | X arms removed IN SOURCE (no tool-level X refinement, no ROOT receipt needed): cal_mu f_idx split into go-only f_lo + stride f_hi (the 8 "d_u" arms were optimizer don't-cares on f_idx[1:0]); lpf_parts ctx_mask4 = {0, ctx_mask} index (user 0 guarded arm) | construct without undef receipt: native strict PASS, 0 role errors |
| 2 | ot_qfd_xpf_static_schedule_p (new file; shared original untouched): record arithmetic registered at load, cycle matches as registered one-edge-early flags, registered one-hot record select captured at start, registered pair conflicts from exact record next-state, flat fault OR | unit lockstep vs original, 3 configs, 276k-292k compares PASS; late-start mutant FAIL |
| 3 | qkd_program_pw_observer_p (new file; original untouched): parallel slice decode, last-wins one-hot select | 400k-vector equivalence PASS; bank-mask mutant FAIL |
| 4 | qfd_dv_cmd_cal_mu: 15 fault sites -> per-site flags, fault = f_p (registered flag OR) \| f_g (registered hold / pw-addr-0 clear), bit-exact incl. fault_code; seal_bad state part and the TLOAD image end (bend, ceil(bend/16)) registered from the exact next-state of dwr / meta_rows; one-hot segment word select + per-word count-nonzero; parallel playhead completion collision; range check and dq_n as 3:2 compressor + Kogge-Stone (rtl/lib/ot_ks_add.sv); one-hot read pointer OR encoder; inflight update both outcomes precomputed, grant only selects; flat issue-register fault guards | end to end: OLD (Codex fullsrc6) RTL flat vs NEW bounded netlist, Verilator 5.050, 186,922 compares / 10,000 cycles / 2 resets PASS; corruption mutant FAIL 9,838, +1-edge mutant FAIL 4,748 |

Textbook depth on the mapped netlist (ASAP7 RVT, same native recipe as Codex native6): 2927.3 ps / 95 lv (candidate6)
-> candidate7 (this build): 818.5 ps / 27 lv (u_gi.u_cal FIREDQ head: rp_oh -> fq_word select -> dq_n Kogge-Stone -> dq). Native strict PASS 85k+ roots / max 32 / 0 violations / 0 role errors; std area 11,500.4 um2.

## Safe-design checklist
| # | Item | Result |
|---|------|--------|
| 1 | Pins registered, reset landed | PASS (lp landings = pin registers; regional reset runs depth 3, rst_n 1 sink) |
| 2 | Reach <= 405 um | inherited safe5 pin placement; gate wire_reach decides (safe5 open item: u_hr me_image_ready -> control_stores_ready fixed by the registered readiness landing in the lp6 parent) |
| 3 | Fanout <= 32 | PASS: native strict census max 32, 0 violations, 0 role errors (all roots incl. reset) |
| 4 | Depth <= ~600 ps | IMPROVED, see lane file (exact restructures only; remaining cones = calendar FIFO head arithmetic) |
| 5 | Storage > 2 kb in SRAM | PASS: 6 SRAM + 3 ROM macros; XPF records 752 b flops |
| 6 | Floorplan | safe5 unchanged (p192 SRAMs 43.2 lattice, 53 % fill, aspect 1.38) |
| 7 | Clock | regional ck_core / ck_hr + landed crossings; OPEN: ck_hr own-entry for u_hr (safe5 measured hr pair 262 ps); not in this kit |
| 8 | Schedule | static; 0 added edges |

Name-based reset-copy hooks of safe5 (lp_reset_copies / same_edge_reset_copies) are dropped: the bounded netlist
already holds every load <= 32. lp_cone_regions.tcl (clock-port traced, name independent) is kept.
