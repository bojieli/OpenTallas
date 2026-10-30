# QC A0 final-net structural closure, 2026-10-29 18:48 PDT

Current sign-off remains NOT SIGNED. No physical build in this experiment is qualified or submitted.

The DIE-QC-39 NL estimate gap has a concrete source: the final clock net at `mp_a0_ldtx5_7` drives registers in separate spatial clusters. Its worst FF wire delay is 143.00 ps over 174.04 um; the previous linear Manhattan model assigns 47.85 ps. The missing 95.15 ps explains most of the reported ~112 ps pair-model gap. The corresponding NK worst wire-model residual is 62.20 ps. The issue is the last loaded clock net, rather than macro early-tap k alone. Source: unchanged DIE-QC-38 `nl_tree_ff.tsv` / `nk_tree_ff.tsv`, at intel2 `/srv/opentallas-scratch2/claude/dqc38-a0`; reproducible with `leaf_wire_diagnose.py`.

Structural candidate: smaller equal-count leaves, spending clock buffers, without changing RTL, latency, early-tap rules or count-balance rules. Existing `gen_a0_tree39.py` generated T30 leaf sizes 1/2/4 on actual NL and NK census. Leaf1 removes the multi-cluster final net: maximum register leaf leg drops to 74.8 um on both tiles. It costs 21,765 planned clock cells on NL / 24,379 NK. Leaf2/4 retain long final legs (NL 186.7/221.0 um; NK 175.3/235.3 um).

Leaf1 alone is insufficient: NL T30 has 245.9-um upstream node legs. The existing plan-faithful estimate gives FF overall p50 -201.3 ps / p05 -225.1 ps; reg-reg p50 -158.6 / p05 -199.7 ps. It does not robustly beat TritonCTS -172.53 ps and is not built.

`gen_a0_corridor.py` adds an opt-in `--corridor-feed` successor: spread nodes walk actual macro-free corridors, rather than snapping a straight centroid point onto a halo edge. Register-domain stage budgets use corridor reach, too. Default off remains identical to the original real NL T30 leaf4 slice (cmp exit 0, before the corridor-budget addition; that addition is guarded by the same opt-in). Membership construction avoids an O(nodes²) identity scan while retaining original list order. No shared tool changes.

Initial corridor T30 failed geometry: 405.2-um final domain-node leg because the register-domain depth budget still used Manhattan reach. This failed candidate is retained as `nl_corr_l1_t30_rep.json`; it must never route. The successor changes that domain budget to actual macro-free corridor length and is estimated at T34. No CTS until its reach and timing feasibility plus rendered-image review pass.

Run root: intel2 `/srv/opentallas-scratch2/claude/codex-qc-a0-1848`. Initial estimate admission unit 2756580; leaf1 timing estimate unit2810081; corridor1 unit2860946; default-identity unit2873760. All exited 0 as analytical jobs, with failed candidate verdicts above retained. The local `ot-run` wrapper forwards to intel2; `--hosts localhost` selects intel2's local host, while `--hosts intel2` is not a valid fleet name there. Two attempted admissions before this correction were NOT RUN, with no physical job started.

A second analytical variant, `gen_a0_corridor_fast.py`, computes the per-domain reach budget with one grid BFS per domain, adding two grid pitches for endpoint stubs, instead of repeating A* for every register. This reduces the predictor's cost; the first A* variant remains running without restart. `nl_corr3_l1_t34{,_rep}.json` is its separate candidate (unit3460329), not a replacement verdict for corridor1/2. It remains unqualified until actual geometry and timing estimates are collected.

## Explicit reset park, 2026-10-29 19:03 PDT

Stopped engineering immediately on parent reset. Corridor3 analytical generation completed: T34, 22,263 planned clock cells, maximum node leg404.2um, macro/register final leg74.8um, equal total stage34, max fanout4. There remain2,020 node legs over the intended60um standard-stage window (696 over90um). This is planning output only; no timing estimate, image review or CTS run on corridor3. Do not adopt or claim a physical gate. Corridor2 original A* budget job2904596 remains live and untouched. Next: collect it, then estimate corridor2/3 timing; only on a robust estimate pass render/review before actual CTS. No new jobs after reset.
