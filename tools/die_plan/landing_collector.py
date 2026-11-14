"""Registered ready-AND/fault-OR along the reverse of a local reset tree.

Only branches with actual ring/status sources are emitted. Each source names
its original reset tap; every reverse edge uses the existing legal reset relay
coordinates. The raw wavefront reset is used before START. No missing child is
tied to a value, and no die-top combinational reduction is generated.
"""
import re
import sys
from collections import defaultdict


def _reach_info(msg):
    """LIMIT-BIND-1 11-14 (OWNER: remove the conservative limits): a collector hop over the reach is reported, not raised;
    routed timing judges the wire."""
    print("COLLECTOR-REACH-INFO " + msg + " (info: not blocking)", file=sys.stderr)


def safe(n):
    return re.sub(r"\W", "_", n)


def effective_tree(ptype, table_tree):
    """The collector tree a type's RTL collectors, their verify and landing_place.tcl ALL walk: the plan
    landing_contract.collector_tree (the tree the reset relays and the placement groups use) when it is a soft relay
    tree, else the landing table's copy.  S81-OTHERFAIL-1 11-07: col_h10_r2__t1__cl99efd374 had a stale table tree
    (t28->60->59->58->50->35) while the plan, the relays and the placement used t28->57->56->55->45->35, so place
    stopped on 'OT_CLAND no mapped cells found under u_cland_collect_rst_rl_45'.  One tree, by construction."""
    ctree = (((ptype or {}).get("clock") or {}).get("landing_contract") or {}).get("collector_tree")
    if (isinstance(ctree, dict) and ctree.get("relays") and not ctree.get("hard") and isinstance(table_tree, dict)
            and not table_tree.get("hard")):
        return ctree
    return table_tree


def raw(n):
    return re.sub(r"^rst_n_t(\d+)$", r"rr_t\1", n)


BODY_RELAY = re.compile(r"ot_dp_r(?:relay|gate)\w*\s+\w+\s*\([^;]*?\.q\((\w+)\)\);[ \t]*//[^\n]*?"
                        r"(?:\bdepth (\d+) )?@ \(([-\d.]+), ([-\d.]+)\)")
SITE_TOL_UM = 1.0     # the bound body states relay sites at 0.1 um (0.5 um in the older ':.0f' form)


def body_sites(body):
    """{net: (depth or None, (x, y))} of the bound reset relays whose site the body states ('// ... depth D @ (x, y)')"""
    return {m.group(1): (int(m.group(2)) if m.group(2) else None, (float(m.group(3)), float(m.group(4))))
            for m in BODY_RELAY.finditer(body)}


def same_relay(edge, site):
    """True when the bound relay at `site` (body_sites value) is the collector-tree relay `edge` itself: same site and
    depth.  No stated site -> True (nothing to compare; the name is the only identity, the old rule)."""
    if edge is None or site is None:
        return True
    depth, (x, y) = site
    if depth is not None and edge.get("depth") is not None and int(edge["depth"]) != depth:
        return False
    return abs(float(edge["xy"][0]) - x) + abs(float(edge["xy"][1]) - y) <= SITE_TOL_UM


