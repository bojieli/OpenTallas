#!/usr/bin/env python3
"""compose_drop_guard.py PREV.json NEW.json [--history OLDER.json ...] [--row NAME=BASE.json:ROW.json ...]
                       [--drop-list FILE] [--max-list N] [--json OUT.json]
                       [--sidecar NEW_SIDECAR.json [--prev-sidecar PREV_SIDECAR.json] [--sidecar-row NAME=BASE_SC:ROW_SC ...]
                        [--sidecar-max N]]

COMPOSE-GUARD-1124 (QC-COMPOSE-GUARD, COORD 11-24): refuse a composed die plan that silently loses what the previous
event's plan (or an adopted private row) carried.  QC C1k lost the QC-OPEN-STA r10 st_a row (3c17478ed804, built on C1g,
never composed into C1h..C1k) and landing_relay_start_copy on two st_a types; four route kits then failed SETUP_TRIAGE.

Findings (each is one plan path, dotted; list elements that are dicts with a unique name/conn/inst/id are keyed by it):
  DROP    PREV has the path and NEW lacks it (or NEW holds null there).  Reported at the highest missing level, so a lost
          partition type is one line, not thousands.
  REVERT  (needs --history) NEW's value equals the value an OLDER plan held, and PREV had changed it: a compose that
          started from a stale base undoes a later row.
  ROW-LOST / ROW-DROP  (needs --row NAME=BASE:ROW) a private row adopted for this event: every path where ROW differs
          from BASE must hold ROW's value in NEW, or some third value (a later row replaced it).  NEW == BASE value is
          ROW-LOST, a missing path ROW-DROP.
Drop list FILE: one fnmatch pattern per line over the dotted path, optional ' # reason'; a matching finding is reported
as INTENDED and does not fail.  '#' lines and blank lines are ignored.  A pattern may be prefixed with the finding kind
('REVERT partition_types.x.clock.*'); without a kind it matches every kind.
Sidecar (QC-GUARD-SIDECAR 11-24, QC-RST-SRCTAP fb9de8c76e09): the strict bind reads the collector source / child reset
nodes (tap index) from the launch sidecar's collector.types[T].local_sources[name] / children[index] {node, tap} and
collector_root_node; landing_place and kit gen read the same fields from the plan's
partition_types[T].clock.landing_contract.collector_local_sources / collector_children / collector_root_node.  A compose
that merges only the plan silently loses a fix that lives in the sidecar (C1m 851b + zz_sidecar_n46r4 9bda: 281 nodes =
560 raw node/tap fields apart; C1n ac1e: 334 / 664).
  SIDECAR-MISMATCH  (--sidecar) per type in both, the reset node a source (by name) / child (by index) names in NEW's plan
          != the sidecar's, compared as the emitter reads it (node, else rst_n_t<tap>), a source/child row present on one
          side only, or collector_root_node.  The raw node/tap field difference count is printed beside it.  The count
          and the first --sidecar-max are printed.  WARN; OT_COMPOSE_DROP=fail makes it rc 1.
  DROP / ROW-LOST / ROW-DROP on 'sidecar:<path>'  (--prev-sidecar / --sidecar-row) the same checks as for the plan, run on
          the sidecars: an entry PREV_SIDECAR carries that NEW_SIDECAR lacks, or a row's sidecar change the composed sidecar
          lost.  rc 1 like plan drops; --drop-list patterns match the 'sidecar:' path.
rc 0 = nothing silent; rc 1 = silent drops/reverts/row losses (listed); rc 2 = usage / unreadable input.
Compose scripts call it after writing NEW and before PRE/bind, for example:
  python3 -I tools/die_plan/compose_drop_guard.py C1j.json C1k.json --history C1g.json C1h.json C1i.json \
      --row r10=C1g.json:plan_c1g_sta10.json --drop-list rows/c1k_drops.txt
plan_gate_pre runs the DROP/REVERT part against --baseline-plan as the COMPOSEDROP class (WARN; OT_COMPOSE_DROP=fail
makes it a FAIL)."""
import argparse
import fnmatch
import hashlib
import json
import os
import sys
from collections import Counter, OrderedDict

ID_KEYS = ("name", "conn", "inst", "id")


def _md5(x):
    return hashlib.md5(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]


def _list_key(v):
    """identity key for a list of dicts (every element has it, values unique hashable), else None"""
    if not v or not all(isinstance(e, dict) for e in v):
        return None
    for k in ID_KEYS:
        vals = [e.get(k) for e in v]
        if all(isinstance(x, (str, int)) for x in vals) and len(set(map(str, vals))) == len(vals):
            return k
    return None


