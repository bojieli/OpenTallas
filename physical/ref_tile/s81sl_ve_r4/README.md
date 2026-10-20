# s81sl_ve_r4 -- native-32 ve (S81-RTLFIX / VE4, 10-20, tree S81.STA.OWN.3.1)

RTL: rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv + ot_s81sl_ve_fp.sv (claude/s81-ve4-1020). r3 6ad9506a1 failed the actual-Liberty
native census (1,919 roots > 32, max 131); r4a (lane WIP) 370 / 64; r4b 39 / 49; r4c 24 / 49; r4d PASS max 32, 0 violations
(327,322 roots; results/rtl/s81_ve4_1020/r4d_native_census.json.gz, yosys 0.68 + ot_keep_regs hook, TT libs, ABC -D 770).
Root causes fixed: (a) a kept WIRE is not an ABC cut -> shifter stages / decodes / picks / hidden bits / enable ANDs are
keep_hierarchy module instances; (b) opt_merge folds a non-kept register twin into its kept copy -> BOTH copies kept
(fadd/fmul y/y2, ring dout/dout2, tree h/b, chunk xr, add8 vl1/vl2); (c) one 28-line one-hot jam -> 7-line x 4-line stages.

Benches (Verilator 5.050, ep7 /srv/opentallas-scratch/claude/s81-ve4/out_r4d): ve beat bench exact / GAP1 / GAP2s5 / s3 PASS,
MUT 1/2/3 REJECTED; miter vs r3 RTL (random power-up, 8 in-flight resets) seeds 7/29 + GAP2s5 PASS, MUT 1/3 REJECTED (MUT 2
needs GAP 1: caught by the beat bench); fp unit bench vs shared f12 units every edge 3.5 M add + 3.5 M mul PASS, MUT 1/2
REJECTED; unit census PASS max 31.

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pins registered, reset landing | PASS: every input lands in a pin flop, every output is a flop (source); rst_n 2-stage landing |
| 2 | reach <= 405 um | 345.6 um square tile, one clock domain; gate-measured |
| 3 | fanout <= 32, kept copies survive | PASS: native census max 32, 0 violations, reset included; copies checked in the mapped netlist |
| 4 | depth | f12 register boundaries unchanged (LAT 4 / 5); jam now 2 AND-OR stages (7 / 4) instead of one 28-wide; gate-measured |
| 5 | storage > 2 kb | delay lines >= 3 are one-hot ring buffers (r3); no new flop arrays |
| 6 | floorplan | no macros; outline from synthesis area estimate at util 0.5 (re-sized from the gate's measured area if needed) |
| 7 | clock | single centre clock; spread <= 80 TT/FF measured by the --cts gate |
| 8 | schedule | PASS: zero added cycles (miter cycle-exact vs r3), static |
