#!/usr/bin/env python3
"""PREFLIGHT-2 (OWNER 10-27): shared fail-closed kit contract checks, run by kit_preflight.py before any allocation.

Static only (no synth, no place): each check is one bug class seen on 10-26/10-27.  Every check returns
(errors, info); an empty error list is PASS, info['applies'] False marks a check with nothing to judge (NA).

  corner_modes         one mode per corner in every generated sdc/tcl: TT setup vclk 250, FF hold 202.5; no global
                       vclk latency in a hook of a single-mode multi-corner session other than TT; per-mode (MM) kits
                       bind FF through one staged FF SDC (HEAD-CORE-R17 / SIGNOFF-MODES)
  ff_binding           OT_VCLK_FF = sdc_lint insertion_ff_ps = clock_binding ff = 202.5; TT 250 (METHODOLOGY 12.3)
  clock_pin_geometry   every file that places/declares a clock port: M5, centre on the M5 track, >= 0.048 x 0.48
                       (io.tcl, core_infra_impl.tcl procs + master_core_infra.tcl calls, pins.json) (GEOM-21)
  rc_calibration       the kit RC file(s) carry signal + clock calibration records (FLOW-RC-1 check_rc_cal)
  duplicate_modules    no module defined twice in VERILOG_FILES (and no file listed twice)
  keep_hook            (* keep *) registers -> SYNTH_CANONICALIZE_TCL keep-regs hook staged and enabled; keep-by-name
                       module lists match a defined module and survive the $paramod rename
  pins_canonical       freeze.json records pins_canon_sha256 (GATE-PINS-2) and the kit pin file's canonical sha equals
                       it (and the plan pin file's, when the plan file is reachable)
  mesh_vias            kit clock-mesh inputs have a VIA89 at every strap crossing (mesh-vias-g0)
  macro_channels       every macro column has a >= MIN_CHANNEL_UM routing channel on both sides (vertical) and every
                       stacked column an interior horizontal channel
  clock_entry_clear    no clock entry lies over a macro
"""
import json
import re
from pathlib import Path

TT_PS, FF_PS = 250.0, 202.5          # METHODOLOGY 12.3 common core latency (TT setup / FF hold)
TOL = 1e-3
CLOCK_PIN_MIN = (0.048, 0.48)        # GEOM-21
MIN_CHANNEL_UM = 10.8                # 2 x 4.32 halo + 8 rows (HBM-MU-QUAD-6 ASK 07:52; ruling pending)
RC_CAL_LAYERS = ("M2", "M3", "M4", "M5", "M6", "M7")

_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
_VCLK_LAT = re.compile(r"set_clock_latency\b[^\n;]*?-source\s+(?:-(?:early|late|rise|fall)\s+)*" + _NUM +
                       r"[^\n;]*\[get_clocks\s+\{?\s*vclk\s*\}?\s*\]")
_VCLK_LAT_ANY = re.compile(r"set_clock_latency\b[^\n;]*\[get_clocks\s+\{?\s*vclk\s*\}?\s*\]")


def _mk(kd):
    p = Path(kd) / "config.mk"
    v = {}
    if not p.is_file():
        return v
    for line in p.read_text().replace("\\\n", " ").splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s*(?:override\s+)?(?:export\s+)?([A-Za-z_]\w*)\s*[:?]?=\s*(.*?)\s*$", line)
        if m:
            v[m.group(1)] = m.group(2)
    return v


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _eq(a, b):
    return a is not None and abs(float(a) - float(b)) <= TOL


def _kfile(kd, value):
    """kit file for a config value (/work/x -> kit/x); None for platform or host paths."""
    if value.startswith("/work/"):
        return Path(kd) / value[6:]
    if not value.startswith("/"):
        return Path(kd) / value
    return None


def _strip_tcl_comment(line):
    s = line.lstrip()
    return "" if s.startswith("#") else line


def _depth_lines(text):
    """(depth at line start, line) for Tcl text; braces counted outside comment lines."""
    d = 0
    for line in text.splitlines():
        code = _strip_tcl_comment(line)
        yield d, code
        d += code.count("{") - code.count("}")
        d = max(d, 0)


def _hook_files(kd, cfg):
    """kit Tcl/SDC files run by the flow: config *_TCL / *_SDC hooks and every kit file they source (closure)."""
    kd = Path(kd)
    todo = []
    for k, v in cfg.items():
        if k.endswith(("_TCL", "_SDC")) or k in ("SDC_FILE",):
            for w in v.split():
                f = _kfile(kd, w)
                if f is not None and f.is_file():
                    todo.append(f)
    seen = {}
    names = {p.name: p for p in kd.glob("*") if p.suffix in (".tcl", ".sdc")}
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen[f] = True
        for tok in re.findall(r"(?:source|read_sdc)\b[^\n]*?([\w.-]+\.(?:tcl|sdc))", f.read_text(errors="replace")):
            if tok in names and names[tok] not in seen:
                todo.append(names[tok])
    return list(seen)


