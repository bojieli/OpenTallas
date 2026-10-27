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
PDN_HOOK_LINE = "if {[file exists /work/master_slice_pdn.tcl]} { source /work/master_slice_pdn.tcl }\n"
CTS_HOOK_LINE = "if {[file exists /work/master_slice_cts.tcl]} { source /work/master_slice_cts.tcl }\n"
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
    errs += validate_pushdown(sl.get("pushdown"), outline)
    for i, p in enumerate(pins):
        if p.get("dir") not in (None, "in", "out"):
            errs.append(f"entry_pins[{p.get('name', i)}]: dir must be null, 'in' or 'out'")
    g = sl.get("gates", {})
    if not isinstance(g, dict) or any(v not in ("PASS", "FAIL", "NOT RUN") for v in g.values()):
        errs.append("gates: {gate: PASS|FAIL|NOT RUN} required")
    return errs


PD_ROLES = ("clock_entry", "tree_leaf", "die_node", "core_tree_node")


def validate_pushdown(pd, outline):
    """12.2a1 pushdown section: islands[] (rect, centre, ft_ports, driver) + clock_repeaters[] (COORD 06:53)."""
    errs = []
    if pd is None:
        return errs
    if not isinstance(pd, dict):
        return ["pushdown: must be an object"]
    names = set()
    for i, k in enumerate(_named(pd.get("islands"), "pushdown.islands", errs)):
        w = f"pushdown.islands[{k.get('name', i)}]"
        if k.get("role") not in PD_ROLES:
            errs.append(f"{w}: role expected one of {PD_ROLES}, got {k.get('role')!r}")
        if _rect(k.get("rect_um"), w, errs, outline) and _xy(k.get("centre_um"), w + ".centre_um", errs, outline):
            if not _inside_rect(k["rect_um"], k["centre_um"]):
                errs.append(f"{w}: centre_um outside its rect")
        drv = k.get("driver")
        if not (isinstance(drv, dict) and isinstance(drv.get("cell"), str) and drv["cell"]
                and isinstance(drv.get("parallel", 1), int) and drv.get("parallel", 1) >= 1):
            errs.append(f"{w}: driver {{cell, parallel>=1}} required")
        for q in k.get("ft_ports") or []:
            if not (isinstance(q, dict) and q.get("name") and q.get("dir") in ("in", "out")):
                errs.append(f"{w}: ft_port {{name, dir in|out, layer, xy_um}} required, got {q!r}")
                continue
            if q["name"] in names:
                errs.append(f"{w}: ft port {q['name']!r} declared twice")
            names.add(q["name"])
            if _xy(q.get("xy_um"), f"{w}.{q['name']}", errs, outline) and not _inside_rect(k.get("rect_um") or [0] * 4,
                                                                                         q["xy_um"]):
                errs.append(f"{w}: ft port {q['name']} outside the island rect")
    for i, r in enumerate(_named(pd.get("clock_repeaters"), "pushdown.clock_repeaters", errs)):
        w = f"pushdown.clock_repeaters[{r.get('name', i)}]"
        _xy(r.get("xy_um"), w, errs, outline)
        if not (isinstance(r.get("cell"), str) and r["cell"]):
            errs.append(f"{w}: cell required")
        for q in r.get("ft_ports") or []:
            if isinstance(q, dict) and q.get("name") in names:
                errs.append(f"{w}: ft port {q['name']!r} declared twice")
            if isinstance(q, dict):
                names.add(q.get("name"))
    return errs


def _inside_rect(r, xy, eps=1e-6):
    return r[0] - eps <= xy[0] <= r[2] + eps and r[1] - eps <= xy[1] <= r[3] + eps


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


def pushdown_rects(sl):
    """rects (rounded) of the islands built by pushdown: no placement hole / routing OBS is cut there (12.2a1)."""
    pd = sl.get("pushdown") or {}
    return {tuple(round(float(v), 3) for v in k["rect_um"]) for k in pd.get("islands") or []}


