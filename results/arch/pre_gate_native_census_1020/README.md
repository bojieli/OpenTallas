# Mandatory mapped fanout admission

Candidate source `2b04da85f`, baseline `f94733d2b`. The source manifest pins the actual tested files and archive bytes. This packet qualifies the helper change; it does not qualify a tile or waive any physical/source contract.

The new gate runs after mapped synthesis and before any floorplan/placement. It derives input/output, clock, unary BUF/INV and literal constant roles from the actual loaded Liberty files, records each library and netlist SHA256, follows transparent branches, deduplicates actual terminal endpoint pins, and refuses every dynamic/reset driver above 32. Mixed clock/data roots retain their data loads, and macro data contacts count. Missing/unsupported connected cells or pin roles fail closed. No user fanout report or threshold override is consumed. The CLI admission argument is captured readonly before kit shell evaluation.

Constant top output bits are report-only and include literal/Liberty and transparent-path provenance. Functional pin semantics, pin registration and storage remain NOT_EVALUATED, with independent source-contract audit required. Legitimate reserved protocol bits/instance IDs are not automatically rejected; functional stubs remain forbidden by the independent contract.

The capture regression checks that new gate-only helpers use the frozen route overlay's exact main head without changing historical route helper inventories. The gate argument regression checks that kit environment cannot disable admission. Native fixtures cover 32 accepted/33 refused, reset, macro contacts, real clock exclusion with mixed clock/data roots, exact 30 direct plus 30 complementary INV consumers, endpoint deduplication, constants, missing Liberty/roles, nested timing attributes, indexed pin roles and nonzero ascending bus indices.

Targeted regression: 39 tests and 9 subtests PASS. Current-source real HROOT V3 mapped coupon: PASS, maximum 30 dynamic endpoints, 9,010 roots examined, five actual loaded FF Liberty files, zero role errors; report retains all 8,487 nonzero dynamic root counts. This establishes only mapped fanout/role behavior. It does not establish the candidate's functional/behavioral proof, physical closure or source-contract acceptance.

The complete HOST source/helper packet e7983edb3 is included in candidate bytes. Both p192 macro directories, opt-in RTL/PC wrapper, spec, kit and test fixtures are committed. The earlier helper-only diagnostic run was incomplete and is preserved as a failed diagnostic, not counted as a production pass.

The final paired full cohort completed on EPYC9 under admitted unit `oth-ubuntu-346716-1792485030`, using pinned Yosys 0.68 (`38e001a6f`) and Verilator 5.050. There are **zero new failure IDs** in all four cohorts:

| Cohort | Baseline | Candidate |
|---|---|---|
| closure_loop | 1,151 pass / 19 fail / 17 skip / 195 subtests | identical |
| ref_tile | 622 pass / 73 fail / 24 skip / 309 subtests | 643 pass / 73 fail / 24 skip / 309 subtests |
| fleet | 52 pass / 7 fail / 1 deselected | identical |
| landed_parent | 12 pass | 12 pass |

These are paired regression results, not an assertion that all repository tests pass. Exact pre-existing failure IDs and full raw logs are retained for both sides. The baseline archive includes tools, RTL, tests, all memory macro fixtures, common_flow and Makefile; unrelated historical result/kit artifacts outside that archive remain absent symmetrically. The intentionally deselected fleet load-hold test waits without a bound and is unchanged.

Current-source actual OpenROAD hook qualification also completed: 32 endpoints PASS followed by `PLACEMENT_STARTED`; 33 endpoints REFUSED inside PRE_FLOORPLAN with no placement marker. Full hook logs, report hashes, exact commands and admitted client receipts are retained. No census helper was deployed during qualification. Root owns main merge and runtime adoption.

Gate-Rule guard: PASS, eight helper-touching commits classified before this evidence-only commit.


Report-only followup: indexed constant Liberty output bus pins now retain the actual indexed child pin and its function in the constant-output provenance (rather than the parent bus default). Nonzero ascending bus17:18 regression checks distinct0/1 sources; all existing native admission fixtures still pass. This changes diagnostic provenance only, not fanout counts/admission. Separate targeted native suite:14 tests PASS on fleet unitoth-ubuntu-514109-1792485605. Runtime sync receipt for042aa171b is included; this report-only followup was not part of that deployed snapshot.
