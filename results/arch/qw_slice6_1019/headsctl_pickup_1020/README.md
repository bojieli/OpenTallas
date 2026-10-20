# HEADS/CTL takeover evidence, 2026-10-20

All three collected candidates are **FAIL under the binding native census**, independent of their old gate verdict. No submission is authorized by these receipts.

| Candidate | Gate result | Nonclock drivers >32 | Flop drivers >32 | Maximum loads |
|---|---|---:|---:|---:|
| xhead gate3 | WARN, 0 failure, GRT 0 | 75 | 58 | 2585 |
| ctl gate2 | WARN, 0 failure, GRT 0 | 136 | 49 | 1956 |
| ctlb gate2 | FAIL, GPL-0305 placement divergence | 136 | 49 | 1956 |

The census parses the exact mapped netlist with the existing textbook parser and counts terminal loads through BUF/INV trees. It excludes clocks, constants and physical buffers/ties as roots; resets remain included. Full offending-driver lists and SHA256 bindings are in each census.json. Compressed mapped netlists preserve reproducibility; run `python3 results/arch/qw_slice6_1019/headsctl_pickup_1020/census.py`.

xhead worst drivers: u_head.b_d[474] 2585, b_d[473,475:478] 2177 each, fep 1707, fill-go delay stage 877. The mapped b_d name aliases the internal shared f_q register even though the top onward output is unused. Root structure is shared fill fields / shift selects and epoch selection, rather than missing exterior input pin flops. Internal go delays >=3 stages also need ring/storage review. Both output retag paths retain one combinational level after the last flop, so literal every-output pin registration is not proven by the kit opt-out. Gate reg->out slack -944.8 ps; TT/FF boundary spreads 52.0/48.8 ps.

ctl worst driver is reset relay g_rr.u_ra.q, 1956 reset sinks; other resets u_rc 165, u_rs 157, u_rg 126 also violate the cap. Embedded argmax control am_u[0] drives234; input pin q_sc_w1_we drives113. Five module-level kept reset relays do not regionalize the embedded argmax or the remaining consumers. All 136 violations must be resolved, including combinational decode roots. Main gate setup +58.7 ps, TT/FF boundary spread58.5/54.8, GRT0 does not override this result. Fallback exact mapped SHA is identical, so changing outline alone cannot resolve fanout.

Storage: synthesized macro counts zero (xhead7916 / ctl7305 flops). This is an inventory observation, not proof that each flop bank violates the 2kb rule. xhead per-epoch row tables and ctl argmax state need a bank-by-bank storage/depth audit before a successor can be marked safe. Reach: existing textbook fixed-terminal estimates are xhead148.6um and ctl0um, measured against a legacy500um threshold; they do not constitute an all-net placed405um census. Registered inputs: existing textbook reports0 input depth and0 input-to-output bits; output xhead has1 level, ctl0. Thus storage/reach/exact pin compliance remain open in addition to the measured fanout failures.

Actual floorplan PNGs for xhead and ctl were inspected: xhead216x432, ctl345.6x259.2, no macros and pin-heavy perimeter; the sparse pin-bound outlines alone do not cure shared wide controls. CTLb432x216 failed placement. Images are preserved as diagnosis, not approval.

Benches: heads eq0 PASS124614 compares, eqxh FAIL23736/124614 (expected mutant witness), bench2 production cases PASS. CTL eq0/eqd11 logs are still build-only at collection; do not claim PASS. Original live jobs are preserved. xheadb gate3 child PID2164565 (parent2164561) and CTL bench fleet units remain owned by existing pending entries3053/3055. No new fleet job, gate or submit was launched.

Source references: HEADS f4746778a (gate3 taken from b9895e3e0), CTL1f858dec1, HEADS benches50b338272. This evidence-only branch forks HEADS and contains no parent s5 source edit; cherry-pick its evidence commit only.
