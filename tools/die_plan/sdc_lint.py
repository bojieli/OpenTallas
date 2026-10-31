"""Fail-closed lint of a generated partition-kit SDC (CP1-R10, COORD 10-24: past CP1 failures were tool bugs found late).

    python3 tools/die_plan/sdc_lint.py KITDIR [--liberty LIB ...]          # exit 1 on any error

Checks (every one is an ERROR; gen_phys.write_type_kit raises on them, run_kit.sh re-runs it against the image's
liberty files before synthesis):
  units      the liberty time_unit equals gen_phys.LIB_TIME_UNIT_PS (the 10-23 KV-P3b bug: ns values against a ps
             library = a 0.833-ps clock) and every create_clock period x unit = the plan period.
  clocks     every clock referenced (-clock X, get_clocks X) is created; every clock tap port is a create_clock source;
             only tap ports are clock sources; one virtual IO clock whose source latency = the TT-bound insertion (FF-bound value in sdc_lint.json).
  ports      every non-clock input has a max AND a min input delay, every output a max AND a min output delay
             (set_*_delay with neither -max nor -min sets both); no delay on a clock port.
  hold       hold uncertainty on every clock; min input delay <= -insertion_tol (seam-hold padding, CP1 r9);
             min output delay <= 0 (a positive min output delay waives the sender's hold check).
  uncertainty  the sign-off clock uncertainty policy on every clock (margin_policy(): OWNER 12.24b/c nominal = setup 0 /
             hold 25 ps; legacy A/B switch OT_MARGIN_POLICY=legacy = the old AGENTS.md 60 / 25 ps); inter-clock overrides
             only on the seam pair (vclk -> clk, clk -> vclk), and per kind the two halves add up to exactly the full
             value (once per seam).
  relaxation every period = the plan period, no -waveform; max delays >= the declared IO budgets; and no exception
             command at all (set_false_path, set_multicycle_path, set_max_delay, set_min_delay, set_disable_timing,
             set_clock_groups, set_case_analysis, ... : any command outside the generator's vocabulary is an error).
             Exception (OWNER 10-25 option B): set_false_path -from [get_ports {...}] on declared ID straps
             (lint(straps=...) / sdc_lint.json "straps" / kit straps.json, strap_* inputs) -- required on every declared strap, refused on any other port.
             The owner reset rule also permits exactly the two unique whole-die asynchronous root RESETN pins;
             root_async_reset context is generated from the wavefront plan, never from a signal-name match.
  ft         (COORD 10-26 12:55, 12.2a1) ports in the kit's ft declaration (ft_ports.json, sha256-checked) are
             DIE-TIMED feed-throughs: no input/output delay, load or driving cell on them (all_inputs / all_outputs
             select them in the built core, so the SDC must name core IO explicitly), never a clock source; every
             declared arc must exist in the kit interface model ft_interface.json.  No new exception: set_false_path
             stays banned; an undeclared port is core IO (delays required) or does not resolve.
  landing    (COORD 10-27 RULING S81-KITS-1, landing_contract.py c467e5cea) a type with a plan clock.landing_contract
             may carry exactly these three forms, nothing wider:
             - `set V [remove_from_collection A B]` (B a subset of A, same object kind; V defined before use);
             - `create_generated_clock -name N -master_clock M -source [get_ports S] -divide_by 1 [get_ports P]` on
               each declared forwarded-clock output P (lint(forwarded_clock_outputs=...)), M a real tap clock with
               source port S; no other generated-clock option; P carries no IO delay and N is referenced by no IO
               delay or exception (it times no path inside the partition, so it needs no uncertainty);
             - `set_max_delay -ignore_clock_latency W` / `set_min_delay -ignore_clock_latency 0`
               `-from [get_clocks A] -to [get_clocks B]` between each declared landed receive clock
               (lint(landed_clock_inputs=...)) and a real tap clock, both directions, W = period/2 - setup
               uncertainty (the meso-ring phase window, held HERE at the legacy 60 ps:
               LANDING_WINDOW_SETUP_PS); every landed clock needs all four.
"""
import math
import os
import argparse
import gzip
import hashlib
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
# Sign-off clock uncertainty policy, held HERE and not read from the generator under test (kit generators, signoff.py
# and die_sta.py read it from here; kits ship this file standalone, so it imports nothing of the repo).
# OWNER 12.24b (2026-10-31 00:56) as finalised by OWNER 12.24c (binding, all dies, die AND core sign-off): REMOVE the
# 60 ps core clock SETUP uncertainty -> 0.  The HOLD side is NOT changed: the 25 ps hold uncertainty stays (a separate
# constant, NOMINAL_UNC_HOLD_PS, so setup and hold move independently), and so do the kit hold-repair margins.
# Kept: setup/hold >= 0 at TT setup / FF hold, slew / cap, DRC, LEC, routed arrivals, the 833 ps period.
# The old AGENTS.md 2026-09-30 setup 60 ps stays reachable for A/B / margin reports only: env OT_MARGIN_POLICY=legacy
# (signoff.py run --margin-policy legacy).
MARGIN_POLICY_ENV = "OT_MARGIN_POLICY"
MARGIN_POLICIES = ("nominal", "legacy")
MARGIN_POLICY_DEFAULT = "nominal"
MARGIN_POLICY_RULE = "OWNER 12.24b/c 2026-10-31: nominal setup (setup clock uncertainty 0, hold 25 kept; legacy setup 60 = A/B only)"
NOMINAL_UNC_SETUP_PS = 0.0     # OWNER 12.24b (a) / 12.24c
NOMINAL_UNC_HOLD_PS = 25.0     # OWNER 12.24c: hold side unchanged (separate constant)
LEGACY_UNC_SETUP_PS, LEGACY_UNC_HOLD_PS = 60.0, 25.0   # AGENTS.md 2026-09-30 / 10-24 policy (A/B switch only)


def margin_policy(policy=None):
    """'nominal' (default, OWNER 12.24b/c) or 'legacy' (setup 60, A/B / margin report only): explicit argument > env OT_MARGIN_POLICY > default."""
    v = policy or os.environ.get(MARGIN_POLICY_ENV) or MARGIN_POLICY_DEFAULT
    if v not in MARGIN_POLICIES:
        raise ValueError(f"{MARGIN_POLICY_ENV}: '{v}' not in {MARGIN_POLICIES}")
    return v


