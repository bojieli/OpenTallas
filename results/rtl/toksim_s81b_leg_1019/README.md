# TOKSIM-S81B/LEG: the on-die leg of every S81 cross-die crossing, measured on the MU release die (10-19)

**PASS, measured-release-RTL, bit-exact.** Per crossing (both ends, farthest slice) the leg is **128 to 140 cycles**,
depending on the circuit. The price was 134. With the worst circuit (140) on every crossing, the token grows by
+2,262 cycles AR (377 crossings) and +2,418 cycles MTP (403 crossings).

## What was priced

The xdie co-sim (`tb_xdie_s81_2`, results/rtl/xdie_s81_1019) starts and ends at the end slice ring stop, on its inward
port. It already contains the 8 lk lane legs: 3 `dsfd_dvrlyh` relays plus a `dsfd_dvland` k 3 landing on every lane.
The path between the end slice and the slice that owns the data was priced in `tools/xdie_s81_2/record.py` as
`ONDIE = 134` = 2 x 67 an end. Each end was 29 stations of 405 um (14.5 cycles), plus 7 landed ring links (1 + E 4.5 = 38.5),
plus 7 ring stops x 2 edges (14). This term appears in every xdie term of `results/arch/token_path_1018/ds_rom.json`
(`grade priced`, `part "on-die leg farthest slice <-> end slice ..."`): `substage_hop0/1`, `unplaced_hops`,
`a/router/rows_allgather`, `out/combine_allreduce` (2 crossings, 268), `idx.topk_merge`, `hop`, `argmax_merge`.

## Vehicle

`rtl/test/toksim_s81b_leg/tb_leg_s81.sv` + `leg_chain_gen.sv`. `tools/toksim_s81b_leg/gen_chain.py` generates the chain
from the GEN mu4c `die.v` (sha256 ce6b7913..., ot-epyc7 `s81-bind-mu4c/bind_main/bind/die.v`), for both tiers:

- 16 `ot_s81sl_rstop` (die sids). In `ot_s81sl_slice` the slice ri/ro pins go straight to `ot_s81sl_xg u_r`, and `ck_line = clk`.
- 112 ring links `xr{E,W}_<c><S|N>_l<0..3>`, each exactly as in die.v: the hop-0 ICG on the source slice line clock,
  **7** `dsfd_dvrlyh_276_{WE,EW}` half-cycle relays, and `dsfd_dvland_276` with die.v's strap k (4 or 5).
- The ICGx4 standard cell uses its behavioural latch + AND model (as in the bound die's cells_used.v).
- The RTL files are blob-identical with `19bf4121e` (and `ceaed19c4`); see `RELEASE_BLOBS.txt`. Verilator is 5.050.
- The die's regions run on one clock with R0 = G (E = K), the same as tb_xdie_s81_2.

Flows: OUT = farthest source slice -> end slice (inject on the control-plane line, `ci_b`). IN = end slice -> farthest
owning slice (beat from the end stop's outer port, as the lep delivers it). Both run W-bound and E-bound, on both tiers.

Payload: every xdie term's production beats a peer (1 / 3 / 8 / 13 / 32 / 40 / 128 / 132 / 321 beats of 128 B) at the
farthest slice, plus a column sweep (1..7 links, 16 beats each). That is 128 windows and 6,320 beats in total.

Cycle definitions match tb_xdie_s81_2, so the parts add up with no overlap and no gap:

- OUT runs from the edge at which the source stop samples `ci_b` to the edge at which the end stop samples `ri`. The latter is the xdie issue edge.
- IN runs from the edge at which the end stop loads its inward `ro` to the edge at which the owning stop loads `dl_e`/`dl_w`. The former is the xdie landing edge.

## Result (`l1/run.log.gz`, `l1/leg.json`)

`PASS leg_s81: 6320 beats crossed the on-die leg bit-exact, in order, no ring-stop or landing fault`. Each beat was checked
as a full 1,104-bit compare, including the hops field as compiled. Every beat of every window has the same latency.
The leg sustains 1 beat a cycle with no wait, so it adds latency only, whatever the payload. Law (0 violations over 128
windows): **each ring link plus the stop it enters = k_link + 5 edges**.

| end, 7 links | S tier | N tier |
|---|---:|---:|
| OUT to W end (k 5 x7 / N 5,5,5,5,5,5,4) | 70 | 69 |
| OUT to E end (S k 4,5,4,5,4,5,4 / N 4,4,4,5,4,4,4) | 66 | 64 |
| IN from W end (E-bound) | 66 | 64 |
| IN from E end (W-bound) | 70 | 69 |

| circuit (tb_xdie_s81_2 pair A) | per crossing |
|---|---:|
| S: d.ES -> (d+1).WS (out_E + in_E) | 132 |
| S: (d+1).WS -> d.ES (out_W + in_W) | **140** |
| N: d.EN -> (d+2).WN | 128 |
| N: (d+2).WN -> d.EN | 138 |

The price under-counted the stations (the die has 7 relay stations on each ring link, so 49 per 7 links, not 29). It
over-counted the landings and stops. The net is +6 cycles a crossing on the worst circuit and -6 on the best.

## Mutants (fail witnesses)

- `mut_rly/` `+define+OT_S81_RLY_MUT` (relay bit 0 inverted): **FAIL** (`mismatches 790`, valid stuck: `extra`).
- `mut_landsel/` `+define+OT_S81_LAND_MUT_SEL` (landing reads one slot early): the bench verdict PASSes (bits exact, no
  epoch fault in the zero-delay sim, the same weakness tb_xdie_s81_2 found). The **law check FAILs**: `parse_leg.py`
  reports 128 law violations, 63 instead of 70 at 7 links (`law.txt`). Under the static schedule the latency is a
  compile-time constant, so the record requires bench PASS **and** law PASS.

## Not covered / notes

- Cross-tier owners (V rung, `tv*` links) are not on the priced path and are not measured here.
- Off-critical xdie slots (exposed 0) stay 0. The `unplaced_hops` slot (62 x 134 = 8,308) scales by 140/134.
- No RTL change. Owed edge NOT folded: LEAD2-S81 INBOX [SLICE 16:39] rstop RELAY=1 successor (claude/s81-xgr-1019, not in mu4c) adds +1 edge per stop = +7 an end, +14 a crossing (worst 154) once bound.

Reproduce: `gen_leg.py --out golden`; stage the 6 RTL files + bench (`RELEASE_BLOBS.txt`); `ot-run --mem 16 -- bash
tools/toksim_s81b_leg/run_leg.sh out_l1`; `parse_leg.py`; `record_leg.py`.
