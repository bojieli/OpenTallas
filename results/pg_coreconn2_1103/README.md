# PG-CORECONN-2: views skipped by the default-on core_pg_connect (DIE-S81-51, 2026-11-03)

Plan: physical/die_plan/s81/plan_h2_2249.json. Table: `skipped_views.tsv`, produced by gen_phys.core_pg_landing(strict=False) over every macro-placing type that relies on the implicit default. The table has 7 views and 183 placed uses. None of them is silently open. Each falls into one of the two follow-up classes below.

## Class A: M7-top views (4 views, 180 uses). PG-CORECONN-3 follow-up

| view | uses | types | PG layers | why the tile grid cannot land it |
|---|---|---|---|---|
| cores/elem_boundary/ot_v41_rom_elem_q_qxpq_w10_gb | 104 | 26 | M1 M2 M6 M7 | M6 PG lies under the view's own detailed M7 OBS. The PG straps are on M7 (vertical, pitch 10.8 um). |
| cores/legacy/lef/ot_v41_bf_col | 56 | 26 | M7 only | No PG on M4/M5/M6. M7 straps pitch 10.8 um. |
| ref_tile/s81sl_capc5r ot_s81sl_capc5r | 16 | 16 | M7 only | Same as bf_col. |
| ref_tile/s81dvbk_sq_hq3 dsdv_bksel_q | 4 | 1 | M7 only | Same as bf_col. |

- These are routed, hardened abstracts, not the pgobs core_pg_stub stubs. pgobs@37a8f8653ad does not touch them, and they need no clip.
- Their PG is a closed M7 strap mesh. M7 is also the top layer of the tile grid: its stripes run vertically at pitch 8.64 um, offset 4.128. The macro straps are at pitch 10.8 um, so the two meshes are not aligned. Tile level therefore has no layer above M7 to via onto them, and no same-layer overlap.
- PG-CORECONN-3 (follow-up class, not in this fix): the landing must come from the parent. Either the tile abstract publishes the macro M7 PG straps as tile PG pin geometry so the die M8 grid lands on them, or the views are regenerated with an M6 PG landing that is free of M7 OBS. The skip leaves an explicit pdn.tcl comment per instance until then.

## Class B: views without PG pins (3 views, 3 uses). Regenerate with PG

| view | uses | proof |
|---|---|---|
| cores/eng/lef/dsdv_eng_rr_h0 | 1 | The LEF has no PIN VDD and no PIN VSS. |
| cores/eng/lef/dsdv_eng_rr_h1 | 1 | The LEF has no PIN VDD and no PIN VSS. |
| cores/legacy/lef/dsdv_eng_rr_e_clkm5_1101 | 1 | The LEF has no PIN VDD and no PIN VSS. |

These abstracts were written without PG pins. Regenerate each view with write_abstract_lef PG pins; nothing can land on a pin that does not exist.

## Pre-existing hard error (explicit core_pg_connect: true)

The four dsdv_slice_lep{w,e}_*_LP types raise in strict mode because physical/die_plan/s81/h2_2249/coll_{w,e}/lane.lef has no PG geometry. This is unchanged by the fix and falls in class B: regenerate lane.lef with PG pins.
