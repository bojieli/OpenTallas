# Bounded candidate packaging model for ROOT review

MODEL ONLY. No source is implemented here and no source equivalence or source-safe qualification is claimed.

Choose a distinct top `dsdv_gunit_l5_fs_guarded_1019`. Keep all current main production RTL, including public dsdv_gunit_l5/tail, SK parameter, L2/L3 reset relays and vstop JREG/taps, byte-identical. There is no new default production flag and no production compiler selection. Candidate-only source list must refuse ordinary dsdv_gunit_l5 aliases.

The minimal logical candidate graph specializes L5 from843 to PIN_COPY=CONTROL_SAFE=Q4=FANOUT_SAFE=TABLE_LIFETIME_SAFE=1, MUT0. Eliminate the dead legacy branches by a reviewed source transform; do not import the changed generic tail at all. Its only needed helper definitions are operand_pin32, control_first, control_bit and capture_bank24; extract those exact module bodies to a private candidate helper file and namespace them plus index5. The candidate L5 references candidate tail_fs, candidate reset-region16 and exact native32x64 behavioral/blackbox view according to simulation/synthesis mode. Tail_fs requires Sinkhorn_fs, skf predecode and common sk_arith plus the existing F12 mul/add source cone. The p/skp units are not in the chosen functional cone and need not be imported just because the old broad bench/spec listed them. Their receipt remains provenance for historical equivalence proofs. If a frontend still resolves dead branches, specialize first rather than importing an alternate generic module.

Candidate source files:

1. Newly named L5 specialized from843 (rename top, remove inactive branches, private helper refs).
2. Private helper module bodies from candidate tail.sv, plus L5 index5; no generic candidate tail module.
3. Newly named tail_fs from d9 (843 has identical bytes).
4. New Sinkhorn_fs source from d9 (843 identical), with its ot_skf_* and ot_hdc_skf_* modules.
5. New skf predecode from d9 (843 identical).
6. Region16 reset source from ed66 (d9/843 identical).
7. The exact existing native dualclock32x64 views, named in SHA-bound artifact source list. Generate no new view in this packaging task.
8. Existing main pass, reset relay, F12 mul/add arithmetic and their exact dependencies: verify against the73-file manifest, retain main rather than ancestor versions.

Namespace every newly defined module in items1–6 consistently if main or another selected source already defines it. Prefix substitution changes hierarchy/module names and can change keep rules/paramod names, so emitted-module registration and exact synth-keep rules need their own narrowly reviewed candidate kit. It is not valid to reuse old native/fanout evidence across those names automatically. No copied common_flow, closure_loop, ref_tile or compiler tree belongs in this source extraction.

Selection guards: separate explicit top, ordered source list SHA256 and per-module definition ownership; refuse duplicate public/private definitions, wrong top alias, omitted native view, mixed macro behavior/blackbox selection, missing mandatory specialized configuration, unknown arithmetic source hash or generic helper fallback. Compiler candidate binding remains absent until source graph plus actual age proof passes. A later source-only binding must accept an exact named candidate graph and reject the current public main top, ed66/f03 aliases and partial source mixtures. These are fail-closed artifact selection checks, never an exception for main release checks.

Price against actual main, not safe2: tail637→893 is +256 core edges = +216 pipeline replacement +40 Q4; no new edge is assigned to same-edge copy or +9FF lifetime guard. Main historical HC port759N/757S and safe2 975N/973S differ216, then historical whole candidate f03 is1015N/1013S. Those are source-bound prior receipts and model expectations, not measurements for the proposed renamed/current-main-composed graph. Re-prove the L5/internal-to-current-L2 boundary and HOP using the minimum actual source component after extraction; do not rerun all arithmetic when exact cone identities establish reuse.

ed66 defines the first whole candidate. 4ae holds its eight-case numerical/causal witnesses. d9 changes L5/tail_fs/Sinkhorn_fs/predecode/generator after those witnesses. 843 changes only L5 lifetime guard relative d9. f03 has separate HOP receipt with ten differences from843 across candidate/host sources. Preserve each receipt's exact graph and never relabel one as another.

Next authorized review is this packaging model and dependency manifest. Implementation, default equivalence, source-safe native audit, cold config-valid/fence, macro escape/reset/PG/clock, physical gate, parent regrant and compiler/token adoption remain separate prerequisites.
