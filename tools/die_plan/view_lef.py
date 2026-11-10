#!/usr/bin/env python3
"""A hard-core view is a pair: lib and LEF must come from one export (KW-FIX-5 11-04 root cause, COORD 01:20 item 2).

Pin narrowing edited the pin table and RTL and left the LEF, and attach scripts set only .lib, so a plan can pair a
newer lib with an older LEF: LEF-only pins segfault OpenSTA (busfit is the stopgap) and shapes can differ from the
signed-off view, so parents route to stale shapes.

 bind LIB LEF --record R  files a signed-off view's exported LEF beside its lib with a hash receipt <stem>.view.json.
 view_lef_for(lef, lib)   at gen (type_macros): a lib with a matching receipt uses that LEF, so a regen gets the signed
                          view LEF with no plan event: block keys stay and running parents are not superseded (COORD 03:47).
 attach(entry, lib)       view attach: sets .lib and moves .lef to the LEF exported beside that lib, when there is one.
 stage_kit_macros(...)    at gen: advisory compare of every macro; where the view has no LEF of its own (provisional
                          ETMs, lib-only signed dirs) the kit's staged LEF copy is pruned to the lib's ports.  The plan LEF
                          on disk is never edited.  Nothing here stops a gen (OWNER 11-03: only sign-off blocks).
 main: report PLAN ROOT   read-only table of the masters that disagree; move PLAN_IN PLAN_OUT ROOT --masters a,b  the plan event.

`move` takes an explicit master list, no default: a plan LEF can differ from the view's export on purpose (x_c.lef,
x_clkm5_1101.lef, and legacy/lef/ copies whose only change is the clock pin), so the scope is a reviewed list.  A view
with its own LEF is not pruned at gen: PHY macros carry LEF pins (bumps) their lib omits."""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

KEEP_USE = {"POWER", "GROUND", "ANALOG"}
PG_BITS = {"VDD", "VSS", "VPWR", "VGND"}  # write_timing_model lists supplies as pins; the LEF marks them USE POWER/GROUND
_PIN = re.compile(r"^([ \t]*)PIN[ \t]+(\S+)(.*?)^[ \t]*END[ \t]+\2[ \t]*\r?\n?", re.M | re.S)
_USE = re.compile(r"^\s*USE\s+(\w+)", re.M)


def _read(path):
    p = Path(path)
    if p.name.endswith(".gz"):
        with gzip.open(p, "rt", errors="replace") as f:
            return f.read()
    return p.read_text(errors="replace")


def lib_view(path):
    """(first cell name, signal port bits) of a liberty file; bits None when a bus range cannot be read"""
    t = _read(path)
    c = re.search(r"\bcell\s*\(\s*\"?([^\")\s]+)\"?\s*\)", t)
    types = {}
    for m in re.finditer(r"\btype\s*\(\s*\"?([^\")\s]+)\"?\s*\)\s*\{(.*?)\}", t, re.S):
        f, o = re.search(r"bit_from\s*:\s*(\d+)", m.group(2)), re.search(r"bit_to\s*:\s*(\d+)", m.group(2))
        if f and o:
            types[m.group(1)] = (int(f.group(1)), int(o.group(1)))
    bits = {m.group(1).replace("\\", "") for m in re.finditer(r"\bpin\s*\(\s*\"?([^\")\s]+)\"?\s*\)", t)}
    for m in re.finditer(r"\bbus\s*\(\s*\"?([^\")\s]+)\"?\s*\)\s*\{\s*bus_type\s*:\s*\"?([^\";\s]+)\"?", t):
        if m.group(2) not in types:
            return (c.group(1) if c else None), None
        a, b = types[m.group(2)]
        bits |= {f"{m.group(1)}[{i}]" for i in range(min(a, b), max(a, b) + 1)}
    return (c.group(1) if c else None), bits - PG_BITS


def _num(w):
    """0.000 and 0 are one coordinate (exports differ in format only)"""
    try:
        return f"{float(w):.4f}"
    except ValueError:
        return w


def _macro_span(t, macro):
    m = re.search(r"^\s*MACRO\s+%s\s*$(.*?)^\s*END\s+%s\s*$" % (re.escape(macro), re.escape(macro)), t, re.M | re.S)
    return m.span(1) if m else None


