#!/usr/bin/env python3
"""dieclock_regeq.py PLAN OUT [die_clock build args...] (REACH-FIX-2 11-12, COORD decision B)

H-tree to region roots, balanced by WIRE only: die_clock build --pad leg (every leg padded to its level's longest leg,
last mile balanced inside its own region), then region equalisation: each leaf's last-mile deficit
  deficit_ps(leaf) = max over leaves (latest tap of the leaf) - own latest tap      (TT, die_clock STA on own SPEF)
becomes extra wire on that leaf's own leg (--leaf-pad, after the leg's first segment).  um += 0.8 * deficit / slope,
slope = the leaf's measured d(arrival)/d(pad) of the previous step (start 0.10 ps/um).  No delay cells: the pad is
M8/M9 wire over the partitions, and wire tracks FF by construction.  Stops at TT tap spread <= --stop-ps.
-> OUT/it<N>/ (die_clock build + arr_TT/FF.txt), OUT/leafpad<N>.json, OUT/regeq.json
HEAD g5p (aware 0, window 0, --wide-levels 10 --ndr 4w): tap spread 108.6 -> 11.8 -> 2.4 ps TT (4.2 FF) in 2 steps."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_clock as DC  # noqa: E402


def stats(d, tree):
    res = {}
    for c in ("TT", "FF"):
        tarr = DC.read_arr(d / f"arr_{c}.txt")[0]
        v = [tarr[t["port"]] for t in tree["taps"] if t["port"] in tarr]
        res[c] = dict(spread=round(max(v) - min(v), 1), mean=round(sum(v) / len(v), 1), max=round(max(v), 1))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--iters", type=int, default=8)
    ap.add_argument("--stop-ps", type=float, default=5.0)
    ap.add_argument("--libdir")
    ap.add_argument("--max-leaf-pad-um", type=float, default=1500.0,
                    help="a leaf needing more wire than this is STRUCTURAL (refused, listed): fix its last mile, not pad it")
    ap.add_argument("--max-iter-mb", type=float, default=2048.0,
                    help="abort when one iteration's output exceeds this (FLEET-2 11-12: a diverged loop wrote a 324 GB "
                         "SPEF on intel1; the SPEF ladder grows with the pad wire)")
    ap.add_argument("--max-leafpad-m", type=float, default=2.0, help="abort before a build whose total leaf pad exceeds this")
    ap.add_argument("--max-residual-ps", type=float, default=300.0,
                    help="refuse to equalise when the first-step tap spread exceeds this (pads would dominate insertion)")
    a, extra = ap.parse_known_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pad, slope, prev, hist = {}, {}, None, []
    for it in range(a.iters + 1):
        d = out / f"it{it}"
        pf = out / f"leafpad{it}.json"
        pf.write_text(json.dumps(pad))
        if sum(pad.values()) > a.max_leafpad_m * 1e6:
            hist.append(dict(it=it, abort=f"leaf pad {sum(pad.values()) / 1e6:.2f} m > {a.max_leafpad_m} m"))
            print(json.dumps(hist[-1]), flush=True)
            break
        subprocess.run([sys.executable, "-B", str(HERE / "die_clock.py"), "build", a.plan, "--out", str(d), "--pad", "leg",
                        "--leaf-pad", str(pf)] + extra, check=True, capture_output=True)
        mb = sum(f.stat().st_size for f in d.iterdir() if f.is_file()) / 2 ** 20
        if mb > a.max_iter_mb:
            (d / "ctree.spef").unlink(missing_ok=True)
            hist.append(dict(it=it, abort=f"iteration output {mb:.0f} MB > {a.max_iter_mb} MB (SPEF deleted)"))
            print(json.dumps(hist[-1]), flush=True)
            break
        DC.cmd_sta(argparse.Namespace(dir=str(d), corner=["TT", "FF"], libdir=a.libdir))
        tree = json.loads((d / "tree.json").read_text())
        tarr = DC.read_arr(d / "arr_TT.txt")[0]
        lm = {}
        for t in tree["taps"]:
            if t["port"] in tarr:
                lm[t["leaf"]] = max(lm.get(t["leaf"], -1e9), tarr[t["port"]])
        tgt = max(lm.values())
        defi = {k: tgt - v for k, v in lm.items()}
        h = dict(it=it, **stats(d, tree), padding_mm=round(tree["meta"]["padding_um"] / 1000, 1),
                 leafpad_mm=round(sum(pad.values()) / 1000, 1))
        hist.append(h)
        print(json.dumps(h), flush=True)
        if it == 0 and h["TT"]["spread"] > a.max_residual_ps:
            slow = sorted(lm.items(), key=lambda kv: -kv[1])[:10]
            h["refused"] = dict(reason=f"regional residual {h['TT']['spread']} ps > {a.max_residual_ps}: structural, not wire",
                                slowest_leaves=[[k, round(v, 1)] for k, v in slow])
            print(json.dumps(h["refused"]), flush=True)
            break
        if len(hist) > 1 and h["TT"]["spread"] > 1.5 * min(r["TT"]["spread"] for r in hist[:-1]):
            h["stop"] = "diverging (spread > 1.5 x best)"
            break
        if len(hist) > 1 and h["TT"]["spread"] >= hist[-2]["TT"]["spread"] - 0.5:
            h["stop"] = "no gain"
            break
        if h["TT"]["spread"] <= a.stop_ps or it == a.iters:
            break
        for k in defi:
            if prev is not None and k in prev[0]:
                dl = pad.get(k, 0.0) - prev[1].get(k, 0.0)
                dt = lm[k] - prev[0][k]
                if dl > 1.0 and dt > 0.5:
                    slope[k] = min(0.5, max(0.02, dt / dl))
        prev = (dict(lm), dict(pad))
        for k, dp in defi.items():
            pad[k] = min(a.max_leaf_pad_um, max(0.0, pad.get(k, 0.0) + 0.8 * dp / slope.get(k, 0.10)))
    done = [r for r in hist if "TT" in r]
    if not done:
        (out / "regeq.json").write_text(json.dumps(dict(best_it=None, history=hist), indent=1) + "\n")
        return 2
    best = min(done, key=lambda r: r["TT"]["spread"])
    for r in done:                                   # only the best iteration keeps its SPEF
        if r["it"] != best["it"]:
            (out / f"it{r['it']}" / "ctree.spef").unlink(missing_ok=True)
    (out / "regeq.json").write_text(json.dumps(dict(best_it=best["it"], history=hist), indent=1) + "\n")
    print("BEST it%d" % best["it"], json.dumps(best["TT"]))
    return 0 if not ({"refused", "abort"} & set(hist[-1])) else 2


if __name__ == "__main__":
    raise SystemExit(main())
