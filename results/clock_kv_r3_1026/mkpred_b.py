"""CLOCK-KV-R3 (b) plan-level prediction input: b_cont plan build (no P&R) + equal driver arrivals per corner taken from
the R2 pred_zm0 model (u32x64 measured median late, late-early, slew).  Tree residual is bounded separately."""
import json, sys, shutil
from pathlib import Path
src, dst, ref = Path(sys.argv[1]), Path(sys.argv[2]), json.load(open(sys.argv[3]))
dst.mkdir(parents=True, exist_ok=True)
shutil.copy2(src / "mesh.json", dst / "mesh.json")
M = json.loads((src / "mesh.json").read_text())
for C in ("TT", "FF"):
    r = ref[C]; L, E, S = r["driver_late_ps"], r["driver_late_ps"] - r["late_minus_early_ps"], r["slew_ps"]
    (dst / f"tree_{C}.txt").write_text("".join(f"D {c} {L:.6f} {E:.6f} {S:.6f}\n" for dv in M["drivers"].values() for c in dv["cells"]))
(dst / "PREDICTION_MODEL.json").write_text(json.dumps(dict(source=str(src), ref=sys.argv[3], model=__doc__, **{C: ref[C] for C in ("TT","FF")}), indent=1))
