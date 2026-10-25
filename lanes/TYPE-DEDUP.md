# TYPE-DEDUP lane (claude/type-dedup-1024, merged to main 4a5c3620d8 @ branch 3700d7ab83)
## Status: DONE (tool merged; proposals posted in S81.md, S81-CORES.md, KV-G3.md, QC-A0.md, HBM-ARCH.md)
## Tool
tools/die_plan/dedup.py (+ `gen.py dedup`), tests tools/die_plan/test_dedup.py 9/9 PASS. die_plan suite = main
(2 pre-existing failures on main too: test_check::test_gen_rtl_lint_and_bench (verilator SYNCASYNCNET),
test_g2::test_per_tap_reset_synchronisers); docker-backed bind tests need `sg docker`.
- analyze/apply: exact merges only (netlist key + per-instance orient keeping die pins and the canon type-frame pin
  table); --fix-order re-solves port bit orders die-wide (parity system); bound-RTL gate (PLANDIR/bind/bound_r8/rtl);
  STRAP / FT-POP families reported, never merged (R7: no tie-offs). verify(): ports/lanes/latency/census untouched,
  tracks per port unchanged, one pin table per type, validate. Writes a copy + dedup_provenance.json.
- variants: bound modules per plan type and what separates them (pads / narrowed ports / params / other).
## Results (copies of main @8a5d1f3 plans; results/type_dedup/summary.json)
| die | types before -> after | G0 before/after | G0C errors before/after |
| S81 | 174 -> 161 (13 merges, 83 ports bit-order repaired, 26 types' pin tables touched) | PASS/PASS | 91 -> 84 |
| QC compute | 56 -> 56 (near-dups are different slice RTL s6b vs s8) | PASS/PASS | 4 -> 4 |
| KV | 49 -> 49 (hg_v1_r1..r5 plan-identical but bound RTL differs; plan-only 49->45 FAILS G0 R8, 7 err) | PASS/PASS | 22 -> 22 |
| HBM | 60 -> 60 (7 netlist-identical _v1 pairs blocked by 2-18 mirrored window positions each) | PASS/PASS | 121 -> 121 |
Bound kit counts: QC 56 plan types -> 80 bound modules; KV 49 -> 76 (S81 bound tree lost, summary stale).
KV hg cN rotating-chain lockstep miter (results/type_dedup/kv_hg_cn_miter): PASS 200k cycles, mutant caught.
## Proposals (owners decide; nothing applied to live plans)
S81: adopt the 13 merges (or derive port order from type order XOR mirror in gen_plan_v4); leaf ft-population is the
real driver (74 types / 66 populations) -> hard-core leaf, standard slot grid, or station strips.
HBM: mirror-symmetric windows on the listed buses -> 60 -> 53. KV: rotating cN chain (+ R8 acal/o_kg decision) ->
hg kits 5 -> 3. QC: full-width rotating encodings for narrowed-port variants, chain-end ring lanes -> 80 -> ~56 kits.
## OWNER?
- KV: R8 acal/o_kg per-row added delay (1/-1/-3/-5/-7) blocks any hg_v1 merge: make uniform, or exempt as boot-static?
- S81: superset ft slots are tie-offs (forbidden) -> leaf type count needs a lane re-pack decision.
## Scratch
localhost:~/scratch/type-dedup/dd_s81/{die_plan.json,dedup_provenance.json} (the 161-type S81 copy); rest removed.

## CODEX notes 2026-10-25 02:43 PDT
Tool DONE on main; current plans use lane-owned type policies. Old strap/FT population proposals cannot bypass R7 or bound-netlist equivalence; no new dedup stream opened.

## CODEX PARKED 2026-10-25 03:35 PDT
Claude reset order: safe park, no new jobs. Sources/jobs/results/failures/OWNER? recorded under Handoff to Claude 2026-10-25 03:35 PDT — GEOM/PROTO/toolchain in CODEX-LOG.md. Prototype strict SU channel job live; point SU done/uncollected. No main merges by this agent.
