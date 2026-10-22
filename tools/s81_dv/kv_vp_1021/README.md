# Real VP / KV consumer component

Run on the fleet from a source tree containing the production KV bank, native
bridge, VP, arithmetic, and SRAM models:

```sh
python3 tools/s81_dv/kv_vp_1021/gate.py --baseline /absolute/kv_bank_run/out --out /absolute/new_run
```

The baseline must be a passing `kv_bank_1021/gate.py` output. Its immutable
golden vectors and shared source hashes are checked and copied. Each attempt
requires a new output directory; prior failures are preserved.

If compilation is interrupted after Verilator has generated its makefile, use
`--resume-objects /absolute/prior_run/obj --jobs 2` with a new `--out`. The
runner checks the old source inventory before resuming make and scans the
generated model with the installed NBA guard before simulation. The real VP
build needs a measured fleet memory reservation; the first 16 GB / eight-job
attempt was terminated during C++ compilation, with no simulation result.

This component replaces the baseline test's behavioral native memory with the
actual `ot_s81sl_vp` and its two 512x128 SRAM macros. Boundary fixture words enter
through the native VP write port. Commands enter VP and use its actual SU command
forwarding output. Every extension response is checked at four edges, with
posedge pre-NBA observations at both request and response pins. The production
KV bridge captures all operands, executes the actual D512 norm/RoPE/QDQ bank,
and drains with the unchanged fixed `DRAIN_AGE=1024` and 104 drain edges. Results
are read back through VP's extension port after the drain. The scoreboard checks
the 25 source-defined output addresses, including both masked exponent halves.
An exponent-write suppression control must fail the same scoreboard.

This proof starts with fixture data at the component boundary. It does not
qualify XS capture, distributed row transport, interrank exchange, SO, or a full
layer/token. Completion is observed for test checking; it does not schedule the
adapter's fixed result drain.