def policy_uncertainty(policy=None):
    """(setup_ps, hold_ps) clock uncertainty of the sign-off policy (read at call time, so the env switch applies)."""
    if margin_policy(policy) == "legacy":
        return LEGACY_UNC_SETUP_PS, LEGACY_UNC_HOLD_PS
    return NOMINAL_UNC_SETUP_PS, NOMINAL_UNC_HOLD_PS


# Landed-crossing phase window W = T/2 - LANDING_WINDOW_SETUP_PS (landing_contract.py meso ring law).  COORD 10-31
# (OWNER 12.24c follow-up): the 60 ps is dropped, the window is the full half-period (legacy policy keeps 60 for A/B).
LANDING_WINDOW_SETUP_PS = 0.0
LEGACY_LANDING_WINDOW_SETUP_PS = LEGACY_UNC_SETUP_PS


def landing_window_setup_ps(policy=None):
    return LEGACY_LANDING_WINDOW_SETUP_PS if margin_policy(policy) == "legacy" else LANDING_WINDOW_SETUP_PS


# import-time snapshot for older readers (die core generators); new code calls policy_uncertainty()
POLICY_SETUP_PS, POLICY_HOLD_PS = policy_uncertainty()
# seam hold contract floor (die tap skew bound 20 ps + routed-RCX error 5 ps, gen_phys.SEAM_HOLD_MIN_PS), held HERE:
# kits ship this linter without gen_phys.py (CLOCK-KV-R3 canary e444b9df7: ModuleNotFoundError gen_phys at sdc_lint).
# test_sdc_lint.py asserts it equals the generator constant.
SEAM_HOLD_MIN_PS = 25.0

# Standalone kits copy this linter without gen_phys.py; the allowed policy is independent of the generator.
ROOT_RESET_FALSE_PATH = (
    r"set_false_path -from [get_ports {arst_n}] -to "
    r"[get_pins -hierarchical -regexp {^u_rst_root[./]p\[[01]\]\$_DFF_PN0_/RESETN$}]"
)


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


# ---- 12.2a1 declared pushdown feed-through ports (COORD 10-26 12:55 ruling QC-SU-BTAB ASK) --------------------------
# Kept here (not in ft_ports.py) because kits / the sign-off bundle copy this linter standalone.
FT_SCHEMA = "opentallas.ft_ports.v1"
FT_MODEL_SCHEMA = "opentallas.ft_interface_model.v1"
FT_KINDS = ("clock", "reset")


def ft_digest(ports, arcs):
    body = dict(ports=sorted(ports, key=lambda p: p["name"]), arcs=sorted(arcs, key=lambda a: (a["source"], a["sink"])))
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def ft_verify(decl):
    """-> [errors] for a loaded declaration (schema, hash, ports == arc ends)."""
    err = []
    if not isinstance(decl, dict) or decl.get("schema") != FT_SCHEMA:
        return [f"ft declaration schema != {FT_SCHEMA}"]
    P, A = decl.get("ports") or [], decl.get("arcs") or []
    if ft_digest(P, A) != decl.get("sha256"):
        err.append("ft declaration sha256 does not match its port/arc list (edited or stale)")
    names = {p.get("name") for p in P}
    ends = {a.get(k) for a in A for k in ("source", "sink")}
    if names != ends:
        err.append(f"ft ports without a declared arc / arc ends not declared: {sorted(names ^ ends)}")
    d = {p.get("name"): p.get("direction") for p in P}
    for a in A:
        if a.get("kind") not in FT_KINDS:
            err.append(f"ft arc {a.get('source')}->{a.get('sink')}: kind {a.get('kind')!r}")
        if d.get(a.get("source")) != "INPUT" or d.get(a.get("sink")) != "OUTPUT":
            err.append(f"ft arc {a.get('source')}->{a.get('sink')}: direction")
    return err


def ft_model_errors(decl, model, require_characterised=False):
    """the interface model must carry every declared arc (same kind), for this declaration hash."""
    if not isinstance(model, dict) or model.get("schema") != FT_MODEL_SCHEMA:
        return ["ft interface model missing or wrong schema (kit fails: arc must exist in the interface model)"]
    err = []
    if model.get("ft_sha256") != decl.get("sha256"):
        err.append("ft interface model is for a different ft declaration (sha256)")
    have = {(a.get("source"), a.get("sink")): a for a in model.get("arcs") or []}
    for a in decl.get("arcs") or []:
        m = have.get((a["source"], a["sink"]))
        if m is None:
            err.append(f"ft arc {a['source']}->{a['sink']} missing from the interface model")
            continue
        if m.get("kind") != a["kind"]:
            err.append(f"ft arc {a['source']}->{a['sink']}: model kind {m.get('kind')} != declared {a['kind']}")
        if require_characterised:
            for c in ("tt_ps", "ff_ps"):
                v = m.get(c)
                if not isinstance(v, dict) or not all(isinstance(v.get(k), (int, float)) and v[k] >= 0
                                                       for k in ("min", "max")):
                    err.append(f"ft arc {a['source']}->{a['sink']}: {c} not characterised")
    extra = set(have) - {(a["source"], a["sink"]) for a in decl.get("arcs") or []}
    if extra:
        err.append(f"ft interface model has undeclared arcs {sorted(extra)}")
    return err


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
    def __init__(self, inputs, outputs, clock_ports, ft_in=(), ft_out=(), clock_out=()):
        self.inputs, self.outputs, self.clock_ports = list(inputs), list(outputs), list(clock_ports)
        # declared 12.2a1 ft ports exist in the built core: all_inputs / all_outputs select them too
        self.ft_in, self.ft_out = list(ft_in), list(ft_out)
        # declared forwarded-clock outputs (landing exports) are real output ports: all_outputs selects them too
        self.clock_out = list(clock_out)
        self.allp = self.inputs + self.outputs + self.clock_ports + self.ft_in + self.ft_out + self.clock_out
        self.vars = {}
        self.clocks = {}
        self.gclocks = {}             # generated clock -> [target port]


