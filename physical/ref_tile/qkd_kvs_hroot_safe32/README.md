# Default-off SAFE32 hroot V3

Model and validation: results/rtl/kv_hroot_safe32_1020/model.json and README.md. Source is standalone, canonical sources unchanged. HROOT_LAND_EDGES must become2 at adoption (+1 vs old landed) for each of four word chains per root. Four roots per die.

Pre-gate checklist:
1. PASS: input captures and output launches exist for every data/strap pin; flow adds two reset landing stages. V3 adds one matched reset-distribution/data edge; initial and mid-run reset bench exact.
2. PLAN:300.24um square; newly added intermediate capture stage provides a central landing between opposite pin faces. Input capture -> intermediate -> output launch makes each half-width/height hop <=300.24um when intermediate flops stay in central register band. Actual placement reach must be checked after gate; no unregistered600um opposite-corner hop is intended.
3. PASS mapped direct: actual ASAP7 synth POST_SYNTH asserts all nonclock nets<=32 after explicit constant-tie replication. Two root copies each feed30 leaf copies;13 output bits per leaf gives at most26 local enable endpoints. Independent BUF/INV terminal census PASS maxdynamic30, roleerrors0 on exact native mapped netlist + five Liberty hashes; no exception for dynamic/reset loads.
4. PASS structural: original two-level stack decode, no wide arbitration, no combinational pin->pin paths; V5.050 bit-exact at matched+1age.
5. PASS: static pipeline/held control words, no runtime-indexed flop memory or variable-depth rings; each stored word<=1118bits. No arithmetic changes.
6. PLAN: no macros, full-width standard-cell region, unchanged300.24square slot. Outline is pin-limited (N1561pins/295.24=5.29 perum, S1494/295.24=5.06), not area-driven; record the low utilisation explicitly.
7. PLAN: single W-face clock as previous landed root, same833.333ps domain/60setup25hold uncertainty; hold margins>=0.03. TT/FF spread must be measured<=80 before submit; no insertion-only waiver.
8. PASS model: static, throughput1word/cycle; +1edge perword relative oldlanded (HROOT_LAND_EDGES2). Compiler/calendar/age/bind integration remains mandatory before adoption.

Physical constant tie hook is source-pinned in orfs_vars POST_SYNTH_TCL and executes before synthesisODB export; it refuses unexpected tied functional ports and refuses any nonclock mapped driver above32. A timing/layout gate or CLOSED route is not yet claimed.
