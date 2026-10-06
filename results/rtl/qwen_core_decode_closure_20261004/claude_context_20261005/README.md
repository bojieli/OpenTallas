# Qwen ROM decode core: in-context route at 1.2 GHz (Claude, 2026-10-05)

Item 2 of the Qwen3-8B ROM physical closure: route `ot_qwen_rom_core` (the final DEC_LA "h" core, main bc6f91862)
**in context** — the units present, since the core alone exposes 1.87 M black-box ports (CODEX_HANDOFF.md).

## What was built

- `tools/qwen_rom_core_ctx_claude.py` — preparation: the DEC_LA core over the retained screen's parameter set
  (VPOS 0, DEC_LA 1, P8191 plain-AR parameters), optional zero-latency patches, the units black-boxed and exposed,
  synthesised `-noabc`, then the **controller cut** (`tools/qwen_rom_core_controller_cut.py`): every port that
  touches no cell (the pass-through ROM/data buses) is removed, so the route carries the core's real logic — 1,237
  input / 1,438 output bits instead of 1.87 M ports.
- `tools/qwen_rom_core_issue_fallback_w12.py` — `DEC_LA_ISSUE_FB` (default 0): the handoff's zero-latency issue-loop
  fallbacks as ordered code targets.
  - **FB 1**: `issue` duplicated per consumer group (ME go, SU go, NEXT/FIFO advance, argmax update), each
    specialised to its unit so the copies are distinct functions; the `d_unit` mux leaves the issue path.
  - **FB 2**: + the unit / barrier / chase-source selection registered one-hot with the NEXT control fields at LOAD,
    so each comparator feeds an AND-OR instead of a `d_unit` / `d_chase_rows` mux.
  - **FB 3**: + the `start` input leaves the data-register enables (token/position captured on every idle edge, the
    running max and `next_val` get their own enables), removing the `start` fan-out from those cones.
  - `DEC_LA_AMQ` (default 0): the engine's argmax result registered at the core boundary, the chunk fold reading the
    registered copy; **+1 cycle per core program END** (not in the issue loop).
  - `DEC_LA_BOUND` (Codex, tools/qwen_rom_core_dec_bound_emit_w12.py): the E2 remainder table narrowed to
    `ODD*2**H-1` — exact, 0 cycles. Applied in all variants.
- `physical/qwen_core_ctx/` — the die-context boundary. Every core port's other side is a unit-boundary register in
  the same core clock region, balanced to the same insertion, so each boundary delay is referenced to this block's
  OWN propagated clock: setup keeps the 0.2 T outside budget, hold credits nothing outside (min 0), and the ICG's
  gated engine clock (`u_me.clk`) is excluded (it is a clock, not a data port). OpenROAD 26Q3 crashes on
  `-reference_pin` inside `load_design` and inside GRT's layer assignment, so the same reference is applied
  numerically from the measured clock arrival at a register of this tree (`io_ref.sdc`, read post-CTS and again at
  GRT/DRT/FILL after `estimate_parasitics`).
- `tools/w18/corner_sta_ref.py` — `tools/w18/corner_sta.py` with the boundary SDC read after the propagated clock is
  set, plus every violating path listed (startpoint / endpoint / slack) for class grouping.

## Routed results (final 6_final SS at 0.833 ns, 60 ps uncertainty; FF hold at 25 ps)

| variant | RTL | post-CTS WNS | **SS60 (die context)** | viol | **FF25 hold** | DRC | cells µm² |
|---|---|---|---|---|---|---|---|
| `c1_plain` | DEC_LA h | -494 | -425.8 (ideal-port boundary) | 940 | +7.18 | 0 | 7,229 |
| `r3_f2ba` | +FB2+BOUND+AMQ | -106.7 | -71.8 | 196 | +7.55 | 0 | 7,160 |
| `r4_f2ba` | +FB2+BOUND+AMQ, keep attrs | -268.2 | -19.0 | 19 | +6.82 | 0 | 6,885 |
| **`r5_f2ba`** | **+FB2+BOUND (adopted)** | **-26.96** | **+6.27** | **0** | **+6.92** | **0** | **6,945** |
| `r5b_f3ba` | +FB3+BOUND+AMQ | -13.26 | +0.87 | 0 | +7.12 | 0 | 6,922 |
| `r5b_f3ba_m25` | FB3+BOUND+AMQ, `SETUP_SLACK_MARGIN=25` | -26.27 | -7.43 | 0 | +8.00 | 0 | 6,926 |
| `r5b_f3ba_td` | FB3+BOUND+AMQ, no GPL routability | -55.25 | -37.45 | 8 | +8.95 | 0 | 6,917 |
| `r5_f3ba_u25` | FB3+BOUND+AMQ, util 25 / density 0.45 | -14.52 | -3.68 | 0 | +6.96 | 0 | 6,982 |