BITSEL = re.compile(r"^(.+)\[(\d+)\]$")


def _glob_ports(ctx, pats):
    r = []
    for p in pats:
        m = BITSEL.match(p)
        if m and m.group(1) in ctx.allp:
            # CLOCK-KV-R21 (hold_demand die_sta): one bit of a declared bus port -> the bus port
            r.append(m.group(1))
            continue
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
            return ("ports", ctx.inputs + ctx.ft_in)
        if len(a) != 1:
            raise SdcLintError(f"unsupported all_inputs options: {w}")
        return ("ports", ctx.inputs + ctx.clock_ports + ctx.ft_in)
    if c == "all_outputs":
        return ("ports", ctx.outputs + ctx.ft_out + ctx.clock_out)
    if c == "all_clocks":
        return ("clocks", list(ctx.clocks) + list(ctx.gclocks))
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
            if nm not in ctx.clocks and nm not in ctx.gclocks:
                raise SdcLintError(f"get_clocks {nm}: clock not defined")
        return ("clocks", names)
    if c == "remove_from_collection":
        # landing contract form: [remove_from_collection A B], B a subset of A of the same kind (no options)
        if len(a) != 3 or any(_isopt(x) for x in a[1:]):
            raise SdcLintError(f"unsupported remove_from_collection: {w}")
        ka, la = _eval_obj(ctx, a[1])
        kb, lb = _eval_obj(ctx, a[2])
        if ka != kb:
            raise SdcLintError(f"remove_from_collection of {kb} from {ka}: {w}")
        miss = [x for x in lb if x not in la]
        if miss:
            raise SdcLintError(f"remove_from_collection removes objects not in the collection {miss}: {w}")
        return (ka, [x for x in la if x not in lb])
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
         unc_setup_ps=None, unc_hold_ps=None, time_unit_ps=1.0, liberty_unit_ps=None,
         io_floor_ps=None, port_latency_ps=None, port_period_mult=None, insertion_ff_ps=None, straps=None,
         hold_in_min_ps=None, hold_out_min_ps=None, seam_hold_ps=None, hold_in_min_ports_ps=None,
         reset_pad_pins=None, root_async_reset=False, ft_ports=None, ft_interface=None,
         ft_require_characterised=False, tap_window_ps=None, forwarded_clock_outputs=None,
         landed_clock_inputs=None, edge_clock_latency_ps=None, pad_clock_inputs=None, pad_clock_outputs=None):
    """lint an SDC.  inputs / outputs: non-clock port (bus) names; clock_ports: the tap ports.  io_floor_ps
    {port: (min_max_delay_ps)}: the declared IO budget per port (max delay must not be below it).  port_latency_ps
    {tap port: ps}: the plan's CP2 early core taps (source latency = -early on exactly those ports).
    hold_in_min_ps / hold_out_min_ps / seam_hold_ps: the plan's opt-in seam hold contract (gen_phys.seam_hold);
    absent = legacy (min input <= -insertion_tol, min output <= 0).  hold_in_min_ports_ps {input port: ps}: IO-HOLD
    option A per-port min input delay limits (gen_phys.input_hold_min: the sender's guaranteed output-min) replacing
    the contract limit on exactly those ports.  ft_ports: the kit's 12.2a1 ft declaration (ft_ports.json: ports + arcs +
    sha256): exactly those ports are die-timed -- no IO delay / load / driving cell on them, never a clock source; any
    other port is core IO as before.  ft_interface: the kit interface model (ft_interface.json), which must carry
    every declared arc (characterised when ft_require_characterised).
    tap_window_ps: the plan's per-tap latency window W (gen_phys
    .tap_window_ps, COORD 11:24): every non-core clock port then carries source -early -W / -late 0, input max delays
    may sit W below their IO budget and output min delays W above the contract limit (the exact IO shift of the
    early tap); without it no -early / -late source latency is allowed.
    forwarded_clock_outputs / landed_clock_inputs: the plan clock.landing_contract export (clock out) and receive
    (clock in) ports (see the 'landing' check above); without them the three landing forms stay forbidden.
    edge_clock_latency_ps {edge clock: (early, late) ps}: the plan clock.edge_clocks[].source_latency_ps TT arrival of a
    source-forwarded edge clock (gen_phys.edge_clock_latency): exactly those clocks carry set_clock_latency -source
    -early / -late on [get_clocks X] with those values; without it no real clock carries a source latency.
    unc_setup_ps / unc_hold_ps: the full clock uncertainty the SDC must carry; None = policy_uncertainty() (OWNER
    12.24b/c nominal 0 / 25, legacy 60 / 25 with OT_MARGIN_POLICY=legacy).
    -> [errors]"""
    err = []
    pol_s, pol_h = policy_uncertainty()
    unc_setup_ps = pol_s if unc_setup_ps is None else unc_setup_ps
    unc_hold_ps = pol_h if unc_hold_ps is None else unc_hold_ps
    u = time_unit_ps
    in_lim = -float(insertion_tol_ps) if hold_in_min_ps is None else float(hold_in_min_ps)
    out_lim = 0.0 if hold_out_min_ps is None else float(hold_out_min_ps)
    if out_lim > EPS:
        err.append(f"hold: contract min output delay {out_lim:g} ps > 0 (sender hold check waived)")
    if hold_in_min_ps is not None or hold_out_min_ps is not None:
        if seam_hold_ps is None or abs((-out_lim - in_lim) - float(seam_hold_ps)) > EPS \
                or float(seam_hold_ps) < SEAM_HOLD_MIN_PS - EPS:
            err.append(f"hold: seam hold contract sender {-out_lim:g} + receiver {-in_lim:g} ps != seam "
                       f"{seam_hold_ps} ps or below {SEAM_HOLD_MIN_PS:g} ps")
    # FLOW 10-25 (ruling 9.7 / 5e): the SDC vclk carries the TT-bound insertion; the FF-bound one (FF-only flow steps,
    # vclk_corner.tcl) must be a positive insertion not above TT
    if insertion_ff_ps is not None and not (0 < float(insertion_ff_ps) <= float(insertion_ps) + EPS):
        err.append(f"clocks: bound FF insertion {insertion_ff_ps} ps not in (0, TT {insertion_ps:g}]")
    if liberty_unit_ps is not None and abs(liberty_unit_ps - u) > EPS:
        err.append(f"units: liberty time_unit {liberty_unit_ps:g} ps but the SDC is written in {u:g} ps units")
    ft_in, ft_out = [], []
    if ft_ports is not None:
        err += [f"ft: {e}" for e in ft_verify(ft_ports)]
        for p_ in ft_ports.get("ports") or []:
            (ft_in if p_.get("direction") == "INPUT" else ft_out).append(p_.get("name"))
        clash = set(ft_in + ft_out) & set(list(inputs) + list(outputs) + list(clock_ports))
        if clash:
            err.append(f"ft: declared ft ports also listed as core IO / clock ports {sorted(clash)}")
        err += [f"ft: {e}" for e in ft_model_errors(ft_ports, ft_interface, ft_require_characterised)]
    elif ft_interface is not None:
        err.append("ft: interface model ft arcs without an ft declaration")
    fwd_l, land_l = list(forwarded_clock_outputs or []), list(landed_clock_inputs or [])
    for x in land_l:
        if x not in clock_ports:
            err.append(f"landing: landed clock input {x} is not a clock tap port")
    clash = set(fwd_l) & set(list(inputs) + list(outputs) + list(clock_ports))
    if clash:
        err.append(f"landing: forwarded clock outputs also listed as data / clock ports {sorted(clash)}")
    pad_in, pad_out = dict(pad_clock_inputs or {}), dict(pad_clock_outputs or {})
    if set(pad_in) - set(clock_ports) or set(pad_out) & set(list(inputs) + list(outputs) + list(clock_ports) + fwd_l):
        err.append('pad_clock: clock pads conflict with declared data/clock roles')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in pad_in.values()):
        err.append('pad_clock: explicit positive finite input period required')
    for name, spec in pad_out.items():
        if not isinstance(spec, dict) or spec.get('source_clock_port') not in clock_ports:
            err.append(f'pad_clock: {name} needs an actual source clock port')
        per_ = spec.get('period_ps') if isinstance(spec, dict) else None
        if isinstance(per_, bool) or not isinstance(per_, (int, float)) or not math.isfinite(per_) or per_ <= 0:
            err.append(f'pad_clock: {name} needs an explicit positive finite output period')
    if any(e.startswith('pad_clock:') for e in err):
        return err
    export_l = fwd_l + list(pad_out)
    ctx = Ctx(inputs, outputs, clock_ports, ft_in, ft_out, export_l)
    gen_src = {}                      # forwarded output port -> generated clock
    land_ex = {}                      # (max|min, from, to) -> ps : landed-crossing delay exceptions
    land_window = float(period_ps) / 2 - landing_window_setup_ps()
    pad_env = set()
    ft_env = set()                    # ft ports reached by set_load / set_driving_cell
    clk_src = {}                      # port -> clock
    latency = {}                      # clock -> source latency (ps)
    port_lat = {}                     # clock port -> source latency (ps) (CP2 early core taps)
    port_win = {}                     # clock port -> {"early"|"late": ps} (plan clock.tap_window)
    clk_win = {}                      # edge clock -> {"early"|"late": ps} (plan edge_clocks[].source_latency_ps)
    tw = float(tap_window_ps or 0.0)
    unc = {}                          # (kind, from, to) -> ps ; from/to None = global
    idly = {p: {} for p in ctx.allp}  # port -> {"max": (clk, ps), "min": ...}
    odly = {p: {} for p in ctx.allp}
    refs = []
    # OWNER 10-25 option B: declared ID straps (strap_* inputs) are quasi-static: exactly one exception is allowed,
    # set_false_path -from [get_ports {<declared straps>}] (no case analysis), and every declared strap must have it
    strap_l = list(straps or [])
    for x in strap_l:
        if not isinstance(x, str) or not re.match(r"^strap_[A-Za-z0-9_]+$", x):
            err.append(f"straps: '{x}' must be named strap_<id> (OWNER 10-25 option B rule 1)")
        elif x not in ctx.inputs:
            err.append(f"straps: '{x}' is not an input port")
    if len(set(strap_l)) != len(strap_l):
        err.append("straps: duplicate names")
    strap_fp = set()
    pad_l, pad_fp = list(reset_pad_pins or []), []
    root_fp = 0
    for cmd in _split_cmds(text):
        try:
            w = _words(cmd)
            c = w[0]
            if c == "set_false_path" and root_async_reset:
                if w == _words(ROOT_RESET_FALSE_PATH):
                    root_fp += 1
                    continue
            if c == "set_false_path" and pad_l and "-to" in w:
                # PATH-KV-POR 10-25: the reset ROOT type of a die reset pad plan -- exactly
                # set_false_path -from [get_ports arst_n] -to [get_pins {<reset_pad_pins>}], nothing wider
                ok = len(w) == 5 and w[1] == "-from" and w[3] == "-to"
                if ok:
                    k, ps = _eval_obj(ctx, w[2])
                    a = _words(w[4][1:-1]) if w[4].startswith("[") else []
                    pins = [x for y in a[1:] for x in (y[1:-1].split() if y.startswith("{") else [y])]
                    ok = k == "ports" and ps == ["arst_n"] and a[:1] == ["get_pins"] and sorted(pins) == sorted(pad_l)
                if not ok:
                    err.append(f"reset pad: only 'set_false_path -from [get_ports arst_n] -to [get_pins {{{' '.join(pad_l)}}}]'"
                               f" is allowed (fail-closed): {cmd}")
                pad_fp.append(cmd)
                continue

            if c == "set_false_path" and strap_l:
                if len(w) != 3 or w[1] != "-from":
                    err.append(f"straps: only 'set_false_path -from [get_ports {{strap_*}}]' is allowed (fail-closed): {cmd}")
                    continue
                k, ps = _eval_obj(ctx, w[2])
                bad = [x for x in ps if x not in strap_l]
                if k != "ports" or bad:
                    err.append(f"straps: set_false_path -from on non-strap object(s) {bad or k} (fail-closed): {cmd}")
                    continue
                strap_fp.update(ps)
                continue
            if c == "create_generated_clock" and export_l:
                opts, objs, i = {}, [], 1
                while i < len(w):
                    if w[i] in ("-name", "-master_clock", "-source", "-divide_by"):
                        if w[i] in opts:
                            raise SdcLintError(f"create_generated_clock: {w[i]} twice: {cmd}")
                        opts[w[i]] = w[i + 1]
                        i += 2
                    elif _isopt(w[i]):
                        raise SdcLintError(f"create_generated_clock option {w[i]} outside the landing form: {cmd}")
                    else:
                        objs.append(w[i])
                        i += 1
                if set(opts) != {"-name", "-master_clock", "-source", "-divide_by"} or len(objs) != 1:
                    raise SdcLintError(f"create_generated_clock needs exactly -name -master_clock -source "
                                       f"-divide_by and one target port: {cmd}")
                nm, mc = opts["-name"], opts["-master_clock"]
                kt, tp = _eval_obj(ctx, objs[0])
                role = 'pad_clock' if any(p in pad_out for p in tp) else 'landing'
                if abs(_num(opts["-divide_by"], "divide_by") - 1) > EPS:
                    err.append(f"{role}: generated clock {nm} -divide_by {opts['-divide_by']} (forwarded clock "
                               "must run at the core period)")
                if nm in ctx.clocks or nm in ctx.gclocks:
                    err.append(f"clocks: {nm} created twice")
                if mc not in ctx.clocks or not ctx.clocks[mc] or mc in {clk_src.get(p) for p in land_l}:
                    err.append(f"{role}: generated clock {nm} master {mc} is not a real tap clock defined before it")
                ks, sp = _eval_obj(ctx, opts["-source"])
                if ks != "ports" or len(sp) != 1 or clk_src.get(sp[0]) != mc:
                    err.append(f"{role}: generated clock {nm} -source {opts['-source']} is not one source port "
                               f"of master clock {mc}")
                if kt != "ports" or len(tp) != 1 or tp[0] not in export_l:
                    err.append(f"{role}: generated clock {nm} target {objs[0]} is not one declared forwarded "
                               "clock output")
                for p in tp:
                    if p in pad_out:
                        want = pad_out[p]
                        if sp != [want.get('source_clock_port')]:
                            err.append(f'pad_clock: {p} source {sp} differs from its explicit source port')
                        src_period = pad_in.get(sp[0], period_ps * int((port_period_mult or {}).get(sp[0], 1))) if sp else None
                        if src_period is None or abs(float(want.get('period_ps', -1)) - src_period) > EPS:
                            err.append(f'pad_clock: {p} declared period differs from its generated source')
                    if p in gen_src:
                        err.append(f"{role}: forwarded clock output {p} carries two generated clocks")
                    gen_src[p] = nm
                ctx.gclocks[nm] = tp
                continue
            if c in ("set_max_delay", "set_min_delay") and land_l:
                kind = "max" if c == "set_max_delay" else "min"
                ok = (len(w) == 7 and w[1] == "-ignore_clock_latency" and w[3] == "-from" and w[5] == "-to")
                if ok:
                    v = _num(w[2], "delay") * u
                    kf, fr = _eval_obj(ctx, w[4])
                    kt, to = _eval_obj(ctx, w[6])
                    ok = kf == kt == "clocks" and len(fr) == len(to) == 1
                if not ok:
                    err.append(f"landing: only '{c} -ignore_clock_latency V -from [get_clocks A] -to [get_clocks B]' "
                               f"is allowed (fail-closed): {cmd}")
                    continue
                a_, b_ = fr[0], to[0]
                landed = {clk_src.get(p) for p in land_l}
                core = {n for n, s in ctx.clocks.items() if s and n not in landed}
                if not ((a_ in landed and b_ in core) or (a_ in core and b_ in landed)):
                    err.append(f"landing: {c} {a_}->{b_} is not between a landed receive clock and a real tap clock")
                    continue
                want = land_window if kind == "max" else 0.0
                if abs(v - want) > EPS:
                    err.append(f"landing: {c} {a_}->{b_} = {v:g} ps, landed-crossing window {want:g} ps")
                if (kind, a_, b_) in land_ex:
                    err.append(f"landing: {c} {a_}->{b_} given twice")
                land_ex[(kind, a_, b_)] = v
                continue
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
                srcp = _eval_obj(ctx, obj)[1] if obj is not None else []
                mult = {int((port_period_mult or {}).get(p, 1)) for p in srcp} or {1}
                if len(mult) > 1:
                    err.append(f"clocks: clock {nm} mixes ports of different plan periods")
                expected = {float(pad_in.get(p, period_ps * int((port_period_mult or {}).get(p, 1)))) for p in srcp} or {float(period_ps)}
                if len(expected) != 1 or not math.isfinite(per) or abs(per - next(iter(expected))) > EPS:
                    err.append(f"units/relaxation: clock {nm} period {opts['-period']} x {u:g} ps = {per:g} ps, "
                               f"plan period {sorted(expected)} ps")
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
                if k == "ports" and ("-early" in w or "-late" in w):     # plan clock.tap_window
                    el = "early" if "-early" in w else "late"
                    if "-early" in w and "-late" in w:
                        raise SdcLintError(f"set_clock_latency: both -early and -late: {cmd}")
                    for x in cl:
                        port_win.setdefault(x, {})[el] = _num(v[0], "latency") * u
                    continue
                if k == "clocks" and ("-early" in w or "-late" in w):    # forwarded edge clock arrival
                    if "-early" in w and "-late" in w:
                        raise SdcLintError(f"set_clock_latency: both -early and -late: {cmd}")
                    el = "early" if "-early" in w else "late"
                    for x in cl:
                        clk_win.setdefault(x, {})[el] = _num(v[0], "latency") * u
                    continue
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
                bitsel = rest[1].startswith("[get_ports") and all(
                    BITSEL.match(x) for x in _words(rest[1][1:-1])[1:][-1].strip("{}").split())
                if bitsel:
                    # CLOCK-KV-R21: per-bit lines may only TIGHTEN a bus-level -min (hold demand die_sta); the bus
                    # record keeps the bus-level value (the max over its bits) for the checks below
                    if mm != ["min"]:
                        err.append(f"ports: per-bit {c} must be -min only: {cmd}")
                    for p in ps:
                        if "min" not in tab[p] or val > tab[p]["min"][1] + EPS or tab[p]["min"][0] != ck:
                            err.append(f"hold: per-bit {c} -min {val:g} ps on {p} relaxes or precedes its bus-level "
                                       f"-min ({tab[p].get('min')})")
                    continue
                for p in ps:
                    for m in mm:
                        tab[p][m] = (ck, val)
                continue
            # set_load / set_driving_cell: evaluate the object (it must resolve); never on a declared ft port
            _k, _ps = _eval_obj(ctx, w[-1])
            ft_env.update(x for x in _ps if x in ctx.ft_in or x in ctx.ft_out)
            pad_env.update(x for x in _ps if x in pad_in or x in pad_out)
        except (SdcLintError, IndexError) as e:
            err.append(f"parse (fail-closed): {e} [{cmd}]")
    # ---- checks
    for p in ctx.ft_in + ctx.ft_out:
        if idly[p] or odly[p]:
            err.append(f"ft: declared die-timed ft port {p} has a core IO delay (12.2a1 ruling: no core IO budget)")
        if p in clk_src:
            err.append(f"ft: declared ft port {p} is a clock source in the core SDC")
    for p in sorted(ft_env):
        err.append(f"ft: set_load / set_driving_cell reaches declared ft port {p} (IO environment is die-owned)")
    for p in sorted(pad_env):
        err.append(f'pad_clock: data load/driving-cell environment on clock pad {p}')
    for p in export_l:
        if p not in gen_src:
            err.append(f"pad_clock: clock output {p} has no create_generated_clock" if p in pad_out else
                       f"landing: forwarded clock output {p} has no create_generated_clock")
        if idly[p] or odly[p]:
            err.append(f"pad_clock: IO delay on clock output {p}" if p in pad_out else
                       f"landing: IO delay on forwarded clock output {p}")
    for n in ctx.gclocks:
        if n in refs or any(n in (a_, b_) for _k, a_, b_ in land_ex):
            err.append(f"landing: generated clock {n} times a path (IO delay / exception); not the landing form")
    for p in land_l:
        n = clk_src.get(p)
        core = sorted(x for x, s in ctx.clocks.items() if s and x not in {clk_src.get(q) for q in land_l})
        if n is None:
            continue                  # reported as 'clock tap port has no create_clock'
        for k in ("max", "min"):
            for a_, b_ in ((n, None), (None, n)):
                if not any(kk == k and (a_ is None or a2 == a_) and (b_ is None or b2 == b_)
                           for kk, a2, b2 in land_ex):
                    err.append(f"landing: landed clock {n} has no set_{k}_delay -ignore_clock_latency "
                               f"{'from' if a_ else 'to'} a core clock {core}")
    for x in strap_l:
        if x not in strap_fp:
            err.append(f"straps: declared strap {x} has no set_false_path -from (quasi-static ID input)")
    if pad_l and len(pad_fp) != 1:
        err.append(f"reset pad: {len(pad_fp)} raw-pad false paths (want exactly one, to {pad_l})")
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
    wports = [p_ for p_ in ctx.clock_ports if p_ not in want and p_ not in pad_in]
    for p_, d in port_win.items():
        if not tw:
            err.append(f"clocks: source -early/-late window on port {p_} without a plan clock.tap_window")
        elif p_ in want:      # DIE-S81-10: early core tap keeps its own latency as late, early end -(early + W)
            if set(d) != {"early"} or abs(d["early"] - (want[p_] - tw)) > EPS:
                err.append(f"clocks: core tap {p_} window {d} ps, plan early {want[p_] - tw:g} (own {want[p_]:g} - W "
                           f"{tw:g}), no -late line")
        elif p_ not in wports:
            err.append(f"clocks: tap window on {p_}, which is not a window clock port")
    if tw:
        for p_ in want:
            if p_ not in port_win:
                err.append(f"clocks: plan early core tap {p_} has no clock.tap_window early line")
    if tw:
        for p_ in wports:
            d = port_win.get(p_, {})
            if abs(d.get("early", 1e9) + tw) > EPS or abs(d.get("late", 1e9)) > EPS:
                err.append(f"clocks: clock port {p_} window early {d.get('early')} / late {d.get('late')} ps, plan "
                           f"clock.tap_window -{tw:g} / 0")
    ewant = {n: (float(a), float(b)) for n, (a, b) in (edge_clock_latency_ps or {}).items()}
    for n, d in clk_win.items():
        if n not in ewant:
            err.append(f"clocks: source -early/-late latency on clock {n}, which has no plan edge clock source_latency_ps")
        elif set(d) != {"early", "late"} or abs(d["early"] - ewant[n][0]) > EPS or abs(d["late"] - ewant[n][1]) > EPS:
            err.append(f"clocks: edge clock {n} source latency {d} ps, plan early/late {ewant[n][0]:g}/{ewant[n][1]:g}")
    for n in ewant:
        if n not in clk_win:
            err.append(f"clocks: plan edge clock {n} source_latency_ps has no set_clock_latency -source -early/-late")
        elif clk_src and n not in {clk_src[p_] for p_ in clk_src}:
            err.append(f"clocks: plan edge clock {n} with source latency is not a port clock")
    for n in latency:
        if n not in virt:
            err.append(f"clocks: source latency on real clock {n} (only the virtual IO clock carries the budget)")
    for p in ctx.inputs:
        for m in ("max", "min"):
            if m not in idly[p]:
                err.append(f"ports: input {p} has no {m} input delay")
        p_lim = float((hold_in_min_ports_ps or {}).get(p, in_lim))
        if "min" in idly[p] and idly[p]["min"][1] > p_lim + EPS:
            err.append(f"hold: input {p} min input delay {idly[p]['min'][1]:g} ps > {p_lim:g} ps "
                       "(seam-hold padding relaxed)")
    for p in (hold_in_min_ports_ps or {}):
        if p not in ctx.inputs:
            err.append(f"hold: IO-HOLD per-port limit on '{p}', which is not an input port")
    for p in ctx.outputs:
        for m in ("max", "min"):
            if m not in odly[p]:
                err.append(f"ports: output {p} has no {m} output delay")
        if "min" in odly[p] and odly[p]["min"][1] > out_lim + tw + EPS:
            err.append(f"hold: output {p} min output delay {odly[p]['min'][1]:g} ps > {out_lim + tw:g} ps "
                       "(sender hold check waived)")
    for p, fl in (io_floor_ps or {}).items():
        tab = idly if p in ctx.inputs else odly
        if "max" in tab.get(p, {}) and tab[p]["max"][1] < fl - (tw if p in ctx.inputs else 0.0) - EPS:
            err.append(f"relaxation: {p} max delay {tab[p]['max'][1]:g} ps below its IO budget {fl:g} ps")
    full = {"setup": unc_setup_ps, "hold": unc_hold_ps}
    for kk, fv in full.items():
        for n in ctx.clocks:
            v = unc.get((kk, n, None))
            if v is None:
                err.append(f"uncertainty: no {kk} uncertainty on clock {n}" + (" (hold off)" if kk == "hold" else ""))
            elif abs(v - fv) > EPS:
                err.append(f"uncertainty: {kk} uncertainty on {n} = {v:g} ps, sign-off policy {fv:g} ps")
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
    if root_async_reset and root_fp != 1:
        err.append(f"root reset: expected exactly one exception to the two async root RESETN pins; found {root_fp}")
    return err


