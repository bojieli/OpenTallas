"""Fail-closed lint of a generated partition-kit SDC (CP1-R10, COORD 10-24: past CP1 failures were tool bugs found late).

    python3 tools/die_plan/sdc_lint.py KITDIR [--liberty LIB ...]          # exit 1 on any error

Checks (every one is an ERROR; gen_phys.write_type_kit raises on them, run_kit.sh re-runs it against the image's
liberty files before synthesis):
  units      the liberty time_unit equals gen_phys.LIB_TIME_UNIT_PS (the 10-23 KV-P3b bug: ns values against a ps
             library = a 0.833-ps clock) and every create_clock period x unit = the plan period.
  clocks     every clock referenced (-clock X, get_clocks X) is created; every clock tap port is a create_clock source;
             only tap ports are clock sources; one virtual IO clock whose source latency = the plan insertion.
  ports      every non-clock input has a max AND a min input delay, every output a max AND a min output delay
             (set_*_delay with neither -max nor -min sets both); no delay on a clock port.
  hold       hold uncertainty on every clock; min input delay <= -insertion_tol (seam-hold padding, CP1 r9);
             min output delay <= 0 (a positive min output delay waives the sender's hold check).
  uncertainty  AGENTS.md: setup 60 ps / hold 25 ps on every clock; inter-clock overrides only on the seam pair
             (vclk -> clk, clk -> vclk), and per kind the two halves add up to exactly the full value (once per seam).
  relaxation every period = the plan period, no -waveform; max delays >= the declared IO budgets; and no exception
             command at all (set_false_path, set_multicycle_path, set_max_delay, set_min_delay, set_disable_timing,
             set_clock_groups, set_case_analysis, ... : any command outside the generator's vocabulary is an error).
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ALLOWED = {"create_clock", "set_clock_latency", "set_clock_uncertainty", "set_input_delay", "set_output_delay",
           "set_load", "set_driving_cell", "set"}
UNIT_PS = {"1ps": 1.0, "1ns": 1000.0, "10ps": 10.0, "100ps": 100.0, "1fs": 0.001}
EPS = 1e-3
# AGENTS.md sign-off policy (user decision 2026-09-30), held HERE and not read from the generator under test
POLICY_SETUP_PS, POLICY_HOLD_PS = 60.0, 25.0


class SdcLintError(Exception):
    pass


def liberty_time_unit_ps(path):
    """time_unit of a liberty file (.lib or .lib.gz) in ps."""
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt", errors="replace") as f:
        for i, ln in enumerate(f):
            m = re.search(r'time_unit\s*:\s*"?\s*([0-9.]+\s*[munpf]?s)\s*"?', ln)
            if m:
                u = m.group(1).replace(" ", "")
                if u not in UNIT_PS:
                    raise SdcLintError(f"{path}: unknown time_unit {u}")
                return UNIT_PS[u]
            if i > 2000:
                break
    raise SdcLintError(f"{path}: no time_unit in the header")


# ---- a tiny evaluator for the generator's SDC subset --------------------------------------------------------------
def _split_cmds(text):
    """logical command lines (comments dropped, backslash continuations joined)."""
    out, cur = [], ""
    for ln in text.splitlines():
        s = ln.strip()
        if not cur and (not s or s.startswith("#")):
            continue
        if s.endswith("\\"):
            cur += s[:-1] + " "
            continue
        cur += s
        out.append(cur.strip())
        cur = ""
    if cur.strip():
        out.append(cur.strip())
    return out


def _words(s):
    """Tcl-ish words: [..] and {..} kept whole (nested)."""
    w, i, n = [], 0, len(s)
    while i < n:
        if s[i].isspace():
            i += 1
            continue
        if s[i] in "[{":
            op, cl = s[i], "]" if s[i] == "[" else "}"
            d, j = 0, i
            while j < n:
                if s[j] == op:
                    d += 1
                elif s[j] == cl:
                    d -= 1
                    if d == 0:
                        break
                j += 1
            if d:
                raise SdcLintError(f"unbalanced {op} in: {s}")
            w.append(s[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < n and not s[j].isspace():
                j += 1
            w.append(s[i:j])
            i = j
    return w


class Ctx:
    def __init__(self, inputs, outputs, clock_ports):
        self.inputs, self.outputs, self.clock_ports = list(inputs), list(outputs), list(clock_ports)
        self.allp = self.inputs + self.outputs + self.clock_ports
        self.vars = {}
        self.clocks = {}


def _glob_ports(ctx, pats):
    r = []
    for p in pats:
        base = re.sub(r"\[\*\]$", "", p)
        hit = [q for q in ctx.allp if q == base or re.fullmatch(re.escape(base).replace(r"\*", ".*"), q)]
        if not hit:
            raise SdcLintError(f"get_ports {p}: matches no port")
        r += hit
    return r


def _eval_obj(ctx, w):
    """-> ('ports', [names]) | ('clocks', [names])."""
    if w.startswith("$"):
        v = w[1:]
        if v not in ctx.vars:
            raise SdcLintError(f"undefined variable {w}")
        return ctx.vars[v]
    if w.startswith("{"):
        return ("ports", _glob_ports(ctx, w[1:-1].split()))
    if not w.startswith("["):
        return ("ports", _glob_ports(ctx, [w]))
    a = _words(w[1:-1])
    c = a[0]
    if c == "all_inputs":
        if a[1:] == ["-no_clocks"]:
            return ("ports", list(ctx.inputs))
        if len(a) != 1:
            raise SdcLintError(f"unsupported all_inputs options: {w}")
        return ("ports", ctx.inputs + ctx.clock_ports)
    if c == "all_outputs":
        return ("ports", list(ctx.outputs))
    if c == "all_clocks":
        return ("clocks", list(ctx.clocks))
    if c == "get_ports":
        pats = []
        for x in a[1:]:
            pats += x[1:-1].split() if x.startswith("{") else [x]
        return ("ports", _glob_ports(ctx, pats))
    if c == "get_clocks":
        names = []
        for x in a[1:]:
            names += x[1:-1].split() if x.startswith("{") else [x]
        for nm in names:
            if nm not in ctx.clocks:
                raise SdcLintError(f"get_clocks {nm}: clock not defined")
        return ("clocks", names)
    if c == "lsearch":
        fl = [x for x in a[1:] if x.startswith("-")]
        rest = [x for x in a[1:] if not x.startswith("-")]
        if set(fl) - {"-inline", "-all", "-not", "-regexp", "-exact"} or "-not" not in fl or len(rest) != 2:
            raise SdcLintError(f"unsupported lsearch: {w}")
        kind, lst = _eval_obj(ctx, rest[0])
        pat = rest[1]
        if "-regexp" in fl:
            raise SdcLintError("regexp on port objects cannot filter names in OpenSTA; use all_inputs -no_clocks")
        _, ex = _eval_obj(ctx, pat)
        return (kind, [p for p in lst if p not in ex])
    raise SdcLintError(f"unsupported expression {w}")


def _isopt(x):
    """an option word (-max), not a negative number (-40.0)."""
    return x.startswith("-") and not re.fullmatch(r"-[0-9.]+(e-?[0-9]+)?", x)


def _num(x, what):
    try:
        return float(x)
    except ValueError:
        raise SdcLintError(f"{what}: not a number: {x}")


def lint(text, *, period_ps, insertion_ps, insertion_tol_ps, clock_ports, inputs, outputs,
         unc_setup_ps=60.0, unc_hold_ps=25.0, time_unit_ps=1.0, liberty_unit_ps=None,
         io_floor_ps=None, port_latency_ps=None):
    """lint an SDC.  inputs / outputs: non-clock port (bus) names; clock_ports: the tap ports.  io_floor_ps
    {port: (min_max_delay_ps)}: the declared IO budget per port (max delay must not be below it).  port_latency_ps
    {tap port: ps}: the plan's CP2 early core taps (source latency = -early on exactly those ports).  -> [errors]"""
    err = []
    u = time_unit_ps
    if liberty_unit_ps is not None and abs(liberty_unit_ps - u) > EPS:
        err.append(f"units: liberty time_unit {liberty_unit_ps:g} ps but the SDC is written in {u:g} ps units")
    ctx = Ctx(inputs, outputs, clock_ports)
    clk_src = {}                      # port -> clock
    latency = {}                      # clock -> source latency (ps)
    port_lat = {}                     # clock port -> source latency (ps) (CP2 early core taps)
    unc = {}                          # (kind, from, to) -> ps ; from/to None = global
    idly = {p: {} for p in ctx.allp}  # port -> {"max": (clk, ps), "min": ...}
    odly = {p: {} for p in ctx.allp}
    refs = []
    for cmd in _split_cmds(text):
        try:
            w = _words(cmd)
            c = w[0]
            if c not in ALLOWED:
                err.append(f"forbidden / unknown SDC command (fail-closed): {cmd}")
                continue
            if c == "set":
                if len(w) != 3:
                    raise SdcLintError(f"set: {cmd}")
                ctx.vars[w[1]] = _eval_obj(ctx, w[2])
                continue
            if c == "create_clock":
                opts, obj = {}, None
                i = 1
                while i < len(w):
                    if w[i] in ("-name", "-period", "-waveform"):
                        opts[w[i]] = w[i + 1]
                        i += 2
                    elif w[i] == "-add":
                        opts["-add"] = 1
                        i += 1
                    else:
                        obj = w[i]
                        i += 1
                nm = opts.get("-name")
                if not nm or "-period" not in opts:
                    raise SdcLintError(f"create_clock without -name/-period: {cmd}")
                if "-waveform" in opts:
                    err.append(f"relaxation: create_clock {nm} -waveform (only the default 50% waveform is allowed)")
                per = _num(opts["-period"], "period") * u
                if abs(per - period_ps) > EPS:
                    err.append(f"units/relaxation: clock {nm} period {opts['-period']} x {u:g} ps = {per:g} ps, "
                               f"plan period {period_ps:g} ps")
                if nm in ctx.clocks:
                    err.append(f"clocks: {nm} created twice")
                src = []
                if obj is not None:
                    k, src = _eval_obj(ctx, obj)
                    if k != "ports":
                        raise SdcLintError(f"create_clock source is not ports: {cmd}")
                ctx.clocks[nm] = src
                for p in src:
                    if p not in ctx.clock_ports:
                        err.append(f"clocks: port {p} is a source of clock {nm} but not a clock tap port")
                    if p in clk_src:
                        err.append(f"clocks: port {p} is the source of two clocks")
                    clk_src[p] = nm
                continue
            if c == "set_clock_latency":
                if "-source" not in w:
                    err.append(f"clocks: network latency override (only -source on the virtual clock): {cmd}")
                    continue
                v = [x for i, x in enumerate(w[1:], 1) if not _isopt(x) and not x.startswith("[")
                     and w[i - 1] != "-clock"]
                k, cl = _eval_obj(ctx, w[-1])
                if len(v) != 1:
                    raise SdcLintError(f"set_clock_latency: {cmd}")
                if k == "ports":         # CP2 early core tap: -source -clock clk <-early> [get_ports tap]
                    for x in cl:
                        port_lat[x] = _num(v[0], "latency") * u
                    continue
                for x in cl:
                    latency[x] = _num(v[0], "latency") * u
                continue
            if c == "set_clock_uncertainty":
                kind = "setup" if "-setup" in w else "hold" if "-hold" in w else "both"
                fr = to = None
                vals, objs = [], []
                i = 1
                while i < len(w):
                    if w[i] in ("-from", "-to", "-rise_from", "-fall_from", "-rise_to", "-fall_to"):
                        if w[i] not in ("-from", "-to"):
                            raise SdcLintError(f"edge-specific uncertainty unsupported: {cmd}")
                        k, cl = _eval_obj(ctx, w[i + 1])
                        if w[i] == "-from":
                            fr = cl
                        else:
                            to = cl
                        i += 2
                    elif w[i] in ("-setup", "-hold"):
                        i += 1
                    elif w[i].startswith("["):
                        objs.append(w[i])
                        i += 1
                    else:
                        vals.append(w[i])
                        i += 1
                if len(vals) != 1:
                    raise SdcLintError(f"set_clock_uncertainty: {cmd}")
                val = _num(vals[0], "uncertainty") * u
                kinds = ["setup", "hold"] if kind == "both" else [kind]
                if fr is None and to is None:
                    k, cl = _eval_obj(ctx, objs[0]) if objs else ("clocks", list(ctx.clocks))
                    for x in cl:
                        for kk in kinds:
                            unc[(kk, x, None)] = val
                elif fr is not None and to is not None and not objs:
                    for a in fr:
                        for b in to:
                            for kk in kinds:
                                unc[(kk, a, b)] = val
                else:
                    raise SdcLintError(f"set_clock_uncertainty needs both -from and -to: {cmd}")
                continue
            if c in ("set_input_delay", "set_output_delay"):
                mm = [m for m in ("max", "min") if f"-{m}" in w] or ["max", "min"]
                if "-add_delay" in w or "-clock_fall" in w or "-network_latency_included" in w \
                        or "-source_latency_included" in w or "-reference_pin" in w:
                    raise SdcLintError(f"unsupported delay option: {cmd}")
                if "-clock" not in w:
                    err.append(f"ports: {c} without -clock: {cmd}")
                    continue
                ck = w[w.index("-clock") + 1]
                refs.append(ck)
                rest = [x for i, x in enumerate(w[1:], 1) if (not _isopt(x)) and w[i - 1] != "-clock"]
                if len(rest) != 2:
                    raise SdcLintError(f"{c}: {cmd}")
                val = _num(rest[0], "delay") * u
                k, ps = _eval_obj(ctx, rest[1])
                tab = idly if c == "set_input_delay" else odly
                for p in ps:
                    for m in mm:
                        tab[p][m] = (ck, val)
                continue
            # set_load / set_driving_cell: evaluate the object (it must resolve), nothing to check
            _eval_obj(ctx, w[-1])
        except (SdcLintError, IndexError) as e:
            err.append(f"parse (fail-closed): {e} [{cmd}]")
    # ---- checks
    for ck in refs:
        if ck not in ctx.clocks:
            err.append(f"clocks: -clock {ck} is not defined")
    for p in ctx.clock_ports:
        if p not in clk_src:
            err.append(f"clocks: clock tap port {p} has no create_clock")
        if idly[p]:
            err.append(f"ports: input delay on clock port {p}")
    virt = [n for n, s in ctx.clocks.items() if not s]
    real = [n for n, s in ctx.clocks.items() if s]
    if len(virt) != 1 or not real:
        err.append(f"clocks: need real tap clock(s) and exactly one virtual IO clock, got real {real} virtual {virt}")
    for n in virt:
        if n not in latency or abs(latency[n] - insertion_ps) > EPS:
            err.append(f"clocks: virtual clock {n} source latency {latency.get(n)} ps, plan insertion {insertion_ps:g} ps")
    want = port_latency_ps or {}
    for p_, v in port_lat.items():
        if p_ not in want or abs(want[p_] - v) > EPS:
            err.append(f"clocks: source latency {v:g} ps on port {p_}, plan early core tap {want.get(p_)}")
    for p_ in want:
        if p_ not in port_lat:
            err.append(f"clocks: plan early core tap {p_} has no source latency")
    for n in latency:
        if n not in virt:
            err.append(f"clocks: source latency on real clock {n} (only the virtual IO clock carries the budget)")
    for p in ctx.inputs:
        for m in ("max", "min"):
            if m not in idly[p]:
                err.append(f"ports: input {p} has no {m} input delay")
        if "min" in idly[p] and idly[p]["min"][1] > -insertion_tol_ps + EPS:
            err.append(f"hold: input {p} min input delay {idly[p]['min'][1]:g} ps > -{insertion_tol_ps:g} ps "
                       "(seam-hold padding relaxed)")
    for p in ctx.outputs:
        for m in ("max", "min"):
            if m not in odly[p]:
                err.append(f"ports: output {p} has no {m} output delay")
        if "min" in odly[p] and odly[p]["min"][1] > EPS:
            err.append(f"hold: output {p} min output delay {odly[p]['min'][1]:g} ps > 0 (sender hold check waived)")
    for p, fl in (io_floor_ps or {}).items():
        tab = idly if p in ctx.inputs else odly
        if "max" in tab.get(p, {}) and tab[p]["max"][1] < fl - EPS:
            err.append(f"relaxation: {p} max delay {tab[p]['max'][1]:g} ps below its IO budget {fl:g} ps")
    full = {"setup": unc_setup_ps, "hold": unc_hold_ps}
    for kk, fv in full.items():
        for n in ctx.clocks:
            v = unc.get((kk, n, None))
            if v is None:
                err.append(f"uncertainty: no {kk} uncertainty on clock {n}" + (" (hold off)" if kk == "hold" else ""))
            elif abs(v - fv) > EPS:
                err.append(f"uncertainty: {kk} uncertainty on {n} = {v:g} ps, AGENTS.md policy {fv:g} ps")
        pairs = {(a, b): v for (k2, a, b), v in unc.items() if k2 == kk and b is not None}
        for (a, b), v in pairs.items():
            seam = (a in virt) != (b in virt)
            if not seam:
                if abs(v - fv) > EPS:
                    err.append(f"uncertainty: {kk} {a}->{b} = {v:g} ps on a non-seam clock pair (policy {fv:g})")
                continue
            if v < -EPS:
                err.append(f"uncertainty: negative {kk} {a}->{b}")
            back = pairs.get((b, a))
            if back is None:
                err.append(f"uncertainty: {kk} seam split {a}->{b} = {v:g} ps without its other half {b}->{a}")
            elif abs(v + back - fv) > EPS:
                err.append(f"uncertainty: {kk} seam {a}<->{b} halves {v:g} + {back:g} ps != {fv:g} ps "
                           "(counted once per seam)")
    return err


