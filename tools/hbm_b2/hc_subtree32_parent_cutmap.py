#!/usr/bin/env python3
"""HBM-BIND-5 (b): exact hub HC central subtree32 parent cut map (opt-in compose input).

The plan hub types q_hub_ne / q_hub_nw carry four hard cores u_hc_Q.u_cen.ot_hbm_hc_subtree32_k
(ot_hbm_hc_subtree32_core, parent_instance u_hc_Q, cut_instance u_cen.ot_hbm_hc_subtree32_k): "five unchanged
registered adder levels; upper two levels and original qhub/client control stay logic" (the cut of
tools/hbm_b2/hc128_qhub_cut.py / hc128_qhub_compact.py on the native W128 ot_hbm_hc_qcen_static).

Input: the flat netlist of an elaboration that DISSOLVES ot_hbm_hc_qhub_static + ot_hbm_hc_qcen_static, so the
qcen adder nodes <hub>.u_cen.g_lvl[l].g_n[i].u_a are leaves.  For subtree k: members = the 31 adder leaves
l = 1..5, i in [k*N/4, (k+1)*N/4) (N = 128 >> l) plus every glue cell whose inputs are all driven by subtree members
(fixpoint; this is the per-node error indicator ne = nv && |err).  Ports use the subtree32 ABI of
hc128_qhub_compact.py: clk, rst_n, valid_in, data[1024] (leaf node i: a = 64*(i-16k)+[0,32), b = +32), sum[32]
(root y), valid_out (root valid_out; kept as the common ABI output even where the parent leaves it unused) and
node_fault[31] (one bit per node, (l, i) order).  Every member terminal on a port net is anchored;
tools/die_plan/bind_compose.py proves terminal equality.  No logic, cycle or constant changes.

usage: hc_subtree32_parent_cutmap.py FLAT.pkl BASE_COMPOSE.json OUT_COMPOSE.json [--hubs hc_NE,hc_NW]
"""
import argparse
import collections
import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))

MODULE = "ot_hbm_hc_subtree32_core"
W = 128


