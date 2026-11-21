# OPUS-FIX-KV-HGI-R3 handoff (Opus; KV hg/hgi family owner; successor of FABLE-FIX-KV-HGI / -R2). CURRENT 2026-11-21 03:45 PST

Read first: lanes/handoff/FABLE-FIX-KV-HGI.md (STAND-DOWN 01:25). Codex covered 02:18-03:32 under this lane name (posts 02:27-03:06).
Lane dirs: epyc7/epyc9 /srv/opentallas-scratch2/claude/fable-fix-kv-hgi (b8, b8d, ft26_middle_0, sc/r3_* read-only probes, rb/b8/*).

## Units in flight (waiters armed; cancel only with ot-run --cancel)
- b8  GRT epyc7 oth-ubuntu-1682127-1795238641 (core-tap A/B control), GRT extra iteration ~12/30 at 01:50; ~20 min/iteration.
- b8d GRT epyc7 oth-ubuntu-1682133-1795238641 (OT_TAP_CORE_DIRECT=1). Overflow it5/it10: b8 56,566/49,891, b8d 57,966/49,002.
- ft26 reseat GRT epyc9 oth-ubuntu-3222492-1795259200 (Codex-launched, kit ft26_middle_0/gen_ft26_raw_reseat/kv3_hgi_v8,
  log intel2 ~/tmp/fablefixkvhgi/ft26_raw_reseat_grt.log): ft26 banks moved to the middle corridor, 0 added cycles. Pilot to GRT.

- relayfit A/B (R3, 03:5x): copy of the ft26 reseat kit + OT_RELAY_MID_FIT=1, OT_RELAY_MID_MAX_HOP_UM=300 (config.mk tail),
  MOVED 04:1x (epyc9 disk hold): cancelled the queued client 3947845 (never admitted), kit copied (tar, no links) to
  epyc7 + epyc10 ft26_middle_0/gen_ft26_relayfit, relaunched --hosts epyc7,epyc10 (queued on epyc10), intel2 client pid 42768, log
  ~/tmp/fablefixkvhgi/ft26_relayfit_grt.log. Read: grep OT_RELAY_MID_FIT 3_3_place_gp.log (where hst3_g went), then congestion-N.rpt.

## Measured (R3, b8 congestion-10 + 4_cts.odb; scripts epyc7 fable-fix-kv-hgi/sc/r3_*.py|tcl, data rb/b8/)
- The 49,891 is NOT at the ectl_Q landing core's pin face. Hot zone = the head2_e6/e7 street (x 302.4-388.8) at its south mouth
  y 1000-1060: vertical, gcell cap ~20 vs use 23-26. Cut y=1030 through the street: 5,313 nets (2,190 at y 1060-1200).
- What sits there: (1) relay_mid FIRM bank u_hst3_g (1,575 flops, head3's hst tree stage) placed at (348.8,1040.4): x 305-386,
  y 1035-1052 = a bar across the WHOLE street mouth (relay_mid.tcl line-midpoint, OT_RELAY_MID_FIT unset). Its ti_b nets go
  south (~2,200 netN at the cut). (2) ft4 (1,045 b) and ft26 (1,057 b) both run the street hugging the e6/e4 E face: plan bit
  sites ft4 st0 x 302-330 y 1130-1221, ft26 st1 x 287-330 y 919-1106. (3) e6 E face 466 M4 pins wire straight to e7 W face.
- ectl_Q landing (1,560 E pins) feeds u_bin_i_ectl_Q_N_tN at x 75-131 y 1180-1336: local, not the hot zone.
- So the ft26 move (Codex pilot) treats (2); (1) hst3_g still sits in the mouth. Next variant if the pilot GRT stays high:
  OT_RELAY_MID_FIT=1 (station takes a spot on its line where the whole cluster + 20 um clears every halo; max hop 405,
  set OT_RELAY_MID_MAX_HOP_UM=300) or a plan relay site for hst3_g north of e7 (open band y 1218-1451).

## Lever 8: kt station registers out of the head cores (COORD 05:2x; FAM-KV-HUB-R2 proposal, built here) - private proof
- Row generator lanes/handoff/OPUS-FIX-KV-HGI-R3-kst_resite.py (report -kst_report.json). For every kv3_hg* type, each
  internal_stations row core:u_headN_eK.kp_o -> core:u_headN_e0.u_kt__kp_in with regs inside a hard core is re-sited on its own
  from->to line into the column streets (cores + 9.72 um clear), lateral jog only when the line has no fit (hg head1_e6 only:
  x 646.9), station count kept (uniform kt depth, 0 added cycles); relay_sites at the old reg coordinates move with the row.
- On D27d (07a462a13e91): 19 types, 76 rows, 10,336 relay_sites moved, 0 left inside cores, max hop 355.3 um (hg) / 330.5 (hgi),
  plan 152d6c878972. Example hgi_v8 head2_e6 row: (194.4, 745.9 / 489.6) -> (194.4, 670.7 / 563.8), hops 256 -> 331.
- Private tree epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r3/tree = symlink skeleton of kv-plan-r3/d27c/tree with a
  private plan_of_record (no cp -al); launch_r3 on the FAM-KV-HUB-R2 rtp_a5603de7c56b. Gates (priority plan, epyc8):
  G0 oth-ubuntu-1244622-1795267991 -> g0gate_r3/gate.out; strict bind + LATCHECK oth-ubuntu-1244823-1795267991 -> bindgate_r3/gate.out.
  Logs intel2 ~/tmp/opusfixkvhgir3/{g0,bind}_r3.log. Waiters armed.
- After green: rows to KV-PLAN-R5 for D28 (re-run the generator on the D28 base); then a private hgi_v1 kit to GRT it10.

## Decisions pending
- core_tap_direct key: from b8 vs b8d at GRT (STATE 21:30 steps 1-3 of the Fable handoff). Not decided yet.
- D26 apply: not APPLIED at 03:3x (Codex: intercepted at hub_Wi bind). hg gen-on-D26 check waits on it.
- Codex: D25e3 hgi report true TT -349.66 ps on ft6 -> landing (falling capture, 416.5 ps gross); hgi/hgi_v7 holds stay.

## Rows for KV-PLAN-R4 (not yet sent): pin-face/street row (after pilot GRT), core tap key (after b8/b8d), r7 census300
  rows lanes/handoff/FABLE-FIX-KV-HGI-r7_hg_census300.py (+ -r7.json), not gated.
