# HC N-row engine: the first gate of HBM-NEXT (HBM-NEXT-UNITS, 2026-10-19)

**Verdict: PASS.** Each added HC_MIX row costs **250 cycles**. The hard gate is 1,041 (PROG 10-19; it was 950 in STUDY), and the design target is 400. The engine stays bit-exact for every row count tested, and no engine redesign is needed.

## Which engine GEN2 binds (risk M2)

`tools/hbm_die_v16/d4g_layers/l3_vm_hc_coll.py` (`--hc split`, the default) re-masters the die's HC engine as the **split engine**. It is one engine:

- `hc_eng` becomes `ot_hbm_hc_root_static`. This is the root: programme, HCP core TPRE 6, mix store, 2 tail (Sinkhorn) units.
- Each of the 4 `hc_<q>` becomes `ot_hbm_hc_qhub_static` (hc_q plus the quarter centre).
- 32 bank tiles `ot_hbm_hc_bankq*_static` sit around them. That is 8 banks a quarter at 64 lanes, so W 256 x 8 = **2,048 MAC lanes**.

The 4,385 cycles a row in STUDY (d) was measured on the earlier codex 128-lane engine (`codex/hc-static-engine-1014` a35449ada). The die does not bind that engine.

## Measured

The vehicle is `tb_hnx_hc_eng4`:
- `ot_hnx_hc_root` plus 4 `ot_hnx_hc_qeng` rings (centre + 8 bank tiles each);
- the d4g U-ring form: DRLY 2, XRLY 1, QDRLY 2, RAW0 167, RS 104;
- the production shape: K 20,480, 24 mix rows, W 256.

The checks run in lockstep against the golden: `hdc_golden_v41` chunk8 mixes, plus the codex tail reference (sigmoid / exp / Sinkhorn 20) for all 24 result words of every row. The build is Verilator 5.050 on ot-epyc4 (`witness/verilator.txt`).

| N rows | HC_MIX_CYCLES (first x wave -> last result) | mixes / results | verdict |
|---:|---:|---|---|
| 1 | 998 | 24 / 4 | PASS |
| 2 | 1,248 | 48 / 8 | PASS |
| 3 | 1,498 | 72 / 12 | PASS |
| 4 | 1,748 | 96 / 16 | PASS |
| 6 | 2,248 | 144 / 24 | PASS |
| 8 | 2,748 | 192 / 32 | PASS |

- **Further-row II = 250.0 cycles, exactly linear.** This equals the core's compute floor: 25 accumulations (ss + 24 rows) x K / 2,048 = 250.
- The 2 tail units keep pace at that rate (497-edge tail, alternating units).
- The x ingest is far from the limit: 80 edges a row per quarter.
- The committed d4g lockstep `results/rtl/hbm_hc_split_1017/verdict.json` (996 / 1,246 / 2,746) has the same II.

**Mutants (FAIL, witnesses committed):**
- `e1_n4.log`: MUT 1, the quarter-0 bank-3 weight rotation gives MIX_MISMATCH, then HC_ENG FAIL.
- `e4_n4.log`: MUT 4, the quarter-0 tree pairs (0,2),(1,3) give 1-ulp MIX_MISMATCH, then HC_ENG FAIL.

## tok/s impact (D1 model, STUDY `runs/hc_ii.json`)

II 250 is the D1 price, so the composition is unchanged:

- **P = 4:** multi-user 1,091 tok/s a user, 4,365 aggregate; DS MTP 3,364.
- **With the L = 5 COLL lane:** 1,120 / 4,482 / 3,460.

For comparison:
- II 600 gives 1,068 a user and MTP 3,241 (-3.7 %, VEH).
- 4,385 would have given 618 a user.

PROG's target of II 400 is met with 150 cycles to spare.

**One engine or four:** the die builds ONE HC engine (DIE), and one is enough. N = 4 user rows take 750 cycles beyond the first row, and N = 6 verify rows take 1,250.

## RTL delta (hnx fork, `rtl/hbm_next/hc/`)

The fork is a sed-renamed copy (`ot_hnx_hc_*`) of `rtl/hbm_accel/generic/peers/static_hc` at main 41ca41389. The d4g files are untouched.

The datapath is unchanged: the core already takes `cmd_npos` up to PMAX 8 against the stationary weight slot. The N-row delta is in hc_q:

- **Programme word, 79 -> 111 b:**
  - [94:79] = residual row stride;
  - [110:95] = result row stride, in 256-b sectors;
  - 0 = the d4g dense form, bit-identical.
- **Residual reader:**
  - a row counter (SPR issue slots a row; 80 = a quarter slice, 320 = the d4g full-K unit);
  - row base += stride;
  - wave words stay sequential, so the engine's ingest check is unchanged;
  - new faults: a stride that is not 32-aligned or that overlaps, and the last row going past the VM.
- **Result store:** base + p x stride.

Bench `tb_hnx_hc_q`: the real lg pair leaves, the split tap and a fixed-latency VM.

| case | verdict |
|---|---|
| N 4, SPR 80, strides 1,024 / 64 | PASS. 80 waves; rows stream back to back every 4 edges (80 a row, no row gap) |
| d4g dense form (N 2, SPR 320, strides 0) | PASS. 160 waves, = the d4g bench |
| MUT 7: reader ignores the stride | FAIL, 1,920 errors (`witness/q_m7.log`) |
| MUT 8: store ignores the stride | FAIL, 18 errors (`witness/q_m8.log`) |

