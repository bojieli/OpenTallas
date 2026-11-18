"""band_capacity.py -- landing band capacity (HEAD-PLAN-R4 11-17, COORD: G0 band-capacity check on all dies).

hd_lep0N lost two GPL runs to undersized landing bands found one at a time (stage:wdq_bank3 shared by two 256-cell groups,
stage:pout_r2 with no legal site).  This tool measures every band at once.

  measure   python3 tools/die_plan/band_capacity.py measure LANDING_TCL NETLIST_V SYNTH_STAT OUT_JSON [--type TN]
            replays landing_placement.tcl's selection offline on the synthesized netlist:
              * group order = cland_groups order (+ optional groups); an instance claimed earlier is skipped (cland_done);
              * prefix in cland_native_leaf_regex -> that regex (+ cland_native_ff_only: DFF* only); non-word prefix ->
                (^|[/.])P[/.]; word prefix -> any non-leaf path component equal to P;
              * only DFF|DHL|DLL|SDF masters are placed; need = cell area / cland_native_tag_density for the tag, else the
                proc's own ceil(w/0.4/site)*site*h (40 % fill sizing);
              * ring tags with >= 2 rects (cland_multi) sum their rects; bands shared by several groups sum their needs.
            fill = need / band area.  Cell areas from synth_stat.txt (area / count per master; ASAP7 row 0.27, site 0.054).
            Write OUT_JSON as PLANDIR/band_fill/<type>.json to feed G0.

  G0        check(P, R, plan_dir): reads PLANDIR/band_fill/*.json (any die); a band's area comes from the plan's CURRENT
            native_stage_groups rect_um for stage:* tags (so growing a band in the plan clears it without re-measuring),
            else the measured rect.  fill > 0.7 WARN (advisory), fill > 1.0 ERROR (the band cannot hold its cells).
            No sidecar: nothing is reported (unmeasured).
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

WARN_FILL, ERROR_FILL = 0.7, 1.0
SITE, ROW = 0.054, 0.27
FF_RE = re.compile(r"DFF|DHL|DLL|SDF")


def parse_tcl(path):
    t = open(path).read().splitlines()
    groups, native, ff_only, dens = [], {}, set(), {}
    on = False
    g_re = re.compile(r"^\s*\{(\{.*\}|\S+) \{([-0-9. ]+)\} (\S+)\}\s*$")
    for ln in t:
        if ln.startswith("set cland_groups {") or ln.startswith("set cland_optional_groups {"):
            on = True
            continue
        if on and ln.strip() == "}":
            on = False
            continue
        if on:
            m = g_re.match(ln)
            if m:
                p = m.group(1)
                if p.startswith("{") and p.endswith("}"):
                    p = p[1:-1]
                groups.append((p, tuple(float(v) for v in m.group(2).split()), m.group(3)))
            continue
        m = re.match(r"^dict set ::cland_native_leaf_regex \{(.*)\} \{(.*)\}\s*$", ln)
        if m:
            native[m.group(1)] = m.group(2)
            continue
        m = re.match(r"^dict set ::cland_native_ff_only \{(.*)\} ", ln)
        if m:
            ff_only.add(m.group(1))
            continue
        m = re.match(r"^dict set ::cland_native_tag_density \{(.*)\} ([0-9.]+)", ln)
        if m:
            dens[m.group(1)] = float(m.group(2))
    return groups, native, ff_only, dens


def parse_areas(path):
    best = {}
    r = re.compile(r"^\s+(\d+)\s+([0-9.]+)\s+(?:\S+\s+\S+\s+)?(\S+_ASAP7_75t_\S+)\s*$")
    for ln in open(path):
        m = r.match(ln)
        if m:
            n, a, c = int(m.group(1)), float(m.group(2)), m.group(3)
            if n and (c not in best or n > best[c][0]):
                best[c] = (n, a / n)
    return {c: v[1] for c, v in best.items()}


def parse_netlist(path):
    r = re.compile(r"^\s*(\S+_ASAP7_75t_\S+)\s+(\\\S+|[A-Za-z_]\S*)\s*\(")
    out = []
    for ln in open(path):
        m = r.match(ln)
        if m:
            nm = m.group(2)
            if nm.startswith("\\"):
                nm = nm[1:]
            out.append((nm.replace("[", "\\[").replace("]", "\\]"), m.group(1)))
    return out


def literal_head(rx):
    """the longest literal text a match must contain (unescaped), '' when none"""
    s, i, out = rx.lstrip("^"), 0, []
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append(s[i + 1])
            i += 2
            continue
        if c in "()[]?*+|{}.$":
            break
        out.append(c)
        i += 1
    return "".join(out)



def measure(tcl, net, stat, type_name=None):
    groups, native, ff_only, dens = parse_tcl(tcl)
    area = parse_areas(stat)
    insts = parse_netlist(net)
    comp_idx = defaultdict(list)
    for k, (nm, _) in enumerate(insts):
        for g in set(nm.replace(".", "/").split("/")[:-1]):
            comp_idx[g].append(k)
    done = set()
    per_rect = defaultdict(lambda: {"need": 0.0, "ff_area": 0.0, "nff": 0, "groups": [], "tags": set()})
    missing = set()
    multi = defaultdict(list)
    for p, rect, tag in groups:
        if tag.startswith("ring:"):
            multi[tag].append(rect)
    for p, rect, tag in groups:
        if p in native:
            rx, head = re.compile(native[p]), literal_head(native[p])
            cand = [k for k, (nm, _) in enumerate(insts) if (not head or head in nm) and rx.search(nm)]
            if p in ff_only:
                cand = [k for k in cand if insts[k][1].startswith("DFF")]
        elif not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p):
            rx, head = re.compile(r"(^|[/.])%s[/.]" % p), literal_head(p)
            cand = [k for k, (nm, _) in enumerate(insts) if (not head or head in nm) and rx.search(nm)]
        else:
            cand = comp_idx.get(p, [])
        rects = multi[tag] if len(multi.get(tag, [])) >= 2 else [rect]
        e = per_rect[tuple(tuple(r) for r in rects)]
        n_ff = 0
        for k in cand:
            if k in done:
                continue
            m = insts[k][1]
            if not FF_RE.search(m):
                continue
            done.add(k)
            a = area.get(m)
            if a is None:
                missing.add(m)
                continue
            e["need"] += a / dens[tag] if tag in dens else math.ceil(a / ROW / 0.4 / SITE - 1e-9) * SITE * ROW
            e["ff_area"] += a
            e["nff"] += 1
            n_ff += 1
        e["groups"].append({"prefix": p[:160], "tag": tag, "nff": n_ff})
        e["tags"].add(tag)
    rows = []
    for key, e in per_rect.items():
        ba = sum((r[2] - r[0]) * (r[3] - r[1]) for r in key)
        rows.append({"rects": [list(r) for r in key], "tags": sorted(e["tags"]), "band_um2": round(ba, 3), "nff": e["nff"],
                     "need_um2": round(e["need"], 3), "ff_area_um2": round(e["ff_area"], 3),
                     "fill": round(e["need"] / ba, 4) if ba > 0 else None, "groups": e["groups"]})
    rows.sort(key=lambda r: -(r["fill"] or 0))
    return {"schema": "opentallas.band_fill.v1", "type": type_name, "tcl": str(tcl), "netlist": str(net),
            "n_groups": len(groups), "n_rects": len(rows), "n_insts": len(insts), "missing_area_masters": sorted(missing),
            "over_warn": sum(1 for r in rows if (r["fill"] or 0) > WARN_FILL),
            "over_error": sum(1 for r in rows if (r["fill"] or 0) > ERROR_FILL), "rows": rows}


def _area(rects):
    return sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects)


def _reader_box(t, bus, groups):
    """box_um of the reader START stage behind group u_cland_reader_start_<bus>_<i>, None when not declared"""
    br = ((((t or {}).get("clock") or {}).get("landing_reader_start") or {}).get("branches") or {}).get(bus) or {}
    for g in groups:
        m = re.search(r"_(\d+)$", g.get("prefix", ""))
        st = br.get("stages") or []
        if m and int(m.group(1)) < len(st) and st[int(m.group(1))].get("box_um"):
            return [float(v) for v in st[int(m.group(1))]["box_um"]]
    return None


def plan_fill(t, doc):
    """[(tags, need, area, fill, rects, source)] for one measured type against the plan type dict t."""
    ns = ((((t or {}).get("clock") or {}).get("landing_contract") or {}).get("native_stage_groups") or {}).get("groups") or []
    by_tag = defaultdict(list)
    for g in ns:
        r = [float(v) for v in g["rect_um"]]
        if r not in by_tag[g["tag"]]:
            by_tag[g["tag"]].append(r)
    out = []
    for row in doc.get("rows", []):
        tags = row["tags"]
        rects, src = [list(r) for r in row["rects"]], "measured"
        if tags and all(tg.startswith("stage:") and len(by_tag.get(tg, ())) == 1 for tg in tags):
            cur = []
            for tg in tags:
                if by_tag[tg][0] not in cur:
                    cur.append(by_tag[tg][0])
            if len(cur) == len(rects):
                rects, src = cur, "plan"
        if len(tags) == 1 and tags[0].startswith("reader-start:") and len(rects) == 1:
            box = _reader_box(t, tags[0][len("reader-start:"):], row.get("groups") or [])
            if box:                                      # plan box_um (BAND-CAP opt-in) around the measured centre
                cx, cy = (rects[0][0] + rects[0][2]) / 2, (rects[0][1] + rects[0][3]) / 2
                rects, src = [[cx - box[0] / 2, cy - box[1] / 2, cx + box[0] / 2, cy + box[1] / 2]], "plan"
        a = _area(rects)
        out.append((tags, row["need_um2"], a, (row["need_um2"] / a) if a > 0 else float("inf"), rects, src))
    return out


def check(P, R, plan_dir=None, max_msgs=40):
    """G0 band_capacity: WARN fill > 0.7, ERROR fill > 1.0, from PLANDIR/band_fill/*.json; silent when unmeasured."""
    summ = dict(measured_types=[], bands=0, over_warn=0, over_error=0, worst=None)
    d = Path(plan_dir) / "band_fill" if plan_dir else None
    if d is None or not d.is_dir():
        return summ
    n = 0
    for f in sorted(d.glob("*.json")):
        try:
            doc = json.loads(f.read_text())
        except (OSError, ValueError) as ex:
            R.warn("band_capacity", f"{f.name}: unreadable band fill sidecar ({ex})")
            continue
        tn = doc.get("type") or f.stem
        t = P.types.get(tn) if hasattr(P, "types") else None
        if t is None:
            R.warn("band_capacity", f"{f.name}: type {tn} not in the plan")
            continue
        summ["measured_types"].append(tn)
        for tags, need, a, fill, rects, src in plan_fill(t, doc):
            summ["bands"] += 1
            if summ["worst"] is None or fill > summ["worst"]["fill"]:
                summ["worst"] = dict(type=tn, tags=tags, fill=round(fill, 4))
            if fill <= WARN_FILL:
                continue
            lvl = "error" if fill > ERROR_FILL else "warn"
            summ["over_" + lvl] += 1
            n += 1
            if n > max_msgs:
                continue
            msg = (f"type {tn} band {','.join(tags)[:80]} {[round(v, 2) for v in rects[0]]}{'+' if len(rects) > 1 else ''}: "
                   f"fill {fill:.3f} (need {need:.1f} um2 / band {a:.1f} um2, {src} rect) > "
                   f"{ERROR_FILL if lvl == 'error' else WARN_FILL} -- grow the band (no legal site / GPL OT_CLAND stop)")
            (R.err if lvl == "error" else R.warn)("band_capacity", msg, type=tn)
    return summ


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("tcl"); m.add_argument("netlist"); m.add_argument("synth_stat"); m.add_argument("out")
    m.add_argument("--type", default=None)
    a = ap.parse_args(argv)
    res = measure(a.tcl, a.netlist, a.synth_stat, a.type)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print("BAND_FILL type", a.type, "groups", res["n_groups"], "rects", res["n_rects"], "insts", res["n_insts"],
          "over%.1f" % WARN_FILL, res["over_warn"], "over%.1f" % ERROR_FILL, res["over_error"],
          "missing_area", len(res["missing_area_masters"]))
    for r in res["rows"][:40]:
        print("%.3f nff %5d band %8.2f %s" % (r["fill"] or 0, r["nff"], r["band_um2"], ",".join(r["tags"])[:80]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
