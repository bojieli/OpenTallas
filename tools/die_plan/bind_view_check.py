#!/usr/bin/env python3
"""BIND-VIEWCHK (advisory, targets-not-gates): does each hard-core view a kit binds match its counted routed DB?

For every macro LEF in <kit>/macros (generated SRAM/ROM abstracts are skipped), compare the kit view with an
export of the counted record's routed DB (write_abstract_lef of that 6_final.odb):
  * outline (SIZE),
  * signal pins: names, DIRECTION, and shapes (layer + rect centre per rect),
  * PG pins: stripe positions per layer (centre across the stripe direction).
Classes per core:
  CLEAN       everything equal
  PIN_STUB    signal pins equal except that one side has extra rects on the same pins (pin-access stubs); info only
  OUTLINE / PIN_SET / PIN_DIR / PIN_SHAPE / PG_OFFSET   mismatches (several may apply)
  NO_EXPORT   no counted-DB export was found to compare against (not a mismatch)
For PG_OFFSET the stale side is named where it can be: a plan stub (PG equals the standard core stub recipe) is the
generator side; a view whose provenance names another routed DB (odb sha / run differ from the counted record's) is
"view from another run".  The tool reports; it never blocks: exit status is always 0.

  python3 -I bind_view_check.py --kit <kit gen dir> --cache release_tree_plan_cache.json \
      [--export-dir DIR] [--export-root DIR] [--git-repo REPO --git-rev origin/main] [--plan s81/plan_h2_2249.json] \
      [--out report.json]

Export lookup per core C (first hit wins):
  --export-dir DIR:  DIR/C/detail.lef, DIR/C/C.lef or DIR/C.lef (optional DIR/C/export.json {"odb_sha256", "routed_db"};
                     with routed_db the row says whether the export is of the counted record's own DB)
  --export-root DIR: DIR/<record archive>/<routed_db dir>/C.lef, then DIR/<routed_db dir>/C.lef (a local mirror)
View provenance: with --git-repo, the abstract.json beside the plan's pins_lef path is read with `git show`.
"""
import argparse
import json
import os
import re
import subprocess
import sys

PG_USES = ("POWER", "GROUND")
NDIG = 3


def _head_text(path):
    """LEF text up to the first OBS (pin section only; detailed exports can be huge)."""
    out = []
    with open(path) as fh:
        for ln in fh:
            if ln.strip() == "OBS":
                break
            out.append(ln)
    return "".join(out)


def is_generated_memory(path):
    with open(path) as fh:
        head = "".join(fh.readline() for _ in range(3)).lower()
    return "memory compiler" in head or "abstract view" in head


def parse_view(text, macro=None):
    """-> dict(name, size, pins={name: dict(dir, use, rects=[(layer, x0, y0, x1, y1)])})."""
    ms = list(re.finditer(r"^\s*MACRO\s+(\S+)", text, re.M))
    if not ms:
        raise ValueError("no MACRO")
    pick = next((m for m in ms if macro is None or m.group(1) == macro), None)
    if pick is None:
        raise ValueError("MACRO %s not found" % macro)
    name = pick.group(1)
    body = text[pick.end():]
    end = re.search(r"^\s*END\s+%s\s*$" % re.escape(name), body, re.M)
    if end:
        body = body[:end.start()]
    sizes = re.findall(r"\bSIZE\s+([-\d.]+)\s+BY\s+([-\d.]+)", body)
    size = (round(float(sizes[-1][0]), NDIG), round(float(sizes[-1][1]), NDIG)) if sizes else None
    pins = {}
    for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$", body, re.S | re.M):
        pname, pb = pm.group(1), pm.group(2)
        d = re.search(r"DIRECTION\s+(\S+)\s*;", pb)
        u = re.search(r"USE\s+(\S+)\s*;", pb)
        rects, layer = [], None
        for ln in pb.splitlines():
            t = ln.split()
            if not t:
                continue
            if t[0] == "LAYER":
                layer = t[1]
            elif t[0] == "RECT" and layer:
                rects.append((layer,) + tuple(round(float(v), NDIG) for v in t[1:5]))
        pins[pname] = dict(dir=d.group(1) if d else None, use=u.group(1) if u else "SIGNAL", rects=rects)
    return dict(name=name, size=size, pins=pins)


