#!/usr/bin/env python3
"""PLACE-PRECHECK-2330: static precheck of the place-stage guard checks, for every type of a die event at once.

Why: about 70 kit attempts failed at place in 24 h, almost all on OUR OWN deterministic guards in the place scripts, found one
attempt at a time after hours of queueing and gen.  Each rule below is decided from the plan (and, for MPL-0020 / the cone, the
bound netlist); this tool re-evaluates it with the code or formula the kit uses, so a finding here is the failure the kit will print.

  class    kit message (stage)                                   decided from            same code / formula
  OVERLAP  "exact packed bank overlaps existing explicit         plan (ft sites + exact  kit_istations.is_packed_exact_banks
           reservation: <inst> x y" / "... hard macro" /          bank sites + macros)    loop; ft_spread.spread_type for the
           "not on row/site" / "outside core"  (global_place)                             gen-time ft sites; --kit reads the
                                                                                          GENERATED ft_bit_sites.tcl+istations.tcl
  KNEE     "internal station knee needs a plan depth change:     plan (pins, leaf, n)    istation_knee.knee / legs (the Python
           worst ideal hop N >403um"  (global_place)                                      mirror of kit_istations.is_knee_site)
  MACRO    "MPL-0034 / overlap / outside CORE_AREA" (macro_place) plan                    kit_fit.findings (+ kit_core_area)
           "macro_channels" (kit preflight advisory)              kit                     kit_contract.macro_channels (--kit)
  MPL0020  "[ERROR MPL-0020] Couldn't find a macro named X"      plan + synth netlist    place_macro names vs netlist cells
           (macro_place; a macro synthesis dropped)                                       (--netlist; not decidable pre-synth)
  CONE     "cone has more than N cells: not separable"           plan + synth netlist    place_regions_cone.tcl ot_pr_cone
           (global_place; since 124d829 the region is DROPPED     (FIRM cells unknown      (--netlist; approximate: FIRM cells
           instead of stopping the kit: reported as CONE-DROP)    statically)              are not excluded)
  STATIONCORE  (no kit message: station flops planned on a hard     plan (pins, leaf, n,    station_core.rows: the kit's per-bit
           macro are moved by detailed placement, their routes     relay_sites, macros)    site model on EVERY station row
           cross the macro on M6-M8 only; flat GRT overflow)
Not static (reported by the kit only): PLACE-HPWL (needs the global placement), DPL-0033 (legaliser), infra kills.

Modes
  place_precheck.py --plan PLAN.json [--types a,b] [--jobs N] [--out DIR]    every type of the plan (G0 / pre-launch)
  place_precheck.py --kit KITDIR [--kit KITDIR ...]                           generated kits (OVERLAP on the kit's own tables)
Report only: exit 0 unless --strict and findings.  Never a gate (OWNER: no new gates)."""
import argparse
import collections
import json
import os
import re
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DBU = 4000                      # ASAP7 db units per um (face_flops ff_dbu)
SITE_W, ROW_H = 0.054, 0.27     # kit site / row grid (um)
CELL = (1.404, 0.27)            # ft_spread.CELL (bit-site footprint)
KNEE_NEAR_UM = 6.0              # advisory band below the 403 um limit: the kit measures real BTerms, the plan the planned pins
CLASSES = ("OVERLAP", "KNEE", "MACRO", "STATIONCORE", "MPL0020", "CONE")


def F(cls, key, msg, **kw):
    return dict(cls=cls, key=key, msg=msg, **kw)


# ---------------------------------------------------------------- OVERLAP (shared core)
class Occ:
    """face_flops ff_reserve_explicit / ff_hits_explicit: rects in dbu, indexed by the rows they cover."""

    def __init__(self, y0):
        self.y0, self.rh, self.rows = y0, round(ROW_H * DBU), collections.defaultdict(list)

    def _rows(self, y, h):
        r = (y - self.y0) // self.rh
        while self.y0 + r * self.rh < y + h:
            yield r
            r += 1

    def reserve(self, x, y, w, h):
        for r in self._rows(y, h):
            self.rows[r].append((x, y, x + w, y + h))

    def hits(self, x, y, w, h):
        for r in self._rows(y, h):
            for a, b, c, d in self.rows.get(r, ()):
                if x < c and a < x + w and y < d and b < y + h:
                    return True
        return False