# ---------------------------------------------------------------------------------------------- 1 corner modes
def corner_modes(kd):
    kd = Path(kd)
    cfg, err = _mk(kd), []
    sdc = kd / "constraint.sdc"
    if not sdc.is_file():
        return ["constraint.sdc missing"], dict(applies=True)
    tt = [float(m.group(1)) for m in _VCLK_LAT.finditer(sdc.read_text())]
    if len(tt) != 1 or not _eq(tt[0], TT_PS):
        err.append(f"constraint.sdc vclk source latency {tt} is not exactly one line = TT {TT_PS:g} (12.3)")
    corners = cfg.get("CORNERS", "").split()
    mm = cfg.get("OT_HOLD_MM", "0") == "1"
    if mm:
        if [c.lower() for c in corners] != ["tc", "bc"] or cfg.get("OT_MM_SETUP_CORNER") != "tc":
            err.append(f"OT_HOLD_MM=1 with CORNERS {cfg.get('CORNERS')!r} / OT_MM_SETUP_CORNER "
                       f"{cfg.get('OT_MM_SETUP_CORNER')!r}: need one TT setup mode (tc) + one FF hold mode (BC)")
        f = _kfile(kd, cfg.get("OT_MM_FF_SDC", ""))
        if f is None or not f.is_file():
            err.append(f"OT_HOLD_MM=1 but OT_MM_FF_SDC {cfg.get('OT_MM_FF_SDC')!r} is not a staged kit file")
        else:
            ff = [float(m.group(1)) for m in _VCLK_LAT.finditer(f.read_text())]
            if len(ff) != 1 or not _eq(ff[0], FF_PS):
                err.append(f"{f.name} (FF mode SDC) vclk latency {ff} is not exactly one line = FF {FF_PS:g}")
    hooks = _hook_files(kd, cfg)
    for f in hooks:
        if f.name == "constraint.sdc" or (mm and f.name == Path(cfg.get("OT_MM_FF_SDC", "")).name):
            continue
        for depth, line in _depth_lines(f.read_text(errors="replace")):
            m = _VCLK_LAT.search(line)
            if not m or depth:
                continue
            v = float(m.group(1))
            if mm:
                err.append(f"{f.name}: global vclk latency {v:g} in a per-mode (MM) session: binds both modes "
                           "(phantom corner); bind FF through OT_MM_FF_SDC only")
            elif len(corners) > 1 and not _eq(v, TT_PS):
                err.append(f"{f.name}: global vclk latency {v:g} applied to every corner of the single-mode "
                           f"session CORNERS '{' '.join(corners)}' (TT scene timed at {v:g}, not TT {TT_PS:g})")
    # every literal vclk latency anywhere in the kit's generated Tcl/SDC is one of the two corner values
    for f in sorted(list(kd.glob("*.tcl")) + list(kd.glob("*.sdc"))):
        for line in f.read_text(errors="replace").splitlines():
            if not _strip_tcl_comment(line):
                continue
            m = _VCLK_LAT.search(line)
            if m and not (_eq(float(m.group(1)), TT_PS) or _eq(float(m.group(1)), FF_PS)):
                err.append(f"{f.name}: vclk latency {float(m.group(1)):g} is neither TT {TT_PS:g} nor FF {FF_PS:g}")
    for p in kd.glob("eco_modes*.json"):
        d = json.loads(p.read_text())
        if not (_eq(d.get("ot_vclk_tt"), TT_PS) and _eq(d.get("ot_vclk_ff"), FF_PS)):
            err.append(f"{p.name}: ECO modes TT {d.get('ot_vclk_tt')} / FF {d.get('ot_vclk_ff')} != {TT_PS:g}/{FF_PS:g}")
    return list(dict.fromkeys(err)), dict(applies=True, corners=corners, per_mode=mm, hooks=sorted(f.name for f in hooks))


# ---------------------------------------------------------------------------------------------- 2 FF binding
def ff_binding(kd):
    kd = Path(kd)
    cfg, err = _mk(kd), []
    vals = dict(OT_VCLK_TT=_num(cfg.get("OT_VCLK_TT")), OT_VCLK_FF=_num(cfg.get("OT_VCLK_FF")))
    lint = kd / "sdc_lint.json"
    if lint.is_file():
        d = json.loads(lint.read_text())
        vals.update(sdc_lint_insertion_ps=_num(d.get("insertion_ps")), sdc_lint_insertion_ff_ps=_num(d.get("insertion_ff_ps")))
    else:
        err.append("sdc_lint.json missing")
    cb = kd / "clock_binding.json"
    if cb.is_file():
        ins = json.loads(cb.read_text()).get("insertion_ps") or {}
        vals.update(clock_binding_tt=_num(ins.get("tt")), clock_binding_ff=_num(ins.get("ff")))
    fz = kd / "freeze.json"
    if fz.is_file():
        d = json.loads(fz.read_text())
        for k in ("insertion_ff_ps", "ff_bound_ps"):
            if k in d:
                vals["freeze_" + k] = _num(d[k])
    for k, v in vals.items():
        want = FF_PS if ("FF" in k or k.endswith(("_ff", "_ff_ps", "bound_ps"))) else TT_PS
        if not _eq(v, want):
            err.append(f"{k} = {v} (must be {want:g}: 12.3 TT setup {TT_PS:g} / FF hold {FF_PS:g})")
    return err, dict(applies=True, values=vals)


