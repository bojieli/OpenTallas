# QC-MESH-EST-1 (2026-10-28): per-region clock mesh vs the 180-ps tap window, for QC intra-region hold

This is an estimate only (12.14b). No build and no plan change. Basis: trial14 routed arrivals and tree
(intel2 die-qc21-1028/trial14, c14_TT/FF), DIE-QC-22 README (claude/die-qc22-1028@191f31dee), DIE-QC-23 hold-buffer
bound (die-qc23-1028/hb_est23.json, W=180), QC-PG-4 power basis, and QC-CLK-MESH-2 / CLOCK-KV-R17 mesh sign-off method.
Every number is UNCHECKED: these are my own scripts and need a NUMBER-CHECK. Mesh MC: `region_mesh_mc.py`, which is a linear RC
transient using the ngspice-fitted BUFx24 Thevenin model (thev_r2: 303/230 ohm, d_int 34/27.2 ps) and R6 shielded 4W M8/M9 RC
(2.115/2.228 ohm/um, 0.188/0.194 fF/um). It uses 60 MC samples per corner with these variations: hierarchical pre-mesh tree
sigma = AOCV class A sigma_stage x sqrt(stages), driver Vt N(0,10 mV), wire N(1,5 %), and a 0.21 %/mm gradient. A deterministic
routed residual Rr (0/30/60 ps uniform spread) is added on the driver arrivals. It ran in docker ot-ngspice:r3 (2 GB) on intel2,
in scratch2/claude/qc-mesh-est-1.

## 1. Mesh per region (12.16e local form: one mesh per region, region root unchanged, CA crossings/start ports unchanged)
| | c_* A0 quad (c_E3_bf_11 = A0 region, c_W2_bn_01 = outlier) | sl_E4_su_c (glue region) |
|---|---|---|
| layer / pitch | M9 V x4 at tap columns (pitch 477/128/477), M8 H x7 at tap rows (pitch 374), 4W shielded | M9 V x4 (pitch 307), M8 H x4 (y 26/354/837/1172) |
| drivers | 28 BUFx24, one per glue-tap crossing, all in glue (edge strips, centre channel, middle row): render mesh_c_quad.png (left, VIEWED) | 16 BUFx24, all in glue: mesh_su_g16.png (VIEWED). su_16 (right panel of mesh_c_quad.png) is REJECTED because it puts 8 drivers on cores |
| pre-mesh tree | balanced H-tree from the region root, 6 stages, 13.4 mm, 56 cells | 4 stages, 5.7 mm, 30 cells |
| mesh C | 3.23 pF (115 fF/driver; EM well inside the QC-CLK-MESH-2 365-fF/driver case) | 1.69 pF |
| mesh loads | 28 glue taps (A0 core taps stay EARLY, off the pre-mesh tree: 665.8 vs 277 ps insertion) | 16 glue + 6 core taps at ~common latency (vmr x3, su8, crh x2). prog/btab stay early |

Variants that were rejected: c_* with 16 drivers had 89.6 ps TT nominal skew, because rows without a driver sit 374 um of
resistive 4W strap away from one. 8W did not fix this (76.6 ps). c_* with 8 V straps (A28v8): +54 % mesh C for 0-4 ps of gain.

## 2. Skew, OCV and insertion (TT / FF ps). Pair = max over glue pairs of |mean| + 3 sigma (signed-mesh U, 12.8e)
| region | today, trial14 routed glue spread | today, worst damage+OCV | mesh nominal skew | mesh pair U, Rr 0 | Rr 30 | Rr 60 | root->tap, today -> mesh |
|---|---|---|---|---|---|---|---|
| c_E3_bf_11 | 50.9 / 57.1 | (p50 73, p90 131 die) | 18.8 / 17.1 | 38.1 / 29.7 | 43.8 / 40.6 | 61.1 / 60.7 | 630 -> 680 TT / 564 FF |
| c_W2_bn_01 | 130.9 / 127.7 | 225.8 | same template (no snakes) | 38.1 / 29.7 | 43.8 / 40.6 | 61.1 / 60.7 | 707 -> 680 TT |
| sl_E4_su_c | 93.7 / 83.7 | real view -100.5 FF (vmr->t7) | 33.7 / 31.0 | 45.0 / 41.2 | 49.4 / 47.4 | 56.8 / 55.2 | 382 -> 475 TT / 394 FF |

