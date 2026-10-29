# QC-MESH-PILOT-1 (2026-10-28 PDT): one A0-quad region clock mesh pilot (c_E3_bf_11 template + c_W2_bn_01 outlier)

Basis: QC-MESH-EST-1 estimate (claude/qc-mesh-est-1-1028@3875bae535), plan ev_qc23pg (sha ad01d656b2b5, DIE-QC-23
claude/die-qc23-pg-1028@520b88330: M9 PG 0.672, 75-um A0 bump field), trial14 tap map. Trigger: DIE-QC-23 20:42 (c) tap
move 270.8 ps. Pilot only: die-local scripts in this folder, no shared tool changed -> default flow byte-identical.
Data: intel2:/srv/opentallas-scratch2/claude/qc-mesh-pilot-1 (tA, tA2, tA3, tB; old/ = superseded M7-leg runs).
**All numbers UNCHECKED** (own scripts) -> NUMBER-CHECK. Geometry rules CHECKED by tests (3/3) + renders VIEWED.

## Form (qc_mesh_pilot.py build)
- 32 BUFx24 mesh drivers (not 28: an equal-leg tree needs 8 leaves per column) on the 4 glue tap columns at
  ymid +-180/540/900/1260 (pitch 360 ~ tap-row pitch 374, so every row is 138-194 um from its drivers).
- Pre-mesh tree, equal legs BY CONSTRUCTION, no detour padding: R -> A x2 (middle band) -> B x4 -> P x8 (repeater) ->
  C x8 -> D x16 -> drivers; legs 311/239/360/360/360/180 um (<= 450). 76 clock cells, all in glue (edge strips,
  centre channel, middle band); none on the 4 A0 hard cores (asserted + tests).
- Mesh: M9 4W x4 (column straps) + M8 4W x7 (tap rows), each centred in a 4.32-um M8/M9 PG gap, VIA89 x28, one
  special net ck_mesh; C = 3.45-3.47 pF incl. 28 x 2.3 fF port loads.
- A0 core taps (clk_c0..3) stay OFF the mesh: equal-leg branch root -> E0 -> Q x2 -> E1 x2 -> core taps.
- Region run (OpenROAD, docker 64 GB): DEF of the partition outline, A0 cores as M1-M7 + placement blockages, M8/M9 PG
  specialnets (ev_qc23pg widths), M2-M7 blocked except pin windows (die clock on M8/M9 only, 12.1a), CK2W2S NDR, GRT
  50 it -> estimate_parasitics -global_routing -> OpenSTA arrivals TT/FF -> detailed_route + OpenRCX (pending, below).
- Sign-off path (KV/HEAD-R24): pilot_signoff.py rec -> tools/die_plan/explicit_mesh_signoff.py mc (qc_clk_mesh2 linear
  RC transient, RC_R6 4W, ngspice-fitted BUFx24 Thevenin mult 1 thev_m1.json, 60 MC samples, KV R18 sigma, 0.21 %/mm
  gradient) -> pair U per glue pair with the die_sta_related.mesh_signoff formula max(max|d|, |mu|+3sd) + gradient.

## Results on GRT-routed arrivals (summary_grt.json; TT / FF ps)
| trial | region, GRT adj | driver-input routed spread | mesh nominal skew | glue pair U max (p50) | root->mesh insertion |
|---|---|---|---|---|---|
| tA3 | c_E3_bf_11, 0.4 | 32.9 / 29.2 | 34.6 / 31.4 | **51.3 / 48.3** (21.1 / 20.7) | 523 / 434 |
| tA2 | c_E3_bf_11, 0.7 | 28.5 / 25.2 | 36.8 / 33.4 | **53.9 / 50.6** (20.5 / 20.0) | 525 / 436 |
| tB  | c_W2_bn_01, 0.4 | 39.7 / 35.2 | 28.8 / 26.3 | **45.3 / 43.0** (21.1 / 21.0) | 525 / 436 |
| tA (first layer setup, M7 not blocked; clean GRT) | c_E3_bf_11, 0.4 | 3.8 / 3.6 | 20.6 / 18.8 | 36.0 / 34.5 | 512 / 424 |
- vs estimate: 38.1/29.7 (Rr 0), 43.8/40.6 (Rr 30), 61.1/60.7 (Rr 60) -> measured lands between Rr 30 and Rr 60, as the
  measured routed residual (29-40 ps) predicts. vs today (trial14 routed): glue spread c_E3 50.9/57.1, c_W2 130.9/127.7,
  c_W2 damage+OCV 225.8. MC 3-sigma pair part 14-15 ps; gradient < 1.3 ps.
