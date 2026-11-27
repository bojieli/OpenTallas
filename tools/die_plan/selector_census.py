#!/usr/bin/env python3
"""selector_census.py -- C-SELECTOR-NAME-MISS / C-RELAY-SEAT-KEYMISS census (CLASS-OWNERS-R3 R3-STREETSEL, 11-27).  REPORT-ONLY.

Name-keyed physical directives (relay seat keys, rank lines, selector / prefix / regex lists of the generated kit's Tcl, regexes named
in the plan) match the NAMES Yosys gave the registers, not the names the plan author expected.  Live misses: HEAD East DSEL inferred
48 vs 64 stride, four UNIT write-select regexes without the Yosys genblk2 segment (each matched zero), 11 shadowed rules; QC Coll_s 57
stale TX origins; S81 P2 2,531 SEAT-MISS on the u_bound prefix.  seat_match.py judges plan keys against the bound RTL TEXT; this census
judges every directive of a generated kit against the instance names of the retained synthesized netlist (1_synth_odb.v / 1_synth.v,
the 1_synth -> 3_2 stages keep the flop names), i.e. exactly what the in-flow Tcl will see.

Directive kinds (all read from the kit dir, optionally the plan):
  seat    istations.tcl rs_place_all keys (+ plan relay_sites keys).  Ladder as kit_istations.rs_place_all: exact, '/'=='.', first
          component dropped, rs_norm (image-flat leaf prefix, generate scopes).  Expected = the keys of the same register base
          (key without its last [bit]): flops of that base in the netlist != keys => UNDER (keys without a flop) / OVER (flops
          without a key, e.g. a 64 vs 48 stride).
  rank    rs_rank_line / plan relay_rank_sites: register base without the last [bit]; first alternative that has flops.
  list    top-level `set <var> {tokens}` of kit *.tcl whose var ends _cone/_prefix(es)/_unit(s)/_pattern(s)/_regex(es)/_selector(s)/_launch.
          A token with regex metacharacters is a regexp (re.search on the instance name, '/' and '.' both tried); a plain token is an
          instance-path component (the kit's `(^|[/.])tok[/.]` convention).
  plan    plan strings under keys named *pattern*/*regex*/*selector* (regex metacharacters) -> regexp on instance names.
Verdicts per directive: ZERO (matches nothing), UNDER / OVER (seat groups), SHADOWED (matches nonempty and every match is already matched
by an earlier directive of the same list: it can never act).

  selector_census.py --kit KIT_DIR [--netlist V] [--plan PLAN --type T] [--json OUT] [--limit N]
Always exit 0 (advisory; BLOCKING later).  Library: census(directives, names) -> record; kit_directives(kit); read_netlist(path).
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

CELL = re.compile(r"(?m)^\s*([A-Za-z_]\w*)\s+(\\\S+|[A-Za-z_][\w$.\[\]/]*)\s*\(")
NOT_CELL = {"module", "assign", "wire", "reg", "input", "output", "inout", "function", "if", "for", "generate", "begin", "case",
            "always", "initial", "localparam", "parameter", "logic", "else", "end", "genvar", "integer", "endmodule"}
LIST_VAR = re.compile(r"(_cone|_prefix(?:es)?|_units?|_patterns?|_regex(?:es)?|_selectors?|_launch)$")
META = re.compile(r"[\\^$()|*+?{}]|\[\^|\.\*|\[[0-9a-z]+-")
# names a kit pass CREATES before the seat step (RELAY-GEN K__rs<n> copies, tail copies): absent from the synth netlist by design
DERIVED = re.compile(r"(__\w+|_u_r\d+_\d+)$")
FLOP_SUFFIX = re.compile(r"\$_[A-Za-z0-9_]*$")
TRAIL_BIT = re.compile(r"\[\d+\]$")
BAND_ROW = re.compile(r"(?m)^\s*\{([A-Za-z_][\w.]*) \{(?:-?[\d.]+ ){3}-?[\d.]+\}\s*([^{}\s]*)\}")
SET_LIST = re.compile(r"(?m)^\s*set\s+(\w+)\s+\{((?:[^{}]|\{[^{}]*\})*)\}\s*$")
PLAN_KEY = re.compile(r"pattern|regex|selector", re.I)


def read_netlist(path):
    """[(cell type, instance name without the escape backslash)] of every instance line of a (flat) gate netlist"""
    out = []
    for m in CELL.finditer(Path(path).read_text(errors="replace")):
        typ, nm = m.group(1), m.group(2)
        if typ in NOT_CELL:
            continue
        out.append((typ, nm.lstrip("\\")))
    return out


def rs_norm(n):
    n = n.replace("/", ".")
    n = re.sub(r"^(u_u_)lf[0-9]+_u_", r"\1", n)
    return re.sub(r"\.g_[A-Za-z0-9_]*(\[[0-9]+\])?(?=\.)", "", n)


def _strip1(n):
    return re.sub(r"^[^./]*[./]", "", n)


def flop_forms(base):
    s = base.replace("/", ".")
    return {base, s, _strip1(base), _strip1(s), rs_norm(base), rs_norm(_strip1(base))}


def key_forms(k):
    return {k, k.replace("/", "."), rs_norm(k)}


def _split_tokens(body):
    return re.findall(r"\{[^{}]*\}|\S+", body.strip())


def kit_directives(kit, plan_type=None):
    """directives of one generated kit dir (+ the plan type dict): [{kind, source, key, ...}] in file order"""
    kit = Path(kit)
    d = []
    for n in ("istations.tcl", "istations_post.tcl"):
        f = kit / n
        if not f.is_file():
            continue
        text = f.read_text(errors="replace")
        for ln in text.splitlines():
            if ln.startswith("rs_place_all "):
                for k in re.findall(r"\{([^{}]+)\} \{-?[\d.e+]+ -?[\d.e+]+\}", ln):
                    d.append(dict(kind="seat", source=f"{n}:rs_place_all", key=k))
        for m in re.finditer(r"(?m)^\s*rs_rank_line\s+\{([^{}]*)\}", text):
            ranks = m.group(1).split()
            if ranks:
                d.append(dict(kind="rank", source=f"{n}:rs_rank_line", key=ranks[0], alts=ranks))
    lp = kit / "landing_placement.tcl"
    if lp.is_file():        # landing band table: {<instance prefix> {x0 y0 x1 y1} <tag>}; the hook errors when a prefix maps no cell
        for m in BAND_ROW.finditer(lp.read_text(errors="replace")):
            d.append(dict(kind="list", source="landing_placement.tcl:bands", key=m.group(1), regex=False, tag=m.group(2)))
    for f in sorted(kit.glob("*.tcl")):
        for m in SET_LIST.finditer(f.read_text(errors="replace")):
            var, body = m.group(1), m.group(2)
            if not LIST_VAR.search(var):
                continue
            for tok in _split_tokens(body):
                tok = tok.strip("{}").strip()
                if tok:
                    d.append(dict(kind="list", source=f"{f.name}:{var}", key=tok, regex=bool(META.search(tok))))
    if plan_type:
        for k in (plan_type.get("relay_sites") or {}):
            d.append(dict(kind="seat", source="plan:relay_sites", key=k))
        for k in (plan_type.get("relay_rank_sites") or {}):
            d.append(dict(kind="rank", source="plan:relay_rank_sites", key=k, alts=[k]))

        def walk(x, path, hot):
            if isinstance(x, dict):
                for k, v in x.items():
                    walk(v, path + "/" + str(k), hot or bool(PLAN_KEY.search(str(k))))
                    if hot and META.search(str(k)):
                        d.append(dict(kind="plan", source="plan:" + path, key=str(k), regex=True))
            elif isinstance(x, list):
                for v in x:
                    walk(v, path, hot)
            elif isinstance(x, str) and hot and META.search(x) and len(x) < 400:
                d.append(dict(kind="plan", source="plan:" + path, key=x, regex=True))
        walk({k: v for k, v in plan_type.items() if k not in ("relay_sites", "relay_rank_sites")}, "", False)
    return d


def _rx(pat):
    try:
        return re.compile(pat)
    except re.error:
        return None


def census(directives, cells, limit=12):
    """cells = [(type, name)].  -> record {counts, rows (non-OK), summary per source}; pure, no I/O"""
    names = [n for _, n in cells]
    flops = [FLOP_SUFFIX.sub("", n) for t, n in cells if "DFF" in t]
    fidx = defaultdict(int)          # flop form -> number of flops
    gidx = defaultdict(int)          # flop form without trailing [bit] -> number of flops
    for b in flops:
        forms = flop_forms(b)
        for f in forms:
            fidx[f] += 1
        for g in {TRAIL_BIT.sub("", f) for f in forms if TRAIL_BIT.search(f)}:
            gidx[g] += 1
    pidx = set()                     # every instance path above a flop (a seat key may name a module instance, not a register)
    for b in flops:
        for f in flop_forms(b):
            for m in re.finditer(r"[./]", f):
                pidx.add(f[:m.start()])
    rows, groups, seen = [], defaultdict(list), defaultdict(list)
    for dv in directives:
        k = dv["key"]
        if dv["kind"] == "seat":
            hit = int(any(f in fidx or f in pidx for f in key_forms(k)))
            if not hit and DERIVED.search(TRAIL_BIT.sub("", k)):
                rows.append(dict(dv, verdict="DERIVED", matches=0))     # reported, not a miss
                continue
            g = TRAIL_BIT.sub("", k.replace("/", "."))
            groups[(dv["source"], g)].append(hit)
            if not hit:
                rows.append(dict(dv, verdict="ZERO", matches=0))
        elif dv["kind"] == "rank":
            n = max((max([gidx.get(f, 0) for f in key_forms(a)] or [0]) for a in dv.get("alts", [k])), default=0)
            if not n:
                rows.append(dict(dv, verdict="ZERO", matches=0))
        else:
            if dv.get("regex"):
                rx = _rx(k)
                if rx is None:
                    rows.append(dict(dv, verdict="BAD-REGEX", matches=0))
                    continue
                m = {i for i, nm in enumerate(names) if rx.search(nm) or rx.search(nm.replace("/", "."))}
            else:
                rx = re.compile(r"(^|[/.])%s([/.]|$)" % re.escape(k))
                m = {i for i, nm in enumerate(names) if rx.search(nm)}
            prev = seen[dv["source"]]
            union = set().union(*prev) if prev else set()
            if not m:
                opt = "optional" in str(dv.get("tag", "")) or dv.get("tag") == "origin-home"     # the hook skips these on no match
                rows.append(dict(dv, verdict="ZERO-OPTIONAL" if opt else "ZERO", matches=0))
            elif prev and m <= union:
                rows.append(dict(dv, verdict="SHADOWED", matches=len(m)))
            prev.append(m)
    for (src, g), hits in groups.items():
        keys = len(hits)
        fl = max([gidx.get(f, 0) for f in key_forms(g)] or [0])
        if fl and fl != keys:
            rows.append(dict(kind="seat-group", source=src, key=g, verdict="OVER" if fl > keys else "UNDER", keys=keys, flops=fl, matches=sum(hits)))
    c = Counter((r["kind"], r["verdict"]) for r in rows)
    tot = Counter(dv["kind"] for dv in directives)
    by_src = defaultdict(Counter)
    for r in rows:
        by_src[r["source"]][r["verdict"]] += 1
    return dict(schema="opentallas.selector_census.v1", directives=dict(tot), cells=len(cells), flops=len(flops),
                counts={f"{a}:{b}": n for (a, b), n in sorted(c.items())}, by_source={s: dict(v) for s, v in by_src.items()},
                rows=rows[:limit * 50], n_rows=len(rows), report_only=True)


def lines(rec, limit=12):
    out = []
    z = sum(n for k, n in rec["counts"].items() if k.endswith(":ZERO"))
    dr = sum(n for k, n in rec["counts"].items() if k.endswith(":DERIVED"))
    out.append(f"SELECTOR-CENSUS WARN {z} zero-match ({dr} more derived-by-kit names not judged), {sum(n for k, n in rec['counts'].items() if k.endswith(':SHADOWED'))} shadowed, "
               f"{sum(n for k, n in rec['counts'].items() if k.endswith(':UNDER') or k.endswith(':OVER'))} under/over seat groups of "
               f"{sum(rec['directives'].values())} directives ({rec['directives']}) on {rec['cells']} cells / {rec['flops']} flops; REPORT ONLY")
    shown = 0
    for src, v in sorted(rec["by_source"].items(), key=lambda kv: -sum(kv[1].values())):
        out.append(f"  {src}: {dict(v)}")
        shown += 1
        if shown >= limit:
            break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", required=True)
    ap.add_argument("--netlist")
    ap.add_argument("--plan")
    ap.add_argument("--type")
    ap.add_argument("--json")
    ap.add_argument("--limit", type=int, default=12)
    a = ap.parse_args(argv)
    try:
        kit = Path(a.kit)
        nl = Path(a.netlist) if a.netlist else next((p for p in (kit / "1_synth_odb.v", kit / "1_synth.v") if p.is_file()), None)
        if nl is None:
            print("SELECTOR-CENSUS WARN not checked: no retained synthesized netlist (1_synth_odb.v / 1_synth.v) in the kit")
            return 0
        pt = None
        if a.plan and a.type:
            pt = (json.loads(Path(a.plan).read_text()).get("partition_types") or {}).get(a.type)
        rec = census(kit_directives(kit, pt), read_netlist(nl), a.limit)
        rec["kit"], rec["netlist"], rec["type"] = str(kit), str(nl), a.type
        if a.json:
            Path(a.json).write_text(json.dumps(rec, indent=1) + "\n")
        print("\n".join(lines(rec, a.limit)))
    except Exception as e:  # noqa: BLE001 advisory: never fails a caller
        print(f"SELECTOR-CENSUS WARN not checked: {type(e).__name__}: {str(e)[:160]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
