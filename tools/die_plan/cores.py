"""Hard-core views for the die-plan tools (CP2: abutted pair with hard cores).

- lef_pins(LEF)          {pin base name: dict(dir, use, width, bits, xy)} of the core's MACRO (PIN / DIRECTION / USE,
                         bus bits 'name[i]' grouped; xy = centre of the first RECT, core frame).
- lib_clocks(LIB)        {clock pin: dict(rise, fall, min_rise, min_fall)}: pins with `clock : true` and their
                         max_clock_tree_path / min_clock_tree_path (ETM internal clock latency, ps; 0 if absent).
- find_views(DIR, mod)   (lef, tt_lib, ff_lib) under DIR/<anything>/views/<mod>/ (fetch_core_views.sh layout).
- fill_views(raw, DIR)   fills hard_cores[].lef / .lib (TT) in place where lib (or lef) is null.
- latency_table(P, tn)   [dict(inst, module, pin, rise_ps, fall_ps, tap)] for every clock pin of every hard core of a
                         type (TT lib; a core without a lib or a pin without max_clock_tree_path counts 0 ps).
"""
import re
from pathlib import Path

_PIN = re.compile(r"^\s*PIN\s+(\S+)")
_RECT = re.compile(r"^\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)")


def lef_pins(path, macro=None):
    """pins of MACRO `macro` (default: the first macro) of a LEF file, grouped by bus base name."""
    raw = {}
    in_macro = False
    cur = None
    port = False
    with open(path, errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not in_macro:
                m = re.match(r"^MACRO\s+(\S+)", s)
                if m and (macro is None or m.group(1) == macro):
                    in_macro = True
                    macro = m.group(1)
                continue
            if s.startswith(f"END {macro}"):
                break
            if cur is None:
                m = _PIN.match(line)
                if m:
                    cur = dict(name=m.group(1), dir=None, use="SIGNAL", xy=None)
                continue
            if s == f"END {cur['name']}":
                raw[cur["name"]] = cur
                cur, port = None, False
                continue
            m = re.match(r"^DIRECTION\s+(\w+)", s)
            if m:
                cur["dir"] = m.group(1)
                continue
            m = re.match(r"^USE\s+(\w+)", s)
            if m:
                cur["use"] = m.group(1)
                continue
            if s.startswith("PORT"):
                port = True
                continue
            m = _RECT.match(line)
            if m and port and cur["xy"] is None:
                x0, y0, x1, y1 = map(float, m.groups())
                cur["xy"] = ((x0 + x1) / 2, (y0 + y1) / 2)
    out = {}
    for n, p in raw.items():
        m = re.match(r"^(.*)\[(\d+)\]$", n)
        base, bit = (m.group(1), int(m.group(2))) if m else (n, None)
        q = out.setdefault(base, dict(dir=p["dir"], use=p["use"], bits=[], xy=p["xy"]))
        if bit is not None:
            q["bits"].append(bit)
        if q["dir"] != p["dir"]:
            raise ValueError(f"{path}: bus {base} mixes directions {q['dir']} / {p['dir']}")
    for base, q in out.items():
        if q["bits"]:
            q["bits"].sort()
            q["width"] = q["bits"][-1] + 1
            if q["bits"] != list(range(q["width"])):
                raise ValueError(f"{path}: bus {base} bits are not contiguous from 0 ({len(q['bits'])} of {q['width']})")
        else:
            q["width"] = 0          # scalar
    return out


def _groups(text):
    """yield (kind, name, body) of every `kind ("name") { ... }` group at any depth (brace matched)."""
    for m in re.finditer(r"\b(pin|bus)\s*\(\s*\"?([^\")]+)\"?\s*\)\s*\{", text):
        i, depth = m.end(), 1
        while depth and i < len(text):
            c = text[i]
            depth += (c == "{") - (c == "}")
            i += 1
        yield m.group(1), m.group(2), text[m.end():i - 1]


def _tree_path(body, kind):
    """(rise, fall) of the `timing_type : <kind>` arc of a pin body, or (None, None)."""
    for m in re.finditer(r"timing\s*\(\s*\)\s*\{", body):
        i, depth = m.end(), 1
        while depth and i < len(body):
            depth += (body[i] == "{") - (body[i] == "}")
            i += 1
        t = body[m.end():i - 1]
        if re.search(r"timing_type\s*:\s*" + kind + r"\s*;", t):
            def val(tag):
                v = re.search(tag + r"\s*\([^)]*\)\s*\{\s*values\s*\(\s*\"([-\d.eE+]+)", t)
                return float(v.group(1)) if v else None
            return val("cell_rise"), val("cell_fall")
    return None, None


def lib_time_unit_ps(text):
    m = re.search(r"time_unit\s*:\s*\"?1(ps|ns)\"?", text)
    return 1000.0 if (m and m.group(1) == "ns") else 1.0


def lib_clocks(path):
    """{clock pin: dict(rise, fall, min_rise, min_fall)} in ps (max_clock_tree_path TT = the core's internal latency
    to its flops; 0 where the arc is missing)."""
    text = Path(path).read_text(errors="replace")
    k = lib_time_unit_ps(text)
    out = {}
    for kind, name, body in _groups(text):
        if kind != "pin":
            continue
        # only the pin's own attributes, not a nested group's
        if not re.search(r"(^|\n)\s*clock\s*:\s*true\s*;", re.sub(r"timing\s*\(\s*\)\s*\{.*", "", body, flags=re.S)):
            continue
        r, f = _tree_path(body, "max_clock_tree_path")
        mr, mf = _tree_path(body, "min_clock_tree_path")
        out[name] = dict(rise=(r or 0.0) * k, fall=(f or 0.0) * k, min_rise=(mr or 0.0) * k, min_fall=(mf or 0.0) * k)
    return out


def find_views(root, module, hint=None):
    """(lef, tt_lib, ff_lib) of `module` under ROOT/<dir>/views/<module>/ (missing files None).  Several matching dirs
    (e.g. s81sl_xrt1 and s81sl_xrt1_b): the one named by `hint` (the plan's repo-relative lef path, whose ref_tile
    directory wins) else the shortest directory name; never silently a random one."""
    cands = sorted(Path(root).glob(f"*/views/{module}/{module}.lef"))
    if not cands:
        cands = sorted(Path(root).glob(f"**/views/{module}/{module}.lef"))
    if not cands:
        return None, None, None
    pick = None
    if hint:
        parts = Path(hint).parts
        for c in cands:
            tile = c.parent.parent.parent.name
            if tile in parts:
                pick = c
                break
    if pick is None:
        pick = min(cands, key=lambda c: (len(c.parent.parent.parent.name), str(c)))
    d = pick.parent
    tt, ff = d / f"{module}_tt.lib", d / f"{module}_ff.lib"
    if not tt.is_file() and (d / f"{module}.lib").is_file():
        tt = d / f"{module}.lib"
    return str(pick.resolve()), (str(tt.resolve()) if tt.is_file() else None), \
        (str(ff.resolve()) if ff.is_file() else None)


def fill_views(raw, root):
    """fill hard_cores[].lef / .lib (TT) from ROOT where lib is null (lef replaced by the found absolute path so the
    kit copies the same view the lib belongs to).  Returns [(type, inst, lef, lib)] filled and [(type, inst)] missing."""
    done, miss = [], []
    for tn, t in raw["partition_types"].items():
        for c in t.get("hard_cores", []) or []:
            if c.get("lib") and c.get("lef") and Path(c["lib"]).is_absolute():
                continue
            if c.get("lib"):
                continue
            mod = c.get("module", c["inst"])
            lef, tt, _ = find_views(root, mod, c.get("lef"))
            if not lef or not tt:
                miss.append((tn, c["inst"]))
                continue
            c["lef"], c["lib"] = lef, tt
            done.append((tn, c["inst"], lef, tt))
    return done, miss


def resolve(path, root=None):
    """repo-relative or absolute view path -> Path."""
    p = Path(path)
    if p.is_absolute():
        return p
    base = Path(root) if root else Path(__file__).resolve().parent.parent.parent
    return base / p


def clock_pins(core, root=None):
    """clock pins of a hard core: liberty `clock : true` pins, else LEF USE CLOCK pins.  {pin: latency dict}."""
    if core.get("lib") and resolve(core["lib"], root).is_file():
        ck = lib_clocks(resolve(core["lib"], root))
        if ck:
            return ck
    if core.get("lef") and resolve(core["lef"], root).is_file():
        pins = lef_pins(resolve(core["lef"], root), core.get("module"))
        return {n: dict(rise=0.0, fall=0.0, min_rise=0.0, min_fall=0.0) for n, p in pins.items()
                if p["use"] == "CLOCK" and p["dir"] == "INPUT"}
    return {}


def core_tap_of(t, inst, pin):
    """the core tap port (clk_c<k>) serving inst/pin when the type's clock.core_taps is 'early', else None."""
    ck = t.get("clock", {}) or {}
    if ck.get("core_taps") != "early":
        return None
    k = 0
    for tp in ck.get("taps", []) or []:
        if tp.get("kind") != "core":
            continue
        nm = tp["name"]
        if nm == inst or nm == f"{inst}.{pin}":
            return f"clk_c{k}"
        k += 1
    return None


def latency_table(P, tn, root=None):
    """per clock pin of every hard core of type tn: dict(inst, module, pin, rise_ps, fall_ps, tap)."""
    t = P.types[tn]
    rows = []
    for c in t.get("hard_cores", []) or []:
        ck = clock_pins(c, root)
        for pin, v in sorted(ck.items()):
            rows.append(dict(inst=c["inst"], module=c.get("module", c["inst"]), pin=pin,
                             rise_ps=round(v["rise"], 2), fall_ps=round(v["fall"], 2),
                             lib=c.get("lib"), tap=core_tap_of(t, c["inst"], pin) or "grid"))
    return rows