def _centres(rects):
    return {(r[0], round((r[1] + r[3]) / 2, NDIG), round((r[2] + r[4]) / 2, NDIG)) for r in rects}


def pg_stripes(view):
    """{net: {layer: sorted stripe centres across the stripe}} for PG pins (vertical stripe -> x, horizontal -> y)."""
    out = {}
    for n, p in view["pins"].items():
        if p["use"] not in PG_USES:
            continue
        per = {}
        for (l, x0, y0, x1, y1) in p["rects"]:
            vert = (y1 - y0) >= (x1 - x0)
            per.setdefault(l + ("/V" if vert else "/H"), set()).add(round((x0 + x1) / 2 if vert else (y0 + y1) / 2, NDIG))
        out[n] = {k: sorted(v) for k, v in per.items()}
    return out


def stub_recipe_stripes(width, height, margin=4.32, pitch=4.32, offset=2.064, wire=0.12, spacing=0.072):
    """Stripe centres of the standard core PDN stub recipe (core_pg_stub.py); {} when the core is too small."""
    res = {}
    if min(width, height) <= 2 * margin:
        return res
    for net, shift in (("VSS", 0.0), ("VDD", wire + spacing)):
        xs, x = [], margin + offset + shift
        while x + wire / 2 <= width - margin + 1e-9:
            xs.append(round(x, NDIG))
            x += pitch
        res[net] = xs
    return res


def compare(kit, exp):
    """-> dict(classes=[...], details)."""
    cls, det = [], {}
    if kit["size"] != exp["size"]:
        cls.append("OUTLINE")
        det["size"] = dict(kit=kit["size"], export=exp["size"])
    ks = {n for n, p in kit["pins"].items() if p["use"] not in PG_USES}
    es = {n for n, p in exp["pins"].items() if p["use"] not in PG_USES}
    if ks != es:
        cls.append("PIN_SET")
        det["only_kit"] = sorted(ks - es)[:20]
        det["only_export"] = sorted(es - ks)[:20]
        det["n_only_kit"], det["n_only_export"] = len(ks - es), len(es - ks)
    common = sorted(ks & es)
    bad_dir = [n for n in common if kit["pins"][n]["dir"] != exp["pins"][n]["dir"]]
    if bad_dir:
        cls.append("PIN_DIR")
        det["pin_dir"] = bad_dir[:20]
    shape, stub = [], []
    for n in common:
        a, b = _centres(kit["pins"][n]["rects"]), _centres(exp["pins"][n]["rects"])
        if a == b:
            continue
        (stub if (a <= b or b <= a) else shape).append(n)
    if shape:
        cls.append("PIN_SHAPE")
        det["pin_shape"] = shape[:20]
        det["n_pin_shape"] = len(shape)
    if stub:
        det["pin_stub"] = stub[:20]
        det["n_pin_stub"] = len(stub)
    det["signal_pins"] = dict(kit=len(ks), export=len(es), equal=len(common) - len(shape) - len(stub))
    kp, ep = pg_stripes(kit), pg_stripes(exp)
    if kp != ep:
        cls.append("PG_OFFSET")
        pg = {}
        for net in sorted(set(kp) | set(ep)):
            for lk in sorted(set(kp.get(net, {})) | set(ep.get(net, {}))):
                a, b = kp.get(net, {}).get(lk, []), ep.get(net, {}).get(lk, [])
                if a != b:
                    pg["%s %s" % (net, lk)] = dict(kit=_summ(a), export=_summ(b), shared=len(set(a) & set(b)))
        det["pg"] = pg
        if kit["size"]:
            rec = stub_recipe_stripes(*kit["size"])
            kv = {net: kp.get(net, {}).get("M5/V", []) for net in ("VSS", "VDD")}
            det["kit_pg_is_stub_recipe"] = bool(rec) and all(kv[n] == rec.get(n) for n in ("VSS", "VDD"))
    if not cls:
        cls = ["PIN_STUB"] if stub else ["CLEAN"]
    elif stub:
        cls.append("PIN_STUB")
    return dict(classes=cls, details=det)


