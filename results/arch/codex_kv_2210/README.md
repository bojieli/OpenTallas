# KV takeover evidence, 2026-10-20

Candidate source is on `codex/kv-die-takeover-2210`. No release adoption or final die closure is claimed.

The independent GEN audit used an isolated copy of the final `ccc9418ac-gen9d22bu` case on ep6. Original inputs are recorded in `original_INPUT_SHA256`; the source case was never edited. The copy repairs one real physical/timing alias through the candidate binder: DCAL netlist port `ego` maps to the existing real kit pin `epoch_go`. The original binder left that connected pin under its RTL name because it was an `extra_conns` tap absent from the frame. The original audit refused the missing alias. The repair adds no pin, coordinate, logic, or timing waiver; `dcal_alias_bind.json` records 98 mapped bits and zero unmapped real pins.

`d22bu_gen_safety.json` is a genuine **FAIL**, not a die result. The final netlist scan covers 46,061 instances, 7,095,328 signal net bits and 7,419,343 driver/load bit pairs, using actual LEF rectangles and final orientations. It reads 57,924 actual TT Liberty pin-clock mappings. Each instance/port pair retains the worst bit-pair shortest Manhattan span and its exact witness net and bit indices. These are planning lower bounds, not measured routed lengths. Free channel rectangles are the exact complement of placed hard macro envelopes; macro areas are never declared relay sites.

ROOT14 reports 8,448 hops above 405 um, maximum 28,959.8 um, and 337 wires with an unsited stretch above 405 um. The 7,582 missing-root entries remain qualification failures: initial examples include dual-clock unbound PC/PHY interfaces without proven per-pin clock identity. They are not automatically 7,582 proven cross-region physical paths. No clock root or landing is inferred from the macro centre, and missing identity is not waived.

The actual largest wire is reset leaf `rrs_n_rst_die_t1__m_0__g1_s188/b` to `rly_pinfix_pll_lock_0__s0/en`, 28,959.8 um. The next reset leaf `rrs_n_rst_die_t0_0__g5_s4/b` drives distant PV forwarded-lane `en`/`rs` pins over 15 mm. Of all long port pairs, 789 are named reset nets. The reset distribution owner is tracing the final netlist and reset protocol before a structural fix. Original evidence remains unchanged.

Nine fleet unit tests passed (`unit_tests.log`), including mirrored actual-pin geometry, constants preserving bit indices, missing geometry/direction refusal, unknown multi-root refusal, real Liberty clock disambiguation, channel exclusion of a macro wall, and exact scalar binding admission/refusal.

AHUB evidence is separate: `ahub_candidate_identity.json` verifies all 21 consumed source files against the committed production behavioral receipt. Positive standard LEC jobs `a7_pos_go`/`a7_pos_sc` were still progressing at pickup. Behavioral exactness receipts alone do not establish the pending equivalence result.

HROOT LAND source and the standard leaf LEC are present as opt-in candidates. Default/release adoption remains held: strict binding and executable absolute four-path/compiler/quiet-observer timing must all qualify. A metadata `+1` note does not meet that obligation. Likewise, the corrected paired r17 D2D/DCAL law and CTL/EMB schedule changes require their own receipts before adoption.

Remote large artifacts remain under `ot-epyc6:/srv/opentallas-scratch/claude/codex-kv-2210/d22bu-aliasbound/`; `final_audit_SHA256` identifies the helpers and complete 109 MB facts artifact. No large raw facts are copied into the repository.