# ---------------------------------------------------------------------------------------------- 3 clock pin
def clock_ports(kd):
    kd = Path(kd)
    ports = set()
    sdc = kd / "constraint.sdc"
    if sdc.is_file():
        for m in re.finditer(r"create_clock\b[^\n]*\[get_ports\s+(\{[^}]*\}|[^\]\s]+)\s*\]", sdc.read_text()):
            ports.update(m.group(1).strip("{}").split())
    pj = kd / "pins.json"
    if pj.is_file():
        for p in _kit_pins(json.loads(pj.read_text())):
            if p.get("clock") or p.get("clock_entry") or p.get("is_clock_entry"):
                ports.add(p["name"])
    return ports


def _base(n):
    return re.sub(r"\[0\]$", "", n)


def _is_clock(name, ports):
    return name in ports or _base(name) in {_base(p) for p in ports}


def clock_pin_geometry(kd):
    import master_slice as MS
    kd = Path(kd)
    ports, err, seen = clock_ports(kd), [], {}
    if not ports:
        return ["no clock port found (constraint.sdc create_clock / pins.json clock)"], dict(applies=True)
    entries = []

    def judge(src, name, layer, x, y, w, h):
        seen[_base(name)] = seen.get(_base(name), 0) + 1
        if layer != "M5":
            err.append(f"{src}: clock {name} on {layer}, not M5")
        if w is None or h is None or w < CLOCK_PIN_MIN[0] - 1e-6 or h < CLOCK_PIN_MIN[1] - 1e-6:
            err.append(f"{src}: clock {name} pin_size {w}x{h} < {CLOCK_PIN_MIN[0]}x{CLOCK_PIN_MIN[1]} (GEOM-21)")
        if layer == "M5" and x is not None:
            try:
                if not MS.on_track(kd, "M5", x, y):
                    err.append(f"{src}: clock {name} centre ({x:g}, {y:g}) off the M5 routing track (GEOM-21)")
            except ValueError as e:
                err.append(f"{src}: clock {name}: {e}")
        if x is not None:
            entries.append((src, name, x, y))

    procs = {}   # proc name -> (layer, w, h) for procs that place_pin a variable pin name
    tcls = sorted(kd.glob("*.tcl"))
    for f in tcls:
        txt = f.read_text(errors="replace")
        for m in re.finditer(r"^proc\s+(\S+)\s+\{([^}]*)\}\s*\{(.*?)^\}", txt, re.M | re.S):
            pm = re.search(r"place_pin\s+-pin_name\s+\$\w+\s+-layer\s+(\S+)[^\n]*?-pin_size\s+\{\s*([\d.]+)\s+([\d.]+)\s*\}",
                           m.group(3))
            if pm:
                procs[m.group(1)] = (pm.group(1), float(pm.group(2)), float(pm.group(3)))
    for f in tcls:
        for line in f.read_text(errors="replace").splitlines():
            if not _strip_tcl_comment(line):
                continue
            m = re.match(r"^\s*place_pin\s+-pin_name\s+(\{[^}]*\}|\S+)(.*)$", line)
            if m:
                n = m.group(1).strip("{}").strip()
                if n.startswith("$") or not _is_clock(n, ports):
                    continue
                lm = re.search(r"-layer\s+(\S+)", line)
                xm = re.search(r"-location\s+\{\s*" + _NUM + r"\s+" + _NUM + r"\s*\}", line)
                sm = re.search(r"-pin_size\s+\{\s*" + _NUM + r"\s+" + _NUM + r"\s*\}", line)
                judge(f.name, n, lm.group(1) if lm else None, float(xm.group(1)) if xm else None,
                      float(xm.group(2)) if xm else None, float(sm.group(1)) if sm else None,
                      float(sm.group(2)) if sm else None)
                continue
            toks = line.split()
            if toks and toks[0] in procs and len(toks) >= 4:
                n = toks[1].strip("{}")
                if not _is_clock(n, ports):
                    continue
                lay, w, h = procs[toks[0]]
                xy = [_num(t.strip("{}")) for t in toks[2:]]
                xy = [v for v in xy if v is not None][:2]
                judge(f"{f.name}->{toks[0]}", n, lay, *(xy + [None, None])[:2], w, h)
    placed = {n for n in seen}
    # pins.json does not place pins; a clock entry it declares differently from the placing files is reported
    # (die pin match reads the pin file) but is not a placement FAIL here.
    warnings, placing_errors = [], len(err)
    pj = kd / "pins.json"
    if pj.is_file():
        for p in _kit_pins(json.loads(pj.read_text())):
            if _is_clock(p["name"], ports):
                sz = p.get("size") or [p.get("w"), p.get("h")]
                judge("pins.json", p["name"], p.get("layer"), _num(p.get("x")), _num(p.get("y")),
                      _num(sz[0]) if sz else None, _num(sz[1]) if sz else None)
        warnings, err = err[placing_errors:], err[:placing_errors]
    for p in sorted(ports):
        if _base(p) not in placed:
            err.append(f"clock {p}: no static placement found in any kit file (cannot verify M5 entry)")
    return list(dict.fromkeys(err)), dict(applies=True, clock_ports=sorted(ports), placements=seen,
                                          entries=[list(e) for e in entries if e[0] != "pins.json"],
                                          pins_json_warnings=list(dict.fromkeys(warnings))[:20])


