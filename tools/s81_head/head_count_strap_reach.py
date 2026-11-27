#!/usr/bin/env python3
"""C-STRAP-REACH (HEAD-INT-R2, COORD 11-26): seat every HEAD CA / count strap group at its own load cluster, and check it.

A HEAD type's count straps (types[].count_straps, tied at the parent) feed the clock-landing instances of the published RTL:
  strap_ca_k_<g>   (6 bits) -> .strap_k of  u_cland_<g>      : the landing ring of group <g>; its load cluster is the planned
                                                              landing-contract pins (fclk_in_<g>, cland_fstart_in_<g>, ready/fault) that the
                                                              instance body names
  strap_ca_efall / strap_ca_pad (1 bit) -> .strap_efall/.strap_pad of u_cland_origin : the landing start block, load cluster =
                                                              clock.start_capture_um (else the cland_tstart_in landing pin)
head_count_strap_sites.apply placed ALL of them around one anchor (first landing_ring_bank / clock.tap_um), so a type whose
groups land on different faces keeps all but one group 400-1400 um from its loads (lep0N coll_i3 1404 um, lep0N_w coll_i1 980 um,
n3_turn / str / transit d-side, efall and pad).  Anchors here are derived from the type's own plan + published RTL.

  group_anchors(t, sv_text)      -> {strap name: (x, y, source)}
  group_findings(t, anchors)     -> rows {type-level strap, seat, anchor, dist, faces, status}
      status REPRODUCE (some seat > LIMIT_UM Manhattan from its anchor, or seat and anchor on opposite die faces), PASS, NOSEAT
      (strap has no sites_um: the pin is placed freely), NOEVIDENCE (no anchor derivable)
  python3 -I head_count_strap_reach.py census PLAN.json [--pub DIR] [--types a,b]    # table, exit 1 when any REPRODUCE
  python3 -I head_count_strap_reach.py check  PLAN.json [--pub DIR]                  # blocking: exit 1 on REPRODUCE
"""
import argparse
import json
import re
import sys
from pathlib import Path

LIMIT_UM = 405.0        # the C-LEG405 hop rule
OPP_MIN_UM = 150.0      # opposite-face flag only counts beyond this Manhattan distance (shim types are narrower than the faces)
STMT = re.compile(r"\n\s*(?:\(\*[^)]*\)\s*)?(\w+)\s+(?:#\((?:[^()]|\([^()]*\))*\)\s*)?(\w+)\s*\((.*?)\);", re.S)


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def face(p, w, h):
    """nearest die face of point p: W / E / S / N"""
    d = {"W": p[0], "E": w - p[0], "S": p[1], "N": h - p[1]}
    return min(d, key=lambda k: (d[k], k))


def opposite(fa, fb):
    return {fa, fb} in ({"W", "E"}, {"S", "N"})


def group_anchors(t, sv_text):
    """{count strap name: (x, y, source)} from the type's landing contract / start_capture_um and the published RTL's landing instances"""
    ck = t.get("clock") or {}
    pins = {p["name"]: p["xy_um"] for p in (ck.get("landing_contract") or {}).get("pins", []) if p.get("xy_um")}
    out = {}
    for _mod, inst, body in STMT.findall(sv_text):
        ids = set(re.findall(r"\b\w+\b", body))
        m = re.search(r"\.strap_k\((\w+)\)", body)
        if m:
            xs = [pins[i] for i in sorted(ids) if i in pins]
            if xs:
                out[m.group(1)] = (sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs), f"{inst} landing pins x{len(xs)}")
        for key in ("efall", "pad"):
            m = re.search(r"\.strap_%s\((\w+)\)" % key, body)
            if m:
                sc = ck.get("start_capture_um")
                if sc:
                    out[m.group(1)] = (float(sc[0]), float(sc[1]), f"{inst} start_capture_um")
                else:
                    xs = [pins[i] for i in sorted(ids) if i in pins]
                    if xs:
                        out[m.group(1)] = (sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs), f"{inst} landing pins x{len(xs)}")
    return out


def group_findings(t, anchors, limit=LIMIT_UM):
    w, h = t["outline_um"]
    rows = []
    for s in t.get("count_straps") or []:
        name = s["name"]
        a = anchors.get(name)
        sites = [tuple(map(float, xy)) for xy in s.get("sites_um") or []]
        row = dict(strap=name, width=s["width"], anchor=None if a is None else [round(a[0], 3), round(a[1], 3)],
                   source=None if a is None else a[2], seat=None, dmax=None, dmean=None, faces=None)
        if a is None:
            row["status"] = "NOEVIDENCE"
        elif not sites:
            row["status"] = "NOSEAT"
        else:
            d = [_man(p, a) for p in sites]
            cx, cy = sum(p[0] for p in sites) / len(sites), sum(p[1] for p in sites) / len(sites)
            fs, fa = face((cx, cy), w, h), face(a, w, h)
            row.update(seat=[round(cx, 3), round(cy, 3)], dmax=round(max(d), 2), dmean=round(sum(d) / len(d), 2), faces=fs + "/" + fa)
            opp = opposite(fs, fa) and _man((cx, cy), a) > OPP_MIN_UM
            row["opposite_face"] = opp
            row["status"] = "REPRODUCE" if (max(d) > limit or opp) else "PASS"
        rows.append(row)
    return rows


def pub_text(plan_path, t, pub=None):
    pub = Path(pub) if pub else Path(plan_path).resolve().parent / "published"
    f = pub / (t["module"] + ".sv")
    return f.read_text() if f.is_file() else None


def census(raw, plan_path, pub=None, types=None, limit=LIMIT_UM):
    out = {}
    for tn, t in sorted(raw["partition_types"].items()):
        if types and tn not in types:
            continue
        if not t.get("count_straps"):
            continue
        txt = pub_text(plan_path, t, pub)
        out[tn] = None if txt is None else group_findings(t, group_anchors(t, txt), limit)
    return out


def findings_for_pre(raw, plan_path, pub=None, level="WARN", types=None):
    """PRE lines: <level> STRAP-REACH per type with a REPRODUCE group (level FAIL blocks)"""
    out = []
    if not (Path(pub) if pub else Path(plan_path).resolve().parent / "published").is_dir():
        return out
    for tn, rows in census(raw, plan_path, pub, types).items():
        if rows is None:
            out.append(f"WARN STRAP-REACH-UNCHECKED {tn}: no published RTL for module")
            continue
        bad = [r for r in rows if r["status"] == "REPRODUCE"]
        if bad:
            out.append(f"{level} STRAP-REACH {tn}: {len(bad)}/{len(rows)} count strap group(s) seated away from their loads "
                       + "; ".join(f"{r['strap']} dmax {r['dmax']} um {r['faces']}" for r in bad[:6])
                       + f"; fix: head_count_strap_sites.py --reach (C-STRAP-REACH)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["census", "check"])
    ap.add_argument("plan", type=Path)
    ap.add_argument("--pub", type=Path)
    ap.add_argument("--types", default="")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    raw = json.loads(a.plan.read_text())
    res = census(raw, a.plan, a.pub, set(filter(None, a.types.split(","))) or None)
    n_rep = 0
    for tn, rows in res.items():
        if rows is None:
            print(f"{tn}\tNORTL")
            continue
        for r in rows:
            n_rep += r["status"] == "REPRODUCE"
            print("\t".join(str(x) for x in (tn, r["strap"], r["status"], r["dmax"], r["dmean"], r["faces"], r["anchor"], r["source"])))
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")
    print(f"STRAP_REACH groups_reproduce {n_rep}")
    return 1 if n_rep else 0


if __name__ == "__main__":
    sys.exit(main())
