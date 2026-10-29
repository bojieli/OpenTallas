#!/usr/bin/env python3
"""Exact clock-sink census of a kit's OWN synthesized netlist, and re-derivation of a planned core_tree's leaf sinks
from it (DIE-S81-25 10-29; METHODOLOGY 12.2a1 / 12.8: sink sets come from the plan, the plan from the current source).

Why: a core_tree slice names every clock sink by its mapped instance (`<register bit>$_<yosys cell type>_/CLK`).  When
the slice census was taken from ANOTHER build of the core (different defines / RTL), the yosys cell-type suffix of a
register bit can differ ($_SDFF_PN0_ -> $_DFF_P_) and registers that the current synthesis removed (merged / constant,
proved by the kit LEC) are still listed; core_infra then stops at OT_CORE_INFRA_SINK_INSTANCE.  The fix is to take the
sink set from the netlist of the same run, not to skip or fuzzy-match at run time.

  census  NETLIST --clock-port P                 every instance whose clock pin (CLK) is driven by port P
  rebind  SLICE NETLIST --out SLICE2 [--report R]

rebind keeps each planned leaf's membership by the register's SOURCE identity: the instance name without the trailing
yosys cell-type suffix `$_<TYPE>_` (the RTL register bit; one flop per bit).  It is exact, never fuzzy:
  * an actual sink whose exact name is planned stays where it is;
  * otherwise its source key must name exactly ONE planned sink and that planned sink exactly one actual sink
    (bijection) -> renamed in place;
  * an actual sink with no planned source key, or any ambiguous key, is a FAIL (an unplanned flop is never left to luck);
  * a planned sink whose source key has no actual sink is reported as REMOVED by synthesis (the kit LEC must account
    for it); a leaf left empty is a FAIL (the tree would need a re-plan, not a rename);
  * a clock pin on any other net (gated / already buffered) is a FAIL here (this tool handles the direct-port census).
Result: the slice's sink set equals the netlist census exactly (0 missing, 0 extra) or nothing is written.
"""
import argparse, collections, gzip, json, re, sys
from pathlib import Path

SUFFIX = re.compile(r"\$_[A-Z0-9_]+_\Z")
INST = re.compile(r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)[ \t]*\((.*?)\);", re.M | re.S)


class CensusError(ValueError):
    pass


def _net(s):
    s = s.strip()
    return s[1:].strip() if s.startswith("\\") else s


def census(text, clock_port, clock_pin="CLK"):
    """{instance: master} of every instance whose `clock_pin` connects to `clock_port`; (sinks, other) where other =
    clock pins on any other net."""
    pin = re.compile(r"\.%s\(\s*(\\\S+\s|[^)\s]+)\s*\)" % re.escape(clock_pin))
    sinks, other = {}, {}
    for m in INST.finditer(text):
        if m.group(1) in ("module", "input", "output", "wire", "assign", "inout", "reg"):
            continue
        p = pin.search(m.group(3))
        if not p:
            continue
        inst = _net(m.group(2))
        (sinks if _net(p.group(1)) == clock_port else other)[inst] = m.group(1)
    return sinks, other


def tcl_name(inst, clock_pin="CLK"):
    return inst.replace("[", "\\[").replace("]", "\\]") + "/" + clock_pin


def plain(sink, clock_pin="CLK"):
    s = sink.replace("\\[", "[").replace("\\]", "]")
    if not s.endswith("/" + clock_pin):
        raise CensusError(f"planned sink {sink!r} is not a {clock_pin} pin")
    return s[:-len(clock_pin) - 1]


def key(inst):
    return SUFFIX.sub("", inst)


