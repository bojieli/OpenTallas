# S81 KVLEAF master geometry review

Viewed exact images on 2026-11-23. The source checkpoints and their render log hashes stay with each lane output.

- Intel1 `s81-kvleaf-t2-arch/master_r2/runs/qnh/layout` and `kvr/layout` show actual 3_place. QNH is 114.5 µm square, 624 pins, fill 0.467. KVR is 140.4 µm square, 261 pins, fill 0.501. Both have a clear PDN and edge-local port registers, no macro walls, and a few local dense bins. PASS for repaired TT/FF CTS, with a fresh result review before GRT.
- Intel1 `runs/kvq_floorplan_1433`, exact 2_floorplan SHA6f1ae2a1598b. Two central stacked SRAMs in the 259.2 µm square leave both side channels open and their PDN crosses the central corridor. PASS for placement after restoring the tracked hold-protection hook. Review post-place pin density and channels before CTS or route.
- E9 `master_drafts_codex/reshape_r2/kvtch_floorplan_1433`, exact 2_floorplan SHAe1dd070e5627. The 702×25.92 µm bit-banded strip shows clean N/S edge separation and continuous PG crossings. PASS for placement with the proven `o_fo` low tie. Review actual routed reach, clock distribution and density separately after it places.
- E9 `master_drafts_codex/route_r2/{cnw,cpl,ikr,ikw,kvpc,kvec}/geometry_1436` shows six exact routed final geometries. All six inherited detailed-route reports have zero markers. PDN crossings and edge pin ordering are clear; CNW and IKW retain dense thin north pin strips with a largely open core. CPL and IKR show separated clusters with no macro obstruction. KVPC spreads uniformly across the rectangle. KVEC shows interleaved banks and localized hot cells without a wall. PASS for TT/FF verdict on the exact routed checkpoints.

## Recovered post-CTS / placed checkpoints

- QNH and KVR exact corrected CTS views on intel1 under `runs/{qnh,kvr}_mm_1433/geometry_1445` were viewed. QNH has isolated hot central and bottom-edge bins. KVR has a north-west concentration, with wide lower and east routing space and no macro wall. PDN stripes and pin faces remain continuous. CTS has zero internal hold violators after repair, +10.00 ps at the repair scope. Direct post-corner aggregate includes boundary paths. PASS-COND for global routing only, use actual congestion and boundary evidence from GRT before proceeding further.
- E9 KVT horizontal exact 3_place SHA6efd4b9f111c viewed from `reshape_r2/kvtch_place_1437/geometry_1445`. N/S bit-bands are intact, fill is approximately 0.34, and the long centre strip is spread with clear PDN access. The centre clock entry is between the two halves. PASS for isolated TT/FF CTS. Route remains held.

## Post-seat hold ECO review 15:05 PST

Viewed the exact E9 seated checkpoint floorplans and density images in `master_drafts_codex/route_r2/<type>/hold_eco_1500/review`. CNW SHA a9831b9a2d8c has two new internal HB4 cells, CPL 2c23c845520f and IKR 9c11486093324 have one each, and IKW ef974ee40a58 has 32. The CNW and IKW north pin edge is dense, with clear interior and continuous PG tracks. CPL and IKR keep separate logic islands and open channels. All four have no macro obstructions, present the original face pin counts and show continuous PDN. PASS for isolated incremental routing of the named HB4 nets. Use fresh extraction and corner checks before promotion.

## KVQ placement, QNH/KVR global route and horizontal KVT CTS 15:09 PST

Viewed exact floorplan and density images under each `review_1502` directory.

