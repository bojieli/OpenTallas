#!/usr/bin/env python3
"""Real-shape ("porous") hard-core child abstracts for parent kits with routing problems (POROUS-ALL-1, OWNER 2026-11-10
18:0x: "yes, you should use the M1-M5 leftovers for all dies with routing problems").

A parent kit normally takes each hard child's signed abstract with one blanket OBS rect per layer, so the parent cannot
use the tracks the core leaves free over its own area (mostly M4/M5 over empty rows, plus unused M6/M7).  This module
gives the parent, OPT-IN per item, the same abstract with the OBS of M4..M7 replaced by the exact metal of the child's
signed routed DB (write_abstract_lef -bloat_factor 1, the abstract_detail.py splice).  Pins, SIZE, FOREIGN, PG pins and
M1..M3 OBS stay byte-identical to the kit LEF (abstract_detail.check proves it).  Netlist, Liberty and LEC are untouched.

  build  --base KIT.lef --detail DETAIL.lef --out OUT.lef [--layers M4,M5,M6,M7] [--source SRC.json]   -> receipt JSON
         splice + guards, exit 0 only when every guard passes:
           * check: everything except the OBS of the replaced layers is identical to the kit LEF;
           * pins: the detail export (same signed ODB) has the kit's outline and signal pin set/centres (a text-format
             difference of the PIN section is allowed, the geometry is compared);
           * PG guard: real PG metal of the signed DB on a replaced layer that the kit PG pins do not cover is added as OBS
             (a kit whose PG stripes differ from the DB keeps its PG pins, and the parent still cannot route on real PG);
           * access: no signal pin that has access on the kit LEF loses it (abstract_detail.access_report).
  add    --die D --module M --lef OUT.lef --receipt R.json     store OUT.lef (gz) + its map row in porous_views_data/
  select / write_receipt                                        the kit generator hooks (gen_phys.type_macros)

Kit option: gen env OT_POROUS_VIEWS (kit_wave die option item_env {item: {OT_POROUS_VIEWS: ...}}) = comma list of child
modules, or 'all'.  Unset or empty: select() returns its input and nothing is written (byte-identical kits).  A row is
applied only when the kit's plan LEF has exactly the row's base_sha256 (else logged 'not applied', the kit LEF stays),
and never to a view with hard landing evidence (it proves the signed LEF by hash).  A kit that took a view carries
porous_views.json (rows applied + listed modules not applied, with the reason).

Sign-off: unchanged scripts; the parent detail route + DRC run against the exact metal (TritonRoute checks spacing to the
spliced OBS).  RC stays optimistic (owner rule 12.24): parent-to-core M4/M5 coupling is not extracted; the receipt says so
(coupling: NOT_MODELED, information only, no gate).
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "porous_views_data"
ENV = "OT_POROUS_VIEWS"
DEFAULT_LAYERS = ("M4", "M5", "M6", "M7")
EDGE_UM = 0.5
APPLIED, SKIPPED = {}, {}
_map = None


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return _sha(Path(p).read_bytes())


def wanted():
    """set of listed modules, {'all'}, or empty set (option off)"""
    v = os.environ.get(ENV, "").strip()
    return {x.strip() for x in v.split(",") if x.strip()} if v else set()


def rows():
    global _map
    if _map is None:
        f = DATA / "map.json"
        _map = json.loads(f.read_text()) if f.is_file() else {}
    return _map


def _module_of(name, row):
    return row.get("module") or re.sub(r"\.lef$", "", name)


def select(lef, resolve, log=print):
    """the LEF path a kit should use for this (already view_lef / lef_override selected) plan LEF path"""
    want = wanted()
    if not want or not lef:
        return lef
    name = Path(str(lef)).name
    row = rows().get(name)
    if not row:
        return lef
    mod = _module_of(name, row)
    if "all" not in want and mod not in want and name not in want:
        return lef
    plan = Path(resolve(lef))
    why = None
    if not plan.is_file():
        why = "plan LEF not found"
    elif (plan.parent / "landing_evidence").exists():
        why = "view carries hard landing evidence (signed LEF proved by hash)"
    elif sha_file(plan) != row["base_sha256"]:
        why = "plan LEF is not the base of this view (sha256 %s)" % sha_file(plan)[:12]
    if why:
        SKIPPED[name] = dict(lef=name, module=mod, plan_lef=str(lef), reason=why)
        log("OT_POROUS_VIEW " + json.dumps(dict(lef=name, action="not applied: " + why)))
        return lef
    raw = gzip.decompress((DATA / row["file"]).read_bytes())
    if _sha(raw) != row["sha256"]:
        raise ValueError(f"porous view {name}: {row['file']} does not match its recorded sha256 {row['sha256']}")
    d = Path(tempfile.gettempdir()) / f"ot_porous_{os.getuid()}" / row["sha256"][:16]
    d.mkdir(parents=True, exist_ok=True)
    out = d / name                       # same basename: the kit stages macros/<name>, ADDITIONAL_LEFS unchanged
    if not out.is_file() or sha_file(out) != row["sha256"]:
        tmp = d / (name + ".tmp%d" % os.getpid())
        tmp.write_bytes(raw)
        os.replace(tmp, out)
    if str(out) not in APPLIED:
        APPLIED[str(out)] = dict(lef=name, module=mod, plan_lef=str(lef), base_sha256=row["base_sha256"],
                                 sha256=row["sha256"], layers=row["layers"], source=row.get("source"),
                                 receipt_sha256=row.get("receipt_sha256"))
        log("OT_POROUS_VIEW " + json.dumps(dict(lef=name, action="applied", sha256=row["sha256"][:12])))
    return str(out)


def write_receipt(kd, macros):
    """kd/porous_views.json when the option is on; nothing written when off (byte-identical kits)"""
    want = wanted()
    if not want:
        return None
    used = {str(m[2]) for m in macros}
    names = {Path(str(m[2])).name for m in macros if m[2]}
    rec = dict(schema="opentallas.porous_views.v1", env=os.environ.get(ENV),
               rows=[APPLIED[u] for u in sorted(used & set(APPLIED))],
               not_applied=[SKIPPED[n] for n in sorted(names & set(SKIPPED))],
               coupling="NOT_MODELED (parent-to-core M4..M7 coupling not extracted; optimistic RC, information only)",
               rule="POROUS-ALL-1 (OWNER 11-10): kit LEF with M4..M7 OBS from the child's signed routed DB")
    (Path(kd) / "porous_views.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


# ------------------------------------------------------------------------------------------------------ build
def _head(path):
    out = []
    with open(path) as fh:
        for ln in fh:
            if ln.strip() == "OBS":
                break
            out.append(ln)
    return "".join(out)


def _pins(text):
    """-> (size, {pin: set((layer, cx, cy))}, pg set, {pg layer: [rect]})"""
    sz = re.findall(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", text)
    size = (round(float(sz[-1][0]), 3), round(float(sz[-1][1]), 3)) if sz else None
    pins, pg, pgr = {}, set(), {}
    for n, b in re.findall(r"^\s*PIN (\S+)(.*?)^\s*END \1\s*$", text, re.S | re.M):
        is_pg = bool(re.search(r"USE (POWER|GROUND)", b))
        if is_pg:
            pg.add(n)
        c, lay = set(), None
        for line in b.splitlines():
            t = line.replace(";", " ").split()
            if t and t[0] == "LAYER":
                lay = t[1]
            elif t and t[0] == "RECT" and len(t) >= 5:
                r = tuple(float(x) for x in t[1:5])
                c.add((lay, round((r[0] + r[2]) / 2, 3), round((r[1] + r[3]) / 2, 3)))
                if is_pg:
                    pgr.setdefault(lay, []).append(r)
        pins[n] = c
    return size, pins, pg, pgr


def pin_compare(base_text, detail_head):
    bs, bp, bpg, _ = _pins(base_text)
    ds, dp, dpg, _ = _pins(detail_head)
    sb, sd = set(bp) - bpg, set(dp) - dpg
    bad = [n for n in sorted(sb & sd) if not (bp[n] == dp[n] or bp[n] <= dp[n] or dp[n] <= bp[n])]
    rep = dict(size_base=bs, size_detail=ds, signal_pins=len(sb), only_base=sorted(sb - sd)[:10],
               only_detail=sorted(sd - sb)[:10], mismatch=bad[:10],
               pg_shapes_equal=all(bp.get(n) == dp.get(n) for n in bpg | dpg))
    rep["match"] = bs == ds and sb == sd and not bad
    return rep


def _minus(r, cut):
    """rect r minus each rect of cut -> [rect] (pieces thinner than 1 nm dropped)"""
    pieces = [r]
    for p in cut:
        nxt = []
        for q in pieces:
            if p[0] >= q[2] or p[2] <= q[0] or p[1] >= q[3] or p[3] <= q[1]:
                nxt.append(q)
                continue
            a, b, c, d = q
            e, f, g, h = p
            if f > b: nxt.append((a, b, c, f))
            if h < d: nxt.append((a, h, c, d))
            if e > a: nxt.append((a, max(b, f), e, min(d, h)))
            if g < c: nxt.append((g, max(b, f), c, min(d, h)))
        pieces = [q for q in nxt if q[2] - q[0] > 1e-3 and q[3] - q[1] > 1e-3]
    return pieces


def pg_guard(base_text, detail_head, layers):
    """{layer: [rect lines]} real PG metal of the detail on replaced layers outside every kit PG pin shape (the part a
    kit with different PG stripes does not show).  Kit PG pin shapes themselves are never covered by OBS, so the parent
    PDN still reaches them."""
    _, _, _, bpg = _pins(base_text)
    _, _, _, dpg = _pins(detail_head)
    out = {}
    for lay in layers:
        cut = bpg.get(lay, [])
        miss = [q for r in dpg.get(lay, []) for q in _minus(r, cut)]
        if miss:
            out[lay] = ["      RECT %.4f %.4f %.4f %.4f ;\n" % r for r in miss]
    return out


def build(base, detail, out, layers=None, source=None):
    sys.path.insert(0, str(HERE))
    import abstract_detail as AD
    with open(base) as fh:
        base_lines = fh.read().splitlines(keepends=True)
    base_text = "".join(base_lines)
    dhead = _head(detail)
    _, body, _ = AD._split(base_lines)
    have = {l for l, _ in AD._obs_by_layer(body)} if body is not None else set()
    want = list(layers or DEFAULT_LAYERS)
    lay = [l for l in want if l in have]
    rep = dict(base=str(base), base_sha256=sha_file(base), detail=str(detail), detail_sha256=sha_file(detail),
               layers_requested=want, layers_detailed=lay, bloat_factor=1, source=source or {},
               helper_sha256=sha_file(HERE / "abstract_detail.py"), tool_sha256=sha_file(__file__))
    rep["pins"] = pc = pin_compare(base_text, dhead)
    problems = [] if pc["match"] else ["detail export pins/outline differ from the kit LEF (different view or ODB)"]
    if not lay:
        problems.append("kit LEF has no OBS on %s: nothing to replace" % ",".join(want))
    det = AD._iter_obs_layers(detail, set(lay))
    guard = pg_guard(base_text, dhead, lay)
    for l, g in guard.items():
        det.setdefault(l, []).extend(g)
    rep["pg_guard_rects"] = {l: len(g) for l, g in guard.items()}
    rep["rects"] = {l: len(det.get(l, [])) for l in lay}
    new = AD.splice(base_lines, det, lay)
    Path(out).write_text("".join(new))
    ok, probs = AD.check(base_lines, new, lay)
    problems += probs
    # a pin within EDGE_UM of the outline has planar entry from outside (enclosed_signal_pins uses the same 0.5 um)
    a0 = AD.access_report(base_lines, edge_um=EDGE_UM)
    a1 = AD.access_report(new, a0["top_layer"], edge_um=EDGE_UM)
    lost = sorted(p for p, e in a1["pins"].items() if not e["ok"] and a0["pins"].get(p, {}).get("ok"))
    rep["access"] = dict(top_layer=a0["top_layer"], without_access_base=sorted(p for p, e in a0["pins"].items() if not e["ok"]),
                         without_access_new=sorted(p for p, e in a1["pins"].items() if not e["ok"]), lost=lost)
    if lost:
        problems.append("%d signal pins lose access on the porous view: %s" % (len(lost), ", ".join(lost[:5])))
    rep["out"], rep["out_sha256"] = str(out), sha_file(out)
    rep["problems"], rep["check_ok"] = problems, not problems
    rep["coupling"] = "NOT_MODELED"
    return rep


def add(die, module, lef, receipt, name=None, data=DATA):
    """store lef (gz, deterministic) and its map row keyed by the kit LEF file name (default: the receipt base name)"""
    with open(receipt) as fh:
        r = json.load(fh)
    if not r.get("check_ok"):
        raise SystemExit(f"{module}: receipt check_ok is not true: {r.get('problems')}")
    raw = Path(lef).read_bytes()
    if _sha(raw) != r["out_sha256"]:
        raise SystemExit(f"{module}: {lef} is not the receipt's out")
    name = name or Path(r["base"]).name
    if not name.endswith(".lef"):
        raise SystemExit(f"{module}: kit LEF name {name} is not a .lef")
    data.mkdir(parents=True, exist_ok=True)
    fn = f"{name}.{r['out_sha256'][:12]}.gz"
    (data / fn).write_bytes(gzip.compress(raw, mtime=0))
    rc = json.dumps(r, indent=1, sort_keys=True) + "\n"
    (data / (fn[:-3] + ".receipt.json")).write_text(rc)
    mf = data / "map.json"
    m = json.loads(mf.read_text()) if mf.is_file() else {}
    m[name] = dict(die=die, module=module, base_sha256=r["base_sha256"], sha256=r["out_sha256"], file=fn,
                   layers=r["layers_detailed"], receipt=fn[:-3] + ".receipt.json", receipt_sha256=_sha(rc.encode()),
                   source=r.get("source") or {})
    mf.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
    return m[name]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--base", required=True)
    b.add_argument("--detail", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--layers", default=",".join(DEFAULT_LAYERS))
    b.add_argument("--source", default=None, help="JSON file: store id / odb sha256 / record of the detail export")
    a2 = sub.add_parser("add")
    for k in ("--die", "--module", "--lef", "--receipt"):
        a2.add_argument(k, required=True)
    a2.add_argument("--name", default=None, help="kit LEF file name the view replaces (e.g. ot_s81sl_vq_tpl.lef)")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        src = json.load(open(a.source)) if a.source else None
        rep = build(a.base, a.detail, a.out, [l for l in a.layers.split(",") if l], src)
        print(json.dumps(rep, indent=1))
        return 0 if rep["check_ok"] else 1
    print(json.dumps(add(a.die, a.module, a.lef, a.receipt, a.name)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