def _children(v):
    """OrderedDict of child label -> value for a dict or an identity-keyed list, else None (a leaf)"""
    if isinstance(v, dict):
        return v
    if isinstance(v, list):
        k = _list_key(v)
        if k:
            return OrderedDict(("[%s=%s]" % (k, e[k]), e) for e in v)
    return None


def show(path):
    """dotted display form of a tuple path; identity-keyed list elements print as [key=value]"""
    out = ""
    for k in path:
        out = k if not out else (out + k if k.startswith("[") and k.endswith("]") and "=" in k else out + "." + k)
    return out


def flatten(v, path=(), out=None):
    """{tuple path: md5} of every leaf plus every container (so a container-level revert is visible too)"""
    if out is None:
        out = {}
    out[path] = _md5(v)
    ch = _children(v)
    if ch:
        for k, x in ch.items():
            flatten(x, path + (str(k),), out)
    return out


def drops(prev, new, path=(), out=None):
    """tuple paths PREV has and NEW lacks (or holds null), at the highest missing level"""
    if out is None:
        out = []
    cp, cn = _children(prev), _children(new)
    if cp is None or cn is None or type(prev) is not type(new):
        return out
    for k, x in cp.items():
        p = path + (str(k),)
        if k not in cn or (cn[k] is None and x is not None):
            out.append(p)
        else:
            drops(x, cn[k], p, out)
    return out


def _innermost(paths):
    """drop every path that is a proper prefix (container) of another path in the set"""
    anc = set()
    for p in paths:
        anc.update(p[:i] for i in range(len(p)))
    return [p for p in paths if p not in anc]


def reverts(prev_fl, new_fl, hist_fls):
    """paths where NEW == an older plan's value, != PREV's (PREV changed it, NEW undid it); innermost only"""
    hits = {}
    for p, nv in new_fl.items():
        pv = prev_fl.get(p)
        if not p or pv is None or pv == nv:
            continue
        for name, hf in hist_fls:
            if hf.get(p) == nv:
                hits[p] = name
                break
    return [(p, hits[p]) for p in _innermost(list(hits))]


def row_check(base, row, new):
    """[(kind, path)] for a private row: every path ROW set vs BASE must be carried (or replaced) in NEW"""
    bf, rf, nf = flatten(base), flatten(row), flatten(new)
    leaf = _innermost([p for p in rf if p and bf.get(p) != rf[p]])   # containers of changed leaves change too
    out = []
    for p in leaf:
        nv = nf.get(p)
        if nv == rf[p]:
            continue
        if nv is None:
            out.append(("ROW-DROP", p))
        elif nv == bf.get(p):
            out.append(("ROW-LOST", p))
    return out


def load_drop_list_lines(lines):
    """[(kind or None, fnmatch pattern)] from drop-list lines ('[KIND ]PATTERN [# reason]')"""
    pats = []
    for line in lines:
        s = line.split(" #", 1)[0].strip()
        if not s or s.startswith("#"):
            continue
        kind, _, pat = s.partition(" ")
        if kind in ("DROP", "REVERT", "ROW-LOST", "ROW-DROP", "SIDECAR-MISMATCH") and pat.strip():
            pats.append((kind, pat.strip()))
        else:
            pats.append((None, s))
    return pats


def load_drop_list(fn):
    if not fn:
        return []
    with open(fn) as f:
        return load_drop_list_lines(f)


def intended(kind, path, pats):
    return any((k is None or k == kind or (k == "DROP" and kind == "ROW-DROP")) and fnmatch.fnmatchcase(path, p)
               for k, p in pats)


def group(path):
    parts = path.replace("[", ".[").split(".")
    return ".".join(parts[:3] if parts[0] in ("partition_types", "sidecar:collector") else parts[:2])


def guard(prev, new, history=(), rows=(), drop_pats=()):
    """[(kind, path, extra)] of every finding; history = [(name, plan)], rows = [(name, base, row)]"""
    found = [("DROP", show(p), "") for p in drops(prev, new)]
    if history:
        pf, nf = flatten(prev), flatten(new)
        found += [("REVERT", show(p), "to " + n) for p, n in reverts(pf, nf, [(n, flatten(h)) for n, h in history])]
    for name, base, row in rows:
        found += [(k, show(p), "row " + name) for k, p in row_check(base, row, new)]
    return [(k, p, x, intended(k, p, drop_pats)) for k, p, x in found]


SC_GROUPS = (("collector_local_sources", "local_sources", "name"), ("collector_children", "children", "index"))
SC_FIELDS = ("node", "tap")
_ABSENT = "<absent>"