def emit_tcl(sl, dbu=1000, clock_ports=None, reset_ports=None):
    """OpenROAD Tcl for the kit (type frame = kit DIE_AREA frame).  Idempotent: a blockage / obstruction with the
    same box is not created twice (PRE_GLOBAL_PLACE hooks run in more than one ORFS step); pushdown cells / ports are
    created once (found by name on a re-run).

    With a "pushdown" section (12.2a1, COORD 06:53) the kit CONSUMES the slice: island driver cells + H-tree leg
    repeaters are instantiated FIXED + dont_touch at the slice coordinates with their ft ports (no island blockage,
    no routing OBS); a clock-entry island binds the kit clock / reset ports (clock_ports / reset_ports) at its ft
    input points with the driver inserted between port and core clock net; bays become reserved site rows (placement
    blockage) that hold only the cells this slice puts there (pushed-down entry-pin repeaters, slot stations)."""
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
    pdr = pushdown_rects(sl)

    def _pd(r):
        return tuple(round(float(v), 3) for v in r) in pdr
    for i in sl.get("islands", []) or []:
        if not _pd(i["rect_um"]):
            place.append((f"island {i.get('name')}", i["rect_um"]))
    for k in sl.get("keepouts", []) or []:
        if "placement" in (k.get("use") or []) and not (k.get("kind") == "island" and _pd(k["rect_um"])):
            place.append((f"keepout {k.get('name')} ({k.get('kind')})", k["rect_um"]))
    for what, r in place:
        x0, y0, x1, y1 = (_d(v, dbu) for v in r)
        L += [f"# placement blockage: {what}",
              f"incr ms_nb [ot_ms_blockage $ms_b {x0} {y0} {x1} {y1}]; lappend ms_place [list {x0} {y0} {x1} {y1}]"]
    for k in sl.get("keepouts", []) or []:
        if k.get("kind") == "island" and _pd(k["rect_um"]):
            continue                     # 12.2a1: no LEF-hole / routing OBS over a pushdown island
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
    rep_names = repeater_pin_names(sl)
    for p in sl.get("entry_pins", []) or []:
        x, y = p["xy_um"]
        if p["name"] in rep_names:
            continue                     # consumed as a pushed-down repeater pair (emit_consume_tcl)
        if p.get("pin"):
            L.append(f"place_pin -pin_name {_tcl_word(p['pin'])} -layer {p.get('layer', 'M7')} "
                     f"-location {{{x:.4f} {y:.4f}}} -pin_size {{0.032 0.192}}   ;# entry {p.get('name')}")
            nplaced += 1
        else:
            L.append(f"dict set ot_master_entry_pins {_tcl_word(p['name'])} [dict create layer {p.get('layer', 'M7')} "
                     f"xy_um {{{x:g} {y:g}}} bay {_tcl_word(p.get('bay') or '')} path {_tcl_word(p.get('path') or '')} "
                     f"bit {p.get('bit', 0)}]")
    L += emit_consume_tcl(sl, dbu, clock_ports, reset_ports)
    L.append(f'puts "OT_MASTER_SLICE type={t} blockages_new=$ms_nb obstructions_new=$ms_no '
             f'bays=[dict size $ot_master_bays] entry_pins_placed={nplaced} '
             f'entry_pins_unbound=[dict size $ot_master_entry_pins]"')
    L.append("}")
    return "\n".join(L) + "\n"


RST_DRIVER = "BUFx4_ASAP7_75t_R"       # island reset repeater (regional reset hop, control only)
EP_REPEATER = "BUFx4_ASAP7_75t_R"      # pushed-down rest-stop repeater of a die-top M8/M9 net (12.1d/12.7a)


def _ident(s):
    return "".join(c if (c.isalnum() or c == "_") else "_" for c in str(s))


def repeater_pairs(sl):
    """[(bay, in_pin, out_pin)]: unbound entry-pin pairs (down 'in' + up 'out' of one bit) at a REPEATER bay = the
    rest stop of a die-top net: the partition gets a pushed-down repeater (2 ft ports + 1 fixed cell in the bay)."""
    kinds = {b["name"]: b.get("kind") for b in sl.get("bays") or []}
    pairs = {}
    for p in sl.get("entry_pins") or []:
        if p.get("pin") or p.get("dir") not in ("in", "out") or p.get("pair") is None:
            continue
        if kinds.get(p.get("bay")) != "repeater":
            continue
        pairs.setdefault((p["bay"], p.get("path"), p.get("drop", 0), p["pair"]), {})[p["dir"]] = p
    return [(k[0], v["in"], v["out"]) for k, v in pairs.items() if "in" in v and "out" in v]


def repeater_pin_names(sl):
    return {q["name"] for _, a, b in repeater_pairs(sl) for q in (a, b)}