def kit_context(P, tn):
    """the lint inputs for partition type tn of plan P (port names exactly as gen_rtl declares them)."""
    import gen_phys
    import gen_rtl
    t = P.types[tn]
    cks = [n for n, _, _ in gen_phys.clock_pins(P, tn) + gen_phys.core_tap_pins(P, tn)]
    edge = {n: m for n, _x, _y, m in gen_phys.edge_clock_pins(P, tn)}
    cks += list(edge)
    import pad_clock as PC
    pad_pins = PC.pins(P, tn)
    pad_in = {p['name']: p['period_ps'] for p in pad_pins if p['dir'] == 'in'}
    pad_out = {p['name']: dict(source_clock_port=p['source_clock_port'], period_ps=p['period_ps']) for p in pad_pins if p['dir'] == 'out'}
    cks += list(pad_in)
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
    ids = [sp["name"] for sp in t.get("id_straps", []) + t.get("count_straps", [])]      # HEAD-BIND-4: partition ID straps (OWNER 10-25 B)
    for n in ids:
        ins.append(n)
        floor[n] = gen_phys.IO_BUDGET * per
    import reset_tree as RT
    if RT.start_broadcast(P) and not t.get("hard"):     # decision 13c START in: timed like arst_n
        ins.append("start_i")
        floor["start_i"] = gen_phys.IO_BUDGET * per
    for n, _x, _y in gen_phys.reset_out_pins(P, tn):      # reset wavefront registered outs (OWNER DECISION 13)
        outs.append(n)
        floor[n] = gen_phys.IO_BUDGET * per
    for p in t.get("pads",[]):
        if p.get("clock",False):continue
        dest=ins if p["dir"]=="in" else outs
        if p["name"] not in dest:dest.append(p["name"])
        floor[p["name"]]=gen_phys.IO_BUDGET*per
    # Landing status/start pins are real timed control ports. Forwarded clock
    # exports remain in _landing_ctx and must never get ordinary IO delays.
    for p in t.get("clock",{}).get("landing_contract",{}).get("pins",[]):
        if p["kind"]=="clock":continue
        dest=ins if p["dir"]=="in" else outs
        if p["name"] not in dest:dest.append(p["name"])
        floor[p["name"]]=gen_phys.IO_BUDGET*per
    ib = gen_phys.insertion_binding(P, tn)
    pad = {"reset_pad_pins": RT.pad_false_path_pins(P, tn)} if RT.pad_false_path_pins(P, tn) else {}
    return dict(**pad, period_ps=per, insertion_ps=ib["tt"], insertion_ff_ps=ib["ff"],
                insertion_tol_ps=float(P.clock["insertion_tol_ps"]), clock_ports=cks, inputs=ins, outputs=outs,
                **dict(zip(("unc_setup_ps", "unc_hold_ps"), policy_uncertainty())),
                time_unit_ps=gen_phys.LIB_TIME_UNIT_PS, io_floor_ps=floor, port_latency_ps=plat,
                port_period_mult=edge,
                **(dict(pad_clock_inputs=pad_in, pad_clock_outputs=pad_out) if pad_pins else {}), **_seam_ctx(P, tn), **_io_hold_ctx(P, tn),
                **({"tap_window_ps": gen_phys.tap_window_ps(P)} if gen_phys.tap_window_ps(P) else {}),
                **({"root_async_reset": True} if gen_phys.root_async_reset(P, tn) else {}),
                **({"straps": ids} if ids else {}), **_landing_ctx(P, tn), **_edge_latency_ctx(P, tn))


