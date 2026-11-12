# QC s28d: cb* bc-column spine (QC-S28-D, 11-12)

Base: plan_qc99_s28 2f0c17d5f1a3 (claude/qc-event-s28-1111@88018018ef). Deliverable: `delta_s28d.json.gz` plus `scripts/apply_s28d.py`.
s28 + delta = plan_qc99_s28d 59b3b2c97da3. The plan is not committed.

    python3 -I scripts/apply_s28d.py apply PLAN_IN PLAN_OUT delta_s28d.json.gz
    python3 -I scripts/apply_s28d.py check PLAN delta_s28d.json.gz

## Keys touched
The only key is `partition_types[T].relay_sites`. It is a NEW key on these 8 types: cbn_q11__cl49ae4555, cbn_q11__cl5cc92dfe,
cbn_q00__cl622f65d2, cbn_q00__cld7bf7197, cbn_q00__cldbcda913, cbf_q01, cbf_q01_s2 and cbf_q11. The delta holds 88,462 flop sites.
The from-value is "absent", so `apply` refuses a plan where one of these types already has relay_sites. It re-applies onto
s28a/s28b/s28c, because none of those touches relay_sites.

Nothing else changes: core positions and orients (the s22/s23 NK orients), outline, buses, pins, internal_stations,
clock, taps, reset, rings and bands are all kept.

## Why this form (visual + numbers)
- The GEOM-VIS reading of a "~40 um centre street" was a misread. The street is 146.88 um (164.16 on cbf_q11), and W/E are 86.4.
  Soft fill is about 3% of the free area. On cbn_q00__cl622f65d2 a20 GRT, the street middles are green or yellow; the hot cells sit on core pin faces and corners.
  Widening the street (to 181 um within the slot) would therefore not address the failures. QC-S28-DIEVIEW also finds that the slots are not oversized.
- The r2r and relay_collapse failures sit on the **bc broadcast column**: ring -> u_bin_<bc_i> -> xstn u_st -> d6 -> xstn u_st
  -> u_bout. None of these has a plan site, so GPL collapses them. In the placed dumps, the column max hop is 1171-1647 um, with 369-1302 bit-hops over 405
  (cbn_q11 bin_bc_i32 -> x_3_2.b_d 1461; x22 -> d6 -> x23 -> t23 tap 9 hops, max hop 558). The NK data chains are already
  spread by core_input_chain.tcl (s25).
- With the NK orients frozen, a column's taps often face away from its windows. Examples: cbn_q11 bc_i32 has its windows in the centre street and its taps on the E face,
  and bc_i22 enters on the W side with its first tap on the centre street. The spine therefore follows the taps, not one fixed street.

## The form
relay_sites (DIE-KV-59 / kit_istations rs_place_all) pin the EXISTING flops FIRM before GPL and release them to DPL. They add
+0 cycles and make no netlist change. The sites, per column:
- `u_bin_<bc_i>`;
- each station split by function: **b_q + ctl** (feeds the next d-chain or bout, and hold/cap) at the column site, and
  **t_q + hold + cap** (feeds the core tap through the FIRM u_pc_nk pipe) at the tap site. Both capture the same station input (ot_qfd_xcst);
- every d<D> stage, at equal fractions of the b_q -> last-stage geodesic.

The sites come from a minimax coordinate descent over free-space L1 geodesics (9 um macro halo) on a 4.32 grid
(`scripts/s28d_spine.py`). Each stage's bits are spread on a 40 um bar.

## Before / after (bc column, max hop um / hops > 405)
| type | column | before (placed dump, per-bit) | after (planned geodesic) |
|---|---|---|---|
| cbn_q11__cl49ae4555 | bc_i22 / bc_i32 | 1285 (901) / 1647 (1030) | 432 (3) / 404 (0) |
| cbn_q11__cl5cc92dfe | bc_i22 / bc_i32 | 1236 (1101) / 1461 (1082) | 432 (3) / 404 (0) |
| cbn_q00__cld7bf7197 | bc_i00 / bc_i10 | 1354 (997) / 1269 (1302) | 312 (0) / 389 (0) |
| cbn_q00__cl622f65d2 | bc_i00 / bc_i10 | r2r 1600 (GEOM-VIS) | 330 (0) / 475 (3) |
| cbn_q00__cldbcda913 | bc_i00 / bc_i10 | (same form as cl622) | 330 (0) / 475 (3) |
| cbf_q01 | bc_i02 / bc_i12 | 567 (369) / 1385 (400) | 238 (0) / 246 (0) |
| cbf_q01_s2 | bc_i02 / bc_i12 | (no dump; same RTL form as cbf_q01) | 194 (0) / 251 (0) |
| cbf_q11 | bc_i22 / bc_i32 | 1171 (1139) / 1429 (780) | 430 (3) / 406 (1) |

In the "after" column, "hops" counts planned stage hops (15-16 per column), not bit pairs.

**Residual over-reach (by design, listed):** the entry leg ring -> bin -> t_q -> pc runs 1.29-1.42 mm in 3 hops.
- cbn_q11 x2 and cbf_q11 bc_i22: up to 432 um (+7%). The ring band sits in the W strip and the t22 tap faces the centre street.
- cbn_q00 cl622/cldbcda913 bc_i10: up to 475 um (+17%). The hard ring child cl_bc_i10 blocks the S street under t10, and the t10 tap faces E.

All of these are below the 450 um repeater spacing except the two hard-ring types (475 um). Recommendation: route them as is (near-miss class).
If sign-off fails on that leg, the fix is +1 declared pipe on u_bin_bc_i10 for those 2 types; pin cycles are pre-approved, but this is a latency-table event for DIE-QC-99.

## Not in this delta (owners)
- Ring strips (route_supply worst region = ring on every cb type, 1.13-2.06): the LAND-RING-2 density form /
  budgets.cland_strip_density_types (QC-S28-B).
- Taps over the 1200 cap on the explicit-tap types: cbn_q00__cldbcda913 (28 taps, max 2062), cbn_q11__cl49ae4555 (28, max 1547)
  (QC-S28-DIEVIEW). They need s28 item-1 sink_bins + density re-derive (HOLD-TAP-SPLIT recipe; DIE-QC-99 composer).
- cbx_q10 x2: QC-S28-C (no core moves; the same relay_sites form applies unchanged if DIE-QC-99 extends it).

## Gates (DO_NOT_COUNT)
See evidence/gates.txt. route_supply and the explorer are identical before and after, because positions do not change and neither tool models relay_sites.

## Composition with HF-1 (QC-S28-FLOORPLAN, claude/qc-s28-floorplan-1112@c5d77381ae)
HF-1 grows cbn_q00 x3 by +34.56 H (to 2566.08). The relay_sites are absolute type coordinates, so on an HF-1 plan, regenerate
the cbn_q00 sites with `scripts/s28d_spine.py PLAN RTL_DIR PINS NAMES TYPES OUT` (about a minute) instead of applying these rows.
The other 5 types keep their outlines and apply unchanged. The cb x pitch is kept, and s28d needs no x growth.
