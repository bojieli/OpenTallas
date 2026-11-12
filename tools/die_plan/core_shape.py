#!/usr/bin/env python3
"""CORE-SHAPE-GATE-1 (OWNER 11-11 CORE-SHAPE FREEZE): G0 ERROR `core_shape_change`.

A plan event may MOVE or ROTATE a hard core but may not change its outline.  A plan hard core whose outline matches
none of the SIGNED shapes of the same RTL identity (module name; the plan carries no netlist identity, so the release
tree keys a core design by module + outline + pin-table hash -- here the module's signed records give the shapes) is an
ERROR, unless the plan declares `core_shape_exceptions: [{core, old, new, reason, measured_by}]` for it.  A module with
no signed shape at all (genuinely new RTL) is not an error.

Offline: the signed shapes come from a cached index file (JSON, schema opentallas.core_shape_index.v1), built once on
the hub from the durable signed store by `core_shape.py build-index OUT.json`.

  core_shape.py build-index OUT.json [--store DIR] [--coord-tools DIR] [--main-tree DIR]
  core_shape.py check PLAN.json INDEX.json            (prints violations; exit 1 when any)
  check.py PLAN --core-shape-index INDEX.json         (G0 ERROR [core_shape_change])
"""
import argparse
import json
import os
import re
import sys
import time

INDEX_SCHEMA = "opentallas.core_shape_index.v1"
TOL_NM = 1


def nm(v):
    return int(round(float(v) * 1000))


def rec_keys(top, name):
    """module-name keys of one signed record (same rule as release_tree_plan.rec_keys)"""
    ks = set()
    for v in (top, name):
        if not v:
            continue
        ks.add(v)
        m = re.match(r"^(dp|kr)_(.+)$", v)
        if m:
            ks.add(m.group(2))
            ks.add(re.sub(r"_(lfp|r\d+|c\d+)$", "", m.group(2)))
    return ks


_SUFFIX = re.compile(r"_(cs\d+|bfp|lfp|r\d+|c\d+|native(_[ew])?|pin)$")
_PREFIX = re.compile(r"^(hbc_|kl_|dp_|kr_)")


def base_name(m):
    """module base name: build-variant tags stripped (__cd13 / __v700685 / __vecd4ae, _cs1, _bfp, _lfp, _rN, _cN, _native_e,
    _pin; NOT dsdv_gunit_l1c / l1f_*, which are different cores).  COORD 11-11: closes the name-only gap."""
    m = _PREFIX.sub("", m)
    m = re.sub(r"__[a-z]*[0-9a-f]+$", "", m)
    while True:
        n = _SUFFIX.sub("", m)
        if n == m:
            break
        m = n
    return m


def family(index):
    """{base name: [outline_nm tuples]} of the index (all modules sharing a base name)"""
    fam = {}
    for k, v in index.get("modules", {}).items():
        fam.setdefault(base_name(k), set()).update(tuple(s["outline_nm"]) for s in v)
    return fam


