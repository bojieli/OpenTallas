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
"""
import hashlib
import json
import os
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
    pushdown = sl.get("kind") == "core" and bool(sl.get("pushdown"))
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
    L.append("# entry pins without a bound pin name (um, type frame): name -> {layer xy_um bay path bit}; for io.tcl")
    L.append("set ot_master_entry_pins [dict create]")
    nplaced = 0
    for p in sl.get("entry_pins", []) or []:
        x, y = p["xy_um"]
        if p.get("pin"):
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


def kit_apply(kd, name, outline_um, slice_dir=None, plan_raw=None, trial=False, kind=None, gpl_hook=None):
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
    if sl.get("kind") == "core" and sl.get("pushdown"):
        import core_infra
        core_infra.install(kd, sl)
    shutil.copyfile(p, kd / "master_slice.json")
    (kd / "master_slice.tcl").write_text(emit_tcl(sl))
    if not (kd / "keepout_phys.tcl").is_file():
        shutil.copyfile(Path(__file__).with_name("keepout_phys.tcl"), kd / "keepout_phys.tcl")
    if gpl_hook:
        h = Path(gpl_hook)
        h.write_text(HOOK_LINE + h.read_text())
    return stamp(sl)
