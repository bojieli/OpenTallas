#!/usr/bin/env python3
"""HBM die-FT band delta (lane DIE-FT-HBM, COORD DIE GRT RULINGS 2026-10-25 11:29): a plan->plan generator step.

    python3 physical/die_plan/hbm_arch/die_ft_band.py --src PLAN_DIR --out PLAN_DIR2 \
        --row 4510.08 [--row 6065.28 ...] [--fixed root NW_hub NE_hub NW_io NE_io] [--types q_b100 ...]

Per abutted row of partitions (same origin y + height):
  1. lane chains: consecutive E/W seam ports of one lane joined by a straight E->W / W->E ft slot of a row partition
     form ONE chain that gets ONE die-y window on every seam it crosses (aligned across neighbours, no jog);
  2. placement on the seams: chains anchored by a --fixed partition keep that partition's window; the other ft
     chains (and ft turn ports) are packed from the row top down (the core-free top of the b1xx blocks) widest first,
     every remaining (terminating bus) port from the row bottom up; window lengths unchanged (same pin density);
  3. die_ft_bands on every --types type: dir EW, span = the type-frame y range of its E/W ft pins, layers M4+M6,
     die_share 1.0 ("M4/M6 belong to the die there"); die_trial models a band with GRT region adjustments;
  4. ft stations of the straight E/W slots move onto the chain's window centre line (x unchanged).
Writes PLAN_DIR2/die_plan.json (+ copies the sidecars) and die_ft_band_report.json.  No hand edits.
"""
import argparse
import re
import copy
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402

SNAP = 0.192          # lcm of the M4 (0.048) and M6 (0.064) pitches; row origins are on the 8.64 lattice
GAP = 0.48            # between two windows on one face (as the plan packer)
MARGIN = 8.64         # from the row corners


