"""Master-plan slices for partition / core kits (METHODOLOGY 12.7c, OWNER 2026-10-26).

Every partition/core kit consumes its slice of the die master plan (outline, keep-outs, islands, bays, entry pins,
latency target).  A slice is one JSON file per partition type / core module (schema opentallas.master_plan_slice.v1,
type/core frame um, rects [x0, y0, x1, y1]) written by the master-plan tool into a slice directory DIR/<name>.json.

Kit generators take it OPT-IN (`--master-slice DIR`).  Once the die plan carries "master_plan": {"required": true,
"sha256": ...} (set at the plan freeze through COORD) or OT_MASTER_PLAN_REQUIRED=1 is exported, a sign-off kit
without a slice is refused; `--trial` kits (not sign-off) stay allowed and are stamped "TRIAL-NO-SLICE".

  load(path) / validate(slice)       schema check (validate returns the error list; load raises SliceError)
  find(slice_dir, name)              DIR/<name>.json
  required(plan_raw)                 plan "master_plan.required" is True or env OT_MASTER_PLAN_REQUIRED=1
  check_against(slice, outline, sha) outline equal to 1e-3 um; slice master_plan_sha256 == the plan's (stale refused)
  emit_tcl(slice, dbu)               OpenROAD Tcl: placement blockages, routing obstructions, bays / entry-pin dicts
  stamp(slice)                       {slice_sha256, master_plan_sha256, type, frozen} for the kit budget
  add_args(ap) / precheck(...)       generator CLI flags (--master-slice DIR, --trial) / early refusal
  kit_apply(...)                     the generator hook: refuse / copy / Tcl / stamp in one call
  clock_entry_ports(slice)           MULTI-ROOT slices (S81-CORE-LAT-R21): the root pins of "clock_entries"

Multi-root core slices (S81-CORE-LAT-R21, COORD S81-CORE-LAT-R20 ruling (e); the declared multi-root cores of
gen_core_kit_legacy multi_root_contract, 12.2a/12.8a "one entry / island per root"): instead of the single-root form
(one island clock_pin + core_clock_port / core_tree) the slice lists one entry PER ROOT PIN:
  "clock_entries": [{"port": "cr" | "xk[0]", "clock": SDC clock name (optional), "island": <islands[].name>,
                     "clock_pin": {"layer": "M5", "xy_um": [x, y]},
                     "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 40}}, ...]
Rules (all hard): every port once, every island once and existing, the clock_pin inside the outline AND inside its
island rect, a per-entry 12.3 latency (TT and FF); no island of a multi-root slice carries its own clock_pin and the
slice has no core_clock_port / pushdown core_tree (one plan tree per root is not compiled by core_infra yet: refused,
fail-closed, rather than one tree on the primary root), except the explicit opt-ins core_tree.root_scope (one planned
root + ordinary roots) and "core_forest" (one ordinary core_tree body per root, disjoint sink/cell owners, ports ==
clock_entries ports exactly; core_infra.validate_forest).  The kit consumes every entry like the single clock entry
(GEOM-21 M5 track snap + full-width shape) and check_kit verifies each, plus the kit's clock_roots.json (pins and
the per-root 12.3 budget) against the entries.
"""
import hashlib
import json
import math
import os
import re
import shutil
from pathlib import Path

SCHEMA = "opentallas.master_plan_slice.v1"
KINDS = ("partition", "core")
KEEPOUT_KINDS = ("island", "in_core_bay", "clock_shield", "hard_core")
BAY_KINDS = ("station", "repeater")
OUTLINE_TOL_UM = 1e-3
TRIAL = "TRIAL-NO-SLICE"
HOOK_LINE = "if {[file exists /work/master_slice.tcl]} { source /work/master_slice.tcl }\n"
REFUSE = ("sign-off kit refused: no master-plan slice (METHODOLOGY 12.7c); pass --master-slice or --trial")


class SliceError(ValueError):
    pass


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _rect(v, where, errs, outline=None):
    if not (isinstance(v, (list, tuple)) and len(v) == 4 and all(_num(x) for x in v)):
        errs.append(f"{where}: rect_um must be [x0, y0, x1, y1] numbers, got {v!r}")
        return False
    x0, y0, x1, y1 = v
    if not (x0 < x1 and y0 < y1):
        errs.append(f"{where}: empty rect {list(v)}")
        return False
    if outline:
        w, h = outline
        t = OUTLINE_TOL_UM
        if x0 < -t or y0 < -t or x1 > w + t or y1 > h + t:
            errs.append(f"{where}: rect {list(v)} outside the outline {w:g} x {h:g}")
            return False
    return True


def _xy(v, where, errs, outline=None):
    if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(_num(x) for x in v)):
        errs.append(f"{where}: xy must be [x, y] numbers, got {v!r}")
        return False
    if outline:
        t = OUTLINE_TOL_UM
        if not (-t <= v[0] <= outline[0] + t and -t <= v[1] <= outline[1] + t):
            errs.append(f"{where}: point {list(v)} outside the outline {outline[0]:g} x {outline[1]:g}")
            return False
    return True


def _named(lst, key, errs):
    if lst is None:
        return []
    if not isinstance(lst, list):
        errs.append(f"{key}: must be a list")
        return []
    names = [e.get("name") for e in lst if isinstance(e, dict)]
    dup = sorted({n for n in names if n is not None and names.count(n) > 1})
    if dup:
        errs.append(f"{key}: duplicate names {dup[:5]}")
    for i, e in enumerate(lst):
        if not isinstance(e, dict):
            errs.append(f"{key}[{i}]: must be an object")
    return [e for e in lst if isinstance(e, dict)]