def emit_consume_tcl(sl, dbu=1000, clock_ports=None, reset_ports=None):
    """Tcl lines (inside emit_tcl's uplevel block) that build what the slice fixes: pushdown island cells + ft ports,
    H-tree leg repeaters, pushed-down entry-pin repeaters, bays as reserved site rows.  Empty without such data."""
    pd = sl.get("pushdown") or {}
    isl = pd.get("islands") or []
    reps = pd.get("clock_repeaters") or []
    pairs = repeater_pairs(sl)
    bays = sl.get("bays") or []
    L = ["# ---- 12.7c CONSUME: reserved rows, pushdown cells (fixed + dont_touch), ft ports (generated)",
         "set ms_np 0; set ms_nc 0; set ms_nbr 0; set ms_ovf 0; set ms_entry 0"]
    if not (isl or reps or pairs):
        return L + _bay_rows(bays, dbu) + [_consume_puts(isl, reps, pairs)]
    L += [

         "set ms_u [[ord::get_db_tech] getDbUnitsPerMicron]",
         "set ms_fixed {}",
         "foreach i [$ms_b getInsts] { set st [$i getPlacementStatus]",
         "  if {$st eq \"FIRM\" || $st eq \"FIXED\" || $st eq \"LOCKED\" || $st eq \"COVER\"} {",
         "    set q [$i getBBox]; lappend ms_fixed [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]] } }",
         "proc ot_ms_free {x0 y0 x1 y1} {",
         "  foreach q $::ms_fixed { if {[lindex $q 0] < $x1 && [lindex $q 2] > $x0 && [lindex $q 1] < $y1 && "
         "[lindex $q 3] > $y0} { return 0 } }",
         "  return 1",
         "}",
         "proc ot_ms_net {nm {sig SIGNAL}} { set n [$::ms_b findNet $nm]",
         "  if {$n eq \"NULL\"} { set n [odb::dbNet_create $::ms_b $nm]; $n setSigType $sig }; return $n }",
         "proc ot_ms_port {nm dir x y {layer M5} {sig SIGNAL}} {",
         "  set bt [$::ms_b findBTerm $nm]",
         "  if {$bt eq \"NULL\"} { set n [ot_ms_net $nm $sig]; set bt [odb::dbBTerm_create $n $nm]",
         "    $bt setIoType [expr {$dir eq \"in\" ? \"INPUT\" : \"OUTPUT\"}]; $bt setSigType $sig; incr ::ms_np }",
         "  place_pin -pin_name $nm -layer $layer -location [list $x $y] -pin_size {0.024 0.384}",
         "  foreach bp [$bt getBPins] { $bp setPlacementStatus FIRM }",
         "  return [$bt getNet]",
         "}",
         "# a cell at (x, y) um snapped to the row/site grid, the nearest free site inside rect (um); FIXED + dont_touch",
         "proc ot_ms_cell {nm mn x y rx0 ry0 rx1 ry1} {",
         "  set i [$::ms_b findInst $nm]; if {$i ne \"NULL\"} { return $i }",
         "  set m [[ord::get_db] findMaster $mn]; if {$m eq \"NULL\"} { error \"master_slice.tcl: no master $mn\" }",
         "  set u $::ms_u; set w [$m getWidth]; set h [$m getHeight]",
         "  set X0 [expr {round($rx0*$u)}]; set Y0 [expr {round($ry0*$u)}]; set X1 [expr {round($rx1*$u)}]; "
         "set Y1 [expr {round($ry1*$u)}]",
         "  set best {}",
         "  foreach r [$::ms_b getRows] { set z [$r getBBox]",
         "    if {[$z yMin] < $Y0 || [$z yMin] + $h > $Y1} continue",
         "    set sw [[$r getSite] getWidth]; set dy [expr {abs([$z yMin] + $h/2 - round($y*$u))}]",
         "    set xc [expr {[$z xMin] + round((round($x*$u) - $w/2 - [$z xMin]) / double($sw)) * $sw}]",
         "    for {set t 0} {$t < 2000} {incr t} { set xx [expr {$xc + (($t + 1) / 2) * ($t % 2 ? 1 : -1) * $sw}]",
         "      if {$xx < $X0 || $xx + $w > $X1 || $xx < [$z xMin] || $xx + $w > [$z xMax]} { if {$t > 1000} break; "
         "continue }",
         "      if {[ot_ms_free $xx [$z yMin] [expr {$xx + $w}] [expr {[$z yMin] + $h}]]} {",
         "        set d [expr {$dy + abs($xx + $w/2 - round($x*$u))}]",
         "        if {$best eq {} || $d < [lindex $best 0]} { set best [list $d $xx [$z yMin] [$r getOrient]] }; "
         "break } } }",
         "  if {$best eq {}} { incr ::ms_ovf; puts \"OT_MASTER_SLICE OVERFLOW no free site for $nm in rect\"; "
         "return NULL }",
         "  set i [odb::dbInst_create $::ms_b $m $nm]",
         "  $i setOrient [lindex $best 3]; $i setLocation [lindex $best 1] [lindex $best 2]",
         "  $i setPlacementStatus FIRM; incr ::ms_nc",
         "  lappend ::ms_fixed [list [lindex $best 1] [lindex $best 2] [expr {[lindex $best 1] + $w}] "
         "[expr {[lindex $best 2] + $h}]]",
         "  return $i",
         "}",
         "proc ot_ms_buf {nm mn x y rect nin nout} { set i [ot_ms_cell $nm $mn $x $y {*}$rect]",
         "  if {$i eq \"NULL\"} { return }",
         "  if {[[$i findITerm A] getNet] eq \"NULL\"} { [$i findITerm A] connect $nin }",
         "  if {[[$i findITerm Y] getNet] eq \"NULL\"} { [$i findITerm Y] connect $nout }",
         "  $i setDoNotTouch 1 }",
         "# clock entry: the kit's own clock / reset port moves to the island ft-input point and the island driver goes",
         "# between the port and the core clock net (the 12.8c designed fixed entry stage, same cell every instance)",
         "proc ot_ms_entry {port x y layer mn par rect sig} {",
         "  set bt [$::ms_b findBTerm $port]; if {$bt eq \"NULL\"} { return 0 }",
         "  place_pin -pin_name $port -layer $layer -location [list $x $y] -pin_size {0.024 0.384}",
         "  foreach bp [$bt getBPins] { $bp setPlacementStatus FIRM }",
         "  if {$mn eq {}} { return 1 }",
         "  set n [$bt getNet]; if {[$::ms_b findInst mp_isl_entry_${port}_0] ne \"NULL\"} { return 1 }",
         "  set nn [ot_ms_net ${port}_mp_core $sig]",
         "  foreach it [$n getITerms] { $it disconnect; $it connect $nn }",
         "  for {set k 0} {$k < $par} {incr k} { ot_ms_buf mp_isl_entry_${port}_$k $mn $x $y $rect $n $nn }",
         "  $n setDoNotTouch 1",
         "  return 1",
         "}"]
    cps = [p for p in (clock_ports or []) if p]
    rps = [p for p in (reset_ports or []) if p]
    L.append("set ms_clock_ports {" + " ".join(_tcl_word(p) for p in cps) + "}; set ms_reset_ports {" +
             " ".join(_tcl_word(p) for p in rps) + "}")
    for k in isl:
        r = " ".join(f"{float(v):g}" for v in k["rect_um"])
        cx, cy = k["centre_um"]
        drv = k.get("driver") or {}
        mn, par = drv.get("cell"), int(drv.get("parallel", 1))
        fp = {q["name"]: q for q in k.get("ft_ports") or []}
        ck_i = next((q for q in fp.values() if q["name"].endswith("_ck_i")), None)
        ck_o = next((q for q in fp.values() if q["name"].endswith("_ck_o")), None)
        rs_i = next((q for q in fp.values() if q["name"].endswith("_rst_i")), None)
        rs_o = next((q for q in fp.values() if q["name"].endswith("_rst_o")), None)
        L.append(f"# pushdown island {k['name']} ({k.get('role')}) rect {{{r}}}: driver {mn} x{par}, {drv.get('basis', '')}")
        if k.get("role") == "core_tree_node":
            # 12.8b internal H-tree node: driver fed from the entry driver's core-side net(s), drives leaf net mp_ct<k>
            leaf = "mp_ct" + k["name"][3:] if k["name"].startswith("isl") else "mp_ct_" + _ident(k["name"])
            L.append(f"set ms_nl [ot_ms_net {leaf} CLOCK]; $ms_nl setDoNotTouch 0")
            L.append("foreach p $ms_clock_ports { set ms_nr [$ms_b findNet ${p}_mp_core]; if {$ms_nr ne \"NULL\"} {")
            for j in range(par):
                L.append(f"  ot_ms_buf mp_{k['name']}_ct_{j} {mn} {cx:.4f} {cy:.4f} {{{r}}} $ms_nr $ms_nl")
            L.append("  break } }")
            continue
        if k.get("role") == "clock_entry" and ck_i:
            # bind the kit clock / reset ports at the ft-input points (no extra ports: ck_o / rst_o are internal)
            L.append("foreach p $ms_clock_ports { incr ms_entry [ot_ms_entry $p %.4f %.4f %s %s %d {%s} CLOCK] }"
                     % (ck_i["xy_um"][0], ck_i["xy_um"][1], ck_i.get("layer", "M5"), mn, par, r))
            if rs_i:
                L.append("foreach p $ms_reset_ports { incr ms_entry [ot_ms_entry $p %.4f %.4f %s {} 0 {%s} RESET] }"
                         % (rs_i["xy_um"][0], rs_i["xy_um"][1], rs_i.get("layer", "M5"), r))
            continue
        if ck_i and ck_o:
            L.append(f"set ms_ni [ot_ms_port {ck_i['name']} in {ck_i['xy_um'][0]:.4f} {ck_i['xy_um'][1]:.4f} "
                     f"{ck_i.get('layer', 'M5')} CLOCK]; set ms_no2 [ot_ms_port {ck_o['name']} out "
                     f"{ck_o['xy_um'][0]:.4f} {ck_o['xy_um'][1]:.4f} {ck_o.get('layer', 'M5')} CLOCK]")
            L.append("$ms_ni setDoNotTouch 1; $ms_no2 setDoNotTouch 1")
            for j in range(par):
                L.append(f"ot_ms_buf mp_{k['name']}_ck_{j} {mn} {cx:.4f} {cy:.4f} {{{r}}} $ms_ni $ms_no2")
        if rs_i and rs_o:
            L.append(f"set ms_ni [ot_ms_port {rs_i['name']} in {rs_i['xy_um'][0]:.4f} {rs_i['xy_um'][1]:.4f} "
                     f"{rs_i.get('layer', 'M5')}]; set ms_no2 [ot_ms_port {rs_o['name']} out {rs_o['xy_um'][0]:.4f} "
                     f"{rs_o['xy_um'][1]:.4f} {rs_o.get('layer', 'M5')}]")
            L.append("$ms_ni setDoNotTouch 1; $ms_no2 setDoNotTouch 1")
            L.append(f"ot_ms_buf mp_{k['name']}_rst {RST_DRIVER} {rs_i['xy_um'][0]:.4f} {rs_i['xy_um'][1]:.4f} {{{r}}} $ms_ni $ms_no2")
    for c in reps:
        x, y = c["xy_um"]
        rr = c.get("rect_um") or [x - 2.16, y - 2.16, x + 2.16, y + 2.16]
        r = " ".join(f"{float(v):g}" for v in rr)
        fi = next((q for q in c.get("ft_ports") or [] if q.get("dir") == "in"), None)
        fo = next((q for q in c.get("ft_ports") or [] if q.get("dir") == "out"), None)
        if not (fi and fo):
            continue
        L.append(f"set ms_ni [ot_ms_port {fi['name']} in {fi['xy_um'][0]:.4f} {fi['xy_um'][1]:.4f} M5 CLOCK]; "
                 f"set ms_no2 [ot_ms_port {fo['name']} out {fo['xy_um'][0]:.4f} {fo['xy_um'][1]:.4f} M5 CLOCK]; "
                 "$ms_ni setDoNotTouch 1; $ms_no2 setDoNotTouch 1")
        L.append(f"ot_ms_buf mp_{_ident(c['name'])} {c['cell']} {x:.4f} {y:.4f} {{{r}}} $ms_ni $ms_no2   "
                 ";# H-tree leg repeater (COORD 06:53)")
    bay_rect = {b["name"]: b["rect_um"] for b in bays}
    for j, (bay, a, b) in enumerate(pairs):
        rr = bay_rect[bay]
        r = " ".join(f"{float(v):g}" for v in rr)
        cx, cy = (rr[0] + rr[2]) / 2, (rr[1] + rr[3]) / 2
        L.append(f"set ms_ni [ot_ms_port mp_ep{j}_i in {a['xy_um'][0]:.4f} {a['xy_um'][1]:.4f} {a.get('layer', 'M7')}]; "
                 f"set ms_no2 [ot_ms_port mp_ep{j}_o out {b['xy_um'][0]:.4f} {b['xy_um'][1]:.4f} "
                 f"{b.get('layer', 'M7')}]; $ms_ni setDoNotTouch 1; $ms_no2 setDoNotTouch 1")
        L.append(f"ot_ms_buf mp_ep{j} {EP_REPEATER} {cx:.4f} {cy:.4f} {{{r}}} $ms_ni $ms_no2   ;# {a.get('path')} "
                 f"bit {a.get('pair')}")
    L += _bay_rows(bays, dbu)
    L += _pg_check_tcl(sl)
    L.append(_consume_puts(isl, reps, pairs))
    L.append("if {$ms_ovf > 0 && [info exists ::env(OT_MASTER_SLICE_STRICT)]} "
             "{ error \"master_slice.tcl: $ms_ovf pushdown cells found no free site (slice/kit mismatch)\" }")
    return L


