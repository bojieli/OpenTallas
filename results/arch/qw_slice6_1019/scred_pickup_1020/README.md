SCRED pickup 2026-10-20 00:38 PT, source claude/qw-slice6-scred-1019 94483a34c

All four current masters FAIL the binding pre-gate native checklist. Their mapped
textbook JSONs are preserved unchanged. The original census reports nets >256,
so initial reports prove failure without enumerating33..256. Follow-up fleet
*_native32.json reruns the native mapped census at hf_report/max/refuse=32
without changing source or any gate-rule helper. Diagnostics are capped by the
existing tool; a short findings list is not the count of all violating nets.

master  reset/data max reported loads  depth ps  levels
sc      3060/742                       1030.2    28
scb     3064/644                        876.8    24
red      740/504                        813.5    22
redb     763/504                        775.2    21

redb terminal gate WARN is NOT admission: GRT overflow0, util51%, 12077 flops,
TT/FF boundary spread11.8/10.8ps and positive setup21.1ps cannot waive fanout32.
Other gates were progressing and preserved. Terminal status is in pending_results.
Pin wrappers register all data pins, input/output comb boundary counts0. Raw reset
lands in2 stages. Geometry reach0 in textbook is unavailable placement evidence,
not proof of physical zero length. No further gates or submissions were launched.

mut2 terminal all8 benches: fallback eqss0 and eqrb0 PASS all4 stimulus modes;
b2ss/b2rb f,j,k,q,m,n,o PASS. sc/scb mutants FAIL random29/legal145 compares;
quiet/hronly pass. red/redb mutants SURVIVE all4 modes: these logs are diagnostic
failure evidence, never acceptable mutant witnesses. Minimal component bench
source rtl/test/qwen_dv/s5_redsc exercises 16-vector SUM, SQ and MAX segments to
address that stimulus gap, including the actual OT_S5_RED_MUT macro, with both
ring implementations. Its source is pinned5cf0c9133; fleet output separate.

Structural successor requirements (not an approved kit)
1. Preserve original pairwise/scalar and csum8 reducer rounding/order, but use
   pipeline add/mul cores whose measured mapped stage depth meets600ps. Original
   3-cycle FP add/mul are the measured red critical cones; a floorplan tweak is
   insufficient. Parameterize all aligned data/control/valid paths together.
2. Partition reset at the consuming register groups: every relay output<=32,
   including async reset pins and control logic; keep hierarchy/unique identity
   and prove mapping did not coalesce copies. Budget each added reset stage.
3. Replicate sq/max/select controls in <=32-load kept groups at the same logical
   edge. redb's sq bit is504 loads despite ring conversion. sc needs staged
   independent candidate comparison and selection, not only one additional
   candidate register (scb still877ps).
4. Use per-slice independently kept ring pointers and write selectors. A single
   pointer or decoded write enable must not fan out across wide storage.
   Validate each logical store<=2048b; splitting one oversized store merely to
   evade SRAM admission is not accepted as architectural SRAM replacement.
5. Before ANY new gate, run fleet synthesis with complete driver census threshold32
   (clock classification separate), runtime-indexed storage inventory, pin launch/
   landing audit, no tied functional ports, and405um planned reach. Report all
   violations, not only top drivers. Price added edge counts to the slice compiler.

No safe successor or closed view is claimed. No main merge, no REVIEW, no submit.

Minimal out2 positive original and ring both PASS800 stimulus cycles, >=30
valid segments checked. Original actual SUM-as-MAX mutant fails valid red_data
cycle59; ring actual mutant also fails valid red_data cycle59. All4 minimal runs
terminal; ot-run exit0. Source manifest and generated bench/reference/dut are
preserved alongside committed build/run logs.