- Intel1 `runs/kvq_place_1437` SHA fbabb4c25a3d has 2 SRAMs, 2,310 pins and 0.537 site fill. The 2 SRAMs preserve open side and middle channels, with narrow populated strips. The two bottom pin clusters remain distinct. PASS for TT/FF CTS on this checkpoint.
- Intel1 `runs/qnh_grt_1450` SHA 74b995b3f34e has 624 pins, 0.493 fill, and 23.04% aggregate GRT demand with zero overflow. Some mid/upper local density is high but shows breaks and open edge space. PASS-COND for isolated detailed route and fresh corner checking.
- Intel1 `runs/kvr_grt_1450` SHA 19895162232f has 261 pins, 0.530 fill, and 21.33% aggregate GRT demand with zero overflow. The northwest hot area is local and the south and southeast retain routing room. PASS-COND for isolated detailed route and fresh corner checking.
- E9 `cts_codex/mm/kvtch_place_1437` SHA 5b981ab8f82f has 7,127 pins, 0.386 fill and 260 PG records. The approximate 702×25.92 µm strip preserves N/S separation and clear edge approaches, continuous PG, and a centre clock entry. PASS-COND for isolated global-route capacity measurement. Setup repair left endpoints to diagnose before adopting the master.

## KVQ CTS and horizontal KVT GRT 15:27 PST

- Intel1 `runs/kvq_mm_1514/review_1518` exact CTS SHA 74a42f927cb1, 2 SRAMs, 2,310 pins and fill 0.562. Center channel and outer sides remain open, with two concentrated bottom clusters and continuous PDN. The native FF repair scoped to internal paths is +10.01 ps. Boundary FF remains −240.56 ps, visible and held. PASS-COND for isolated GRT to measure routing capacity and the boundary independently.
- E9 `reshape_r2/kvtch_grt_1510/review_1526` exact GRT SHA 0da87272a352, 7,127 pins, fill 0.386, with 18.78% aggregate demand and zero overflow. Pins remain in N/S bands, the spread cell strip is bounded on both lateral sides, and PDN access crosses the length. PASS-COND for isolated detailed route and extract, with TT/FF closure and LEC still owed.

## QNH final routed geometry 15:33 PST

Viewed intel1 QNH `runs/qnh_drt_1510/review_1531`, final ODB SHA af60d38afaaa. The 624 pin positions and continuous 42-record PDN remain visible with fill 0.493 and no hard macro wall. There are local red density bins in the lower pin band and centre, while detailed route is DRC 0 and antenna 0. PASS for exact TT/FF and netlist LEC. The final-report-only rerun corrects ASAP7 corner spelling from unsupported TT to TC after DRC-zero route and retains this routed geometry.

## CPL/CNW incremental route and KVR final geometry 15:35 PST

- E9 CPL `route_r2/cpl/hold_eco_1500/incremental/review_1533` SHA 2eb17135595e and CNW `route_r2/cnw/hold_eco_1500/incremental/review_1534` SHA e5ec00739fa5 have zero DRC markers and were visually reviewed. CPL retains clusters separated by thin open channels, 167 pins, and 64 PDN records. CNW retains its dense north pin band, open interior and 66 PDN records, with 1,655 pins. PASS for fresh extraction and TT/FF checks of these exact incremental routed ODBs.
- Intel1 KVR `runs/kvr_drt_1510/review_1534` SHA bd49d763bfe9 shows 261 pins, 52 PDN records, site fill 0.530 and concentrated northwest density with open southern approaches. Detailed route has zero DRC markers. PASS for exact TT/FF and netlist LEC.

## Horizontal KVT final geometry 15:39 PST

Viewed E9 `reshape_r2/kvtch_drt_1527/review_1538` final SHA 3999a6680ff9. Exact 7,127 pins and 260 PDN records, N/S pin bands and centre clock remain separated across the 702×25.92 µm strip. The interior bands are spread along the length, with no macro or new wall. Detailed route is DRC0. PASS for TT/FF and netlist LEC. Parent adoption and corner/LEC gates are pending.

## IKR and IKW incremental route geometry 15:41 PST

Viewed E9 `route_r2/{ikr,ikw}/hold_eco_1500/incremental/review_1540`, final IKR SHA 8d922045dbb1 and IKW SHA 93509b365df1. Both have DRC0 and preserve their port counts, continuous PG and open channels. IKR keeps concentrated logic to one side and clear lower-right space. IKW retains a narrow dense north pin band with an open lower interior. PASS for exact fresh extraction and TT/FF verification.