VIA_WIN_HALF_UM = 0.648       # die via-stack window half size around a die drop point (3 x 0.432 um M5 pitch)
VIA_WIN_LAYERS = ("M5", "M6", "M7")   # core PG layers the die M9->M5 stack passes through (12.2a1)


def via_windows(sl):
    """[(port name, rect_um)] of the die drop points of the slice: the *_i ft ports of pushdown islands with a via
    stack and of clock repeaters.  pdngen must not put core straps there (HBM-CORE-LAT r8 probe: windows made BEFORE
    pdngen cut the straps)."""
    out = []
    pd = sl.get("pushdown") or {}
    items = [k for k in pd.get("islands") or [] if k.get("via_stack")] + list(pd.get("clock_repeaters") or [])
    for k in items:
        for q in k.get("ft_ports") or []:
            if q.get("dir") == "in":
                x, y = q["xy_um"]
                h = VIA_WIN_HALF_UM
                out.append((q["name"], [round(x - h, 4), round(y - h, 4), round(x + h, 4), round(y + h, 4)]))
    return out


def emit_pdn_tcl(sl):
    """Prefix of the kit pdn.tcl (reused from HBM-CORE-LAT 5b1fd19f1 infra_islands_pdn_tcl, generic here): via-window
    routing obstructions on M5-M7 at every die drop point exist BEFORE pdngen, so the core straps are cut there.
    The consume step (PRE_GLOBAL_PLACE, after PDN) removes these obstructions again (no LEF hole, no lasting OBS)
    and fail-closes when a window still holds core PG or an island lost its M1 followpin rails."""
    w = via_windows(sl)
    if not w:
        return ""
    L = [f"# GENERATED by tools/die_plan/master_slice.py: 12.2a1 via windows of {sl['type']} before pdngen",
         "uplevel #0 {", "set mw_b [ord::get_db_block]; set mw_t [ord::get_db_tech]; set mw_n 0",
         "set mw_u [$mw_t getDbUnitsPerMicron]"]
    for _, r in w:
        for ly in VIA_WIN_LAYERS:
            L.append(f"if {{[$mw_t findLayer {ly}] ne \"NULL\"}} {{ odb::dbObstruction_create $mw_b [$mw_t findLayer {ly}] "
                     f"[expr {{round({r[0]}*$mw_u)}}] [expr {{round({r[1]}*$mw_u)}}] [expr {{round({r[2]}*$mw_u)}}] "
                     f"[expr {{round({r[3]}*$mw_u)}}]; incr mw_n }}")
    L += [f'puts "OT_MASTER_SLICE_PDN via_windows={len(w)} obstructions=$mw_n"', "}"]
    return "\n".join(L) + "\n"


