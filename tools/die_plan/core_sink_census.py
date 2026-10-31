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
  * HARD clock pins (DIE-KV-51 10-31): a planned sink whose pin is not the register clock pin (an SRAM macro's
    `.../u_s/clk`) is kept iff that instance pin is connected to the clock port in the netlist; it is never renamed,
    and a hard pin on the port that the plan does not list is a FAIL (no implicit sink).  A leaf holding only hard pins
    is not empty.
Result: the slice's sink set equals the netlist census exactly (0 missing, 0 extra) or nothing is written.

  refresh KIT --slice SLICE --netlist N [--report R]   (kit-time, default-on in run_kit_kv.sh after the synth ODB export)
    rebind SLICE against the kit's own synthesized netlist; when every planned sink is already exact (0 renamed,
    0 removed) NOTHING is written (the kit stays byte-identical); otherwise the rebound slice is re-compiled in place
    with core_infra (master_core_infra.tcl, core_infra_plan.json and the plan-tree hooks; impl/PG files untouched)
    and the report is kept.  FAIL -> exit 1, nothing written (the kit stops before floorplan).
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


def port_pins(text, clock_port):
    """{(instance, pin)} of every instance pin connected to `clock_port` (any pin name)."""
    pin = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)\(\s*(\\\S+\s|[^)\s]+)\s*\)")
    out = set()
    for m in INST.finditer(text):
        if m.group(1) in ("module", "input", "output", "wire", "assign", "inout", "reg"):
            continue
        for p in pin.finditer(m.group(3)):
            if _net(p.group(2)) == clock_port:
                out.add((_net(m.group(2)), p.group(1)))
    return out


def unescape(sink):
    return sink.replace("\\[", "[").replace("\\]", "]")


def tcl_name(inst, clock_pin="CLK"):
    return inst.replace("[", "\\[").replace("]", "\\]") + "/" + clock_pin


def plain(sink, clock_pin="CLK"):
    s = sink.replace("\\[", "[").replace("\\]", "]")
    if not s.endswith("/" + clock_pin):
        raise CensusError(f"planned sink {sink!r} is not a {clock_pin} pin")
    return s[:-len(clock_pin) - 1]


def key(inst):
    return SUFFIX.sub("", inst)


