# IDX.TOPK redesign: `ot_hgi_idx_tk2` (el1013 redesign-idx, 2026-10-13)

From-scratch engine for the production IDX.TOPK shape (DS-V4.1 1M `route.top6`: n 384, k 6, ascending ids), opt-in
through the unit parameter `TK2 = 1` of `rtl/hbm_accel/generic/idx/ot_hgi_idx_unit.sv` (default 0: every existing
path is unchanged). The old engines (`ot_hgi_idx_topk_registered`, `ot_hgi_idx_topk_heap`) are reference only.
Parent commit `b54c3214a`; the RTL, benches and these results are one commit on `claude/hbm-redesign-idx`.
Everything below is measured (logs in `logs/`, numbers in `report.json`).

## Result

| | cycles / TOPK record | ratio to the price 283.008 |
|---|---|---|
| default reader (`m0`, committed record) | 1,212 | 4.28x |
| **tk2 (`t0`)** | **169** service (170 record-to-record period) | **0.597x** (0.601x) |

Limit 1.10x = 311 cycles: qualifies. Design budget was ~156; measured 169. All six TOPK records take 169 cycles.
The three IDX.OWNED records of the bench are untouched (1,240 / 4,515 / 1,236).

## Architecture (as built)

- Reader: A prefetched sector by sector on the unit's VM packet client, at most 4 requests outstanding (reads and
  writes share the 4; a 4-entry kind queue separates the in-order responses), 4-entry sector FIFO.
- S1: the FIFO head is taken in two phases (words 0-3, 4-7), one word a lane a cycle, registered as
  {valid, key, nz, id}. key = FP32 as an unsigned total order with -0 folded onto +0 (the golden `topk_ids` compares
  numbers, so -0 == +0 and the lowest index wins); nz keeps the -0 bit pattern for the R value. NaN fails the record
  closed before any output of that row is written.
- 4 lanes x 8 sorted register entries; a lane inserts one word a cycle (8 parallel compares against registered
  entries, one-position shift insert).
- Merge: the lanes shift out their first k entries one a cycle (4k cycles) into a final 8-entry list
  (value descending, id ascending).
- Order: one cycle of ranks (order = 1: 28 id compares; order = 0: slot), one cycle of one-hot placement.
- Writes: O (ids) and R (values, when present) rotated to their word offset and written as whole-sector VM writes
  with byte masks (one write a touched sector, at most two a stream).
- m rows back to back; done rises after every issued request has been answered.

## Exactness and mutants

| run | what | outcome |
|---|---|---|
| tput `t0` | TK2 1, 9 production records, 3,171 words | PASS, 0 mismatches |
| tput `t1` | MUT_TK2 1 (ascending order ranks scores) | FAIL (34 mismatches), as required |
| tput `t2` | MUT_TK2 3 (merge skips lane 3) | FAIL (20 mismatches), as required |
| CF-TOPK `k0` / `k1` | TK2 1 over the default reader / PREF 1 + TOPKW 1 + TWIW 8 | PASS 9 / 9 each |
| CF-TOPK `k0m1` / `k0m2` / `k0m3` | MUT_TK2 1 / 2 (ties to the higher index) / 3 | FAIL each, as required |
| directed random `r0` | 96 vectors of `tools/hgi_unit_tput/idx_tk2_vectors.py`, TK2 1 | PASS: 90 exact, 6 NaN faults |
| directed random `r2` | same, MUT_TK2 2 | FAIL (45 of 90 exact), as required |

Gates: `IDX_TPUT GATE PASS (m0/p0/w0/x0/t0 PASS, m1/p1/p2/w1/x1/t1/t2 FAIL)`, `IDX_UNIT_CF GATE PASS`; the existing
variants give their committed cycle counts (m0 1,212, p0 453).
In CF-TOPK the k <= 8 vectors (k6 n384 asc, k1 m3, k2 m2, k8 m2, k8 asc, NaN) run on tk2; k 512 n 2,048 and the two
order-fault vectors (k 512 asc, k 9 asc) run on the old path.
The directed-random vectors cover what the others do not: unaligned A / O / R bases, rows sharing a sector, outputs
spanning two sectors, n < 8, heavy ties, -0 / +0, +-inf, denormals, R present / absent, both orders, m 1..3.
The tie mutant (MUT_TK2 2) is not in the tput gate: the production vectors cannot see it (in the tie record all five
tied values are inside the top 6 and order = 1 hides their order). CF-TOPK and the random vectors kill it.

## Size and lint

- yosys 0.9 (`/usr/bin/yosys`, `synth -flatten`, generic cells), `ot_hgi_idx_tk2` alone: **4,259 flops** at the
  default IDW 20 (30,448 cells); 3,827 flops at IDW 12 (27,109 cells). No SRAM. (The spec estimate was ~3k at id 12.)
- verilator 5.050 `--lint-only` with the repo's flags: no warning in `ot_hgi_idx_tk2.sv`. `-Wall` on the unit with
  TK2 1: the same warning classes as the unit at the parent commit (+1 DECLFILENAME, +3 UNUSEDSIGNAL).

## Open (not done, stated as such)

- k > 8 or a non-unit inner stride does not run on tk2; such records keep the engine selected by PREF / TOPKW.
- No synthesis at 833 ps and no P&R of `ot_hgi_idx_tk2`: the timing of the compare + shift-insert stage, the rank
  stage (id compare + 3-bit count) and the 4:1 FIFO-head select + key stage is unmeasured.
- TK2 is opt-in; no die top sets it yet.
- O / R inner stride is taken as 1, as in the existing unit.
- Observation, not root-caused: with TK2 0 (default reader + reference engine) the unit never returns on the records
  that follow a NaN-faulted record in the directed-random list (`logs/rand_ref_tk2off_truncated.log`; the 15 vectors
  before the first NaN are exact). CF-TOPK has its NaN vector last, so the committed gate does not see this.

## Commands (repo root; `VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator`)

```
python3 tools/hgi_unit_tput/idx_vectors.py --out $S/vec
bash tools/hgi_unit_tput/run_idx.sh $S/vec $S/tput            # t0 / t1 / t2 + the existing variants
bash tools/hgi_unit_tput/run_idx_unit_cf.sh $S/cf             # k0 / k1 / k0m1 / k0m2 / k0m3 + the existing variants
python3 tools/hgi_unit_tput/idx_tk2_vectors.py $S/rvec 96     # then tb_hgi_idx_unit -GTK2=1 [-GMUT_TK2=2] +DIR=$S/rvec
yosys -p "read_verilog -sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv; synth -flatten -top ot_hgi_idx_tk2; stat"
```
