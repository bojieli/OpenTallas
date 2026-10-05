# Collective transpose clock-only fanout review

Status: **candidate qualification for architecture review; original route
remains NOT MET**. The immutable record at
`results/physical_abi3/asap7/chip/v41_coll_transpose_outpipe1/physical_slew40.json`
routes the full 4×512-bit output-pipelined transpose from source `05ad9903`
at 0.92 ns. It has +120.430 ps routed setup slack, +14.715 ps routed hold
slack, zero DRC and antenna violations, and zero max-slew/cap violations.
Its explicit max-fanout **12** rule fails at 16 clock-tree `BUFx24` outputs,
each fanout 16. No data/control max-fanout violation is reported. The record
must keep its `NOT_MET` verdict.

The source-pinned routed `6_finish.rpt` shows max-slew slack **105.117 ps**
under its 320 ps limit and max-capacitance slack **9.701 fF**; those checks
use the pinned ASAP7 Liberty and routed parasitics. The critical setup path
has **28.38 ps** setup clock skew. Its printed clock branch reaches an internal
`clkbuf_4_14_0_clk/Y` with fanout 16, then two later buffer levels and the
capture FF. The critical-path clock-arrival report lists target latencies
212.379 ps (max) and 234.370 ps (min); these are path-specific, not a
full clock-tree skew distribution. Setup and hold both pass the 0.92 ns
constraint in this physical run.

The physically scoped option is a **separate** clock-tree qualification with
fanout 16 only for these specific clock-buffer outputs while retaining
fanout 12 for data/control nets. That qualification would need to show from
the routed database, for **all 16** nets: actual sink count, capacitance
versus each driving Liberty pin limit, output slew versus limit, clock
insertion and launch/capture skew, setup/hold under explicit uncertainty,
and a sensitivity to the chosen clock variation reserve. A clock-only rule
cannot be inferred from the clean data path or applied globally. Until this
check and architecture signoff, the routed result is an informative full-width
physical negative, not achieved frequency or collective-rate evidence.