def _sc_rows(rows, key):
    """OrderedDict key -> row (sources by name, children by their 'index' field, else list position)"""
    out = OrderedDict()
    for i, r in enumerate(rows or []):
        if isinstance(r, dict):
            out[r.get(key, i) if key == "index" else r.get(key)] = r
    return out


def _eff_node(r):
    """the reset node the emitter uses: 'node' when the row names one, else rst_n_t<tap> (landing_collector.build_local,
    landing_place._source_node, collector_reattach); a tap beside a different node is ignored by all of them (GENBUG D2)"""
    return r.get("node", "rst_n_t%s" % r.get("tap", 0))


def sidecar_mismatches(plan, side, raw=None):
    """[(plan path, plan value, sidecar value)] where the reset node the strict bind takes from the sidecar differs from
    the node kit gen / landing_place take from the plan: per type in both (plan landing_contract + sidecar
    collector.types), sources by name and children by index compared on their EFFECTIVE node (node, else rst_n_t<tap>),
    plus collector_root_node when the sidecar names one.  A row present on one side only is one finding on the row path.
    raw (a Counter, optional) also gets the raw per-field node/tap differences (field present on either side), the
    count hand scripts report (QC-RST-SRCTAP's 692), which includes stale taps the emitter ignores."""
    st = ((side or {}).get("collector") or {}).get("types") or {}
    out = []
    for tn, t in sorted((plan.get("partition_types") or {}).items()):
        lc = ((t or {}).get("clock") or {}).get("landing_contract") if isinstance(t, dict) else None
        if not isinstance(lc, dict) or not isinstance(st.get(tn), dict):
            continue
        row, base = st[tn], f"partition_types.{tn}.clock.landing_contract."
        for pg, sg, k in SC_GROUPS:
            pm, sm = _sc_rows(lc.get(pg), k), _sc_rows(row.get(sg), k)
            for kv in list(pm) + [x for x in sm if x not in pm]:
                p, q = pm.get(kv), sm.get(kv)
                where = f"{base}{pg}[{k}={kv}]"
                if p is None or q is None:
                    out.append((where, _ABSENT if p is None else "row", _ABSENT if q is None else "row"))
                    continue
                if raw is not None:
                    for f in SC_FIELDS:
                        if p.get(f, _ABSENT) != q.get(f, _ABSENT):
                            raw[sg + "." + f] += 1
                if _eff_node(p) != _eff_node(q):
                    out.append((where + ".node", _eff_node(p), _eff_node(q)))
        sr = row.get("collector_root_node")
        if sr is not None and lc.get("collector_root_node", "rst_root_n") != sr:
            out.append((base + "collector_root_node", lc.get("collector_root_node", _ABSENT), sr))
    return out


def sidecar_guard(plan, side, prev_side=None, rows=(), drop_pats=(), raw=None):
    """(mismatch findings, loss findings), each [(kind, path, extra, intended)]; losses use 'sidecar:'-prefixed paths"""
    mm = [("SIDECAR-MISMATCH", p, f"plan={json.dumps(a)} sidecar={json.dumps(b)}")
          for p, a, b in sidecar_mismatches(plan, side, raw)]
    loss = []
    if prev_side is not None:
        loss += [("DROP", "sidecar:" + show(p), "") for p in drops(prev_side, side)]
    for name, b, r in rows:
        loss += [(k, "sidecar:" + show(p), "sidecar row " + name) for k, p in row_check(b, r, side)]
    tag = lambda fs: [(k, p, x, intended(k, p, drop_pats)) for k, p, x in fs]  # noqa: E731
    return tag(mm), tag(loss)


def sidecar_report(mm, n_first=20, level="WARN", raw=None):
    """lines for the SIDECAR-MISMATCH findings: the count by group, the types, the raw field count, and the first n_first"""
    silent = [f for f in mm if not f[3]]
    rawtxt = f"; raw node/tap field diffs {sum(raw.values())} ({', '.join(f'{k} {v}' for k, v in sorted(raw.items()))})" if raw else ""
    if not silent:
        return [f"SIDECAR PASS plan and sidecar name the same collector reset node everywhere ({len(mm)} intended{rawtxt})"]
    def _g(p):
        if p.endswith(".collector_root_node"):
            return "root"
        g = "source" if ".collector_local_sources[" in p else "child"
        return g + ("_node" if p.endswith(".node") else "_row_one_side")
    by = Counter(_g(p) for _, p, _, _ in silent)
    types = {p.split(".")[1] for _, p, _, _ in silent}
    lines = [f"{level} SIDECAR-MISMATCH {len(silent)} collector reset nodes of the plan disagree with the sidecar in {len(types)} "
             f"types ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))}; {len(mm) - len(silent)} intended{rawtxt}): the "
             f"strict bind reads the sidecar, landing_place / kit gen read the plan -- carry the row's sidecar "
             f"(collector_reattach --sidecar)"]
    lines += [f"{level} SIDECAR-MISMATCH {p} {x}" for _, p, x, _ in silent[:n_first]]
    if len(silent) > n_first:
        lines.append(f"{level} SIDECAR-MISMATCH ... {len(silent) - n_first} more (--sidecar-max / --json)")
    return lines


