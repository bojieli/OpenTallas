#!/usr/bin/env python3
"""LINT-AT-SUBMIT (stream lint-at-submit, 2026-10-09): the floorplan margin lint's pin-density and utilisation checks,
estimated from the job's pin plan + outline at intake, before any queue slot or synthesis is spent.

Since 2026-10-08 22:30, 43 closure-loop jobs died at FLOORPLAN_MARGIN (tools/fp_margin_lint.py at ORFS PRE
GLOBAL_PLACE), most on pin density > 12 b/um/layer, each after a full queue + synth cycle.  The pin density of a
die-master route is fixed by data the loop already has at intake: the cfg's outline (FW x FH), its --pin-region plan,
the top module's port widths (ANSI header, parameters resolved; no elaboration, no synthesis) and the IO placer
settings (route_master.sh PIN_H / PIN_V / PIN_MIN_TRACKS, run_abi3_physical OT_PIN_GROUP_MAX / OT_PIN_BALANCE_H/V).

The model is a LOWER BOUND on what fp_margin_lint measures (it never refuses a floorplan the lint could pass):
  * a --pin-region is ONE ordered group (set_io_pin_constraint -group -order): the IO placer packs it on one layer at
    the minimum slot pitch (PIN_MIN_TRACKS x layer pitch), so a group of N pins peaks at min(N, slots in 100 um)/100
    b/um on whichever layer it lands -- adding a layer cannot dilute one group (the be5b56d78 "pin2" jobs re-failed at
    S/M5 20.8 b/um with M5+M7).  OT_PIN_GROUP_MAX chunks bound that term to the chunk size.
  * all pins of a face, however placed, average at least T / (k x max(L, 100 um)) b/um on the best of its k layers.
  * OT_PIN_BALANCE_H/V (with OT_PIN_GROUP_MAX) places pins uniformly over the region, alternating layers per chunk:
    exactly that average.
Verdict: PASS; FIX (fails as configured, passes with an approved automatic fix, tried in order: 1. pin_balance =
OT_PIN_GROUP_MAX=32 + OT_PIN_BALANCE_H 'M4 M6' / _V 'M5 M7'; 2. pin_tracks2_spread = PIN_MIN_TRACKS=2 + PIN_H 'M4 M6' /
PIN_V 'M5 M7' -> the loop puts the settings on the route_master invocations and records them in spec.submit_lint);
REFUSE (no approved fix passes: the message says why each does not); SKIP (recipe without a readable pin plan).
Utilisation: an estimate only where it is available -- a previous FLOORPLAN_MARGIN util measurement of the same
synthesis input (top, parameters, source blobs, synthesis env) -- scaled to the new outline; > util_max refuses.

    submit_lint.py check JOB.json [--repo R]       # print the verdict (exit 0 PASS/FIX/SKIP, 3 REFUSE)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
try:
    from fp_margin_lint import THRESHOLDS as FP_THRESHOLDS  # noqa: E402
except Exception:  # noqa: BLE001  (shipped without tools/: keep the documented values)
    FP_THRESHOLDS = {"pin_density_max": 12.0, "pin_density_target": 6.0, "pin_density_window_um": 100.0,
                     "util_max": 0.60}

# ASAP7 routing pitches (um) of the IO layers (fp_margin_lint calibration; 1/0.048 = 20.8 b/um, 1/0.064 = 15.6 b/um)
PITCH = {"M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064, "M8": 0.08, "M9": 0.08}
SPREAD = {"PIN_H": "M4 M6", "PIN_V": "M5 M7"}           # approved two-layer spread (route_master be5b56d78, DQ1/DQ2)
DEFAULT = {"PIN_H": "M4", "PIN_V": "M5"}
# Approved automatic fixes, in order (coordinator 2026-10-09, layout only, 0 cycles): 1. balanced pins (uniform over the
# region, alternating M4/M6 | M5/M7 per 32-pin chunk: run_abi3_physical OT_PIN_GROUP_MAX / OT_PIN_BALANCE_H/V);
# 2. two-track slot pitch + the two-layer spread (route_master PIN_MIN_TRACKS / PIN_H / PIN_V).
FIXES = (
    {"name": "pin_balance", "env": {"OT_PIN_GROUP_MAX": "32", "OT_PIN_BALANCE_H": "M4 M6", "OT_PIN_BALANCE_V": "M5 M7",
                                    "PIN_H": "M4 M6", "PIN_V": "M5 M7"}},
    {"name": "pin_tracks2_spread", "env": {"PIN_MIN_TRACKS": "2", "PIN_H": "M4 M6", "PIN_V": "M5 M7"}},
)                # ORFS IO_PLACER_H / IO_PLACER_V
EDGES = {"left": "W", "right": "E", "top": "N", "bottom": "S"}
CORE_INSET = 2.16                                       # route_master --core-area 2.16 2.16 FW-2.16 FH-2.16
ENV_KEYS = ("PIN_H", "PIN_V", "PIN_MIN_TRACKS", "OT_PIN_GROUP_MAX", "OT_PIN_BALANCE_H", "OT_PIN_BALANCE_V")
SYNTH_ENV_RE = re.compile(r"\b(OT_ABC_\w+|OT_SYNTH_\w+|OT_MULTI_VT|OT_KEEP_\w+)=('[^']*'|\"[^\"]*\"|[^\s;]+)")
MASTER_RE = re.compile(r"(?:physical/qwen_die_masters/jobs/)?route_master\.sh\s+([A-Za-z0-9_.-]+)")
CFG_DIR = "physical/qwen_die_masters/cfg"
# drive-0212 2026-10-09: an IO-placer setting only acts when the job's SOURCE COMMIT's flow reads it.  OT_PIN_GROUP_MAX /
# OT_PIN_BALANCE_H/V entered tools/run_abi3_physical.py at dde873a8e (2026-10-08 23:39) and route_master.sh never read
# PIN_MIN_TRACKS before main; 12 of the 15 lint-at-submit pin_balance requeues ran on older sources, the env was
# silently ignored and two re-failed at the IDENTICAL density (sys-08ef6a8a8-ls E/M4 20.8 @819, kv624-a732a1d76-ls
# N/M5 20.8 @1).  Each key -> (file at the source commit, marker that file must contain for the key to take effect).
FLOW_SUPPORT = {
    "PIN_H": ("physical/qwen_die_masters/jobs/route_master.sh", "IO_PLACER_H"),
    "PIN_V": ("physical/qwen_die_masters/jobs/route_master.sh", "IO_PLACER_V"),
    "PIN_MIN_TRACKS": ("physical/qwen_die_masters/jobs/route_master.sh", "PIN_MIN_TRACKS"),
    "OT_PIN_GROUP_MAX": ("tools/run_abi3_physical.py", "OT_PIN_GROUP_MAX"),
    "OT_PIN_BALANCE_H": ("tools/run_abi3_physical.py", "OT_PIN_BALANCE_H"),
    "OT_PIN_BALANCE_V": ("tools/run_abi3_physical.py", "OT_PIN_BALANCE_V"),
}


def flow_support(git, commit: str) -> dict:
    """{env key: True when the source commit's flow reads it} (a missing file reads nothing)"""
    cache, out = {}, {}
    for k, (path, marker) in FLOW_SUPPORT.items():
        if path not in cache:
            cache[path] = git.show(commit, path) or ""
        out[k] = marker in cache[path]
    # dde873a8e itself balanced only bounded (lo-hi) regions and raised on a whole-face one; a66978536 relaxed it
    out["balance_whole_face"] = "bounded regions" not in cache.get("tools/run_abi3_physical.py", "")
    return out


# ------------------------------------------------------------------------------------- constant expressions (SV)
class ExprError(ValueError):
    pass


_TOK = re.compile(r"\s*(?:(\d+)?'[sS]?([bodhBODH])([0-9a-fA-FxXzZ_?]+)|(\d[\d_]*)|(\$?[A-Za-z_][A-Za-z0-9_$]*)|"
                  r"(\*\*|<<<|>>>|<<|>>|<=|>=|==|!=|&&|\|\||[-+*/%<>()?:,!~&|^]))")
_BIN = {"||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "<": 7, ">": 7, "<=": 7, ">=": 7,
        "<<": 8, ">>": 8, "<<<": 8, ">>>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10, "**": 11}


def sv_eval(expr: str, env: dict) -> int:
    """integer value of a Verilog constant expression over parameters env (raises ExprError)"""
    toks, pos, s = [], 0, expr.strip()
    while pos < len(s):
        m = _TOK.match(s, pos)
        if not m or m.end() == pos:
            raise ExprError(f"cannot parse {s[pos:pos + 20]!r}")
        pos = m.end()
        if m.group(3) is not None:
            digits = m.group(3).replace("_", "")
            if re.search(r"[xXzZ?]", digits):
                raise ExprError("x/z literal")
            toks.append(("n", int(digits, {"b": 2, "o": 8, "d": 10, "h": 16}[m.group(2).lower()])))
        elif m.group(4) is not None:
            toks.append(("n", int(m.group(4).replace("_", ""))))
        elif m.group(5) is not None:
            toks.append(("id", m.group(5)))
        elif m.group(6) is not None:
            toks.append(("op", m.group(6)))
    i = 0

    def peek():
        return toks[i] if i < len(toks) else ("end", None)

    def take(op=None):
        nonlocal i
        t = peek()
        if op is not None and t != ("op", op):
            raise ExprError(f"expected {op} in {expr!r}")
        i += 1
        return t

    def unary():
        t = take()
        if t == ("op", "("):
            v = ternary()
            take(")")
            return v
        if t[0] == "op" and t[1] in "-+!~":
            v = unary()
            return {"-": -v, "+": v, "!": int(not v), "~": ~v}[t[1]]
        if t[0] == "n":
            return t[1]
        if t[0] == "id":
            name = t[1]
            if peek() == ("op", "("):
                take("(")
                args = [ternary()]
                while peek() == ("op", ","):
                    take(",")
                    args.append(ternary())
                take(")")
                if name in ("$clog2", "clog2"):
                    return 0 if args[0] <= 1 else (args[0] - 1).bit_length()
                if name in ("$max", "max"):
                    return max(args)
                if name in ("$min", "min"):
                    return min(args)
                raise ExprError(f"function {name}")
            if name not in env:
                raise ExprError(f"unknown identifier {name}")
            return env[name]
        raise ExprError(f"unexpected {t[1]!r} in {expr!r}")

    def binary(prec):
        lhs = unary()
        while True:
            t = peek()
            if t[0] != "op" or t[1] not in _BIN or _BIN[t[1]] < prec:
                return lhs
            op = take()[1]
            rhs = binary(_BIN[op] + (0 if op == "**" else 1))
            if op in ("/", "%") and rhs == 0:
                raise ExprError("division by zero")
            lhs = {"||": lambda a, b: int(bool(a) or bool(b)), "&&": lambda a, b: int(bool(a) and bool(b)),
                   "|": lambda a, b: a | b, "^": lambda a, b: a ^ b, "&": lambda a, b: a & b,
                   "==": lambda a, b: int(a == b), "!=": lambda a, b: int(a != b), "<": lambda a, b: int(a < b),
                   ">": lambda a, b: int(a > b), "<=": lambda a, b: int(a <= b), ">=": lambda a, b: int(a >= b),
                   "<<": lambda a, b: a << b, ">>": lambda a, b: a >> b, "<<<": lambda a, b: a << b,
                   ">>>": lambda a, b: a >> b, "+": lambda a, b: a + b, "-": lambda a, b: a - b,
                   "*": lambda a, b: a * b, "/": lambda a, b: int(a / b), "%": lambda a, b: int(math.fmod(a, b)),
                   "**": lambda a, b: a ** b}[op](lhs, rhs)

    def ternary():
        c = binary(1)
        if peek() == ("op", "?"):
            take("?")
            a = ternary()
            take(":")
            b = ternary()
            return a if c else b
        return c

    v = ternary()
    if i != len(toks):
        raise ExprError(f"trailing tokens in {expr!r}")
    return v


# --------------------------------------------------------------------------------------------- port extraction
def _strip_comments(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", " ", t)


def _balanced(t: str, start: int) -> int:
    """index just past the ')' closing the '(' at t[start]"""
    depth = 0
    for k in range(start, len(t)):
        if t[k] == "(":
            depth += 1
        elif t[k] == ")":
            depth -= 1
            if depth == 0:
                return k + 1
    raise ExprError("unbalanced parentheses")


def _split_top(t: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in t:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


_DIM = re.compile(r"\[([^\[\]]*):([^\[\]]*)\]")
_TYPEWORDS = {"wire", "reg", "logic", "signed", "unsigned", "var", "bit", "tri", "integer", "int", "type"}


def top_ports(text: str, top: str, overrides: dict | None = None) -> list[tuple[str, int, int]]:
    """[(name, width, lsb)] of module top's ANSI port list in text, parameters from the header defaults + overrides
    (raises ExprError for anything this parser does not model: non-ANSI headers, interfaces, typedef'd ports)"""
    t = _strip_comments(text)
    m = re.search(r"\bmodule\s+(?:automatic\s+)?" + re.escape(top) + r"\b", t)
    if not m:
        raise ExprError(f"module {top} not found")
    k = m.end()
    env: dict = {}
    while t[k].isspace():
        k += 1
    if t[k] == "#":
        p0 = t.index("(", k)
        p1 = _balanced(t, p0)
        for ent in _split_top(t[p0 + 1:p1 - 1]):
            pm = re.match(r"\s*(?:parameter|localparam)?\s*(?:integer|int|logic|bit|signed|unsigned|"
                          r"\[[^\]]*\]|\s)*\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*$", ent, re.S)
            if not pm:
                raise ExprError(f"parameter entry {ent.strip()[:60]!r}")
            name = pm.group(1)
            if overrides and name in overrides:
                env[name] = sv_eval(str(overrides[name]), env)
            else:
                env[name] = sv_eval(pm.group(2), env)
        k = p1
        while t[k].isspace():
            k += 1
    if t[k] != "(":
        if t[k] == ";":
            return []
        raise ExprError("no ANSI port list")
    p1 = _balanced(t, k)
    ports, last = [], None
    for ent in _split_top(t[k + 1:p1 - 1]):
        e = " ".join(ent.split())
        if not e:
            continue
        dm = re.match(r"(input|output|inout)\b\s*(.*)$", e)
        if dm:
            rest = dm.group(2)
            words = re.sub(r"\[[^\[\]]*\]", " ", rest).split()
            if not words:
                raise ExprError(f"port entry {e!r}")
            name = words[-1]
            if any(w not in _TYPEWORDS for w in words[:-1]):
                raise ExprError(f"port type {' '.join(words[:-1])!r} not modelled")
            pre = rest[:rest.rfind(name)]
            dims = [(sv_eval(a, env), sv_eval(b, env)) for a, b in _DIM.findall(pre)]
            if any(w in ("integer", "int") for w in words[:-1]) and not dims:
                dims = [(31, 0)]
            last = dims
        elif last is not None and re.fullmatch(r"[A-Za-z_]\w*", e):
            name, dims = e, last
        else:
            raise ExprError(f"port entry {e!r} not modelled")
        if re.search(r"\]\s*$", e[e.rfind(name):]):
            raise ExprError(f"unpacked port {name} not modelled")
        width = 1
        for a, b in dims:
            width *= abs(a - b) + 1
        lsb = min(dims[-1]) if len(dims) == 1 else 0
        ports.append((name, width, lsb if dims else -1))
    return ports


def bit_names(ports) -> list[str]:
    out = []
    for name, width, lsb in ports:
        if lsb < 0:
            out.append(name)
        else:
            out += [f"{name}[{lsb + i}]" for i in range(width)]
    return out


# --------------------------------------------------------------------------------------------------- cfg + cmd
def read_cfg(text: str) -> dict:
    """source a route_master cfg (bash) in a clean shell; the variables route_master.sh reads"""
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
        f.write(text)
        p = f.name
    try:
        script = ('set +u; source "$1" >/dev/null 2>&1; '
                  'for v in TOP SRCS FW FH PIN_H PIN_V PIN_MIN_TRACKS; do printf "%s=%s\\0" "$v" "${!v-__unset__}"; done; '
                  'printf "PARAMS\\0"; for x in "${PARAMS[@]}"; do printf "%s\\0" "$x"; done; printf "\\1\\0"; '
                  'printf "PINS\\0"; for x in "${PINS[@]}"; do printf "%s\\0" "$x"; done; printf "\\1\\0"; '
                  'printf "MACROS\\0"; for x in "${MACROS[@]}"; do printf "%s\\0" "$x"; done; printf "\\1\\0"')
        r = subprocess.run(["bash", "--noprofile", "--norc", "-c", script, "cfg", p], capture_output=True, text=True,
                           timeout=30, env={"PATH": "/usr/bin:/bin"}, cwd=tempfile.gettempdir())
    finally:
        os.unlink(p)
    parts = r.stdout.split("\0")
    cfg, arr = {}, None
    for x in parts:
        if arr is not None:
            if x == "\1":
                arr = None
            else:
                cfg[arr].append(x)
        elif x in ("PARAMS", "PINS", "MACROS"):
            arr = x
            cfg[x] = []
        elif "=" in x:
            k, v = x.split("=", 1)
            if v != "__unset__":
                cfg[k] = v
    return cfg


def cmd_env(cmd: str) -> dict:
    """PIN_* / OT_PIN_* settings a stage command gives route_master.sh (inline VAR=... or export VAR=...)"""
    out = {}
    head = cmd[:MASTER_RE.search(cmd).start()] if MASTER_RE.search(cmd) else cmd
    try:
        words = shlex.split(head.replace(";", " ; ").replace("&&", " && "), posix=True)
    except ValueError:
        words = head.split()
    for w in words:
        if "=" in w:
            k, v = w.split("=", 1)
            if k in ENV_KEYS:
                out[k] = v
    return out


def master_cfg_name(cmd: str):
    m = MASTER_RE.search(cmd or "")
    return m.group(1) if m else None


def parse_params(params: list[str]) -> dict:
    out, k = {}, 0
    while k < len(params):
        a = params[k]
        if a == "--param" and k + 1 < len(params):
            n, _, v = params[k + 1].partition("=")
            out[n] = v
            k += 2
            continue
        if a.startswith("--param="):
            n, _, v = a[len("--param="):].partition("=")
            out[n] = v
        k += 1
    return out


def parse_regions(pins: list[str]) -> list[dict]:
    regs, k = [], 0
    while k < len(pins):
        if pins[k] == "--pin-region" and k + 1 < len(pins):
            regex, _, spec = pins[k + 1].rpartition("=")
            m = re.fullmatch(r"(left|right|top|bottom)(?::([0-9.]+)-([0-9.]+))?", spec)
            if not m:
                raise ExprError(f"pin region {pins[k + 1]!r}")
            r = {"regex": regex, "edge": m.group(1)}
            if m.group(2) and float(m.group(3)) <= float(m.group(2)):
                raise ExprError(f"pin region {pins[k + 1]!r}: HIGH must exceed LOW")
            if m.group(2):
                r["range_um"] = (float(m.group(2)), float(m.group(3)))
            regs.append(r)
            k += 2
        else:
            k += 1
    return regs


# ------------------------------------------------------------------------------------------------ density model
def density(plan: dict, layers: dict, tracks: float, group_max: int = 0, balance: bool = False,
            window: float = 100.0) -> dict:
    """{edge: {"est": b/um lower bound on the best layer, "layers": [...], "why": text}} for plan
    {"die": (FW, FH), "regions": [{"edge", "n", "len", "regex"}], "free": n}"""
    fw, fh = plan["die"]
    length = {"left": fh, "right": fh, "top": fw, "bottom": fw}
    perim = 2 * (fw + fh)
    out = {}
    for edge in ("left", "right", "top", "bottom"):
        ls = layers["PIN_H" if edge in ("left", "right") else "PIN_V"].split()
        regs = [r for r in plan["regions"] if r["edge"] == edge]
        total = sum(r["n"] for r in regs) + plan.get("free", 0) * length[edge] / perim
        if not total:
            continue
        avg = total / (len(ls) * max(length[edge], window))
        grp, gwhy, nofit = 0.0, "", []
        for r in regs:
            span = (r["range_um"][1] - r["range_um"][0]) if r.get("range_um") else length[edge]
            if r["n"] and not balance and \
                    all(r["n"] * tracks * PITCH.get(lay, 0.048) > span for lay in ls) and not group_max:
                nofit.append(f"{r['regex']} {r['n']} pins need {r['n'] * tracks * PITCH.get(ls[-1], 0.048):.0f} um "
                             f"> {span:.0f} um")
        if not balance:
            for r in regs:
                chunk = min(r["n"], group_max) if group_max else r["n"]
                # a group packs one layer at the slot pitch: the best layer is the coarsest (fewest slots / window)
                best = min(min(chunk, math.floor(window / (tracks * PITCH.get(lay, 0.048))) + 1) / window for lay in ls)
                if best > grp:
                    grp, gwhy = best, f"group {r['regex']} {r['n']} pins" + (f" (chunks {group_max})" if group_max else "")
        if balance:
            # run_abi3_physical OT_PIN_BALANCE: each region's pins uniformly over its span, layer alternating per chunk.
            # drive-0212: the densities add only where regions OVERLAP along the edge; summing every region of a face
            # refused qfd_hub_ps-dde873a8e-tc-bal32 at 26.3 b/um (six disjoint right:lo-hi ranges), measured 8.0, CLOSED.
            # The estimate is the densest 100 um window over the piecewise-uniform pin line.
            segs = []
            for r in regs:
                if not r["n"]:
                    continue
                lo, hi = r["range_um"] if r.get("range_um") else (0.0, length[edge])
                span = hi - lo
                if span <= 0 or span / r["n"] < max(PITCH.get(lay, 0.048) for lay in ls):
                    nofit.append(f"balanced {r['regex']} {r['n']} pins at {max(span, 0) / r['n']:.3f} um spacing "
                                 f"< the layer pitch")
                    continue
                segs.append((lo, hi, r["n"] / span))
            starts = {x for lo, hi, _ in segs for x in (lo, hi - window)}
            peak = max((sum(rate * max(0.0, min(hi, a + window) - max(lo, a)) for lo, hi, rate in segs)
                        for a in starts), default=0.0)
            avg = max(avg, peak / (len(ls) * window))
        est = max(grp, avg)
        why = gwhy if grp >= avg else f"{total:.0f} pins over {length[edge]:.0f} um x {len(ls)} layer(s)"
        out[edge] = {"est": round(est, 2), "layers": ls, "why": why, "pins": round(total), "nofit": nofit}
    return out


PPL_SECTION = 200  # OpenROAD place_pins slots per section (PPL-0005)


def _fails(d: dict, limit: float) -> list[str]:
    return [f"{EDGES[e]}/{'+'.join(v['layers'])} {v['est']} b/um ({v['why']})" for e, v in d.items() if v["est"] > limit]


# ------------------------------------------------------------------------------------------------------- driver
class Git:
    def __init__(self, repo):
        self.repo = str(repo)

    def show(self, commit, path):
        r = subprocess.run(["git", "-C", self.repo, "show", f"{commit}:{path}"], capture_output=True, text=True,
                           timeout=60)
        return r.stdout if r.returncode == 0 else None

    def blob(self, commit, path):
        r = subprocess.run(["git", "-C", self.repo, "rev-parse", f"{commit}:{path}"], capture_output=True, text=True,
                           timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None


def thresholds(spec: dict) -> tuple[dict, bool]:
    th = dict(FP_THRESHOLDS)
    cfg = spec.get("fp_lint", True)
    warn_only = False
    if isinstance(cfg, dict):
        for k, v in (cfg.get("set") or {}).items():
            try:
                th[k] = float(v)
            except (TypeError, ValueError):
                pass
        warn_only = bool(cfg.get("warn_only"))
    return th, warn_only


def stage_cmds(spec: dict) -> dict:
    st = spec.get("stages") or {}
    return {k: (st.get(k) or {}).get("cmd") for k in ("calibrate", "route", "signoff") if (st.get(k) or {}).get("cmd")}


def master_plan(spec: dict, git: Git) -> dict:
    """everything the estimate needs, from the job's source commit (raises ExprError when not modelled)"""
    cmd = (spec.get("stages") or {}).get("route", {}).get("cmd", "")
    name = master_cfg_name(cmd)
    if not name:
        raise LookupError("not a route_master.sh job")
    commit = spec["source"]["commit"]
    text = git.show(commit, f"{CFG_DIR}/{name}.env")
    if text is None:
        raise LookupError(f"{CFG_DIR}/{name}.env not readable at {commit[:12]}")
    cfg = read_cfg(text)
    if not cfg.get("TOP") or not cfg.get("FW") or not cfg.get("FH"):
        raise ExprError(f"cfg {name}: TOP / FW / FH not set")
    env = cmd_env(cmd)
    params = parse_params(cfg.get("PARAMS", []))
    srcs = cfg.get("SRCS", "").split()
    ports = None
    blobs = []
    for s in srcs:
        blobs.append(f"{s}:{git.blob(commit, s)}")
        if ports is None and s.endswith((".sv", ".v")):
            body = git.show(commit, s)
            if body and re.search(r"\bmodule\s+" + re.escape(cfg["TOP"]) + r"\b", body):
                ports = top_ports(body, cfg["TOP"], params)
    if ports is None:
        raise ExprError(f"top {cfg['TOP']} not found in SRCS")
    regs = parse_regions(cfg.get("PINS", []))
    bits = bit_names(ports)
    for r in regs:
        rx = re.compile(r["regex"])
        r["n"] = sum(1 for b in bits if rx.search(b))
    matched = sum(1 for b in bits if any(re.search(r["regex"], b) for r in regs))
    # a setting the source's flow does not read is ignored by the flow, so the estimate ignores it too
    flow = flow_support(git, commit)
    cfg = {k: v for k, v in cfg.items() if k not in flow or flow[k]}
    env = {k: v for k, v in env.items() if k not in flow or flow[k]}
    # route_master sources the cfg AFTER the environment: a variable the cfg sets wins over the command's
    layers = {k: cfg.get(k) or env.get(k) or DEFAULT[k] for k in ("PIN_H", "PIN_V")}
    synth_env = sorted(f"{a}={b}" for a, b in SYNTH_ENV_RE.findall(cmd))
    key = hashlib.sha256(json.dumps([cfg["TOP"], cfg.get("PARAMS", []), blobs, cfg.get("MACROS", []), synth_env])
                         .encode()).hexdigest()[:20]
    fw, fh = float(cfg["FW"]), float(cfg["FH"])
    return {"cfg": name, "die": (fw, fh), "regions": [{k: r[k] for k in ("regex", "edge", "n", "range_um") if k in r} for r in regs],
            "free": len(bits) - matched, "pins": len(bits), "layers": layers,
            "cfg_sets": [k for k in ("PIN_H", "PIN_V", "PIN_MIN_TRACKS") if cfg.get(k)],
            "tracks": float(cfg.get("PIN_MIN_TRACKS") or env.get("PIN_MIN_TRACKS") or 1),
            "group_max": int(env.get("OT_PIN_GROUP_MAX") or 0),
            "balance": bool(env.get("OT_PIN_BALANCE_H") and env.get("OT_PIN_BALANCE_V") and env.get("OT_PIN_GROUP_MAX")),
            "flow": flow, "commit": commit,
            "synth_key": key, "core_um2": round((fw - 2 * CORE_INSET) * (fh - 2 * CORE_INSET), 1)}


def _choose_fix(plan, limit, window, res, force=False):
    """the first approved automatic pin fix (FIXES order) whose estimate passes: ("FIX", message, "") with
    res["fix"] / res["est_fix"] set, or ("NONE", "", why none applies)"""
    why = []
    cur_bal = plan["balance"]
    for fx in FIXES:
        env = fx["env"]
        unread = [k for k in env if not plan.get("flow", {}).get(k, True)]
        if unread:
            why.append(f"{fx['name']}: the source {str(plan.get('commit'))[:9]} flow does not read "
                       f"{','.join(unread)} (OT_PIN_* since dde873a8e; rebase the source)")
            continue
        if fx["name"] == "pin_balance":
            if cur_bal:
                why.append("pin_balance already set")
                continue
            if not plan["regions"]:
                why.append("pin_balance: no --pin-region to balance")
                continue
            if not plan.get("flow", {}).get("balance_whole_face", True) and \
                    any("range_um" not in r for r in plan["regions"]):
                why.append(f"pin_balance: the source {str(plan.get('commit'))[:9]} flow balances only lo-hi regions "
                           f"(whole-face regions raise; relaxed at a66978536)")
                continue
            d = density(plan, {"PIN_H": env["OT_PIN_BALANCE_H"], "PIN_V": env["OT_PIN_BALANCE_V"]}, plan["tracks"],
                        int(env["OT_PIN_GROUP_MAX"]), True, window)
        else:
            same = {"PIN_H": plan["layers"]["PIN_H"] == env["PIN_H"], "PIN_V": plan["layers"]["PIN_V"] == env["PIN_V"],
                    "PIN_MIN_TRACKS": plan["tracks"] >= float(env["PIN_MIN_TRACKS"])}
            blocked = [k for k in same if k in plan["cfg_sets"] and not same[k]]
            if blocked:
                why.append(f"{fx['name']}: the cfg sets {','.join(blocked)}")
                continue
            if plan["tracks"] >= float(env["PIN_MIN_TRACKS"]) and plan["layers"] == {k: env[k] for k in SPREAD}:
                why.append(f"{fx['name']} already set")
                continue
            d = density(plan, {k: env[k] for k in SPREAD}, float(env["PIN_MIN_TRACKS"]), plan["group_max"],
                        cur_bal, window)
        bad = _fails(d, limit)
        nofit = [x for v in d.values() for x in v["nofit"]]
        if bad or nofit:
            why.append(f"{fx['name']}: {'; '.join(bad + nofit)[:300]}")
            continue
        res["fix"], res["fix_env"] = fx["name"], dict(env)
        res["est_fix"] = {EDGES[e]: v["est"] for e, v in d.items()}
        return "FIX", (f"approved automatic fix {fx['name']} "
                       f"({' '.join(f'{k}={v!r}' for k, v in env.items())}) -> "
                       f"{max(v['est'] for v in d.values())} b/um"), ""
    return "NONE", "", " | ".join(why)


def check(spec: dict, git: Git, util_db: dict | None = None, force: bool = False) -> dict:
    """pin-density / utilisation estimate (_pin_check) + the RTL registered-boundary check (rtl_boundary.py, struct-close
    2026-10-09): boundary findings WARN (message + res["rtl_boundary"]) and REFUSE only when spec.registered_io is true"""
    res = _pin_check(spec, git, util_db, force)
    if spec.get("fp_lint", True) is False or spec.get("submit_lint", True) is False:
        return res
    try:
        sys.path.insert(0, str(HERE)); import rtl_boundary  # noqa: E702
        rb = rtl_boundary.check(spec, git.show)
    except Exception as ex:  # noqa: BLE001  (the boundary check never blocks intake on its own failure)
        rb = {"verdict": "SKIP", "message": f"rtl_boundary skipped: {type(ex).__name__}: {str(ex)[:160]}"}
    if rb.get("verdict") == "SKIP":
        return res
    res["rtl_boundary"] = {k: rb.get(k) for k in ("verdict", "message", "in_to_out_bits", "in_to_reg_max",
                                                  "reg_to_out_max", "levels", "strict")}
    if rb["verdict"] == "REFUSE":
        res["verdict"] = "REFUSE"
        res["message"] = (res.get("message", "") + " || " if res.get("verdict") != "SKIP" and res.get("message") else "") \
            + rb["message"] + " (spec registered_io: true): register the boundary (pin flops / registered outputs) or drop the claim"
    elif rb["verdict"] == "WARN":
        if res.get("verdict") == "SKIP":
            res["verdict"], res["message"] = "PASS", "pin estimate n/a"
        res["message"] = res.get("message", "") + " || WARN " + rb["message"]
    elif res.get("verdict") == "SKIP":
        res["verdict"], res["message"] = "PASS", "pin estimate n/a || " + rb["message"]
    return res


def _pin_check(spec: dict, git: Git, util_db: dict | None = None, force: bool = False) -> dict:
    """{"verdict": PASS|FIX|REFUSE|SKIP, "message", "est", "fix", "fix_env", "est_fix", "util_est", ...}
    force: apply the first fix that passes even when the estimate passes as configured (a MEASURED failure)"""
    if spec.get("fp_lint", True) is False or spec.get("submit_lint", True) is False:
        return {"verdict": "SKIP", "message": "fp_lint / submit_lint opted out"}
    try:
        plan = master_plan(spec, git)
    except (LookupError, ExprError, KeyError, ValueError, subprocess.SubprocessError, re.error) as ex:
        return {"verdict": "SKIP", "message": f"no pin plan estimate: {str(ex)[:200]}"}
    th, warn_only = thresholds(spec)
    limit, window = th["pin_density_max"], th["pin_density_window_um"]
    res = {"cfg": plan["cfg"], "pins": plan["pins"], "die_um": list(plan["die"]), "layers": plan["layers"],
           "tracks": plan["tracks"], "limit": limit}
    est = density(plan, plan["layers"], plan["tracks"], plan["group_max"], plan["balance"], window)
    res["est"] = {EDGES[e]: v["est"] for e, v in est.items()}
    msgs, verdict = [], "PASS"
    fails = _fails(est, limit)
    # drive-0849 (2026-10-09): an ordered --pin-region group larger than an IO-placer section (PPL "Slots per section 200")
    # is placed in FALLBACK mode and then fails PPL-0107 "Invalid pin placement" at 3_2_place_iop although its density
    # passes (hgi_coll_row_formatter c130/c180 1024/512 pins, hgi_ehash_ds a/b 768/768/256, qfd_coll_xfifo a/b, 4 routes x 2
    # crashes on 10-09).  Such a plan takes the approved pin_balance fix (32-pin chunks) at submit, as a measured failure.
    gmax = int(th.get("ppl_group_max", PPL_SECTION))  # fp_lint {"set": {"ppl_group_max": 0}} switches the rule off
    big = [r for r in plan["regions"] if r.get("n", 0) > gmax] if gmax and not (plan["group_max"] or plan["balance"]) else []
    if big and not fails and not force:
        force = True
        names = ", ".join(f"{r['regex']} {r['n']}" for r in big[:3])
        msgs.append(f"ordered pin group(s) > {gmax} pins ({names}) fall back in the IO placer (PPL-0107)")
    if fails or force:
        verdict, fix_msg, why_not = _choose_fix(plan, limit, window, res, force=force and not fails)
        if verdict == "FIX":
            msgs.append((f"pin density > {limit} b/um/layer as configured ({'; '.join(fails)}); " if fails else
                         "measured pin-density failure (the estimate is a lower bound); ") + fix_msg)
        elif fails:
            verdict = "REFUSE"
            msgs.append(f"pin density > {limit} b/um/layer at submit ({'; '.join(fails)}); no approved automatic fix "
                        f"passes ({why_not}). A --pin-region is one ordered group packed on ONE layer at the slot "
                        f"pitch, so more layers alone cannot dilute it. Fix: a longer edge / split the pin group")
        else:
            verdict = "PASS"
    # utilisation, where a measurement of the same synthesis input exists
    u = (util_db or {}).get(plan["synth_key"])
    if u and u.get("core_um2") and u.get("lint_core_um2"):
        core_new = u["lint_core_um2"] * plan["core_um2"] / u["core_um2"]
        ue = u["area_um2"] / core_new
        res["util_est"] = {"util": round(ue, 3), "from": u.get("job"), "area_um2": u["area_um2"],
                           "core_um2": round(core_new)}
        if ue > th["util_max"]:
            verdict = "REFUSE"
            msgs.append(f"utilisation {ue:.1%} > {th['util_max']:.0%} at submit: the same synthesis input measured "
                        f"{u['area_um2']:.0f} um2 (job {u.get('job')}) in this outline's {core_new:.0f} um2 core: "
                        f"grow the outline to <= 55-60%")
    if verdict == "REFUSE" and warn_only:
        verdict, msgs = "PASS", ["warn_only: " + m for m in msgs]
    res["verdict"] = verdict
    res["message"] = " || ".join(msgs) if msgs else "pin density within limits (estimate)"
    return res


def apply_fix(spec: dict, res: dict, when: str) -> dict:
    """a copy of spec whose route_master invocations run with res["fix_env"] (inline assignments just before
    `bash ...route_master.sh`, so they win over earlier exports in the command), recorded in spec.submit_lint"""
    out = json.loads(json.dumps(spec))
    env = res["fix_env"]
    assigns = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in env.items())
    for k, cmd in stage_cmds(spec).items():
        if master_cfg_name(cmd):
            new, n = re.subn(r"\bbash(\s+(?:\S*/)?route_master\.sh\b)", lambda m: f"{assigns} bash{m.group(1)}", cmd)
            out["stages"][k]["cmd"] = new if n else f"export {assigns}; " + cmd
    out["submit_lint"] = {"applied": res["fix"], "env": dict(env), "at": when, "est_as_configured": res.get("est"),
                          "est_fix": res.get("est_fix"), "why": res.get("message", "")[:400]}
    return out


UTIL_RE = re.compile(r"utilisation\s+([\d.]+)%\s*>\s*\d+%\s*\(std\s+(\d+)\s*\+\s*macro\s+(\d+)\s*um2\s+in\s+(\d+)\s*um2")


def util_record(spec: dict, reason: str, git: Git, job: str):
    """(synth_key, record) from a FLOORPLAN_MARGIN util reason, or None"""
    m = UTIL_RE.search(reason or "")
    if not m:
        return None
    try:
        plan = master_plan(spec, git)
    except Exception:  # noqa: BLE001
        return None
    return plan["synth_key"], {"area_um2": int(m.group(2)) + int(m.group(3)), "lint_core_um2": int(m.group(4)),
                               "core_um2": plan["core_um2"], "util": float(m.group(1)) / 100, "job": job}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("file")
    c.add_argument("--repo", default=os.environ.get("CL_REPO", "/home/ubuntu/OpenTallas"))
    a = ap.parse_args(argv)
    res = check(json.loads(Path(a.file).read_text()), Git(a.repo))
    print(json.dumps(res, indent=1))
    return 3 if res["verdict"] == "REFUSE" else 0


if __name__ == "__main__":
    sys.exit(main())
