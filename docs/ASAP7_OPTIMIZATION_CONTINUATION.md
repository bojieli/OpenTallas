# ASAP7 optimization continuation, 2026-09-22

The goal remains optimization and recharacterization of the complete design:
pipeline slow arithmetic, reduce area and control overhead, and measure latency
at a modern clock target. A routed block or passing functional test does not
complete that goal. The existing coverage inventory reports 18 instantiated
modules without closed coverage; it must be regenerated against current sources
before being used as a completion claim. The design-level clock must include
every instantiated block, or a verified clock-domain boundary and its overhead.

## Recovered evidence

The prior session's `lim_bothpipe` route is terminal, not still running:
Sinkhorn with `PIPELINED_DIVIDER=1` measures 427.294 MHz, setup slack -0.540311 ns
at a 1.8 ns target. Signal integrity is clean, but timing is not closed.
Do not change its default on this frequency alone: compare whole-design clock
effects and measured transaction cycles as well as local throughput.

The narrowed default series divider in the nonpositive exponential measures
378.281 MHz, setup slack -0.0435409 ns at 2.6 ns. Its critical path is still
`series_divisor_q` to `series_div_upper.inexact`, a ten-step restoring chain.
This is a reason to shorten the chain, not to label the missed target closed.

`results/physical_abi3/asap7/recovered_session_experiments.json` indexes these
records and the positive-exponential sweep, with original paths, record hashes,
and recorded versus current source hashes. The original artifacts remain in the
prior session's scratch directory. This index is recovery evidence rather than
a portable replacement for those artifacts.

## RTL changes and verification

The prior session fixed both Taylor divisors at six bits. That saves three bits
at the default 56 terms, but truncates divisors for larger supported series.
Both units now derive their width as `$clog2(SERIES_TERMS + 2)`, retaining the
default six-bit implementation while covering the next omitted term too.

Both units expose `DIV_BITS_PER_STEP`, default 10, so shorter serial chains can
be measured without editing arithmetic or silently changing all consumers.

`tests/compiler/test_series_divisor_width.py` compares the narrowed implementation
against the previous nine-bit divider on outputs, error codes, ready/valid and
cycle timing. Both exponential units pass with 56, 64 and 254 terms at ten steps,
and 56 terms at four steps. Inputs include magnitude one, magnitude 80, the
minimum subnormal and zero; magnitude one has an independent exact binary32
result check. Positive exp intentionally refuses zero. This is a focused
regression, not replacement of the full certifying arithmetic campaigns.

The existing `tb_wide_div_small_seq_equiv` also passes 354 arguments at each of
six step counts (1, 2, 4, 8, 16, 32), 2,124 quotient/remainder comparisons.

## Active experiment and next work

A source-hashed physical flow was launched for the nonpositive exponential with
`DIV_BITS_PER_STEP=4`, 1.2 ns target, PNR only, slew margin 60 percent:

- Work directory: `/tmp/opentallas-trans-div4-route`
- Output: `results/physical_abi3/asap7/fp32_transcendental_cr_rne/pnr_div4_1p2ns.json`
- Tool session handle at launch: `9515`
- Synthesis was live at the last observation; no routed result was yet available.

Poll this existing job before considering a restart. Inspect its actual critical
path, area, setup/hold and physical violations. Compare added transaction cycles
against clock improvement before selecting a default. The general sigmoid
divider and wide multiplier may become the next limit after the series chain.
Then reroute the containing softmax block, since its old 250.9 MHz record does
not establish timing for modified exponential RTL.

The full arithmetic campaigns and source-bound manifests still need refresh
after selecting the implementation. Continue the remaining instantiated-block
coverage work, control-path review, latency-model updates and whole-design clock
audit; none is discharged by the focused tests above.