def kit_context(P, tn):
    """the lint inputs for partition type tn of plan P (port names exactly as gen_rtl declares them)."""
    import gen_phys
    import gen_rtl
    t = P.types[tn]
    cks = [n for n, _, _ in gen_phys.clock_pins(P, tn) + gen_phys.core_tap_pins(P, tn)]
    plat = {n: -float(early) for n, _i, _p, early, _s in gen_phys.core_tap_rows(P, tn)}
    ins, outs, floor = ["arst_n"], [], {}
    per = float(P.die["period_ps"])
    for b in t.get("buses", []):
        n = gen_rtl.sv_id(b["name"])
        (ins if b["dir"] == "in" else outs).append(n)
        floor[n] = gen_phys.IO_BUDGET * per
    for s in t.get("ft_slots", []):
        ni, no = gen_rtl.sv_id(s["name"] + "_i"), gen_rtl.sv_id(s["name"] + "_o")
        ins.append(ni)
        outs.append(no)
        floor[ni] = (1 - gen_phys.ft_hop_in_share(P)) * per
        floor[no] = gen_phys.ft_hop_in_share(P) * per
    floor["arst_n"] = gen_phys.IO_BUDGET * per
    return dict(period_ps=per, insertion_ps=float(P.clock["insertion_ps"]),
                insertion_tol_ps=float(P.clock["insertion_tol_ps"]), clock_ports=cks, inputs=ins, outputs=outs,
                unc_setup_ps=POLICY_SETUP_PS, unc_hold_ps=POLICY_HOLD_PS,
                time_unit_ps=gen_phys.LIB_TIME_UNIT_PS, io_floor_ps=floor, port_latency_ps=plat)


def lint_kit_files(kitdir, liberties=()):
    """lint KITDIR/constraint.sdc against KITDIR/sdc_lint.json (written by gen_phys with the kit) and, if given,
    the liberty files' time_unit.  -> [errors]"""
    kd = Path(kitdir)
    ctx = json.loads((kd / "sdc_lint.json").read_text())
    err = []
    lu = None
    for lib in liberties:
        v = liberty_time_unit_ps(lib)
        if lu is not None and abs(v - lu) > EPS:
            err.append(f"units: liberty files disagree on time_unit ({lu:g} vs {v:g} ps: {lib})")
        lu = v if lu is None else lu
    if liberties and lu is None:
        err.append("units: no liberty time_unit found")
    return err + lint((kd / "constraint.sdc").read_text(), liberty_unit_ps=lu, **ctx)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kitdir")
    ap.add_argument("--liberty", nargs="*", default=[])
    a = ap.parse_args(argv)
    libs = [x for x in a.liberty if x]
    err = lint_kit_files(a.kitdir, libs)
    for e in err:
        print(f"SDC_LINT ERROR {e}")
    print(f"SDC_LINT {'FAIL' if err else 'PASS'} {a.kitdir} errors {len(err)} liberty {len(libs)}")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