# ---------------------------------------------------------------------------------------------- 4 RC calibration
def check_rc_text(txt):
    """FLOW-RC-1 check_rc_cal (claude/flow-rc-1027@2bbe885e4 tools/die_plan/core_flow.py), as a findings list."""
    rec = dict(re.findall(r"^#\s*OT_RC_CAL\s+(signal|clock)\s+(\S.*)$", txt, re.M))
    miss = [f"# OT_RC_CAL {k} record" for k in ("signal", "clock") if k not in rec]
    miss += [f"set_wire_rc -{k}" for k in ("signal", "clock")
             if not re.search(rf"^set_wire_rc\s+-{k}\s+-resistance\s+\S+\s+-capacitance\s+\S+", txt, re.M)]
    miss += [f"set_layer_rc {L}" for L in RC_CAL_LAYERS
             if not re.search(rf"^set_layer_rc\s+-layer\s+{L}\s+-resistance\s+\S+\s+-capacitance\s+\S+", txt, re.M)]
    return miss, rec


def rc_calibration(kd):
    kd = Path(kd)
    cfg, err, recs = _mk(kd), [], {}
    files = []
    for k in ("SET_RC_TCL", "LAYER_PARASITICS_FILE"):
        v = cfg.get(k, "").strip()
        if not v:
            continue
        f = _kfile(kd, v)
        if f is None:
            err.append(f"{k} {v}: not a staged kit RC file (platform default RC is uncalibrated)")
        elif not f.is_file():
            err.append(f"{k} {v}: missing")
        elif f not in files:
            files.append(f)
    if not files and not err:
        err.append("no SET_RC_TCL / LAYER_PARASITICS_FILE: kit runs on the platform RC (no signal/clock calibration)")
    for f in files:
        miss, rec = check_rc_text(f.read_text(errors="replace"))
        recs[f.name] = rec
        if miss:
            err.append(f"{f.name}: no {', '.join(miss)} (FLOW-RC-1: signal + clock calibration required)")
    return err, dict(applies=True, files=[f.name for f in files], records=recs)


# ---------------------------------------------------------------------------------------------- 5 duplicate modules
_MOD = re.compile(r"^\s*(?:\(\*.*?\*\)\s*)*(?:module|macromodule)\s+(?:automatic\s+|static\s+)?(\\\S+|[A-Za-z_][\w$]*)",
                  re.M)


