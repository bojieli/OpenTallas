# HBM-NEXT-ATT4 step 2: risk A1, the PV merge of a 4-query BF16 column (2026-10-19)

PROG decision (10-19 00:36 / 01:35): shared 4-lane time-multiplexed merge = PRIMARY, per-lane flop stack = FALLBACK,
chunk sums to COLL = rejected. Step 1 measured the per-lane macro merge (one `ot_hnx_att_pv_merge` + 64x512 macro per
lane) at ~37 mm² cells / ~79 mm² outline per die, against 0.21-0.3 mm² in the model.

## Variants (all in `rtl/hbm_next/att/`, selected in `ot_hnx_att4_slice` by SHARED / STORE / LV)

| variant | RTL | merge state | adders per column |
|---|---|---|---|
| base (step 1) | 4 x `ot_hnx_att4_pvm` (STORE 0) | 64x512 SRAM macro a lane, LV 4 | 4 x 16 |
| flop (fallback) | 4 x `ot_hnx_att4_pvm` (STORE 1, LV 3) -> `ot_hnx_att_stack_flop` | 8 entries x (3 levels + node word) of flops a lane | 4 x 16 |
| shared (primary) | 1 x `ot_hnx_att4_spvm` -> `ot_hnx_att4_smerge` | per-lane LV 3 x 8-stage flop rings, head-only access | 1 x 16 |

Shared merge: one 16-adder FP32 datapath (ot_gpu_fadd LAT 7 = one 8-cycle ring turn) serves all 4 lanes. Entry
(lane, residue) is touched only at its ring head; events are written at arrival into the binary counter's free level
(no hold buffer, no stall); the turn order (returning chain keeps the turn, else lowest lane) is a fixed function of the
record's lane masks, so the compiler replays it. Collision = sticky fault. LV 3 = runs of up to 4 chunks (enough
for the bench's production top-512 shape, which passes; longer runs fault).

## Schedule stress (`tools/hbm_next/att4_smerge_sched.py`, Python model of the smerge turn rule)

- LV 3: 20,000 trials (aligned / staggered / random lane event patterns), 199,568 nodes, **0 faults**, worst node
  latency 8 turns = 64 cycles (`sched_stress_lv3.json`).
- LV 4: 77 faults in 5,000 trials (`sched_stress_lv4.json`), all "event on an entry with an unissued step" (aligned
  lane patterns, 8-chunk runs). LV 4 is NOT supported by the shared merge; LV 3 is the production setting.

## Benches (Verilator 5.050, `tools/hbm_next/att4_a1_matrix.sh`, ot-agidock128, run m2 on the committed sources)

Real DS operands (head dim 512, window 128 KV8 + top-k KV4 a lane), golden = 4 single-query runs + cross-SM merge ==
att_pv on every lane. `bench/<run>.{log,json}`.

| run | sigma (overlap) | top-k | shared | flop | PV span max shared / flop / base (step 1) |
|---|---|---:|---|---|---|
| s00 | 0.0 (full) | 512 | PASS 200/200 | PASS 200/200 | 385 / 393 / 401 |
| s03 | 0.3 | 512 | PASS 200/200 | PASS 200/200 | 529 / 561 / 569 |
| s10 | 1.0 | 512 | PASS 40/40 | PASS 40/40 | 745 / 777 / 785 |
| sdj | disjoint | 512 | PASS 200/200 | PASS 200/200 | 1,089 / 1,121 / 1,129 |
| k500 / k490 | 0.3 | 500 / 490 (partial last run: flush paths) | PASS | PASS | 537 / 561 |
| k486 | 0.0 | 486 | PASS | PASS | 385 / 393 |

QK spans are identical across variants (422 / 597 / 792 / 1,115). The shared merge is **not slower**: its PV span is
8-40 cycles SHORTER than the per-lane merges (measured; the flop variant at the same LV 3 is 8-32 cycles slower than
shared).

Mutants (witnesses `witness/*.log`, regex `^FAIL HNX_ATT4`):

| mutant | what it does | result |
|---|---|---|
| sh_smut1 | event bypass dropped for operand B | FAIL |
| sh_smut2 | result written into lane l^1's ring | FAIL |
| sh_smut3 | ripple reads one level too high | FAIL |
| sh_smut4 / sh_smut4k | flush's first add drops S[k0] | top-k 512: PASS (no flush with popcount >= 2 at 4-chunk runs: unexercised); top-k 500: **FAIL** (witness sh_smut4k) |
| fl_pvmut1 | merge ripple reads +1 entry | FAIL |
| fl_pvmut2 / fl_pvmut2k | stack level LV-1 read as 0 | top-k 512: PASS (unexercised at LV 3); top-k 500: **FAIL** (witness fl_pvmut2k) |
| fl_pvmut5 | flop stack read one entry up | FAIL |

## Area (synthesis + gate outlines, 0.77 ns route period; per BF16 column of 4 query lanes)

| variant | tile | synth area um² (cells + macro) | flops | outline um | outline um² | per column cells / outline um² |
|---|---|---:|---:|---|---:|---:|
| base | hnx_rp4a4_pvm x4 | 23,860 (10,336 std + macro) | 12.2k | 216 x 237.6 | 51,322 | 95,440 / 205,290 |
| flop | hnx_rp4a4_fpvm x4 | 21,736 | 29.1k | 194.4 x 194.4 | 37,791 | 86,940 / 151,160 |
| shared | hnx_rp4a4_spvm x1 | 31,587 | 64.1k | 287.28 x 287.28 (util 0.38) | 82,530 | 31,590 / 82,530 |

**A1 figure for DIE / PROG (die increment over the release's one merge a column, x 512 columns):**

| variant | cells mm² | outline mm² (as gated) | outline at util ~0.57 |
|---|---:|---:|---:|
| base (per-lane macro) | +36.6 | +78.8 | - |
| flop fallback | +32.3 | +51.1 | +51.1 |
| **shared (primary)** | **+4.0** | **+16.0** | **~+2.1** (31.6k / 0.57 = 55.4k um²) |

The shared merge cuts A1 by ~9x in cells and 5-37x in outline; the residual (+2-16 mm²) is what DIE reserves (use
+16 mm² until the outline is shrunk by a passing gate).

## Timing (gates still running at 01:55; final numbers in the gate results)

- base pvm (agidock128, --cts): post-CTS SS setup ws -217 ps on the `g_madd` adder ring, FF hold +30 ps.
- shared spvm (epyc4): placement repair WNS -398 ps at endpoint `u_sm.oa[*]` (operand register). Path = `ph` residue
  counter -> 32-entry descriptor read -> step decode -> `sel` -> 12-way 512-b operand mux + bypass (textbook: 16 levels,
  685 ps; `rq` reset fanout 7.4k).
- flop fpvm (epyc4): placement repair WNS -122 ps on the flop-stack write enables (`u_stack.w[*]`; 8,192-load decode
  XNOR nets).

Fix for the shared merge (next step, RTL): decode the turn one cycle ahead. The descriptors of residue ph+1 and the
returning chain are known a cycle early; register sel / s_a / s_b as one-hot per-512-b-slice replicated selects so the
operand cycle holds only the mux + bypass; land the reset per region. The adder-ring miss is shared with the base
(release fork) merge.
