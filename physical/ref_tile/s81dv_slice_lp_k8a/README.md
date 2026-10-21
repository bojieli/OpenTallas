# s81dv_slice_lp_k8a -- DIAGNOSTIC landed slice parent (ot_s81sl_slice), DRIVE-S81-SLICEP 10-20
CRITICAL prefix s81dv_slice: gate PNGs -> COORD-REVIEW-QUEUE; never REVIEW.json / submit. Stand-ins (STANDIN_NOT_A_VIEW): vp x5, ve x5, xg (xg5 size).
Generator tools/s81_slice/pl_slice/mk_slicep.py; top ot_s81sl_slice_c1x_k8_lp (lp.py tools/s81_slice/pl_slice/c1x_k8.json, audit PASS,
8 landings D4/E2, 38,596 landing + 1,410 reset flops, reset depth 6, leaf<->centre latency unchanged (reference schedule)).
Regions (10-20 clock rule): C (leaf 2 + centre band) / L0 / L1 / L3 / L4, one CTS root each (ck_C, ck_L*); every crossing is a landing ring.
## SAFE checklist
1 pins: lp parent ports region C; children register their own pins; reset lands via lp reset root + per-chunk forest (2 stages+).
2 reach: all C ports on the W/E faces of the C rows (no C wire across a leaf band); L0/L4 landing flight crosses one band inside E=2 (gate measures).
3 fanout: chunk-8 landings + kept enable (lepenh2 census recipe: max 32); in-gate mapped census decides.
4 depth: glue = relays / landing muxes (registered one-hot selects).
5 storage: no parent storage (landing rings are 4-slot static rings, chunked).
6 floorplan: children on the 43.2 lattice, channels 43.2 um (small row half); outline 1252.8 x 6739.2 (8.44 mm2, hard 69%); aspect 5.4:1 / 5.8:1 waived (die slice column shape).
7 clock: regional roots + landed crossings; spread <=80 TT/FF judged per region.
8 schedule: static; landed leaf<->centre +0 edges, reset +13 (PL-SLICE record), fault +3.
## Die finding
Hard children alone = 5.84 mm2 > die slot 950 x 4600 (4.37 mm2) -> die plan must re-slot the slice (posted COORD-REVIEW-QUEUE).