def _strip_v(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def sources(kd):
    import rtl_lint
    return rtl_lint._kit_sources(Path(kd))


def duplicate_modules(kd):
    err, where, listed = [], {}, {}
    for p in sources(kd):
        key = str(p.resolve()) if p.exists() else str(p)
        listed[key] = listed.get(key, 0) + 1
        if not p.is_file():
            err.append(f"source {p} missing")
            continue
        for m in _MOD.finditer(_strip_v(p.read_text(errors="replace"))):
            where.setdefault(m.group(1), []).append(p.name)
    err += [f"source listed {n} times: {k}" for k, n in listed.items() if n > 1]
    err += [f"module {m} defined {len(fs)} times ({', '.join(fs)})" for m, fs in sorted(where.items()) if len(fs) > 1]
    return err, dict(applies=True, modules=len(where), files=len(listed))


# ---------------------------------------------------------------------------------------------- 6 keep hook
_KEEP_ATTR = re.compile(r"\(\*[^*]*?\bkeep\b(?!_)(?:\s*=\s*(\"?)(?:1|true|TRUE|yes)\1)?[^*]*\*\)")
_KEEP_OFF = re.compile(r"\(\*[^*]*?\bkeep\b(?!_)\s*=\s*\"?(?:0|false|FALSE|no)\"?[^*]*\*\)")


def keep_hook(kd):
    kd = Path(kd)
    cfg, err = _mk(kd), []
    texts = {p.name: _strip_v(p.read_text(errors="replace")) for p in sources(kd) if p.is_file()}
    keeps = sum(len(_KEEP_ATTR.findall(t)) - len(_KEEP_OFF.findall(t)) for t in texts.values())
    info = dict(applies=False, keep_attrs=keeps)
    if keeps > 0:
        info["applies"] = True
        hook = _kfile(kd, cfg.get("SYNTH_CANONICALIZE_TCL", "") or "/")
        if hook is None or not cfg.get("SYNTH_CANONICALIZE_TCL") or not hook.is_file():
            err.append(f"{keeps} (* keep *) register attributes but SYNTH_CANONICALIZE_TCL "
                       f"{cfg.get('SYNTH_CANONICALIZE_TCL')!r} is not a staged keep-regs hook: opt_merge folds the copies")
        else:
            t = hook.read_text(errors="replace")
            if not (re.search(r"a:keep", t) and re.search(r"setattr\s+-set\s+keep\s+1", t)):
                err.append(f"{hook.name}: not the keep-regs hook (no w:* a:keep selection / setattr -set keep 1)")
        if cfg.get("OT_KEEP_REGS", "1").strip() == "0":
            err.append("OT_KEEP_REGS=0 disables the keep-regs hook while the RTL declares keep registers")
    # keep-by-name module lists must match a defined module, and a parameterised module instantiated with
    # parameter overrides is renamed $paramod$...\name by Yosys: a plain-name keep then matches nothing.
    defined = {m.group(1) for t in texts.values() for m in _MOD.finditer(t)}
    paramd = {m.group(1) for t in texts.values()
              for m in re.finditer(r"^\s*(?:\(\*.*?\*\)\s*)*module\s+([A-Za-z_]\w*)\s*(?:import\s[^;]*;\s*)?#\s*\(", t, re.M)}
    attr_kh = {m.group(1) for t in texts.values()
               for m in re.finditer(r"\(\*[^*]*\bkeep_hierarchy\b[^*]*\*\)\s*module\s+([A-Za-z_]\w*)", t)}
    overridden = {m for m in paramd if any(re.search(r"(?<![\w$])" + re.escape(m) + r"\s*#\s*\(", t) for t in texts.values())}
    named = set()
    for k, v in cfg.items():
        if re.search(r"KEEP.*MODULE|KEEP_HIER", k):
            named |= set(v.split())
    for f in kd.glob("*.tcl"):
        for m in re.finditer(r"setattr\s+-mod\s+-set\s+keep_hierarchy\s+\S+\s+([^\n;\]]+)", f.read_text(errors="replace")):
            named |= {w.strip("{}") for w in m.group(1).split() if not w.startswith(("@", "-", "$::"))}
    for n in sorted(named):
        if any(c in n for c in "*?"):
            if n.startswith("$paramod") or n.startswith("*"):
                continue
            base = n
        else:
            base = n
        if base not in defined:
            err.append(f"keep module {n}: no such module in the source list (keep matches nothing)")
        elif base in overridden and base not in attr_kh:
            err.append(f"keep module {n}: parameterised and instantiated with overrides -> Yosys renames it "
                       f"$paramod...\\{n}; the name-based keep matches nothing (keep by source attribute or "
                       "post-rename name)")
    if named:
        info["applies"] = True
    info.update(named_keep_modules=sorted(named), paramod_renamed=sorted(overridden & named))
    return err, info


# ---------------------------------------------------------------------------------------------- 7 pins canonical
def _kit_pins(doc):
    rows = doc.get("pins", []) if isinstance(doc, dict) else doc
    out = []
    for p in rows:
        p = dict(p)
        if "name" not in p:
            b, bit = p.get("bus"), p.get("bit")
            p["name"] = b if bit is None else f"{b}[{bit}]"
        out.append(p)
    return out


def _canon(doc, outline):
    import die_sta_related as DSR
    d = dict(doc) if isinstance(doc, dict) else dict(pins=doc)
    d["pins"] = _kit_pins(d)
    return DSR.canon_sha256(DSR.canon_pins(d, outline))


def placed_pins(kd):
    """the kit's placed pin set in plan pin-file form [{name, layer, x, y}] (pin centres) from io.tcl, without the
    kit-added pins of pins_added.json (they are not plan pins)."""
    kd = Path(kd)
    added = set()
    pa = kd / "pins_added.json"
    if pa.is_file():
        d = json.loads(pa.read_text())
        for p in (d.get("added", []) if isinstance(d, dict) else d):
            added.add(p if isinstance(p, str) else (p.get("name") or
                      (p["bus"] if p.get("bit") is None else f"{p['bus']}[{p['bit']}]")))
    pins = {}
    for line in (kd / "io.tcl").read_text(errors="replace").splitlines():
        m = re.match(r"\s*place_pin\s+-pin_name\s+(\{[^}]*\}|\S+)\s+-layer\s+(\S+)\s+-location\s+\{\s*" + _NUM +
                     r"\s+" + _NUM + r"\s*\}", line)
        if m and m.group(1).strip("{}").strip() not in added:
            n = m.group(1).strip("{}").strip()
            pins[n] = dict(name=n, layer=m.group(2), x=float(m.group(3)), y=float(m.group(4)))
    return list(pins.values())


def pins_canonical(kd, plan_dir=None):
    """GATE-PINS-2: freeze.json pins_canon_sha256 recorded; the kit's placed pin set (io.tcl centres, plan form) has
    that canonical sha; a reachable plan pin file (whole-file sha = freeze pins_sha256) has it too."""
    import hashlib
    kd = Path(kd)
    err = []
    fz = kd / "freeze.json"
    if not fz.is_file():
        return ["freeze.json missing (no pin provenance)"], dict(applies=True)
    if not (kd / "io.tcl").is_file():
        return ["io.tcl missing (no placed pin set)"], dict(applies=True)
    F = json.loads(fz.read_text())
    outline = F.get("outline_um")
    if not outline:
        m = re.search(r"^\s*export\s+DIE_AREA\s*:?=\s*\S+\s+\S+\s+(\S+)\s+(\S+)", (kd / "config.mk").read_text(), re.M)
        outline = [float(m.group(1)), float(m.group(2))] if m else None
    want = F.get("pins_canon_sha256")
    kit_c = _canon(placed_pins(kd), outline)
    info = dict(applies=True, kit_canon=kit_c, recorded=want, plan_file=None, plan_canon=None)
    if not want:
        err.append("freeze.json has no pins_canon_sha256 (GATE-PINS-2 canonical pin hash not recorded)")
    elif kit_c != want:
        err.append(f"kit placed pins (io.tcl) canonical sha {kit_c[:12]} != freeze pins_canon_sha256 {want[:12]} "
                   "(kit pin set is not the plan pin file)")
    pf = F.get("pins_file")
    cands = []
    if pf:
        cands += [kd / "plan_pins.json", kd / Path(pf).name]
        if plan_dir:
            cands.append(Path(plan_dir) / pf)
        if Path(pf).is_absolute():
            cands.append(Path(pf))
    for c in cands:
        if c.is_file() and c.name != "pins.json":
            b = c.read_bytes()
            if F.get("pins_sha256") and hashlib.sha256(b).hexdigest() != F["pins_sha256"]:
                continue
            pc = _canon(json.loads(b), outline)
            info.update(plan_file=str(c), plan_canon=pc)
            if pc != kit_c:
                err.append(f"kit placed pins canonical sha {kit_c[:12]} != plan pin file {c.name} {pc[:12]}")
            if want and pc != want:
                err.append(f"plan pin file {c.name} canonical sha {pc[:12]} != recorded {want[:12]}")
            break
    return err, info


# ---------------------------------------------------------------------------------------------- 8 mesh vias
def mesh_vias(kd):
    kd = Path(kd)
    meshes = []
    for f in sorted(kd.glob("*.json")):
        if f.stat().st_size > 64 << 20:
            continue
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("xs"), list) and isinstance(d.get("ys"), list):
            meshes.append((f, d))
    if not meshes:
        return [], dict(applies=False, reason="no clock-mesh inputs in the kit")
    import die_clock_mesh as DCM
    err = []
    for f, M in meshes:
        err += [f"{f.name}: {x}" for x in DCM.mesh_via_findings(M, kd)]
    return err, dict(applies=True, meshes=[f.name for f, _ in meshes])


