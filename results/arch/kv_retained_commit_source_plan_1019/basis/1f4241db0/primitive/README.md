Source-pinned primitive expansion for the health-plane model; read-only, no build or simulation.

`inventory.json` contains unique concrete hierarchy rows, separate aggregate/duplicate rows, actual selected boundary/reset/clock connections, unresolved dependencies, and hashes of every input and 18 source snapshots. `derive.py` reproduces it from selected commit `4db097403` and die SHA256 `18464a8b31042bea03b3fc5779d42803ab7b05bebbaab733a4d83d4a714c1ea6`. The selected component bodies match the prior PC export identity receipt. Source snapshots are under `source/`.

| Bounded expansion | Concrete rows | Meaning |
| --- | ---: | --- |
| 128 PC chain + ES merge | 512 | Per PC: chain.bfault, chain.fault, merge.m_fault, embedding endpoint.fault. Chain.fault adds local checks as well as forwarding bfault. ES merge.fault is a combinational aggregate of two actual registers. |
| Existing landing exports | 351 | Each wrapper forwards ot_qfd_land.fault: a sticky receiving-clock epoch mismatch detector. |
| Four KC exports | 4 | Local f_ovf registers only. kf is a registered aggregate that also forwards fi via f1/f2; the fi source chains remain unresolved. |
| DCAL | 2 | Wrapper fault and inner sequencer fault both have local checks. Four f_col/f_run/f_stale/f_early registers mirror observability history; the output uses n_* causes directly. |
| Existing_ufh AHUB | 2 + 25 | xf and core.fault are pass-scoped detector registers; 16 Z adder error channels and nine reciprocal arithmetic error channels feed core.fault. Encoded error bits and forwarding/pipeline registers are not independent detector causes. |

The 896 rows above combine explicitly typed detector registers and causal arithmetic channels. They are a bounded decomposition, not a complete or qualified all-primitive count. The previous 357 + 256 = 613 expression counts exports/aggregates and cannot establish a primitive inventory. The complete qualified count is null.

AHUB xf is replaced by bad_t on every start; core.fault is replaced by its start-invalid predicate on start. Therefore the existing ufh aggregate can lose prior-pass health without separate continuous sticky capture. Its reset ancestry is the selected ahub regional reset pipe, including separate IO/core/Z/reciprocal regions, followed by 34 actual core_c forwarding relays. Arithmetic channels are valid-qualified pulses; the core latches them only while active.

Remaining source dependencies are explicit: each PC receives real HOST landing fault from hsl_<stack>_<pc>.land_er[260]; each embedding endpoint receives controller error/uncorrectable return bits; KC fi forwards the PC fault chain; existing PC return core/HBM state is outside this bounded new chain/ES subtask. In particular selected KC_WS fi traverses a pinfix relay clocked by hbm_WS before its core_WS capture. No same-clock phase/edge tail bound follows from the source graph.

No source count establishes reset-first-use safety, physical collector placement, FF/comb fanout closure, actual regional/forwarded clock timing, STATUS deadline, host commit veto, or future admission veto. Those remain model obligations for the parent.
