# FABLE-DIE-KV handoff (owner of whole-die PD quality for KV qwen_kvsys; started 2026-11-16 07:00 PST)

Scope: die floorplan, die clock network, die GRT, die STA, reset/ft reach, PG, lane latency. Types stay with FABLE-FIX-KV-PVHUB / KV-PVHG-O.
Work dir: epyc9 /srv/opentallas-scratch2/claude/fable-die-kv (shared/ = die chain scripts copied from DIE-KV-ROUTE-1; runs/<tag>). Logs intel2 ~/tmp/fdkv.
Tree: epyc9 kw45/src_kv_kvgeom7yhr_eb1e73448bd0 (= v2 src_kv_pin_eb1e73448bd0 + plan 7yhr 723fd5b4b006).

## In flight
- b7: baseline die kit -> GRT0 TT/FF -> die STA -> count-aligned gate on 7yhr (ot-run epyc9, log intel2 ~/tmp/fdkv/b7.log, run dir runs/b7/CHAIN.log).
  Last die run before this was kvgeom6 p6 (epyc10 die-kv-route-1/runs6/p6, 11-15).

## Next
1. Read b7 + render; verdict in lanes/FABLE-DIE-KV.md.
2. One die plan event (clock + floorplan rows), delta rows to KV-102, proof run.
