# COORD handoff — 2026-11-01 05:3x PST (Claude coordinator, near rate limit)

Read this first after a limit. Then the tail of `lanes/COORD-REVIEW-QUEUE.md` from 05:30 PST onward, and act on every READY/ASK that has no `[COORD]` reply.

## 1. State in one screen
- **Sign-offs: 48 hard cores.**

  | Die | Signed |
  |---|---|
  | S81 | 22/54 |
  | HEAD | 3/4 |
  | QC | 5/15 |
  | KV | 14/35 |
  | HBM | 4/84 |

  Types: 0 of ~485.
- **main** = 16de74978. Merged today:
  - lecsib2, clkauto, reaper, KV taps, hroot geom2, twomode, kv phy
  - s81 kva3 (plan 381e75b001cd), kvtap, kv-fn-7, hubeo, rstc
  - fp8r, ctsprot, fgorig, kv phytap, hbm clkloc7 (92a83cbcc5f)

  Check with `git log origin/main` whether the queue below has landed.
- **ROOT-MERGE-AL queue (approved, merge-train form):**
  1. QC mchan2 220358646e6 (replaces 069b9d698c0)
  2. S81 childlib 61fee51a46f (105 S81 types leave WAIT-DEP; provisional child ETMs approved)
  3. KIT-TRIAGE-1 int f9cb0e099d6 (replaces g7 a8214309dc0 + g26 63bf14bc1f6)
  4. HBM hb4 b26a827db45

  - HELD: QC suw-lec 4a8040d537e, until DIE-QC-59 posts the su collector delta (strict bind gave 5 errors on sle_su_l0).
  - REJECTED duplicate: kit-triage-1-s81lib 9d4908b832a.
- **Hosts:** all saturated (intel1 ~177/112, intel2 ~192/112, epyc2 ~85/128). Scratch 79-80% after PRUNE-1101 freed 709 GB (manifests in `lanes/PRUNE-1101-*.tsv`). The ot-run hub is intel2 (`ssh -o ControlPath=none intel2 ~/.local/bin/ot-run --status`); epyc1 is retired.
- **Codex** is usage-limited until 11-04 02:59 and did not cover the 02:07-03:1x gap. No new Codex handoff.

## 2. OWNER rules made today (binding, also in memory)
1. **Older pass still counts as a pass.**
2. **Failures in BATCHES, never one by one:**
   - group by stage and reason;
   - one class fix, default-on, canary on all dies;
   - batch relaunch of the whole group;
   - hourly class table from `autopilot/kit_wave_stages.tsv`.
3. **No rentable machine; KEEP THE QUEUE FULL** (agents hit rate limits):
   - every host has waiters, target ≥8 h of queued work;
   - pilot-first no longer keeps volume out of the queue: volume is queued behind its pilot at lower priority, and a pilot class failure cancels queued volume;
   - the autopilot timer on intel2 (autopilot.timer) must run the kit wave with no agent alive;
   - lanes queue their next 2 variants per item at once.
4. Approved the QC↔KV pair-calendar die form: **MU single-seq, image-driven, on both dies** (what KV boots). QC u_cseq on qfd_sys_face_lctx3_core is changed by DIE-QC-59Q (branch claude/die-qc-59q-cseq-1101).
5. Standing from before:
   - 12.28b: closure first, no new restrictive rules.
   - Rule at once; never wait for COORD.
   - Owner questions in plain text with a recommendation and a default.
   - On a safeguard cut, just continue.

## 3. COORD speed-up rulings 05:1x (in queue file)
- **FLOW-21:** pre-route LEC no longer gates placement. It runs in parallel; sign-off still needs EQ.
- **ROOT-MERGE-AL:** merge TRAIN, one full test run per combined tip.
- **KIT-TRIAGE-1 G5:** post-CTS FF hold is INFO at 4_cts (hard stop only below -150 ps). Route with HB4 hold repair; hold is judged at routed sign-off (+10 ps).
- **G7:** clock_reach is INFO at 3_place when a kit has 0 fixed clock cells; judged by clock_leaf_reach ≤220 at 4_cts.

## 4. Type-kit failure classes (autopilot/kit_wave_stages.tsv at 04:2x: 421 FAIL / 45 RUN / 0 signed)

| Class | Count | Owner / fix |
|---|---|---|
| geom G7 | 105 (most fail on real items, 8 released) | KIT-TRIAGE-1 + per-die tap fixes (HBM 14 single-root cores → DIE-HBM-57; HEAD hd_tile clk_t12; S81 t48 tap b3e8508b64d READY ~06:00) |
| gen G1 child libs | 84 | childlib 61fee51a46f; 23 still WAIT-DEP → DIE-S81-47 provisional-ETM batch |
| tool G2/G6 | 26 + 17 + 17 | classifier in int f9cb0e099d6, then `kit_wave.py reclassify --write` and `rejudge-geom --write` |
| contract metadata | 19 | KIT-TRIAGE-1 |
| route post-CTS hold G5 | 17 | HB4 hook cross-die + INFO ruling |
| place GPL-0305 G4 | — | plain-GPL fallback extended to core and type kits |
| KV hgi ×10 PORT_BIND, KV pc/hg macro not declared, KV qkd_hr NO_RECIPE ×15 | — | DIE-KV-60 |
| QC cb* per-instance params | — | DIE-QC-59C |
| QC sle_st_b LEC (64-edge contract in type kits) | — | DIE-QC-59 |