def snap(v, mode="near"):
    import math
    f = {"near": round, "down": math.floor, "up": math.ceil}[mode]
    return round(f(v / SNAP - (1e-6 if mode == "up" else -1e-6 if mode == "down" else 0)) * SNAP, 3)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--row", type=float, action="append", required=True, help="row origin y (die um)")
    ap.add_argument("--fixed", nargs="*", default=["root"], help="partitions whose seam windows stay (root = ROOTPACK lane)")
    ap.add_argument("--types", default=r"^q_b[01]\d\d$|^q_su30$",
                    help="regex of the types that get die_ft_bands (default: the ruling's b0xx/b1xx blocks + su30)")
    ap.add_argument("--layers", nargs="*", default=["M4", "M6"])
    ap.add_argument("--keep-turns", action=argparse.BooleanOptionalAction, default=True,
                    help="ports of turn slots keep their windows (anchors), default on")
    ap.add_argument("--v-layers", nargs="*", default=["M5", "M7"])
    ap.add_argument("--die-share", type=float, default=1.0)
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    raw = json.loads((src / "die_plan.json").read_text())
    P = S.Plan(copy.deepcopy(raw), src / "die_plan.json")
    T = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    ports = {p["id"]: p for p in raw["ports"]}
    rep = dict(src=str(src), rows=[], moved=0, anchored=[], unaligned=[], bands={})

    def rect(n):
        p = parts[n]
        w, h = T[p["type"]]["outline_um"]
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        return p["origin_um"][0], p["origin_um"][1], p["origin_um"][0] + w, p["origin_um"][1] + h

    def slot_of(part, bus):
        t = T[parts[part]["type"]]
        for s in t.get("ft_slots", []) or []:
            if bus in (s["name"] + "_i", s["name"] + "_o"):
                return s
        return None

    new_win = {}
    for y0 in a.row:
        row = sorted([n for n in parts if abs(parts[n]["origin_um"][1] - y0) < 1e-3], key=lambda n: parts[n]["origin_um"][0])
        h = T[parts[row[0]]["type"]]["outline_um"][1]
        y1 = y0 + h
        members = set(row)
        for n in parts:     # spanning anchors (root): face overlaps the row
            x0_, ya, x1_, yb = rect(n)
            if n not in members and n in a.fixed and ya <= y0 + 1e-3 and yb >= y1 - 1e-3:
                members.add(n)
        seam_ports = {}
        for pid, pr in ports.items():
            if pr.get("face") not in ("E", "W"):
                continue
            s_, d_ = pr["src"]["part"], pr["dst"]["part"]
            if s_ in members and d_ in members and s_ != S.DIE_PART:
                xs = rect(s_)[2] if pr["face"] == "E" else rect(s_)[0]
                lo, hi = sorted(pr["window_um"])
                if lo >= y0 - 1e-3 and hi <= y1 + 1e-3:
                    seam_ports[pid] = round(xs, 3)
        # chains along lanes
        nxt = {}
        for lid, ln in P.lanes.items():
            ps = ln["ports"]
            for pa, pb in zip(ps, ps[1:]):
                if pa in seam_ports and pb in seam_ports:
                    part = ports[pa]["dst"]["part"]
                    if part in a.fixed:
                        continue
                    s = slot_of(part, ports[pa]["dst"]["bus"])
                    if s and s["in_face"] in "EW" and s["out_face"] in "EW" and s["in_face"] != s["out_face"]:
                        nxt[pa] = pb
        prev = {v: k for k, v in nxt.items()}
        chains = []
        for pid in seam_ports:
            if pid in prev:
                continue
            c = [pid]
            while c[-1] in nxt:
                c.append(nxt[c[-1]])
            chains.append(c)
        occ = defaultdict(list)       # seam x -> [(lo, hi)]

        def is_ft(c):
            for pid in c:
                for side in ("src", "dst"):
                    e = ports[pid][side]
                    if e["part"] in parts and e["part"] not in a.fixed and slot_of(e["part"], e["bus"]):
                        return True
            return False

        def length(c):
            return max(abs(ports[p]["window_um"][1] - ports[p]["window_um"][0]) for p in c)

        def free(c, lo, hi):
            for p in c:
                for a_, b_ in occ[seam_ports[p]]:
                    if lo < b_ + GAP - 1e-6 and a_ < hi + GAP - 1e-6:
                        return False
            return True

        def put(c, lo, hi):
            for p in c:
                occ[seam_ports[p]].append((lo, hi))
                new_win[p] = [lo, hi]

        anchored, ftc, rest = [], [], []
        def turn_end(p):
            """port feeding / fed by a turn slot (E/W <-> N/S) of a row partition: its window stays, so the turn's
            stations (sited for that corner) keep their hop lengths."""
            for side in ("src", "dst"):
                e = ports[p][side]
                if e["part"] in parts and e["part"] not in a.fixed:
                    s = slot_of(e["part"], e["bus"])
                    if s and (s["in_face"] in "EW") != (s["out_face"] in "EW"):
                        return True
            return False

        for c in chains:
            fx = [p for p in c if ports[p]["src"]["part"] in a.fixed or ports[p]["dst"]["part"] in a.fixed
                  or (a.keep_turns and turn_end(p))]
            (anchored if fx else ftc if is_ft(c) else rest).append((c, fx))
        for c, fx in anchored:
            ws = {tuple(sorted(ports[p]["window_um"])) for p in fx}
            lo, hi = sorted(ws)[0]
            if len(ws) > 1:
                rep["unaligned"].append(dict(chain=c, why="anchored ports with different windows", windows=sorted(ws)))
                for p in c:
                    w = sorted(ports[p]["window_um"]) if p in fx else [lo, hi]
                    occ[seam_ports[p]].append(tuple(w))
                    new_win[p] = list(w)
            else:
                put(c, lo, hi)
            rep["anchored"].append(dict(chain=c, window=[lo, hi]))
        def place(c, top_down):
            L = length(c)
            cands = []
            for p in c:
                for a_, b_ in occ[seam_ports[p]]:
                    cands += [a_ - GAP, b_ + GAP]
            if top_down:
                vs = sorted({snap(v, "down") for v in cands + [y1 - MARGIN] if v - L >= y0 + MARGIN - 1e-6}, reverse=True)
                spans = [(snap(v - L, "down"), v) for v in vs]
            else:
                vs = sorted({snap(v, "up") for v in cands + [y0 + MARGIN] if v + L <= y1 - MARGIN + 1e-6})
                spans = [(v, snap(v + L, "up")) for v in vs]
            for lo, hi in spans:
                if lo >= y0 + MARGIN - 1e-6 and hi <= y1 - MARGIN + 1e-6 and free(c, lo, hi):
                    put(c, lo, hi)
                    return True
            return False

        order = sorted([(c, True) for c, _ in ftc] + [(c, False) for c, _ in rest],
                       key=lambda x: (-len(x[0]), not x[1], -length(x[0])))
        for c, top_down in order:
            if place(c, top_down):
                continue
            ok = all(place([p], top_down) for p in c)
            rep["unaligned"].append(dict(chain=c, why="no common free window; ports placed one by one" if ok else
                                         "NO FREE WINDOW (port left unplaced)", length=length(c)))
            for p in c:
                if p not in new_win:
                    occ[seam_ports[p]].append(tuple(sorted(ports[p]["window_um"])))
        rep["rows"].append(dict(y0=y0, h=h, members=sorted(members), seam_ports=len(seam_ports), chains=len(chains),
                                anchored=len(anchored), ft_chains=len(ftc), other=len(rest)))
    for pid, w in new_win.items():
        if [round(v, 3) for v in sorted(ports[pid]["window_um"])] != [round(v, 3) for v in w]:
            rep["moved"] += 1
        ports[pid]["window_um"] = [round(w[0], 3), round(w[1], 3)]
    # bands + stations, per type (type frame; G0 proves every instance identical)
    rowparts = [n for n in parts if any(abs(parts[n]["origin_um"][1] - y) < 1e-3 for y in a.row) and n not in a.fixed]
    done = set()
    for n in sorted(rowparts):
        tn = parts[n]["type"]
        if tn in done or not re.search(a.types, tn):
            continue
        done.add(tn)
        t = T[tn]
        w, h = t["outline_um"]
        oy = parts[n]["origin_um"][1]
        ys, straight = [], {}
        for pid, pr in ports.items():
            for side in ("src", "dst"):
                if pr[side]["part"] != n or pr.get("face") not in ("E", "W"):
                    continue
                s = slot_of(n, pr[side]["bus"])
                if not s:
                    continue
                lo, hi = sorted(pr["window_um"])
                ys += [lo - oy, hi - oy]
                if s["in_face"] in "EW" and s["out_face"] in "EW":
                    straight.setdefault(s["name"], []).append((lo + hi) / 2 - oy)
        xs = []
        for pid, pr in ports.items():
            for side in ("src", "dst"):
                if pr[side]["part"] != n or pr.get("face") not in ("N", "S"):
                    continue
                if slot_of(n, pr[side]["bus"]):
                    lo, hi = sorted(pr["window_um"])
                    xs += [lo - parts[n]["origin_um"][0], hi - parts[n]["origin_um"][0]]
        if not ys and not xs:
            continue
        t["die_ft_bands"] = []
        if ys:
            span = [snap(max(0.0, min(ys) - MARGIN)), snap(min(h, max(ys) + MARGIN))]
            t["die_ft_bands"].append(dict(dir="EW", span_um=span, layers=list(a.layers), die_share=a.die_share,
                                          note="DIE-FT-HBM 10-25: die-owned FT band (COORD DIE GRT RULINGS 11:29)"))
        if xs:
            if parts[n].get("orient", "R0") in ("MY", "R180"):
                xs = [w - v for v in xs]
            xspan = [snap(max(0.0, min(xs) - MARGIN)), snap(min(w, max(xs) + MARGIN))]
            t["die_ft_bands"].append(dict(dir="NS", span_um=xspan, layers=list(a.v_layers), die_share=a.die_share,
                                          note="DIE-FT-HBM 10-25: die-owned FT stripe under the N/S ft windows"))
        span = t["die_ft_bands"][0]["span_um"]
        mv = 0
        for s in t.get("ft_slots", []) or []:
            cs = straight.get(s["name"])
            if cs and len(cs) == 2 and abs(cs[0] - cs[1]) < 1.0 and s.get("regs_um"):
                yc = round(cs[0], 3)
                s["regs_um"] = [[r[0], yc] if r[0] > 1e-6 and r[0] < w - 1e-6 else [r[0], yc] for r in s["regs_um"]]
                mv += 1
        rep["bands"][tn] = dict(bands=[(b["dir"], b["span_um"]) for b in t["die_ft_bands"]], straight_slots_restationed=mv)
    out.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.name in ("die_plan.json",):
            continue
        d = out / f.name
        if f.is_dir():
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(f, d)
        else:
            shutil.copy2(f, d)
    raw["die"]["label"] = raw["die"].get("label", "") + " | die_ft_band (DIE-FT-HBM 10-25): aligned row FT chains + die-owned M4/M6 bands"
    (out / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
    (out / "die_ft_band_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(moved=rep["moved"], rows=rep["rows"], unaligned=len(rep["unaligned"]),
                          bands=rep["bands"]), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