def _d(v):
    return round(float(v) * DBU)


def exact_bank_check(rows, occ, core, blocks, tag=""):
    """The is_packed_exact_banks loop of kit_istations.PACKED_EXACT_BANK_TCL over `rows` = [(inst, banks, (fw, fh))] in kit order, ONE
    first error per row (the kit stops there), later rows still evaluated.  occ already holds the explicit ft sites; every checked row
    reserves its sites afterwards, as the kit does.  core = (x0, y0, x1, y1) um; blocks = [(name, x0, y0, x1, y1)] um.
    -> [finding]"""
    x0, y0, x1, y1 = (_d(v) for v in core)
    sw = _d(SITE_W)
    bl = [(n, _d(a), _d(b), _d(c), _d(d)) for n, a, b, c, d in blocks]
    out = []
    for inst, banks, (fw, fh) in rows:
        cw, ch = _d(fw), _d(fh)
        err, reserve = None, []
        for bank in banks:
            for x, y in bank:
                cx, cy = _d(x), _d(y)
                if (cy - y0) % _d(ROW_H) != 0 or cy < y0 or cy >= y1 or (cx - x0) % sw != 0:
                    err = ("GRID", f"exact packed reserved site is not on row/site: {inst} {x:g} {y:g}")
                elif cx < x0 or cy < y0 or cx + cw > x1 or cy + ch > y1:
                    err = ("CORE", f"exact packed reserved footprint outside core: {inst} {x:g} {y:g}")
                elif occ.hits(cx, cy, cw, ch):
                    err = ("EXPLICIT", f"exact packed bank overlaps existing explicit reservation: {inst} {x:g} {y:g}")
                else:
                    for n, ax, ay, bx, by in bl:
                        if cx < bx and ax < cx + cw and cy < by and ay < cy + ch:
                            err = ("MACRO", f"exact packed bank overlaps hard macro {n}: {inst} {x:g} {y:g}")
                            break
                if err:
                    break
                reserve.append((cx, cy, cw, ch))
            if err:
                break
        if err:
            out.append(F("OVERLAP", inst, err[1], sub=err[0]))
        for r in reserve:                       # the kit reserves only after a clean row; keep going for later rows
            occ.reserve(*r)
    return out


# ---------------------------------------------------------------- plan mode
def _type_box_core(t):
    import kit_fit
    w, s, e, n = kit_fit.kit_core_area(t)
    ow, oh = t["outline_um"]
    return (w, s, e, n)


def ft_explicit_sites(P, tn, t):
    """[(x, y, w, h)] um of the ft_bit_sites.tcl the kit gets: ft_spread.spread_type + ft_bit_sites.snap_slots, as gen_phys does."""
    import ft_spread
    import kit_fit
    from ft_bit_sites import snap_slots
    try:
        slots, _ = ft_spread.spread_type(P, tn, t)
    except Exception:                           # gen: spread is never a failure, plan sites only
        slots = list(t.get("ft_slots", []) or [])
    slots, _ = snap_slots(slots, kit_fit.kit_core_area(t)[:2])
    out = []
    for s in slots:
        if not s.get("bit_sites_um"):
            continue
        cw, ch = s["bit_site_cell_um"]
        for st in s["bit_sites_um"]:
            out += [(float(x), float(y), float(cw), float(ch)) for x, y in st]
    return out


