"""adv_tap_set_agree.py -- PRECHECK ADV-TAP-SET-AGREE (P-SEAM-UNTIMED-CTL-NSTRIP, HEAD-PART-R3 11-27; DEFAULT OFF, report only).

W13 finding: plan clock.tap_window.per_port_ps.hd_ctl listed clk_t64 while clock.tap_offset and the generated hd_ctl RTL had 63
taps (clk_t1..clk_t63), and the die model carried a W6 hd_ctl view with 64 taps, so clk_t64 was an open input in the die STA and
7 seams were untimed.  This check makes the tap set a single fact per type.

Off unless $OT_PRE_TAPSET=1 (or kw enabled=True); findings() then returns [].  Per partition type the tap sets (names matching
clk_t<k>; "clk" and core clk_c* ports are not taps here) of

  window   clock.tap_window.per_port_ps[T] keys
  offset   clock.tap_offset.per_port_ps[T] keys (only where the plan carries a row)
  rtl      `input ... clk_t<k>` ports of the generated / published module of T (kw rtl_dirs=, else <plan dir>/published and
           $OT_PRE_TAPSET_RTL, ':'-separated; module name = partition_types[T].module)
must agree: window vs offset both ways, and every table name absent from the RTL is a WARN line (RTL taps without a table row are only counted: the window is measured for open ports, the rest use per_type_ps).  A type whose module is in no RTL dir is counted NOT-CHECKED for the
RTL leg (the table-vs-table leg still runs).

Optional view legs (only where supplied; kw views= dir of <module>/ilm.json, $OT_PRE_TAPSET_VIEWS; kw top_sv= die top verilog,
$OT_PRE_TAPSET_TOP):
  view     ilm.json clock_ports tap names vs the RTL taps (a stale view has ports the module lacks, or misses some)
  top      every ilm.json clock port (clk_t*, fclk_in_*) must be connected on the module's instance in the die top
           (.port( in the instance body), else the port is open in the die model (siblings: ctl fclk_in_lepk_i0, nst4 d1/d2, ...)

findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import os
import re
from pathlib import Path

CHECK = "ADV-TAP-SET-AGREE"
MAX_LINES = 25
TAP = re.compile(r"^clk_t\d+$")
IN_PORT = re.compile(r"\binput\b[^;,()]*?\b(clk_t\d+)\b")


def _w(*a):
    return f"WARN {CHECK} " + " ".join(str(x) for x in a)


def enabled(kw=None):
    if kw and "enabled" in kw:
        return bool(kw["enabled"])
    return os.environ.get("OT_PRE_TAPSET") == "1"


def taps(names):
    return {n for n in names if TAP.match(n)}


def rtl_taps(text, module):
    """clk_t<k> input ports of `module` in verilog text (header up to the first ');'); None if the module is absent"""
    m = re.search(r"\bmodule\s+" + re.escape(module) + r"\b(.*?)\)\s*;", text, re.S)
    if not m:
        return None
    return set(IN_PORT.findall(m.group(1)))


def find_rtl(module, dirs):
    for d in dirs:
        d = Path(d)
        for f in ([d / f"{module}.sv", d / f"{module}.v"] if d.is_dir() else []):
            if f.is_file():
                t = rtl_taps(f.read_text(errors="replace"), module)
                if t is not None:
                    return t
        if d.is_dir():                                   # wrapper file named differently (hd_lep0N_w_part.sv)
            for f in sorted(d.glob("*.sv")):
                try:
                    txt = f.read_text(errors="replace")
                except OSError:
                    continue
                if re.search(r"\bmodule\s+" + re.escape(module) + r"\b", txt):
                    t = rtl_taps(txt, module)
                    if t is not None:
                        return t
    return None


def instance_ports(top_text, module):
    """connected port names of every instance of `module` in the die top: [(inst, {ports})]"""
    out = []
    for m in re.finditer(r"^\s*" + re.escape(module) + r"\s+(?:#\(.*?\)\s*)?(\w+)\s*\((.*?)\)\s*;", top_text, re.S | re.M):
        out.append((m.group(1), set(re.findall(r"\.(\w+)\s*\(\s*[^\s)]", m.group(2)))))
    return out


def _num(s):
    return int(s[5:])


def _diff(label_a, a, label_b, b):
    out = []
    if a - b:
        out.append(f"{label_a} only {sorted(a - b, key=_num)}")
    if b - a:
        out.append(f"{label_b} only {sorted(b - a, key=_num)}")
    return out


def _findings(raw, plan_path, tree=None, **kw):
    if not enabled(kw):
        return []
    clk = raw.get("clock") or {}
    win = (clk.get("tap_window") or {}).get("per_port_ps") or {}
    off = (clk.get("tap_offset") or {}).get("per_port_ps") or {}
    pt = raw.get("partition_types") or {}
    dirs = list(kw.get("rtl_dirs") or [])
    dirs += [d for d in (os.environ.get("OT_PRE_TAPSET_RTL") or "").split(":") if d]
    dirs.append(str(Path(plan_path).resolve().parent / "published"))
    views = kw.get("views") or os.environ.get("OT_PRE_TAPSET_VIEWS")
    top_sv = kw.get("top_sv") or os.environ.get("OT_PRE_TAPSET_TOP")
    top_text = Path(top_sv).read_text(errors="replace") if top_sv and Path(top_sv).is_file() else None
    lines, nt, nbad, nort, nview, ntop, nrtlonly = [], 0, 0, 0, 0, 0, 0
    for tn in sorted(set(win) | set(off)):
        if tn not in pt:
            continue
        nt += 1
        mod = (pt[tn] or {}).get("module") or tn
        w = taps(win.get(tn) or {})
        o = taps(off[tn]) if tn in off else None
        r = find_rtl(mod, dirs)
        bad = []
        if o is not None:
            bad += _diff("tap_window", w, "tap_offset", o)
        if r is None:
            nort += 1
        else:
            for lab, tab in (("tap_window", w), ("tap_offset", o or set())):
                if tab - r:
                    bad.append(f"{lab} names {sorted(tab - r, key=_num)} absent from the RTL")
            nrtlonly += bool(r - w - (o or set()))      # RTL taps with no table row: per_type_ps / TAPOFF-MISSING cover those, counted only
        ilm = Path(views) / mod / "ilm.json" if views else None
        if ilm and ilm.is_file():
            nview += 1
            try:
                cp = set(json.loads(ilm.read_text()).get("clock_ports") or [])
            except (OSError, ValueError):
                cp = set()
            if r is not None:
                if taps(cp) - r:                  # a view older than the RTL has ports the module lacks (views list only connected clocks: RTL-only is not judged)
                    bad.append(f"view has tap port(s) {sorted(taps(cp) - r, key=_num)} the RTL module lacks (stale view)")
            if top_text is not None:
                insts = instance_ports(top_text, mod)
                for inst, conn in insts:
                    miss = sorted((p for p in cp if (TAP.match(p) or p.startswith("fclk_in_")) and p not in conn),
                                  key=lambda p: (TAP.match(p) is not None, int(p[5:]) if TAP.match(p) else 0, p))
                    if miss:
                        ntop += 1
                        lines.append(_w(f"{tn}/{inst} (module {mod}): view clock port(s) not connected in the die top {miss[:12]}{' ...' if len(miss) > 12 else ''}: open in the die model, "
                                        f"seams on their flops are untimed"))
        if bad:
            nbad += 1
            lines.append(_w(f"{tn}: tap sets disagree: " + "; ".join(bad)
                            + " (tap_window/tap_offset/RTL must name the same taps; drop a name the RTL lacks from the plan, or add the missing row for a tap the RTL has)"))
    lines = lines[:MAX_LINES]
    lines.append(_w("summary", f"{nbad} of {nt} types with a tap table disagree on the tap set; {nort} types have no RTL module found (RTL leg not checked); "
                               f"{nrtlonly} types have RTL taps without a table row (not a finding: per_type_ps / TAPOFF-MISSING); view leg on {nview} types, {ntop} instances with open view clock ports"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")] if enabled(kw) else []


if __name__ == "__main__":
    import sys
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], enabled=True,
                       rtl_dirs=sys.argv[2].split(":") if len(sys.argv) > 2 else [],
                       views=sys.argv[3] if len(sys.argv) > 3 else None, top_sv=sys.argv[4] if len(sys.argv) > 4 else None):
        print(ln)
