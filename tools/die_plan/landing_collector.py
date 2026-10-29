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


def raw_reset(tree, node, body):
    """Resolve a pre-START consumer using its exact existing reset-tree edge."""
    reset = raw(node)
    declared = lambda n: re.search(r"\bwire\b[^;]*\b"+re.escape(n)+r"\b", body)
    if node == "rst_root_n" or declared(reset):
        return reset, [], []
    boot = re.search(r"ot_dp_rrelay(?:_drive)?\s+\w+\s*\([^;]*\.q\("+re.escape(node)+r"\)\);", body)
    if boot:
        return node, [], []
    reset = "cland_reset_" + safe(node)
    if declared(reset):
        return reset, [], []
    relays = {r["q"]: r for r in tree["relays"]}
    if node not in relays:
        raise ValueError(f"collector {node}: reset-tree relay absent")
    edge = relays[node]
    parent = raw(edge["d"])
    if edge["d"] != "rst_root_n" and not declared(parent):
        raise ValueError(f"collector {node}: raw reset parent {parent} absent")
    lines = [f"    wire {reset};",
             f"    ot_dp_rrelay u_{reset} (.clk(clk), .d({parent}), .q({reset}));"]
    inst = dict(name="u_"+reset, module="ot_dp_rrelay", xy_um=edge["xy"],
                flops=1, role="raw pre-START reset copy")
    return reset, lines, [inst]


def build_local(tree, sources, body, *, reach_um=405, root_node="rst_root_n"):
    reset_root="rst_root_n";root=root_node
    relays = {r["q"]: r for r in tree["relays"]}
    xy = {reset_root: tree["root"], **{q: r["xy"] for q, r in relays.items()}}
    reset_parent = {q: r["d"] for q, r in relays.items()}
    if root not in xy:raise ValueError(f"collector root {root} is not a real reset relay site")
    adj=defaultdict(list)
    for q,d in reset_parent.items():adj[q].append(d);adj[d].append(q)
    parent={root:None};queue=[root]
    while queue:
        n=queue.pop()
        for other in adj[n]:
            if other in parent:continue
            parent[other]=n;queue.append(other)
    at, active = defaultdict(list), set()
    max_source_hop = 0
    for src in sources:
        node = src.get("node",f"rst_n_t{src.get('tap',0)}")
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
        reset, added, copies = raw_reset(tree, node, body+"\n"+"\n".join(lines))
        lines.extend(added)
        insts.extend(copies)
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


def build_hard_chain(tree, sources, *, reach_um=405):
    """Registered ready/fault chain in a HARD partition's soft wrapper.

    tree = clock_landing_plan._hard_tree: root rst_root_n at the delivered
    reset entry, relays cland_h* (<= reach) toward the landing ring. Every stage
    is an ot_dp_landing_collect on the wrapper's delivered reset rst_n (the reset
    its own stations use). Boot-only; zero data cycles. No child is tied.
    """
    relays={r["q"]:r for r in tree["relays"]}
    xy={"rst_root_n":tree["root"],**{q:r["xy"] for q,r in relays.items()}}
    leaf=tree["leaf_node"];lines,insts,hops=[],[],[]
    if not sources:raise ValueError("hard collector without a landing source")
    for src in sources:
        if src.get("node",leaf)!=leaf:raise ValueError(f"hard collector source {src['name']} not at the chain leaf")
        p=src.get("xy_um",xy[leaf]);hop=abs(p[0]-xy[leaf][0])+abs(p[1]-xy[leaf][1])
        if hop>reach_um+1e-6:raise ValueError(f"hard collector source {src['name']}: {hop:.3f}um exceeds {reach_um}")
        hops.append(dict(src=src["name"],dst=leaf,hop_um=hop))
    chain=[leaf]
    while chain[-1]!="rst_root_n":chain.append(relays[chain[-1]]["d"])
    def nets(n):
        return ("cland_up_ready","cland_up_fault") if n=="rst_root_n" else (f"cland_r_{safe(n)}",f"cland_f_{safe(n)}")
    for i,n in enumerate(chain):
        if i==0:ready=[s["ready"] for s in sources];fault=[s["fault"] for s in sources]
        else:
            r,f=nets(chain[i-1]);ready,fault=[r],[f]
            d=abs(xy[chain[i-1]][0]-xy[n][0])+abs(xy[chain[i-1]][1]-xy[n][1])
            if d>reach_um+1e-6:raise ValueError(f"hard collector {chain[i-1]}->{n}: {d:.3f}um exceeds {reach_um}")
            hops.append(dict(src=chain[i-1],dst=n,hop_um=d))
        rn,fn=nets(n)
        if n!="rst_root_n":lines.append(f"    wire {rn}, {fn};")
        name="u_cland_collect_"+safe(n)
        lines += [f"    ot_dp_landing_collect #(.N({len(ready)})) {name} (",
                  f"        .clk(clk), .rst_n(rst_n), .ready_i({{{', '.join(ready)}}}),",
                  f"        .fault_i({{{', '.join(fault)}}}), .ready_o({rn}), .fault_o({fn}));"]
        insts.append(dict(name=name,module="ot_dp_landing_collect",xy_um=xy[n],flops=2,active_inputs=len(ready),
                          raw_reset="rst_n (delivered, hard wrapper)",depth_to_root=len(chain)-i))
    return dict(rtl=lines,instances=insts,active=True,depth=len(chain),max_hop_um=max(h["hop_um"] for h in hops),
                hops=hops,source_count=len(sources),data_cycles_added=0,hard_wrapper=True)