def _edge_latency_ctx(P, tn):
    """plan clock.edge_clocks[].source_latency_ps TT early/late (none without the field: byte-identical json)."""
    import gen_phys
    m = {n: list(v["tt"]) for n, v, _b in gen_phys.edge_clock_latency(P, tn)}
    return {"edge_clock_latency_ps": m} if m else {}


def _landing_ctx(P, tn):
    """plan clock.landing_contract export / receive clock ports (none without a contract: byte-identical json)."""
    pins = P.types[tn].get("clock", {}).get("landing_contract", {}).get("pins", [])
    fwd = [p["name"] for p in pins if p.get("kind") == "clock" and p.get("dir") == "out"]
    land = [p["name"] for p in pins if p.get("kind") == "clock" and p.get("dir") == "in"]
    return dict(**({"forwarded_clock_outputs": fwd} if fwd else {}), **({"landed_clock_inputs": land} if land else {}))


def _io_hold_ctx(P, tn):
    """IO-HOLD option A per-port min input delay limits (none in legacy mode: byte-identical json)."""
    import gen_phys
    m = gen_phys.input_hold_min(P, tn)
    return dict(hold_in_min_ports_ps={p: d["in_min_ps"] for p, d in sorted(m.items())}) if m else {}


def _seam_ctx(P, tn=None):
    """Keep the sender's checked output-min consistent in lint and sign-off."""
    import gen_phys
    checked = gen_phys.out_hold_check_ps(P, tn) if tn is not None else None
    if not P.clock.get("seam_hold") and checked is None:
        return {}
    sh = gen_phys.seam_hold(P)
    out_min = gen_phys.hold_out_min_ps(P, tn)
    return dict(hold_in_min_ps=sh["in_min_ps"], hold_out_min_ps=out_min,
                seam_hold_ps=sh["seam_ps"] if checked is None else round(-out_min-sh["in_min_ps"], 6))


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
    if ctx.get("ft_ports") is not None or (kd / "ft_ports.json").is_file():
        # 12.2a1 ft declaration: the kit file and the lint context must be the same declaration
        fp = json.loads((kd / "ft_ports.json").read_text()) if (kd / "ft_ports.json").is_file() else None
        if fp is None or ctx.get("ft_ports") is None or fp.get("sha256") != ctx["ft_ports"].get("sha256"):
            err.append("ft: kit ft_ports.json and sdc_lint.json ft_ports differ or one is missing")
        ctx["ft_ports"] = ctx.get("ft_ports") or fp
        mp = kd / "ft_interface.json"
        ctx["ft_interface"] = json.loads(mp.read_text()) if mp.is_file() else None
    if not ctx.get("straps") and (kd / "straps.json").is_file():
        d = json.loads((kd / "straps.json").read_text())   # OWNER 10-25 option B: the kit's declared ID straps
        ctx["straps"] = list(d.get("straps", []) if isinstance(d, dict) else d)
    err += ff_binding_errors(kd, ctx)
    return err + lint((kd / "constraint.sdc").read_text(), liberty_unit_ps=lu, **ctx)