def raw_reset(tree, node, body, sites=None):
    """Resolve a pre-START consumer using its exact existing reset-tree edge.

    QC-TYPES-10/CLAND 11-08 (class M, STALE COLLECTOR TREE): the collector tree (plan landing_contract / sidecar) and
    the reset tree the bind emits (RT.for_type) can be different trees whose relays share NAMES (slw_fe_v1 30-tap
    collector tree vs the 92-tap bound tree: u_cland_reset_rst_n_t29 at (332,1322) took .d(rst_rl_45), the bound
    tap-7 pad 946 um away, G2 TT -269.56).  A bound wire is reused only when its relay is this tree's relay (same
    site and depth, `same_relay`); otherwise the consumer gets the copy chain along the collector tree up to a
    relay the two trees share or the root: cycle-equal, every hop a legal collector-tree edge.  Trees that agree
    reuse exactly as before."""
    sites = body_sites(body) if sites is None else sites
    relays = {r["q"]: r for r in tree["relays"]}
    here = lambda net, n: same_relay(relays.get(n), sites.get(net))
    reset = raw(node)
    declared = lambda n: re.search(r"\bwire\b[^;]*\b"+re.escape(n)+r"\b", body)
    # DIE-KV-32 10-29 (face_guard 'shared' hub_Ei rst_o_0): a raw tap that is the registered reset OUT of the
    # wrapper (reset_tree `assign rst_o_k = rr_tN`) is that port's face flop; a pre-START consumer takes its own
    # copy at the same parent/depth below (cycle-equal), never the face flop's Q.
    face = re.search(r"\bassign\s+rst_o_\d+\s*=\s*" + re.escape(reset) + r"\s*;", body)
    if node == "rst_root_n" or (declared(reset) and not face and here(reset, node)):
        return reset, [], []
    boot = re.search(r"ot_dp_rrelay(?:_drive|_nl)?\s+\w+\s*\([^;]*\.q\("+re.escape(node)+r"\)\);", body)
    if boot and here(node, node):
        return node, [], []
    reset = "cland_reset_" + safe(node)
    if declared(reset):
        return reset, [], []
    if node not in relays:
        raise ValueError(f"collector {node}: reset-tree relay absent")
    edge = relays[node]
    parent = raw(edge["d"])
    up_lines, up_insts = [], []
    if edge["d"] != "rst_root_n" and not (declared(parent) and here(parent, edge["d"])):
        # DIE-S81-62 11-05 (S81 cem drop, iq_C/kv512_C rst_rl_197/rst_rl_41): the wrapper no longer emits a pure wire
        # relay whose other consumers left with u_em; copy it too at its own relay site (same depth, cycle-equal),
        # recursively up to a declared ancestor. A parent that is no reset-tree relay still fails closed.
        # CLAND 11-08: the same when the declared wire of that name is another tree's relay (another site/depth).
        if edge["d"] not in relays:
            raise ValueError(f"collector {node}: raw reset parent {parent} absent")
        parent, up_lines, up_insts = raw_reset(tree, edge["d"], body, sites)
    lines = up_lines + [f"    wire {reset};",
             f"    ot_dp_rrelay u_{reset} (.clk(clk), .d({parent}), .q({reset}));"]
    inst = dict(name="u_"+reset, module="ot_dp_rrelay", xy_um=edge["xy"],
                flops=1, role="raw pre-START reset copy")
    return reset, lines, up_insts + [inst]


def check_local_resets(tree, text, sites=None):
    """Fail closed (QC-TYPES-10/CLAND 11-08): every collector-tree reset in `text` -- copy u_cland_reset_<n> and
    collector u_cland_collect_<n> -- is driven by the collector tree's own relay: a copy's d is its tree parent (the
    parent's copy, or the parent's bound wire only where that bound relay is the tree's relay: same site and depth);
    a collector's rst_n is node n's copy, n's own same-site bound wire, or rst_root_n at the root.  A name that
    coincides with another tree's relay (another site) raises.  -> number of resets checked."""
    sites = body_sites(text) if sites is None else sites
    relays = {r["q"]: r for r in tree["relays"]}
    by_safe = {safe(q): q for q in relays}

    def owned(net, n):          # net carries node n's reset at n's collector-tree site
        if n == "rst_root_n":
            return net == "rst_root_n"
        if net == "cland_reset_" + safe(n):
            return True
        return net in (n, raw(n)) and same_relay(relays.get(n), sites.get(net))
    count = 0
    for m in re.finditer(r"ot_dp_rrelay\s+u_cland_reset_(\w+)\s*\(\.clk\(clk\),\s*\.d\(([^)]+)\),", text):
        n = by_safe.get(m.group(1))
        if n is None:
            continue                     # not a collector-tree copy (a landing ring / face copy)
        count += 1
        if not owned(m.group(2).strip(), relays[n]["d"]):
            raise ValueError(f"collector reset copy u_cland_reset_{m.group(1)}: d {m.group(2)} is not its collector-tree "
                             f"parent {relays[n]['d']} at {tuple(relays.get(relays[n]['d'], {}).get('xy', tree.get('root', ())))}")
    for m in re.finditer(r"ot_dp_landing_collect\b[^;]*?\bu_cland_collect_(\w+)\s*\([^;]*?\.rst_n\(([^)]+)\)", text):
        n = "rst_root_n" if m.group(1) == "rst_root_n" else by_safe.get(m.group(1))
        if n is None:
            continue
        count += 1
        if not owned(m.group(2).strip(), n):
            raise ValueError(f"collector u_cland_collect_{m.group(1)}: rst_n {m.group(2)} is not node {n}'s own reset at "
                             f"its collector-tree site")
    return count


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
        hop = max(abs(p[0]-xy[node][0])+abs(p[1]-xy[node][1])
                  for p in src.get("status_pins_xy_um", [point]))
        max_source_hop = max(max_source_hop, hop)
        if hop > reach_um + 1e-6:
            _reach_info(f"collector source {src['name']} -> {node}: {hop:.3f}um exceeds {reach_um}")
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
    sites = body_sites(body)     # the bound relays' stated sites; the copies added below state none

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
                _reach_info(f"reverse collector {ch}->{node}: {distance:.3f}um exceeds {reach_um}")
            hops.append(dict(src=ch, dst=node, hop_um=distance))
        if not ready:
            raise ValueError(f"collector {node}: empty active branch")
        reset, added, copies = raw_reset(tree, node, body+"\n"+"\n".join(lines), sites)
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
    check_local_resets(tree, body+"\n"+"\n".join(lines), sites)
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
        if hop>reach_um+1e-6:_reach_info(f"hard collector source {src['name']}: {hop:.3f}um exceeds {reach_um}")
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
            if d>reach_um+1e-6:_reach_info(f"hard collector {chain[i-1]}->{n}: {d:.3f}um exceeds {reach_um}")
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