def _pg_check_tcl(sl):
    """After PDN (PRE_GLOBAL_PLACE): drop the via-window obstructions, then the rail-survival check reused from
    HBM-CORE-LAT (infra_islands_tcl): every pushdown island keeps VDD+VSS M1 followpin rails, and no core PG shape
    is left in a via window.  FAIL = Tcl error (the kit stops)."""
    w = via_windows(sl)
    isl = (sl.get("pushdown") or {}).get("islands") or []
    if not (w or isl):
        return []
    wins = " ".join("{" + " ".join(f"{v:g}" for v in r) + "}" for _, r in w)
    rects = " ".join("{" + " ".join(f"{float(v):g}" for v in k["rect_um"]) + "}" for k in isl)
    return [
        "proc ot_ms_dbu {v} { return [expr {round($v*$::ms_u)}] }",
        "set ms_u [[ord::get_db_tech] getDbUnitsPerMicron]",
        "set ms_wins {" + wins + "}; set ms_wdel 0",
        "foreach o [$ms_b getObstructions] { set bb [$o getBBox]; set ln [[$bb getTechLayer] getName]",
        "  if {[lsearch {" + " ".join(VIA_WIN_LAYERS) + "} $ln] < 0} continue",
        "  foreach r $ms_wins { if {[$bb xMin] == [ot_ms_dbu [lindex $r 0]] && [$bb yMin] == [ot_ms_dbu [lindex $r 1]] "
        "&& [$bb xMax] == [ot_ms_dbu [lindex $r 2]] && [$bb yMax] == [ot_ms_dbu [lindex $r 3]]} { odb::dbObstruction_destroy $o; incr ms_wdel; break } } }",
        "proc ot_ms_pg {x0 y0 x1 y1 lys} {",
        "  set n [dict create VDD 0 VSS 0]",
        "  foreach net {VDD VSS} { set nt [$::ms_b findNet $net]; if {$nt eq \"NULL\"} continue",
        "    foreach sw [$nt getSWires] { foreach s [$sw getWires] {",
        "      if {[$s isVia]} { set v [$s getTechVia]; if {$v eq \"NULL\"} { set v [$s getBlockVia] }; "
        "if {$v eq \"NULL\"} continue; set ly [$v getTopLayer] } else { set ly [$s getTechLayer] }",
        "      if {[lsearch $lys [$ly getName]] < 0} continue",
        "      if {[$s xMax] > [ot_ms_dbu $x0] && [$s xMin] < [ot_ms_dbu $x1] && [$s yMax] > [ot_ms_dbu $y0] && "
        "[$s yMin] < [ot_ms_dbu $y1]} { dict incr n $net } } } }",
        "  return $n }",
        "set ms_haspg [expr {[$ms_b findNet VDD] ne \"NULL\" && [llength [[$ms_b findNet VDD] getSWires]] > 0}]",
        "set ms_norail 0; set ms_winpg 0",
        "if {$ms_haspg} {",
        "  foreach r {" + rects + "} { set c [ot_ms_pg {*}$r {M1}]; "
        "if {[dict get $c VDD] == 0 || [dict get $c VSS] == 0} { incr ms_norail } }",
        "  foreach r $ms_wins { set c [ot_ms_pg {*}$r {" + " ".join(VIA_WIN_LAYERS) + "}]; "
        "incr ms_winpg [expr {[dict get $c VDD] + [dict get $c VSS]}] } }",
        'puts "OT_MASTER_SLICE_PG pg_present=$ms_haspg via_windows=[llength $ms_wins] window_obs_removed=$ms_wdel '
        'islands_without_rails=$ms_norail window_pg_shapes=$ms_winpg"',
        "if {$ms_norail > 0} { error \"OT_MASTER_SLICE_PG FAIL: $ms_norail pushdown islands without VDD/VSS M1 rails\" }",
        "if {$ms_winpg > 0} { error \"OT_MASTER_SLICE_PG FAIL: $ms_winpg core PG shapes in die via windows\" }"]