def build_index(store=None, coord_tools=None, log=lambda *a: None, main_tree=None):
    """-> index dict from the signed store (verdict SIGNED, outline known), minus retired / COUNT-REVOKED / DO_NOT_COUNT."""
    ct = coord_tools or os.path.expanduser("~/coord/tools")
    sys.path.insert(0, ct)
    import signed_store as SS
    import release_tree_plan as RTP
    manifest = SS.read_manifest(store)
    recs, mods = [], {}
    for e in manifest:
        if e.get("verdict") != "SIGNED":
            continue
        ol = (e.get("pins") or {}).get("outline_nm")
        if not ol or len(ol) != 2:
            mods.setdefault("_no_outline", 0)
            mods["_no_outline"] += 1
            continue
        s = {k: e["scan"][k] for k in SS.SCAN_FIELDS if k in (e.get("scan") or {})}
        s.setdefault("top", e.get("top"))
        s.setdefault("name", e.get("name"))
        for a in e.get("aliases") or [e.get("origin")]:
            h, p = SS._alias_split(a)
            recs.append(dict(s, path=p, scan_host=h, store_id=e["id"], netlist_sha=e.get("netlist_sha"),
                             _outline=[int(ol[0]), int(ol[1])], _pins_sha=_pins_sha(e.get("pins"))))
    if main_tree:
        # signed views checked into main (S81 cores/views/<m>/signoff.json + pins.json + config.mk DIE_AREA beside it)
        import pathlib
        mrecs = RTP.main_records(pathlib.Path(main_tree))
        k = 0
        for r in mrecs:
            mp = RTP.MAIN_PINS.get(r["path"])
            if mp and mp.get("outline_nm"):
                recs.append(dict(r, _outline=[int(x) for x in mp["outline_nm"]], _pins_sha=_pins_sha(mp)))
                k += 1
        log("main tree: %d signed views, %d with a DIE_AREA" % (len(mrecs), k))
    n0 = len(recs)
    ret = RTP.retired_refs()
    recs, _ = RTP.split_retired(recs, ret)
    recs, _ = RTP.split_revoked(recs, RTP.revoked_rows(), sha=lambda r: r.get("netlist_sha"))
    recs, _ = RTP.split_dnc(recs, RTP.dnc_rows())
    log("records %d -> %d after retired/revoked/do-not-count" % (n0, len(recs)))
    out = {}
    for r in recs:
        for k in rec_keys(r.get("top"), r.get("name")):
            lst = out.setdefault(k, {})
            key = tuple(r["_outline"])
            ent = lst.setdefault(key, dict(outline_nm=list(key), pins_sha=r["_pins_sha"], records=0, ref=None))
            ent["records"] += 1
            ent["ref"] = ent["ref"] or "%s:%s" % (r.get("scan_host"), r.get("path"))
    return dict(schema=INDEX_SCHEMA, generated=time.strftime("%Y-%m-%d %H:%M %Z"), source="signed-store",
                records=len(recs), no_outline_entries=mods.get("_no_outline", 0),
                modules={k: sorted(v.values(), key=lambda x: x["outline_nm"]) for k, v in sorted(out.items())})


def _pins_sha(pins):
    import hashlib
    rows = (pins or {}).get("rows")
    if not isinstance(rows, dict):
        return None
    return hashlib.sha256(json.dumps(sorted([k] + list(v) for k, v in rows.items())).encode()).hexdigest()[:16]


def load_index(path):
    doc = json.loads(open(path).read())
    if doc.get("schema") != INDEX_SCHEMA:
        raise ValueError("%s: not a %s index" % (path, INDEX_SCHEMA))
    return doc


def _fit(a, b, tol=TOL_NM):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _fmt(wh):
    return "%gx%g" % (wh[0], wh[1])


def _exc_index(raw):
    out = {}
    for x in raw.get("core_shape_exceptions") or []:
        out.setdefault(x["core"], []).append(x)
    return out


def cores(raw):
    """[(type, inst, module, (w_nm, h_nm), orient)] of every hard core of a plan"""
    out = []
    for tn, t in sorted(raw.get("partition_types", {}).items()):
        for hc in t.get("hard_cores") or []:
            m = hc.get("module")
            if not m or not hc.get("outline_um"):
                continue
            out.append((tn, hc.get("inst"), m, (nm(hc["outline_um"][0]), nm(hc["outline_um"][1])), hc.get("orient") or "R0"))
    return out


def violations(raw, index, slots=True):
    """-> [dict(module, type, inst, plan_nm, closest_nm, signed_nm[], fits_slot)] for hard cores whose outline matches no
    signed shape of their module and that carry no declared exception.  A core is excepted by its module name, its
    `type/inst` or its inst; the exception's `new` must equal the plan outline."""
    mods = index.get("modules", {})
    exc = _exc_index(raw)
    seen, out = {}, []
    fam = family(index)
    for tn, inst, m, wh, orient in cores(raw):
        sig = [tuple(s["outline_nm"]) for s in mods.get(m, [])]
        via = "module"
        if not sig:
            sig = sorted(fam.get(base_name(m), ()))            # variant family (same base name)
            via = "family " + base_name(m)
        if not sig:
            continue                                           # new RTL: nothing signed to preserve
        if any(_fit(wh, s) for s in sig):
            continue
        ex = [x for k in (m, "%s/%s" % (tn, inst), inst) for x in exc.get(k, [])]
        if any(_fit((nm(x["new"][0]), nm(x["new"][1])), wh) for x in ex):
            continue
        key = (m, wh)
        if key in seen:
            seen[key]["instances"] += 1
            if len(seen[key]["where"]) < 3:
                seen[key]["where"].append("%s/%s" % (tn, inst))
            continue
        near = min(sig, key=lambda s: (abs(s[0] - wh[0]) + abs(s[1] - wh[1]),
                                       abs(s[0] - wh[1]) + abs(s[1] - wh[0])))
        v = dict(module=m, plan_nm=list(wh), orient=orient, closest_nm=list(near), signed_nm=sorted(list(s) for s in sig),
                 instances=1, where=["%s/%s" % (tn, inst)],
                 rotated_match=any(_fit((wh[1], wh[0]), s) for s in sig),
                 declared_exception=bool(ex), via=via)
        seen[key] = v
        out.append(v)
    return out


