# Qwen methodology re-plan: both-cluster xt1 PASS

Collected 2026-10-25 from the existing epyc3 run, without rebuilding or changing the RTL. Bind = `epyc1:/srv/opentallas-scratch2/claude/qc/bind_meth_cb16` on `claude/qc-meth-1024@a281ceb5ce` (405-um methodology re-plan plus R8/CB16).

Nominal lead24/gap4: **near64/64 and far64/64 exact** across QKV/O/GU/down. The +1 hr-lane mutant also remains numerically64/64, and the strict static-consumer schedule gate catches it on all16 signal groups (cw_go and result edges for4 operations on2 clusters). `results/schedule_gate.json` verdict PASS. This is the same numeric-plus-fixed-consumer-edge rule as the accepted capacity pass.

The regenerated constants are kept alongside the actual timing records. The link pass is `../link_meth` on parent commit f3edf0870: tp8 3/3 +9 mutants, xdie9/9 +13, ovl4u2/2 +8, all PASS. tp8 LS is407; +1296 collective cycles/token vs LS389.

This carve does not establish a whole generated-die token pass or physical sign-off. The generated bound top still distributes rst_n directly; wavefront reset/start-broadcast integration remains open (see link_meth README). Existing bound-s8 stage failures are tracked independently in TOK-QW.

The paused collector `finish_xt1.py` contained an invalid unquoted rsync command. Collection here uses the existing `bind_smoke.fixed_schedule_gate` on untouched simulation logs; the failed collector did not require another simulation.

## Constants diff vs the capacity bind (bind_eq_cb16), same tool @a281ceb5ce (constants_diff_vs_cap_eq.json)

regen_constants on bind_meth_cb16: 22/22 OK (25/25 with the kv41 peer; kv44 gives identical xdie values). The same tool
on bind_eq_cb16 reproduces the committed constants_cap_eq.json exactly, so the diff below comes from the re-plan only.
17 changed, 5 unchanged:
- COLL_LS / MU_CAL_LS / COLL_F2_L / F3_L / F4_L 391 -> 407; COLL_F2_PHY 353 -> 362, COLL_F4_PHY 353 -> 361 (F3_PHY 343
  unchanged); COLL_F2/F3/F4_R 7/8/8 -> 11/11/11, PEER_R 8/8/7 -> 11/11/11; COLL_BENCH_ARGS
  "--relays 0 7 8 8 --lanes 2 2 12 2 2 12 --lx 14 4 14" -> "--relays 0 11 11 11 --lanes 2 2 21 2 2 20 --lx 23 4 22".
- COLL_SLICE_LEGS landed cmd 8,9 -> 11,12, in 6..8 -> 9..11, out 6,7 -> 9,10 (delta vs as-built -3/-3/-4 -> 0/0/-1).
- XT1_FILL_LEAD_OFFSET 8 -> 16 (all 12 slices: hr 12 -> 20, sw 2, xt 2) -> xt1 lead 24 (from the constants, bind_smoke).
- Unchanged: TREQ_CMD_OFFSET 0, TREQ_HOPS, XDIE_SEAM_C 2,2,2,3,2,2, D2D_TXDP_C 0a010308, COLL_F3_PHY 343.

The bound top RTL is byte-identical to the capacity bind top (sha256 3f91e832...). The re-plan stations and pads sit
inside the partitions (21 carved partition files changed).

Reset: the plan releases by wavefront (root sl_W0_ctl; carve partitions release at cycles 77..116, die max 128;
reset_offsets_meth.json). The bound top still fans rst_n to all 377 arst_n, so the bench NRST 16 matches the vehicle.
The offsets apply only once the bind realises the wavefront.

Build 48 min, peak 79.5 GB (epyc3); sims 5.1 + 6.4 min. An independent re-run of tools/die_plan/xt1_schedule_gate.py on
these logs gives the same verdict: PASS, 16/16 edge groups.