_VCLK_FF_RE = re.compile(r"^\s*(?:override\s+)?export\s+OT_VCLK_FF\s*[:?]?=\s*(\S+)\s*$", re.M)
FF_BINDING_TOL_PS = 0.5


def kit_vclk_ff(kitdir):
    """the kit's config.mk OT_VCLK_FF (SDC time units; the FF basis of the in-flow FF-only GRT hold repair and the
    post-CTS / pre-route FF gates), last assignment wins; None when the kit has no per-corner binding."""
    cm = Path(kitdir) / "config.mk"
    if not cm.is_file():
        return None
    m = _VCLK_FF_RE.findall(cm.read_text(errors="replace"))
    return float(m[-1]) if m else None


def ff_binding_errors(kitdir, ctx):
    """HBM-CORES-R6 10-27 (collar_idx256r R5 attempt 3): the flow repaired FF hold against OT_VCLK_FF while the kit's
    sdc_lint.json carried no insertion_ff_ps, so signoff.py silently timed FF hold against the single TT vclk and
    failed ff_ref_missing after a 40-min route.  Fail closed BEFORE synth when the flow's FF binding and the sign-off
    reference disagree or one is missing.  -> [errors]"""
    ff = kit_vclk_ff(kitdir)
    if ff is None:
        return []
    unit = float(ctx.get("time_unit_ps") or 1.0)
    if ctx.get("insertion_ff_ps") is None:
        return [f"clocks: config.mk OT_VCLK_FF {ff:g} (flow FF hold-repair basis) but sdc_lint.json has no "
                "insertion_ff_ps: sign-off would time FF hold against the single TT vclk (ff_ref_missing); "
                "regenerate the kit with the per-corner FF binding in sdc_lint.json"]
    if abs(float(ctx["insertion_ff_ps"]) - ff * unit) > FF_BINDING_TOL_PS:
        return [f"clocks: sdc_lint.json insertion_ff_ps {float(ctx['insertion_ff_ps']):g} ps != config.mk OT_VCLK_FF "
                f"{ff:g} x {unit:g} ps (flow repair and sign-off would use different FF references)"]
    return measured_frame_errors(kitdir)


