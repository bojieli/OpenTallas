# INT8 exact granted CTS diagnostic: FAILED, stop

One authorized run executed 2026-10-19 13:49 PDT via unpinned ot-run, 24 GB/8 threads. Placement had already been accepted by ROOT; this packet grants no adoption. Eligible ep6/ep7/ep8 snapshots all passed exact 50-file hashes and pinned image identity. Admission chose ot-epyc8, unit `oth-ubuntu-1813104-1792442962`; detached controller2439725 completed with actual ot-run RAN exit1. Directory `/srv/opentallas-scratch/claude/hbm-int8-cts-granted-run-1019` is immutable failure evidence. Original placement and source are unchanged. No retries, source/helper amendments, GRT, route, gate, submission or shared activation occurred.

## Actual failure and proposed source correction (NOT APPLIED)

`cts_only.tcl:54` sources `report_timing.tcl`; the latter sources clock_family.tcl then calls `ot_cf_wire` without its required initializer. `ot_cf_active` reads `::ot_cf_active_cache` (line90), which is initialized only by `ot_cf_refresh` (line23). Exact failure: `can't read "::ot_cf_active_cache": no such variable`. The independent prior working caller `39021a45e:tools/closure_loop/ck_insertion.py` explicitly calls `ot_cf_refresh` immediately after loading CLOCK_FAMILY_TCL (line182), before family-pin/arrival calls. Full caller and exact kit source are included.

A source-only successor proposal is to call `ot_cf_refresh` after source and before any ot_cf_root/ot_cf_wire queries, retaining the real owner/edge checks. Separately write and hash an immutable postCTS ODB immediately after successful placement/master identity and all-native PG checks, BEFORE report-only calls. Reports and native exports should replay that checkpoint read-only so a reporting-interface failure cannot discard the graph. These are proposals only; they require a newly reviewed/pinned kit and explicit ROOT grant. No successor run is authorized here.

## Native observations before the reporting failure

- Actual 2782 register sinks, 143 CTS buffers plus110 dummy clock loads; clock path min/max4 buffers. CTS log reports 253 inserted instances in aggregate by area/PG difference, not a saved independent raw census.
- Added movable native area75.86um²; fixed ordinary/tie area1322.54um²; utilization4.8%. Final legalizer reached zero violations after recovering3 remaining cells. Exact source code original-cell location/orientation/master identity loop completed without error.
- All-native logical PG coverage:20740 input terminals,21246 after insertion and again after legal placement. This is logical binding evidence only: conductor/physical-contact proof was never reached.
- Preliminary TT root-referenced output diagnostic reports slack−226.59ps for o_data[45], with full expanded path in cts.log. Root boundary remains unqualified. This is no TT closure claim or structural data-path verdict; actual output loading/parent compensation requires review.
- Error occurred before `write_db`; no cts_only.odb/v exists. FF replay, complete TT/FF clock-pin arrivals/spreads, native strict fanout, clock area/cap breakdown, full electrical/depth/reset reports, reach recheck, signal identity, conductor proof and PNGs are UNAVAILABLE. clock_pins_TT.tsv contains only the header. No timing/adoption conclusion is supported.

## Eight-item checklist disposition

1. Source input/output registration/reset ages inherited unchanged; final native identity UNAVAILABLE.
2. Original whole-outline reach367.2um bound inherited; final raw recheck UNAVAILABLE.
3. Source/preCTS transparent nonclock max24 inherited; postCTS strict recheck UNAVAILABLE.
4. Full timing/depth/electrical qualification INCOMPLETE due reporting failure.
5. No added functional storage or edges; actual added cells clock-only per CTS log, independent inventory UNAVAILABLE.
6. Original accepted outline/no macros unchanged; legalizer zero violations; no saved checkpoint/new PNG for ROOT review.
7. Logical all-native PG inventory PASS at21246; physical contacts, FF hold, TT/FF spread and neighbor boundary UNQUALIFIED.
8. Source reset2/low2/high3 ages and +0 functional-edge contract inherited; no token-rate claim.

`failed_output.tar.gz` contains all resulting output files including full pre-native graph, platform checks and truncated clock-pin table. `preflight_50.txt` pins every input/script/receipt byte; ROOT_APPROVAL and manifest are included. Heavy processes completed; no pending job remains for this attempt. Parent must review the concrete protocol correction before any new work.
