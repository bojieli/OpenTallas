# BF full-rate input hold-seat candidate, 2026-10-09

Source branch `codex/s81-bf-inhold-cx-20261009`. Unified sizing precedes RTL
(`19e0a488f`); RTL opt-in `INPUT_HOLD_SEATS` defaults to zero. The existing
PINREG edges, RECUT arithmetic, throughput and latency remain unchanged.

Four HB2xp67_ASAP7_75t_R cells per captured input reserve 481.7232 um² for
the observed 1,652 routed input flops. The complete 1,672-bit RTL bundle has
an upper bound of 487.5552 um². Each real LEF cell is 0.27 × 0.27 um.
No capture-row fit, new clock topology or routed timing is qualified yet.

The admitted EPYC4 minimal real-library chain probe (`420dd60a6`) drives
one DFFHQNx1 capture pin. It uses the actual TT/FF libraries, an ideal
833.333 ps clock, 60/25 ps uncertainty, zero input minimum and 250 ps
input maximum. It takes no wire-delay credit. Both tool runs exit zero:

- FF minimum chain arrival: 84.421 ps.
- TT maximum chain delay: 126.871 ps (376.871 ps arrival minus 250 ps input).
- The preserved correct-reference BF I2R miss is −72.7 ps with approximately
  470 ps TT input setup room. The analytical remaining hold is +11.721 ps;
  this is a candidate estimate, not full-shape or routed closure.

The full golden transaction bench and enabled-seat stuck-sign negative are
pending remote admission. `model_missing_package_a1.log` preserves the
first attempt's sparse-checkout import failure, before any RTL build. The
same pinned source was retried after including `src` and `configs`.
No route may be queued before actual golden PASS, explicit mutant failure,
correct TT-reference re-STA and Claude review.

Fresh source-preserving baseline reference STA (`393b57467`), EPYC4,
completed at both actual TT and FF with tool exit0. Original source
`6e8f0b698`, route `bfi_recut_cg0_hm0_6e8f0b698`; original ODB/SDC/SPEF
hashes are recorded in `reference_input_sha256.txt`. The original sources,
objects and unsupported legacy reporting-appendix failure are preserved.
The new reports remove that reporting appendix only, preserve the original
loads and boundary policy, and measure the actual propagated clock:

- Correct TT input reference at the original 730ps route period, with
  60/25ps uncertainty: worst input setup +362.255ps (xs_q0[56]).
- Headline833.333ps TT setup −1.532552ps, a genuine internal path miss.
- Actual FF input hold −72.741757ps (xb_sv[0]); boundary insertion mean
  max570.818628/min549.544247ps. No SS-library insertion is substituted.

Full1672-bit technology binding passes with6688 actual HB2 masters
(`tech_probe.log`, source672075b5e), check/assert and cell-count assertion.
This establishes mapped topology only, without capture-row fit or routing.

The actual PVE1 full transaction positive (`positive_a3.log`, clean pinned
82a708f5e) passes456 independent golden rows/912 value assertions/448
configuration assertions, actual-element124422cycles,232partials,4288issues,
and TXN MATCH456 with no faults. Stuck-sign negative is still running;
this positive receipt alone does not authorize routing or adoption.