def lef_view(text, macro):
    """{signal pin bit: sorted port geometry lines} and SIZE of one MACRO; None when the file does not hold it"""
    span = _macro_span(text, macro)
    if not span:
        return None, None
    body = text[span[0]:span[1]]
    pins = {}
    for p in _PIN.finditer(body):
        u = _USE.search(p.group(3))
        if u and u.group(1).upper() in KEEP_USE:
            continue
        geo = re.findall(r"^\s*(LAYER\s+\S+|(?:RECT|POLYGON)\b[^;\n]*)", p.group(3), re.M)
        pins[p.group(2).replace("\\", "")] = sorted({" ".join(_num(w) for w in g.split()) for g in geo})
    s = re.search(r"^\s*SIZE\s+(\S+)\s+BY\s+(\S+)", body, re.M)
    return pins, (_num(s.group(1)), _num(s.group(2))) if s else None


def prune_lef_text(text, macro, keep):
    """-> (text with this macro's signal pins outside keep removed, removed names); power, ground, analog pins stay"""
    span = _macro_span(text, macro)
    if not span:
        return text, []
    removed = []

    def drop(p):
        u = _USE.search(p.group(3))
        name = p.group(2).replace("\\", "")
        if (u and u.group(1).upper() in KEEP_USE) or name in keep:
            return p.group(0)
        removed.append(name)
        return ""
    body = _PIN.sub(drop, text[span[0]:span[1]])
    return text[:span[0]] + body + text[span[1]:], sorted(removed)


# KV-PLAN-2 11-09 (kv3_hgi_v3 GRT-0116, 14305-30448 overflow): a signed hard core exports its own M6/M7 routing as
# OBS fragments (kv3_head_eighth_e0: 25094 M6 / 11112 M7 rects, 0.032 um wide, touching 87% / 82% of 2.88-um cells).
# GRT sees a sieve over the core: partial capacity that ends in cap-0 GCells, so die nets detour over the core and
# overflow there (every hgi_v3 overflow GCell lies inside a core outline, none in the channels).  The router cannot
# use that space for real either.  Safe by construction: such a layer is staged as ONE solid OBS rect over the macro,
# so die nets plan in the channels.  Layers already solid or lightly used (< SOLID_FRAC of the cells) stay as exported.
SOLID_GRID_UM = 2.88
SOLID_FRAC = 0.5
_OBS = re.compile(r"^([ \t]*)OBS[ \t]*\r?\n(.*?)^([ \t]*)END[ \t]*\r?\n", re.M | re.S)
_RECT = re.compile(r"^\s*RECT\s+(?:MASK\s+\d+\s+)?(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;", re.M)


def _obs_layers(body):
    """[(layer, [rect line, ...]), ...] in file order; a LAYER line starts a group"""
    groups = []
    for line in body.splitlines(keepends=True):
        m = re.match(r"^\s*LAYER\s+(\S+)", line)
        if m:
            groups.append([m.group(1), []])
        elif groups:
            groups[-1][1].append(line)
    return groups


