#!/usr/bin/env python3
"""svc_ft_resite.py BASE_PLAN PLAN_IN PLAN_OUT --types RE [--reach 405]

VL3-S81-SVCSTN: after a street / growth form, re-site the ft-slot station registers of a type whose chain got a hop
over reach that it did not have in BASE_PLAN (or got worse than its base worst hop).  Same register count (0 cycles):
hub_repack.route_station on the form's own core raster from the face flop regs_um[0] to the middle of the slot's out
window on its out face.  A re-sited slot drops its explicit bit_sites_um / bit_site_cell_um (optional per
ft_bit_sites.validate_slot; the kit then places the stage flops at the station homes).  Exit 1 if a slot cannot keep
its count within reach (reported, plan still written with that slot unchanged)."""
import argparse, json, re, sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_repack as HR


def hops(pts):
    return [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]


def exit_pt(t, f):
    W, H = t["outline_um"]; lo, hi = f["out_window_um"]; m = (lo + hi) / 2
    return {"N": (m, H), "S": (m, 0.0), "W": (0.0, m), "E": (W, m)}[f["out_face"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base"); ap.add_argument("plan_in"); ap.add_argument("plan_out")
    ap.add_argument("--types", required=True); ap.add_argument("--reach", type=float, default=405.0)
    a = ap.parse_args()
    B = json.load(open(a.base)); P = json.load(open(a.plan_in)); rx = re.compile(a.types); bad = 0
    for tn, t in P["partition_types"].items():
        if not rx.search(tn):
            continue
        tb = B["partition_types"][tn]
        rects = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1])
                 for h in t["hard_cores"]]
        rects += [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
                  for c in t.get("contents") or [] if "origin_um" in c and "outline_um" in c]
        W, H = t["outline_um"]; R = HR.Raster(W, H, rects)
        for f, fb in zip(t.get("ft_slots") or [], tb.get("ft_slots") or []):
            e, eb = exit_pt(t, f), exit_pt(tb, fb)
            hn = hops(f["regs_um"] + [list(e)]); hb = hops(fb["regs_um"] + [list(eb)])
            if max(hn) <= max(a.reach, max(hb)) + 0.5:
                print(tn, f["name"], "keep", "max %.0f (base %.0f)" % (max(hn), max(hb)))
                continue
            n = len(f["regs_um"]) - 1
            r = HR.route_station(R, tuple(f["regs_um"][0]), e, n, a.reach)
            if r is None or len(r["regs"]) != n:
                print(tn, f["name"], "FAIL same-count re-site", None if r is None else len(r["regs"]), "vs", n); bad += 1
                continue
            new = [f["regs_um"][0]] + [[round(p[0], 4), round(p[1], 4)] for p in r["regs"]]
            hh = hops(new + [list(e)])
            print(tn, f["name"], "RESITED", r["kind"], "max %.0f -> %.0f (base %.0f)" % (max(hn), max(hh), max(hb)), [round(x) for x in hh])
            f["regs_um"] = new
            f.pop("bit_sites_um", None); f.pop("bit_site_cell_um", None)
            f["note"] = (f.get("note", "") + " | VL3-S81-SVCSTN growth form: stations re-sited (%s, same count %d)" % (r["kind"], n)).strip(" |")
    json.dump(P, open(a.plan_out, "w"), indent=1)
    print("wrote", a.plan_out, hashlib.sha256(open(a.plan_out, "rb").read()).hexdigest()[:12], "bad", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