def nodes_of(k):
    out = []
    for l in range(1, 6):
        n = W >> l
        for i in range(k * n // 4, (k + 1) * n // 4):
            out.append((l, i))
    assert len(out) == 31
    return out


def cut(F, byp, drivers, net_cells, topnets, hub, k):
    nodes = nodes_of(k)
    leaves = [f"{hub}.u_cen.g_lvl[{l}].g_n[{i}].u_a" for l, i in nodes]
    for p in leaves:
        if p not in byp or byp[p].kind != "leaf":
            raise SystemExit(f"{p}: missing adder leaf (elaborate with ot_hbm_hc_qhub_static/qcen dissolved)")
    ms = set(leaves)
    owner = {p: j for j, p in enumerate(leaves)}
    glue = []
    pref = hub + ".u_cen."
    cand = [c for c in F.cells if c.path.startswith(pref) and c.kind == "glue"]
    changed = True
    while changed:
        changed = False
        for c in cand:
            if c.path in ms:
                continue
            ins = [b for p, bs in c.ports.items() if c.dirs[p] == "input" for b in bs]
            nets = [b for b in ins if isinstance(b, int)]
            if not nets:
                continue
            srcs = set()
            ok = True
            for b in nets:
                d = drivers.get(b, [])
                if len(d) != 1 or d[0] not in ms:
                    ok = False
                    break
                srcs.add(owner[d[0]])
            if ok and len(srcs) == 1:
                ms.add(c.path)
                owner[c.path] = srcs.pop()
                glue.append(c)
                changed = True
    glue.sort(key=lambda c: (owner[c.path], c.ytype, c.path))
    members = leaves + [c.path for c in glue]
    cells = [byp[p] for p in members]
    net_terms = collections.defaultdict(list)
    for c in cells:
        for p, bs in c.ports.items():
            for i, b in enumerate(bs):
                if isinstance(b, int):
                    net_terms[b].append((c.path, p, i, c.dirs[p]))
    boundary = {b for b in net_terms if (net_cells[b] - ms) or b in topnets}
    lab = {}

    def put(name, idx, b):
        if b in lab and lab[b] != (name, idx) and name not in ("clk", "rst_n", "valid_in"):
            raise SystemExit(f"{hub} subtree{k}: net labelled twice {lab[b]} / {(name, idx)}")
        lab.setdefault(b, (name, idx))

    for j, (l, i) in enumerate(nodes):
        c = byp[leaves[j]]
        for b in c.ports["clk"]:
            put("clk", 0, b)
        for b in c.ports["rst_n"]:
            put("rst_n", 0, b)
        if l == 1:
            for b in c.ports["valid_in"]:
                put("valid_in", 0, b)
            base = 64 * (i - 16 * k)
            for z, b in enumerate(c.ports["a"]):
                put("data", base + z, b)
            for z, b in enumerate(c.ports["b"]):
                put("data", base + 32 + z, b)
    root = byp[leaves[-1]]
    for z, b in enumerate(root.ports["y"]):
        put("sum", z, b)
    for b in root.ports["valid_out"]:
        put("valid_out", 0, b)
    # node_fault: the boundary outputs of the per-node indicator glue, one per node
    nf = collections.defaultdict(list)
    for c in glue:
        for p, bs in c.ports.items():
            if c.dirs[p] == "output":
                for b in bs:
                    if isinstance(b, int) and b in boundary:
                        nf[owner[c.path]].append(b)
    if sorted(nf) != list(range(31)) or any(len(v) != 1 for v in nf.values()):
        raise SystemExit(f"{hub} subtree{k}: node_fault boundary {dict((x, len(v)) for x, v in nf.items())}")
    for j in range(31):
        put("node_fault", j, nf[j][0])
    unl = [b for b in boundary if b not in lab]
    if unl:
        raise SystemExit(f"{hub} subtree{k}: {len(unl)} unlabelled boundary nets, e.g. {net_terms[unl[0]][:3]}")
    groups = collections.defaultdict(dict)
    for b, (n, i) in lab.items():
        if i in groups[n]:
            raise SystemExit(f"{hub} subtree{k}: duplicate {n}[{i}]")
        groups[n][i] = b
    ports = {}
    for n, d in sorted(groups.items()):
        if sorted(d) != list(range(len(d))):
            raise SystemExit(f"{hub} subtree{k}: {n} not contiguous")
        bits, dirs = [], set()
        for i in range(len(d)):
            b = d[i]
            dd = "output" if any(t[3] == "output" for t in net_terms[b]) else "input"
            dirs.add(dd)
            bits.append([dict(member=t[0], port=t[1], bit=t[2]) for t in net_terms[b] if t[3] == dd])
        if len(dirs) != 1:
            raise SystemExit(f"{hub} subtree{k}: mixed directions on {n}")
        ports[n] = dict(dir=dirs.pop(), bits=bits)
    counts = {n: (p["dir"], len(p["bits"])) for n, p in ports.items()}
    want = {"clk": ("input", 1), "data": ("input", 1024), "node_fault": ("output", 31), "rst_n": ("input", 1),
            "sum": ("output", 32), "valid_in": ("input", 1), "valid_out": ("output", 1)}
    if counts != want:
        raise SystemExit(f"{hub} subtree{k}: ABI {counts} != {want}")
    inst = f"{hub}.u_cen.ot_hbm_hc_subtree32_{k}"
    return dict(inst=inst, module=MODULE, members=members, ports=ports), dict(
        inst=inst, members=len(members), leaves=len(leaves), glue=dict(collections.Counter(c.ytype for c in glue)),
        boundary_nets=len(boundary), valid_out_boundary=root.ports["valid_out"][0] in boundary, ports=counts)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("flat")
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--hubs", default="hc_NE,hc_NW")
    a = ap.parse_args(argv)
    F = pickle.load(open(a.flat, "rb"))
    spec = json.loads(Path(a.base).read_text())
    byp = {c.path: c for c in F.cells}
    used = {m for c in spec["cores"] for m in c["members"]}
    topnets = {b for _, bs in F.top_ports.values() for b in bs if isinstance(b, int)}
    net_cells = collections.defaultdict(set)
    drivers = collections.defaultdict(list)
    for c in F.cells:
        for p, bs in c.ports.items():
            for b in bs:
                if isinstance(b, int):
                    net_cells[b].add(c.path)
                    if c.dirs.get(p) == "output":
                        drivers[b].append(c.path)
    for b, d in F.const_drivers.items():
        drivers[b].append("<const>")
    cores, report = [], []
    for hub in a.hubs.split(","):
        for k in range(4):
            core, rep = cut(F, byp, drivers, net_cells, topnets, hub, k)
            if used & set(core["members"]):
                raise SystemExit(f"{core['inst']}: members overlap a base core")
            cores.append(core)
            report.append(rep)
    spec["cores"] = spec["cores"] + cores
    Path(a.out).write_text(json.dumps(spec))
    Path(a.out).with_suffix(".subtree32_report.json").write_text(json.dumps(dict(cores=report), indent=1))
    for r in report:
        print(r["inst"], "members", r["members"], "glue", r["glue"], "boundary", r["boundary_nets"],
              "valid_out_used", r["valid_out_boundary"])


if __name__ == "__main__":
    main()
