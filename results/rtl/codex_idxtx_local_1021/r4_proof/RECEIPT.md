# IDXTX R4 actual production and existing causal proof

Logic39bea79e1; L20S SHA7729217cb859a19013d0edf5c6ba56e6e96148f07d7b980e412163570300637f; TREE SHA4fdbaf13ac73d998ae3f5566ef3cb46628559a19b6a69f5c6dc6a3aecdd66032. Verified copied source before admission. Baseline ep9 unitoth-ubuntu-3419175-1792625089 exited0; build866.14s and19,575,084KiB peak RSS. Existing actual six-die SRAM DIEM1/TXS1/k3 production bench PASS0 mismatches/0faults, unchanged exact TX spans die1 edges17963..19406/1431 beats and die2 edges19564..20987/1424 beats.

Only after baseline PASS, existing MUT1/2/3 used byte-identical independent fixture files and independent build outputs. Actual units3615047-1792626700,3615256-1792626701,3615901-1792626703 all exited0 (expected-caught runner). Independent checker reports caught74/72/2 mismatches respectively, no faults. These are actual result JSONs, not an exit-code-only inference. MUT3 shifts first TX edges+1; MUT1/2 alter actual output data/sequence. MUT4 remains unexercised by the existing full-mask k3 fixture.

R4 changes combinational ownership only: private genuine accept&&onehot/open predicate modules feed downstream enable-only consumer modules; no added state, edges, arrival restrictions, SRAM, public ports or calendar. Actual mapped native MAIN/FB must test whether consumer factoring remains bounded32. Native/physical have not yet passed for R4. Earlier R1/R2/R3 refusals remain immutable.

Connected scope remains VMUX+baseline dsdv_bk_sel+changed TX, not the39-region cb73 PlanA parent. No complete PlanA+TX source/physical/calendar claim.
