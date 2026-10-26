# HBM B2 independent die-grid IR windows — 2026-10-12

The SW VM window measures 6.785 mV rail-to-rail bound at the existing assumed peak current density. OpenROAD pdngen and power-grid connectivity pass; both rail solves complete. This is measured evidence for the upper die grid. It does not establish integrated die IR closure.

| Window | VDD drop mV | VSS rise mV | Sum of rail maxima mV | Budget mV | Status |
|---|---:|---:|---:|---:|---|
| VM SW | 3.577 | 3.208 | 6.785 | 35 | measured upper-grid PASS |
| SM SW | 4.241 | 4.305 | 8.546 | 35 | measured upper-grid PASS |
| Service SW | 7.711 | 7.749 | 15.460 | 35 | measured upper-grid PASS |

Inputs are the repaired pinned `hbmdie-v10/sta_stn/clock/model.json.gz` and its `elements.lef` plus `views.lef`; every manifest records input and generator SHA256. The model's original source label is `120f11b14`; the remote snapshot contains the station sizing patch `a236cd79f` and clock domain patch `d17aa0ad3`, as recorded in `SOURCE_COMMIT`. The authoritative GRT run and its checkpoint are unchanged.

The complete `power_map.json` assigns each core instance its pinned geometry, domain, peak load, and PG layers from its actual view where available. Peak densities are the existing HBM assumptions: SM 1.20 W/mm², service 3.924, hub/spine/attention 1.05, waypoint 0.6, index override 1.25. The core total is 453.799 W. PHY, link, host and SerDes rails are excluded. This is a design load budget, not measured switching activity.

The test divides footprint current among tiles no larger than 43.2 µm, avoiding PSM's large-block single-node injection artefact. M7 load stripes feed pdngen M8/M9 straps (0.48 µm width, 4.896 µm pitch in VM/SM; the service retains its denser existing coverage). Bumps use the existing assumed 45 µm array / 63.640 µm per-rail pitch and 20 µm size at 0.7 V. A guard of two bump pitches surrounds the evaluated rectangle. The reported bound sums the separate maximum VDD drop and VSS rise inside the inner window.

The load projection is an independent die-grid experiment. It does not preserve child signal obstructions or prove actual leaf M5/M6-to-die M8 via access. The pinned abstract audit lacks both PG rails for 41,484 instances, principally generated stations and reserved blocks, including new B2 slots without real PG views. Therefore no integrated child connectivity, internal tile drop, bump/package impedance, all-window coverage or final signoff is claimed. Actual view PG layers include M8 (32 SM instances; 64 per-rail layer occurrences in the manifest), which must be reconciled with the top-layer contract or explicitly retained exceptions before integrating the next PDN die iteration.

Full immutable solver cases, voltage reports and `pdn.odb` remain on `ot-epyc1tb:/srv/opentallas-scratch/claude/hbmdie-v10/ir_1012/{vmSW,smSW,svcSW}`. Generation/run tools are `tools/hbm_die_ir_window.py` and `tools/hbm_die_ir_run.sh`; the admitted chain writes `ir_1012/STATUS.log`. Its failed first grid direction experiment is retained separately in `ir_1012_try1_horizontal_m7`.
