The oracle compares actual baseline `ot_hgi_qdq_core FIN_BYPASS=1` with actual distinct `ot_hgi_qdq_core_fin2 FIN_BYPASS=2`, from exact parent source `80e1681e0`. No production RTL changes are included. Both receive the same real FR descriptor stream with phases 61/487 ps on an 833 ps period. Default proof uses the closed SPANPIPE1 frontend and CORE admission margin; SPANPIPE0 is an additional diagnostic.

The final r3 runs pass both configurations. The real candidate dependency-ignore MUT=2 fails at the actual beat port on cycle 36210. Every actual issued request contributes one bounded FIFO response and credit; beat pop/fire requires all its real lane responses, and FIN requires consumption of a real last beat. Grant, idle, credits, fires and finishes follow that finite service state. No constant service stub or Python CORE mirror is used.

The independent FR range ledger checks each newly enqueued live dependency mask and prevents a first read beat from starting while an older RAW/WAR/WAW conflict remains live. Every CORE edge compares real ready/retire/fault, request valid/address, beat valid/payload, grant request, active and reset outputs. It also compares queue state and effective dependency masks, allowing the candidate's stale retired columns until deferred clearing.

Across 102 tail wraps and eight simultaneous enqueue/retire events per run, each enqueue checks independent actual retirement history: reuse before two edges and simultaneous same-slot reuse are fatal. The shortest observed reuse gap is 99 CORE edges for SPANPIPE1 and 11 for SPANPIPE0. The source assertions and independent no-live/pending-clear check stay active. This is bounded source-exact stress evidence, not an exhaustive formal theorem over all possible legal streams.

Final SPANPIPE1 measured live-range dependency events: RAW 103, WAR 255, WAW 357; rejected descriptors 204, multirow read walks 1325, credit stalls 24843, full-beat-queue stalls 7025. SPANPIPE0: RAW 103, WAR 306, WAW 511; rejected 204, multirow 1326, credit stalls 24664, full-beat stalls 6848. Four clean phases admit and retire 512/512/512/96 records. Two fault-drain phases each admit and retire three records. Three warm-reset records and one malformed record-count stimulus explain the total 1642 issued record stimuli versus 1638 completed records; the malformed count produces the real sticky frontend nfault. Real staged reset flushes pending service state, and no stale CORE valid survives release.

Evidence directories retain the initial r1 coverage failure (no credit exhaustion), intermediate r2 results, and final r3 logs/manifests. All heavy builds ran through auto-placed `ot-run --mem 4 --threads 4` with the codex coordinator lock verified before each admission; no explicit execution host was selected.

To reproduce, first export the exact source in a fresh directory:

```sh
python3 tools/hgi_unit_tput/snapshot_qdq_core_fin2_oracle.py 80e1681e0 /tmp/core-fin2-pinned
```

Ship the snapshot, bench and runner to each eligible fleet host, then submit via `ot-run` with `CORE_SOURCE_DIR` naming the pinned directory and `OUT` a fresh evidence directory. The runner verifies every source SHA256 before compilation. `CORE_SPANPIPE=0 FR_SPANPIPE=0` selects the diagnostic; `MUT_CAND=2` selects the expected negative. No arithmetic word-golden, native 184/168 price, placement, or timing qualification is claimed here; the parent owns those separate gates.
