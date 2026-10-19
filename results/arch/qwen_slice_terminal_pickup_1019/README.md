# Existing SAFE-QW-SLICE terminal pickup, 2026-10-19

Read-only receipt pickup. No synthesis, simulation, gate, source activation, restart, cancellation, or parent regeneration was performed. This packet contains results only and must not import the old source branch.

## Regional reset diagnostic

Original ep8 unit `oth-ubuntu-1080786-1792434153` ended at 11:23:48 PT: 75.592 s wall, 75.576 s CPU, 14.6 GiB observed memory peak. Exact command is retained in `regional_scope.log`. Its input is the original 2,085,431,332-byte primitive JSON, SHA256 `afe2519df70fbb418ac52162a822882ca91011361a8da2e68c1b5b89f83784bc`; it remains on ep8 and was not copied locally.

The completed report counts **3,749,291 primitive cells, 29,211 reset nets, 6,400 reset nets above 32 loads, maximum 10,033 reset pin loads**. The complete 104,516,973-byte report and 56,523-byte summary are losslessly preserved in `regional_raw.tar.gz`, together with the exact original source archive, source manifest, run script, and diagnostic helpers. All 40 manifest entries match actual frozen files, including helpers. The parent source is f543b8717 with VM candidate 5c0e7bfc9; final station, stream, and native head composition was not integrated.

The executed `run_v2.sh` uses `read_verilog -defer`; the older manifest command omits `-defer`. Preserve this difference: the run script and terminal Yosys footer are the actual execution evidence. Yosys 0.68, git 38e001a6f, reports terminal synthesis with 21,275.70 MB peak. The complete 139 MB log and 2 GB input remain at `ot-epyc8:/srv/opentallas-scratch/claude/safe-qw-regional-endpoints-1019-v2/out/`; their exact hashes are in `regional_identity.json`.

Hierarchy expansion includes retained soft modules and hard-candidate interior RTL. No reset-load exclusions or hard-child waivers were applied. Category labels are explanatory, and the worst head/SFU reset aliases fall under `other_soft_or_unclassified` because their generated hierarchy includes an additional genblk scope. The raw paths, individual loads, and totals remain authoritative. These primitive results establish a reset fanout failure for this frozen diagnostic source; they do not establish real mapped native cell area, native all-role fanout, reset two-stage release, clock phase/spread, first-use, PG binding, pin access, 405 um reach, placement, routing, or TT/FF timing.

## Original station and CFG jobs

All eight old R8/R10/CFG scopes have terminal consumption receipts. Complete retained trace/event files, generated Verilator input identities, and build logs are archived in `station_raw.tar.gz`. `station_identity.json` hashes all actual source/tool inputs from each generated `__verFiles.dat`, the exact binaries, raw traces, and build logs. Verilator is pinned to 5.050. Source input identities are complete: 40 per station run and 17 per CFG job, with no missing files. Scope start commands preserve the exact parameters and work paths.

The original bench stdout was streamed to expired client sessions and is not retained in these run directories or scope journals. Therefore the new functional verdicts are **UNKNOWN**, not PASS or FAIL inferred from completed builds, binary presence, trace length, or terminal resource records. No bench was rerun and no new comparison was substituted. R7's previously collected all-ten E/W PASS and intended MUT14/MUT15 failures remain prior evidence in SAFE-QW-SLICE_RETURN_1124.md; this pickup does not extend those results to R8/R10. The corrected four-update CFG positive and intended early-write guard failure remain unqualified without original terminal stdout. The dirty 32-update enhanced CFG witness and no-epoch physical API were not run.

| Existing run | Unit suffix | Terminal resource receipt | Functional verdict |
| --- | --- | --- | --- |
| r10_e | `1881564-1792433616` | 1h 44min 38.666s CPU time over 27min 6.800s wall clock time, 24.2G memory peak. | UNKNOWN |
| r10_w | `1881741-1792433616` | 1h 44min 57.818s CPU time over 27min 12.944s wall clock time, 24.1G memory peak. | UNKNOWN |
| r10_m14 | `1881556-1792433616` | 1h 43min 17.987s CPU time over 24min 50.675s wall clock time, 24.1G memory peak. | UNKNOWN |
| r10_m15 | `1881523-1792433616` | 1h 43min 41.827s CPU time over 25min 24.111s wall clock time, 24.2G memory peak. | UNKNOWN |
| r8_e | `1833894-1792432760` | 1h 24min 43.369s CPU time over 26min 56.296s wall clock time, 33.8G memory peak. | UNKNOWN |
| r8_w | `1833891-1792432760` | 1h 25min 733ms CPU time over 27min 9.168s wall clock time, 33.8G memory peak. | UNKNOWN |
| cfg_positive | `1895606-1792433774` | 26min 59.295s CPU time over 13min 4.853s wall clock time, 4.9G memory peak. | UNKNOWN |
| cfg_mutant | `1895580-1792433774` | 27min 3.381s CPU time over 13min 30.638s wall clock time, 4.7G memory peak. | UNKNOWN |

R10 snapshots inherit rejected blanket `SYNTHESIS` epoch-zero source from 9a86 through 3ed184c54, although station simulation does not define SYNTHESIS. **Do not adopt that branch or infer native qualification from it.** The generic restoration and untested separate physical no-epoch successor remain outside this results packet. The rejected 76,682 FF diagnostic is not an approved area result; the generic predecessor contains 12,375 assertion-only writer epoch/counter FFs.

## Preserved live baseline and next dependency

At actual 15:51:47 PT, ep8 original baseline PID 3135775 remained live after 7h11m, RSS 17,241,412 KiB, approximately 101% CPU. `baseline_live.log` preserves exact command, source working directory, log mtime, and current tail. It was neither restarted nor canceled. This old flattened baseline is distinct from the completed v2 regional diagnostic.

The next implementation dependency is a coherent final station/stream/head/VM/producer snapshot implementing the already directed eight regional station roots, landed crossings, and explicit OT_ASSERT separation while preserving all functional consumers. It then needs actual source-bound all-role <=32 proof without exclusions, reset two-stage/clock/phase/first-use, exact production and CFG mutant receipts, real native memory/PG/pin/reach/geometry, mapped area, and contextual timing. No parent regeneration or physical build is authorized by this receipt pickup.
