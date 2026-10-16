# SM↔HBM hops: layout options (OWNER 07:30, H-DIE-V790 10-16)

**Question.** In the d3 case, 107 of the 491 SM_HBM relay hops are longer than 600 µm, up to 8.6 mm. The cause is that
chains from the service groups at the PHY/PC row to SMs in the far rows cross SM rows (and the band). Can a re-pack fix
this, and at what DS cost?

**Base.** The v5 geometry *before* the rp4c carve frame: core4_sfu2_b3624 with SM 7,200 × 1,800 and edge 100, 828.3
mm². The final carve-frame v5 (830.2 mm²) has the same rows; its base hop numbers are in
`../core4_sfu2_b3624/README.md`.

## Method
- **Hops** (`tools/hbm_die_v15/sm_hbm_hops_1016.py`):
  - Each SM_HBM chain is routed pin-to-pin in the v6_eval lane model at 480 µm reach.
  - Relays are placed greedily, only outside hard blocks. A hard run longer than the reach forces a long hop.
  - `--free sm_` makes SM frames relay-legal, standing in for the 40-µm carve.
- **Cut and stages:** `v6_eval.py`. New lane-mode options:
  - `homescls=SM_HBM` keeps SM_HBM lanes off routes with no relay homes;
  - `feed=` sets which blocks are relay-legal;
  - `--face` forces the HBM port face.
- **DS cost proxy** (`tools/hbm_die_v15/layout_ds_cost_1016.py`):
  - It uses H-MTP2's ds_relay_latency method: crossings × per-class stage delta, re-run on the same S2 schedule. Cases
    are AR and the 3,500 MTP design, nominal.
  - One fix: the parallel SM legs are charged with the change of max(SM_HBM, SM_X) absolute.
  - Base cycles: AR 596,948.7 and MTP_design as `ds_cost.json`.

## Results (`comparison.json`, `ds_cost.json`)

| Option | Die mm² | Cut V/H (lines > 0.60) | SM_HBM hops > 600 / max (µm) | SM_HBM stages | SM_OUT | HBM_VM | COLL_EP | DS AR % | DS MTP % |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| base (v5 as adopted) | 828.3 | 0.535 / 0.577 (0) | 80 / 4,367 | 12.03 | 10.56 | 26.06 | 14.44 | 0 | 0 |
| base, SM_HBM on relay-legal routes | 828.3 | 0.633 / 0.559 (3) | 74 / 1,804 | 12.22 | 10.56 | 26.06 | 14.44 | −0.05 | −0.09 |
| **(1) SM feedthrough carve** | 828.3 | 0.530 / 0.559 (0) | **10 / 1,416** | 12.47 | 10.53 | 26.03 | 14.44 | −0.16 | −0.21 |
| (2) svg next to its SM | 828.3 | 0.518 / 0.579 (0) | 79 / 4,367 | 11.72 | 10.16 | 26.56 | 14.44 | +0.12 (lane noise) | +0.23 (lane noise) |
| (3) SM columns 1,785 × 7,260 over the PC row, 420-µm channel | 854.7 | 0.587 / 0.499 (0) | **0 / 480** | **2.12** | 15.91 | 35.50 | 22.89 | **−0.92** | **−1.06** |
| (3b) SM columns, 20-µm channel | 828.3 | 0.603 / 0.485 (1) | 12 / 1,039 | 1.94 | 15.94 | 34.72 | 22.11 | −0.77 | −0.87 |
| (4) SM columns above a band next to the PC row | 834.9 | 1.071 / 0.649 (159) | 11 / 2,828 | 10.72 | 13.97 | 20.19 | 8.56 | −1.18 | −1.57 |

## Findings and ranking (by the DS proxy, then hops)
1. **(1) SM feedthrough carve is recommended.**
   - Stage count is unchanged by construction. Hops over 600 µm drop from 80 to 10.
   - The 10 that remain (max 1.42 mm) are chains to the rows beyond the band that cross band blocks (sfucore 3,580 tall,
     SU slices). They need a band relay column or channel at those x, the same carve idea applied to the band.
   - The −0.16 % comes from the lanes having to detour to relay-legal routes. It is not intrinsic.
   - The carve is now in the v5 frame: 7,228.8 × 1,807.2.
2. **(2) svg next to its SM is not recommended.**
   - The long chain becomes svg↔vmks/ctl: 1,368 + 1,120 = 2,488 b against SM_HBM's 1,132 b, so it is 2.2× wider.
   - It has the same length and stages, and hops are unchanged (79 over 600).
   - The +0.12 % is lane-assignment noise from re-weighted bits, not a structural gain.
3. **(3) SM columns are not recommended for DS.**
   - SM_HBM collapses (12.0 → 2.1 stages, all hops ≤ 480 µm). But the SM_X leg is in parallel, so only the max-leg
     saving counts: −2.2 stages per matvec.
   - The band moves to the die centre, so the classes that pay are SM_OUT (+5.4), PC↔hub (+9.4), COLL_EP (+8.4) and
     KV_DESC (+4.2).
   - Net: DS AR −0.92 %, MTP −1.06 %, +26 mm².
   - It also needs a new H-SM 4 × 4-tile column frame, which is not built.
4. **(4) Band next to the PC row:** a cut overload of 1.07 and DS −1.2 %. Rejected.

**Conclusion.** SM↔HBM chain *length* is not where DS time goes. Under the S2 schedule the SM fetch overlaps the x load
(SM_X), and the collective/VM classes are the sensitive ones. So:
- keep the row layout;
- use the carve to make every hop ≤ 480 µm within the SM rows;
- add a band relay column (or channel) for the 10 remaining band crossings.

Not modelled: HBM_K (PHY↔PC controller) is held fixed in all options. The PHYs stay at their package positions; their
21.6-mm centre spacing is already at the HBM-stack width.

## Reproduce
The plan variants are built from `core4_sfu2_b3624` (SM 7,200 × 1,800, edge 100):
- `--sm-columns CH [--band-low]` adds the column options in `compact_plan.py`;
- evaluation is `v6_eval.py ... --lanes-mode legs[,homescls=SM_HBM,feed=|feed=sm_] [--face SM_HBM:sm_SW:S ...]`;
- then `sm_hbm_hops_1016.py DIR [--free sm_]` and `layout_ds_cost_1016.py base/eval.json NAME=DIR/eval.json ...`.