def packed_candidates(t):
    """[(label, banks, cell)] of the exact-bank rows the kit realises through is_packed_exact_banks: exact internal sites on an in bus,
    no bit_route, no face sites, one stage per planned register (kit_istations.packed_exact_geometry).  The u_lpad_<bus> RTL form
    itself comes from the bind; a row that is NOT a packed receiver in the bound RTL is marked in the finding as 'candidate'."""
    import kit_istations as KI
    width = {b["name"]: int(b.get("width", 1)) for b in t.get("buses") or [] if isinstance(b, dict) and "name" in b}
    dirs = {b["name"]: b.get("dir") for b in t.get("buses") or [] if isinstance(b, dict) and "name" in b}
    rows = []
    for e in t.get("internal_stations") or []:
        c = e.get("conn", "")
        if not c.startswith("bus:") or c[4:] not in width:
            continue
        bus = c[4:]
        try:
            ex = KI.exact_banks(e, width[bus])
        except (ValueError, KeyError, TypeError, IndexError, AssertionError):
            continue
        if ex is None or ex[2] is not None or dirs.get(bus) != "in" or len(ex[0]) != len(e.get("regs_um") or []):
            continue
        cell = ex[1] or CELL
        rows.append(("u_lpad_" + re.sub(r"\W", "_", bus), ex[0], (float(cell[0]), float(cell[1]))))
    return rows


def overlap_plan(P, tn, t):
    from schema import placed_macro_boxes
    rows = packed_candidates(t)
    if not rows:
        return []
    core = _type_box_core(t)
    occ = Occ(_d(core[1]))
    for x, y, w, h in ft_explicit_sites(P, tn, t):
        occ.reserve(_d(x), _d(y), _d(w), _d(h))
    blocks = [(n, *map(float, b[:4])) for n, b in placed_macro_boxes(t, halo=0.0).items()]
    fs = exact_bank_check(rows, occ, core, blocks)
    for f in fs:
        f["msg"] += "  [plan form; packed receiver confirmed only by the bound RTL]"
    return fs


def knee_plan(P, tn, t):
    """istation_knee.replay rule incl. leg_order along_first (kit passes order along); leg_order channel is another rule: unchecked."""
    import istation_knee as K
    import gen_phys as G
    out = []
    ents = [e for e in (t.get("internal_stations") or []) if e.get("bit_route") == "per_bit"]
    if not ents:
        return out
    pins = {}
    for bus, bit, ln, x, y, f in G.type_pins(P, tn):
        pins.setdefault(bus, {})[int(bit)] = (x, y)
    for e in ents:
        bus = e["conn"].split(":", 1)[1]
        b = next((x for x in t["buses"] if x["name"] == bus), None)
        bp = pins.get(bus) or {}
        if b is None or len(bp) not in (int(b["width"]), int(b["width"]) + 1) or e.get("leg_order") == "channel" or "leaf_um" not in e:
            continue
        n = len(e["regs_um"])
        first, second = K.legs(b["face"], b["dir"], e["leaf_um"], list(bp.values()), K.leaf_offset(t, b))
        if e.get("leg_order") == "along_first":
            first, second = second, first
        w, split = K.knee(first, second, n + 1)
        if w > K.KIT_LIMIT_UM - KNEE_NEAR_UM:
            near = w <= K.KIT_LIMIT_UM
            out.append(F("KNEE", f"{bus}", ("NEAR (kit pins differ from plan pins by ~2 um; failed at 404.7 from 401.x here): " if near else "") +
                         f"internal station knee needs a plan depth change: worst ideal hop {w:.3f} >403um "
                         f"(bus {bus} dir {b['dir']} face {b['face']} {n} stations; stations needed "
                         f"{K.stations_needed(b['face'], b['dir'], e['leaf_um'], list(bp.values()), n, K.KIT_LIMIT_UM, K.leaf_offset(t, b))})",
                         worst=round(w, 3), stations=n, sub="NEAR" if near else "FAIL"))
    return out


def macro_plan(P, tn, t):
    import kit_fit
    from kit_fit import CORE_MARGIN_UM
    return [F("MACRO", "kit_fit", s) for s in kit_fit.findings({tn: t}, core_margin=CORE_MARGIN_UM)]


