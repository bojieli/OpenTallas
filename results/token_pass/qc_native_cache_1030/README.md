# Native59 completion-cache reserved-bit refinement

PASS for the twelve unreset low reserved cache bits and their actual STATUS valid mask. This is a component proof, not a native59 whole-unit LEC result.

The actual source captures each cache only on an accepted completion. Legal begin tags have low six bits zero, and the held tags reset to zero. The last-completing-slot selector chooses a cache loaded on that accepted event. Before any accepted completion the STATUS observer masks its native payload; afterward the selected reserved bits are zero. Both concurrent-completion priority and arbitrary accepted-event spacing are included.

`miter.sv` instantiates the exact `qfd_status_obs_hold_chunk` and exact extracted `ot_qwen_status_obs_v1_state` source. Its accepted-completion inputs are arbitrary: no producer protocol or START delay is assumed. The test abstracts unrelated tag payload to zero because this proof concerns only the low six bits in each slot; observer context, result, and epoch inputs remain free. All initial flip-flops are arbitrary defined Boolean state, including both unreset caches. Four common local cold-reset edges are applied; no assertion is made about the physical reset graph or asynchronous release relation between different components.

| Check | Result |
|---|---|
| Actual two-observer full 208-bit snapshot and fault comparison, 16 edges | PASS |
| Capture-low-bit corruption mutant | FAIL, detected |
| Wrong-slot/unloaded-cache selection mutant | FAIL, detected |
| Single-observer valid-mask invariant, temporal induction | PASS, induction step 1 |

The inductive invariant includes held-tag low bits zero, `seen -> selected_cache_low == 0`, `completed -> seen`, actual STATUS `nat_v -> seen`, and actual masked snapshot low six bits zero. Thus the reserved cache payload is unobservable before initialization and known zero whenever observable. Fault and the remaining snapshot outputs have no combinational dependence on these six payload bits; the bounded full comparison is an additional check, not a whole-unit refinement claim.

An earlier broad induction over two independent observer state replicas grew without their state-congruence invariant. It was stopped as NOT PROVEN; its immutable `induct.log` remains in the remote scratch directory. The original setup attempt retained the module keep_hierarchy attribute and selected multiple modules; it was NOT RUN and is also preserved remotely. Neither is relabeled a design failure or a pass.

Reproduce the bounded checks with `run_r2.sh` after setting its work directory. Reproduce induction with `yosys -Q -T -s mask_induct.ys`. Source hashes are in `source.json`; logs and mutant counterexamples accompany this receipt. Heavy worker units: bounded r2 3110968; mask induction 3383524-1793362800 on intel2. Source files and logs originate from `/srv/opentallas-scratch2/claude/codex-native-cache-proof-1030`.

The six separately reported fault-state differences remain HELD. This proof adds no constraints on incoming fstart, mission start_i, quasistatic straps, bound CA paths, or the unqualified current QC provider. It changes no RTL, model cycles, plan, or selected source.