def rebind(slice_, actual, clock_pin="CLK", hard_actual=None):
    """hard_actual: {"inst/pin"} non-register clock pins on the port (port_pins); None = legacy (no hard pins)."""
    hard_mode = hard_actual is not None
    hard_actual = set(hard_actual or ())
    tree = slice_.get("core_tree") or {}
    leaves = tree.get("leaves") or []
    if not leaves:
        raise CensusError("slice has no core_tree leaves")
    if tree.get("gates"):
        raise CensusError("gated core_tree: gated sinks are outside this direct-port census")
    planned, hard_planned = {}, {}
    for li, leaf in enumerate(leaves):
        for s in leaf.get("sinks", []):
            if hard_mode and not s.endswith("/" + clock_pin):
                h = unescape(s)
                if h in hard_planned:
                    raise CensusError(f"planned hard clock pin {h} listed twice")
                hard_planned[h] = li
                continue
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
    errors += [f"{h}: planned hard clock pin is not on the clock port in the netlist" for h in sorted(set(hard_planned) - hard_actual)]
    unplanned_hard = sorted(hard_actual - set(hard_planned))
    if hard_planned:   # a plan that lists hard pins must list all of them; a plan without any keeps the legacy behaviour
        errors += [f"{h}: hard clock pin on the port is not in the plan (no implicit sink)" for h in unplanned_hard]
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
            if unescape(s) in hard_planned:
                if unescape(s) in hard_actual:
                    keep.append(s)
                continue
            p = plain(s, clock_pin)
            if p in act:
                keep.append(s)
            elif p in renamed:
                keep.append(tcl_name(renamed[p], clock_pin))
        if not keep:
            errors.append(f"leaf {leaf.get('node')}: no actual sink left (re-plan, not rename)")
        new_leaves.append(dict(leaf, sinks=keep))
    got = [plain(s, clock_pin) for l in new_leaves for s in l["sinks"] if unescape(s) not in hard_planned]
    if not errors and (len(got) != len(set(got)) or set(got) != act):
        errors.append(f"post-rebind census mismatch: planned {len(set(got))} actual {len(act)}")
    report = dict(planned=len(planned), actual=len(act), exact=len(exact), renamed=len(renamed), hard=len(hard_planned), hard_unplanned=len(unplanned_hard),
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


def rebind_netlist(sl, text, clock_port=None, clock_pin="CLK"):
    """rebind against a netlist text: (out | None, report).  Hard (non-register) clock pins on the port are honoured."""
    port = clock_port or (sl.get("core_tree") or {}).get("clock_port") or sl.get("core_clock_port")
    if not port:
        raise CensusError("rebind: no clock port (slice core_tree.clock_port / --clock-port)")
    sinks, other = census(text, port, clock_pin)
    hard = {f"{i}/{p}" for i, p in port_pins(text, port) if p != clock_pin}
    out, rep = rebind(sl, sinks, clock_pin, hard)
    if other:
        rep["errors"].append(f"{len(other)} {clock_pin} pins on nets other than {port}: e.g. {sorted(other)[:3]}")
        rep["verdict"], out = "FAIL", None
    rep.update(clock_port=port, masters=dict(collections.Counter(sinks.values())))
    return out, rep


def stamp(out, rep, netlist):
    out["core_tree"]["sink_census"] = dict(source="tools/die_plan/core_sink_census.py rebind", netlist=Path(netlist).name,
                                          actual=rep["actual"], exact=rep["exact"], renamed=rep["renamed"],
                                          removed=rep["removed"], hard=rep["hard"])
    return out


def refresh(kit, slice_path, netlist, report=None):
    """Kit-time default-on step: rc 0 unchanged / 0 refreshed (files rewritten) / 1 FAIL (nothing written)."""
    kit = Path(kit)
    sl = json.loads(_read(slice_path))
    out, rep = rebind_netlist(sl, _read(netlist))
    rep.update(netlist=str(netlist), slice=str(slice_path))
    changed = out is not None and (rep["renamed"] or rep["removed"])
    rep["action"] = "FAIL" if out is None else ("refreshed" if changed else "unchanged")
    if out is not None and changed:
        here = str(Path(__file__).resolve().parent)
        if here not in sys.path:
            sys.path.insert(0, here)
        import core_infra
        new = stamp(out, rep, netlist)
        if not core_infra.install(kit, new, copy_support=False):
            rep["action"], out = "FAIL", None
            rep["errors"].append("core_infra.install refused the rebound slice (no pushdown)")
        else:
            Path(slice_path).write_text(json.dumps(new, indent=1))
    if report and (out is None or changed):
        Path(report).write_text(json.dumps(rep, indent=1))
    print("CORE_SINK_REFRESH", rep["action"], json.dumps({k: v for k, v in rep.items()
                                                         if k not in ("removed_sinks", "renamed_pairs")})[:2000])
    return 1 if out is None else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("census"); c.add_argument("netlist"); c.add_argument("--clock-port", required=True)
    r = sub.add_parser("rebind"); r.add_argument("slice"); r.add_argument("netlist"); r.add_argument("--out", required=True)
    r.add_argument("--report"); r.add_argument("--clock-port", help="default: the slice core_tree.clock_port")
    for p in (c, r):
        p.add_argument("--clock-pin", default="CLK")
    f = sub.add_parser("refresh"); f.add_argument("kit"); f.add_argument("--slice", required=True)
    f.add_argument("--netlist", required=True); f.add_argument("--report")
    a = ap.parse_args(argv)
    if a.mode == "refresh":
        try:
            return refresh(a.kit, a.slice, a.netlist, a.report)
        except Exception as exc:   # fail closed: any refusal stops the kit before floorplan
            print(f"CORE_SINK_REFRESH FAIL {type(exc).__name__}: {exc}")
            return 1
    if a.mode == "census":
        sinks, other = census(_read(a.netlist), a.clock_port, a.clock_pin)
        print(json.dumps(dict(sinks=len(sinks), other_clock_net=len(other),
                              masters=dict(collections.Counter(sinks.values())))))
        return 0
    sl = json.loads(_read(a.slice))
    try:
        out, rep = rebind_netlist(sl, _read(a.netlist), a.clock_port, a.clock_pin)
    except CensusError as exc:
        raise SystemExit(str(exc))
    rep.update(netlist=str(a.netlist))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    print("CORE_SINK_CENSUS", json.dumps({k: v for k, v in rep.items() if k not in ("removed_sinks", "renamed_pairs")})[:2000])
    if out is None:
        return 1
    stamp(out, rep, a.netlist)
    Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
