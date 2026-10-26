"""Registered ready-AND/fault-OR along the reverse of a local reset tree.

Only branches with actual ring/status sources are emitted. Each source names
its original reset tap; every reverse edge uses the existing legal reset relay
coordinates. The raw wavefront reset is used before START. No missing child is
tied to a value, and no die-top combinational reduction is generated.
"""
import re
from collections import defaultdict


def safe(n):
    return re.sub(r"\W", "_", n)


def raw(n):
    return re.sub(r"^rst_n_t(\d+)$", r"rr_t\1", n)


def build_local(tree, sources, body, *, reach_um=405):
    root = "rst_root_n"
    relays = {r["q"]: r for r in tree["relays"]}
    xy = {root: tree["root"], **{q: r["xy"] for q, r in relays.items()}}
    parent = {q: r["d"] for q, r in relays.items()}
    at, active = defaultdict(list), set()
    max_source_hop = 0
    for src in sources:
        node = f"rst_n_t{src['tap']}"
        if node not in xy:
            raise ValueError(f"collector source {src['name']}: reset tap {node} absent")
        point = src.get("xy_um", xy[node])
        hop = abs(point[0]-xy[node][0])+abs(point[1]-xy[node][1])
        max_source_hop = max(max_source_hop, hop)
        if hop > reach_um + 1e-6:
            raise ValueError(f"collector source {src['name']} -> {node}: {hop:.3f}um exceeds {reach_um}")
        at[node].append(src)
        seen = set()
        while True:
            if node in seen:
                raise ValueError("collector reset graph contains a cycle")
            seen.add(node); active.add(node)
            if node == root:
                break
            if node not in parent:
                raise ValueError(f"collector reset graph has no parent for {node}")
            node = parent[node]
    if not active:
        return dict(rtl=[], instances=[], depth=0, active=False, max_hop_um=0)
    kids = defaultdict(list)
    for node in active - {root}:
        kids[parent[node]].append(node)
    depth = {root: 0}
    todo = [root]
    while todo:
        n = todo.pop()
        for c in kids[n]:
            depth[c] = depth[n] + 1
            todo.append(c)
    lines, insts, hops = [], [], []

    def nets(node):
        return ("cland_up_ready", "cland_up_fault") if node == root else \
            (f"cland_r_{safe(node)}", f"cland_f_{safe(node)}")

    for node in sorted(active, key=lambda n: (-depth[n], n)):
        ready = [s["ready"] for s in at[node]]
        fault = [s["fault"] for s in at[node]]
        for ch in sorted(kids[node]):
            r, f = nets(ch); ready.append(r); fault.append(f)
            distance = abs(xy[ch][0]-xy[node][0])+abs(xy[ch][1]-xy[node][1])
            if distance > reach_um + 1e-6:
                raise ValueError(f"reverse collector {ch}->{node}: {distance:.3f}um exceeds {reach_um}")
            hops.append(dict(src=ch, dst=node, hop_um=distance))
        if not ready:
            raise ValueError(f"collector {node}: empty active branch")
        reset = raw(node)
        # A raw copy of a terminal mission tap is not always needed by the old
        # reset tree. Materialize that existing parent->tap edge locally.
        if node != root and not re.search(r"\bwire\b[^;]*\b"+re.escape(reset)+r"\b", body):
            # A bootstrap tap already carries raw reset under its original name.
            boot = re.search(r"ot_dp_rrelay\s+\w+\s*\([^;]*\.q\("+re.escape(node)+r"\)\);", body)
            if boot:
                reset = node
            else:
                reset = "cland_reset_" + safe(node)
                rp = raw(parent[node])
                if parent[node] != root and not re.search(r"\bwire\b[^;]*\b"+re.escape(rp)+r"\b", body):
                    raise ValueError(f"collector {node}: raw reset parent {rp} absent")
                lines += [f"    wire {reset};",
                          f"    ot_dp_rrelay u_{reset} (.clk(clk), .d({rp}), .q({reset}));"]
                insts.append(dict(name="u_"+reset, module="ot_dp_rrelay", xy_um=xy[node], flops=1,
                                  role="raw pre-START reset copy"))
        rn, fn = nets(node)
        if node != root:
            lines += [f"    wire {rn}, {fn};"]
        name = "u_cland_collect_" + safe(node)
        lines += [f"    ot_dp_landing_collect #(.N({len(ready)})) {name} (",
                  f"        .clk(clk), .rst_n({reset}), .ready_i({{{', '.join(ready)}}}),",
                  f"        .fault_i({{{', '.join(fault)}}}), .ready_o({rn}), .fault_o({fn}));"]
        insts.append(dict(name=name, module="ot_dp_landing_collect", xy_um=xy[node], flops=2,
                          active_inputs=len(ready), raw_reset=reset, depth_to_root=depth[node]+1))
    return dict(rtl=lines, instances=insts, active=True, depth=max(depth.values())+1,
                max_hop_um=max([h["hop_um"] for h in hops]+[max_source_hop]), hops=hops,
                source_count=len(sources), data_cycles_added=0)
