# Full-geometry DeepSeek attention numeric gate

This gate uses the unchanged H16/D512/TD32/NL4/TROWS640 attention RTL and
its existing testbench. The software golden provides Q, stored-format KV,
and BF16 probabilities. The testbench checks every FP32 score and PV result,
including expected fault indications.

## Evidence boundary

This is full-geometry **standalone numerical attention**, not a full token,
checkpoint-derived layer, HBM integration, SU softmax, physical implementation,
or an achieved-frequency/token-rate claim. The probability input is provided
by the golden. The bench's cycle count includes its driver and barriers.

The compiler uses reusable hierarchy blocks while retaining RTL clocks and
handshakes. The initial8GiB-capped probe failed during top elaboration; a
subsequent PVE2 front-end completed with12,937,200KiB peakRSS (recorded exactly in
status.json). Source pins are unchanged. Existing generated C++ archives were
linked to the original harness; no replacement numerical datapath was used.

## Reproduction

Generate four synthetic cases, each as a separate process because the
original bench has320 probability words of image capacity:

```
python3 tools/v41_full_attention_numeric_prepare.py --root . --out /tmp/v41-attention-vectors
```

`results/rtl/v41_full_attention_numeric/status.json` records the exact full
front-end command. Build its existing `Vtb.mk` archive and hierarchical child
libraries, then link using `tools/v41_full_attention_numeric_link.py`. That
script checks the build's `pins.json` and refuses to recreate an absent archive.
Pass absolute paths for build and harness.

```
python3 tools/v41_full_attention_numeric_run.py --exe /path/to/Vtb_exact --vectors /tmp/v41-attention-vectors --out /tmp/v41-attention-results
```

The runner verifies all image hashes and requires all expected outputs,
zero mismatches, exact expected fault count, one completed job and no timeout.
Sources, golden generator, images and executable are recorded by SHA256.

## Next integration gate

Use these same window128 KV images to drive the real WINDOW block-write
producer. Retain delayed HBM write completions, packed refill and source
backpressure, and connect its packed output to this numerical engine.

The combined engine retains KV internally between QK and PV. This does not
prove that the current core adapter's separate QK/PV descriptors avoid their
second refill. That requires an explicit retained-lifetime contract or the
actual two-descriptor integration test.

## Measured verdict

All four cases pass:24,592 score outputs and32,768 PV outputs checked,
zero mismatches. The wide-exponent case expects9,670 fault indications, all
matched; these are deliberately exceptional operands, not clean checkpoint
activations.

| Synthetic case | Rows | Bench cycles | Score/PV mismatches |
|---|---:|---:|---:|
| Window FP8 |128|225|0/0|
| Mixed FP8/FP4 |640|609|0/0|
| Mixed wide-exponent |640|609|0/0|
| Partial final block |129|234|0/0|

The640-row case issues160 PV beats over312 cycles (248through559 inclusive),
consistent with the one-probability-word-per-cycle loader bottleneck. Last PV
output is cycle609; no frequency conversion is credited.

Negative checker control flips one bit of the expected first score while
holding inputs and executable unchanged. It produces exactly one score
mismatch and no PV mismatch, showing the checker compares the result bits.
This is checker sensitivity, not a hardware-fault-detection claim.