def report(found, max_list=12):
    """(lines, silent findings): one line per (kind, plan path group, note) with a count and up to 3 example paths"""
    lines = []
    silent = [f for f in found if not f[3]]
    for label, sel in (("SILENT", silent), ("INTENDED", [f for f in found if f[3]])):
        c, ex = Counter(), {}
        for k, p, x, _ in sel:
            g = (k, group(p), x)
            c[g] += 1
            ex.setdefault(g, []).append(p) if len(ex.get(g, ())) < 3 else None
        for i, ((k, g, x), n) in enumerate(sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))):
            if i >= max_list:
                lines.append(f"{label} ... {len(c) - max_list} more groups (--max-list / --json)")
                break
            lines.append(f"{label} {k} {g} x{n}{(' (' + x + ')') if x else ''}: " + ", ".join(ex[(k, g, x)]))
    return lines, silent


def plan_drop_pats(new, plan_path=None):
    """P-COMPOSE-DROP (QC-R3-TREERTL 11-27): intended drops a plan carries itself: plan key compose_drop_list (drop-list lines) and
    the file <plan>.drop_list that compose emits next to the plan"""
    pats = []
    v = (new or {}).get("compose_drop_list")
    if isinstance(v, (list, tuple)):
        pats += load_drop_list_lines([str(x) for x in v])
    if plan_path:
        cands = [str(plan_path) + s for s in (".drop_list", ".drop_list.txt")] + [os.path.join(os.path.dirname(str(plan_path)), "compose_drop_list.txt")]
        for fp in cands:
            if os.path.isfile(fp):
                pats += load_drop_list(fp)
    return pats


def reanchored_types(prev, new):
    """types whose reset_tree_anchor was re-derived (its inputs hashes changed) and still carries relays: a different relay set under the
    new inputs is a re-solve, not a loss (QC 77f2: sle_ctl / slw_st_a_v2 / coll_ft relays renamed or re-picked by the new sink bins)"""
    out = {}
    for tn, t in ((new or {}).get("partition_types") or {}).items():
        a = (((prev or {}).get("partition_types") or {}).get(tn) or {}).get("clock", {}).get("reset_tree_anchor") if isinstance(t, dict) else None
        b = (t.get("clock") or {}).get("reset_tree_anchor") if isinstance(t, dict) else None
        if isinstance(a, dict) and isinstance(b, dict) and a.get("inputs") != b.get("inputs") and b.get("relays"):
            out[tn] = {k: (a.get("inputs") or {}).get(k) for k in ("sink_bins", "ft_slots", "taps") if (a.get("inputs") or {}).get(k) != (b.get("inputs") or {}).get(k)}
    return out


def emit_drop_list(prev, new, intended_pats=()):
    """-> (text, intended paths, unnamed paths): the explicit drop list of composing NEW from PREV.  Intended drops are drop-list lines
    ('DROP <path>  # intended'); an unnamed drop is written as a comment ('#UNNAMED DROP <path>') so the list never names it and
    COMPOSEDROP keeps failing until a row or a person names it"""
    named, unnamed, why = [], [], {}
    re_t = reanchored_types(prev, new)
    for k, p, _x, ok in guard(prev, new, drop_pats=list(intended_pats)):
        if k in ("DROP", "ROW-DROP"):
            seg = p.split(".")
            if not ok and len(seg) > 4 and seg[0] == "partition_types" and seg[1] in re_t and ".clock.reset_tree_anchor.relays." in p:
                ok, why[p] = True, "re-anchored: inputs " + "/".join(sorted(re_t[seg[1]])) + " changed"
            (named if ok else unnamed).append(p)
    text = "".join(f"DROP {p}  # {why.get(p, 'intended')}\n" for p in sorted(named)) + "".join(f"#UNNAMED DROP {p}\n" for p in sorted(unnamed))
    return text, sorted(named), sorted(unnamed)