# ---------------------------------------------------------------------------------------------- 9/10 macros
def _lef_sizes(kd, cfg):
    sizes = {}
    files = list((Path(kd) / "macros").glob("*.lef")) if (Path(kd) / "macros").is_dir() else []
    for w in cfg.get("ADDITIONAL_LEFS", "").split():
        f = _kfile(kd, w)
        if f is not None and f.is_file() and f not in files:
            files.append(f)
    for f in files:
        for m in re.finditer(r"^MACRO\s+(\S+)(.*?)^END\s+\1", f.read_text(errors="replace"), re.M | re.S):
            s = re.search(r"SIZE\s+" + _NUM + r"\s+BY\s+" + _NUM, m.group(2))
            if s:
                sizes[m.group(1)] = (float(s.group(1)), float(s.group(2)))
    return sizes


def _tcl_list(s):
    """split a Tcl list (brace groups kept as one element, outer braces stripped)."""
    out, i, s = [], 0, s.strip()
    while i < len(s):
        if s[i].isspace():
            i += 1
            continue
        if s[i] == "{":
            d, j = 1, i + 1
            while j < len(s) and d:
                d += {"{": 1, "}": -1}.get(s[j], 0)
                j += 1
            out.append(s[i + 1:j - 1])
            i = j
        else:
            j = i
            while j < len(s) and not s[j].isspace():
                j += 1
            out.append(s[i:j])
            i = j
    return out


def _foreach_lists(txt):
    """[(vars, list body)] of every `foreach {v1 v2 ..} {list} {` in Tcl text."""
    out = []
    for m in re.finditer(r"foreach\s+\{([^}]*)\}\s+\{", txt):
        d, j = 1, m.end()
        while j < len(txt) and d:
            d += {"{": 1, "}": -1}.get(txt[j], 0)
            j += 1
        out.append((m.group(1).split(), txt[m.end():j - 1]))
    return out