def _summ(xs):
    if not xs:
        return dict(n=0)
    return dict(n=len(xs), first=xs[0], pitch=round(xs[1] - xs[0], NDIG) if len(xs) > 1 else None)


def counted_record(cache, top):
    """Newest versioned signed record with a routed DB for `top` (else newest record of any kind)."""
    rows = [r for r in cache.get("signed_records", []) if r.get("top") == top]
    with_db = [r for r in rows if r.get("routed_db")]
    pool = with_db or rows
    if not pool:
        return None
    pool.sort(key=lambda r: (bool(r.get("versioned")), bool(r.get("flow_tag")), str(r.get("generated"))))
    return pool[-1]


def find_export(core, rec, export_dir, export_root):
    if export_dir:
        for p in (os.path.join(export_dir, core, "detail.lef"), os.path.join(export_dir, core, core + ".lef"),
                  os.path.join(export_dir, core + ".lef")):
            if os.path.isfile(p):
                meta = os.path.join(os.path.dirname(p), "export.json") if os.path.dirname(p) != export_dir else None
                return p, (json.load(open(meta)) if meta and os.path.isfile(meta) else {})
    if export_root and rec and rec.get("routed_db"):
        d = os.path.dirname(rec["routed_db"]).lstrip("/")
        for p in (os.path.join(export_root, str(rec.get("archive", "")).lstrip("/"), d, core + ".lef"),
                  os.path.join(export_root, d, core + ".lef")):
            if os.path.isfile(p):
                return p, {}
    return None, {}


def plan_pins_lef(cache, plan, core):
    for pn, p in cache.get("plans", {}).items():
        if plan and pn != plan:
            continue
        x = p.get("designs", {}).get(core)
        if x and x.get("pins_lef"):
            return pn, x["pins_lef"]
    return None, None


def view_provenance(repo, rev, lef_path):
    """abstract.json beside the plan LEF -> {odb_sha256, odb_host, raw_manifest_sha256} (None when absent)."""
    if not repo or not lef_path:
        return None
    path = os.path.dirname(lef_path) + "/abstract.json"
    try:
        txt = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (rev, path)], capture_output=True, text=True,
                             timeout=60).stdout
        d = json.loads(txt) if txt else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if not d:
        return None
    out = dict(abstract=path)
    for k, v in (d.get("verdict", {}).get("files", {}) or {}).items():
        if k.endswith("6_final.odb"):
            out.update(odb_sha256=v.get("sha256"), odb_host=v.get("host"))
    ep = d.get("export_provenance") or {}
    if ep:
        out["raw_manifest_sha256"] = ep.get("raw_manifest_sha256")
    return out


def stale_side(res, rec, meta, prov):
    """Name the stale side of a mismatch where the evidence allows."""
    c = res["classes"]
    if not any(k in c for k in ("OUTLINE", "PIN_SET", "PIN_DIR", "PIN_SHAPE", "PG_OFFSET")):
        return None
    if "PG_OFFSET" in c and res["details"].get("kit_pg_is_stub_recipe"):
        return "kit: plan PG stub recipe does not match the counted DB's PDN (generator side)"
    if prov and prov.get("odb_sha256"):
        exp_sha = meta.get("odb_sha256")
        if exp_sha and prov["odb_sha256"] != exp_sha:
            return "kit: view exported from another routed DB (%s, odb %s) than the counted DB (odb %s)" % (
                prov.get("odb_host"), prov["odb_sha256"][:12], exp_sha[:12])
        if exp_sha and prov["odb_sha256"] == exp_sha:
            return "same routed DB on both sides: view post-processing differs"
        return "kit: view from routed DB %s (odb %s); counted DB sha not given" % (prov.get("odb_host"),
                                                                                 prov["odb_sha256"][:12])
    return "kit view (no provenance) differs from the counted DB export; counted record %s" % (
        (rec or {}).get("store_id", "?")[:12])


