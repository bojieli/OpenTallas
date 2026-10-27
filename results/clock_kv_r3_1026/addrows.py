"""model: add mesh drivers (m=2) on the driverless strap rows of a pred dir, tree arrival = base + DELTA ps (both corners)."""
import json, sys, shutil
from pathlib import Path
src, dst, delta = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])
dst.mkdir(parents=True, exist_ok=True)
M = json.loads((src / "mesh.json").read_text())
xs, ys = M["xs"], M["ys"]; new = []
for j in M["meta"]["driverless_rows"]:
    for i, x in enumerate(xs):
        cells = [f"ckm_d_{i}_{j}_{k}" for k in range(2)]
        M["drivers"][f"{i}_{j}"] = dict(i=i, j=j, ideal=[x, ys[j]], site=[round(x, 3), round(ys[j], 3)], strap="M8",
                                        move_um=0.0, jog_um=0.0, cells=cells, model_added=True)
        new += cells
(dst / "mesh.json").write_text(json.dumps(M))
for C in ("TT", "FF"):
    lines = (src / f"tree_{C}.txt").read_text().splitlines()
    L, E, S = map(float, lines[0].split()[2:5])
    lines += [f"D {c} {L + delta:.6f} {E + delta:.6f} {S:.6f}" for c in new]
    (dst / f"tree_{C}.txt").write_text("\n".join(lines) + "\n")
print(len(new))
