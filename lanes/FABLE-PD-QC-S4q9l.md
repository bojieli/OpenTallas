# FABLE-PD-QC-S4q9l: r199 review of QC plan event S4q9l (clock rows)

2026-11-16, FABLE-PD-QC-S4q9l (Fable). Read-only. MEASURED = recomputed by me on epyc2 from the files named.

## Verdict: ADOPT-OK

No split needed, no blocking number. The K re-derive (3 h 20 min die chain) that the adoption was waiting for is not needed:
the die clock inputs of S4q9c and S4q9k are identical (section 1), so it would return the same rows.

Files: L = epyc2 `/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc/treeJ/.../plan_of_record/zz_s29_qc103_s4q9l.json`
sha 50d472e1a81f; K = `zz_s29_qc103_s4q9kf.json` sha a826abb3a3fd (the fe-only form; the 15-row s4q9k c73c is withdrawn);
C = `zz_s29_qc103_s4q9c.json` sha dd47490db390; proof = epyc2 `fable-die-qc/chain/qc/s4q9c/reg/proof` tap_arrivals TT / FF
(42,256 taps each); rows = `lanes/handoff/FABLE-DIE-QC-clock-rows.json.gz`.

## 1. Transfer C -> K: exact, 0 ports changed

| item | C vs K |
|---|---|
| `clock` (spine, region_map, feed, landing_network, rows) | byte-equal |
| `partitions`, `ports`, `die`, `reset`, `budgets` | equal |
| sidecars cland_bin_sites / clock_merge / kit_pricing | same sha (53455fa4fc / f6219a3387 / eb38cf8a8c) |
| type `outline_um`, `hard_cores`, `buses`, `ft_slots`, `relay_sites` | equal on 130 / 130 types |
| type clock tap fields (`taps`, `tap_um`, `core_taps`, ...) | equal on 130 / 130; only additions: `landing_local_resets` + `reset_tree_anchor` on 6 types (reset rows) |
| clock port sets (`tap_offset.per_port_ps` keys) | 15,286 ports, 0 added, 0 removed |

What differs C -> K: `internal_stations` on 12 types (9 fe, 2 slw_su_l1, glue), 32 lane `fixed_cycles`, 96 latency fields.
None of these is a tap site, a region or a feed. Ports whose tap or feed changed: **none**.

L vs K: only `clock.tap_offset` (52 types, 4,252 ports changed, 105 added on slw_su_c__cl19bb38ef = ports that had no row),
`clock.tap_window.per_port_ps`, `clock.seam_hold.seam_ps` 110 -> 180. Everything outside `clock` is equal. L rows = the
handed rows file exactly. gen_phys `tap_offset_table` and `tap_window_port_table` (treeJ tools): 0 errors on 130 types.

## 2. Margins

Independent re-run of `tap_offset_gate` on the C proof: L rows **PASS, 84,512 checks, 0 outside**; K rows FAIL 5,014 of 84,302
(same as the lane reported).

| number | value |
|---|---|
| ports with a row | 15,391 |
| ports at 0 margin (<= 0.15 ps) | **2,607** (17 %): by construction, the extreme instance of every multi-instance port sits on the band edge |
| ports under 1 ps / under 5 ps | 2,737 / 3,597 |
| ports at the 10 ps tol floor | 12,800 (9,660 are single-instance) |
| largest tol | 129.1 ps (cbn_q01__cld9ff4c40 clk_t130); tol > 60 ps on 557 ports, all in the 14 cb types |

Seam window 180 ps: measured need 169.18 ps FF (seam related-pair late - early with CPPR, so the tap OCV is inside the need),
about 170.5 ps TT. Margin +10.8 FF, about +9 TT. Covered. The need is the same 169.2 on the S4k and S4q9c runs.
Intra kit-contract: W 79 / need 79.0, margin 0.00 by construction.

The 0-margin ports are not a failure now. They mean any re-route of the die clock moves some taps out of band; the cost is
an STA re-sign of that type, no P&R unless hold then fails.

## 3. Mean +/- half range: not present in the rows

The rows are **mid-range**, not mean: on the 4,469 multi-instance (type, port, corner) rows with range >= 20 ps, 4,469 equal
the mid-range and 63 equal the mean. So skewed instance sets are covered (0 outside, section 2). With mean +/- half range
4,343 taps on 2,321 ports would have been outside (worst 56.4 ps, cbx_q10__cl94a12200_h clk_c3, 14 instances -454.9 / mean
-396.1 / -224.5). Text error only: `clock.tap_offset.source` in L still says "mean over the type's instances".

## 4. st_a station rows of K: no conflict

K's rows are stations on the fe receiving chains (`bus:x_st_a_i`, 3 -> 6 regs); the seam face flop (launch "face flop",
from_um unchanged) is the same, so the seam pairs and the 169.18 need are unchanged. 7 of the 12 station types are among the
52 clock types; they get a new kit anyway. Of the 10 st_a types only slw_st_a_v2__cl9f076a5c is in the 52; none of the six
st_a_v1 types with the open HI_PAD / SKEW item is touched. Lanes and latency are equal K = L.

## 5. Die setup margin: no risk from the rows

The rows do not change the die clock, so TT setup stays +362.0 intra / +540.4 seam (FF +412.2 / +587.9), same in the proof
with old and new rows. Kit-level effect, priced at re-sign: tol grows on 1,361 ports, at most +12.5 ps (sle_sc_v2 clk_t36,
so at most 25 ps per pair); 358 ports shift more than 20 ps, worst 105.2 ps (slw_sc_v1__cl64543eaf__cl4590432d clk_c0).
Seam hold repair grows by 70 ps against +540 seam setup. Largest offset span 724.5 ps (cbx_q10__cl94a12200_h; it was 681.8
in K), worst growth +95.6 ps (slw_sc_v1__cl64543eaf__cl5e017c6f 135.3 -> 230.9).

## 6. Advisory (none blocks)

1. `tap_window.per_port_ps` is inert in L: all 130 types have offset rows and the offset form replaces the window table.
   316 of its entries exceed T/4 = 208.25 ps (max 357, 12 cb types); they would raise in gen_phys if a type lost its offset row.
2. Fix the `source` text (mean -> mid-range) at the next event.
3. The cb instance spread (tol to 129 ps, span to 724 ps of 833) is the real cost; FABLE-DIE-QC item 3 (one region tree per
   type) is the structural fix and removes most of the 2,607 edge ports.
4. Not checked: real-view hold (BLOCKED(kits) at the die), the 3 serdes count-align crossings (separate item), and whether
   the 52 types' kits close setup at the new offsets (their re-sign measures that).
