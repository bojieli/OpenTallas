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
           * access: no signal pin that has access on the kit LEF loses it (abstract_detail.access_report);
           * access windows (--exact BLOAT0.lef, KW44-DRT0073 class fix): around every signal pin on the pin layer
             (+ planar escape), the layer below and above, the bloated OBS is replaced by the exact metal; a pin
             whose landings real core metal blocks keeps the kit LEF OBS in its windows (kit fallback, iterated);
             an OBS over part of / abutting a pin is completed to cover the pin (pin cover);
           * pin access (static model, reported): via up/down with tech via shapes, eol and wide spacing.
         The export gate is the TritonRoute probe below (add refuses a LEF without a passing probe of it).
  probe  --lef OUT.lef --dir D --tech-path T                  DEF+Tcl: TritonRoute pin_access of the view alone (every
                                                                signal pin on a net, kit track phase); the export gate
  add    --die D --module M --lef OUT.lef --receipt R.json --probe D
                                                                store OUT.lef (gz) + its map row in porous_views_data/,
                                                                only with a passing probe of exactly OUT.lef
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


# ------------------------------------------------------------------------------------------------ pin access
# KW44-DRT0073-1111 (11-10): the bloat-1 detail put an M5 OBS over the via landing of 25 west-edge M4 pins of
# ot_s81sl_vs (u[235]: pin 0..0.084 x 162.144..162.168, M5 OBS 0.048..0.12, M4 OBS from 0.06 over the pin itself), and
# the build's access guard counted them as "edge" pins (planar entry) without probing -> DRT-0073 in every parent.
# Class fix, every view: (1) access windows: around every signal pin, on the pin layer (plus its planar escape to the
# outline when the pin is near it), the layer above and the layer below, the bloated OBS is replaced by the EXACT metal of
# the same signed DB (write_abstract_lef -bloat_factor 0); a window never removes real metal.  (2) a hard check: every
# signal pin must have a legal via access point on the result (via up or via down, judged with the tech via shapes and
# end-of-line spacing), else the export fails.  A planar-only exit is reported, not credited: u[235] had one on the
# bloat-1 view and TritonRoute still found no access point.
# Tech rules: ASAP7 asap7_tech_1x_201209.lef (WIDTH / SPACING / PITCH / LEF58 ENDTOEND per layer; VIA<lo><hi> Default
# metal shapes as half extents x, y).  parse_tech() reads the same from any tech LEF (build --tech).
TECH_ASAP7 = dict(
    source="asap7_tech_1x_201209.lef (ORFS platforms/asap7/lef)",
    layers={"M2": dict(width=0.018, spacing=0.018, pitch=0.036, eol=0.031),
            "M3": dict(width=0.018, spacing=0.018, pitch=0.036, eol=0.031),
            "M4": dict(width=0.024, spacing=0.024, pitch=0.048, eol=0.04, wide=(0.025, 0.072)),
            "M5": dict(width=0.024, spacing=0.024, pitch=0.048, eol=0.04, wide=(0.025, 0.072)),
            "M6": dict(width=0.032, spacing=0.032, pitch=0.064, eol=0.04, wide=(0.033, 0.072)),
            "M7": dict(width=0.032, spacing=0.032, pitch=0.064, eol=0.04, wide=(0.033, 0.072))},
    vias={("M2", "M3"): {"M2": (0.014, 0.009), "M3": (0.009, 0.014)},
          ("M3", "M4"): {"M3": (0.009, 0.017), "M4": (0.02, 0.012)},
          ("M4", "M5"): {"M4": (0.023, 0.012), "M5": (0.012, 0.023)},
          ("M5", "M6"): {"M5": (0.012, 0.027), "M6": (0.023, 0.016)},
          ("M6", "M7"): {"M6": (0.027, 0.016), "M7": (0.016, 0.027)},
          ("M7", "M8"): {"M7": (0.016, 0.027), "M8": (0.027, 0.02)}})
METALS = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9")
EDGE_TOUCH_UM = 0.001      # a pin shape this close to the outline exits planar to the outside
ESCAPE_UM = 0.5            # a pin shape within this of the outline also gets its planar escape corridor windowed
PIN_SHAPE_CUT = False      # cut OBS over a pin's own shape (off: the router probe passes the kit LEF, whose blanket
                           # covers the pins, and a hole exactly the pin leaves OBS abutting it)
