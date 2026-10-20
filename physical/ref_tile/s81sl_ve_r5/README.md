# s81sl_ve_r5 -- VE5 opt-in native-32 ve (S81-GUVE, 10-20, tree S81.STA.OWN.3 / OWN.3.1)

RTL: r4 (9ad718735, claude/s81-ve4-1020) + Codex VE5 opt-in 73b3a517a (codex/s81-ve-loadsafe5-1020), selected by the spec
define OT_S81_VE_LOADSAFE5 (synthesis, lint and every bench: OT_VE_DEFS). Default source (no define) is unchanged.
Why: the r4 --cts gate ep7 ref_gate/s81sl_ve_r4-20261020-055315 was REFUSED at the pre-floorplan native census
(PRE_GATE_NATIVE_CENSUS_REFUSED, 4 roots > 32: three fmul s2_top[3] at 33 loads, normal hidden-bit decode at 34).
VE5: a fifth kept same-edge s2_top copy drives only the exponent/overflow select; hidden-bit low/high partition 9/15
(was 12/12). +1 FF per ve-local fmul, combinational partition only, zero added cycles, no arithmetic change.

Census (full actual-source native, r4 gate cohort 055315 synth recipe + the define; Codex unit2004335,
ep7 /srv/opentallas-scratch/claude/codex-ve5-full-native-1020/work/native_census.json): PASS limit 32, max 32,
0 violations (reset nets included), mapped sha 570ba6a2e0ea...; r4 was 4 roots > 32 max 34; r3 1,919 / 131.
Unit proofs (bde80f8e8, results/rtl/s81_ve_loadsafe5_1020): Verilator 5.050 default + opt-in 300k cycles random
init + mid-run reset PASS (262,613 add / 262,612 mul comparisons), 2 scoreboard mutants + causal wrong-exponent
mutant REJECTED. Whole-ve benches (beat exact / GAP2s5, MUT1/2/3, miter vs r3 + MUT1) re-run with the define:
witnesses in results/rtl/s81_ve5_1020.

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pins registered, reset landing | PASS: source-registered inputs (*_q) and flop outputs; rst_n 2-stage landing |
| 2 | reach <= 405 um | PASS: 345.6 um square tile, one clock region; gate-measured |
| 3 | fanout <= 32, kept copies survive | PASS: full native census max 32, 0 violations (r4: 4 > 32, max 34) |
| 4 | depth | unchanged from r4 (f12 boundaries LAT 4 / 5; 2-stage 7/4 jam); gate-measured |
| 5 | storage > 2 kb | PASS: delay lines >= 3 are one-hot ring buffers; no new flop arrays |
| 6 | floorplan | no macros; outline 345.6^2 from synthesis area at util 0.5; full std-cell band |
| 7 | clock | single centre-fed root, one region (no crossings); spread <= 80 TT/FF measured by the --cts gate |
| 8 | schedule | PASS: zero added cycles (miter cycle-exact vs r3), static |