def _plan_contents(kd, plan_dir):
    """{instance: contents entry} of this partition kit's type from plan_dir/die_plan.json (budget.json type)."""
    if not plan_dir:
        return None
    pf = Path(plan_dir) / "die_plan.json"
    bj = Path(kd) / "budget.json"
    if not pf.is_file() or not bj.is_file():
        return None
    typ = json.loads(bj.read_text()).get("type")
    pt = json.loads(pf.read_text()).get("partition_types", {}).get(typ)
    if not pt:
        return None
    return {e["inst"]: e for e in pt.get("contents", []) if isinstance(e, dict) and e.get("inst") and e.get("outline_um")}


def macro_boxes(kd, plan_dir=None):
    """(boxes [(name, x0, y0, x1, y1)], problem or None) from the kit's static macro placement."""
    kd = Path(kd)
    cfg = _mk(kd)
    sizes = _lef_sizes(kd, cfg)
    if not sizes:
        return [], None
    mp = _kfile(kd, cfg.get("MACRO_PLACEMENT_TCL", "") or "/")
    if not cfg.get("MACRO_PLACEMENT_TCL") or mp is None or not mp.is_file():
        return None, (f"{len(sizes)} macro master(s) but no staged MACRO_PLACEMENT_TCL "
                      f"({cfg.get('MACRO_PLACEMENT_TCL')!r}): placement not static, channels/entry not checkable")
    txt = mp.read_text(errors="replace")
    boxes = []
    for vars_, body in _foreach_lists(txt):
        if "master" not in vars_:
            continue
        vals = _tcl_list(body)
        n = len(vars_)
        if n == 0 or len(vals) % n:
            return None, f"{mp.name}: foreach {{{' '.join(vars_)}}} list length {len(vals)} not a multiple of {n}"
        for k in range(0, len(vals), n):
            row = dict(zip(vars_, vals[k:k + n]))
            master = row["master"]
            if master not in sizes:
                return None, f"macro {master}: no LEF SIZE"
            sites = [_tcl_list(s) for s in _tcl_list(row["sites"])] if "sites" in row else \
                [[row.get("x"), row.get("y"), row.get("orient", "R0")]]
            for i, s in enumerate(sites):
                x, y, o = float(s[0]), float(s[1]), (s[2] if len(s) > 2 else "R0")
                w, h = sizes[master]
                if o in ("R90", "R270", "MXR90", "MYR90"):
                    w, h = h, w
                boxes.append((f"{master}#{len(boxes)}", x, y, x + w, y + h))
    pm = list(re.finditer(r"place_macro\s+-macro_name\s+(\S+)\s+-location\s+\{\s*" + _NUM + r"\s+" + _NUM +
                          r"\s*\}(?:\s+-orientation\s+(\S+))?", txt))
    if pm:
        # gen.py phys partition form: instance names at plan sites. KV-KITS-7: master + outline come from the plan's
        # partition_types[type].contents entry of that instance (plan_dir/die_plan.json, type from budget.json); a
        # staged LEF SIZE of the master must agree. No plan -> fail closed.
        inst = _plan_contents(kd, plan_dir)
        if inst is None:
            return None, "place_macro by instance name: no plan contents (pass --plan-dir) to resolve macro masters"
        for m in pm:
            name = m.group(1).strip("{}").replace("\\[", "[").replace("\\]", "]")
            x, y, o = float(m.group(2)), float(m.group(3)), (m.group(4) or "R0")
            ent = inst.get(name)
            if ent is None:
                return None, f"place_macro {name}: not a contents macro of this type in the plan"
            w, h = map(float, ent["outline_um"])
            master = ent.get("module")
            if master in sizes and (abs(sizes[master][0] - w) > 1e-3 or abs(sizes[master][1] - h) > 1e-3):
                return None, f"macro {master}: LEF SIZE {sizes[master]} != plan outline {(w, h)}"
            if o in ("R90", "R270", "MXR90", "MYR90"):
                w, h = h, w
            boxes.append((f"{master}#{len(boxes)}", x, y, x + w, y + h))
    # gen_core_kit_kv --hard-children form (one block per instance): master match, setOrient, setLocation
    # [expr {round(X * $dbu) ...}] [expr {round(Y * $dbu) ...}] (KV-KITS-7: static FIRM sites, was "no macro sites parsed")
    for m in re.finditer(r'getName\] eq "(\S+)".*?\$i setOrient (\S+).*?setLocation \[expr \{round\(' + _NUM +
                         r' \* \$dbu\)[^\n]*?\[expr \{round\(' + _NUM + r' \* \$dbu\)', txt, re.S):
        master, o, x, y = m.group(1), m.group(2), float(m.group(3)), float(m.group(4))
        if master not in sizes:
            return None, f"macro {master}: no LEF SIZE"
        w, h = sizes[master]
        if o in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        boxes.append((f"{master}#{len(boxes)}", x, y, x + w, y + h))
    if not boxes:
        return None, f"{mp.name}: no macro sites parsed"
    return boxes, None


