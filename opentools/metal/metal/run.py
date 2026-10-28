"""opentools.metal driver: shared plan + clock wire list -> allocation (plan section metal_alloc) + phase scan.

    python3 -m metal.run PLAN.json --wires WIRES.json --layer M8 --out OUTDIR
WIRES.json = [{name, ndr?(default plan clock.ndr), y_pref, x0, x1, row|null, max_jog_um?}] (across-run coordinate first:
for a V layer pass x as y_pref and the y span as x0/x1).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # opentools/
from common import plan as PL                                       # noqa: E402

from . import alloc as A                                            # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--wires", required=True)
    ap.add_argument("--layer", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    P = PL.load(a.plan)
    pg = next((g for g in P["pg"] if g["layer"] == a.layer), None) or dict(layer=a.layer, pitch_um=1e6, stripes=[])
    wins = [w for w in P["pin_windows"] if w["layer"] == a.layer]
    ndr = P["clock"]["ndr"]
    W = [dict(w, ndr=w.get("ndr") or ndr) for w in json.loads(Path(a.wires).read_text())]
    res = A.allocate(dict(pg=pg, pin_windows=wins), W)
    scan = [A.phase_scan(pg, ndr, w["rows"]) for w in wins if "rows" in w]
    Q = json.loads(json.dumps(P))
    Q.setdefault("metal_alloc", {})[a.layer] = dict(tool="opentools.metal", **res, phase_scan=scan)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    PL.save(Q, out / "plan_out.json")
    print(f"{a.layer}: {res['stats']}")
    for c in res["conflicts"][:20]:
        print("  CONFLICT", c["name"], c["y_pref"], "; ".join(c["blockers"]))
    return 1 if res["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
