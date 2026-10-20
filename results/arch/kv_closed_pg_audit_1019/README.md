# KV closed-leaf native PG audit, bounded first pass

Verdict: **PG_HOLD** for the two exact CDC closures below. Their CLOSED timing/DRC history is preserved. This audit changes no database, RTL, bindings, constraints, helper, or verdict.

| Leaf | CLOSED source / record | Final ODB SHA256 | Instances | Native PG MTerms | Correctly bound | Missing bindings | Missing on protected instances |
|---|---|---|---:|---:|---:|---:|---:|
| cdc_pc | 50430b600 / 7b4518d85 | af9ddb3ee76b3bfe6e02686059b8b501608d6a0ee1dab2bf772cd67d9f535b41 | 374024 | 748048 | 158526 | 589522 | 6770 |
| cdc_host | 53973e6bc / 03e3a8b12 | 46d3abdd2225eb17c879ca24b92d3c4964b0abf00d808e8d975d454b26d89f09 | 527054 | 1054108 | 96642 | 957466 | 3942 |

Each supply has half the reported terminals/counts. All failures have NULL actual net; expected supply is unambiguous VDD or VSS from the native global-connect instance rule and exact dbRegion. No missing ITerm, wrong nonempty net, ambiguous mapping or unknown domain was found. Every instance is traversed, then every native master POWER/GROUND MTerm is resolved with findITerm; protected CTS, filler, hold and physical-only cells have no exemptions. The native master PG dimensions/roles/shapes are snapshotted and hashed independently in summary.json. Full per-instance pins and master/protection/category breakdowns are committed, compressed.

## Released identity and causal scope

Committed CLOSED verdicts explicitly identify these exact source commits, host and run paths. The frozen released export_tt.tcl files byte-match their CLOSED committed copies and read these exact `6_final.odb`, `6_final.sdc`, and `6_final.spef` files. Final and installed-ECO ODB/SPEF hashes match (see manifests). The record does not contain an original ODB content hash, so this audit pins the presently preserved released final bytes; the export paths, source identity and installed-ECO byte equality establish provenance without inventing a historical ODB hash.

Both are post hold-ECO final databases. Frozen hold_eco.tcl removes fillers (line109), inserts hold repair cells, places fillers (437), and writes final ODB (445), with no global_connect invocation anywhere in that script. The frozen eco_install excerpt copies the ECO final ODB/SPEF into the same released route path. The master/protection matrices show missing unprotected hold/filler bindings as well as protected buffers, so a protected-CTS-only binding fix cannot close these receipts. No causal repair experiment was run; the ordering is source evidence, not a claimed complete fix. The original route 6_report logs claim PSM all VDD/VSS shapes connected, but those are net-only results, not a final all-native binding proof, and predate the installed ECO output.

## Read-only execution

Unpinned ot-run, 8GB/1thread, no-spill because final ODB is an external immutable input outside the small audit directory. cdc_pc terminal unit oth-ubuntu-3658909-1792442070 (ep4), cdc_host oth-ubuntu-1959148-1792442070 (agidock128), both actual exit0. Successful logs report 748048/1054108 master PG terminals and 589522/957466 failures respectively. Initial attempts units3656918/1958725 exited127 because openroad was not on PATH; no ODB was read then. Corrected invocation uses the exact absolute binary path. Image IDs/digests are in each image.txt. The copied IDX source-only helper SHA13e936d24fc2a2e35a9f8cc0c6047820753cb5cc8a559a13a7eb8fe56e1ebef3 is immutable; audit uses only prepare/expected read-only methods, never its binding callback. Our independent master-MTerm loop also detects missing ITerms.

## Bounded coverage and next selected inventory

These two recent host CDC closures are candidate host children; this packet does not establish that the frozen GEN8 die actually binds either. Frozen5f2ce19bc-gen8v3mub lane_views.tsv identifies16 relay/landing closure refs plus D2D r7t, copied verbatim here. Those17 exact selected views require a fresh all-native PG audit, ordered by parent binding. tile_views.json has bind={} and seven ASSUMED main KV tiles: historical CTL/EMB/ATTN CLOSED records must not be described as actually selected. Hroot_k1 is selected as a diagnostic stand-in after native failure; DCAL_bc bootcfg selection is a separate scope. This is explicitly a bounded first pass, not all-KV coverage.

Actual master pin-shape/contact/via connectivity to the supply network remains OPEN. Correct logical net membership alone cannot prove physical PG contacts, and this audit does not claim that missing logical bindings imply every physical rail contact is absent. ROOT owns source/helper repair design, domain/contact validation, later reruns and any adoption decision.