def run(kit, cache, export_dir=None, export_root=None, git_repo=None, git_rev="origin/main", plan=None):
    rows = []
    mdir = os.path.join(kit, "macros")
    for fn in sorted(os.listdir(mdir)):
        if not fn.endswith(".lef"):
            continue
        path = os.path.join(mdir, fn)
        if is_generated_memory(path):
            continue
        kv = parse_view(_head_text(path))
        core = kv["name"]
        rec = counted_record(cache, core)
        exp, meta = find_export(core, rec, export_dir, export_root)
        pn, plef = plan_pins_lef(cache, plan, core)
        row = dict(core=core, kit_lef=path, plan=pn, plan_pins_lef=plef,
                   counted=dict(store_id=(rec or {}).get("store_id"), name=(rec or {}).get("name"),
                                flow_tag=(rec or {}).get("flow_tag"), routed_db=(rec or {}).get("routed_db"),
                                generated=(rec or {}).get("generated")) if rec else None,
                   export=exp, export_meta=meta or None)
        if not exp:
            row.update(classes=["NO_EXPORT"])
            rows.append(row)
            continue
        if meta.get("routed_db") and rec and rec.get("routed_db"):
            row["export_is_counted_db"] = os.path.normpath(meta["routed_db"]) == os.path.normpath(rec["routed_db"])
        res = compare(kv, parse_view(_head_text(exp), core))
        prov = view_provenance(git_repo, git_rev, plef)
        row.update(res, view_provenance=prov, stale=stale_side(res, rec, meta, prov))
        rows.append(row)
    mism = [r["core"] for r in rows if set(r["classes"]) & {"OUTLINE", "PIN_SET", "PIN_DIR", "PIN_SHAPE", "PG_OFFSET"}]
    summary = "BIND-VIEWCHK %s: %d hard cores, %d mismatch (%s), %d clean, %d pin-stub only, %d no export" % (
        os.path.basename(os.path.normpath(kit)), len(rows), len(mism), ",".join(mism) or "-",
        sum(r["classes"] == ["CLEAN"] for r in rows), sum(r["classes"] == ["PIN_STUB"] for r in rows),
        sum(r["classes"] == ["NO_EXPORT"] for r in rows))
    return dict(schema="opentallas.bind_view_check.v1", advisory=True, kit=kit, rows=rows, mismatches=mism,
                summary=summary)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", required=True)
    ap.add_argument("--cache", default=os.path.expanduser("~/.local/state/fleet-viz/release_tree_plan_cache.json"))
    ap.add_argument("--export-dir")
    ap.add_argument("--export-root")
    ap.add_argument("--git-repo")
    ap.add_argument("--git-rev", default="origin/main")
    ap.add_argument("--plan")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        cache = json.load(open(a.cache))
        rep = run(a.kit, cache, a.export_dir, a.export_root, a.git_repo, a.git_rev, a.plan)
    except Exception as e:  # advisory: report, never block
        rep = dict(schema="opentallas.bind_view_check.v1", advisory=True, kit=a.kit, error=repr(e),
                   summary="BIND-VIEWCHK %s: ERROR %r" % (a.kit, e))
    txt = json.dumps(rep, indent=1)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(txt + "\n")
    else:
        print(txt)
    print(rep["summary"], file=sys.stderr if not a.out else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
