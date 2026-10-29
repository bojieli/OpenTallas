#!/usr/bin/env python3
"""HBM-BIND-5 (a): exact SFU ctl parent cut map for the as-built sfucore_* slices (opt-in compose input).

The plan types q_b113 carry the SFU control hard core u_sfucore_Q_ctl (ot_hgi_sfu_core_split3__ctl).  Its split
definition (physical/die_plan/hbm/over_cap_split/ot_hgi_sfu_core_split3.split.json, core "ctl") is
u_core.u_vm + u_core (local) + u_core.u_engine (local) + u_core.u_engine.u_arithmetic (control reg); the operand
store (u_core.u_engine.u_memory.*) is NOT ctl (its pins x_u_core_u_engine_u_memory_* are ctl crossings).

For each sfucore slice: members = every flat cell under the slice that (1) is not already a member of a base compose
core, (2) is not a primitive-split parent, and (3) is not under u_core.u_engine.u_memory.  The cut is the set of
those exact cells, unchanged; ports = the boundary nets (a net with a terminal outside the member set or on a top
port), every member terminal on a port net anchored.  tools/die_plan/bind_compose.py then proves terminal equality
(cell/terminal/net bijection); no logic, cycle or constant changes.  The relay input u_core.u_rst.rst_n_in is the
core's rst_n (the plan wavefront core reset target); clocks are clk; other ports are named
<member rel path>__<port> (sanitized), bits renumbered contiguously in terminal order (mapping in the report).

usage: sfu_ctl_parent_cutmap.py FLAT.pkl BASE_COMPOSE.json MAP.json OUT_COMPOSE.json OUT_MAP.json
  MAP.json/OUT_MAP.json: bind map file; the composed inst <slice>.__cut_ctl is added with the slice's b113
  partition and the plan local name u_sfucore_Q_ctl (as the existing __cut_lane* entries).
"""
import collections
import json
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))

EXCLUDE = ("u_core.u_engine.u_memory.",)
MODULE = "ot_hgi_sfu_core_split3__ctl"
LOCAL = "u_sfucore_Q_ctl"


def sanitize(s):
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s if re.match(r"[A-Za-z_]", s) else "p_" + s


def cut_slice(F, slice_, used, split_parents, net_cells, topnets):
    cand = [c for c in F.cells if c.path.startswith(slice_ + ".")]
    members = [c for c in cand if c.path not in used and c.path not in split_parents
               and not any(c.path[len(slice_) + 1:].startswith(e) for e in EXCLUDE)]
    ms = {c.path for c in members}
    rst = slice_ + ".u_core.u_rst"
    if rst not in ms:
        raise SystemExit(f"{slice_}: reset relay {rst} not a ctl member")
    byp = {c.path: c for c in members}
    rnet = byp[rst].ports["rst_n_in"][0]
    net_terms = collections.defaultdict(list)
    for c in members:
        for p, bs in c.ports.items():
            for i, b in enumerate(bs):
                if isinstance(b, int):
                    net_terms[b].append((c.path, p, i, c.dirs[p], c.kind))
    boundary = [b for b in net_terms if (net_cells[b] - ms) or b in topnets]
    clk_nets = {b for c in members for p, bs in c.ports.items() if p == "clk" for b in bs if isinstance(b, int)}
    if not isinstance(rnet, int) or rnet not in boundary:
        raise SystemExit(f"{slice_}: relay rst_n_in is not a boundary net")

    def key(t):  # leaf before glue, driver before load, then path/port/bit
        return (t[4] != "leaf", t[3] != "output", t[0], t[1], t[2])

    groups = collections.defaultdict(list)
    for b in boundary:
        if b == rnet:
            groups["rst_n"].append((0, b))
            continue
        if b in clk_nets:
            groups["clk"].append((len(groups["clk"]), b))
            continue
        t = sorted(net_terms[b], key=key)[0]
        rel = t[0][len(slice_) + 1:]
        groups[sanitize(rel) + "__" + sanitize(t[1])].append((t[2], b))
    if len(groups["clk"]) != 1:
        raise SystemExit(f"{slice_}: expected one clock net, got {len(groups['clk'])}")
    ports, mapping = {}, {}
    for n, items in sorted(groups.items()):
        items.sort()
        if len({i for i, _ in items}) != len(items):
            raise SystemExit(f"{slice_}: duplicate bit label {n}")
        bits, dirs = [], set()
        for _, b in items:
            # an output port anchors its one member driver; internal member loads keep the internal wire.
            # An input port anchors every member load (no member drives it).
            d = "output" if any(t[3] == "output" for t in net_terms[b]) else "input"
            dirs.add(d)
            bits.append([dict(member=t[0], port=t[1], bit=t[2]) for t in net_terms[b] if t[3] == d])
        if len(dirs) != 1:
            raise SystemExit(f"{slice_}: mixed directions {n}")
        ports[n] = dict(dir=dirs.pop(), bits=bits)
        mapping[n] = [i for i, _ in items]
    names = [c.path for c in members]
    return dict(inst=f"{slice_}.__cut_ctl", module=MODULE, members=names, ports=ports), dict(
        inst=f"{slice_}.__cut_ctl", members=len(names),
        kinds=dict(collections.Counter(c.kind for c in members)),
        leaves=sorted(c.path for c in members if c.kind == "leaf"),
        excluded_operand_store=sum(1 for c in cand if c.path not in used and c.path not in split_parents and c not in members),
        ports={n: [v["dir"], len(v["bits"])] for n, v in ports.items()},
        pins=sum(len(v["bits"]) for v in ports.values()), source_bits=mapping)


def part_of(v):
    """map value: "PART" or [PART, local name]."""
    return v[0] if isinstance(v, list) else v


def main(argv):
    flat, base, mapf, out, outmap = argv
    F = pickle.load(open(flat, "rb"))
    spec = json.loads(Path(base).read_text())
    used = {m for c in spec["cores"] for m in c["members"]}
    split_parents = {s["member"] for s in spec.get("primitive_splits", [])}
    topnets = {b for _, bs in F.top_ports.values() for b in bs if isinstance(b, int)}
    net_cells = collections.defaultdict(set)
    for c in F.cells:
        for bs in c.ports.values():
            for b in bs:
                if isinstance(b, int):
                    net_cells[b].add(c.path)
    M = json.loads(Path(mapf).read_text())
    slices = sorted({c.path.split(".")[0] for c in F.cells if re.match(r"sfucore_[NS][EW]\.", c.path)})
    cores, report = [], []
    for s in slices:
        core, rep = cut_slice(F, s, used, split_parents, net_cells, topnets)
        parts = {part_of(M["parts"].get(m)) for m in core["members"]}
        if len(parts) != 1 or None in parts:
            raise SystemExit(f"{s}: ctl members span partitions {parts}")
        part = parts.pop()
        if core["inst"] in M["parts"]:
            raise SystemExit(f"{core['inst']} already mapped")
        M["parts"][core["inst"]] = [part, LOCAL]
        rep["partition"] = part
        cores.append(core)
        report.append(rep)
    spec["cores"] = spec["cores"] + cores
    Path(out).write_text(json.dumps(spec))
    Path(outmap).write_text(json.dumps(M))
    Path(out).with_suffix(".sfu_ctl_report.json").write_text(json.dumps(dict(slices=slices, ctl_cores=report), indent=1))
    for r in report:
        print(r["inst"], r["partition"], "members", r["members"], r["kinds"], "pins", r["pins"],
              "ports", len(r["ports"]), "excluded_operand_store", r["excluded_operand_store"])


if __name__ == "__main__":
    main(sys.argv[1:])
