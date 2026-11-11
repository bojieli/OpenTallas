# OpenTallas physical-design process (COORD, owner request 2026-11-11 ~02:4x)

This is the binding order for every die. No stage starts for a block until the previous stage's gate passes for that block. Evidence for each gate is a committed file plus an explorer render (tools/fleet_viz, headless CLI from EXPLORER-SCRIPT-1).

| Stage | What | Gate (evidence) | Owner |
|---|---|---|---|
| S0 Architecture feasibility | Wide-bus census from the explorer link model; cut demand vs track supply per die and per type | No bus >=512 b driving any cut >0.8 without a recorded arch decision (serialise with pin cycles / registered tree / local replication / narrower beats / pass-through routed around). FEAS-AUDIT.tsv | FEAS-AUDIT-1 -> die owners |
| S1 Die floorplan | Type blocks, pins/face windows, ft slots, stations, clock spine, PG, M8/M9 use | Explorer die view reviewed; route_supply die cuts <=0.8; die GRT on abstract views = 0 overflow (halving-off image); die STA on abstracts meets the inter-type budgets (TT setup >= 0, FF hold >= 0). DIE-PROTO.md | die owner + DIE-PROTO-1 |
| S2 Type floorplan (macro placement) | INTENT SHEET: dataflow chain + link roles, critical pairs; hand-drawn layout following the chain; search only to legalise/fine-tune | Explorer type view (before/after) reviewed; route_supply type score <=0.8 (0.8-1.0 needs a written reason); EQ + G0 clean; rationale in the CLEANSLATE row | CPL/VIS lanes -> die owner adopts |
| S3 Plan event + bind | Changes batched into one plan event per die per cut; one canonical bind | One event and one bind sha per die per cut; no plan events between cuts except blocker fixes | die owner, KW-FIX-43 |
| S4 Kit build | Batch launch for every block that passed S2 | Blocks that failed S2 are never launched | KIT-WAVE / KW-FIX-43 |
| S5 Per-run review | Auto-geom + explorer type view at place; GRT congestion map at route | A failure is classified (ARCH / PLACEMENT / TOOL / FLOW / TIMING) before any rerun. No blind retries: two strikes -> structural re-form | class lanes |
| S6 Sign-off + die close | Type sign-off; die GRT/STA on real views | Owner sign-off rules (AGENTS.md) | die owners |
| S7 Feedback | Every failure class fixes the stage that let it through (plan rule, generator, gate), not just the instance | A class fix names the stage and gate it changes | COORD |

## What we skipped (why the count stalled)
S0 and S2 were never done: kits were built from shelf-packed types with unbudgeted wide buses, and we iterated on S4/S5 failures. The die-level S1 gate (GRT/STA on abstracts) was never run.

## COORD enforcement (every LOOP-GAP and HOURLY)
1. Reject any READY/ADOPT that lacks its stage's gate evidence (file + explorer render). No exceptions for "small" changes.
2. HOURLY reports a STAGE FUNNEL per die: blocks at S0 / S1 / S2 passed / launched / signed. The sign-off count alone is not progress.
3. No kit launch for a block whose S2 gate is missing (KW-FIX-43 checks this before each batch).
4. Each new failure class gets one class lane, and its fix must name the upstream stage it corrects.
5. COORD itself views at least 2 explorer renders per hour (GEOM-REVIEW.md) from the blocks that changed.