def station_core_plan(P, tn, t):
    """STATION-CORE (FABLE-FIX-QC-SLE-R2 11-21): every station row (bus chains with no `core` key included) on the kit's per-bit
    site model against every hard macro; the kit prints no message for it, the build ends in flat GRT overflow (QC sle_ctl)."""
    import station_core as SC
    return [F("STATIONCORE", r["conn"], SC.line(tn, r), sub=r["kind"], sites_in_macro=r["sites_in_macro"],
              routes_crossing=r["routes_crossing"], macros=r["macros"]) for r in SC.report(P, tn)]


_CACHE = {}


def _load(plan_path):
    """one parse of the (60 MB) plan per worker process"""
    if _CACHE.get("path") != plan_path:
        import schema as S
        raw = json.load(open(plan_path))
        import copy
        _CACHE.update(path=plan_path, raw=raw, P=S.Plan(copy.deepcopy(raw), path=plan_path))
    return _CACHE["raw"], _CACHE["P"]


def check_type(args):
    plan_path, tn = args
    try:
        raw, P = _load(plan_path)
        t = raw["partition_types"][tn]
        out = []
        for fn in (overlap_plan, knee_plan, macro_plan, station_core_plan):
            try:
                out += fn(P, tn, t)
            except Exception as ex:
                out.append(F("ERROR", fn.__name__, f"{type(ex).__name__}: {ex}"[:300]))
        return tn, out
    except Exception as ex:
        return tn, [F("ERROR", "load", f"{type(ex).__name__}: {ex}"[:300], tb=traceback.format_exc()[-400:])]


def run_plan(plan, types=None, jobs=1):
    raw = json.load(open(plan))
    pt = raw["partition_types"]
    used = {p.get("type") for p in (raw["partitions"].values() if isinstance(raw["partitions"], dict) else raw["partitions"])}
    names = sorted(types or [n for n in pt if n in used or not used])
    work = [(str(plan), n) for n in names]
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            res = list(ex.map(check_type, work, chunksize=2))
    else:
        res = [check_type(w) for w in work]
    return names, dict(res)


# ---------------------------------------------------------------- kit mode (generated kit dir)
_SITE = re.compile(r"dict set ff_bit_sites \{([^,}]+),(\d+),(\d+)\} \{([-\d.e+]+) ([-\d.e+]+)\}")
_CELL = re.compile(r"dict set ff_bit_site_cells \{([^}]+)\} \{([-\d.e+]+) ([-\d.e+]+)\}")
_CALL = re.compile(r"^is_packed_exact_banks \{([^}]+)\} (\d+) (\d+) \{(.*)\} ([-\d.e+]+) ([-\d.e+]+) ist:(\S+) (\d)\s*$", re.M)
_NUM2 = re.compile(r"\{([-\d.e+]+) ([-\d.e+]+)\}")


def _parse_banks(s):
    """'{{x y} {x y}} {{x y}}' -> [[(x, y)..]..] (a bank is the second brace level)."""
    out = []
    for b in re.findall(r"\{((?:\{[^{}]*\}\s*)+)\}", s):
        out.append([(float(a), float(c)) for a, c in _NUM2.findall(b)])
    return out


def check_kit(kd):
    kd = Path(kd)
    out = []
    cfg = (kd / "config.mk").read_text()
    m = re.search(r"CORE_AREA\s*=\s*([-\d.e+]+) ([-\d.e+]+) ([-\d.e+]+) ([-\d.e+]+)", cfg)
    core = tuple(float(v) for v in m.groups()) if m else None
    env = {}
    try:
        env = json.load(open(kd / "kit_effective_env.json"))
    except Exception:
        pass
    ist = kd / "istations.tcl"
    calls = _CALL.findall(ist.read_text()) if ist.exists() else []
    if not calls:
        return out, dict(calls=0)
    occ = Occ(_d(core[1]))
    cells = {n: (float(w), float(h)) for n, w, h in _CELL.findall((kd / "ft_bit_sites.tcl").read_text())} if (kd / "ft_bit_sites.tcl").exists() else {}
    nft = 0
    if (kd / "ft_bit_sites.tcl").exists():
        for slot, j, bit, x, y in _SITE.findall((kd / "ft_bit_sites.tcl").read_text()):
            w, h = cells[slot]
            occ.reserve(_d(x), _d(y), _d(w), _d(h))
            nft += 1
    rows = [(inst, _parse_banks(tbl), (float(fw), float(fh))) for inst, W, D, tbl, fw, fh, tag, eu in calls]
    out = exact_bank_check(rows, occ, core, [])
    return out, dict(calls=len(calls), ft_sites=nft, core=core, land_reserve=env.get("OT_LAND_RESERVE"))


