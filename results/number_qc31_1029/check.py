"""Independent arithmetic on existing QC31 MC samples; no STA/physical rerun."""
import itertools
import json
import math
from pathlib import Path
import statistics
import sys

root = Path(sys.argv[1])
rows = []
for variant, edge, corner in itertools.product(("vK", "vT"), ("rise", "fall"), ("TT", "FF")):
    trial = root / variant / ("tA3d" if edge == "rise" else "tA3d_fall")
    data = json.loads((trial / f"mc_drt_{corner}.json").read_text())
    report = json.loads((trial / "pair_drt.json").read_text())["corners"][corner]
    arrivals, gradient, loads = data["arr"], data["grad_vec_ps"], data["loads"]
    pairs = []
    for a, b in itertools.combinations(range(len(loads)), 2):
        # This pilot's routed reference equals MC sample zero by construction.
        # Keep the independently read correction explicit.
        correction = ((data["routed"][a] - arrivals[0][a]) -
                      (data["routed"][b] - arrivals[0][b]))
        delta = [sample[a] - sample[b] + correction for sample in arrivals]
        sample = delta[1:] or delta
        statistical = abs(statistics.mean(sample)) + 3 * statistics.stdev(sample)
        spatial = math.dist(gradient[a], gradient[b])
        uncertainty = max(max(map(abs, delta)), statistical) + spatial
        pairs.append((uncertainty, loads[a], loads[b]))
    worst = max(pairs)
    recorded = report["pair_U_max_ps"]
    assert len(pairs) == report["pairs"] == 378
    assert abs(worst[0] - recorded) < .006, (variant, edge, corner, worst, recorded)
    assert list(worst[1:]) == report["worst_pair"]
    rows.append(dict(variant=variant, edge=edge, corner=corner,
                     pair_count=len(pairs), independent_pair_U_ps=worst[0],
                     recorded_pair_U_ps=recorded, worst_pair=list(worst[1:]),
                     target_80_pass=worst[0] <= 80,
                     nominal_spread_ps=max(arrivals[0]) - min(arrivals[0])))
shape_checks = []
for source, shapes in json.loads((root / "c1_shapes.json").read_text()).items():
    if not any(f"/{v}/" in source for v in ("base", "vK")):
        continue
    mesh = [s for s in shapes if s[0] == "ck_mesh"]
    findings = []
    for net, layer, x0, y0, x1, y1 in shapes:
        if net not in ("n_P1u", "n_B1"):
            continue
        for _, ml, a0, b0, a1, b1 in mesh:
            if ml != layer:
                continue
            overlap_x, overlap_y = min(x1, a1) - max(x0, a0), min(y1, b1) - max(y0, b0)
            if overlap_x > 1e-6 and overlap_y > 1e-6:
                findings.append(dict(net=net, layer=layer, overlap_um=[overlap_x, overlap_y]))
    shape_checks.append(dict(source=source, selected_net_to_mesh_overlap_rectangles=findings))
assert len(shape_checks) == 2
assert any(r["selected_net_to_mesh_overlap_rectangles"] for r in shape_checks if "/base/" in r["source"])
assert not any(r["selected_net_to_mesh_overlap_rectangles"] for r in shape_checks if "/vK/" in r["source"])
print(json.dumps(dict(scope="existing artifact arithmetic only; not die STA or freeze",
                     rows=rows, selected_shape_checks=shape_checks), indent=2))