def measured_frame_errors(kitdir):
    """FLOW-SHARED-4 10-27 (rebase of codex/flow-mcmm-1351 2f4c07767 + 9891c5f4e7 WITHOUT b52ec3248..fba10301d, COORD RM77):
    the measured-FF two-mode hold reference is OPT-IN per kit (config.mk 'override export OT_MM_MEASURED_HOLD = 1',
    staged by kit_modes.py stage --measured-hold).  Kits without the flag are untouched (no new preflight error).  An
    opted-in kit must be a 'rebind' kit with an active two-mode session and the staged BC binding hook; else fail closed
    before synth.  -> [errors]"""
    kd = Path(kitdir)
    try:
        import kit_modes
        cfg = kit_modes.mk_vars((kd / "config.mk").read_text())
    except Exception as e:                       # noqa: BLE001
        return [f"clocks: measured MM configuration undecidable ({e})"]
    if cfg.get("OT_MM_MEASURED_HOLD") != "1":
        return []
    try:
        import vclk_ref
        ref = vclk_ref.ff_reference(kd)["ref"]
        if ref != "rebind":
            raise ValueError(f"measured hold requires the 'rebind' FF reference, kit has {ref}")
        miss = [f for f in ("vclk_measured_hold.tcl", "vclk_ref.py", "orfs_hold_mm.tcl") if not (kd / f).is_file()]
        if miss:
            raise ValueError(", ".join(miss))
        if not kit_modes.mm_state(kd, kit_modes.binding(kd)):
            raise ValueError("measured hold requires an active two-mode session")
        mm = (kd / "orfs_hold_mm.tcl").read_text()
        vm = (kd / "vclk_measured_hold.tcl").read_text()
        if "ot_vclk_measured_bind" not in mm or "OT_MM_MEASURED_HOLD" not in mm or "proc ot_vclk_measured_bind" not in vm:
            raise ValueError("measured BC binding hook missing")
    except Exception as e:                       # noqa: BLE001
        return [f"clocks: measured MM hold repair is incomplete ({e}); regenerate the staged kit"]
    return []


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
