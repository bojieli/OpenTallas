#!/usr/bin/env python3
"""S81-SVC-7: R5 svc_lo no-growth band budget from measured mapped provider areas (Option C, dY 0).

Arithmetic only: 8.64-um box grid, 259.2-um band height, 4.32-um halo per side, 8.64-um gaps, four freed bands.
Inputs are the receipts named in SOURCES; GLUE count is the SVC-5 estimate (not measured). No plan or RTL change.
"""
import json, math, sys
GRID = 8.64; GAP = 8.64; BAND_H = 259.2; HALO = 4.32
BAND_X0, BAND_XMAX, BANDS = 34.56, 1401.84, 4
CAP = BANDS * (BAND_XMAX - BAND_X0 + GAP)
FIXED = {"SML": (8, 120.96), "H4": (8, 103.68), "SMD": (4, 69.12)}
GLUE = (7, 120.96)
HSLICES = 32; AREA = {"measured_9095.7": 9095.70384, "fastpad_model_7096.1": 7096.13868}
SOURCES = dict(fixed_boxes="results/geom_review/svc_r5_provider_1113/review.json (mapped SML/SMD/H4 at their boxes)",
    hslice="results/rtl/svc_native_providers_1113/result.json (MAP+ODB, 69881 cells)",
    fastpad="results/rtl/svc_irg_fastpad_1113/model.json (estimated_only, RTL unbuilt, unproved)",
    glue="S81-SVC-5 07:20 estimate: 7 boxes, shape and count not measured")
def box(area, util, h):
    inner = area / util / (h - 2 * HALO)
    return math.ceil(round((inner + 2 * HALO) / GRID, 6)) * GRID
fixed = sum(n * (w + GAP) for n, w in FIXED.values())
glue = GLUE[0] * (GLUE[1] + GAP)
rows = []
for name, area in AREA.items():
    for util in (0.40, 0.45, 0.55, 0.63):
        for dy_total in (0.0, 77.76):
            h = BAND_H + dy_total / BANDS
            w = box(area, util, h)
            irg = HSLICES * (w + GAP)
            total = fixed + glue + irg
            rows.append(dict(area=name, util=util, dy_total_um=dy_total, band_h_um=round(h, 2), hslice_box_w_um=round(w, 2),
                             irg_band_um=round(irg, 2), demand_um=round(total, 2), slack_um=round(CAP - total, 2), fits=total <= CAP))
print(json.dumps(dict(scope="estimate from mapped areas; no placement, no plan event", capacity_um=round(CAP, 2), fixed_um=round(fixed, 2),
                      glue_um=round(glue, 2), sources=SOURCES, rows=rows), indent=1))
