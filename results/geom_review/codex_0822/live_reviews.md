# Independent live geometry reviews 2026-10-29 08:42 PDT

## HEAD-FTFACE-0822

Personally viewed codex/head-kits-0822@ee6fe6a10
results/geom_review/head_ftface_0822/plan.png. Nine pure-FT types keep bus
endpoints on abutting faces, ordered stations extend to output faces, no macros.
Reset/START endpoints now have local taps. PASS-COND for hk5 plan geometry
and one diagnostic st_str placement/CTS under existing parent/source/flow
conditions. Changed hk6 hd_st_n4 width1140.48 needs its own updated image
(the viewed image shows1442.88); other eight unchanged. No production route
or source/signoff qualification. HEAD kits owner notified.

## KV-PHY-MODELED-0822

Personally viewed codex/kv-kits-0822
results/kv_phy_wrapper_0822/fit/geometry.png. E pinstripe puts wide native
buses beside E boundary; analog reserve preserves full gross window and
carved utility corridors/island holes. Independent data_legs.json check:
2500 unique same-y M4/M6 legs, max34.56um. G1 PASS-COND for MODELED interface
proposal. Coreclock354.24/reset354.28,56.16 fit405 budget as modeled. Before
wrapper P&R materialize analog M1-M3 OBS, utility holes, PG keepouts and
separate PHY supply access in actual LEF/ODB; current event27f bind must
retain modeled forward-clock group/latency semantics and report actual local
clock duty/FFhold. Upper-layer permeability remains a licensed-PHY modeling
assumption; no silicon/signoff claim. KV kits owner notified.

## PROG-SPREAD-0825

Personally viewed codex/qc-fix-0825
results/codex_qc_fix_0825/prog_spread_full.png and prog_corner.png. Moving376
comb cells from congested SRAM E corner into visibly open E street addresses
pin-access pressure; capture columns/macros/clock remain. Native r2r354.73
with0>405, pinp9023.11/max27.73, ownleaf44.5 support this. E partial face
467pins/38percent at4.67perum is baseline, not added pressure. PASS-COND for
ONE >=50iteration GRT-only after usual native placement-legality0; require
GRT0 and view new guide/corner before any DRT. Preserve old47h DRTfailure.
Four legacy ft aliases were subsequently resolved by owner's existing typed
declaration to actual two buffer instances (no RTL/ODB/SDC change). No new
clock, cycle or timing claim. QC owner notified.