def coverage(raw, index):
    """modules of the plan with a signed shape (checked) / without (new RTL, or signed with no readable DIE_AREA: not checked)"""
    mods = {c[2] for c in cores(raw)}
    fam = family(index)
    have = sorted(m for m in mods if index.get("modules", {}).get(m) or fam.get(base_name(m)))
    return dict(modules=len(mods), modules_signed_shape=len(have), modules_no_signed_shape=sorted(mods - set(have)))


def message(v):
    return ("%s: plan outline %s matches no signed shape %s (closest %s%s)%s; declare core_shape_exceptions or re-point to a signed shape"
            % (v["module"], _fmt([x / 1000 for x in v["plan_nm"]]),
               "[" + ", ".join(_fmt([x / 1000 for x in s]) for s in v["signed_nm"][:4]) + ("..." if len(v["signed_nm"]) > 4 else "") + "]",
               _fmt([x / 1000 for x in v["closest_nm"]]), ", the transpose of a signed shape" if v["rotated_match"] else "",
               " x%d at %s" % (v["instances"], ",".join(v["where"])) if v["instances"] > 1 or v["where"] else "")
            + ("" if v.get("via") == "module" else " [signed shapes of the %s]" % v["via"]))


def check_core_shape(raw, R, index_path):
    """G0 hook: ERROR [core_shape_change] per violating (module, outline).  Returns a summary dict."""
    idx = load_index(index_path)
    vs = violations(raw, idx)
    for v in vs:
        # exact module: ERROR.  Matched only through the base-name variant family (_bfp, _cs1, __cdN ...): WARN, the variant
        # may be a different design with its own shape; S81-CORES-1 / the die owner confirms or declares an exception
        (R.err if v["via"] == "module" else R.warn)("core_shape_change", message(v))
    return dict(index=str(index_path), index_generated=idx.get("generated"), cores=len(cores(raw)), violations=len(vs),
                **coverage(raw, idx))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build-index")
    b.add_argument("out")
    b.add_argument("--store")
    b.add_argument("--coord-tools")
    b.add_argument("--main-tree", help="checkout (or copy of the signoff.json/pins.json/config.mk files) of origin/main: its signed views are counted too")
    c = sp.add_parser("check")
    c.add_argument("plan")
    c.add_argument("index")
    c.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "build-index":
        doc = build_index(a.store, a.coord_tools, log=lambda m: print(m, file=sys.stderr), main_tree=a.main_tree)
        tmp = a.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(doc, f, indent=0, sort_keys=True)
        os.replace(tmp, a.out)
        print("%s: %d modules, %d records" % (a.out, len(doc["modules"]), doc["records"]))
        return 0
    import gzip
    p = a.plan
    raw = json.loads((gzip.open(p, "rt") if p.endswith(".gz") else open(p)).read())
    vs = violations(raw, load_index(a.index))
    if a.json:
        print(json.dumps(vs, indent=1))
    else:
        for v in vs:
            print(message(v))
        cv = coverage(raw, load_index(a.index))
        print("%d violation(s); %d plan modules, %d with a signed shape, %d without (not checked)"
              % (len(vs), cv["modules"], cv["modules_signed_shape"], len(cv["modules_no_signed_shape"])))
    return 1 if vs else 0


if __name__ == "__main__":
    sys.exit(main())