SCAN_STEP_UM = 0.004       # access-point candidates along the pin centre line


def parse_tech(path):
    """tech LEF -> rules dict like TECH_ASAP7 (metal layers with WIDTH/SPACING/PITCH, ENDTOEND as eol; Default vias)"""
    text = Path(path).read_text()
    lay = {}
    for name, body in re.findall(r"^LAYER (M\d)\s*$(.*?)^END \1", text, re.S | re.M):
        g = lambda k: re.search(r"^\s*%s\s+([\d.]+)" % k, body, re.M)
        if not (g("WIDTH") and g("PITCH")):
            continue
        sp = float(g("SPACING").group(1)) if g("SPACING") else float(g("WIDTH").group(1))
        e2e = [float(x) for x in re.findall(r"ENDTOEND\s+([\d.]+)", body)]
        lay[name] = dict(width=float(g("WIDTH").group(1)), spacing=sp, pitch=float(g("PITCH").group(1)),
                         eol=max([sp] + e2e))
        wt = re.search(r"SPACINGTABLE\s+PARALLELRUNLENGTH\s+[\d.]+\s+WIDTH\s+[\d.]+\s+[\d.]+\s+WIDTH\s+([\d.]+)\s+([\d.]+)", body)
        if wt:
            lay[name]["wide"] = (float(wt.group(1)), float(wt.group(2)))
    vias = {}
    for _, body in re.findall(r"^VIA (\S+) Default\s*$(.*?)^END \1", text, re.S | re.M):
        sh = {}
        for l, x0, y0, x1, y1 in re.findall(r"LAYER (M\d) ;\s*RECT\s+(\S+) (\S+) (\S+) (\S+)", body):
            sh[l] = (round((float(x1) - float(x0)) / 2, 4), round((float(y1) - float(y0)) / 2, 4))
        ms = sorted(sh, key=METALS.index)
        if len(ms) == 2:
            vias[tuple(ms)] = sh
    return dict(source=str(path), layers=lay, vias=vias)


def _nb(layer, d):
    i = METALS.index(layer) + d if layer in METALS else -1
    return METALS[i] if 0 <= i < len(METALS) else None


def _halo(layer, tech):
    """window margin on `layer`: largest via landing half extent there + end-of-line spacing + one track pitch"""
    L = tech["layers"].get(layer)
    if not L:
        return 0.0
    ext = [max(sh[layer]) for sh in tech["vias"].values() if layer in sh] or [L["width"] / 2]
    return round(max(ext) + L["eol"] + L["pitch"], 4)


def access_windows(lines, layers, tech=TECH_ASAP7, escape_um=ESCAPE_UM, only=None):
    """{layer: [rect]}: per signal pin shape on layer L, the shape grown by _halo on L and on the layers below/above
    (only layers in `layers`, i.e. the replaced ones); on L also the planar escape corridor to every outline side
    within escape_um.  Clipped to SIZE."""
    sys.path.insert(0, str(HERE))
    import abstract_detail as AD
    W, H = AD._size_wh(lines)
    out = {}
    for pin, shapes in AD._signal_pin_shapes(lines).items():
        if only is not None and pin not in only:
            continue
        for L, r in shapes:
            for l2 in (L, _nb(L, -1), _nb(L, 1)):
                if l2 not in layers:
                    continue
                g = _halo(l2, tech)
                w = [r[0] - g, r[1] - g, r[2] + g, r[3] + g]
                if l2 == L:
                    if r[0] <= escape_um: w[0] = 0.0
                    if r[1] <= escape_um: w[1] = 0.0
                    if W - r[2] <= escape_um: w[2] = W
                    if H - r[3] <= escape_um: w[3] = H
                w = (max(0.0, AD._snap(w[0], False)), max(0.0, AD._snap(w[1], False)),
                     min(W, AD._snap(w[2], True)), min(H, AD._snap(w[3], True)))
                out.setdefault(l2, []).append(w)
    return out