def cell_cover(rects, w, h, grid=SOLID_GRID_UM):
    """fraction of the macro's grid x grid cells that any rect touches"""
    nx, ny = max(1, int(w // grid) + (w % grid > 1e-9)), max(1, int(h // grid) + (h % grid > 1e-9))
    cells = set()
    for a, b, c, d in rects:
        for i in range(max(0, int(a // grid)), min(nx - 1, int(c // grid)) + 1):
            for j in range(max(0, int(b // grid)), min(ny - 1, int(d // grid)) + 1):
                cells.add((i, j))
    return len(cells) / (nx * ny)


def solid_routed_obs(text, macro, frac=SOLID_FRAC, grid=SOLID_GRID_UM):
    """-> (text, {layer: cover}) with each metal OBS layer of `macro` ABOVE its highest signal-pin layer that is routing
    fragments covering >= frac of the grid cells replaced by one solid RECT 0 0 W H.  Pin layers and the layers under
    them keep their exported shapes (their gaps are pin access); a layer that already has a full-outline rect is left
    as is."""
    span = _macro_span(text, macro)
    if not span:
        return text, {}
    body = text[span[0]:span[1]]
    s = re.search(r"^\s*SIZE\s+(\S+)\s+BY\s+(\S+)", body, re.M)
    o = _OBS.search(body)
    if not s or not o:
        return text, {}
    w, h = float(s.group(1)), float(s.group(2))
    plev = 0
    for p in _PIN.finditer(body):
        u = _USE.search(p.group(3))
        if u and u.group(1).upper() in KEEP_USE:
            continue
        plev = max([plev] + [int(x) for x in re.findall(r"^\s*LAYER\s+M(\d+)\b", p.group(3), re.M)])
    ind = re.match(r"^([ \t]*)", o.group(2)).group(1) if o.group(2) else "    "
    changed, out = {}, []
    for layer, lines in _obs_layers(o.group(2)):
        rects = [tuple(map(float, m.groups())) for m in _RECT.finditer("".join(lines))]
        full = any(a <= 1e-6 and b <= 1e-6 and c >= w - 1e-6 and d >= h - 1e-6 for a, b, c, d in rects)
        if re.fullmatch(r"M\d+", layer) and int(layer[1:]) > plev and rects and not full:
            cov = cell_cover(rects, w, h, grid)
            if cov >= frac:
                changed[layer] = round(cov, 3)
                out.append(f"{ind}LAYER {layer} ;\n{ind} RECT  0 0 {s.group(1)} {s.group(2)} ;\n")
                continue
        out.append(f"{ind}LAYER {layer} ;\n" + "".join(lines))
    if not changed:
        return text, {}
    nb = body[:o.start(2)] + "".join(out) + body[o.end(2):]
    return text[:span[0]] + nb + text[span[1]:], changed


def own_lef_path(lib):
    """the LEF path a lib's own export would have: same dir, lib stem without its corner"""
    n = Path(str(lib)).name
    return Path(str(lib)).with_name(re.sub(r"(_(tt|typ|ff|ss))?\.lib(\.gz)?$", "", n) + ".lef")


def compare(lef_text, lib_file, own_text=None):
    """advisory row: lef_only / lib_only pin bits, and against the view's own LEF the pins whose shapes differ"""
    cell, bits = lib_view(lib_file)
    pins, size = lef_view(lef_text, cell) if cell else (None, None)
    row = dict(cell=cell, lef_only=[], lib_only=[], own_lef=own_text is not None, moved=[], own_only=[], size_differs=False)
    if pins is None or bits is None:
        row["unread"] = "lib cell not a MACRO of the plan LEF" if pins is None else "lib bus range not readable"
        return row
    row["lef_only"], row["lib_only"] = sorted(set(pins) - bits), sorted(bits - set(pins))
    if own_text is not None:
        own, osize = lef_view(own_text, cell)
        if own is not None:
            row["moved"] = sorted(p for p in set(pins) & set(own) if pins[p] != own[p])
            row["own_only"] = sorted(set(own) - set(pins))
            row["size_differs"] = osize != size
    return row


def stale(row):
    return bool(row.get("unread") or row["lef_only"] or row["lib_only"] or row["moved"] or row["own_only"] or row["size_differs"])


def _own_text(lef, lib, resolve):
    own = resolve(own_lef_path(lib))
    if not own.is_file():
        return None
    return None if own.resolve() == resolve(lef).resolve() else _read(own)


def _has_own(lib, resolve):
    return resolve(own_lef_path(lib)).is_file()


def stage_kit_macros(kd, macros, resolve, prune=True, log=print, solid=False):
    """macros = type_macros rows.  Prints one OT_VIEW_LEF line per master that disagrees; prunes kd/macros/<lef> when the
    view has no LEF of its own; a metal OBS layer that is the core's own routing fragments is staged solid
    (solid_routed_obs, OT_SOLID_OBS line).  Clean masters print nothing and their staged copy is untouched (byte-identical kits).
    Any read problem is reported, never raised: the kit keeps the plain copy and busfit still covers it."""
    seen, out = set(), []
    for _inst, mod, lef, lib, *_ in macros:
        if not lef or not lib or (lef, lib) in seen:
            continue
        seen.add((lef, lib))
        try:
            staged = Path(kd) / "macros" / resolve(lef).name
            text = staged.read_text(errors="replace")
            row = compare(text, resolve(lib), _own_text(lef, lib, resolve))
            action = "none"
            keep = lib_view(resolve(lib))[1]
            if prune and row["lef_only"] and keep and not _has_own(lib, resolve):
                new, removed = prune_lef_text(text, row["cell"], keep)
                if removed:
                    staged.write_text(new)
                    text = new
                    action = f"pruned {len(removed)} LEF-only pins"
            if solid and row["cell"]:
                new, cov = solid_routed_obs(text, row["cell"])
                if cov:
                    staged.write_text(new)
                    text = new
                    log("OT_SOLID_OBS " + json.dumps(dict(module=mod, lef=str(lef), layers=cov)))
                    action = (action + "; " if action != "none" else "") + "solid OBS " + ",".join(sorted(cov))
        except Exception as e:  # noqa: BLE001 - advisory: never stop a gen
            log("OT_VIEW_LEF " + json.dumps(dict(module=mod, lef=str(lef), lib=str(lib), error=f"{type(e).__name__}: {e}")))
            continue
        if stale(row) or action != "none":
            log("OT_VIEW_LEF " + json.dumps(dict(module=mod, lef=str(lef), lib=str(lib), action=action, own_lef=row["own_lef"],
                                                 lef_only=len(row["lef_only"]), lib_only=len(row["lib_only"]),
                                                 moved=len(row["moved"]), own_only=len(row["own_only"]),
                                                 size_differs=row["size_differs"], unread=row.get("unread", ""),
                                                 sample=(row["lef_only"] + row["lib_only"] + row["moved"])[:4])))
        out.append((mod, row, action))
    return out


def receipt_path(lib):
    return own_lef_path(lib).with_name(own_lef_path(lib).stem + ".view.json")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def view_lef_for(lef, lib, resolve, log=print):
    """the LEF a kit should stage for this (plan lef, lib): the receipt's LEF when the receipt names this lib and its LEF
    by hash, else the plan lef.  A receipt whose hashes do not match is reported and ignored (the lib moved on)."""
    if not lef or not lib:
        return lef
    try:
        rp = resolve(receipt_path(lib))
        if not rp.is_file():
            return lef
        rec = json.loads(rp.read_text())
        own = resolve(own_lef_path(lib))
        if not own.is_file() or _sha(resolve(lib)) != rec.get("lib_sha256") or _sha(own) != rec.get("lef_sha256"):
            log("OT_VIEW_LEF " + json.dumps(dict(lib=str(lib), action="receipt ignored, hash differs", lef=str(lef))))
            return lef
        if Path(str(lef)) != own_lef_path(lib):
            log("OT_VIEW_LEF " + json.dumps(dict(lib=str(lib), action="view LEF used", plan_lef=str(lef), lef=str(own_lef_path(lib)),
                                                 record=rec.get("record", ""))))
        return str(own_lef_path(lib))
    except (OSError, ValueError) as e:
        log("OT_VIEW_LEF " + json.dumps(dict(lib=str(lib), error=f"{type(e).__name__}: {e}")))
        return lef


def bind(lib, lef, record):
    """file a signed-off LEF beside its lib, with the receipt; a LEF that disagrees with the lib's pins is not filed"""
    text = _read(lef)
    row = compare(text, lib)
    if row.get("unread") or row["lef_only"] or row["lib_only"]:
        sys.exit(f"view_lef bind: LEF and lib disagree: unread={row.get('unread', '')} lef_only={row['lef_only'][:6]} lib_only={row['lib_only'][:6]}")
    dst = own_lef_path(lib)
    if Path(lef).resolve() != dst.resolve():
        dst.write_text(text)
    out = dict(lib=Path(lib).name, lib_sha256=_sha(lib), lef=dst.name, lef_sha256=_sha(dst), record=record, pins=len(lef_view(text, row["cell"])[0]))
    receipt_path(lib).write_text(json.dumps(out, indent=1) + "\n")
    return out


def attach(entry, lib, resolve=None):
    """view attach: entry.lib = lib, and entry.lef follows to the LEF exported beside it.  -> the new lef or None (kept:
    the view has no LEF of its own, gen prunes it).  resolve(path) -> Path; default = the path as given."""
    resolve = resolve or Path
    entry["lib"] = str(lib)
    own = own_lef_path(lib)
    if resolve(own).is_file():
        entry["lef"] = str(own)
        return str(own)
    return None


def _entries(raw):
    for tn, t in (raw.get("partition_types") or {}).items():
        for kind in ("hard_cores", "contents"):
            for c in t.get(kind) or []:
                if c.get("lef"):
                    yield tn, c
                for q in c.get("physical_parts") or []:
                    if q.get("lef"):
                        yield tn, q


def _derived(lef, lib):
    return Path(str(lef)).stem != own_lef_path(lib).stem


def scan(raw, resolve):
    """{(module, lef, lib): {'types': set, 'row': compare row, 'derived': bool}} for every master with a lef and a lib"""
    out = {}
    for tn, c in _entries(raw):
        if not c.get("lib"):
            continue
        k = (c.get("physical_master") or c.get("module") or c.get("inst"), c["lef"], c["lib"])
        out.setdefault(k, dict(types=set()))["types"].add(tn)
    for (m, lef, lib), v in out.items():
        v["derived"] = _derived(lef, lib)
        try:
            v["row"] = compare(_read(resolve(lef)), resolve(lib), _own_text(lef, lib, resolve))
        except OSError as e:
            v["row"] = dict(unread=str(e), lef_only=[], lib_only=[], moved=[], own_only=[], size_differs=False, own_lef=False)
    return out


def main(argv=None):
    import cores as C
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("plan")
    r.add_argument("root")
    m = sub.add_parser("move")
    m.add_argument("plan_in")
    m.add_argument("plan_out")
    m.add_argument("root")
    m.add_argument("--masters", required=True, help="comma list of modules to move to the LEF beside their lib")
    b = sub.add_parser("bind")
    b.add_argument("lib")
    b.add_argument("lef")
    b.add_argument("--record", required=True, help="host:signoff.json of the signed-off view the LEF comes from")
    a = ap.parse_args(argv)
    if a.cmd == "bind":
        print(json.dumps(bind(a.lib, a.lef, a.record)))
        return 0
    resolve = lambda p: C.resolve(p, a.root)
    if a.cmd == "report":
        rows = scan(json.loads(Path(a.plan).read_text()), resolve)
        print("module\tn_types\town_lef\tderived\twould_prune\tlef_only\tlib_only\tmoved\town_only\tsize\tunread\tlef\tlib\ttypes")
        for (mod, lef, lib), v in sorted(rows.items()):
            x = v["row"]
            if stale(x):
                prune = bool(x["lef_only"]) and not _has_own(lib, resolve)
                print("\t".join(map(str, (mod, len(v["types"]), int(x["own_lef"]), int(v["derived"]), int(prune), len(x["lef_only"]),
                                          len(x["lib_only"]), len(x["moved"]), len(x["own_only"]), int(x["size_differs"]),
                                          x.get("unread", ""), lef, lib, ",".join(sorted(v["types"]))))))
        return 0
    raw = json.loads(Path(a.plan_in).read_text())
    rows = scan(raw, resolve)
    named = {x for x in a.masters.split(",") if x}
    missing = named - {k[0] for k in rows}
    if missing:
        sys.exit(f"view_lef move: not masters of this plan: {sorted(missing)}")
    moved, types = {}, set()
    for tn, c in _entries(raw):
        lib = c.get("lib")
        if not lib:
            continue
        v = rows[(c.get("physical_master") or c.get("module") or c.get("inst"), c["lef"], lib)]
        mod = c.get("physical_master") or c.get("module") or c.get("inst")
        if mod in named and v["row"]["own_lef"]:
            moved[mod] = str(own_lef_path(lib))
            c["lef"] = moved[mod]
            types.add(tn)
    Path(a.plan_out).write_text(json.dumps(raw, indent=2) + "\n")
    print(json.dumps(dict(moved=moved, types_rebuild=sorted(types)), indent=1))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
