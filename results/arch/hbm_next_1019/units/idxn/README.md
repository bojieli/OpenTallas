# HBM-NEXT-UNITS-IDXN: IDX.INDEX with N queries over ONE key stream (2026-10-19)

This is the follow-up to `units/idx/README.md`. That design was bit-exact, but each added row cost **953** cycles against a price of 152. The cause was that every row re-read the keys and ran the whole top-512 selection on the single selector.

This lane redesigns IDX.INDEX so that the keys are read once per record and the rows run as a static pipeline:

- The rows are pipelined.
- The keys come from HBM **once per record**.
- The selectors are time-shared.
- Collisions and hazards raise a fault. There is no ready, credit or backpressure anywhere.

All benches ran on the fleet (Verilator 5.050, ot-epyc5, bundle 58daf6366). The logs are committed in `index/`. An independent replicate of the whole index bench (same bundle, ot-epyc7, 10-19 03:11) reproduced every result: N = 1..6 PASS with the same edges, all 7 mutants FAIL, and both d4g equivalences IDENTICAL (`index/verdict_index_r2_epyc7.txt`).

## Verdict

**PASS at a measured row II of 232 per added row.** The target was 307 or less; the price is 152.

- **Bit-exact for N = 1..6.** Each row checks all 10,928 scores and its 512-record top set against its own oracle, and every row's timeline matches the compiled one.
- **One key stream:** the bench answers only the DUT's `key_slot` edges and requires exactly 171 live key-line deliveries per record. The runs scored 171 / 342 / ... / 1,026 beats from those 171 deliveries.

### Measured record length

| N | last TX edge (record cycles) | d4g / old hnx fork | price (658.9 + 152 (N-1)) |
|---|---|---|---|
| 1 | 1,297 | 1,393 | 658.9 |
| 2 | 1,529 | 2,346 | 810.9 |
| 3 | 1,761 | 3,299 | 962.9 |
| 4 | **1,993** | 4,252 | 1,114.9 |
| 5 | 2,225 | - | 1,266.9 |
| 6 | **2,457** | - | 1,418.9 |

**Added row = 232.0 cycles, exactly the compiled pitch, at every N.**

The fixed frame went from 1,397 to 1,301. The emit-to-key gap fell from 100 to 4; the scorer needs at least 3 (engine settle). The remaining miss against the price is mostly the pre-existing d4g frame (1,297 against 658.9).

**For CMTP re-timing:** IDX.INDEX = 1,297 + 232 (N - 1) cycles, in place of 1,397 + 953 (N - 1).

### N = 1 equivalence with d4g

- **d4g programme on the IDXN unit** (`n1_d4gprog`): identical to the d4g `ot_hbm_idx_scheduled_static` on all 700 score and TX lines, at every edge.
- **Row frame at N = 1** (`n1`): the payload is identical (every score line and TX flit). Only the timing moves: everything is 96 edges earlier because of the shorter gap.

## Mechanisms (rtl/hbm_next/idxn/), each with a mutant that fails

| Mechanism | RTL | Mutant (fail witness in `index/`) |
|---|---|---|
| **Pipelined row streams.** The issuer runs K = 8 streams over ONE frame SRAM: each stream owns the read port every 8th edge and keeps a 4-row window, with rows 0..3 captured at programme load. Fields are routed per class (OPR, QEM, KEY, PRE, SEL per selector, LIN, LOUT) from the one stream that owns the class on that edge, tagged with that stream's row. Two streams in one class on one edge is a fault. | `ot_hnx_idxn_calendar.sv` | `msel`: pitch 200, so rows r and r+4 collide on a selector. Fault, plus score and TX errors (`run_msel.log`). |
| **Key replay buffer, per scorer.** Row 0 scores the live HBM key lines and the buffer captures them: 8,704 b x 171 beats in 34 macros of 256x256. Rows 1 and up replay them. The PRE class reads the buffer one edge before each replay beat, and the tag is regenerated. It faults on a replay of a beat that was never captured, or a replay without its PRE read. | `ot_hnx_idxn_keybuf.sv` | `m21`: the read happens on the replay edge (no lookahead). Fault, and 37,191 score errors. |
| **Time-shared selectors.** There are S = 4 d4g selectors, unchanged, all on the one score bus. Row r uses selector r mod 4, which covers both N = 4 and N = 6. The selector clears move to just before ingest, so a selector is busy for 830 of every 4 x 232 edges. Two selectors delivering to the link on one edge is a fault. | `ot_hnx_idxn_parent.sv` | `m22`: every row goes to selector 0. Fault, and 4,816 TX errors. |
| **Row-slot link.** The 8 existing 64x512 banks now hold 8 row slots, so row r+1 is ingested while row r is still being emitted. It faults on a clear of a slot that is still full, an emit from a slot that is not full, or an ingest into a full slot. | `ot_hnx_idxn_link.sv` | `m23`: slots are dropped. Fault at edge 1,221, when row 1's clear lands on row 0's unemitted slot. |
| **Query-reload hazard check.** The hslices hold ONE query and read the head weight 28 edges after each key. The next row's head emits must therefore come at least G2 = 23 issue slots after the last key; this was derived analytically. The calendar faults when the gap is smaller than G2MIN = 23. | calendar (`since_key`) | `mii1`: pitch 231 gives a gap of 22. Row 0's last 25 scores are corrupted and the unit faults, which confirms the bound is exact. `mg2`: a frame compiled with G2 = 8 gives 389 score errors and a fault. |
| Row strides (from the IDX fork) | `ot_hnx_idx_vm_query_static` | `mstride`: strides set to 0, which gives 12,397 score errors. |

