# HOLD-PAD-FLOW handoff (lane memory; update at each step)

Job (COORD 11-24 ~08:5x): land a planned hold pad as a normal flow step (per-endpoint pad from FF hold slack, TT setup
headroom check, one-pass insert; default when repair_timing -hold stalls), then relaunch the 8 stalled QC pregrt_ff_hold
kits with it (resume, not rerun). Owner of the kits: QC-ALLFIX (08:56: "go ahead and cancel + relaunch").

## State 09:2x PST
- Lane clone: epyc2 /srv/opentallas-scratch3/claude/HOLD-PAD-FLOW/wt, branch claude/hold-pad-flow-1124:
  0049dd17b7c hold_pad.tcl + pregrt_ff_hold rr pass pads (mode OT_PREGRT_HOLD_PAD rr|all|0, default rr)
  0c62df1994a pregrt_ff_hold.refresh + kit_wave die option pregrt_refresh (true | [fnmatch]) -> run-item regenerates the kit tcl
  NOT pushed yet (waiting for the proof).
- Cause: these kits' pregrt base pass (margin 5) closes in ~12 min; then the rr family pass (margin 40, OLD unbounded form from
  the pinned snapshot qwen_compute_v4c4) calls repair_timing on 62-64k endpoints and never prints a row.
- Proof: epyc2 /srv/opentallas-scratch3/claude/HOLD-PAD-FLOW/p1 (copy of slw_st_b_v1__cle6023ec2 work), unit oth-ubuntu-2015400-1795540303,
  log p1/pregrt_ff_hold.log.
- The 8 gen kits (R6V4, queue.tsv rows): see lanes/posts/HOLD-PAD-FLOW.md. NOPROG-WATCHDOG cancels them ("cancel next pass");
  route-queue infra-stopped resubmits once from the gen kit run dir; otherwise the wave makes a new attempt from the snapshot.
## Next
1. proof result -> push both commits (ot-push-main), rt sync.
2. relaunch: patch the gen kits' pregrt_ff_hold.tcl (copy+mv; pregrt_ff_hold.py refresh) for route-queue resubmits, and set
   qwen_compute pregrt_refresh [the 8 items] via kit_wave_edit for wave relaunches. Post unit names to QC-ALLFIX.
