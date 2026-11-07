# NK pin-cycle node drain

The vR4 node path uses ICG=1, ICG_IREG=1 and ICG_EREG=1. The node hard leaf runs on the ungated clock. Its valid latency is nine edges: one input register, then an eight-register valid delay. The n_y output face runs on the gated clock.

Number the input capture edge t. Without PINC, node valid reaches the hard-leaf output after t+9. The output face captures valid at t+10 and must capture its falling edge at t+11. The registered enable keeps the gate open through t+D+2 after the node-activity pulse, so D must be at least 9.

With PINC enabled, the additional input register moves node valid to t+10. The two output registers capture it at t+11 and t+12, and clear the output at t+13. Node activity is also delayed one edge, so the gate remains open through t+D+3. D must therefore be at least 10.

The bench supplies exactly 63 paired valid inputs: 27 multiples of 11 in [600,900), plus 36 in [6000,6400). The extra n_b-only pulse at 6300 tests the sticky fault and does not add a node valid word. A correct node output therefore has 63 valid edges, independently of engine work.

A short drain can close the gate just after it captures valid=1. The held output then repeats that valid word until the next activity. This explains why the unmodified reference at D=8 reported excess valid edges and why the vR4 D=9 case failed even though its reference still produced the expected 63 words. A smaller value can also close before the word arrives, dropping it. Those failures do not establish a legal-drain restriction: the general parameter guard accepts 1..255 (the retimed-idle class also checks a lower bound of 2). Neither check prices the nine-/ten-edge node tail.

The patch preserves the public parameter range and floors the effective drain to 9 + (PINC != 0), only for the registered-enable, ungated-node class above. Both normal and retimed counter reloads and the retimed-idle lower-bound guard use that effective value; the retimed busy reload still subtracts one. Other clock-gating classes retain their current implementation.

Cost: no extra data or pin cycles beyond vR4's existing t_out +1 and n_a/n_b-to-n_y +2. At the shortest correct setting, PINC adds one tail clock edge (minimum 9 becomes 10). A requested value below the floor is automatically raised; request 1 becomes 9 without PINC and 10 with PINC. Existing D=64 counters still reload exactly 64 (or 63 for the retimed busy reload), so this change adds no activity, state, ports or cells to that configuration after constant folding. Existing physical/LEC jobs retain their own source identity and are not modified by this patch.

The bench adds an isolated fault-only pulse after the node traffic and engine work. A valid-pulse train can keep the gate open and fail to exercise opening from idle. The one-edge-late activity mutant must be tested on the isolated pulse; its survival in the original D=64 run was an unsensitized control, not evidence that the activity term is redundant.

For an isolated fault-only pulse at t, PINC=1 places the fault at fy_q after t+2. The registered enable must open the gate for n_y_p at t+3, followed by n_y_q at t+4. The one-edge-late activity mutant first opens at t+4 and misses that one-edge fy_q pulse. The new D=10 test catches exactly this loss at edge 11504; a long drain cannot protect the opening of a gate that is already closed.

## Validation, 2026-11-07

Source base: `2371c9bf991fe0fc00a42c4926ca71cd9d06aa4e`. Full-class tests use NKP=15, LQR=31, RSTP=3, PINC=1, ICG=1, ICG_EREG=1, ICG_IREG=1, ICG_RRST=1 and ICG_IDLE_RT=1. The reference uses PINC=0 and RSTP=0. No valid/data comparison qualifier was changed.

| Requested drain | Nonmutant result |
| --- | --- |
| 1 | PASS, 4608 engine words, 63 node valid edges, zero qualified mismatches |
| 8 | PASS, same counts |
| 9 | PASS, same counts |
| 10 | PASS, same counts |
| 64 | PASS, same counts |

Every passing run compares 12000 edges, reports t_out +1 and checks n_y at +2. Mutant p1 at drain 10 fails with 5704 qualified node mismatches. Mutant p2 at drain 10 fails on all 4608 engine words and reports t_out delta 0. Mutant p3 at both drain 10 and 64 fails on exactly one qualified fault edge, 11504. All controls fail as expected.

The first requested-drain-1 attempt hit the old raw-parameter lower-bound assertion. That failure remains intact. After moving the effective value to module scope and using it in that assertion, a fresh drain-1 attempt passes. The other tested configurations have the same effective reload constants before and after that assertion/scope correction.

Three controller-only Yosys miters pass: old drain 64 versus new drain 64 at PINC=1; old drain 10 versus new requested drain 1 at PINC=1; and old drain 9 versus new requested drain 1 at PINC=0. The unchanged arithmetic body is abstracted by an arbitrary busy input and an observable gated-clock output. The reset relay is retained, with async2sync used for the sampled formal model. These checks supplement the full-class data bench; they do not replace the existing full/routed LEC.

For drain 64, removing the constant-equivalent drain alias and its declarations reconstructs the original top byte for byte: SHA256 `fba60f8183024725c54593d4778ea1adc5606ddb5fbba82aa4165cab17c38d7b`. The generated body remains byte-identical, SHA256 `4cd4ea752d6bddb4a029cdf45d6aa9e18bd4b021efaf9c2557db184b99a96229`. PINC still defaults to 0. Existing physical and LEC inputs were left untouched.

Evidence: `epyc5:/srv/opentallas-scratch3/claude/codex-nk-drain-1107/`, especially per-case result.json/run.log, guard_fix_d1, gate_proof_v4 and D64_source_identity.json. The original sweep ran in guarded direct unit `oth-ubuntu-1475116-1794061794`; its exit 1 records the preserved first drain-1 assertion. The corrected drain-1 unit `oth-ubuntu-1851750-1794062527` and controller-miter unit `oth-ubuntu-1836841-1794062498` both returned exit 0. The resolved nine-case matrix has five expected passes and four expected mutant failures.
