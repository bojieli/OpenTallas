# G4/G8 retained inventory: dense one-phase capacity refusal

**FAIL, geometry candidate only.** Both service alternatives retain the same 96
frame inventory (SHA256 `3ec8547d14da46bacc2534bcf572c8bf0691d118a46b23ef8369fae167297375`).
The actual allocator rejects this inventory before an expert stage map or
multi-user calendar can be admitted. Increasing the expert stage count cannot
repair the dense layer under the current one-phase ownership contract.

The released L0 fixture has 320 `wq_a` rows and 128 `wkv` rows per TP4 rank.
`lower_xs.placement` assigns one real a_proj phase per frame, separates the two
tensors, and enforces the measured four rows per phase. Thus it needs at least
80 + 32 = **112 frames**. The 96-frame proportional allocation gives 69 + 27;
`320 > 69 * 4` triggers `('a_proj one-phase capacity', 'wq_a', 320, 69)`.
112 is a necessary dense capacity condition, not a proof that a complete
112-frame inventory, expert programme, or physical die fits.

`capacity96.py` installs precisely the retained frame names in an isolated
in-memory compiler die. It verifies every retained source master, including MX,
against the candidate inventory (source suffix `_l4` removed). It does not edit
the source die, its RTL, or either live candidate. The allocator snapshot was
copied from the previous pinned capacity campaign to a new run directory.

The unpinned fleet job ran on ot-epyc9, unit
`oth-ubuntu-2530564-1792559799`, terminal exit 1. `fleet_failure.log` preserves the
original failure. N1/N2/N3 expert probes each report 96/96 placement failures
(the current compile_frame also constructs the a_proj placement for expert-only
specs). The first dense N0 signature then raises the same assertion. There is
no summary.json because signature generation correctly stopped on that error.
The three frame JSONL files retain every failure. No ROM fill or rate has been
inferred from those failed allocations.

Release choices: preserve at least 112 frames and qualify the resulting actual
inventory, or implement and measure a multi-phase a_proj programme with matching
CAP/gather ownership, producer timing, and calendar prices. The current 140-stage
calendar and 46/10 or 36/8 user counts do not qualify this 96-frame candidate.

Source snapshot `source/lower_xs.py` SHA256:
`2ebcaa925dd09bd126d51215c4c56d36890c746e319714fce142d82dfff07863`.
The failure is a compile-time functional capacity result, not a routed die
result. No synthesis, route, whole-die simulation, or new physical claim was made.