- Residual source (renders VIEWED): GRT jogs some vertical tree legs off the strap's glue column onto M9 over the core
  edge (10-60 um x-jogs), giving 130-150 ps input slews on 4-8 D cells. Fixable structurally (reserve the tree-leg
  M9 track beside the strap); tA shows the floor with straight legs (3.8 ps -> U 36/34.5).
- Tap stability (mesh-tap nominal arrivals, region-relative / absolute, between any two trials incl. the other region):
  **7.0-18.0 ps rel / 11.4-25.1 abs** vs today trial14->15: c_E3 42.3 rel / 32.8 abs, c_W2 92.2 / 135.4, die max
  96.3 / 270.8 -> trigger (c) (> 30 ps) cleared by the mesh form.
- A0 core taps (off mesh): early vs mesh 336-339 TT / 279-283 FF; required (trial14 glue median - core median) 398-408 TT /
  340-354 FF -> **structural offset error 60-72 ps** (core branch 3 stages vs mesh path 7 stages + mesh). W_core
  (offset + AOCV 3 sigma sqrt(3+7) + U/2) 99-111; with the offset planned (core branch joined one stage upstream of the
  region root, or +1 mesh-side stage; plan-computed from the core view, not a trim) 32-47.
- Hold buffers (DIE-QC-23 hb_est23 method, measured windows, k in/out unchanged 5/1): c_E3_bf_11 71,208 (W180) ->
  44,372 (-38 %; k hop 4->1, core 5->3) / 34,044 (-52 %) with the planned core offset; c_W2_bn_01 110,284 -> 57,228
  (-48 %) / 46,900 (-57 %). tA2 hop k 2 (U 53.9) -> 46,432.
- Power (C V^2 f 0.7 V 1.2 GHz + 7.7 uW/BUFx24): 4.97-4.99 mW/region (mesh 2.04, tree wire 21.1 mm 2.36, cells 0.59)
  vs today 2.7 (c_E3) / 4.0 (c_W2) mW (estimate basis) -> +1.0-2.3 mW/region, ~+0.2-0.44 W over 192 c_* regions;
  hold-buffer power -0.1..-0.15 W (estimate) -> net about +0.1-0.3 W.
- Tracks: straps M9 0.21 % / M8 0.17 % of the region; tree GRT demand M9 0.10 % / M8 0.01 %; GRT overflow 0.

## Not done (successor)
- DRT + OpenRCX: detailed_route sat > 45 min in "Init gr pin query" on the whole 3.23-mm2 region (fine M1-M3 tracks +
  886 PG stripes). tA2/tA3/tB keep running (docker qcmp-t*, 64 GB). Collect: when tX/run.log and tX/run_ff.log end
  "EXIT 0": `bash results/qc_mesh_pilot_1/pilot_chain.sh tX drt` (X = A3, A2, B) then `pilot_summary.py drt
  hb_est23.json summary_drt.json tA3 tA2 tB`, `pilot_render.py tX tX/render_drt.png` (VIEW), DRC = tX/drc.rpt. If still in
  init after 2 h: kill them and run DRT on a clip (one column strip incl. its straps) instead.
- die_sta_related --mesh-signoff on a die proof dir (region re-referenced to 'm'): not run; the U above is its formula.