# ---------------------------------------------------------------- netlist checks (MPL-0020, CONE): kit dir + synth netlist
_OUT_PINS = {"Y", "QN", "Q", "CON", "SN", "H", "L"}          # ASAP7 output pin names
_SEQ = re.compile(r"^(DFF|DHL|DLL|SDF|ICG)")
_STD = re.compile(r"_ASAP7_75t_[A-Z]+$")
_NCELL = re.compile(r"^\s*(\S+)\s+(\\\S+|[A-Za-z_]\w*)\s*\((.*?)\);", re.S | re.M)
_PIN = re.compile(r"\.(\w+)\(([^()]*)\)")


def read_netlist(path):
    """-> (cells {name: (master, {pin: net})}, nets {net: [(cell, is_output)]}); names without the yosys escapes."""
    txt = open(path, errors="replace").read()
    cells, nets = {}, collections.defaultdict(list)
    for m in _NCELL.finditer(txt):
        master, name, body = m.group(1), m.group(2), m.group(3)
        if master in ("module", "input", "output", "wire", "assign", "endmodule", "reg"):
            continue
        name = name.replace("\\", "").strip()
        pins = {pn: net.strip() for pn, net in _PIN.findall(body)}
        cells[name] = (master, pins)
        for pn, net in pins.items():
            if net:
                nets[net].append((name, pn in _OUT_PINS))
    return cells, nets


def mpl0020(kit, cells):
    """macro_place.tcl `place_macro -macro_name {X}`: X must be an instance of the synthesised netlist (else MPL-0020)."""
    out = []
    mp = Path(kit) / "macro_place.tcl"
    if not mp.exists():
        return out
    names = [m.replace("\\[", "[").replace("\\]", "]").replace("\\", "")
             for m in re.findall(r"place_macro -macro_name \{([^}]+)\}", mp.read_text())]
    for n in names:
        if n not in cells:
            out.append(F("MPL0020", n, f"[ERROR MPL-0020] Couldn't find a macro named {n}."))
    return out


def cone_regions(kit, cells, nets, limit=8):
    """place_regions.tcl ot_pr_cone on the synth netlist for each place_regions_data.tcl row (members = cells matching inst_re that are
    not macros; FIRM cells are not excluded, so the member count can exceed the kit's by the pin/station registers)."""
    out = []
    pr = Path(kit) / "place_regions_data.tcl"
    if not pr.exists():
        return out
    # PLACE-GROUP 11-22: a row may carry kind / box / radius after near_re (gen_phys.place_regions_tcl)
    rows = re.findall(r"^\s*\{(\S+) \{([^}]*)\} ([\d.]+) (\S+) (\S+) \{([^}]*)\}(?: \S+ \{[^}]*\} \S+)?\}", pr.read_text(), re.M)
    macro = {n for n, (m, _) in cells.items() if not _STD.search(m)}
    seq = {n for n, (m, _) in cells.items() if _SEQ.match(m)}
    for name, inst_re, util, cx, cy, near in rows:
        rx = re.compile(inst_re)
        members = [n for n in cells if n not in macro and rx.search(n)]
        if not members:
            out.append(F("CONE", name, f"OT_PLACE_REGION {name}: inst_re '{inst_re}' matches no movable standard cell"))
            continue
        seen, extra, queue = set(members), 0, collections.deque(members)
        cap = limit * len(members)
        nbr = lambda c: [x for pn, net in cells[c][1].items() if net and len(nets[net]) <= 256 for x, _o in nets[net] if x != c]
        while queue and extra <= cap:
            cur = queue.popleft()
            for nb in nbr(cur):
                if nb in seen:
                    continue
                seen.add(nb)
                if nb in macro or nb in seq:
                    continue
                extra += 1
                queue.append(nb)
                if extra > cap:
                    break
        if extra > cap:
            out.append(F("CONE", name, f"cone has more than {cap} cells (> {limit} x {len(members)} members): not separable from the design "
                         f"(tools >= 124d829 DROP this region; older tools stop global_place)", members=len(members), sub="DROP"))
    return out


