#!/usr/bin/env python3
"""type_contract.py: contract_v1 type contract, REPORT ONLY (TYPE-CONTRACT-SPEC pilot, FABLE-RC-ALL 11-24 03:13 accept, r703).

    type_contract.py contract PLAN --type T [--window-ops OPS] [--tools TREE/tools/die_plan]     print one type's contract JSON
    type_contract.py census   PLAN --out JSON [--types RE] [--window-ops OPS] [--arrivals ROWS] [--core-rows ROWS] [--tsv TSV]
    type_contract.py credit   --base PLAN_A --new PLAN_B --out JSON [--types RE] [--kits-base DIR] [--kits-new DIR]
                              [--env-base FILE] [--env-new FILE] [--window-ops-new OPS] [--tsv TSV]
    type_contract.py kit-hash KIT_GEN_DIR --item T [--rtl DIR] [--env FILE]                       print KW_CONTRACT_KIT_HASH <sha256>

Nothing here gates, holds, retires or credits a count: every command only writes a report (r703).  The kit wave, the counter and
gen are unchanged; the pilot measures what contract_v1 WOULD credit and where the declared windows do not hold.

The five accepted changes (FABLE-RC-ALL 51358d36 on DESIGN.md):
 1. CREDIT ONLY BY KIT CONTENT.  kit_hash() covers the kit netlist (every file the kit RTL list names, by content), io.tcl,
    macro_place.tcl, constraint.sdc, core_taps_ff.sdc, pins.json, config.mk, the EFFECTIVE per-type verilog defines (as the
    kit applies them: config.mk VERILOG_DEFINES / -D lines plus the plan's verilog_defines) and the EFFECTIVE build env (the
    OT_* gen/build variables, ENV_IGNORE = bookkeeping only).  The contract hash only SCHEDULES (which types need a new kit);
    a type is CREDIT only when the kit hash of its new kit equals the kit hash of the kit it already has.
 2. ENTRIES WITH RELATIVE TIMING.  Each clock entry carries its relative offset (TT/FF, from clock.tap_offset.per_port_ps
    minus the type's minimum: the die owns only the common shift) and every core entry its core schedule_ps {TT, FF}
    (tap insertion_ps / insertion_ff_ps) and lead over the type's common latency.
 3. RESET ENTRY DEPTHS.  reset = {port, sync_stages, in_type_depth, flush_depth, required_hold_cycles}: in_type_depth =
    sync_stages + the deepest in-type reset relay chain (relay_depth D + stages_existing, reset_replicate copy_depth, reset
    wavefront_min_depth, landing reader/writer start depth); flush_depth = the deepest lane pipeline through the type
    (ft_slots stations, internal_stations registers); required_hold_cycles = in_type_depth + flush_depth.
 4. KEYED BY SITE OR PORT, NEVER BY DIE TAP NAME.  Grid entries are keyed 'site:<x>,<y>' (type frame, 0.1 um); core entries
    'core:<inst>[.<pin>]'; forwarded edge clocks 'edge:<type port>'.  The die tap name (clk, clk_t<n>, clk_c<k>) is kept as
    a field for lookup only and never enters the contract hash, so a re-name / re-number of die taps is not a change.
 5. ARRIVAL vs DECLARED WINDOW AT BIND.  census() compares, per entry, the modelled arrival spread (per-port kit window need of
    the die clock model, --arrivals {per_port_ps: {type: {port: need}}}, re-keyed to SITES through --arrivals-plan = the plan the
    model was measured on) with the entry's declared window, and every core entry's modelled insertion (--core-rows,
    core_tap_retarget rows keyed by core pin: signed mean, else ETM) with its schedule.  OUTSIDE = need >
    window (or |model - schedule| > window); UNMODELLED = no model value.  Report only.

CONTRACT WINDOW.  An entry's window is clock.tap_window.per_port_ps[type][port], else per_type_ps[type], else window_ps.  With
--window-ops (S81 TPLWIN-ENVELOPE ops: replace ops on /clock/tap_window/..., old-checked) the windows come from the plan with
those ops applied: one window per port per template group becomes the contract window, not a second mechanism.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path

CONTRACT_V = "contract_v1"
KIT_HASH_V = b"contract-kit-v1"
HERE = Path(__file__).resolve().parent

# type-node keys that are DIE SIDE (sites of die relays / bookkeeping / provenance): not in the contract
DIE_SIDE_TYPE_KEYS = frozenset({
    "note", "sources", "relay_sites", "relay_polylines", "relay_rank_sites", "relay_branch", "type_template",
    "param_base_type", "landing_base_type", "reach_homes",
})
# clock keys that are DIE SIDE: die tap lists (replaced by entries), die tap bookkeeping, provenance
DIE_SIDE_CLOCK_KEYS = frozenset({"taps", "added_taps", "tap_um", "core_taps", "edge_clocks", "tap_core_src", "tap_grt_pre",
                                 "tap_core_etap", "landing_local_resets"})
TEXT_KEYS = frozenset({"note", "notes", "source", "proof", "why", "authority", "budget_owner", "insertion_basis", "provenance"})
# die reset NET names inside type data (raw / raw_reset = the die relay net that feeds a stage): die side, dropped
DIE_NAME_KEYS = frozenset({"raw", "raw_reset"})
# build env variables that are bookkeeping only (never change a kit or a build)
ENV_IGNORE = frozenset({"OT_LANE", "OT_KIT_WAVE", "PYTHONDONTWRITEBYTECODE", "TMPDIR", "OT_RUN_ID", "OT_JOB", "HOME", "PWD"})
KIT_FILES = ("io.tcl", "macro_place.tcl", "constraint.sdc", "core_taps_ff.sdc", "pins.json", "config.mk")


def _sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _strip(o):
    """drop provenance text and die net names, recursively"""
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in TEXT_KEYS and k not in DIE_NAME_KEYS}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def _r(v, q=0.1):
    return round(round(float(v) / q) * q, 3)


def site_key(x, y):
    return "site:%.1f,%.1f" % (_r(x), _r(y))


def _num(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


# ---------------------------------------------------------------- windows (TPLWIN-ENVELOPE ops)
def _ptr(path):
    return [p.replace("~1", "/").replace("~0", "~") for p in path.lstrip("/").split("/")]


def apply_window_ops(raw, ops):
    """a COPY of the clock.tap_window part of raw with replace ops applied (old-checked); -> (tap_window, applied, refused)"""
    tw = copy.deepcopy((raw.get("clock") or {}).get("tap_window") or {})
    root = {"clock": {"tap_window": tw}}
    ok = bad = 0
    for op in (ops.get("ops") if isinstance(ops, dict) else ops) or []:
        keys = _ptr(op["path"])
        if op.get("op") != "replace" or keys[:2] != ["clock", "tap_window"]:
            bad += 1
            continue
        cur = root
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        if "old" in op and cur.get(keys[-1]) != op["old"]:
            bad += 1
            continue
        cur[keys[-1]] = op["value"]
        ok += 1
    return tw, ok, bad


def window_of(tw, tn, port):
    pp = ((tw.get("per_port_ps") or {}).get(tn) or {})
    if port in pp and _num(pp[port]) is not None:
        return float(pp[port]), "port"
    pt = (tw.get("per_type_ps") or {}).get(tn)
    if _num(pt) is not None:
        return float(pt), "type"
    return _num(tw.get("window_ps"), 0.0), "die"


# ---------------------------------------------------------------- the contract
def _ports(P, raw, tn):
    """-> ({grid port: (x, y)}, [(core port, x, y, tap)], why) through the die tools (schema.tap_grid / core_taps); falls back to
    the plan's explicit taps when the tools are not importable or the grid cannot be evaluated"""
    ck = raw["partition_types"][tn].get("clock") or {}
    core, grid, why = [], {}, None
    if P is not None:
        import schema as S
        try:
            core = list(S.core_taps(P, tn))
        except Exception as e:                           # noqa: BLE001  report, never die
            why = "core_taps: %s" % type(e).__name__
        try:
            grid = {n: (float(x), float(y)) for n, x, y in S.tap_grid(P, tn)}
        except Exception as e:                           # noqa: BLE001
            why = (why + "; " if why else "") + "tap_grid: %s: %s" % (type(e).__name__, str(e)[:120])
            grid = {}
    if not grid:
        for tp in ck.get("taps") or []:
            if tp.get("kind") != "core" and isinstance(tp.get("xy"), (list, tuple)):
                grid[tp["name"]] = (float(tp["xy"][0]), float(tp["xy"][1]))
        for a in ck.get("added_taps") or []:
            if isinstance(a.get("xy"), (list, tuple)):
                grid.setdefault(a["name"], (float(a["xy"][0]), float(a["xy"][1])))
    if not core and P is None and ck.get("core_taps") == "early":
        for tp in ck.get("taps") or []:
            if tp.get("kind") == "core":
                core.append(("clk_c%d" % len(core), float(tp["xy"][0]), float(tp["xy"][1]), tp))
    return grid, core, why


