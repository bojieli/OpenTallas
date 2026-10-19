# HBM-NEXT-ATT4 step 3: shared-merge timing fix + publication bench + shrunk outline (2026-10-19)

Primary A1 variant (PROG decision): ONE shared 4-lane PV merge a BF16 column (`ot_hnx_att4_smerge` inside tile
`hnx_rp4a4_spvm`). Step 2 gated it at -398 ps (placement repair, 770 ps route period) on the operand register `u_sm.oa/ob`:
`ph` -> 32-entry descriptor read -> step decode -> turn `sel` -> 12-way 512-b operand mux + bypass (16 levels, select
fanout ~7k), plus the registered reset `rq` at 7.4k loads.

## RTL change (`rtl/hbm_next/att/ot_hnx_att4_smerge.sv`): the turn is decoded one cycle ahead

- Entry (l, ph+1) is written only at its own head turn (7 cycles earlier), and the returning chain of the next head turn is
  `rp_*[ALAT-1]`. The only input that is not known a cycle early is the arriving event, so the merge takes its inputs
  through ONE input register (`ev/sum -> *_q`, pub request too) and the decode reads the raw inputs.
- DECODE stage (cycle before the head turn): descriptors, step, turn, post-step descriptor, collision faults, node-valid
  clear -> registered (`x_*`), plus ONE-HOT selects: operand A/B = ring head word m (12) | returning result | lane l's event
  word (4), and the head writes (event word / returning result) per ring word.
- HEAD stage: per 32-b word g (= adder g) a `(* keep *)` copy of every select (fanout 32; the FLOW-FIX-0410 keep hook keeps
  each copy a flop), so the operand register is fed by a 17-input AND-OR only; the head write is a 2-level mux.
- Reset: kept copies `rst_c` (control), `rst_e` (entries), one `rst_m` a adder (the 16 adders' ~7k reset flops) instead
  of one 7.4k-load net.
- Function: identical to the step-2 merge with its inputs one cycle later (a pure retiming). Every node, tag and fault is
  unchanged; `pv_*` and `pub_*` come one edge later. The compiler counts it: pin -> head turn is +2 edges in
  `hnx_rp4a4_spvm` (pin register + decode stage), request -> first published word +1 edge vs step 2.
- MUT 5 (new negative control): the publication reads lane `pub_lane ^ 1`.

## Benches (Verilator 5.050, fleet ot-epyc4, `tools/hbm_next/att4_a1_matrix.sh`; `bench/`, witnesses `witness/`)

Slice bench (`att4_bench.py`, real DS operands, 4 single-query goldens + cross-SM merge == att_pv per lane), shared variant:

| run | step 3 | PV span max (step 3 / step 2) | QK span |
|---|---|---:|---:|
| sh_s00 (sigma 0) | PASS 200/200 | 386 / 385 | 422 |
| sh_s03 (0.3) | PASS 200/200 | 530 / 529 | 597 |
| sh_s10 (1.0) | PASS 40/40 | 746 / 745 | 792 |
| sh_sdj (disjoint) | PASS 200/200 | 1,090 / 1,089 | 1,115 |
| sh_k500 / k490 / k486 (flush paths) | PASS | 538 / 538 / 386 | 597 / 597 / 422 |
| sh_smut1 / 2 / 3 | FAIL (witnessed) | | |
| sh_smut4 (top-k 512) / sh_smut4k (500) | PASS (unexercised, as step 2) / FAIL (witnessed) | | |

PV spans are exactly +1 cycle on every op (the retiming), still 7-39 cycles shorter than the per-lane merges.

NEW publication-path bench (`tools/hbm_next/att4_pub_bench.py` + `rtl/hbm_next/att/tb_hnx_att4_pub.sv`), the tile
`ot_hnx_att4_spvm` (PUBLISH = 1) at its pins: per round every (lane, slot) runs one chunk run of 1-4 chunks under the legal
record bound of `att4_smerge_sched.py` (aligned / staggered / random lanes; random FP32 chunk sums), then the compiler's
publication requests read all 32 nodes (back to back at word 14 when the slot repeats, else >= 18 cycles apart);
golden = csum8 pairwise tree (`hgi_sim/lib.py pairwise`), plus tag / lane / slot / word order:

| run | result |
|---|---|
| pub_m0 (seed 1019, 24 rounds) | PASS 768 nodes, 0 mismatches (runs of 1/2/3/4 chunks: 132/127/125/384) |
| pub_s2 (seed 2027, 36 rounds) | PASS 1,152 nodes, 0 mismatches |
| pub_m1 / m2 / m3 / m4 / m5 | FAIL 421 / 768 / 636 / 125 / 768 nodes (all witnessed; the tile bench also catches smut4) |

The kit spec (`physical/hbm_next/att4/hnx_rp4a4_spvm.json`) now carries the publication bench + the m5 witness.

## Outline (DIE input)

Step 2 gated 287.28 x 287.28 um at util 0.38 (std guess 40,000 vs 31,587 synthesised). Step 3: spec std 33,000 at util
0.55 -> **250.56 x 250.56 um = 62,780 um2** (-24% vs 82,530). Measured synthesis (gate, ot-epyc7): **32,083 um2, 67,354
flops** (+3.2k: the decode-stage input register + 944 kept select copies) -> util 0.53. Pins: N 1,068 bits (4.26/um), S 1,115
(4.45/um), full faces.

**DIE area (x512 columns, over the release's one merge a column, 23,860 um2 synth / 51,322 um2 outline): shared = +4.2 mm2
cells / +5.9 mm2 outline** (step 2 as gated: +4.0 / +16.0). DIE reserve 16 -> 5.9 mm2 (`../geometry.json` area_die_step3).

## Gates

- hnx_rp4a4_spvm step 3 (250.56 um, --cts, ot-epyc7 `/srv/opentallas-scratch/claude/ref_gate/hnx_rp4a4_spvm-20261019-020708`):
  synthesis textbook lint: worst stage now the DECODE (`ph` -> `ka_hw`, ~608 ps / 14 levels; step 2 operand stage 685 ps / 16
  levels with ~7k select fanout); reset nets 602 (rst_e) / 432 a adder (rst_m) loads, no net > 3,000.  Timing-driven global
  placement first estimate **-308 ps** vs **-745 ps** for step 2 at the same stage (final post-repair / post-CTS numbers in the
  gate result, pending).  If the decode stage still misses: put the per-entry descriptors in 8-stage shift rings like the data
  (entry ph+1 always at stage 1) to remove the 8:1 residue mux from the decode (~3 levels).
- step-2 gates (collected): hnx_rp4a4_pvm (step-1 per-lane macro merge) WARN 0 fail, TT placement RC reg->reg -155 ps @770 on
  the release-fork adder input stage (bp -> g_madd, ~692 ps / 16 levels), CTS TT/FF pin-flop spread 24.9/24.3 ps, insertion
  411.6 TT, GRT overflow 0; hnx_rp4a4_fpvm (fallback) WARN 0 fail, placement repair -122 ps (flop-stack write-enable decode,
  8,192-load XNOR nets), GRT overflow 0; hnx_rp4a4_spvm step 2 (287 um, superseded by this step) still in GRT repair at
  -378 ps on u_sm.oa/ob (not collected).
- fpvm fix NOT done (fallback only; shared is primary and its bench/area/timing all improved): register the write one-hot per
  word with replicated copies + a read bypass of the pending write, if the fallback is ever needed.