def check_kit_netlist(kit, netlist=None):
    kit = Path(kit)
    nl = netlist or next(iter(sorted(kit.glob("run/results/asap7/*/base/1_2_yosys.v"))), None)
    if not nl:
        return [], dict(netlist=None)
    cells, nets = read_netlist(nl)
    return mpl0020(kit, cells) + cone_regions(kit, cells, nets), dict(netlist=str(nl), cells=len(cells))


def write_report(findings, out):
    os.makedirs(out, exist_ok=True)
    types_by = collections.defaultdict(set)
    for f in findings:
        types_by[f["cls"]].add(f["type"])
    json.dump(dict(schema="opentallas.place_precheck.v1", advisory=True, findings=findings,
                   by_class={c: sorted(v) for c, v in types_by.items()}), open(Path(out) / "place_precheck.json", "w"), indent=1)
    with open(Path(out) / "place_precheck.tsv", "w") as fh:
        fh.write("class\ttype\tmode\tmessage\n")
        for f in findings:
            fh.write(f"{f['cls']}\t{f['type']}\t{f['mode']}\t{f['msg']}\n")


def summary(findings, ntypes, label):
    """one post line: per class the number of types and up to 6 example types with a tail of the message"""
    by = collections.defaultdict(dict)
    for f in findings:
        by[f["cls"]].setdefault(f["type"], f)
    parts = []
    for c in [c for c in CLASSES if c in by] + [c for c in by if c not in CLASSES]:
        ex = "; ".join(f"{t} ({f['msg'][:70]})" for t, f in list(by[c].items())[:6])
        parts.append(f"{c} {len(by[c])} type(s): {ex}" + (f"; +{len(by[c]) - 6} more" if len(by[c]) > 6 else ""))
    head = f"PLACE-PRECHECK {label}: {ntypes} types checked, " + (f"{len(set(f['type'] for f in findings))} with findings" if findings else "no findings")
    return head + ". Advisory, not a gate (kit place guards decided statically)." + ("\n" + "\n".join(parts) if parts else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan")
    ap.add_argument("--kit", action="append", default=[])
    ap.add_argument("--netlist", help="synth netlist (1_2_yosys.v) for the --kit MPL-0020 / CONE checks; default: the kit's own run/results")
    ap.add_argument("--types")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", help="directory for place_precheck.json + .tsv")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    findings = []
    if a.plan:
        names, res = run_plan(a.plan, a.types.split(",") if a.types else None, a.jobs)
        for tn in names:
            for f in res[tn]:
                findings.append(dict(f, type=tn, mode="plan"))
        print(f"place_precheck plan {a.plan}: {len(names)} types checked")
    for kd in a.kit:
        fs, info = check_kit(kd)
        for f in fs:
            findings.append(dict(f, type=Path(kd).name, mode="kit"))
        nf, ninfo = check_kit_netlist(kd, a.netlist)
        for f in nf:
            findings.append(dict(f, type=Path(kd).name, mode="kit"))
        print(f"place_precheck kit {kd}: {info} {ninfo}")
    by = collections.Counter((f["cls"], f.get("sub", "")) for f in findings)
    types_by = collections.defaultdict(set)
    for f in findings:
        types_by[f["cls"]].add(f["type"])
    for c in list(CLASSES) + ["ERROR"]:
        if types_by.get(c):
            print(f"  {c}: {len(types_by[c])} type(s)")
    for f in findings:
        print(f"{f['cls']}\t{f['type']}\t{f['msg']}")
    if a.out:
        write_report(findings, a.out)
    return 1 if (a.strict and findings) else 0


if __name__ == "__main__":
    sys.exit(main())