def emit_cts_tcl(sl, clock_ports=None):
    """PRE_CTS Tcl of the 12.8b structured internal H-tree (slice core_tree): every clock sink on the entry driver's
    core net joins the leaf net of the NEAREST leaf island centre (plan geometry: the symmetric leaf grid's regions;
    no measured value).  The kit's CTS then builds one sub-tree per leaf net (ot_master_cts_nets).  Empty without a
    core_tree."""
    ct = sl.get("core_tree") or {}
    leaves = ct.get("leaves") or []
    if not leaves:
        return ""
    L = [f"# GENERATED by tools/die_plan/master_slice.py: 12.8b internal H-tree of {sl['type']} "
         f"(grid {ct.get('grid')}, leaf reach {ct.get('leaf_reach_um')} um)",
         "uplevel #0 {",
         "set mc_b [ord::get_db_block]; set mc_u [[ord::get_db_tech] getDbUnitsPerMicron]",
         "set mc_leaf {" + " ".join(f"{{{q['net']} {q['centre_um'][0]:g} {q['centre_um'][1]:g}}}" for q in leaves) + "}",
         "set ot_master_cts_nets {" + " ".join(q["net"] for q in leaves) + "}",
         "set mc_n 0; set mc_cnt [dict create]",
         "foreach p {" + " ".join(_tcl_word(p) for p in (clock_ports or [])) + "} {",
         "  set root [$mc_b findNet ${p}_mp_core]; if {$root eq \"NULL\"} continue",
         "  foreach it [$root getITerms] {",
         "    set inst [$it getInst]",
         "    if {[$it getIoType] ne \"INPUT\" || [string match mp_isl* [$inst getName]]} continue",
         "    set bb [$inst getBBox]; set x [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $mc_u}]; "
         "set y [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $mc_u}]",
         "    set best {}; set bd 1e30",
         "    foreach q $mc_leaf { set d [expr {abs($x - [lindex $q 1]) + abs($y - [lindex $q 2])}]",
         "      if {$d < $bd} { set bd $d; set best [lindex $q 0] } }",
         "    $it disconnect; $it connect [$mc_b findNet $best]; dict incr mc_cnt $best; incr mc_n",
         "  }",
         "}",
         "puts \"OT_MASTER_CORE_TREE sinks=$mc_n per_leaf=$mc_cnt cts_nets=$ot_master_cts_nets\"",
         "}"]
    return "\n".join(L) + "\n"