class _Idx:
    """bucketed rects; hits(box) = rects overlapping the box interior"""

    def __init__(self, rects, cell=2.0):
        self.cell, self.b = cell, {}
        for r in rects:
            for k in self._keys(r):
                self.b.setdefault(k, []).append(r)

    def _keys(self, r):
        c = self.cell
        return [(x, y) for x in range(int(r[0] // c), int(r[2] // c) + 1) for y in range(int(r[1] // c), int(r[3] // c) + 1)]

    def hits(self, q, e=1e-9):
        seen, out = set(), []
        for k in self._keys(q):
            for r in self.b.get(k, ()):
                if id(r) not in seen and r[0] < q[2] - e and r[2] > q[0] + e and r[1] < q[3] - e and r[3] > q[1] + e:
                    seen.add(id(r))
                    out.append(r)
        return out


_RRECT = re.compile(r"(\s*)RECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;")


def _clip(r, w):
    c = (max(r[0], w[0]), max(r[1], w[1]), min(r[2], w[2]), min(r[3], w[3]))
    return c if c[2] > c[0] + 1e-9 and c[3] > c[1] + 1e-9 else None


def cut_windows(lines, wins, exact):
    """OBS of each windowed layer minus its windows, plus the exact metal (exact = {layer: [rect]} from the bloat-0
    export) clipped to the windows.  Lines outside the windows stay byte-equal.  -> (lines, {layer: stats})"""
    sys.path.insert(0, str(HERE))
    import abstract_detail as AD
    head, body, tail = AD._split(lines)
    if body is None or not wins:
        return list(lines), {}
    widx = {l: _Idx(ws) for l, ws in wins.items()}
    add = {}
    for l, rs in exact.items():
        if l not in widx:
            continue
        got = set()
        for r in rs:
            for w in widx[l].hits(r):
                c = _clip(r, w)
                if c:
                    got.add(tuple(round(v, 4) for v in c))
        add[l] = sorted(got)
    out, rep, layer, indent = [], {}, None, "      "

    def flush(l):
        if l in add and add[l]:
            st = rep.setdefault(l, dict(rects_cut=0, um2_cut=0.0))
            st["exact_added"] = len(add[l])
            out.extend("%sRECT %.4f %.4f %.4f %.4f ;\n" % ((indent,) + q) for q in add.pop(l))
    for ln in body:
        lm = re.match(r"\s*LAYER\s+(\S+)\s*;", ln)
        if lm:
            flush(layer)
            layer = lm.group(1)
            out.append(ln)
            continue
        m = _RRECT.match(ln) if layer in widx else None
        if not m:
            out.append(ln)
            continue
        indent = m.group(1)
        r = tuple(float(v) for v in m.groups()[1:])
        hit = widx[layer].hits(r)
        if not hit:
            out.append(ln)
            continue
        rs = _minus(r, hit)
        st = rep.setdefault(layer, dict(rects_cut=0, um2_cut=0.0))
        st["rects_cut"] += 1
        st["um2_cut"] = round(st["um2_cut"] + (r[2] - r[0]) * (r[3] - r[1]) - sum((q[2] - q[0]) * (q[3] - q[1]) for q in rs), 6)
        out += ["%sRECT %.4f %.4f %.4f %.4f ;\n" % ((indent,) + q) for q in rs]
    flush(layer)
    for l in [l for l in METALS if l in add] + sorted(set(add) - set(METALS)):     # windowed layer with no OBS left
        if add[l]:
            out.append("    LAYER %s ;\n" % l)
            flush(l)
    return head + out + tail, rep


def _touch(a, b, e=1e-6):
    return a[0] <= b[2] + e and a[2] >= b[0] - e and a[1] <= b[3] + e and a[3] >= b[1] - e


def _grow(r, gx, gy=None):
    gy = gx if gy is None else gy
    return (r[0] - gx, r[1] - gy, r[2] + gx, r[3] + gy)


def pin_access(lines, tech=TECH_ASAP7, step=SCAN_STEP_UM, stub_rule=False):
    """Per signal pin: a legal access point on this view's OBS, or none.  Candidates p on each pin shape's centre line
    (step um).  via up (down): the via's pin-layer shape at p grown by the pin layer's end-of-line spacing is OBS-free on
    the pin layer AND its other-layer shape at p grown by that layer's eol is OBS-free there; OBS that overlaps or
    touches the pin's own shape on that layer is its own conductor and does not block.  planar_only (reported, ok
    False): no via point, but the min-width wire from a touched outline to p, grown by eol, is OBS-free.
    stub_rule: also fail a shape with an OBS over part of it / abutting it on its own layer (probe-proven DRT-0073
    signature; build() removes it with pin_cover, a view from another exporter may still carry it).
    -> {pin: {ok, mode, layer, point}}"""
    sys.path.insert(0, str(HERE))
    import abstract_detail as AD
    W, H = AD._size_wh(lines)
    idx = {l: _Idx(rs) for l, rs in AD._obs_rects(lines).items()}
    out = {}
    for pin, shapes in AD._signal_pin_shapes(lines).items():

        def free(l, b):
            """no OBS of layer l comes within spacing of box b (box b is already grown by the eol spacing; a wide OBS,
            min side >= the tech wide width, needs the wide spacing: USEMINSPACING OBS OFF).  OBS that overlaps the
            pin's own shape is its own conductor (the router probe passes the kit LEF, whose blanket covers every pin)."""
            if l not in idx:
                return True
            mine = [q for ll, q in shapes if ll == l]
            hit = [h for h in idx[l].hits(b) if not any(_clip(h, q) for q in mine)]
            if hit:
                return False
            wd = tech["layers"][l].get("wide")
            if wd:
                g = wd[1] - tech["layers"][l]["eol"]
                return not [h for h in idx[l].hits(_grow(b, g)) if min(h[2] - h[0], h[3] - h[1]) >= wd[0] - 1e-9
                            and not any(_clip(h, q) for q in mine)]
            return True
        res = dict(ok=False, mode=None, layer=None, point=None)
        planar = None
        for L, r in shapes:
            if L not in tech["layers"]:
                continue
            if stub_rule and L in idx:
                near = [h for h in idx[L].hits(_grow(r, 1e-4)) if _touch(h, r)]
                if near and not any(h[0] <= r[0] + 1e-6 and h[1] <= r[1] + 1e-6 and h[2] >= r[2] - 1e-6
                                    and h[3] >= r[3] - 1e-6 for h in near):
                    res["stub"] = "OBS over part of / abutting the pin on %s (probe: no access point)" % L
                    continue
            horiz = (r[2] - r[0]) >= (r[3] - r[1])
            if horiz:
                c, lo, hi = (r[1] + r[3]) / 2, r[0], r[2]
            else:
                c, lo, hi = (r[0] + r[2]) / 2, r[1], r[3]
            eL, wL = tech["layers"][L]["eol"], tech["layers"][L]["width"] / 2
            lo, hi = (lo + wL, hi - wL) if hi - lo > 2 * wL else ((lo + hi) / 2,) * 2   # the wire end sits inside the pin
            n = max(1, int((hi - lo) / step))
            pts = [lo + (hi - lo) * i / n for i in range(n + 1)]
            pts = [(x, c) if horiz else (c, x) for x in pts]
            for p in pts:
                for d in (1, -1):
                    o = _nb(L, d)
                    v = tech["vias"].get((L, o) if d > 0 else (o, L))
                    if not v or o not in tech["layers"]:
                        continue
                    eo = tech["layers"][o]["eol"]
                    bL = _grow((p[0] - v[L][0], p[1] - v[L][1], p[0] + v[L][0], p[1] + v[L][1]), eL)
                    bo = _grow((p[0] - v[o][0], p[1] - v[o][1], p[0] + v[o][0], p[1] + v[o][1]), eo)
                    if free(L, bL) and free(o, bo):
                        res = dict(ok=True, mode="via_up" if d > 0 else "via_down", layer=L, point=[round(p[0], 4), round(p[1], 4)])
                        break
                if res["ok"]:
                    break
                touch = [r[0] <= EDGE_TOUCH_UM, r[1] <= EDGE_TOUCH_UM, W - r[2] <= EDGE_TOUCH_UM, H - r[3] <= EDGE_TOUCH_UM]
                for side, t in enumerate(touch):
                    if not t:
                        continue
                    if side == 0: wire = (0.0, p[1] - wL, p[0] + wL, p[1] + wL)
                    elif side == 2: wire = (p[0] - wL, p[1] - wL, W, p[1] + wL)
                    elif side == 1: wire = (p[0] - wL, 0.0, p[0] + wL, p[1] + wL)
                    else: wire = (p[0] - wL, p[1] - wL, p[0] + wL, H)
                    if planar is None and free(L, _grow(wire, eL)):
                        planar = dict(layer=L, point=[round(p[0], 4), round(p[1], 4)])
                if res["ok"]:
                    break
            if res["ok"]:
                break
        if not res["ok"] and planar:
            res.update(mode="planar_only", layer=planar["layer"], point=planar["point"])   # not credited (KW44 u[235])
        out[pin] = res
    return out


# TritonRoute probe: the view alone, PHASES copies at different track phases (TritonRoute's pin access depends on where
# the parent tracks fall on the macro), one net per signal pin, parent tracks as in the S81 kits (ot_s81sl_leaf__t50
# 4_cts.def: M4/M5 offset 24 step 48, M6/M7 offset 32 step 64, M1..M3 offset 9 step 36, M8/M9 offset 40 step 80, nm).
PROBE_TRACKS = (("M1", 9, 36), ("M2", 9, 36), ("M3", 9, 36), ("M4", 24, 48), ("M5", 24, 48), ("M6", 32, 64), ("M7", 32, 64), ("M8", 40, 80),
                ("M9", 40, 80))
# origin phase (x, y) nm modulo the M4/M5 step: the kits place a macro so that its pins sit on the parent tracks
# (ot_s81sl_vs in ot_s81sl_leaf__t50: FIXED 838188 622092 = phase (12, 12), u[235] at die y 784.248 on 24 + n*48);
# probe_phase() derives it from the view's pins the same way (most common M5 pin x / M4 pin y centre)
PROBE_PHASES_NM = None
PROBE_GAP_NM = 20160       # a multiple of 2880 = lcm of the track steps 36/48/64/80: the phase is the origin's phase


def probe_phase(lines, dbu=1000):
    """(px, py) nm: the origin phase (0..575 = lcm of the track steps 36/48/64) that puts the most signal pin centres of
    the view on the parent tracks of their layer (vertical shapes vote x, horizontal ones y)"""
    sys.path.insert(0, str(HERE))
    import abstract_detail as AD
    tr = {l: (o, st) for l, o, st in PROBE_TRACKS}
    cs = {"x": [], "y": []}
    for shapes in AD._signal_pin_shapes(lines).values():
        for L, r in shapes:
            if L not in tr:
                continue
            vertical = (r[3] - r[1]) > (r[2] - r[0])
            c = int(round((r[0] + r[2]) / 2 * dbu)) if vertical else int(round((r[1] + r[3]) / 2 * dbu))
            cs["x" if vertical else "y"].append((c,) + tr[L])

    def pick(v):
        if not v:
            return 12
        best = max(range(576), key=lambda p: (sum(1 for c, o, st in v if (c + p - o) % st == 0), -abs(p - 12)))
        return best
    return pick(cs["x"]), pick(cs["y"])


def probe_def(lines, macro=None, phases=PROBE_PHASES_NM, dbu=1000):
    """DEF text: the view's macro placed len(phases) times side by side (origin phase (px, py) nm against the parent
    tracks), each signal pin of each copy on its own net -> (def text, macro name)"""
    sys.path.insert(0, str(HERE))
    import abstract_detail as AD
    W, H = AD._size_wh(lines)
    if macro is None:
        macro = next(re.match(r"\s*MACRO (\S+)", l).group(1) for l in lines if re.match(r"\s*MACRO (\S+)", l))
    phases = phases or (probe_phase(lines, dbu),)
    g = PROBE_GAP_NM
    w, h = (int(round(W * dbu)) // g + 1) * g, (int(round(H * dbu)) // g + 1) * g
    dx, dy = len(phases) * (w + g) + g + 100, h + 2 * g + 100
    out = ["VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN pv_probe ;",
           "UNITS DISTANCE MICRONS %d ;" % dbu, "DIEAREA ( 0 0 ) ( %d %d ) ;" % (dx, dy)]
    for lay, off, step in PROBE_TRACKS:
        out.append("TRACKS X %d DO %d STEP %d LAYER %s ;" % (off, (dx - off) // step + 1, step, lay))
        out.append("TRACKS Y %d DO %d STEP %d LAYER %s ;" % (off, (dy - off) // step + 1, step, lay))
    out.append("COMPONENTS %d ;" % len(phases))
    for k, p in enumerate(phases):
        out.append("    - u%d %s + FIXED ( %d %d ) N ;" % (k, macro, g + k * (w + g) + p[0], g + p[1]))
    out.append("END COMPONENTS")
    pins = list(AD._signal_pin_shapes(lines))
    nets = ["    - n%d_%d ( u%d %s ) + USE SIGNAL ;" % (k, i, k, pn) for k in range(len(phases)) for i, pn in enumerate(pins)]
    out += ["NETS %d ;" % len(nets)] + nets + ["END NETS", "END DESIGN", ""]
    return "\n".join(out), macro


def probe_tcl(tech_lef, view_lef, def_path, layers="M2-M7"):
    return "\n".join(["read_lef %s" % tech_lef, "read_lef %s" % view_lef, "read_def %s" % def_path,
                      "set_routing_layers -signal %s" % layers, "pin_access", "puts PV_PROBE_PIN_ACCESS_DONE", ""])


def pin_cover(lines, layers):
    """an OBS that overlaps or touches a signal pin shape on its layer (the DB's exit stub on the pin) is completed to
    cover the whole pin shape.  TritonRoute probe (dsfd_qbank_S rs[0], M4 pin 0..0.084, stub 0.06..0.137): stub over
    part of the pin FAILS, stub abutting the pin FAILS, OBS over the whole pin PASSES (as the kit blanket does).
    -> (lines, {layer: pins covered})"""
    sys.path.insert(0, str(HERE))
    import abstract_detail as AD
    oidx = {l: _Idx(rs) for l, rs in AD._obs_rects(lines).items() if l in layers}
    cov = {}
    for shapes in AD._signal_pin_shapes(lines).values():
        for L, r in shapes:
            near = [h for h in oidx[L].hits(_grow(r, 1e-4)) if _touch(h, r)] if L in oidx else []
            if near and not any(h[0] <= r[0] + 1e-6 and h[1] <= r[1] + 1e-6 and h[2] >= r[2] - 1e-6
                                and h[3] >= r[3] - 1e-6 for h in near):
                cov.setdefault(L, []).append(r)
    if cov:
        lines, _ = cut_windows(lines, cov, cov)
    return lines, {l: len(v) for l, v in cov.items()}


def build(base, detail, out, layers=None, source=None, exact=None, tech=None):
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
    tech = tech or TECH_ASAP7
    rep["tech"] = tech.get("source")
    if exact:
        ehead = _head(exact)
        pe = pin_compare(base_text, ehead)
        rep["exact"] = dict(path=str(exact), sha256=sha_file(exact), bloat_factor=0, pins_match=pe["match"])
        if not pe["match"]:
            problems.append("exact export pins/outline differ from the kit LEF (not the same signed ODB)")
        wins = access_windows(new, lay, tech)
        ex = {l: [tuple(float(v) for v in m.groups()[1:]) for m in map(_RRECT.match, ls) if m]
              for l, ls in AD._iter_obs_layers(exact, set(wins)).items()}
        for l, g in guard.items():                    # real PG metal outside the kit PG pins stays inside windows too
            if l in wins:
                ex.setdefault(l, []).extend(tuple(float(v) for v in _RRECT.match(x).groups()[1:]) for x in g)
        new, wrep = cut_windows(new, wins, ex)
        rep["windows"] = dict(rule="pin shape + (max via landing half extent + eol spacing + 1 pitch) on pin layer, "
                                   "layer below, layer above; pin-layer planar escape to outline sides within %g um; "
                                   "bloated OBS replaced by the exact (bloat 0) metal" % ESCAPE_UM,
                              halo_um={l: _halo(l, tech) for l in lay}, count={l: len(w) for l, w in wins.items()},
                              cut=wrep)
    else:
        rep["exact"] = None
    # OBS over a signal pin's own shape (the signed DB's exit stub, exported as OBS) is cut out on the replaced layers:
    # the pin shape itself carries that metal, and TritonRoute treats an OBS over the pin as foreign (KW44 u[235])
    own = {}
    for shapes in AD._signal_pin_shapes(new).values():
        for L, r in shapes:
            if L in lay:
                own.setdefault(L, []).append(r)
    if PIN_SHAPE_CUT:
        new, orep = cut_windows(new, own, {})
        rep["pin_shape_cut"] = orep
    # kit fallback: a pin that still has no via point because REAL core metal sits on its landings (ot_s81sl_vs u[234]:
    # the core's M5 at x 0.048 over the west-edge pin) keeps the kit LEF's representation inside its windows (kit OBS
    # clipped to them), i.e. exactly the access the signed kit abstract gives today; the router probe decides.
    # A kit-OBS window can itself crowd a neighbour pin (wide-metal spacing), so repeat until no new pin fails.
    if exact:
        fb, frep, kit, rounds = set(), {}, None, 0
        post = new
        while rounds < 64:
            bad = {p for p, e in pin_access(post, tech).items() if not e["ok"]} - fb
            if not bad:
                break
            fb |= bad
            rounds += 1
            fw = access_windows(new, lay, tech, only=fb)
            if kit is None:
                kit = {l: rs for l, rs in AD._obs_rects(base_lines).items()}
            post, frep = cut_windows(new, fw, {l: rs for l, rs in kit.items() if l in fw})
        new = post
        rep["kit_fallback"] = dict(pins=sorted(fb)[:200], count=len(fb), rounds=rounds, cut=frep)
    new, rep["pin_cover"] = pin_cover(new, lay)
    Path(out).write_text("".join(new))
    ok, probs = AD.check(base_lines, new, lay)
    problems += probs
    pa = pin_access(new, tech)
    pb = pin_access(base_lines, tech)
    noap = sorted(p for p, e in pa.items() if not e["ok"])
    rep["pin_access"] = dict(rule="every signal pin: via up/down access point, tech via shapes + eol spacing (planar-only not credited)",
                             pins=len(pa), without=noap[:50], without_count=len(noap),
                             modes={m: sum(1 for e in pa.values() if e["mode"] == m) for m in ("via_up", "via_down", "planar_only")},
                             without_on_kit_lef=sorted(p for p, e in pb.items() if not e["ok"])[:50])
    # the gate is the TritonRoute probe (probe + add --probe): this static model only picks the kit-fallback pins and
    # reports; it over-predicts (DIE-S81-85 11-10: 110 static vs 1 DRT pin on vs)
    rep["pin_access"]["gate"] = "TritonRoute pin_access probe of the out LEF (add --probe), not this static count"
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


def probe_verdict(probe_dir, out_sha256):
    """the TritonRoute probe of exactly this LEF passed: probe.json names its sha, probe.log reached the end marker with
    no DRT-0073 and no Error -> summary dict, else SystemExit"""
    d = Path(probe_dir)
    pj = json.loads((d / "probe.json").read_text())
    log = (d / "probe.log").read_text(errors="replace")
    if pj.get("lef_sha256") != out_sha256:
        raise SystemExit(f"probe {d}: probed LEF {str(pj.get('lef_sha256'))[:12]} is not {out_sha256[:12]}")
    bad = [ln for ln in log.splitlines() if "DRT-0073" in ln or ln.startswith("Error")]
    if bad or "PV_PROBE_PIN_ACCESS_DONE" not in log:
        raise SystemExit(f"probe {d}: pin access FAILED: {(bad or ['no end marker'])[:3]}")
    return dict(verdict="PASS", tool="TritonRoute pin_access (openroad/orfs:asap7lock)", phase_nm=pj.get("phase_nm"),
                every_signal_pin_connected=True, log_sha256=_sha(log.encode()), def_sha256=sha_file(d / "probe.def"))


def add(die, module, lef, receipt, name=None, data=DATA, probe_dir=None, allow_unprobed=False):
    """store lef (gz, deterministic) and its map row keyed by the kit LEF file name (default: the receipt base name);
    the LEF must carry a passing TritonRoute probe (probe_dir) unless allow_unprobed (unit tests only)"""
    with open(receipt) as fh:
        r = json.load(fh)
    if not r.get("check_ok"):
        raise SystemExit(f"{module}: receipt check_ok is not true: {r.get('problems')}")
    raw = Path(lef).read_bytes()
    if _sha(raw) != r["out_sha256"]:
        raise SystemExit(f"{module}: {lef} is not the receipt's out")
    if probe_dir is None and not allow_unprobed:
        raise SystemExit(f"{module}: no pin-access probe (add --probe DIR)")
    pv = probe_verdict(probe_dir, r["out_sha256"]) if probe_dir is not None else None
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
                   source=r.get("source") or {}, pin_access_probe=pv)
    mf.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
    return m[name]


_HOOK_A = """            _VIEW_LEF[k] = LO.select(VL.view_lef_for(c["lef"], c.get("lib"), _CR.resolve), _CR.resolve)\n"""
_HOOK_A2 = """            import porous_views as PV
            # POROUS-ALL-1 11-10 (OWNER): opt-in real-shape child abstract (gen env OT_POROUS_VIEWS); unset = unchanged
            _VIEW_LEF[k] = PV.select(LO.select(VL.view_lef_for(c["lef"], c.get("lib"), _CR.resolve), _CR.resolve),
                                     _CR.resolve)\n"""
_HOOK_B = "        _LO.write_receipt(kd, macros)"
_HOOK_B2 = """        import porous_views as _PV
        _PV.write_receipt(kd, macros)     # POROUS-ALL-1: porous_views.json only when OT_POROUS_VIEWS is set\n"""


def overlay_gen_phys(text):
    """the two gen_phys hooks by exact anchor (each must occur once); idempotent; ValueError when an anchor is missing"""
    if "porous_views as PV" in text and "_PV.write_receipt(kd, macros)" in text:
        return text
    if text.count(_HOOK_A) != 1:
        raise ValueError("gen_phys: own_lef anchor not found exactly once")
    lines = text.splitlines(keepends=True)
    hits = [i for i, ln in enumerate(lines) if ln.startswith(_HOOK_B)]
    if len(hits) != 1:
        raise ValueError("gen_phys: lef_override write_receipt anchor not found exactly once")
    lines.insert(hits[0] + 1, _HOOK_B2)
    return "".join(lines).replace(_HOOK_A, _HOOK_A2)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--base", required=True)
    b.add_argument("--detail", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--layers", default=",".join(DEFAULT_LAYERS))
    b.add_argument("--source", default=None, help="JSON file: store id / odb sha256 / record of the detail export")
    b.add_argument("--exact", default=None, help="write_abstract_lef -bloat_factor 0 export of the same signed ODB "
                                                 "(pin access windows; without it no window is cut)")
    b.add_argument("--tech", default=None, help="tech LEF for the access rules (default: built-in ASAP7 rules)")
    a2 = sub.add_parser("add")
    for k in ("--die", "--module", "--lef", "--receipt"):
        a2.add_argument(k, required=True)
    o = sub.add_parser("overlay", help="patch DIR/tools/die_plan/gen_phys.py with the two hooks (wave src overlay)")
    o.add_argument("--src", required=True)
    o.add_argument("--check", action="store_true")
    a2.add_argument("--probe", required=True, help="DIR of a passing probe of this LEF (probe.json, probe.log)")
    a2.add_argument("--name", default=None, help="kit LEF file name the view replaces (e.g. ot_s81sl_vq_tpl.lef)")
    pr = sub.add_parser("probe", help="write DIR/probe.def + DIR/probe.tcl: TritonRoute pin_access of the view alone "
                                      "(run: openroad -no_init -exit probe.tcl; pass = PV_PROBE_PIN_ACCESS_DONE, no DRT-0073)")
    pr.add_argument("--lef", required=True)
    pr.add_argument("--dir", required=True)
    pr.add_argument("--tech-path", required=True, help="tech LEF path as openroad sees it")
    pr.add_argument("--lef-path", default=None, help="view LEF path as openroad sees it (default --lef)")
    pr.add_argument("--def-path", default=None, help="probe.def path as openroad sees it (default DIR/probe.def)")
    a = ap.parse_args(argv)
    if a.cmd == "probe":
        lines = Path(a.lef).read_text().splitlines(keepends=True)
        d = Path(a.dir)
        d.mkdir(parents=True, exist_ok=True)
        text, macro = probe_def(lines)
        (d / "probe.def").write_text(text)
        (d / "probe.tcl").write_text(probe_tcl(a.tech_path, a.lef_path or a.lef, a.def_path or str(d / "probe.def")))
        print(json.dumps(dict(macro=macro, lef_sha256=sha_file(a.lef), phase_nm=probe_phase(lines), tracks=PROBE_TRACKS)))
        return 0
    if a.cmd == "build":
        src = json.load(open(a.source)) if a.source else None
        rep = build(a.base, a.detail, a.out, [l for l in a.layers.split(",") if l], src, a.exact,
                    parse_tech(a.tech) if a.tech else None)
        print(json.dumps(rep, indent=1))
        return 0 if rep["check_ok"] else 1
    if a.cmd == "overlay":
        f = Path(a.src) / "tools" / "die_plan" / "gen_phys.py"
        old = f.read_text()
        new = overlay_gen_phys(old)
        print(json.dumps(dict(gen_phys=str(f), changed=new != old, before_sha256=_sha(old.encode()),
                              after_sha256=_sha(new.encode()))))
        if not a.check and new != old:
            f.write_text(new)
        return 0
    print(json.dumps(add(a.die, a.module, a.lef, a.receipt, a.name, probe_dir=a.probe)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