KIT-WAVE-12 batch-relaunched 171 kits (S81 125, KV 23, HBM 21, HEAD 2) at 04:27.

## 5. Per die: what is open
- **S81:**
  - Die GRT and die clock PASS.
  - Tiles 22/54: crs4, gunit_l1, xrt1, bf_front_roots, xfin (S81-CORES-KITS-13).
  - t48 tap fix pending.
  - TOK-DS-2 is building the whole-die Verilator token sim (it hit an OOM in lint; split per type/quadrant if needed).
- **HEAD:**
  - 3/4. The last core is kp4_dchn / hd_serdes (HEAD-SERDES-3).
    - Best variant so far, e5b: 0 DRC, TT -19.58.
    - e6a/e6b fix the long-wire cause and are in DRT.
  - hd_host_n:
    - a2 FAIL: launch/capture tap skew 198 ps.
    - b2 ~05:40, c2 ~06:30 (`grep OT_POSTCTS_GATE dh53/host_{b2,c2}.otrun.log` on intel2 die-head-48).
    - The fix is the shared H1/H2 tap-balance class.
- **QC:**
  - 5/15. su_lane chain: rstc merged; suw-lec held; fp8r merged; etap 4f3b5831db6 + l1 CTS probe; then su collector delta.
  - A0 NK/NL fail LEC (NK 7 points u_me.nb, NL GPL then LEC), DIE-QC-59.
  - Owner question still open from the 10-30 Codex handoff: QC PHY 30-µm M9 contact pad. Default: modeled contact contract.
- **KV:**
  - 14/35. Die clock passes except hold on real views (37,674 pairs unmeasured until kits).
  - KV-FN-7: the next token abort is at kv 42327 (far KVN port-3).
  - core_tx re-signed (TT +24.41 / FF +4.62), LEC due ~08:30 (SIGNOFF-SPRINT-17); KV stays 14 (replaces the old record).
  - kv3_phy CTS hold -515 ps is fixed structurally by phytap (merged); re-cut by KIT-WAVE-13.
- **HBM:**
  - 4/84.
  - **Die GRT:** 605k overflow is local:
    - bus L15x1 stations are clumped in 4 E-strip columns of q_b011pv1 (11% avg use);
    - b101_nw has the same class (1.37M).
    - Variants:
      - p1/p2 (strip widening, partial);
      - **p3** (per-bit sites at each bit's pin y, columns across the full width, L183x2 over ≥4 rows), ordered at 04:0x.
    - Also a 41-type class sweep.
    - b110 50-it = 0 (PASS).
    - The 50-it GRT takes ~13 h and is single-threaded (run with --cpus 2).
  - **Die clock:** T010 CLOSED. 41 CA start-tree edges remain; HBM-CLKLOC-7 fixes them as one class (start relay / max-hop, 2 variants).
  - **Cores:** HBM-CORES-KITS-40 classes:
    - LEC batch of 6 (intel2 hbm-cores-kits-39/lecb);
    - near misses (tnode, HCOL kA, QUERY);
    - HB4 on tailx_rest ×2 + exp0;
    - >50 cast forms in rtl/hbm_accel to fix before preflight.

## 6. Lanes (agent IDs in /home/ubuntu/.claude/jobs/b7f906df/tmp/agent_ids.tsv; grep before SendMessage)
- Live:
  - ROOT-MERGE-AL, FLOW-21, SIGNOFF-SPRINT-17, KIT-TRIAGE-1, KIT-WAVE-13
  - GEOM-102 (B), GEOM-103 (A)
  - DIE-S81-47, DIE-QC-59 (+59C, 59Q), DIE-KV-60, DIE-HEAD-53 (+ helpers), DIE-HBM-57
  - HBM-CLKLOC-7, HBM-CORES-KITS-40, S81-CORES-KITS-13, HEAD-SERDES-3, KV-FN-7
  - TOK-DS-2, TOK-QK-2
- If a lane is dead after the limit:
  - start a fresh agent with its lane file PARKED/last lines plus `lanes/_FRESH_LANE_BRIEF.md`;
  - the briefs are in `/home/ubuntu/.claude/jobs/b7f906df/tmp/r1231/`;
  - always add: batch rule, queue-full rule, continue on safeguard cuts, until-loops, delete only own dirs, .keep.
- Not started yet: an HBM whole-die token lane (start it once TOK-DS-2/TOK-QK-2 run).

## 7. Unowned items
- CLOSURE-LIST S81-007 (18 G0C die errors).
- KV-023 (regen constants not re-run on plan_c).

Assign them to DIE-S81-47 and DIE-KV-60 as batch items.

## 8. Recurring duties (crons in this session die with it; re-create after restart)
- **LOOP-GAP** about every 20 min: READY/ASK older than 30 min, GEOM REQ older than 20 min, PARKED lanes without a successor.
- **Hourly at :19:**
  1. ot-run status and disks on all hosts.
  2. `python3 tools/release_tree_render.py --summary`.
  3. Append to `lanes/SIGN-RATE.tsv`.
  4. Failure-class table.
  5. View 2 GEOM renders.
  6. Refresh RELEASE_TREE.md (header line 3 + body).
  7. Append a HANDOFF.md line.
  8. Check every host has queued work.
  9. Prune when scratch is below 15% free (manifest first; never PROTECTED-DBS or .keep paths).
- Coord commits only via `timeout 280 ~/coord/bin/coord-commit.sh "msg" files`. Verify with `git fetch -q origin coord/state; git show origin/coord/state:<file> | grep -c`.