def validate(sl):
    """Schema check of a slice dict; returns the list of errors (all hard: a kit is refused on any)."""
    errs = []
    if not isinstance(sl, dict):
        return ["slice: must be a JSON object"]
    if sl.get("schema") != SCHEMA:
        errs.append(f"schema: expected {SCHEMA!r}, got {sl.get('schema')!r}")
    if sl.get("kind") not in KINDS:
        errs.append(f"kind: expected one of {KINDS}, got {sl.get('kind')!r}")
    for k in ("die", "type", "module"):
        if not (isinstance(sl.get(k), str) and sl.get(k)):
            errs.append(f"{k}: non-empty string required")
    if not isinstance(sl.get("master_plan_sha256"), str) or not sl.get("master_plan_sha256"):
        errs.append("master_plan_sha256: non-empty string required")
    if not isinstance(sl.get("frozen"), bool):
        errs.append("frozen: boolean required")
    if not isinstance(sl.get("instances", []), list):
        errs.append("instances: must be a list")
    ol = sl.get("outline_um")
    outline = None
    if isinstance(ol, (list, tuple)) and len(ol) == 2 and all(_num(x) and x > 0 for x in ol):
        outline = (float(ol[0]), float(ol[1]))
    else:
        errs.append(f"outline_um: [w, h] positive numbers required, got {ol!r}")
    for i, k in enumerate(_named(sl.get("keepouts"), "keepouts", errs)):
        w = f"keepouts[{k.get('name', i)}]"
        _rect(k.get("rect_um"), w, errs, outline)
        if k.get("kind") not in KEEPOUT_KINDS:
            errs.append(f"{w}: kind expected one of {KEEPOUT_KINDS}, got {k.get('kind')!r}")
        use, layers = k.get("use", []), k.get("layers", [])
        if not isinstance(use, list) or any(u != "placement" for u in use):
            errs.append(f"{w}: use must be a list of 'placement', got {use!r}")
        if not isinstance(layers, list) or any(not (isinstance(x, str) and x) for x in layers):
            errs.append(f"{w}: layers must be a list of layer names, got {layers!r}")
        if not use and not layers:
            errs.append(f"{w}: keeps nothing out (no 'placement' use, no layers)")
    for i, k in enumerate(_named(sl.get("islands"), "islands", errs)):
        w = f"islands[{k.get('name', i)}]"
        if _rect(k.get("rect_um"), w, errs, outline) and k.get("centre_um") is not None:
            if _xy(k["centre_um"], w + ".centre_um", errs):
                x0, y0, x1, y1 = k["rect_um"]
                cx, cy = k["centre_um"]
                if not (x0 <= cx <= x1 and y0 <= cy <= y1):
                    errs.append(f"{w}: centre_um {list(k['centre_um'])} outside its rect")
        cp = k.get("clock_pin")
        if cp is not None:
            if not (isinstance(cp, dict) and isinstance(cp.get("layer"), str)):
                errs.append(f"{w}: clock_pin must be null or {{layer, xy_um}}")
            else:
                _xy(cp.get("xy_um"), w + ".clock_pin", errs, outline)
    bays = _named(sl.get("bays"), "bays", errs)
    for i, b in enumerate(bays):
        w = f"bays[{b.get('name', i)}]"
        if not b.get("name"):
            errs.append(f"{w}: name required")
        _rect(b.get("rect_um"), w, errs, outline)
        if "regions_um" in b:
            regions = b["regions_um"]
            if not isinstance(regions,list) or not regions:
                errs.append(f"{w}: regions_um must be a nonempty rectangle list")
            else:
                for j,r in enumerate(regions):
                    if _rect(r,f"{w}.regions_um[{j}]",errs,outline) and b.get("rect_um"):
                        q=b["rect_um"]
                        if r[0]<q[0]-OUTLINE_TOL_UM or r[1]<q[1]-OUTLINE_TOL_UM or r[2]>q[2]+OUTLINE_TOL_UM or r[3]>q[3]+OUTLINE_TOL_UM:
                            errs.append(f"{w}: region outside bay envelope")
        if b.get("kind") not in BAY_KINDS:
            errs.append(f"{w}: kind expected one of {BAY_KINDS}, got {b.get('kind')!r}")
        for n in ("bits", "cell_area_um2", "fill"):
            if n in b and not (_num(b[n]) and b[n] >= 0):
                errs.append(f"{w}: {n} must be a non-negative number")
    bay_names = {b.get("name") for b in bays}
    pins = _named(sl.get("entry_pins"), "entry_pins", errs)
    seen = {}
    for i, p in enumerate(pins):
        w = f"entry_pins[{p.get('name', i)}]"
        if not p.get("name"):
            errs.append(f"{w}: name required")
        if p.get("pin") is not None and not (isinstance(p["pin"], str) and p["pin"]):
            errs.append(f"{w}: pin must be null or a pin name")
        if not (isinstance(p.get("layer"), str) and p["layer"]):
            errs.append(f"{w}: layer required")
        _xy(p.get("xy_um"), w, errs, outline)
        if p.get("bay") is not None and p["bay"] not in bay_names:
            errs.append(f"{w}: bay {p['bay']!r} is not a bay of this slice")
        if p.get("pin"):
            if p["pin"] in seen:
                errs.append(f"{w}: pin {p['pin']!r} also bound by entry pin {seen[p['pin']]!r}")
            seen[p["pin"]] = p.get("name")
    for i, c in enumerate(_named(sl.get("hard_cores"), "hard_cores", errs)):
        w = f"hard_cores[{c.get('inst', i)}]"
        if _xy(c.get("origin_um"), w + ".origin_um", errs) and isinstance(c.get("outline_um"), (list, tuple)) \
                and len(c["outline_um"]) == 2 and all(_num(x) for x in c["outline_um"]):
            x, y = c["origin_um"]
            cw, ch = c["outline_um"]
            if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
                cw, ch = ch, cw
            _rect([x, y, x + cw, y + ch], w, errs, outline)
        else:
            errs.append(f"{w}: origin_um / outline_um required")
    ents = sl.get("clock_entries")
    if ents is not None:
        _validate_clock_entries(sl, ents, outline, errs)
    elif sl.get("core_forest") is not None:
        errs.append("core_forest: a forest is a multi-root slice; clock_entries (one per root) required")
    lat = sl.get("latency")
    if lat is not None:
        cl = lat.get("common_clock_latency_ps") if isinstance(lat, dict) else None
        if not (isinstance(cl, dict) and all(_num(v) for v in cl.values())):
            errs.append("latency.common_clock_latency_ps: {corner: ps} required")
    for i, c in enumerate(sl.get("corridors", []) or []):
        if not (isinstance(c, dict) and isinstance(c.get("polyline_um"), list)):
            errs.append(f"corridors[{i}]: polyline_um list of [x, y] required")
            continue
        for q in c["polyline_um"]:
            _xy(q, f"corridors[{i}]", errs)
    g = sl.get("gates", {})
    if not isinstance(g, dict) or any(v not in ("PASS", "FAIL", "NOT RUN") for v in g.values()):
        errs.append("gates: {gate: PASS|FAIL|NOT RUN} required")
    return errs


