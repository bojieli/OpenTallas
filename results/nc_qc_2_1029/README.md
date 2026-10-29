# NUMBER-CHECK-QC-2 — independent check of DIE-QC-34 QC provider PG materialization + census

Target: `claude/die-qc-34-1029@c6953bc4c02` `results/qc_die34_1029/pg/README.md`. Checker is not the author.
Run dir: intel2 `/srv/opentallas-scratch2/claude/nc-qc-2` (own scripts copied from git, own pydeps310, own outputs).

## Verdict: CHECKED (every README count matches)

| README claim | Own evidence | Result |
|---|---|---|
| source provider.odb sha ddab9669 | `input_sha.txt`; same sha in committed `codex/qc-import-0824` complete_pg_candidate.json | MATCH |
| 185,698 contacts, 109,168 groups, 2,947,537 rects, 873,344 vias, 0 unresolved | own count from access_plan.json/reserved_access.json (`indep.json`, `dedup.txt`) | MATCH |
| 48,259 provider + 44,590 CKINV cells = 92,849 | own: 48,259 in all_cells.json, 44,590 others are all `ck_*` CKINVDCx16; 0 missing in the ODB | MATCH |
| canonical grid 13,304 stripes | own long-M8/M9 count 6,653 VDD + 6,651 VSS | MATCH |
| +2,602,853 rects, +867,296 vias (rest duplicate) | own: unique dbu-rect set of the plan = 2,602,853 (0 overlap with grid); unique via keys = 867,296 (6,048 duplicate shared-stack vias); own ODB delta wires 2,616,157 = 2,602,853 + 13,304, vias 867,296; source ODB had 0 PG SWires | MATCH |
| non-PG hash unchanged | own different fingerprint (inst name/master/xy/orient/status + signal net iterms/bterms/wire length): a9f0284e src == out, 93,226 insts, 92,852 signal nets | MATCH |
| provider_pg.odb sha 96515c35 | own rerun of committed materialize_full.py (paths only changed, `mat_nc.py`) with own pydeps310 (shapely 2.0.6/numpy 2.2.6, Python 3.10.12): output BYTE-IDENTICAL sha 96515c35 | MATCH (no hand edits) |
| census VDD 92,849/92,849, VSS 92,849/92,849, 0 failed | own rerun of committed run_census.sh/pg_conn_census.py on their ODB: identical census.json (shapes 2,268,556/2,267,891, grid comps 5,829/5,794) and identical per-layer counts | MATCH |
| census can fail | own mutant (all 54,584 VDD VIA12 deleted): VDD 0/92,849 connected, VSS 92,849/92,849, FAIL; shapes -109,168 | CAUGHT |

Provenance: committed scripts on the branch are byte-identical to the run-dir copies; mixed_apply_access.py ==
`codex/qc-import-0824` results copy (sha 499873b3); pg_census.py == codex results/qc_pg_access_1029 (e213862f);
infra_replay.py == main tools/die_plan (a595ab57). The scripts live in results/ (Codex/lane), not in tools/.
Inputs (provider.odb, pg_candidate, readback) are Codex run-dir artifacts; only provider.odb and the counts are pinned in git.

Not established (agrees with README): grid has 5,829/5,794 components per net (no M8-M9 grid vias), so "reaches a canonical
stripe" is not whole-grid continuity; native-cell PG, DRC, IR, clock route open. No freeze claim.