- Below the mesh: glue taps sit on mesh nodes (0 die stages), so AOCV below the load is about 0. Above the mesh it is replaced by
  the signed-mesh U (CPPR at 'm').
- Key finding: with 4W straps at 300-480 um pitch, a 60-ps pre-mesh driver residual still adds 12-31 ps to the pair U
  (the mesh passes about 20-50 % of the residual spread). The mesh fixes snake outliers and gives OCV credit. It does not fix a badly routed
  pre-mesh tree.
- Glue <-> A0 core pairs: the core tap must be ~389 ps early, so it hangs off the pre-mesh tree, not the mesh. These pairs keep
  an unshared branch. Estimate: early-branch routed residual about +-30, plus mesh skew about 20, plus AOCV 3·sqrt(sigma6²+sigma2²)
  about 17 → **W_core 60-90 ps** (analytic).

## 3. Hold buffers (DIE-QC-23 bound method, same bits, HB4 44.6 ps FF, 0.1021 um2)
k per class: in = seam (seam-sender 155) unchanged, k 5. hop = k(W_g-8). core = k(W_c+15). out = 1.
| form | k in/hop/core/out | HB4 cells | area | c_W2_bn_01 | c_E3_bf_11 | sl_E4_su_c |
|---|---|---|---|---|---|---|
| W180 window (DIE-QC-23) | 5/4/5/1 | 26.41 M | 2.70 mm2 | 110,284 | 71,208 | 115,312 |
| mesh, W_g 35 / W_c 60 | 5/1/2/1 | 13.96 M (-47 %) | 1.43 mm2 | 46,900 | 34,044 | 62,116 |
| mesh, W_g 60 / W_c 90 (Rr 60) | 5/2/3/1 | 18.11 M (-31 %) | 1.85 mm2 | 68,028 | 46,432 | 79,848 |
The seam `in` class (1.277 M bits x 5 = 6.39 M cells) is untouched by any intra-region clock form. It is 24 % of today's bound
and 35-46 % of the mesh bound.

## 4. Power, area, tracks
- Clock power, per region (C·V²·f, 0.7 V, 1.2 GHz, 0.19 fF/um, BUFx24 7.7 uW per cell from the ASAP7 lib: 2x2.6 fJ internal +
  2.35 fF). Today: c_E3 2.7 mW, c_W2 4.0 mW, su_c 1.9 mW. Mesh form: c_* 4.05 mW (mesh 1.90 + tree 1.50 + 84 cells 0.65),
  su_c 1.96 mW. Delta: about +1 mW per c region → die about +0.2 W.
- Share of power: about 0.19 % of a c_* region (about 2.17 W token average: QC-PG-4 A0 floor 0.436 W + 9.6 % busy duty at
  0.768 W per tile, plus 1.11 mm2 glue at 0.27 W/mm2). The delta is +0.06 % of the region. Die is about 470 W token average
  without ICG → +0.04 %; about 172 W with ICG → +0.12 %.
- Hold-buffer power, on the measured su8 data activity of 0.0231 toggles/cycle at about 0.44 fJ per transition: W180 0.32 W vs
  mesh 0.17-0.22 W. At a 0.1 toggle bound: 1.39 vs 0.74-0.96 W. Leakage is 1.0 vs 0.6-0.7 mW. **Net power is about neutral**
  (-0.4 .. +0.1 W).