Every variant is the same-or-better at the die context than at the ideal-port boundary in the loop path
(`worst_reg_to_reg_slack_ps` +41.8 ps at `r5b_f3ba`); only the input/output ports move, by the ~280 ps of clock
insertion the ideal reference was charging them for.

## Fixes, round by round (procedure §3, one class per round)

1. **`c1_plain`** (−425.8): the plain-path boundary charges the ideal port edge, so every boundary register sees the
   block's ~300 ps insertion as budget. The die-context boundary removed 3,720 endpoints in one step.
2. **Boundary hook** (r2, ×4 runs aborted): `-reference_pin` SDC → GRT `Signal 11` in
   `grt::FastRouteCore::updateSlacks`; replaced by the numerically referenced delay. Output max/min used the wrong
   corner's arrival → CTS hold blow-up (9,586 hold buffers, abort); corrected to the analysis corner (max: `L_max`,
   min: `-L_min`).
3. **Issue loop** (r3: −71.8): the handoff's path. FB1 made it worse (a second `issue` cone), FB2 removed the
   `d_unit` mux and the chase-source mux → the loop class disappeared from the report.
4. **`start` / argmax fold** (r4: −19.0, then `keep` attributes): `start` drove `tok_r`/`pos_r`/`run_*`/`next_val`
   enables through 6 buffers and an 8-gate `AND` before the fold logic; AMQ + FB3 decoupled it.
5. **Predecode adder re-ripple** (r3→r4→r5): with the issue loop fixed the worst reg-to-reg path was
   `u_pa_a_base.b → fqd_a_base` (−21.9 ps), i.e. the kept prefix adder; **`write_verilog -noattr` in the cut flow
   (the same line is in Codex's `controller_cut/prepare.sh`) drops `(* keep *)`, so ABC re-ripples every adder and
   comparator.** Keeping attributes moved post-CTS WNS from −106.7 to −26.96 ps and made them close in every
   variant. This is a reusable finding.

## Exactness (lockstep, nonzero exit on any mismatch)

Same five adopted 8K benches and golden plans as `results/rtl/qwen_core_decode_closure_20261004/proof/h`
(`k_L0` 49,582 · `k_AR0` 14,581 · `c_H1`/`c_H2` 12,000 · `k_D0r` 30,618, all 0 mismatches).

| config | benches | cycles |
|---|---|---|
| FB2+BOUND+AMQ (`r3..r4`) | 5/5 pass, 0 mismatches | 49,585 · 14,584 · 12,004 · 12,004 · 30,621 (+3 per layer bench, +4 per head bench) |
| FB3+BOUND+AMQ (`r5b`) | 5/5 pass, 0 mismatches | same |
| FB2+BOUND (`r5_f2ba`, adopted) | running on ot-epyc1tb | — |

The +3/+4 cycle deltas are `DEC_LA_AMQ`'s one cycle per core program END, which the adopted variant does not carry.

## Added cycles and rate

`r5_f2ba` (adopted) adds **0 cycles**: FB2 is a fan-out/copy change, `DEC_LA_BOUND` narrows a table exactly. So the
P8191 plain-AR token stays at the measured 193,955 cycles (main 756e8c54f) and the 8K rate above it is unchanged.
`DEC_LA_AMQ`/FB3 would add 1 cycle per core program END (1 per layer program + 4 for the chunked head), i.e. ~0.02 %
of the token; it is kept as a default-off margin lever only.

## Reproduce

`jobs/run_variant.sh NAME FALLBACK BOUNDARY UTIL DENSITY [extra]` — FALLBACK `N` = `DEC_LA_ISSUE_FB`, suffix `b` =
`DEC_LA_BOUND`, suffix `a` = `DEC_LA_AMQ` (adopted: `r5_f2ba 2b ref 30 0.5`).
