# HEAD compiler witness and schedule on l48un (TOK-HEAD-1, 2026-11-07)

Replaces the 10-30 witness in `head_root88_compiler_1030` (plan 655784af, sidecar 02dece).
`tools/s81_dv/layer_prog/head_root_boot.py` now pins plan 340743d8 (l48un), sidecar 90d006,
START tree 255b2b4e, START SV e9ed25cd, and refuses the 10-30 bundle. Status stays
SOURCE_WITNESS_ONLY: no physical START, HOST, PMA or mission date. Parent bind on l48un is
DIE-HEAD-81's and is not run here.

No whole-die token ran. Tok/s below is an estimate.

## Rebuild

    make_bundle.py REPO BUNDLE                          # from plan_of_record/l48ui only
    qualify.py REPO BUNDLE OLD_10_30_BUNDLE OUT         # witness controls + schedule
    qualify_pipeline.py REPO BUNDLE RUN OUT.json        # two-job compile_pipeline, TEST date books

The bundle is about 30 MB and regenerates exactly, so it is not committed.

## Measured

**Rings** (`tools/s81_dv/head_n4_age_1107`, Verilator, main l48ui wrappers, top and START tree,
literal reset/START control of 357 parts, retained 1608-clock TT/FF phases).

- `age_n4/`: on all 4 links, TT and FF, age(FREG, K 41/13) - age(old form, K 39/11) = +1.
  FREG ring with K 39/11: ready0 fault1 on all 4 links at both corners, so a mismatch faults at
  boot. K+1 stays in window, age +1, no fault.
- `all_rings/lat.json`: all 427 rings. The 11 ports with added_cycles 3 and sched_lat 4 measure
  4 at TT and 4 or 5 at FF, never 3, so sched_lat is the true count and those rows are stale. They
  predate the n4 event.
- Same result on the exact6 parent: 0 differences in cycles, same faults.

**Boot bounds** recomputed on l48un, unchanged: settle 88, root START 110, part START 382,
ready-or-fault 5861.

**Schedule** (`tools/s81_head/regen_schedule_constants.py --landed-sidecar`), HEAD transport:

| Input | Transport (cycles) |
|---|---:|
| plan l48un latency.lanes alone | 332 |
| + the 4 n4 links only | 332 |
| + sidecar 90d006 by sched_lat (n4 and the 11 stale ports) | 336 |

The 336 is spine 174 (slice 5 W) + 2 x worst gather m0S_rx 81. 13 lanes change, 15 lane-cycles.
plan latency.lanes carries neither the n4 +1 nor the 11 ports; gen.py latency gives the same 332.

## Estimate

Serial bound on the 1258.9 tok/s model (T 953,595 cycles), which is not lane-driven:

| Charge | Tok/s | Change |
|---|---:|---:|
| n4 +2 (one u and one d link in a token) | 1258.8974 | -0.00021% |
| n4 +4 (all four links serial) | 1258.8947 | -0.00042% |
| n4 +4 and transport +4 | 1258.8894 | -0.00084% |

The model may already include part of the 11 ports; that was not checked.

## Open

- Literal rings that fault under the retained phases: TT lk_ES0.coll_i0, lk_WN1.coll_i0, tE1o0.i;
  FF sp0 ad/bd/hd/x (Codex head_guard_1107), sp5 au/bu/hu. These are not caused by l48un (same on
  exact6) and are functional phase-model results, not routed STA.
- 78 rings read one cycle apart between TT and FF in the nominal frame; about 8% differ from
  sched_lat at each corner. Likely START origin sampling under the retained phases; not analysed.
- Two 1-bit rings (lepf__0, head_lep_fault_return__0) cannot carry the word count, so their
  reading of 50 is an artefact.
- `coll_*` lanes have no consumer in tools/s81_dv; only this schedule tool reads them.
- The plan names assets/sink_bins_N.json but main stores .json.gz, so tools that read the bins
  fail on a clean checkout. Noted for DIE-HEAD-81.