def _validate_clock_entries(sl, ents, outline, errs):
    if not isinstance(ents, list) or not ents:
        errs.append("clock_entries: non-empty list required (omit it for a single-root slice)")
        return
    isl = {i.get("name"): i for i in sl.get("islands", []) or [] if isinstance(i, dict)}
    ports, used = {}, {}
    for i, e in enumerate(ents):
        w = f"clock_entries[{e.get('port', i) if isinstance(e, dict) else i}]"
        if not isinstance(e, dict):
            errs.append(f"{w}: must be an object")
            continue
        pt = e.get("port")
        if not (isinstance(pt, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\[[0-9]+\])?", pt or "")):
            errs.append(f"{w}: port must be a pin name (bus bits as name[i]), got {pt!r}")
        elif pt in ports:
            errs.append(f"{w}: port {pt!r} listed twice")
        ports[pt] = i
        nm = e.get("island")
        if nm not in isl:
            errs.append(f"{w}: island {nm!r} is not an island of this slice")
        elif nm in used:
            errs.append(f"{w}: island {nm!r} also the entry of {used[nm]!r} (one island per root)")
        used[nm] = pt
        cp = e.get("clock_pin")
        if not (isinstance(cp, dict) and isinstance(cp.get("layer"), str)):
            errs.append(f"{w}: clock_pin {{layer, xy_um}} required")
        elif _xy(cp.get("xy_um"), w + ".clock_pin", errs, outline) and nm in isl and _num_rect(isl[nm].get("rect_um")):
            x0, y0, x1, y1 = isl[nm]["rect_um"]
            x, y = cp["xy_um"]
            t = OUTLINE_TOL_UM
            if not (x0 - t <= x <= x1 + t and y0 - t <= y <= y1 + t):
                errs.append(f"{w}: clock_pin {list(cp['xy_um'])} outside island {nm} {list(isl[nm]['rect_um'])}")
        cl = (e.get("latency") or {}).get("common_clock_latency_ps") if isinstance(e.get("latency"), dict) else None
        if not (isinstance(cl, dict) and all(_num(cl.get(c)) for c in ("TT", "FF"))):
            errs.append(f"{w}: latency.common_clock_latency_ps {{TT, FF}} required (12.3, one budget per root)")
        if e.get("clock") is not None and not (isinstance(e["clock"], str) and e["clock"]):
            errs.append(f"{w}: clock must be null or an SDC clock name")
    for i in isl.values():
        if i.get("clock_pin"):
            errs.append(f"islands[{i.get('name')}]: multi-root slice: the entry is clock_entries[], not islands[].clock_pin")
    tree = sl.get("core_tree")
    if sl.get("core_forest") is not None:
        # DIE-QC-47 COLLFT (default off): one ordinary plan tree per root, disjoint owners (core_infra.validate_forest)
        import core_infra
        try:
            core_infra.validate_forest(sl)
        except core_infra.InfraError as exc:
            errs.append(str(exc))
    elif tree and tree.get("root_scope") is not None:
        import core_infra
        try:
            core_infra.validate_root_scope(tree, ents)
        except core_infra.InfraError as exc:
            errs.append(str(exc))
        if sl.get("core_clock_port") or (sl.get("pushdown") or {}).get("core_tree"):
            errs.append("clock_entries: scoped tree lives in core_tree only; core_clock_port/pushdown.core_tree refused")
    elif sl.get("core_clock_port") or (sl.get("pushdown") or {}).get("core_tree") or tree:
        errs.append("clock_entries: a multi-root slice has no core_clock_port / core_tree (per-root plan trees are not "
                    "compiled by core_infra yet: refused)")


def _num_rect(r):
    return isinstance(r, (list, tuple)) and len(r) == 4 and all(_num(x) for x in r)


def clock_entry_ports(sl):
    """root pins of a multi-root slice (clock_entries[].port, slice order); [] for a single-root slice."""
    return [e["port"] for e in sl.get("clock_entries") or [] if isinstance(e, dict) and e.get("port")]


def load(path):
    path = Path(path)
    try:
        sl = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise SliceError(f"master-plan slice {path}: unreadable ({e})")
    errs = validate(sl)
    if errs:
        raise SliceError(f"master-plan slice {path}: {len(errs)} error(s): " + "; ".join(errs[:10]))
    return sl


def find(slice_dir, name):
    p = Path(slice_dir) / f"{name}.json"
    if not p.is_file():
        raise SliceError(f"master-plan slice for {name!r} not found: {p}")
    return p


def required(plan_raw=None):
    mp = (plan_raw or {}).get("master_plan", {}) if isinstance(plan_raw, dict) else {}
    return (isinstance(mp, dict) and mp.get("required") is True) or os.environ.get("OT_MASTER_PLAN_REQUIRED") == "1"


def plan_sha(plan_raw=None):
    mp = (plan_raw or {}).get("master_plan", {}) if isinstance(plan_raw, dict) else {}
    return mp.get("sha256") if isinstance(mp, dict) else None


def check_against(sl, outline_um, plan_sha256=None):
    """Raise SliceError when the slice does not fit this kit: outline (1e-3 um) or a stale master plan."""
    so = sl["outline_um"]
    if len(outline_um) != 2 or any(abs(float(a) - float(b)) > OUTLINE_TOL_UM for a, b in zip(so, outline_um)):
        raise SliceError(f"master-plan slice {sl['type']}: outline {list(so)} != kit outline {list(outline_um)}")
    if plan_sha256 and sl.get("master_plan_sha256") != plan_sha256:
        raise SliceError(f"master-plan slice {sl['type']}: stale (master_plan_sha256 {sl.get('master_plan_sha256')} "
                         f"!= plan master_plan.sha256 {plan_sha256})")
    return True


def digest(sl):
    return hashlib.sha256(json.dumps(sl, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def stamp(sl):
    return dict(slice_sha256=digest(sl), master_plan_sha256=sl.get("master_plan_sha256"), type=sl.get("type"),
                frozen=bool(sl.get("frozen")))


def _d(v, dbu):
    return int(round(float(v) * dbu))


def _tcl_word(s):
    return "{" + str(s).replace("{", "").replace("}", "") + "}"


def emit_tcl(sl, dbu=1000):
    """OpenROAD Tcl for the kit (type frame = kit DIE_AREA frame).  Idempotent: a blockage / obstruction with the
    same box is not created twice (PRE_GLOBAL_PLACE hooks run in more than one ORFS step)."""
    t = sl["type"]
    L = [f"# GENERATED by tools/die_plan/master_slice.py: master-plan slice of {t} (METHODOLOGY 12.7c)",
         f"# master_plan_sha256 {sl.get('master_plan_sha256')}  slice_sha256 {digest(sl)}  frozen {bool(sl.get('frozen'))}",
         f"# coordinates in DBU at {dbu}/um, type frame (= kit DIE_AREA frame)",
         "uplevel #0 {",
         "set ms_b [ord::get_db_block]",
         "set ms_tech [ord::get_db_tech]",
         f"if {{[$ms_tech getDbUnitsPerMicron] != {dbu}}} {{ error \"master_slice.tcl: emitted at {dbu} DBU/um, "
         "tech has [$ms_tech getDbUnitsPerMicron]\" }",
         "if {![llength [info procs ot_clear_keepout_physical]] && [file exists /work/keepout_phys.tcl]} "
         "{ source /work/keepout_phys.tcl }",
         "proc ot_ms_blockage {b x0 y0 x1 y1} {",
         "  foreach k [$b getBlockages] { set q [$k getBBox]",
         "    if {[$q xMin]==$x0 && [$q yMin]==$y0 && [$q xMax]==$x1 && [$q yMax]==$y1} { return 0 } }",
         "  odb::dbBlockage_create $b $x0 $y0 $x1 $y1; return 1",
         "}",
         "proc ot_ms_obstruction {b ln x0 y0 x1 y1} {",
         "  set l [[ord::get_db_tech] findLayer $ln]",
         "  if {$l eq \"NULL\" || $l eq \"\"} { error \"master_slice.tcl: no layer $ln\" }",
         "  foreach o [$b getObstructions] { set q [$o getBBox]",
         "    if {[[$q getTechLayer] getName] eq $ln && [$q xMin]==$x0 && [$q yMin]==$y0 && [$q xMax]==$x1 && "
         "[$q yMax]==$y1} { return 0 } }",
         "  odb::dbObstruction_create $b $l $x0 $y0 $x1 $y1; return 1",
         "}",
         "set ms_place {}; set ms_nb 0; set ms_no 0"]
    place = []
    # 12.2a1 + COORD (MASTER-PLAN-R2 ruling): islands of cores AND partitions are pushdown cells, never strip
    # placement blockages; core_infra places the fixed cells and their ft ports
    pushdown = bool(sl.get("pushdown"))
    for i in sl.get("islands", []) or []:
        if not pushdown:
            place.append((f"island {i.get('name')}", i["rect_um"]))
    for k in sl.get("keepouts", []) or []:
        if pushdown and k.get("kind") == "island":
            continue  # 12.2a1: the fixed core-owned cells replace the old hole
        if "placement" in (k.get("use") or []):
            place.append((f"keepout {k.get('name')} ({k.get('kind')})", k["rect_um"]))
    for what, r in place:
        x0, y0, x1, y1 = (_d(v, dbu) for v in r)
        L += [f"# placement blockage: {what}",
              f"incr ms_nb [ot_ms_blockage $ms_b {x0} {y0} {x1} {y1}]; lappend ms_place [list {x0} {y0} {x1} {y1}]"]
    for k in sl.get("keepouts", []) or []:
        if pushdown and k.get("kind") == "island":
            continue  # no cut-out routing obstruction over pushdown cells
        x0, y0, x1, y1 = (_d(v, dbu) for v in k["rect_um"])
        for ln in k.get("layers") or []:
            L.append(f"incr ms_no [ot_ms_obstruction $ms_b {ln} {x0} {y0} {x1} {y1}]   ;# keepout {k.get('name')}")
    L.append("if {[llength $ms_place] && [llength [info procs ot_clear_keepout_physical]]} "
             "{ ot_clear_keepout_physical $ms_b $ms_place master_plan_slice }")
    # bays: named rects only.  Cells are not known at floorplan time; the ft station / repeater steps that own the
    # cells read this dict (no cell-to-bay assignment is made here).
    L.append("# bays (um, type frame): name -> {kind rect_um layer bits fill owner}; consumers: ft station / repeater "
             "placement.  No cell-to-bay assignment is made here.")
    L.append("set ot_master_bays [dict create]")
    for b in sl.get("bays", []) or []:
        r = " ".join(f"{v:g}" for v in b["rect_um"])
        L.append(f"dict set ot_master_bays {_tcl_word(b['name'])} [dict create kind {b.get('kind')} rect_um {{{r}}} "
                 f"layer {b.get('layer', 'M7')} bits {b.get('bits', 0)} fill {b.get('fill', 0)} "
                 f"owner {_tcl_word(b.get('owner', ''))}]")
        if b.get("regions_um"):
            regions = " ".join("{" + " ".join(f"{v:g}" for v in q) + "}" for q in b["regions_um"])
            L.append(f"dict set ot_master_bays {_tcl_word(b['name'])} regions_um {{{regions}}}")
    L.append("# entry pins without a bound pin name (um, type frame): name -> {layer xy_um bay path bit}; for io.tcl")
    L.append("set ot_master_entry_pins [dict create]")
    nplaced = 0
    for p in sl.get("entry_pins", []) or []:
        x, y = p["xy_um"]
        if p.get("pin") and pushdown:
            nplaced += 1          # placed (fail-closed on a missing port) by master_core_infra.tcl ot_ci_entry
        elif p.get("pin") and p["pin"] == sl.get("core_clock_port"):
            # _consume_io already places the declared core clock with its full-width,
            # on-track GEOM-21 shape. A generic entry placement here would replace
            # it with the smaller signal-pin geometry and the unsnapped source xy.
            nplaced += 1
        elif p.get("pin"):
            L.append(f"place_pin -pin_name {_tcl_word(p['pin'])} -layer {p.get('layer', 'M7')} "
                     f"-location {{{x:.4f} {y:.4f}}} -pin_size {{0.032 0.192}}   ;# entry {p.get('name')}")
            nplaced += 1
        else:
            L.append(f"dict set ot_master_entry_pins {_tcl_word(p['name'])} [dict create layer {p.get('layer', 'M7')} "
                     f"xy_um {{{x:g} {y:g}}} bay {_tcl_word(p.get('bay') or '')} path {_tcl_word(p.get('path') or '')} "
                     f"bit {p.get('bit', 0)}]")
    L.append(f'puts "OT_MASTER_SLICE type={t} blockages_new=$ms_nb obstructions_new=$ms_no '
             f'bays=[dict size $ot_master_bays] entry_pins_placed={nplaced} '
             f'entry_pins_unbound=[dict size $ot_master_entry_pins]"')
    if pushdown:
        L.append("source /work/master_core_infra.tcl")
    L.append("}")
    return "\n".join(L) + "\n"


def add_args(ap):
    """--master-slice DIR (opt-in) and --trial on a kit generator's argparse parser."""
    ap.add_argument("--master-slice", metavar="DIR", default=None,
                    help="METHODOLOGY 12.7c: master-plan slices DIR/<type or module>.json (opt-in; required once the plan "
                         "sets master_plan.required or OT_MASTER_PLAN_REQUIRED=1)")
    ap.add_argument("--trial", action="store_true",
                    help="trial kit (not sign-off): allowed without a master-plan slice when one is required")


def precheck(slice_dir, trial, plan_raw=None, name="kit"):
    """Fail closed BEFORE a generator writes or removes anything: required and no slice and not --trial."""
    if not slice_dir and not trial and required(plan_raw):
        raise SystemExit(f"{name}: {REFUSE}")


def resolve(slice_dir, name, outline_um, plan_raw=None, trial=False, kind=None):
    """(path, slice) of DIR/<name>.json after every check, writing nothing: schema, kind, type/module name, outline,
    stale master plan, and (once required, unless --trial) a frozen master plan."""
    p = find(slice_dir, name)
    sl = load(p)
    if kind and sl["kind"] != kind:
        raise SliceError(f"master-plan slice {p}: kind {sl['kind']!r}, this generator needs {kind!r}")
    if sl["type"] != name and sl.get("module") != name:
        raise SliceError(f"master-plan slice {p}: type {sl['type']!r} / module {sl.get('module')!r} != {name!r}")
    check_against(sl, outline_um, plan_sha(plan_raw))
    if required(plan_raw) and not sl.get("frozen") and not trial:
        raise SystemExit(f"{name}: sign-off kit refused: master-plan slice {p} is not from a frozen master plan "
                         "(METHODOLOGY 12.7c); pass --trial for a trial kit")
    return p, sl


def kit_apply(kd, name, outline_um, slice_dir=None, plan_raw=None, trial=False, kind=None, gpl_hook=None,
              clock_ports=None, reset_ports=None):
    """Generator hook.  Returns the budget value: stamp dict (slice given), TRIAL (required, --trial, no slice) or
    None (not required, no slice: the kit is unchanged).  Raises SystemExit when a sign-off kit has no slice, and
    SliceError when the slice does not fit.  gpl_hook: a kit Tcl file (PRE_GLOBAL_PLACE) the guarded
    `source /work/master_slice.tcl` line is prepended to."""
    req = required(plan_raw)
    if not slice_dir:
        if req and not trial:
            raise SystemExit(f"{name}: {REFUSE}")
        return TRIAL if req else None
    p, sl = resolve(slice_dir, name, outline_um, plan_raw, trial, kind)
    kd = Path(kd)
    if len([p_ for p_ in (clock_ports or []) if p_]) > 1 and not clock_entry_ports(sl):
        raise SliceError(f"multi-root kit (root pins {sorted(clock_ports)}) needs a slice with clock_entries[] "
                         f"(one entry per root), got the single-entry form")
    if clock_entry_ports(sl):
        want = sorted(clock_entry_ports(sl))
        if clock_ports is None or sorted(p_ for p_ in clock_ports if p_) != want:
            raise SliceError(f"multi-root slice entries {want} != generator root pins {sorted(clock_ports or [])}")
    if sl.get("pushdown"):
        import core_infra
        effective = sl
        explicit = [p for p in (clock_ports or []) if p] if not clock_entry_ports(sl) else []
        if explicit:
            if len(explicit) != 1:
                raise SliceError("core infrastructure needs exactly one manifest clock port")
            declared = sl.get("core_clock_port") or (sl.get("core_tree") or {}).get("clock_port")
            if declared and declared != explicit[0]:
                raise SliceError(f"slice clock port {declared!r} differs from generator manifest {explicit[0]!r}")
            effective = dict(sl, core_clock_port=explicit[0])
        core_infra.install(kd, effective)
        # COORD 10-26 12:55 (12.2a1): the declared ft ports are die-timed -- ft-safe kit SDC + interface model
        if (kd / "constraint.sdc").is_file() and (kd / "sdc_lint.json").is_file():
            import ft_ports
            ft_ports.install(kd)
    shutil.copyfile(p, kd / "master_slice.json")
    (kd / "master_slice.tcl").write_text(emit_tcl(sl))
    _consume_io(kd, sl, _clock_port(kd, sl))
    if not (kd / "keepout_phys.tcl").is_file():
        shutil.copyfile(Path(__file__).with_name("keepout_phys.tcl"), kd / "keepout_phys.tcl")
    if gpl_hook:
        h = Path(gpl_hook)
        h.write_text(HOOK_LINE + h.read_text())
    return stamp(sl)


def plan_tree_cts(kd, cfg):
    """Generator hook, AFTER kit_apply and BEFORE config.mk is written (CTS-HOOK-PORT-1): a kit whose slice carries a
    plan-built core tree gets the shared plan-tree CTS hook (core_infra.kit_cts_hook: TritonCTS only on the plan's
    CTS-open nets, post-CTS tap balance / leaf affinity report-only); cfg (config.mk lines) is extended in place.
    Returns False and changes nothing for a kit without a plan tree."""
    import sys
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    import core_infra
    return core_infra.kit_cts_hook(kd, cfg)


# ------------------------------------------------------------------------------------------------ kit <-> slice
# MASTER-PLAN-R3 (COORD 10-26): kits CONSUME the slice.  The generator's own io placement is rewritten so the core
# clock entry and every bound M7 entry pin sit where the slice says (no later override), and check_kit() is the
# static gate GEOM-REVIEW / the kit preflight runs on a finished kit dir: kit == slice, else FAIL with the reason.
_PLACE = re.compile(r"^(\s*place_pin\s+-pin_name\s+)(\{[^}]*\}|\S+)(.*)$")
_OWN = ("master_slice.tcl", "master_core_infra.tcl", "core_infra_impl.tcl", "native_pg_binding.tcl",
        "keepout_phys.tcl")


def _pin_name(tok):
    return tok[1:-1] if tok.startswith("{") and tok.endswith("}") else tok


def _clock_port(kd, sl):
    p = Path(kd) / "core_infra_plan.json"
    if p.is_file():
        try:
            return json.loads(p.read_text()).get("core_clock_port")
        except ValueError:
            return None
    return sl.get("core_clock_port") or (sl.get("core_tree") or {}).get("clock_port")


def slice_pins(sl, clock_port=None):
    """{pin name: (layer, (x, y))} the slice fixes: core clock entry (M5) + bound entry pins (M7)."""
    want = {}
    entry = next((i["clock_pin"] for i in sl.get("islands", []) or [] if i.get("clock_pin")), None)
    if entry and clock_port and (sl.get("kind") == "core" or sl.get("core_clock_port")):
        want[clock_port] = (entry.get("layer", "M5"), tuple(float(v) for v in entry["xy_um"]))
    for e in sl.get("clock_entries") or []:                  # multi-root: one M5 entry per root pin
        want[e["port"]] = (e["clock_pin"].get("layer", "M5"), tuple(float(v) for v in e["clock_pin"]["xy_um"]))
    for p in sl.get("entry_pins", []) or []:
        if p.get("pin"):
            want[p["pin"]] = (p.get("layer", "M7"), tuple(float(v) for v in p["xy_um"]))
    return want


# Clock entry port geometry (COORD GEOM-21 10-27): the centre clock entry is one full-width M5 shape
# (>= 0.048 x 0.48 um) whose centre lies ON a routing track of its layer, so detailed route can reach the root driver
# (DRT-0255 = small AND off-track entry; the 0.048-wide shape alone sat 12 nm off the M5 track in the c15b kits).
CLOCK_PIN_SIZE = (0.048, 0.48)
_VERTICAL = {"M1", "M3", "M5", "M7", "M9"}           # ASAP7 preferred direction: odd metals vertical (track grid in x)
# ASAP7 platform make_tracks (openRoad/make_tracks.tcl), used only when the kit has no make_tracks.tcl of its own.
_ASAP7_TRACKS = {"M1": (0.009, 0.036, 0.009, 0.036), "M3": (0.009, 0.036, 0.009, 0.036),
                 "M4": (0.009, 0.036, 0.012, 0.048), "M5": (0.012, 0.048, 0.012, 0.048),
                 "M6": (0.012, 0.048, 0.016, 0.064), "M7": (0.016, 0.064, 0.016, 0.064),
                 "M8": (0.116, 0.080, 0.116, 0.080), "M9": (0.116, 0.080, 0.116, 0.080)}
_MKTRACK = re.compile(r"^\s*make_tracks\s+(\S+)\s+-x_offset\s+([-\d.]+)\s+-x_pitch\s+([-\d.]+)\s+"
                      r"-y_offset\s+([-\d.]+)\s+-y_pitch\s+([-\d.]+)", re.M)


def _layer_tracks(kd, layer):
    """(x_offset, x_pitch, y_offset, y_pitch, source) of LAYER: the kit's own make_tracks.tcl, else the ASAP7 platform."""
    f = Path(kd) / "make_tracks.tcl"
    if f.is_file():
        rows = [m for m in _MKTRACK.finditer(f.read_text()) if m.group(1) == layer]
        if len(rows) == 1:
            return tuple(float(v) for v in rows[0].groups()[1:]) + ("kit make_tracks.tcl",)
        if len(rows) > 1:
            raise ValueError(f"make_tracks.tcl: {len(rows)} track rows for {layer}; on-track snap is ambiguous")
    if layer not in _ASAP7_TRACKS:
        raise ValueError(f"no routing track grid known for layer {layer}")
    return _ASAP7_TRACKS[layer] + ("asap7 platform make_tracks.tcl",)


def _die_origin(kd):
    cfg = Path(kd) / "config.mk"
    m = re.search(r"^\s*export\s+DIE_AREA\s*:?=\s*([-\d.eE+]+)\s+([-\d.eE+]+)", cfg.read_text(), re.M) \
        if cfg.is_file() else None
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)


def snap_on_track(kd, layer, x, y):
    """Pin centre moved to the NEAREST routing track of LAYER (preferred-direction normal coordinate only; ties go up)."""
    xo, xp, yo, yp, _ = _layer_tracks(kd, layer)
    ox, oy = _die_origin(kd)
    if layer in _VERTICAL:
        x = ox + xo + math.floor((x - ox - xo) / xp + 0.5) * xp
    else:
        y = oy + yo + math.floor((y - oy - yo) / yp + 0.5) * yp
    return round(x, 4), round(y, 4)


def on_track(kd, layer, x, y, tol=1e-4):
    sx, sy = snap_on_track(kd, layer, x, y)
    return abs(sx - x) <= tol and abs(sy - y) <= tol


def slice_placements(kd, sl, clock_port=None):
    """{pin: (layer, x, y, (w, h))} where the kit places every slice-fixed pin: the slice position, the core clock
    entry snapped onto its track at CLOCK_PIN_SIZE (GEOM-21), bound entry pins 0.032 x 0.192.  One source for the io
    rewrite (_consume_io) and the generator's plan pin record (gen_phys.plan_pin_records -> freeze.json)."""
    out = {}
    ckset = set(clock_entry_ports(sl))
    for name, (layer, (x, y)) in slice_pins(sl, clock_port).items():
        if name == clock_port or name in ckset:
            x, y = snap_on_track(kd, layer, x, y)
            out[name] = (layer, x, y, CLOCK_PIN_SIZE)
        else:
            out[name] = (layer, x, y, (0.032, 0.192))
    return out


def kit_slice_placements(kd):
    """slice_placements of a kit that consumed a slice (master_slice.json staged), else {}."""
    kd = Path(kd)
    p = kd / "master_slice.json"
    if not p.is_file():
        return {}
    sl = json.loads(p.read_text())
    return slice_placements(kd, sl, _clock_port(kd, sl))


def _consume_io(kd, sl, clock_port):
    want = slice_pins(sl, clock_port)
    place = slice_placements(kd, sl, clock_port)
    done = {}
    if not want:
        return done
    for f in sorted(Path(kd).glob("*.tcl")):
        if f.name in _OWN:
            continue
        lines, hit = f.read_text().split("\n"), False
        for i, ln in enumerate(lines):
            m = _PLACE.match(ln)
            if not m or _pin_name(m.group(2)) not in want:
                continue
            name = _pin_name(m.group(2))
            # The centre clock entry needs a full M5 routing track, enough length for via access beside the root
            # driver, and its centre ON that track (GEOM-21) -- slice_placements (every declared root entry too).
            layer, x, y, wh = place[name]
            size = "%g %g" % wh
            lines[i] = (f"{m.group(1)}{{{name}}} -layer {layer} -location {{{x:.4f} {y:.4f}}} -pin_size {{{size}}}"
                        f"   ;# master-plan slice (was:{m.group(3).strip()[:80]})")
            done.setdefault(name, []).append(f.name)
            hit = True
        if hit:
            f.write_text("\n".join(lines))
    (Path(kd) / "master_slice_io.json").write_text(json.dumps(dict(
        rewritten={k: v for k, v in sorted(done.items())},
        slice_pins={k: dict(layer=v[0], xy_um=list(v[1])) for k, v in sorted(want.items())}), indent=1) + "\n")
    return done


def _kit_outline(kd):
    cfg = Path(kd) / "config.mk"
    if not cfg.is_file():
        return None
    m = re.search(r"^\s*export\s+DIE_AREA\s*:?=\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)",
                  cfg.read_text(), re.M)
    if not m:
        return None
    x0, y0, x1, y1 = (float(v) for v in m.groups())
    return (x1 - x0, y1 - y0)


def pushdown_cell_issues(islands, cells):
    """Every pushdown island's fixed cells lie inside its slice rect.  An island with driver_rect_um (HBM-CORES-REBAL-5
    opt-in, master_plan.pushdown_island driver_rect: island centre over a core SRAM) has its drivers placed by
    core_infra at the planned macro-channel site, so its cells are judged against driver_rect_um instead."""
    issues = []
    for isl in islands:
        mine = [c for c in cells if c["name"].startswith(f"mp_{isl['name']}_")]
        if not mine and not isl.get("cells"):
            issues.append(f"pushdown island {isl['name']}: no fixed cells")
        dr = isl.get("driver_rect_um")
        r = dr if dr is not None else isl["rect_um"]
        for c in mine:
            x, y = c["xy_um"]
            if not (r[0] <= x <= r[2] and r[1] <= y <= r[3]):
                issues.append(f"{c['name']} at {c['xy_um']} outside island {isl['name']} "
                              + (f"driver_rect {r}" if dr is not None else f"{r}"))
    return issues


def check_kit(kd, slice_path=None, tol=1e-3):
    """Static kit-vs-slice gate (12.7c GEOM-REVIEW part 1).  Every finding is a FAIL; returns a report dict."""
    kd = Path(kd)
    issues, checks = [], {}
    sp = Path(slice_path) if slice_path else kd / "master_slice.json"
    try:
        sl = load(sp)
    except SliceError as e:
        return dict(verdict="FAIL", kit=str(kd), issues=[str(e)], checks={})
    if slice_path and (kd / "master_slice.json").is_file() and \
            digest(json.loads((kd / "master_slice.json").read_text())) != digest(sl):
        issues.append("kit master_slice.json is not the given slice (stale or different plan)")
    ol = _kit_outline(kd)
    checks["outline"] = dict(kit=list(ol) if ol else None, slice=sl["outline_um"])
    if ol is None:
        issues.append("config.mk DIE_AREA missing")
    elif any(abs(a - b) > tol for a, b in zip(ol, sl["outline_um"])):
        issues.append(f"outline {list(ol)} != slice {sl['outline_um']}")
    mtcl = kd / "master_slice.tcl"
    if not mtcl.is_file() or mtcl.read_text() != emit_tcl(sl):
        issues.append("master_slice.tcl missing or not generated from this slice")
    if not any(HOOK_LINE.strip() in f.read_text() for f in kd.glob("*.tcl") if f.name not in _OWN):
        issues.append("no kit step sources /work/master_slice.tcl")
    clock_port = _clock_port(kd, sl)
    if sl.get("pushdown"):
        import core_infra as CI
        try:
            eff = dict(sl, core_clock_port=clock_port) if clock_port else sl
            plan = CI.compile_slice(eff, kd)
            got = json.loads((kd / "core_infra_plan.json").read_text())
            if got != json.loads(json.dumps(plan)):
                issues.append("core_infra_plan.json differs from compile_slice(slice)")
            if plan.get("arcs") and (kd / "constraint.sdc").is_file():
                import ft_ports
                fp = kd / "ft_ports.json"
                want = ft_ports.from_core_infra_plan(json.loads(json.dumps(plan)))
                if not fp.is_file() or json.loads(fp.read_text()).get("sha256") != want["sha256"]:
                    issues.append("ft_ports.json missing or not the slice ft declaration (12.2a1 die-timed ports)")
            if (kd / "master_core_infra.tcl").read_text() != CI.emit_tcl(eff, kd):
                issues.append("master_core_infra.tcl not generated from this slice")
            impl = (kd / "core_infra_impl.tcl").read_text()
            if impl != (Path(__file__).with_name("core_infra.tcl")).read_text():
                issues.append("core_infra_impl.tcl differs from the shared tools/die_plan/core_infra.tcl")
            checks["pushdown"] = dict(cells=len(plan["cells"]), ft_ports=len(plan["ports"]),
                                      tree=bool(plan.get("core_tree")), bay_cells=len(plan["bays"]),
                                      reserved_bays=len(plan.get("reserved_bays", [])),
                                      unbound_entry_pins=plan.get("unbound_entry_pins", 0))
            # island coordinates: every pushdown island's cells inside its slice rect at the slice centre
            issues += pushdown_cell_issues(sl["pushdown"].get("islands") or [], plan["cells"])
        except (OSError, ValueError, KeyError, CI.InfraError) as e:
            issues.append(f"pushdown not installed from the slice: {type(e).__name__}: {e}")
        # no island strip blockage left in the kit
        for k in sl.get("keepouts", []) or []:
            if k.get("kind") == "island" and f"keepout {k.get('name')} (island)" in (mtcl.read_text() if mtcl.is_file() else ""):
                issues.append(f"island {k.get('name')} emitted as a placement blockage (12.2a1: pushdown cells)")
    elif sl.get("kind") == "core" and sl.get("islands"):
        issues.append("core slice without pushdown section: islands would be strip blockages (12.2a1)")
    # clock entry + bound entry pins: every place_pin of those ports in the kit must be the slice's
    want = slice_pins(sl, clock_port)
    entry = next((i["clock_pin"] for i in sl.get("islands", []) or [] if i.get("clock_pin")), None)
    if sl.get("kind") == "core" and entry and not clock_port:
        issues.append("core clock entry in the slice but no core clock port bound (kit cannot place it)")
    ckset = set(clock_entry_ports(sl))
    if ckset:
        issues += _check_clock_roots(kd, sl)
    seen = {}
    for f in sorted(kd.glob("*.tcl")):
        if f.name in _OWN:
            continue
        for ln in f.read_text().split("\n"):
            m = _PLACE.match(ln)
            if not m or _pin_name(m.group(2)) not in want:
                continue
            n = _pin_name(m.group(2))
            lm = re.search(r"-layer\s+(\S+)", ln)
            xm = re.search(r"-location\s+\{\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s*\}", ln)
            lay, (x, y) = want[n]
            seen[n] = seen.get(n, 0) + 1
            if n == clock_port or n in ckset:
                try:
                    x, y = snap_on_track(kd, lay, x, y)
                except ValueError as e:
                    issues.append(f"{f.name}: clock entry {n}: {e}")
                sm = re.search(r"-pin_size\s+\{\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s*\}", ln)
                if not sm or float(sm.group(1)) < CLOCK_PIN_SIZE[0] - 1e-6 or float(sm.group(2)) < CLOCK_PIN_SIZE[1] - 1e-6:
                    issues.append(f"{f.name}: clock entry {n} pin_size {sm.groups() if sm else '?'} < "
                                  f"{CLOCK_PIN_SIZE[0]}x{CLOCK_PIN_SIZE[1]} (GEOM-21)")
                if xm and lm:
                    try:
                        if not on_track(kd, lm.group(1), float(xm.group(1)), float(xm.group(2))):
                            issues.append(f"{f.name}: clock entry {n} centre ({xm.group(1)}, {xm.group(2)}) is off the "
                                          f"{lm.group(1)} routing track (GEOM-21)")
                    except ValueError as e:
                        issues.append(f"{f.name}: clock entry {n}: {e}")
            if not lm or lm.group(1) != lay or not xm or abs(float(xm.group(1)) - x) > tol or abs(float(xm.group(2)) - y) > tol:
                issues.append(f"{f.name}: {n} placed at {xm.groups() if xm else '?'} {lm.group(1) if lm else '?'}, "
                              f"slice {lay} ({x:g}, {y:g})")
    for n in sorted(ckset):
        if not seen.get(n):
            issues.append(f"clock entry {n}: no place_pin in the kit io (multi-root entry not placed)")
    checks["slice_pins"] = dict(fixed=len(want), placed_by_kit_io=sum(seen.values()), clock_entries=sorted(ckset),
                                clock_port=clock_port, clock_entry=list(entry["xy_um"]) if entry else None)
    # latency target carried into the kit SDC/budget (12.3)
    lat = (sl.get("latency") or {}).get("common_clock_latency_ps") or {}
    checks["latency"] = lat
    issues = list(dict.fromkeys(issues))
    return dict(verdict="FAIL" if issues else "PASS", kit=str(kd), slice=str(sp), slice_sha256=digest(sl),
                type=sl.get("type"), kind=sl.get("kind"), issues=issues[:50], n_issues=len(issues), checks=checks)


def _check_clock_roots(kd, sl, tol=1e-6):
    """multi-root kit: clock_roots.json (gen_core_kit_legacy multi_root_contract) == the slice entries: same root pins,
    each root's 12.3 budget (TT / FF) == the entry's latency."""
    p = Path(kd) / "clock_roots.json"
    if not p.is_file():
        return ["multi-root slice but the kit has no clock_roots.json (not a declared multi-root kit)"]
    cr = json.loads(p.read_text())
    out = []
    kp = sorted(e.get("pin") for e in cr.get("entries") or [])
    sp = sorted(clock_entry_ports(sl))
    if kp != sp:
        out.append(f"clock_roots.json root pins {kp} != slice clock_entries {sp}")
    b = cr.get("budget_ps") or {}
    for e in sl.get("clock_entries") or []:
        cl = e["latency"]["common_clock_latency_ps"]
        lb = {"TT": e.get("budget_tt", b.get("tt")), "FF": e.get("budget_ff", b.get("ff"))}
        for c in ("TT", "FF"):
            if lb[c] is None or abs(float(lb[c]) - float(cl[c])) > tol:
                out.append(f"clock entry {e['port']}: kit {c} budget {lb[c]} != slice latency {cl[c]} (12.3)")
        if e.get("clock"):
            kc = next((x.get("clock") for x in cr.get("entries") or [] if x.get("pin") == e["port"]), None)
            if kc != e["clock"]:
                out.append(f"clock entry {e['port']}: kit clock {kc} != slice clock {e['clock']}")
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="master-plan slice tools")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check-kit", help="static kit-vs-slice gate on finished kit dirs")
    c.add_argument("kits", nargs="+")
    c.add_argument("--slice", help="the plan slice the kit must match (default: the kit's own copy)")
    c.add_argument("--out")
    a = ap.parse_args(argv)
    rows = [check_kit(k, a.slice) for k in a.kits]
    rep = dict(verdict="PASS" if all(r["verdict"] == "PASS" for r in rows) else "FAIL", kits=rows)
    txt = json.dumps(rep, indent=1)
    if a.out:
        Path(a.out).write_text(txt + "\n")
    print(txt if len(rows) <= 3 else json.dumps({r["kit"]: r["verdict"] for r in rows}, indent=1))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