def _core(kd):
    cfg = _mk(kd)
    for k in ("CORE_AREA", "DIE_AREA"):
        v = [_num(t) for t in cfg.get(k, "").split()]
        if len(v) == 4 and None not in v:
            return v
    return None


def _clusters(boxes, a0, a1):
    """groups of boxes overlapping on axis interval (a0, a1 indices)."""
    bs = sorted(boxes, key=lambda b: b[a0])
    out = []
    for b in bs:
        if out and b[a0] < max(x[a1] for x in out[-1]) - 1e-6:
            out[-1].append(b)
        else:
            out.append([b])
    return out


def macro_channels(kd, plan_dir=None, min_um=MIN_CHANNEL_UM):
    boxes, prob = macro_boxes(kd, plan_dir)
    if boxes == [] and prob is None:
        return [], dict(applies=False, reason="no macros")
    if prob:
        return [prob], dict(applies=True)
    core = _core(kd)
    if core is None:
        return ["CORE_AREA/DIE_AREA missing"], dict(applies=True)
    err = []
    cols = _clusters(boxes, 1, 3)               # x-overlap clusters = macro columns
    edges = [core[0]] + [v for c in cols for v in (min(b[1] for b in c), max(b[3] for b in c))] + [core[2]]
    for i, c in enumerate(cols):
        lo, hi = min(b[1] for b in c), max(b[3] for b in c)
        wgap, egap = lo - edges[2 * i], edges[2 * i + 3] - hi
        for side, g in (("W", wgap), ("E", egap)):
            if g < min_um - 1e-6:
                err.append(f"macro column {i} x[{lo:g},{hi:g}]: {side} vertical channel {g:.3f} um < {min_um:g}")
        stack = sorted(c, key=lambda b: b[2])
        if len(stack) > 1:
            gaps = [stack[k + 1][2] - stack[k][4] for k in range(len(stack) - 1)]
            if max(gaps) < min_um - 1e-6:
                err.append(f"macro column {i}: {len(stack)} stacked macros with no interior horizontal channel "
                           f">= {min_um:g} um (largest gap {max(gaps):.3f})")
    return err, dict(applies=True, macros=len(boxes), columns=len(cols), min_channel_um=min_um,
                     min_channel_note="10.8 um = 2x4.32 halo + 8 rows, HBM-MU-QUAD-6 ASK pending COORD ruling")


def clock_entry_clear(kd, plan_dir=None, entries=None):
    boxes, prob = macro_boxes(kd, plan_dir)
    if boxes == [] and prob is None:
        return [], dict(applies=False, reason="no macros")
    if prob:
        return [prob], dict(applies=True)
    if entries is None:
        entries = clock_pin_geometry(kd)[1].get("entries", [])
    pts = list(entries)
    ms = Path(kd) / "master_slice.json"
    if ms.is_file():
        for isl in json.loads(ms.read_text()).get("islands", []) or []:
            cp = isl.get("clock_pin")
            if cp and cp.get("xy_um"):
                pts.append(("master_slice.json", isl.get("name"), *map(float, cp["xy_um"])))
    if not pts:
        return ["no clock entry coordinates found"], dict(applies=True)
    err = []
    for src, name, x, y in pts:
        for b in boxes:
            if b[1] - 1e-6 <= x <= b[3] + 1e-6 and b[2] - 1e-6 <= y <= b[4] + 1e-6:
                err.append(f"{src}: clock entry {name} ({x:g}, {y:g}) over macro {b[0]} {[round(v, 3) for v in b[1:]]}")
    return list(dict.fromkeys(err)), dict(applies=True, entries=len(pts), macros=len(boxes))


CHECKS = ("corner_modes", "ff_binding", "clock_pin_geometry", "rc_calibration", "duplicate_modules", "keep_hook",
          "pins_canonical", "mesh_vias", "macro_channels", "clock_entry_clear")


def is_core_kit(kd):
    """hard-core kit (S81/HEAD/QC/KV/HBM core generators): core freeze schema, core master slice, or core.json."""
    kd = Path(kd)
    try:
        if "core" in str(json.loads((kd / "freeze.json").read_text()).get("schema", "")):
            return True
    except (OSError, ValueError):
        pass
    try:
        if json.loads((kd / "master_slice.json").read_text()).get("kind") == "core":
            return True
    except (OSError, ValueError):
        pass
    return (kd / "core.json").is_file() or (kd / "core_infra_plan.json").is_file()


def run_all(kd, plan_dir=None):
    out = {}
    for name in CHECKS:
        fn = globals()[name]
        try:
            errors, info = fn(kd, plan_dir) if name in ("pins_canonical", "macro_channels", "clock_entry_clear") else fn(kd)
        except Exception as error:      # fail closed: a check that cannot run is a FAIL, never a skip
            errors, info = [f"check could not run: {type(error).__name__}: {error}"], dict(applies=True)
        verdict = "FAIL" if errors else ("PASS" if info.get("applies", True) else "NA")
        out[name] = dict(verdict=verdict, errors=errors[:40], n_errors=len(errors), info=info)
    return out