def _depth_list(v, keys):
    out = []
    for e in v or []:
        if isinstance(e, dict):
            out.append(sum(int(_num(e.get(k), 0) or 0) for k in keys))
    return max(out) if out else 0


def reset_entry(raw, tn, P=None):
    """change 3: in-type reset depth and flush depth (required hold cycles) of type tn.  With the die tools (P), the in-type depth
    is reset_tree.for_type's own tree (depth = equal-padded relay depth inside the type, + sync stages); else the plan estimate."""
    ty = raw["partition_types"][tn]
    rs = ty.get("reset") or {}
    ck = ty.get("clock") or {}
    sync = int(_num(rs.get("sync_stages"), 0) or 0)
    relay = _depth_list(ty.get("relay_depth"), ("D", "stages_existing"))
    repl = _depth_list(ty.get("reset_replicate"), ("copy_depth",))
    wave = int(_num(rs.get("wavefront_min_depth"), 0) or 0)
    land = max([int(_num((ck.get(k) or {}).get("depth"), 0) or 0) for k in ("landing_reader_start", "landing_writer_start")] + [0])
    chain = max(relay, repl, wave, land)
    st = [int(_num(f.get("stations"), 0) or 0) for f in ty.get("ft_slots") or [] if isinstance(f, dict)]
    st += [len(s.get("regs_um") or []) for s in ty.get("internal_stations") or [] if isinstance(s, dict)]
    flush = max(st) if st else 0
    parts = dict(relay=relay, replicate=repl, wavefront=wave, landing_start=land, basis="plan")
    if P is not None:
        try:
            import reset_tree as RT
            T = RT.for_type(P, tn)
            chain = int(T.get("depth") or 0)
            sync = int(T.get("sync_stages") or sync)
            parts.update(basis="reset_tree", tree_depth=chain, own_depth=T.get("own_depth"), entry=T.get("entry"))
        except Exception as e:                           # noqa: BLE001  report, never die
            parts["tree_why"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    return dict(port="rst_n", sync_stages=sync, in_type_depth=sync + chain, flush_depth=flush,
                required_hold_cycles=sync + chain + flush, parts=parts)


def contract(raw, tn, P=None, tw=None):
    """-> contract_v1 dict of type tn: type-owned fields + entries (changes 2-4) + reset entry (change 3) + 'sha' (no port names)"""
    ty = raw["partition_types"][tn]
    ck0 = raw.get("clock") or {}
    tw = tw if tw is not None else (ck0.get("tap_window") or {})
    off = ((ck0.get("tap_offset") or {}).get("per_port_ps") or {}).get(tn) or {}
    common = _num(ty.get("clock", {}).get("insertion_ps"), _num(ck0.get("common_latency_ps"), 0.0))
    grid, core, why = _ports(P, raw, tn)

    def rel(port):
        if port not in off:
            return None
        o = off[port]
        return {c: _num(o.get(c) if isinstance(o, dict) else o) for c in ("TT", "FF")} if isinstance(o, dict) else {"TT": _num(o)}

    entries = {}
    for port, (x, y) in grid.items():
        w, wsrc = window_of(tw, tn, port)
        entries[site_key(x, y)] = dict(kind="grid", port=port, site=[_r(x), _r(y)], window_ps=w, window_src=wsrc, rel=rel(port))
    for port, x, y, tp in core:
        tt, ff = _num(tp.get("insertion_ps")), _num(tp.get("insertion_ff_ps"))
        w, wsrc = window_of(tw, tn, port)
        entries["core:%s" % tp.get("name")] = dict(kind="core", port=port, site=[_r(x), _r(y)], window_ps=w, window_src=wsrc,
                                                   rel=rel(port), schedule_ps={"TT": tt, "FF": ff},
                                                   lead_ps=(None if tt is None or common is None else round(tt - common, 3)))
    for ec in (ty.get("clock") or {}).get("edge_clocks") or []:
        entries["edge:%s" % ec.get("port")] = dict(kind="edge", port=ec.get("port"), site=[_r(v) for v in ec.get("tap_um") or []],
                                                  period_mult=ec.get("period_mult"))
    # relative offsets: minus the type minimum (the die owns the common shift)
    for c in ("TT", "FF"):
        vals = [e["rel"][c] for e in entries.values() if e.get("rel") and e["rel"].get(c) is not None]
        if vals:
            m = min(vals)
            for e in entries.values():
                if e.get("rel") and e["rel"].get(c) is not None:
                    e["rel"][c] = round(e["rel"][c] - m, 3)
    own = {k: _strip(v) for k, v in ty.items() if k not in DIE_SIDE_TYPE_KEYS and k != "clock"}
    own["clock"] = {k: _strip(v) for k, v in (ty.get("clock") or {}).items() if k not in DIE_SIDE_CLOCK_KEYS}
    rst = reset_entry(raw, tn, P)
    hashed = dict(v=CONTRACT_V, own=own, reset={k: v for k, v in rst.items() if k != "parts"},
                  entries={k: {kk: vv for kk, vv in e.items() if kk not in ("port", "window_src")} for k, e in entries.items()})
    return dict(v=CONTRACT_V, type=tn, sha=_sha(hashed), own_sha=_sha(own), entries_sha=_sha(hashed["entries"]),
                reset_sha=_sha({k: v for k, v in rst.items() if k != "parts"}), reset=rst, entries=entries, tools_why=why)


# ---------------------------------------------------------------- change 5: arrival vs declared window
def census_type(c, need=None, core_model=None, eps=0.05):
    """-> list of entry rows {key, kind, port, window, model, status}.  need {entry key: kit window need ps} (keyed by SITE / core
    pin, change 4: use need_by_key() to re-key a per-port model through the plan it was measured on); core_model {entry key: TT ps}"""
    rows = []
    need, core_model = need or {}, core_model or {}
    for k, e in sorted(c["entries"].items()):
        if e["kind"] == "edge":
            continue
        w = e.get("window_ps")
        if e["kind"] == "core":
            m = core_model.get(k)
            sch = (e.get("schedule_ps") or {}).get("TT")
            if m is None or sch is None:
                st, d = "UNMODELLED", None
            else:
                d = round(abs(float(m) - float(sch)), 3)
                st = "OUTSIDE" if w is not None and d > w + eps else "INSIDE"
            rows.append(dict(key=k, kind="core", port=e["port"], window_ps=w, model_ps=m, schedule_tt=sch, dev_ps=d, status=st))
            if k in need:                                     # the core entry also has a kit window need
                n = float(need[k])
                rows.append(dict(key=k + "#win", kind="core-win", port=e["port"], window_ps=w, model_ps=n, schedule_tt=None,
                                 dev_ps=n, status="OUTSIDE" if w is not None and n > w + eps else "INSIDE"))
            continue
        n = need.get(k)
        st = "UNMODELLED" if n is None else ("OUTSIDE" if w is not None and float(n) > w + eps else "INSIDE")
        rows.append(dict(key=k, kind="grid", port=e["port"], window_ps=w, model_ps=n, schedule_tt=None, dev_ps=n, status=st))
    return rows


def need_by_key(raw, tn, per_port, P=None):
    """change 4: a per-PORT model row (die tap names of the plan it was measured on = raw) -> {entry key: value}, through that
    plan's own tap sites; ports the plan does not have are dropped (returned second)"""
    grid, core, _ = _ports(P, raw, tn)
    m = {p: site_key(x, y) for p, (x, y) in grid.items()}
    m.update({p: "core:%s" % tp.get("name") for p, x, y, tp in core})
    out, lost = {}, []
    for p, v in (per_port or {}).items():
        if p in m and _num(v) is not None:
            out[m[p]] = max(float(v), out.get(m[p], float("-inf")))
        else:
            lost.append(p)
    return out, lost


# ---------------------------------------------------------------- change 1: kit content hash
def _norm(t, kit, item):
    t = t.replace(str(kit), "<K>")
    t = re.sub(r"/srv/opentallas-scratch\d*/[^\s\"';:]*?/(physical|rtl|tools)/", r"<SRC>/\1/", t)
    t = re.sub(r"/srv/opentallas-scratch\d*/[^\s\"';:]*", lambda m: "<P>/" + os.path.basename(m.group(0)), t)
    t = re.sub(r"attempt_\d+", "attempt_N", t)
    return t


def effective_defines(config_text, plan_defines=None):
    d = set()
    for l in config_text.splitlines():
        if re.search(r"VERILOG_DEFINES|DEFINES\s*[:+]?=", l):
            d.update(re.findall(r"-D\s*([A-Za-z_][A-Za-z0-9_]*(?:=[^\s\"']*)?)", l))
    for v in plan_defines or []:
        d.add(str(v) if not isinstance(v, dict) else json.dumps(v, sort_keys=True))
    return sorted(d)


def effective_env(env):
    return {k: (os.path.basename(v) if v.startswith("/") else v) for k, v in sorted((env or {}).items())
            if k.startswith("OT_") and k not in ENV_IGNORE}


def read_env_file(p):
    """KEY=VALUE lines, or a shell line with export KEY=VALUE ... ; -> dict"""
    env = {}
    for tok in re.findall(r"\b([A-Z][A-Z0-9_]*)=(\S+)", Path(p).read_text()):
        env[tok[0]] = tok[1].strip("'\"")
    return env


def kit_rtl_files(rtl_dir):
    """the kit netlist files: every existing file a *.f list in rtl_dir names, plus *.sv/*.v in rtl_dir"""
    rtl_dir = Path(rtl_dir)
    fs = set()
    for f in sorted(rtl_dir.glob("*.f")):
        for l in f.read_text(errors="replace").splitlines():
            l = l.strip()
            if l and not l.startswith(("+", "-", "//", "#")):
                p = Path(l) if os.path.isabs(l) else rtl_dir / l
                if p.is_file():
                    fs.add(p)
    fs.update(p for p in rtl_dir.iterdir() if p.suffix in (".sv", ".v", ".svh", ".vh") and p.is_file())
    return sorted(fs, key=lambda p: (p.name, str(p)))


def kit_hash(gen_dir, item, rtl_dir=None, env=None, plan_defines=None):
    """change 1: sha256 of the kit content + effective defines + effective env; -> (hex, parts {name: sha12})"""
    gen_dir = Path(gen_dir)
    h = hashlib.sha256(KIT_HASH_V)
    parts = {}
    cfg = ""
    for f in KIT_FILES:
        p = gen_dir / f
        t = _norm(p.read_text(errors="replace"), gen_dir, item) if p.is_file() else "\0MISSING\0"
        if f == "config.mk":
            cfg = t
        parts[f] = hashlib.sha256(t.encode()).hexdigest()[:12]
        h.update(f.encode() + b"\0" + t.encode() + b"\0")
    if rtl_dir:
        rh = hashlib.sha256()
        for p in kit_rtl_files(rtl_dir):
            rh.update(p.name.encode() + b"\0" + _norm(p.read_text(errors="replace"), rtl_dir, item).encode() + b"\0")
        parts["netlist"] = rh.hexdigest()[:12]
        h.update(b"netlist\0" + rh.hexdigest().encode())
    else:
        parts["netlist"] = "MISSING"
        h.update(b"netlist\0MISSING")
    dfs = effective_defines(cfg, plan_defines)
    ev = effective_env(env)
    parts["defines"], parts["env"] = _sha(dfs)[:12], _sha(ev)[:12]
    h.update(b"defines\0" + _sha(dfs).encode() + b"env\0" + _sha(ev).encode())
    return h.hexdigest(), parts


def find_kit(kits, tn):
    """kits/<T>/gen/<T> (+ kits/<T>/rtl) or kits/<T> -> (gen_dir, rtl_dir) or (None, None)"""
    if not kits:
        return None, None
    b = Path(kits) / tn
    for g in (b / "gen" / tn, b):
        if (g / "constraint.sdc").is_file():
            r = b / "rtl"
            return g, (r if r.is_dir() else None)
    return None, None


def credit_row(ca, cb, kh_a, kh_b):
    """-> verdict: CREDIT (kit hash equal), KIT-CHANGED (kits differ: re-issue), SCHEDULE-SAME (contract same, no kit pair:
    provisional, no credit), REISSUE (contract changed, no kit pair)"""
    if kh_a and kh_b:
        return "CREDIT" if kh_a == kh_b else "KIT-CHANGED"
    return "SCHEDULE-SAME" if ca["sha"] == cb["sha"] else "REISSUE"


# ---------------------------------------------------------------- CLI
def _plan_obj(raw, path, tools):
    if tools:
        sys.path.insert(0, str(Path(tools).resolve()))
    else:
        sys.path.insert(0, str(HERE))
    try:
        import schema as S
        return S.Plan(raw, Path(path)) if path else S.Plan(raw)
    except Exception as e:                               # noqa: BLE001
        print("type_contract: schema.Plan unavailable (%s: %s); explicit taps only" % (type(e).__name__, str(e)[:160]), file=sys.stderr)
        return None


def _types(raw, rx, listf=None):
    ts = sorted(raw["partition_types"])
    if listf:
        keep = {l.split()[0] for l in Path(listf).read_text().splitlines() if l.strip() and not l.startswith("#")}
        ts = [t for t in ts if t in keep]
    return [t for t in ts if not rx or re.search(rx, t)]


def _tsv(path, rows, cols):
    with open(path, "w") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("contract"); a1.add_argument("plan"); a1.add_argument("--type", required=True)
    a2 = sub.add_parser("census"); a2.add_argument("plan"); a2.add_argument("--out", required=True)
    a3 = sub.add_parser("credit"); a3.add_argument("--base", required=True); a3.add_argument("--new", required=True)
    a3.add_argument("--out", required=True)
    a4 = sub.add_parser("kit-hash"); a4.add_argument("gen"); a4.add_argument("--item", required=True)
    a4.add_argument("--rtl"); a4.add_argument("--env")
    for a in (a1, a2, a3):
        a.add_argument("--tools"); a.add_argument("--types"); a.add_argument("--types-file")
    for a in (a1, a2):
        a.add_argument("--window-ops")
    a2.add_argument("--arrivals"); a2.add_argument("--arrivals-plan"); a2.add_argument("--core-rows"); a2.add_argument("--tsv")
    for s in ("base", "new"):
        a3.add_argument("--kits-" + s); a3.add_argument("--env-" + s); a3.add_argument("--window-ops-" + s)
    a3.add_argument("--tsv")
    a = ap.parse_args(argv)

    if a.cmd == "kit-hash":
        h, parts = kit_hash(a.gen, a.item, a.rtl, read_env_file(a.env) if a.env else dict(os.environ))
        print(json.dumps(parts, sort_keys=True))
        print("KW_CONTRACT_KIT_HASH " + h)
        return 0

    def load(path, ops_path):
        raw = json.load(open(path))
        tw, ok, bad = (apply_window_ops(raw, json.load(open(ops_path))) if ops_path
                       else ((raw.get("clock") or {}).get("tap_window") or {}, 0, 0))
        return raw, _plan_obj(raw, path, a.tools), tw, dict(applied=ok, refused=bad)

    if a.cmd == "contract":
        raw, P, tw, _ = load(a.plan, a.window_ops)
        print(json.dumps(contract(raw, a.type, P, tw), indent=1, sort_keys=True))
        return 0

    if a.cmd == "census":
        raw, P, tw, opsr = load(a.plan, a.window_ops)
        need = (json.load(open(a.arrivals)).get("per_port_ps") or {}) if a.arrivals else {}
        if a.arrivals_plan:
            raw_m = json.load(open(a.arrivals_plan))
            P_m = _plan_obj(raw_m, a.arrivals_plan, a.tools)
        else:
            raw_m, P_m = raw, P
        core = {}
        if a.core_rows:
            for r in json.load(open(a.core_rows)).get("rows") or []:
                v = _num(r.get("signed_mean_TT"))
                if v is None:
                    v = _num(r.get("etm_max_TT"))
                if v is not None and r.get("tap"):
                    core.setdefault(r["type"], {})["core:%s" % r["tap"]] = v
        out, flat, lost_n, name_diff = {}, [], 0, 0
        for tn in _types(raw, a.types, a.types_file):
            c = contract(raw, tn, P, tw)
            nk, lost = ({}, []) if tn not in need or tn not in raw_m["partition_types"] else need_by_key(raw_m, tn, need[tn], P_m)
            lost_n += len(lost)
            byname = {k: need[tn][e["port"]] for k, e in c["entries"].items() if tn in need and e.get("port") in need[tn]}
            name_diff += sum(1 for k in set(nk) | set(byname) if nk.get(k) != byname.get(k))
            rows = census_type(c, nk, core.get(tn))
            cnt = {}
            for r in rows:
                cnt[r["status"]] = cnt.get(r["status"], 0) + 1
                flat.append(dict(type=tn, **r))
            out[tn] = dict(sha=c["sha"], entries=len(c["entries"]), reset=c["reset"], counts=cnt, tools_why=c["tools_why"],
                           outside=[r for r in rows if r["status"] == "OUTSIDE"][:20])
        tot = {}
        for v in out.values():
            for k, n in v["counts"].items():
                tot[k] = tot.get(k, 0) + n
        types_out = sorted(t for t, v in out.items() if v["counts"].get("OUTSIDE"))
        summ = dict(v=CONTRACT_V, report_only="r703", plan=a.plan, window_ops=a.window_ops, window_ops_result=opsr,
                    types=len(out), entries=tot, types_outside=len(types_out),
                    types_unmodelled=sum(1 for v in out.values() if v["counts"].get("UNMODELLED")),
                    arrivals=a.arrivals, arrivals_plan=a.arrivals_plan or a.plan, model_ports_not_in_model_plan=lost_n,
                    entries_where_name_key_differs_from_site_key=name_diff)
        Path(a.out).write_text(json.dumps(dict(summary=summ, types=out, types_outside=types_out), indent=1, sort_keys=True))
        if a.tsv:
            _tsv(a.tsv, flat, ["type", "key", "kind", "port", "window_ps", "model_ps", "schedule_tt", "dev_ps", "status"])
        print("TYPE_CONTRACT census: %s" % json.dumps(summ, sort_keys=True))
        return 0

    raw_a, P_a, tw_a, _ = load(a.base, a.window_ops_base)
    raw_b, P_b, tw_b, opsr = load(a.new, a.window_ops_new)
    env_a = read_env_file(a.env_base) if a.env_base else None
    env_b = read_env_file(a.env_new) if a.env_new else None
    rows = []
    for tn in _types(raw_b, a.types, a.types_file):
        if tn not in raw_a["partition_types"]:
            rows.append(dict(type=tn, verdict="NEW"))
            continue
        ca, cb = contract(raw_a, tn, P_a, tw_a), contract(raw_b, tn, P_b, tw_b)
        kh = []
        for kits, env, raw in ((a.kits_base, env_a, raw_a), (a.kits_new, env_b, raw_b)):
            g, r = find_kit(kits, tn)
            kh.append(kit_hash(g, tn, r, env or {}, raw["partition_types"][tn].get("verilog_defines")) if g else (None, None))
        rows.append(dict(type=tn, verdict=credit_row(ca, cb, kh[0][0], kh[1][0]), contract_same=ca["sha"] == cb["sha"],
                         own_same=ca["own_sha"] == cb["own_sha"], entries_same=ca["entries_sha"] == cb["entries_sha"],
                         reset_same=ca["reset_sha"] == cb["reset_sha"], kit_base=(kh[0][0] or "")[:16], kit_new=(kh[1][0] or "")[:16],
                         kit_parts_diff=",".join(k for k in (kh[0][1] or {}) if kh[1][1] and kh[0][1][k] != kh[1][1].get(k)),
                         sha_base=ca["sha"][:16], sha_new=cb["sha"][:16]))
    cnt = {}
    for r in rows:
        cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1
    summ = dict(v=CONTRACT_V, report_only="r703", base=a.base, new=a.new, window_ops_new_result=opsr, types=len(rows), verdicts=cnt,
                contract_same=sum(1 for r in rows if r.get("contract_same")))
    Path(a.out).write_text(json.dumps(dict(summary=summ, rows=rows), indent=1, sort_keys=True))
    if a.tsv:
        _tsv(a.tsv, rows, ["type", "verdict", "contract_same", "own_same", "entries_same", "reset_same", "kit_base", "kit_new",
                           "kit_parts_diff", "sha_base", "sha_new"])
    print("TYPE_CONTRACT credit: %s" % json.dumps(summ, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