def _bay_rows(bays, dbu):
    """bays = reserved site rows: a placement blockage keeps the placer's own cells out; the cells this slice puts
    there are FIXED, slot stations already placed FIRM at their plan sites stay."""
    out = []
    for bb in bays:
        x0, y0, x1, y1 = (_d(v, dbu) for v in bb["rect_um"])
        out.append(f"incr ms_nbr [ot_ms_blockage $ms_b {x0} {y0} {x1} {y1}]   ;# reserved rows: bay {bb['name']} "
                   f"({bb.get('kind')})")
    return out


def _consume_puts(isl, reps, pairs):
    return ('puts "OT_MASTER_SLICE_CONSUME pushdown_islands=%d clock_repeaters=%d ep_repeaters=%d ports_new=$ms_np '
            'cells_new=$ms_nc entry_ports_bound=$ms_entry reserved_bays_new=$ms_nbr overflow=$ms_ovf"'
            % (len(isl), len(reps), len(pairs)))


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
              clock_ports=None, reset_ports=None, cts_hook=None, pdn_tcl=None):
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
    shutil.copyfile(p, kd / "master_slice.json")
    (kd / "master_slice.tcl").write_text(emit_tcl(sl, clock_ports=clock_ports, reset_ports=reset_ports))
    pdn = emit_pdn_tcl(sl)
    pf = Path(pdn_tcl) if pdn_tcl else kd / "pdn.tcl"
    if pdn:
        (kd / "master_slice_pdn.tcl").write_text(pdn)
        if pf.is_file() and "master_slice_pdn.tcl" not in pf.read_text():
            pf.write_text(PDN_HOOK_LINE + pf.read_text())
    cts = emit_cts_tcl(sl, clock_ports)
    if cts:
        (kd / "master_slice_cts.tcl").write_text(cts)
        (kd / "master_slice_cts_nets.txt").write_text(" ".join(q["net"] for q in sl["core_tree"]["leaves"]) + "\n")
        if cts_hook and Path(cts_hook).is_file():
            h = Path(cts_hook)
            h.write_text(CTS_HOOK_LINE + h.read_text())
    if (sl.get("pushdown") or {}).get("islands"):
        # 12.2a1: islands are pushdown cells now -> the old top-owned island hole (die_islands.tcl blockage +
        # row clear) is dropped from this kit
        di = kd / "die_islands.tcl"
        if di.is_file():
            di.unlink()
        for f in ([Path(gpl_hook)] if gpl_hook else []) + [kd / "face_flops.tcl"]:
            if f.is_file():
                f.write_text(f.read_text().replace("source /work/die_islands.tcl\n", ""))
    if not (kd / "keepout_phys.tcl").is_file():
        shutil.copyfile(Path(__file__).with_name("keepout_phys.tcl"), kd / "keepout_phys.tcl")
    if gpl_hook:
        h = Path(gpl_hook)
        h.write_text(HOOK_LINE + h.read_text())
    return stamp(sl)
