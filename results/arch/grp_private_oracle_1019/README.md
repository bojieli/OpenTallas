# Selected GRP private ABI component oracle

PASS: two full selected components, GRP and GRP_H, with all retained outputs
compared against the exact selected public wrappers. The 2,048-edge run performs
38,912 vector comparisons across all 19 retained outputs (5,823 output bits per
edge). Five actual source-equation mutants produce the required causal failures.

The reference is the selected `_mu_ba` wrapper file SHA256
`df66545140a103b45170c9132cf19e521945c61c8fc649e836df4bb9c49e6e97`.
The private pair has SHA256
`00ef5753843beb24ed7b137318b9481a2f208ab56aa287f216ad1bc979d91de9`.
No retired `_ds` wrappers, output-age compensation, forced child outputs, or
reduced components are used. Both sides instantiate the same 16 real leaf
module definitions, including five actual boot transports and the actual landing
SRAM behavioral model. `closure.json` pins each leaf; every definition matches
the frozen GEN8 5f2 source root (`selected_leaf_identity.json`). Macro identity
uses its entire model file; the other identities use exact extracted module text.

`tb.sv` drives complete random inputs, deterministic EST toggles, independent
core/HBM clocks with half-periods 5/7 ns, initial reset and two reset pulses.
GRP_H's trimmed control input receives exactly the public low 194 bits; scalar
EST receives exactly public bit zero. Original extra input bits remain driven.
All retained outputs are compared one ns after each core rising edge, including
reset. This is a finite two-state Verilator equivalence simulation. It is not an
exhaustive formal proof, a legal boot programme qualification, an arbitrary CDC
phase proof, or throughput/physical qualification. The separate private-source
structural proof checks every retained equation and instance connection.

| Source mutant | Expected fail witness |
|---|---|
| GRP retained EST inverted | est_grp.log: y__est__0_1, edge 0 |
| GRP retained down bit corrupted | down_grp.log: o_dn, edge 0 |
| GRP down permutation bypassed (`o_dn=i_ctl`) | down_permutation.log: o_dn, edge 0 |
| GRP_H retained EST inverted | est_h.log: y__est__0_1, edge 0 |
| GRP_H retained control bit corrupted | ctl_h.log: o_ctl, edge 0 |

Mutations change actual wrapper source assignments. The bench comparison itself
is unchanged. Every mutant log and exact mutated source is retained; positive
and mutant return codes are in `results.json` and `permutation_results.json`.
The initial elaboration failure omitted `ot_async_fifo` from the dependency
closure. It is preserved as `attempt1_missing_fifo.build.log`; the corrected
closure includes the real FIFO, reset synchronizer, and select-copy modules.

All compiles/simulations ran through unpinned ot-run on ot-epyc8, 64 GB / 8 threads,
with the closure daemon's exact Verilator 5.050. Terminal units:
- missing-dependency failure: oth-ubuntu-1810556-1792442672, exit 1;
- positive and first four mutants: oth-ubuntu-1810813-1792442703, exit 0;
- down permutation mutant: oth-ubuntu-1811617-1792442737, exit 0.

Reproduce from this directory on the fleet:
`python3 run.py` then `python3 run.py --extra-permutation`.
`prepare.py` regenerates the frozen wrapper extraction and bench from selected
source snapshots and repository leaf definitions; the committed `leaves.sv`
is the immutable leaf input actually simulated. No gate, source adoption,
placement, constraints, schedule, or physical files are changed by this packet.
