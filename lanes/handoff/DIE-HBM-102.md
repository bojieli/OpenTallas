# DIE-HBM-102 lane handoff (HBM die owner, phase 2). Started 2026-11-13 00:5x PST.

## 1 Scope
Successor of DIE-HBM-100/-101 (both stopped). Job: HBM plan event pEv11 from the pEv10 open list (whole families, one event), then post READY and stop.
Base: pEv10 b334c92f7a84 (main train 26, events/hbm_pEv10_1112/). wbq v8 on main (train 27). kitist tools on train 31 (claude/hbm-kitist-1@deea4319e1, queued).
Owner rules: event posts when current gates pass; new non-functional findings -> open list; structural first, whole families; visual gate GOOD/OK/ISSUES-ACCEPT; core shapes frozen (move/rotate); growth/cycles/perf pre-approved.

## 2 Locations
- Worktree: epyc7 /srv/opentallas-scratch2/claude/die-hbm-102/wt (clone of hub:OpenTallas, branch claude/die-hbm-102-wt = origin/main a7d4a13623).
- Plans: epyc9 /srv/opentallas-scratch2/claude/die-hbm-102/plans/<plan>/die_plan.json (pEv10 copied with cp -a, sha b334c92f7a84). Scripts: epyc9 .../die-hbm-102/scripts/.
- Predecessor builders/gates: epyc9 /srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane/hbm101/ (mk_ev*.sh, g0_*.sh, latcheck.py, pairsym.py, bindEv10/bind.sh). Plan tools tree: epyc9 /srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18.

## 3 pEv11 items (status)
1. TIMING-CLASS SKEW q_spb1/vsN1/vsN2: lockup latch on the RECEIVING (capture) tap. Mechanism exists: plan clock.ft_hop_lockup.tap {type:{slot:{k:"capture"}}} -> gen_phys OT_HOP_LATCH_CAPTURE_TAP -> clock_taps.tcl re-hang + grt_pre HOPLATCH-HOLD 30 ps pad. pEv10 has vsN1/vsN2 L201 hops on "launch" (form A' launch + frac 0.95); q_spb1 has none. Plan: every latched hop of the 3 types -> "capture".
2. 4 BAD forms q_su30/q_su20/q_su00/q_spu1 (GEOM-VIS-10 17:12/17:43 lines): new forms. q_b000 cap check for pad_landing +16k.
3. NW_io mirrored station spread of NE_io pR9b (GEOM-2 00:49: NW_io a30 GRT-0232 overflow 68,651, x 118-647 y 1088-1312).
4. q_b010 pair0 x 203.04 -> 177.12 (13.8 um pinch; DIE-LAYOUT-HBM b010pinch.py).
5. hidx_s3 prefix adder, hnx_fused_lane_c SRAM wdata regs + clock balance, splitstrap: core RTL items (open list / core lanes).

## 4 COORD inputs 00:5x (HBM-GEOM-2 stopped)
- PHY_NC / PHY_NW attempt_1 (epyc7 hbm-geom-2/builds/hg2/items/PHY_N{C,W}/attempt_1): HBM-GEOM-3 is NOT alive (last log 11-12 17:07). Both route attempts ended NOT SIGNED on the SAME structural class: single clock tap (config OT_TAP_PITCH_UM = W, log "OT_CLOCK_TAPS single tap"), clock insertion 800-970 ps, NC CTS setup WNS -736 / hold -847, NW GRT hold -996 on 3628 endpoints (hold repair capped). pEv10 already carries phytap3 (tap_edge_y 1032.16, pitch W/3 = 3 taps). Decision: do NOT route attempt_1; the pEv10 re-kit rebuilds PHY_NC/NW in the 3-tap form.

## 5 Gotchas (inherited)
- Copy a plan with cp -a of the dir (sidecars). G0 schema errors short-circuit. die_trial is station-blind; fabric.py is station-aware.
- coord-commit can lose an append: verify with git show origin/coord/state:<file> | grep -c.
- Branches go to hub:OpenTallas; verify with git ls-remote from /tmp on intel2.