The binding unit is the scorer array: 32 head emits + 5 gap + 171 key beats + 23 reload gap ≈ 232 (the compiled II). The other units are below that:

| Unit | Edges per row |
|---|---|
| Query unit | 225 |
| Selector | 208 (830 / 4) |
| Link ingest | 175 |
| Operand reader | 157 |

### Why not "N query lanes per scorer"

The ideal of 152 needs the 1,024-hslice scorer arithmetic replicated N times, which costs several mm² at N = 4 to 6. Two cheaper alternatives were considered:

- **Time-share the scorer per beat** (N query register sets per hslice): about 1.7 to 2.9 M flops, and the II is still about 330, because all N queries must be loaded before the key pass.
- **Replay buffer (chosen):** the key bytes still come from HBM once, about 0.49 mm² of macro on the d4g die, and the II is 232. It is independent of N up to 8 rows in flight.

## Area estimate (pre-layout synthesis, ASAP7 RVT TT; `synth/area.json`, `tools/hbm_next/hnx_idxn_synth.sh`)

| Item | Cells (µm²) | Flops | Macros | Macro (µm²) |
|---|---|---|---|---|
| One d4g selector (each of the 3 added) | 25,200 | 20,605 | 12 x 256x256 | 85,100 |
| Key replay buffer (one per scorer) | 1,670 | 181 | 34 x 256x256 | 241,118 |
| IDXN issuer (vs d4g issuer 65 µm², 1 macro) | 6,858 | 10,133 | 1 x 256x256 | 7,092 |
| Row-slot link | not run (synthesis did not finish) | +~11 | none new (unused rows of the existing banks) | 0 |

The die adder for DIE is based on the d4g quad IDX: 8 engines, 2 x 8,792 b key lines a beat, so 2 replay buffers.

| Component | Adder |
|---|---|
| 3 added selectors | 0.331 mm² |
| 2 key buffers | 0.486 mm² |
| Issuer | +0.007 mm² |
| **Total** | **about 0.82 mm²** of cell plus macro area (about 1.2 mm² of outline at roughly 70% fill) |

The full-die bench form (N_Q = 4, four scorers) would need four key buffers instead (0.97 mm²).

## Files

- **RTL:** `rtl/hbm_next/idxn/{ot_hnx_idxn_scheduled,ot_hnx_idxn_calendar,ot_hnx_idxn_parent,ot_hnx_idxn_keybuf,ot_hnx_idxn_link}.sv`. The scorers, query unit and selectors are the unchanged d4g masters; the operand reader is the IDX fork.
- **Bench:** `rtl/hbm_next/idxn/tb/tb_hnx_idxn_rows.sv`, `tools/hbm_next/hnx_idxn_bench.sh OUT {lint|index}`. The two hierarchical builds run one after the other, about 29 GB RSS each; declare `--mem 96`. Two builds in parallel were OOM-killed at 80 GB.
- **Frame compiler:** `tools/hbm_next/hnx_idxn_calendar.py OUT [--gap 4 --g2 23 --sel 4 --streams 8]`.

## Next

1. **CMTP:** re-time IDX.INDEX at 1,297 + 232 (N - 1), and price the MTP and 4-user delta against 1,397 + 953 (N - 1).
2. **DIE:** about 0.82 mm² (about 1.2 mm² of outline) of IDX additions. Place the key buffers beside the quadrant scorers (quad form: half a buffer per quadrant scorer quarter) and the 3 selectors beside idx_sel.
3. **Gates:** re-gate the touched tiles under hnx_ names: the quadrant key buffer, the idx_link with slots, the issuer, and the replicated selector (unchanged view, 3 more instances). Porting to the quad soft composition (`ot_hbm_idx_client_static_quad`) is mechanical: the key buffer sits on each quarter's 4 PC key lines, and the root takes the selectors and link.
4. **Optional, toward the 152 ideal:** a two-query hslice (double-buffered query, +560 flops a slice) would remove the 23-slot reload gap and overlap the 32 emits, for an II of about 180. Its price is about 0.6 M flops.