def rebind(slice_, actual, clock_pin="CLK"):
    tree = slice_.get("core_tree") or {}
    leaves = tree.get("leaves") or []
    if not leaves:
        raise CensusError("slice has no core_tree leaves")
    if tree.get("gates"):
        raise CensusError("gated core_tree: gated sinks are outside this direct-port census")
    planned = {}
    for li, leaf in enumerate(leaves):
        for s in leaf.get("sinks", []):
            p = plain(s, clock_pin)
            if p in planned:
                raise CensusError(f"planned sink {p} listed twice")
            planned[p] = li
    act = set(actual)
    pk = collections.defaultdict(list); ak = collections.defaultdict(list)
    for p in planned:
        pk[key(p)].append(p)
    for a in act:
        ak[key(a)].append(a)
    exact = act & set(planned)
    renamed, errors = {}, []
    for a in sorted(act - exact):
        k = key(a)
        cand = [p for p in pk.get(k, []) if p not in act]
        if len(ak[k]) != 1 or len(pk.get(k, [])) != 1 or len(cand) != 1:
            errors.append(f"{a}: source key {k} planned {len(pk.get(k, []))} / actual {len(ak[k])} (no exact bijection)")
            continue
        renamed[cand[0]] = a
    removed = sorted(p for p in planned if p not in act and p not in renamed)
    removed_live = [p for p in removed if key(p) in ak]
    if removed_live:
        errors += [f"{p}: planned sink's source key is still an actual flop under another name" for p in removed_live]
    new_leaves = []
    for li, leaf in enumerate(leaves):
        keep = []
        for s in leaf.get("sinks", []):
            p = plain(s, clock_pin)
            if p in act:
                keep.append(s)
            elif p in renamed:
                keep.append(tcl_name(renamed[p], clock_pin))
        if not keep:
            errors.append(f"leaf {leaf.get('node')}: no actual sink left (re-plan, not rename)")
        new_leaves.append(dict(leaf, sinks=keep))
    got = [plain(s, clock_pin) for l in new_leaves for s in l["sinks"]]
    if not errors and (len(got) != len(set(got)) or set(got) != act):
        errors.append(f"post-rebind census mismatch: planned {len(set(got))} actual {len(act)}")
    report = dict(planned=len(planned), actual=len(act), exact=len(exact), renamed=len(renamed),
                  removed=len(removed), removed_sinks=removed,
                  renamed_pairs=sorted([p, a] for p, a in renamed.items()),
                  missing=len(act - set(got)), extra=len(set(got) - act), errors=errors,
                  verdict="FAIL" if errors else "PASS")
    if errors:
        return None, report
    out = json.loads(json.dumps(slice_))
    out["core_tree"]["leaves"] = new_leaves
    return out, report


def _read(path):
    b = Path(path).read_bytes()
    return (gzip.decompress(b) if str(path).endswith(".gz") else b).decode()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("census"); c.add_argument("netlist"); c.add_argument("--clock-port", required=True)
    r = sub.add_parser("rebind"); r.add_argument("slice"); r.add_argument("netlist"); r.add_argument("--out", required=True)
    r.add_argument("--report"); r.add_argument("--clock-port", help="default: the slice core_tree.clock_port")
    for p in (c, r):
        p.add_argument("--clock-pin", default="CLK")
    a = ap.parse_args(argv)
    if a.mode == "census":
        sinks, other = census(_read(a.netlist), a.clock_port, a.clock_pin)
        print(json.dumps(dict(sinks=len(sinks), other_clock_net=len(other),
                              masters=dict(collections.Counter(sinks.values())))))
        return 0
    sl = json.loads(_read(a.slice))
    port = a.clock_port or (sl.get("core_tree") or {}).get("clock_port") or sl.get("core_clock_port")
    if not port:
        raise SystemExit("rebind: no clock port (slice core_tree.clock_port / --clock-port)")
    sinks, other = census(_read(a.netlist), port, a.clock_pin)
    out, rep = rebind(sl, sinks, a.clock_pin)
    if other:
        rep["errors"].append(f"{len(other)} {a.clock_pin} pins on nets other than {port}: e.g. {sorted(other)[:3]}")
        rep["verdict"], out = "FAIL", None
    rep.update(netlist=str(a.netlist), clock_port=port, masters=dict(collections.Counter(sinks.values())))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    print("CORE_SINK_CENSUS", json.dumps({k: v for k, v in rep.items() if k not in ("removed_sinks", "renamed_pairs")})[:2000])
    if out is None:
        return 1
    out["core_tree"]["sink_census"] = dict(source="tools/die_plan/core_sink_census.py rebind", netlist=Path(a.netlist).name,
                                          actual=rep["actual"], exact=rep["exact"], renamed=rep["renamed"],
                                          removed=rep["removed"])
    Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
