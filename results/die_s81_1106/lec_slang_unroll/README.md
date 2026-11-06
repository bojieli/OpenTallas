# Native-C finite Slang elaboration recovery

Scope: **frontend elaboration only**, not RTL/netlist equivalence or physical qualification.

The four captured native-C attempt-3 forms (`dsdv_slice_lepe_mu_C__t1`,
`dsdv_slice_c1x_C__t6`, `dsdv_slice_lepw_mus_C__t1`, `dsdv_slice_c1x_C__t8`)
failed the independent Slang lint before correspondence. Their Verilog synthesis
was not the failed step. The retained failure reports `unroll limit of 4000
exhausted` at `ot_s81sl_xs4.sv` lines 1127 and 1143.

The output-register process contains three finite literal loop nests. Counting
each nested loop's iterations gives:

| Nest dimensions | Iteration tally |
|---|---:|
| 8 × 32 × 3 × 4 | 8 + 256 + 768 + 3072 = 4104 |
| 10 × 3 × 2 | 10 + 30 + 60 = 100 |
| 4 × 8 × 32 × 3 × 8 | 4 + 32 + 1024 + 3072 + 24576 = 28708 |
| **Whole process** | **32912** |

The first nest alone exceeds the frontend's default. The fix adds the reusable
`OT_LEC_SLANG_UNROLL_LIMIT` option, accepted from the captured kit configuration
or the caller environment. It accepts only positive decimal integers; zero,
unlimited, negative, malformed and option-injection values are rejected. Absent
this option, Slang's existing default is unchanged. No source-size heuristic,
unlimited unrolling, automatic retry or proof assumption is introduced.

For the unchanged XS4 source above, put this in a **fresh captured** configuration:

```make
export OT_LEC_SLANG_UNROLL_LIMIT = 32912
```

Alternatively set the same environment variable; host Docker dispatch forwards
it. The async proof identity includes the captured configuration value and the
existing `OT_LEC_*` environment inventory, so a changed budget cannot silently
reuse an earlier async proof. It applies to each Slang read (lint, BB extraction,
and gold); the Verilog frontend is unchanged. Do not edit a live kit to enable it.

Actual canary: E4 unit `oth-ubuntu-1407999-1793966059`, 16 GiB/one thread,
completed with exit 0 in 19 seconds for the combined canary. The captured lepe
lint command read the **same frozen sources**, with only
`--unroll-limit=32912` added; elaboration passed. A deliberately nonterminating
loop under that same finite budget failed with `unroll limit of 32912 exhausted`.
`receipt.json` records exact RTL hashes, image identity and both return codes;
compressed logs preserve the complete original 4000 failure, actual pass and
negative control. The original kit was mounted read-only.

Six focused tests cover default preservation, captured/config selection,
invalid/unlimited rejection, Docker forwarding, async identity separation and
unchanged RTL/Verilog commands. Full LEC remains **NOT RUN** by this lane: the
canary removes one concrete frontend blocker, and does not resolve other
warnings, mapping differences, timing, busfit, or signoff gates.
