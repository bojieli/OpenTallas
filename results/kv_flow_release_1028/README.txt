KV per-die flow release candidate (2026-10-28 takeover)

Requested tag: flow-20261029-a-kv
Exact tag target: 3e7fccd2164499bced1d58a3dc2d6be23bf3fda1

This is the exact source of all four physically signed e1/e2/e5/e6
archives. Tagging current main cannot qualify them because its watched
flow differs. No source, timing, or canonical baseline is modified here.

Existing exact-source KV core canary:
intel2:/srv/opentallas-scratch2/claude/flow-canary/runs/qwen_kvsys_core_3e7fccd21_1028_065630_929547
canary.json: canonical NO-REGRESSION, LEC EQUIVALENT, routed SPEF TT/FF.
Actual signoff_hold/signoff.json: SIGNED, TT setup +1.43 ps, FF hold
+1.27 ps, hold endpoints 0, overflow 0, DRV 0. Canonical baseline
deltas TT -0.79 ps / FF -1.65 ps within unchanged -10 ps tolerances.
The absolute INFO FAIL compares the old +36.61-ps golden and notes TT
pin-register mean 290.71 vs 250+40 by 0.71 ps; it is not canonical
regression and is preserved unchanged. The recorded SIGNED result
is not a claim that any current die gate or plan passes.

Archives already physically SIGNED (same source target above):
879969d886af kv3_head_eighth_e1
7b0052de79b5 kv3_head_eighth_e2
36fd0f34e1e2 kv3_head_eighth_e5
fcf8ef4a925f kv3_head_eighth_e6
All at localhost:/srv/opentallas-scratch2/claude/autopilot/closed/qwen_kvsys/<type>__3e7fccd216
Autopilot retry_unversioned resolves a matching tag and promotes them
at its next ordinary tick; do not reroute or rewrite old verdicts.

Release action belongs to ROOT-MERGE. This packet creates no tag.
