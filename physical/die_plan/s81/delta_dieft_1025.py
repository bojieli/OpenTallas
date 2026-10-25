#!/usr/bin/env python3
"""DIE-FT-S81 10-25 (COORD DIE GRT RULINGS 11:29, S81 items 1+2): slice-L1 feedthrough relief for the die global route.

DIE-GRT-COLLECT (it5, M4-M7 signals, 0.75 derate): s81 4.36M overflow, 96 % in the ot_s81sl_leaf L1 partitions next
to C: every L1 seam packs its ft / leaf bus windows into the low end of the face (S face x 6-833 of 1443 = 58 %,
E/W faces y 6-487 + 1112-1221), straight over the leaf hard-core field, and the five leaf cores ve_m / ve_s / vn_a /
vn_b / vs declare OBS M1-M7 in their 10-24 planning abstracts, so the die keeps only its 25 % share of M4-M7 there
and nothing on M5/M7 (V) over 62 % of the columns.

(2) M5 core cap (zero area, no re-hardening): every kit of those five cores already routes M2-M5
    (MAX_ROUTING_LAYER = M5, core PDN M1/M2/M5 -- kits-spare/lb ve_m/ve_s, s81-cores-split vn_a_t42,
    s81-cores3-sw vn_b_f6s/f6c, s81-cores3-nk vs_lfp; none has a signed view yet).  The planning abstracts
    cores/leaf/lef/<core>{,_xm,_lfp}.lef drop their M6/M7 OBS (pins are M3-M5 only) and hard_cores[].obs_max = M5 in
    every type that places them, so M6 (H) / M7 (V) run over them, as over every other leaf core (M4/M5 caps).
(1) Seam re-lay (zero area): every abutted seam of an L1 partition (L1|C, L1|L3, L1|L1) re-lays ALL of its port
    windows over the whole face: same order, one common pin density (window length = bits / layers x u), equal gaps,
    symmetric 6.144-um margins (mirror invariant, so MY / R0 instances of a shared type get identical type-frame
    windows), both ends of every port identical (port window_um + the two types' bus / ft slot windows).  A seam whose
    neighbour type has another instance on a seam outside this set stays as is (consistency).  The N-S / E-W bundles
    then spread over the full face and cross the (M5-capped) core field on M7 / M6, plus M5 / M4 in the core gaps.
    The ft stations of every type with a moved window are re-sited by tools/die_plan/ft_corridor.py (straight / Z
    corridors over the cores, registers in the inter-core gaps, station counts unchanged = 0 added cycles).
(3) L1 row growth: NOT applied (only if the die GRT on this delta still overflows).

Idempotent on its own output (re-lay is a fixed point; LEF edit / obs_max are idempotent).

    python3 physical/die_plan/s81/delta_dieft_1025.py [PLAN] [--report R.json] [--no-corridor]
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE.parents[2]
sys.path[:0] = [str(HERE), str(W), str(W / "tools" / "die_plan")]
import compact_plan  # noqa: E402

CAP_CORES = ("ot_s81sl_ve_m", "ot_s81sl_ve_s", "ot_s81sl_vn_a", "ot_s81sl_vn_b", "ot_s81sl_vs", "ot_s81sl_vq")
MARGIN = 6.144
FILL = 0.88                 # window share of the face span; the rest = equal gaps
OPP = dict(N="S", S="N", E="W", W="E")


# ------------------------------------------------------------------------------------------------ (2) M5 core cap
def cap_lefs(raw):
    done = []
    paths = set()
    for t in raw["partition_types"].values():
        for h in t.get("hard_cores", []) or []:
            if h.get("module") in CAP_CORES:
                if h.get("obs_max") != "M5":
                    h["obs_max"] = "M5"
                if h.get("lef"):
                    paths.add(h["lef"])
    for rel in sorted(paths):
        p = W / rel
        if not p.is_file():
            raise SystemExit(f"missing core LEF {rel}")
        txt = p.read_text()
        pins_hi = re.search(r"PIN .*?END \S+", txt, re.S)
        body = txt.split("  OBS", 1)
        assert len(body) == 2, rel
        pin_part = body[0]
        assert not re.search(r"LAYER\s+M[6-9]\s*;", pin_part), f"{rel}: pins above M5"
        obs = re.sub(r"    LAYER M[6-9] ;\n(      RECT[^\n]*\n)+", "", body[1])
        new = body[0] + "  OBS" + obs
        if new != txt:
            p.write_text(new)
        done.append(rel)
    return done


# ---------------------------------------------------------------------------------------------- (1) seam re-lay
def rect(raw_types, p):
    w, h = raw_types[p["type"]]["outline_um"]
    o = p.get("orient", "R0")
    assert o in ("R0", "MY"), (p["name"], o)
    return p["origin_um"][0], p["origin_um"][1], p["origin_um"][0] + w, p["origin_um"][1] + h


def tface(p, df):
    return {"E": "W", "W": "E"}.get(df, df) if p.get("orient", "R0") == "MY" else df


def to_type(raw_types, p, df, a, b):
    """die-frame window [a,b] on die face df -> type-frame window on the type face."""
    x0, y0, x1, y1 = rect(raw_types, p)
    if df in "EW":
        return [round(a - y0, 3), round(b - y0, 3)]
    if p.get("orient", "R0") == "MY":
        return [round(x1 - b, 3), round(x1 - a, 3)]
    return [round(a - x0, 3), round(b - x0, 3)]


def from_type(raw_types, p, df, a, b):
    x0, y0, x1, y1 = rect(raw_types, p)
    if df in "EW":
        return [round(y0 + a, 3), round(y0 + b, 3)]
    if p.get("orient", "R0") == "MY":
        return [round(x1 - b, 3), round(x1 - a, 3)]
    return [round(x0 + a, 3), round(x0 + b, 3)]


def type_win_ref(t, bus):
    """(dict, key) holding the type-frame window of bus on its type (bus window / slot in/out window)."""
    for b in t.get("buses", []) or []:
        if b["name"] == bus:
            return b, "window_um"
    for s in t.get("ft_slots", []) or []:
        if bus == s["name"] + "_i":
            return s, "in_window_um"
        if bus == s["name"] + "_o":
            return s, "out_window_um"
    return None, None


def layout(items, span):
    """items [(port, nbits_per_layer)] in face order -> [[lo, hi]] in a [0, span] frame."""
    use = span - 2 * MARGIN
    tot = sum(n for _, n in items)
    k = len(items)
    u = FILL * use / tot
    g = (1 - FILL) * use / (k - 1) if k > 1 else 0.0
    out, c = [], MARGIN + (((1 - FILL) * use / 2) if k == 1 else 0.0)
    for _, n in items:
        ln = n * u
        out.append([round(c, 3), round(c + ln, 3)])
        c += ln + g
    return out


def seams(raw):
    PA = {p["name"]: p for p in raw["partitions"]}
    S = defaultdict(list)
    for pr in raw["ports"]:
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if a not in PA or b not in PA or not (a.endswith("_L1") or b.endswith("_L1")):
            continue
        if "window_um" not in pr:
            continue
        S[(a, b, pr["face"]) if a < b else (b, a, OPP[pr["face"]])].append(pr)
    return PA, S


def relay(raw):
    T = raw["partition_types"]
    PA, S = seams(raw)
    inst = defaultdict(list)
    for p in raw["partitions"]:
        inst[p["type"]].append(p["name"])
    seam_parts = set()
    for (a, b, f) in S:
        seam_parts |= {(a, f), (b, OPP[f])}
    # consistency: a neighbour type with another instance whose same type face is NOT on a re-laid seam -> skip
    skip = []
    for key in list(S):
        a, b, f = key
        ok = True
        for part, df in ((a, f), (b, OPP[f])):
            tf = tface(PA[part], df)
            for other in inst[PA[part]["type"]]:
                if other == part:
                    continue
                odf = {"E": "W", "W": "E"}.get(tf, tf) if PA[other].get("orient", "R0") == "MY" else tf
                if (other, odf) not in seam_parts:
                    ok = False
        if not ok:
            skip.append(key)
    for key in skip:
        del S[key]
    newtype = defaultdict(dict)       # (type, bus) -> window, conflict check
    rep = dict(seams=[], skipped=[f"{a}|{b}/{f}" for a, b, f in skip])
    changed_types = set()
    for (a, b, f), prs in sorted(S.items()):
        # canonical frame: the L1 side (W/S-most L1 on L1|L1 seams)
        can = a if a.endswith("_L1") else b
        cdf = f if can == a else OPP[f]
        ra, rb = rect(T, PA[a]), rect(T, PA[b])
        span = (min(ra[2], rb[2]) - max(ra[0], rb[0])) if f in "NS" else (min(ra[3], rb[3]) - max(ra[1], rb[1]))
        span = round(span, 3)
        full = (rect(T, PA[can])[2] - rect(T, PA[can])[0]) if f in "NS" else (rect(T, PA[can])[3] - rect(T, PA[can])[1])
        assert abs(span - full) < 1e-3, (a, b, f, span, full)
        cur = []
        for pr in prs:
            lo, hi = sorted(pr["window_um"])
            tw = to_type(T, PA[can], cdf, lo, hi)
            cur.append((tw[0], pr))
        cur.sort(key=lambda x: x[0])
        items = [(pr, -(-int(pr["width"]) // len(pr["layers"]))) for _, pr in cur]
        wins = layout(items, span)
        before = [round(x[0], 1) for x in cur]
        for (pr, _), tw in zip(items, wins):
            dw = from_type(T, PA[can], cdf, *tw)
            pr["window_um"] = dw
            for side in ("src", "dst"):
                part = pr[side]["part"]
                p = PA[part]
                df = pr["face"] if side == "src" else OPP[pr["face"]]
                t = T[p["type"]]
                ref, key = type_win_ref(t, pr[side]["bus"])
                if ref is None:
                    continue
                w2 = to_type(T, p, df, *dw)
                k = (p["type"], pr[side]["bus"])
                if k in newtype and any(abs(u - v) > 0.0015 for u, v in zip(newtype[k], w2)):
                    raise SystemExit(f"type window conflict {k}: {newtype[k]} vs {w2} ({part})")
                newtype[k] = w2
                if ref.get(key) != w2:
                    ref[key] = w2
                    changed_types.add(p["type"])
        lo_dens = max(n / (w[1] - w[0]) for (_, n), w in zip(items, wins))
        rep["seams"].append(dict(seam=f"{a}|{b}/{f}", ports=len(prs), bits=sum(int(p["width"]) for p in prs),
                                 span_um=span, pins_per_um_per_layer=round(lo_dens, 2),
                                 starts_before=before[:3] + ["..."], starts_after=[w[0] for w in wins][:3] + ["..."]))
    rep["changed_types"] = sorted(changed_types)
    return rep, changed_types


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", nargs="?", default=str(HERE / "die_plan.json"))
    ap.add_argument("--report", default=str(HERE / "dieft_1025_report.json"))
    ap.add_argument("--no-corridor", action="store_true")
    ap.add_argument("--no-relay", action="store_true", help="variant: (2) M5 core cap only")
    ap.add_argument("--out", help="write the plan here (default: in place)")
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    rep = dict(lefs=cap_lefs(raw))
    changed = set()
    if not a.no_relay:
        r, changed = relay(raw)
        rep.update(r)
    if changed and not a.no_corridor:
        import ft_corridor
        types = sorted(tn for tn in changed if raw["partition_types"][tn].get("ft_slots"))
        rep["corridor"] = ft_corridor.place(raw, types)
    Path(a.out or a.plan).write_text(compact_plan.dumps(raw))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"lefs {len(rep['lefs'])}, seams {len(rep.get('seams', []))} (skipped {len(rep.get('skipped', []))}), "
          f"types changed {len(changed)}")


if __name__ == "__main__":
    main()
