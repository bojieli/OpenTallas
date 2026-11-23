#!/usr/bin/env python3
"""usage: cut_inert_graph.py DIR   (DIR holds <stem>_gold.json / <stem>_gate.json written by yosys write_json after proc; opt_clean; memory_collect)"""
# S81-SVC-J9 SVC-CUT-DEPTH inert witness (COORD ruling 11-23): Codex compare_graph_port_anchored.py + exactly two normalizations:
#  (1) cell parameter CUT_D on a dsdv_svc_att_cut instance is dropped ONLY when its value is 1 (the inert default);
#  (2) a \ MEMID that yosys auto-generated (\.cc:<line>:do_switch\$<counter>) is replaced by a fixed token.
# Anything else (any other parameter, any other MEMID, CUT_D != 1) still mismatches.
import re
NORMALIZED = []
def norm_params(cell):
    p = dict(cell["parameters"])
    if cell["type"] == "dsdv_svc_att_cut" and "CUT_D" in p:
        if int(p["CUT_D"], 2) == 1:
            NORMALIZED.append("CUT_D=1"); del p["CUT_D"]
    if cell["type"] == "$mem_v2" and re.fullmatch(r"\$auto\$proc_rom\.cc:\d+:do_switch\$\d+", p.get("MEMID", "")):
        NORMALIZED.append("MEMID"); p["MEMID"] = "$auto$proc_rom"
    return p
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

def adjacency(module, common_nets, common_cells):
    labels, edges = {}, defaultdict(list)
    for name, port in module["ports"].items():
        key = ("port", name)
        labels[key] = ("port", name, port["direction"])
        for index, bit in enumerate(port["bits"]):
            edges[key].append(((name, index), ("bit", bit)))
    for name, cell in module.get("cells", {}).items():
        key = ("cell", name)
        attributes = {k: v for k, v in cell.get("attributes", {}).items() if k not in ("src", "hdlname")}
        labels[key] = ("cell", name if name in common_cells and not cell["hide_name"] else None,
                       cell["type"], json.dumps(norm_params(cell), sort_keys=True), json.dumps(attributes, sort_keys=True))
        for pin, bits in sorted(cell["connections"].items()):
            for index, bit in enumerate(bits):
                edges[key].append(((pin, index), ("bit", bit)))
    aliases = defaultdict(list)
    for name, net in sorted(module.get("netnames", {}).items()):
        if name in common_nets and not net["hide_name"]:
            for index, bit in enumerate(net["bits"]):
                aliases[bit].append((name, index))
    for node, pins in list(edges.items()):
        for label, target in pins:
            bit = target[1]
            labels[target] = ("bit", bit if isinstance(bit, str) else None, tuple(aliases[bit]))
            edges[target].append((label, node))
    return labels, edges

def check(left, right):
    attributes = lambda m: {k: v for k, v in m.get("attributes", {}).items() if k not in ("src", "hdlname")}
    params = lambda m: {k: v for k, v in m.get("parameter_default_values", {}).items() if k != "CUT_D"}
    if attributes(left) != attributes(right) or params(left) != params(right):
        return "attribute or parameter mismatch"
    common_nets = set()
    common_cells = left.get("cells", {}).keys() & right.get("cells", {}).keys()
    (la, ea), (lb, eb) = [adjacency(v, common_nets, common_cells) for v in (left, right)]
    def encode(a, b):
        codes = {}
        def ids(labels):
            return {n: codes.setdefault(label, len(codes)) for n, label in labels.items()}
        return ids(a), ids(b)
    ca, cb = encode(la, lb)
    for step in range(25):
        if Counter(ca.values()) != Counter(cb.values()):
            return f"graph color mismatch at refinement {step}"
        def refine(colors, edges):
            return {node: (code, tuple(sorted((label, colors[target]) for label, target in edges[node])))
                    for node, code in colors.items()}
        a, b = encode(refine(ca, ea), refine(cb, eb))
        stable = len(set(a.values())) == len(set(ca.values()))
        ca, cb = a, b
        if stable:
            break
    ga, gb = defaultdict(list), defaultdict(list)
    for group, values in [(ga, ca), (gb, cb)]:
        for node, color in values.items():
            group[color].append(node)
    if {k: len(v) for k, v in ga.items()} != {k: len(v) for k, v in gb.items()}:
        return "graph color counts differ"
    mapping = {}
    for color, nodes in ga.items():
        targets = gb[color]
        for node, target in zip(sorted(nodes, key=str), sorted(targets, key=str)):
            mapping[node] = target
    for node, target in mapping.items():
        if la[node] != lb[target]:
            return "graph labels differ"
        forward = Counter((label, mapping[neighbor]) for label, neighbor in ea[node])
        if forward != Counter(eb[target]):
            return f"no exact witness, {sum(len(v)>1 for v in ga.values())} ambiguous classes"
    return "exact graph witness"

root = Path(sys.argv[1])
for gold in sorted(root.glob("*_gold.json")):
    stem = gold.name.removesuffix("_gold.json")
    gate = root / f"{stem}_gate.json"
    a, b = [json.loads(p.read_text())["modules"] for p in (gold, gate)]
    x, y = a.pop("gold"), b.pop("gate")
    del NORMALIZED[:]
    res = check(x, y)
    from collections import Counter as _C
    print(stem, "wrapper", res, "| normalized (both sides):", dict(_C(NORMALIZED)), flush=True)
    for name in a.keys() | b.keys():
        if name not in a or name not in b:
            print("child set differs", name, flush=True)
        elif a[name] != b[name]:
            print(name, check(a[name], b[name]), flush=True)
