"""Hierarchical gate-level netlist (Yosys JSON) -> flat leaf graph.

The design is flattened to leaf cells (std cells + hard macros) with
hierarchical instance names joined by '.', while the instance tree is kept
so the partitioner can group whole subtrees.  Every bit becomes a global
net id; constants are the strings '0'/'1'/'x'/'z'.

Produce the input with scripts/export_json.ys (Yosys):
    read_liberty -lib <libs>; read_verilog <netlist>; hierarchy -top T;
    write_json net.json
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

CONSTS = ("0", "1", "x", "z")


@dataclass
class Leaf:
    name: str            # hierarchical path, '.'-joined
    type: str
    conns: dict          # port -> list of (net id | const str)
    inst_path: tuple     # ancestor instance path (tuple of names), excl. leaf


@dataclass
class InstNode:
    path: tuple
    module: str
    children: list = field(default_factory=list)   # InstNode
    leaves: list = field(default_factory=list)     # leaf indices directly inside
    n_cells: int = 0
    area: float = 0.0
    n_macros: int = 0


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        p = self.p
        p.setdefault(a, a)
        root = a
        while p[root] != root:
            root = p[root]
        while p[a] != root:
            p[a], a = root, p[a]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # constants always win as representative
            if isinstance(rb, tuple) and rb[0] == "CONST":
                ra, rb = rb, ra
            self.p[rb] = ra


@dataclass
class FlatNetlist:
    top: str
    leaves: list                 # [Leaf]
    net_names: list              # net id -> name
    ports: dict                  # top port -> {"direction", "bits": [net|const]}
    tree: InstNode
    pin_dirs: dict = field(default_factory=dict)   # cell type -> {pin: dir}

    # ---- derived helpers -------------------------------------------------
    def net_pins(self):
        """net id -> list of (leaf index, port, bit index)."""
        out = {}
        for li, lf in enumerate(self.leaves):
            for port, bits in lf.conns.items():
                for bi, b in enumerate(bits):
                    if isinstance(b, int):
                        out.setdefault(b, []).append((li, port, bi))
        return out

    def port_nets(self):
        """net id -> list of (top port, bit index, direction)."""
        out = {}
        for pn, p in self.ports.items():
            for bi, b in enumerate(p["bits"]):
                if isinstance(b, int):
                    out.setdefault(b, []).append((pn, bi, p["direction"]))
        return out


def _is_hier(mod_json, typ, libcells):
    if typ in libcells:
        return False
    m = mod_json.get(typ)
    if m is None:
        return False
    attrs = m.get("attributes", {})
    if str(attrs.get("blackbox", "0")).strip("0") or str(attrs.get("whitebox", "0")).strip("0"):
        return False
    return True


def load_yosys_json(path, top=None, libcells=None):
    with open(path) as fh:
        data = json.load(fh)
    return flatten(data, top, libcells or {})


def flatten(data, top=None, libcells=None):
    libcells = libcells or {}
    mods = data["modules"]
    if top is None:
        tops = [n for n, m in mods.items() if str(m.get("attributes", {}).get("top", "0")).strip("0")]
        if len(tops) != 1:
            raise ValueError(f"cannot infer top module, give --top (candidates: {tops})")
        top = tops[0]
    uf = _UF()
    name_cands = {}       # key -> (depth, hidden, name)
    raw_leaves = []       # (name, type, {port: [key|const]}, inst_path)
    pin_dirs = {}

    def key(path, b):
        if isinstance(b, int):
            return (path, b)
        return ("CONST", b)

    def walk(modname, path, node):
        m = mods[modname]
        for nn, info in m.get("netnames", {}).items():
            hidden = bool(info.get("hide_name", 0))
            bits = info["bits"]
            for i, b in enumerate(bits):
                if not isinstance(b, int):
                    continue
                full = ".".join(path + (nn,))
                if len(bits) > 1:
                    full += f"[{i}]"
                k = (path, b)
                cand = (len(path), hidden, full)
                old = name_cands.get(k)
                if old is None or cand < old:
                    name_cands[k] = cand
        for cn, cell in m.get("cells", {}).items():
            typ = cell["type"]
            conns = cell.get("connections", {})
            if _is_hier(mods, typ, libcells):
                cpath = path + (cn,)
                child = InstNode(cpath, typ)
                node.children.append(child)
                cports = mods[typ].get("ports", {})
                for port, bits in conns.items():
                    cbits = cports.get(port, {}).get("bits", [])
                    for cb, pb in zip(cbits, bits):
                        if isinstance(cb, int):
                            uf.union(key(path, pb), (cpath, cb))
                walk(typ, cpath, child)
            else:
                if "port_directions" in cell:
                    pin_dirs.setdefault(typ, dict(cell["port_directions"]))
                raw_leaves.append((".".join(path + (cn,)), typ,
                                   {p: [key(path, b) for b in bits] for p, bits in conns.items()},
                                   path))
                node.leaves.append(len(raw_leaves) - 1)

    tree = InstNode((), top)
    walk(top, (), tree)
    topm = mods[top]
    raw_ports = {pn: {"direction": p["direction"], "bits": [key((), b) for b in p["bits"]]}
                 for pn, p in topm.get("ports", {}).items()}

    # number the net roots
    root_id = {}
    names = []

    def nid(k):
        r = uf.find(k)
        if isinstance(r, tuple) and r[0] == "CONST":
            return r[1]
        if r not in root_id:
            root_id[r] = len(names)
            names.append(None)
        return root_id[r]

    leaves = []
    for name, typ, conns, ipath in raw_leaves:
        leaves.append(Leaf(name, typ, {p: [nid(k) for k in ks] for p, ks in conns.items()}, ipath))
    ports = {pn: {"direction": p["direction"], "bits": [nid(k) for k in p["bits"]]}
             for pn, p in raw_ports.items()}
    # best name per net: top port names first, else shallowest visible netname
    best = {}
    for k, cand in name_cands.items():
        r = uf.find(k)
        if isinstance(r, tuple) and r[0] == "CONST":
            continue
        if r not in root_id:
            continue
        i = root_id[r]
        if i not in best or cand < best[i]:
            best[i] = cand
    for i in range(len(names)):
        names[i] = best[i][2] if i in best else f"_n{i}_"

    # subtree statistics
    def stats(node):
        n = a = mac = 0
        for li in node.leaves:
            c = libcells.get(leaves[li].type)
            n += 1
            if c is not None:
                a += c.area
                mac += 1 if c.is_macro else 0
        for ch in node.children:
            stats(ch)
            n += ch.n_cells
            a += ch.area
            mac += ch.n_macros
        node.n_cells, node.area, node.n_macros = n, a, mac

    stats(tree)
    for typ, c in libcells.items():
        if c.pins:
            pin_dirs.setdefault(typ, dict(c.pins))
    return FlatNetlist(top, leaves, names, ports, tree, pin_dirs)