def findings_for_pre(prev, new, drop_list=None, level="WARN", max_list=6, plan_path=None):
    """plan_gate_pre COMPOSEDROP: DROP findings of NEW vs the baseline plan, one line per group"""
    found = guard(prev, new, drop_pats=load_drop_list(drop_list) + plan_drop_pats(new, plan_path))
    lines, silent = report([f for f in found if not f[3]], max_list)
    if not silent:
        return []
    return [f"{level} COMPOSEDROP {len(silent)} plan paths the baseline carries are missing (compose_drop_guard.py; "
            f"--drop-list names intended drops)"] + [f"{level} COMPOSEDROP {ln[len('SILENT '):]}" for ln in lines[:max_list]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prev")
    ap.add_argument("new")
    ap.add_argument("--history", nargs="*", default=[], help="older plans (oldest first) for REVERT detection")
    ap.add_argument("--row", action="append", default=[], help="NAME=BASE.json:ROW.json adopted private row")
    ap.add_argument("--drop-list", help="intended drops, fnmatch patterns over dotted paths")
    ap.add_argument("--max-list", type=int, default=12)
    ap.add_argument("--json", help="write every finding as JSON")
    ap.add_argument("--sidecar", help="NEW's launch sidecar: its collector tap fields must equal NEW's plan fields")
    ap.add_argument("--prev-sidecar", help="PREV's sidecar: entries it carries that --sidecar lacks are DROPs")
    ap.add_argument("--sidecar-row", action="append", default=[], help="NAME=BASE_SC.json:ROW_SC.json a row's sidecar change")
    ap.add_argument("--sidecar-max", type=int, default=20, help="SIDECAR-MISMATCH lines listed (the count is always printed)")
    a = ap.parse_args(argv)
    try:
        ld = lambda p: json.load(open(p))
        prev, new = ld(a.prev), ld(a.new)
        hist = [(p, ld(p)) for p in a.history]
        rows = []
        for r in a.row:
            name, _, br = r.partition("=")
            b, _, rw = br.partition(":")
            if not (name and b and rw):
                raise ValueError("--row wants NAME=BASE.json:ROW.json, got " + r)
            rows.append((name, ld(b), ld(rw)))
        pats = load_drop_list(a.drop_list)
        if (a.prev_sidecar or a.sidecar_row) and not a.sidecar:
            raise ValueError("--prev-sidecar / --sidecar-row need --sidecar NEW_SIDECAR")
        side = ld(a.sidecar) if a.sidecar else None
        if a.sidecar and not ((side.get("collector") or {}).get("types") if isinstance(side, dict) else None):
            raise ValueError(f"--sidecar {a.sidecar} has no collector.types section")
        prev_side = ld(a.prev_sidecar) if a.prev_sidecar else None
        side_rows = []
        for r in a.sidecar_row:
            name, _, br = r.partition("=")
            b, _, rw = br.partition(":")
            if not (name and b and rw):
                raise ValueError("--sidecar-row wants NAME=BASE_SC.json:ROW_SC.json, got " + r)
            side_rows.append((name, ld(b), ld(rw)))
    except (OSError, ValueError) as e:
        print(f"compose_drop_guard: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    found = guard(prev, new, hist, rows, pats)
    mm = []
    if side is not None:
        raw = Counter()
        mm, sloss = sidecar_guard(new, side, prev_side, side_rows, pats, raw)
        found += sloss
    lines, silent = report(found, a.max_list)
    for ln in lines:
        print(ln)
    fail_mm = os.environ.get("OT_COMPOSE_DROP", "").strip().lower() == "fail"
    mm_silent = [f for f in mm if not f[3]]
    if side is not None:
        for ln in sidecar_report(mm, a.sidecar_max, "FAIL" if fail_mm else "WARN", raw):
            print(ln)
    if a.json:
        json.dump([dict(kind=k, path=p, note=x, intended=i) for k, p, x, i in found + mm], open(a.json, "w"), indent=0)
    n_int = len(found) - len(silent)
    if silent or (fail_mm and mm_silent):
        extra = f"; {len(mm_silent)} sidecar tap mismatches (OT_COMPOSE_DROP=fail)" if fail_mm and mm_silent else ""
        print(f"REFUSED {len(silent)} silent losses ({n_int} intended){extra}: name them in --drop-list or restore them")
        return 1
    warn = f"; WARN {len(mm_silent)} sidecar tap mismatches (OT_COMPOSE_DROP=fail refuses them)" if mm_silent else ""
    print(f"PASS 0 silent losses ({n_int} intended){warn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
