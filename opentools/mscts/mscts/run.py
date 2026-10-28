"""opentools.mscts region-mode driver.

    python3 -m mscts.run build REGION.json --out DIR [--objective late_split|nearest] [--corner TT]
        REGION.json = {name, entry[x,y], sinks[{name, xy}], crossings[[a, b], ...], period_ps?}
        writes DIR/tree.json (cells, wires, model arrivals, crossing report) and, for verification,
        DIR/region_tree.{v,spef}, DIR/deck_<C>.sp, DIR/sta_<C>.tcl
    python3 -m mscts.run compare DIR [--corner TT]      model vs OpenSTA vs ngspice per sink (skew report)
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))                 # opentools/
sys.path.insert(0, str(HERE.parents[1] / "clkplan"))
from clkplan import model as MD                           # noqa: E402

from . import netlist as NL                               # noqa: E402
from . import region as RG                                # noqa: E402


def build(a):
    spec = json.loads(Path(a.region).read_text())
    M = MD.load(a.model)
    xs = [tuple(x) for x in spec.get("crossings", [])]
    R = RG.build(spec["sinks"], M, tuple(spec["entry"]), xs, objective=a.objective, corner="TT")
    rep, rows = RG.report(R, xs, spec.get("period_ps", 833.0) / 2.0)
    bufs, edges = RG.segments(R)
    arr = {c: RG.arrivals(R, c)[0] for c in ("TT", "FF")}
    sink_ids = {nd["name"]: nd["id"] for nd in R.nodes if nd["kind"] == "sink"}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    root = f"r{R.root}"
    sinks = [f"s_{n}" for n in sink_ids]
    tree = dict(tool="opentools.mscts.region", region=spec.get("name"), objective=a.objective, summary=rep,
                buffers={k: dict(xy=list(v[0]), kind=v[1]) for k, v in bufs.items()},
                wires=[dict(drv=d, load=l, um=round(w, 2)) for d, l, w in edges],
                wirelength_um=round(sum(w for _, _, w in edges), 1), snakes=R.snakes,
                model_arrival_ps={c: {f"s_{n}": round(arr[c][i], 2) for n, i in sink_ids.items()} for c in arr},
                crossings=rows, root=root)
    (out / "tree.json").write_text(json.dumps(tree, indent=1) + "\n")
    names = list(bufs)
    (out / "region_tree.v").write_text(NL.verilog(names, edges, root, sinks))
    (out / "region_tree.spef").write_text(NL.spef(names, edges, sinks))
    for c in ("TT", "FF"):
        t_end = 100 + NL.CFG["ramp_ps"] + max(arr[c].values()) * 1.3 + 600
        (out / f"deck_{c}.sp").write_text(NL.spice(names, edges, root, sinks, c, a.libdir, a.osdi, out_dat=f"arr_{c}.dat")
                                          + NL.tran_line(t_end))
        (out / f"sta_{c}.tcl").write_text(NL.sta_tcl(f"lib_{c}.lib", sinks, root).replace("sta_arr.txt", f"sta_arr_{c}.txt"))
    print(f"{spec.get('name')} [{a.objective}]: {len(bufs)} buffers, {tree['wirelength_um']} um wire; " + json.dumps(rep))


def _cross(path, vh):
    rows = [list(map(float, ln.split())) for ln in Path(path).read_text().splitlines() if ln.strip()]
    nv = len(rows[0]) // 2
    res = []
    for v in range(nv):
        hit, tp, xp = None, None, None
        for r in rows:
            t, x = r[2 * v], r[2 * v + 1]
            if xp is not None and xp < vh <= x:
                hit = tp + (vh - xp) * (t - tp) / (x - xp)
                break
            tp, xp = t, x
        res.append(hit)
    return res


def compare(a):
    d = Path(a.dir)
    tree = json.loads((d / "tree.json").read_text())
    c = a.corner
    sinks = list(tree["model_arrival_ps"][c])
    sp = _cross(d / f"arr_{c}.dat", NL.CFG["vdd"][c] / 2)
    sp0 = sp[0]
    spice = {s: (x - sp0) * 1e12 for s, x in zip(sinks, sp[1:]) if x is not None}
    st = {}
    for ln in (d / f"sta_arr_{c}.txt").read_text().splitlines():
        p, v = ln.split()
        st[p.split("/")[0][2:]] = float(v)
    r0 = st.pop(tree["root"])
    sta = {s: st[s] - r0 for s in sinks}
    mod = tree["model_arrival_ps"][c]
    rows = []
    for s in sinks:
        rows.append(dict(sink=s, model=mod[s], sta=round(sta[s], 2), spice=round(spice.get(s, float("nan")), 2)))
    def stat(k):
        v = [r[k] for r in rows if not math.isnan(r[k])]
        return dict(max=round(max(v), 2), min=round(min(v), 2), skew=round(max(v) - min(v), 2))
    dsm = [r["sta"] - r["spice"] for r in rows if not math.isnan(r["spice"])]
    dmm = [r["model"] - r["spice"] for r in rows if not math.isnan(r["spice"])]
    out = dict(corner=c, sinks=len(rows), spice_missing=sum(1 for r in rows if math.isnan(r["spice"])),
               model=stat("model"), sta=stat("sta"), spice=stat("spice"),
               sta_minus_spice=dict(max=round(max(dsm), 2), min=round(min(dsm), 2), mean=round(sum(dsm) / len(dsm), 2),
                                    rel_mean_pct=round(100 * sum(dsm) / sum(r["spice"] for r in rows if not math.isnan(r["spice"])), 2)),
               model_minus_spice=dict(max=round(max(dmm), 2), min=round(min(dmm), 2), mean=round(sum(dmm) / len(dmm), 2)))
    # crossing pairs: nominal d by spice vs sta
    xd = []
    for x in tree["crossings"]:
        sa, sb = f"s_{x['a']}", f"s_{x['b']}"
        if sa in spice and sb in spice:
            xd.append(abs((spice[sb] - spice[sa]) - (sta[sb] - sta[sa])))
    out["crossing_d_sta_vs_spice_max_ps"] = round(max(xd), 2) if xd else None
    (d / f"compare_{c}.json").write_text(json.dumps(dict(summary=out, rows=rows), indent=1) + "\n")
    print(json.dumps(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build")
    b.add_argument("region")
    b.add_argument("--out", required=True)
    b.add_argument("--objective", default="late_split", choices=["late_split", "nearest"])
    b.add_argument("--model")
    b.add_argument("--libdir", default="/w/lib")
    b.add_argument("--osdi", default="/w/osdi/bsimcmg23.osdi")
    c = sp.add_parser("compare")
    c.add_argument("dir")
    c.add_argument("--corner", default="TT")
    a = ap.parse_args(argv)
    return build(a) if a.cmd == "build" else compare(a)


if __name__ == "__main__":
    raise SystemExit(main())
