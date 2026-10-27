import sys, json
sys.path.insert(0, "/w/die_plan")
import schema as S, die_clock_mesh as DCM, die_clock_128 as C128, die_infra as DI
from pathlib import Path
P = S.Plan(S.load("inputs/candidate_oneqc0733.json"), Path("inputs/candidate_oneqc0733.json"))
pgr = DI.pg_rects(P, C128.pg_grid(P))
print("pg rects", len(pgr), sorted({(r[0], r[1]) for r in pgr})[:6])
m8 = sorted({round((r[3]+r[5])/2,4) for r in pgr if r[1]=="M8"})[:8]; print("M8 stripe centres", m8)
nd = DCM.NDR["16w"]; print("16w", nd, "shield_geom", C128.shield_geom(nd), "flank_gap", C128.flank_gap(nd))
x0, x1 = float(sys.argv[1]), float(sys.argv[2])
legal = {}
for k in range(0, 2*108+1):
    y = float(sys.argv[3]) + k*0.04
    R = C128.TrackRouter(nd, "VSS", DCM.DEFAULT_TRACKS, 0.0, wide_merge_um=nd.get("wide_merge_um"))
    R.reserve(C128.pg_shapes(pgr))
    c, mode, e = R.place("M8", y, x0, x1, "probe")
    if c is not None: legal[c] = mode
print("legal M8 centres (single 16w trunk, max_move 0)", sorted(legal.items()))