**ISA decode (CMTP HGI-1R, `cmtp/isa_rows.md`):**
- `residual_npos` = nm1 + 1;
- `residual_row_stride` = rs_A / 8 (FP32 words -> sectors; must be a multiple of 256 words);
- `result_row_stride` = rs_O / 8;
- the weights (B) are broadcast (rs_B = 0) and loaded once a record.

## Files

- **RTL:** `rtl/hbm_next/hc/*.sv`; benches `rtl/hbm_next/hc/tb/`.
- **Fleet script:** `tools/hbm_next/hnx_hc_bench.sh` (stages q, q0, qm7, qm8, e0, e1, e4).
- **Kit:** `physical/ref_tile/hnx_hcq_hub_1019`, the hub tile (hc_q + centre) as an hnx fork of `hbm_hcq_hub_1017`: same outline, pins and macro; io_hold_margin 0.03.

## Open / next

- The landed root (claude/hc-xrdu-1018, XRD/XRU 11) changes latency only: HC_MIX P1 1,020. Re-fork the root when it merges to main.
- A third Sinkhorn tail unit would take the II to the 240 compute floor (-4 %). It is not worth it (owner: significant gains only).

## Re-gate scope beyond the hub (10-19 restart check)

I diffed every `rtl/hbm_next/hc/*.sv` against its d4g source after reversing the rename (`ot_hnx_hc_* -> ot_hbm_hc_*_static`, `ot_hnx_hgi_* -> ot_hgi_*_static`, `ot_hnx_hcp_sys1 -> ot_hdc_v41x_hcp_sys1_static`).

**Only three modules differ:**
- `ot_hnx_hc_q`;
- `ot_hnx_hgi_hc_residual_vm`;
- `ot_hnx_hgi_hc_result_vm`.

All three sit inside the quarter hub `ot_hnx_hc_qhub`, which is kit `hnx_hcq_hub_1019`, closure job `hnx_hcq_hub_1019-n1-c8a284b41`.

**Identical apart from module names:**
- the root (programme, HCP core TPRE 6, mix store);
- both Sinkhorn/tail units (`ot_hnx_hc_tail_unit`, `ot_hnx_hgi_hc_tail`);
- the bank tiles (`bank`, `bankq`);
- `qcen`, `qeng`, `xw_rx`, `eng_seq`, `gathered_mix_reader`.

The core already takes `cmd_npos` up to PMAX 8, and `tb_hnx_hc_eng4` shows the tails keeping pace at 250 cycles a row up to N = 8.

**Verdict:** no further HC tile needs an hnx re-gate. The die binds the d4g HC root/bank/tail views unchanged. Only the hub view changes.

**If the VM grows to 2^19 (`units/vm/README.md`),** the hc_q residual/result base fields widen by one sector bit. That is a hub-only delta, to fold into the next hub revision.

## HUBFIX 10-19: hub wire reach (closure job hnx_hcq_hub_1019-n1-c8a284b41, FLOORPLAN_MARGIN)

`textbook_lint` route.a1 refused the hub with `wire_reach` 3 stages > 500 um:
- `u_q.residual.x_wave_beat[1]`: 608 um (pins `xb_beat_n[1]` / `xb_beat_e[1]`);
- `u_q.residual.x_wave_beat[0]`: 549 um (`xb_beat_n[0]` / `xb_beat_e[0]`);
- `u_q.residual.x_wave_v`: 530 um (`xb_v_n` / `xb_v_e`).

**Cause: NOT the N-row stride counters.** `ot_hnx_hc_qhub` drives the bank beat control (v + beat) on all four faces (W bank 0, N bank 2, E bank 4, S bank 6) from ONE register in the residual reader. On the 734.4 um tile, one flop is at least 530-608 um from one of its face pins. The d4g hub `hbm_hcq_hub_1017` has the same RTL (same `assign xb_v_n = xv; ...`), pins and outline. The d4g hub will hit the same refusal when it is routed with the current lint.

**Fix (structural, zero cycles):** `ot_hnx_hc_xbrep` (not parameterised) adds four per-face copies of the beat-control register. Each copy loads on the same edge from the same next-state (`nx_v`, `nx_en`, `nx_beat`) as the original. The original register now feeds only the centre.
- The kit keeps the copies by name (`route.synth_keep_modules`), so `opt_merge` cannot fold them back together.
- Schedule unchanged: per-record latency delta 0, row II still 250 cycles/added row.
- `ot_hnx_hc_q` / `residual_vm` param XFC (0 = wires of the original, so the d4g form is unchanged); the hub sets XFC 1.

**Benches (fleet, Verilator 5.050, @83a25d2e9).** `tb_hnx_hc_q` now checks every face copy against the original register on every edge:
- q_n4s PASS, q_d4g PASS;
- MUT 7 and MUT 8 FAIL;
- MUT 9 FAIL: the E copy is loaded one edge late, as a relay stage would be, and 321 edges mismatch (`witness/q_m9.log`).

`tb_hnx_hc_eng4` sources are unchanged: the ring benches do not include hc_q. The committed e0 N=1..8 results stand, and the closure job reruns ring_rows.