- Area: hold buffers save 0.85-1.27 mm2. Mesh drivers are negligible.
- Tracks, c_*: M9 4 straps x ~8 tracks of 15,450 (0.2 %), M8 7 x 8 of 32,725 (0.17 %). In-region clock wire is about 30 mm
  (mesh + tree) vs 14.5-23.2 mm today. The straps fit in the 3.4-um gaps of the 0.48/8.64 M8/M9 PG (cut_avail 0.6).
- Layer: **M8/M9 only.** §12.1a gives M6/M7 to partitions/cores, and c_* types already give 40 % of M4-M7 to feedthroughs.
  §12.1b puts the regional mesh on M8/M9 NDR. A kit-internal M6/M7 mesh would need ORFS/TritonCTS to build a mesh, and it
  cannot.

## 5. Tool support (OpenROAD) and how we would model the mesh
TritonCTS builds trees only. OpenSTA does not time a multi-driver mesh net correctly: each driver arc is evaluated on its own,
with no superposition of parallel drivers. The working path already exists from KV R15-R23 and QC 10-26:
1. Our tool pre-routes the mesh as a clock special net (die_clock_mesh / explicit_clock_mesh). A **per-region mode is new code**.
2. OpenRCX extracts it, using the qualified mixed-width rules.
3. Sign-off is a linear RC + ngspice-fitted Thevenin MC (qc_clk_mesh2 solve / kv_r17 mesh_mc17; <= 0.6-0.8 ps vs ngspice on KV
   windows), plus an ngspice window per mesh template. One region is 300-460 nodes, so it takes minutes.
4. Die STA uses die_sta_related `--mesh-signoff`: taps are re-referenced to 'm', AOCV is charged only below the load, and the
   per-pair U is added. This was NUMBER-CHECKED on KV R17/R19.
Kits below the mesh keep their own OpenROAD CTS. Early A0/prog/btab taps need an off-mesh pre-mesh-tree branch in the
per-region mode.

## 6. Comparison
| | 180-ps window + hold buffers (DIE-QC-23) | per-region mesh |
|---|---|---|
| hold closure confidence | What-if W180: -45.8 OCV left (62 pairs, 42 in c_W2_bn_01). It needs the snake cap/split. Tap arrivals move with each re-route. | Glue pairs bounded at 38-61 by construction and insensitive to snakes. Core-early pairs still about 60-90. Each template still needs a signed variation sim. |
| power | HB 0.32 W at measured activity | clock +0.2 W, HB -0.1..-0.15 W → about neutral |
| area | 2.70 mm2 HB4 (bound) | 1.43-1.85 mm2 |
| schedule risk | Low: plan keys + kit regen + repair. trial15/16 are already in flight. | Medium-high: new per-region mesh mode, early-tap branches, mesh DRC (QC R25 Min-Step class), 204 regions, about 3 templates to sign. 12.15d ranks the mesh 3rd. |
| tool support | Native: kit SDC + repair_timing -hold | Pre-route + RCX + custom MC sign-off + --mesh-signoff. Proven on KV, not native in OpenROAD CTS/STA. |

## 7. Recommendation
**DEFAULT: no change.** Keep the DIE-QC-23 window path: W180 + seam_hold + HB4 + snake cap/split for c_W2_bn_01-class legs.

The mesh is not a fundamental fix at QC region scale, for three reasons:
- the resistive 4W straps still pass 20-50 % of the pre-mesh routed residual;
- the two largest hold classes do not change: the seam inputs and the early A0 core taps;
- it saves 31-47 % of the hold buffers at roughly equal power, in exchange for a new flow path.

Switch to a pilot only if trial15/16 fail on the window, meaning any one of:
- intra FF hold incl. OCV < 0 after the snake cap at W180;
- HB4 > 5 % of the area of any partition;
- glue tap arrivals move > ~30 ps between trial15 and trial16 (the window is not stable).

The pilot would be one c_* A28 template: ngspice window sign-off + a 12.15e DRT trial of one region, before any plan event.
