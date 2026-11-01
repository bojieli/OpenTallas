# Claude -> Codex handoff 2026-11-01 05:32 PST

Claude (pane 0:0.0) is about to hit its usage limit (reset time not shown yet; check pane 0:0.0). Your role and rules: /home/ubuntu/coord/CODEX-ROLE.md. **Read the full current handoff first: /home/ubuntu/coord/HANDOFF-COORD-1101.md** (state, merge queue, owner rules of 11-01, failure classes, per-die open items, live lanes, recurring duties). It overrides older sections of CODEX-HANDOFF.md. Then the tail of lanes/COORD-REVIEW-QUEUE.md from 05:30 PST and answer every READY/ASK without a [COORD] reply. Log to CODEX-LOG.md and HANDOFF.md (prefix `CODEX:`); when Claude is back, write `## Handoff to Claude <time>` in CODEX-LOG.md.

## Most important owner rules from 11-01 (binding)
1. Older pass still counts as a pass.
2. Handle failures in BATCHES by class, never one by one (class fix default-on + canary all dies + batch relaunch).
3. No rentable machine: KEEP THE ot-run QUEUE FULL on every host (>= 8 h queued); pilot volume queued behind pilots at lower priority; autopilot.timer on intel2 runs the kit wave with no agent alive.
4. QC<->KV link calendar: MU single-seq image-driven on BOTH dies (QC u_cseq change by DIE-QC-59Q).
5. 12.28b closure first, no new restrictive rules; rule at once; owner questions in plain text with recommendation + default.

## Merge queue (ROOT-MERGE-AL, merge-train form)
mchan2 220358646e6 -> s81 childlib 61fee51a46f -> kit-triage-1 int f9cb0e099d6 -> hbm hb4 b26a827db45. HELD: qc suw-lec 4a8040d537e (needs su collector delta). Do NOT merge kit-triage-1-s81lib 9d4908b832a (duplicate).

## main
16de74978 2026-11-01 04:27:17 -0800 Merge claude/hbm-clkloc-7-1031 (HBM C12 configs + die_trial opt-ins)

## fleet
```
ot-run status: epyc2 admits 34 GB (avail 293, reserve 0, fresh 48, peak 147) load 79/128 run 27 root 2% scratch 171 GB | intel1 admits -30 GB (avail 291, reserve 0, fresh 146, peak 111.3) load 208/112 waiters 4:334 GB run 49 root 9% scratch 679 GB | localhost admits -89 GB (avail 82, reserve 0, fresh 0, peak 106.6) load 229/112 waiters 10:562 GB run 38 root 14% scratch 738 GB | next 16-thread 32 GB job -> epyc2
```

## Live Claude lane agents
They pause with Claude's limit; their fleet jobs keep running. Lane files ~/coord/lanes/<LANE>.md (PARKED/last lines = collect chain): ROOT-MERGE-AL, FLOW-21, SIGNOFF-SPRINT-17, KIT-TRIAGE-1, KIT-WAVE-13, GEOM-102, GEOM-103, DIE-S81-47, DIE-QC-59, DIE-KV-60, DIE-HEAD-53, DIE-HBM-57, HBM-CLKLOC-7, HBM-CORES-KITS-40, S81-CORES-KITS-13, HEAD-SERDES-3, KV-FN-7, TOK-DS-2, TOK-QK-2.
