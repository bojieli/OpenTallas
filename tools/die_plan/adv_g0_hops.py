"""adv_g0_hops.py -- PRECHECK ADV-G0-HOPS (COORD 11-24 00:5x; S81 c8 post-tail: INT/RTHOPS found 98 hop ERRORs on 98 lanes only at G0).

G0 (check.py) runs check_hops(P, R, geo) -- every lane's mandatory-slot-pin / ft-station hop against its reach (lane reach_um or
P.reach) -- as part of a long full G0; this advisory runs ONLY that function on the plan (lane_geometry + check_hops, ~30 s on S81 c8,
973 lanes) so the 98 land in PRE time, before the tail / bind.  Same messages as G0 ('lane L: hop i via mandatory slot pins is X um > reach
Y' / 'normal FT ... real input bit'), lane count and worst over-reach per type in the summary.  The sibling plan_gate_pre classes RSTREACH
and DERIVEDNAME (derived_drop.py: stale START raw pointers, the 28 reset-reach FAIL types on c8) already run in PRE, not here.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.  Needs a tree whose tools/die_plan carries check.py.
"""
import sys
from pathlib import Path

CHECK = "ADV-G0-HOPS"
MAX_LINES = 20


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _findings(raw, plan_path, tree=None, **kw):
    d = Path(tree) / "tools" / "die_plan" if tree and (Path(tree) / "tools" / "die_plan" / "check.py").is_file() else Path(__file__).resolve().parent
    sys.path.insert(0, str(d))
    import check as C
    import schema as S
    R = C.Report(False)
    P = S.Plan(raw, Path(plan_path))
    geo = {lid: C.lane_geometry(P, lid) for lid in P.lanes}
    C.check_hops(P, R, geo)
    errs = [i for i in R.items if i.get("check") == "hops"]
    over = {}
    for i in errs:
        m = i["msg"]
        try:
            h = float(m.split(" um > reach ")[0].split()[-1])
            r = float(m.split(" um > reach ")[1].split()[0].rstrip(";,)"))
        except (ValueError, IndexError):
            continue
        over[i.get("lane")] = max(over.get(i.get("lane"), 0.0), h - r)
    out = [_w(i["msg"]) for i in sorted(errs, key=lambda i: -over.get(i.get("lane"), 0.0))[:MAX_LINES]]
    out.append(_w("summary", f"{len(over) or len(errs)} lane(s) with a hop over reach ({len(errs)} ERROR(s); worst +{max(over.values(), default=0.0):.0f} um) "
                             f"of {len(P.lanes)} lanes; same check as G0 hops, fix: add stations / re-seat the crossed ft slot"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