def reattach_sources(info, tree, *, status_points=None, reach_um=405):
    """Reattach status sources after reset sites move, preserving their relative depth.

    The source and each registered collector edge retain the same cycle count
    when the old/new tree depth is equal. A depth change is explicit in the
    report. Actual hard-child ready/fault points may replace the old soft-band
    estimate; every point must reach the selected real reset relay.
    """
    import copy
    status_points = status_points or {}
    old = info["tree"]
    nodes = lambda t: {"rst_root_n": dict(xy=t["root"], depth=0),
                       **{r["q"]: r for r in t["relays"]}}
    before, after = nodes(old), nodes(tree)
    root = info.get("collector_root_node", "rst_root_n")
    if root != "rst_root_n":
        raise ValueError("rerooted collector reattachment requires an explicit parent seam event")
    if root not in after or tuple(before[root]["xy"]) != tuple(after[root]["xy"]):
        raise ValueError("collector root moved; requires an explicit parent seam event")
    added = tree["depth"] - old["depth"]
    rows = []
    for group in ("local_sources", "children"):
        for index, src in enumerate(info[group]):
            name = src.get("name", "child"+str(index))
            was = src.get("node", "rst_n_t"+str(src.get("tap", 0)))
            if was not in before:
                raise ValueError(f"collector source {name}: old node {was} absent")
            depth = before[was]["depth"] + added
            points = status_points.get(name, src.get("status_pins_xy_um", [src["xy_um"]]))
            dist = lambda r: max(abs(p[0]-r["xy"][0])+abs(p[1]-r["xy"][1]) for p in points)
            eligible = [(dist(r), n) for n, r in after.items()
                        if r["depth"] == depth and dist(r) <= reach_um+1e-6]
            if not eligible:       # LIMIT-BIND-1: no relay within reach -> nearest relay at that depth, reported
                far = sorted((dist(r), n) for n, r in after.items() if r["depth"] == depth)
                if not far:
                    raise ValueError(f"collector source {name}: no depth-{depth} relay")
                _reach_info(f"collector source {name}: nearest depth-{depth} relay {far[0][0]:.3f}um > {reach_um}")
                eligible = far[:1]
            keep = [(d,n) for d,n in eligible if n == was]
            hop, node = min(keep or eligible)
            src["node"] = node
            if re.fullmatch(r"rst_n_t\d+", node): src["tap"] = int(node[7:])
            else: src.pop("tap", None)
            if name in status_points:
                src["xy_um"] = list(points[0])
                src["status_pins_xy_um"] = [list(p) for p in points]
            rows.append(dict(name=name, old_node=was, node=node, old_depth=before[was]["depth"],
                             depth=depth, max_source_hop_um=hop))
    info["tree"] = copy.deepcopy(tree)
    return dict(added_collector_cycles=added, sources=rows,
                max_source_hop_um=max((r["max_source_hop_um"] for r in rows), default=0))
