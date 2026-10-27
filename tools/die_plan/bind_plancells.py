"""bind_plancells: plan-only cells in a bound die (tools/die_plan/bind.py, asbuilt.plan_cells).

A plan may add hardware that has no as-built counterpart -- counted ID lanes that replace per-replica constants
(ot_dp_id_src / _add / _rot), landing checks (ot_dp_efault), fault chains, new OR roots -- so the binder cannot take
their nets from the as-built die.  asbuilt.plan_cells names a JSON file (schema opentallas.kv_p4.cell_conns.v1, e.g.
physical/die_plan/qwen_kvsys/bind/plan_cell_conns_v34.json) with, PER PLAN PARTITION TYPE:
  cells[inst]   = {module, params, conns{port: [entry...]}}
                  INPUT port : entries are the drivers, concatenated LSB-first;
                  OUTPUT port: entries are the sinks; each sink takes port bits 'from' [lo, hi] (whole port if absent)
  leaf_binds[]  = {inst, port, drivers[]}: a leaf input port driven straight from plan signals (LSB-first)
  bus_drivers[] = {bus, drivers[]}: an out bus assembled from plan signals (LSB-first)
  rewired[]     = {sink: {inst, port, bits?}, driver: entry}: an as-built leaf input whose driver the plan changes
  entry kinds   : {"bus": B, "bits": [lo, hi]}  (in bus: its registered q; out bus: its data d)
                  {"epoch": B}  (the in-boundary epoch of in bus B)   {"net": "clk" | "rst_n"}
                  {"inst": LEAF, "port": P, "bits": [lo, hi]}  {"cell": INST, "port": P, "bits": [lo, hi]}
Effects: the leaf input bits a plan cell drives stop being as-built constants (TIED / straps) -- they are counted as
plan_driven; out buses driven by plan cells get their plan lanes (reserved: no as-built bit is packed onto them); the
cells are emitted in the partition module.  A reference the partition cannot resolve (an in bus that carries nothing,
an unknown leaf / cell / port) is an error and stays an undriven wire -- never a constant.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import bind_elab as E


class PlanCells:
    def __init__(self, B, path, base):
        self.B = B
        self.doc = json.loads(Path(path).read_text())
        self.T = self.doc["types"]
        self.ptype0 = {p["name"]: p["type"] for p in B.plan["partitions"]}       # plan type before any split
        self.bus_dir = {tn: {b["name"]: b["dir"] for b in t.get("buses", [])} for tn, t in B.plan["partition_types"].items()}
        self.bus_w = {tn: {b["name"]: int(b["width"]) for b in t.get("buses", [])} for tn, t in B.plan["partition_types"].items()}
        self.stats = defaultdict(int)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import die_port_bind as D
        ab = B.ab
        idx = E.module_index(ab.get("rtl_roots", ["rtl"]), ab.get("files", []), base)
        prefer = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab.get("prefer", [])]
        self.iface = {}
        for t in self.T.values():
            for c in t["cells"].values():
                m = c["module"]
                if m in self.iface:
                    continue
                f, _ = E.pick(idx, m, prefer)
                if f is None:
                    B.errors.append(f"PLAN_CELL_MODULE {m}: no RTL defines it")
                    self.iface[m] = None
                    continue
                mods = {x.name: x for x in D.parse_modules(Path(f).read_text(errors="replace"), f)}
                self.iface[m] = mods[m]
                if f not in B.extra_lib:
                    B.extra_lib.append(f)
        # per plan type: leaf-bit drivers, plan out-bus bit drivers
        self.leafdrv, self.busdrv, self.celldrv, self.explicit = {}, {}, {}, {}
        for tn, t in self.T.items():
            self.leafdrv[tn], self.busdrv[tn] = self._resolve(tn, t)

    # ---------------------------------------------------------------- conns -> per-bit atoms
    def _atoms(self, tn, e):
        if "bus" in e:
            lo, hi = e.get("bits", [0, self.bus_w[tn].get(e["bus"], 1) - 1])
            k = "busq" if self.bus_dir[tn].get(e["bus"]) == "in" else "busd"
            return [(k, e["bus"], j) for j in range(lo, hi + 1)]
        if "epoch" in e:
            return [("eq", e["epoch"])]
        if "net" in e:
            return [("net", e["net"])]
        if "inst" in e:
            lo, hi = e["bits"]
            return [("leaf", e["inst"], e["port"], j) for j in range(lo, hi + 1)]
        if "cell" in e:
            lo, hi = e["bits"]
            return [("cell", e["cell"], e["port"], j) for j in range(lo, hi + 1)]
        raise ValueError(f"plan_cells {tn}: bad entry {e}")

    def width(self, m, port, params):
        mod = self.iface.get(m)
        if mod is None or port not in mod.ports:
            return None
        try:
            return mod.width(port, mod.env({k: str(v) for k, v in params.items()}))
        except Exception:
            return None

    def _resolve(self, tn, t):
        leafdrv, busdrv, celldrv = {}, defaultdict(dict), {}
        self.celldrv[tn] = celldrv
        self.explicit[tn] = set()
        for inst, c in t["cells"].items():
            mod = self.iface.get(c["module"])
            for port, ents in c.get("conns", {}).items():
                d = mod.ports[port][0] if mod is not None and port in mod.ports else None
                if d is None:
                    self.B.errors.append(f"PLAN_CELL_PORT {tn}.{inst}.{port}: not a port of {c['module']}")
                    continue
                if d != "output":
                    continue
                for e in ents:
                    flo, fhi = e.get("from", [0, (self.width(c["module"], port, c.get("params", {})) or 1) - 1])
                    src = [("cell", inst, port, j) for j in range(flo, fhi + 1)]
                    dst = self._atoms(tn, e)
                    if len(dst) != len(src):
                        self.B.errors.append(f"PLAN_CELL_WIDTH {tn}.{inst}.{port} -> {e}: {len(src)} != {len(dst)} bits")
                        continue
                    for a, s in zip(dst, src):
                        if a[0] == "busd":
                            busdrv[a[1]][a[2]] = s
                        elif a[0] == "leaf":
                            leafdrv[(a[1], a[2], a[3])] = s
                            self.explicit[tn].add((a[1], a[2]))     # a plan cell output named this leaf input
                        elif a[0] == "cell":
                            celldrv[(a[1], a[2], a[3])] = s
        for lb in t.get("leaf_binds", []):
            atoms = [a for e in lb["drivers"] for a in self._atoms(tn, e)]
            for j, a in enumerate(atoms):
                leafdrv[(lb["inst"], lb["port"], j)] = a
        for bd in t.get("bus_drivers", []):
            atoms = [a for e in bd["drivers"] for a in self._atoms(tn, e)]
            for j, a in enumerate(atoms):
                busdrv[bd["bus"]][j] = a
        for rw in t.get("rewired", []):
            s = rw["sink"]
            atoms = self._atoms(tn, rw["driver"])
            lo = s.get("bits", [0, len(atoms) - 1])[0]
            for j, a in enumerate(atoms):
                leafdrv[(s["inst"], s["port"], lo + j)] = a
        return leafdrv, dict(busdrv)

    def ptype(self, p):
        return self.ptype0.get(p)

    # ---------------------------------------------------------------- analysis hooks
    def reserved_buses(self):
        """{(partition, out bus)} driven by plan cells: their lanes carry no as-built bit"""
        r = set()
        for p in self.B.parts:
            tn = self.ptype(p)
            if tn in self.busdrv:
                for b in self.busdrv[tn]:
                    r.add((p, b))
        return r

    def rewired_keys(self):
        """(ci, port, bit) of the leaf inputs a plan rewired[] entry re-points: their as-built source is not a crossing
        of the bound die (the binder must not route it), the plan bus drives them"""
        B = self.B
        keys = set()
        for p, members in B.members.items():
            tn = self.ptype(p)
            if tn not in self.leafdrv:
                continue
            rel = {B.rel_of(ci): ci for ci in members}
            rw = {(s["sink"]["inst"], s["sink"]["port"]) for s in self.T[tn].get("rewired", [])}
            for (inst, port, j) in self.leafdrv[tn]:
                ci = rel.get(inst)
                if ci is not None and (inst, port) in rw:
                    keys.add((ci, port, j))
        return keys

    def apply_sinks(self):
        """re-point the leaf input bits that plan cells drive: as-built constants become plan_driven"""
        B = self.B
        drop = set()
        self.reducers = defaultdict(set)
        for ci, c in enumerate(B.F.cells):
            if B.G.kind[ci] == "reducer":
                p = B.R.part_of(c.path)
                if p is not None:
                    self.reducers[p].add(B.R.local_of(c.path) or c.path.rsplit(".", 1)[-1])
        for p, members in B.members.items():
            tn = self.ptype(p)
            if tn not in self.leafdrv:
                continue
            rel = {B.rel_of(ci): ci for ci in members}
            rw = {(s["sink"]["inst"], s["sink"]["port"]) for s in self.T[tn].get("rewired", [])} | self.explicit[tn]
            seen = set()
            for (inst, port, j), a in self.leafdrv[tn].items():
                ci = rel.get(inst)
                if ci is None and (inst, port) in rw and inst in self.reducers.get(p, ()):
                    # a re-pointed input of an as-built fault-OR cell: the binder re-emits every fault tree from its
                    # leaf sources (ot_dp_or per sink), so the plan's bypass is already in the bound OR -- recorded
                    if (inst, port) not in seen:
                        seen.add((inst, port))
                        self.stats["rewired_reducer_inputs"] += 1
                        B.findings.append(f"PLAN_REWIRED_REDUCER {p}: {inst}.{port} (as-built fault-OR cell; tree "
                                          f"re-emitted from its leaf sources)")
                    continue
                if ci is None or (ci, port, j) not in B.sinks:
                    if (inst, port) not in seen:
                        seen.add((inst, port))
                        B.errors.append(f"PLAN_CELL_SINK {p}: {inst}.{port} is not a leaf input of the partition")
                    continue
                old = B.sinks[(ci, port, j)]
                if old[0] == "tied":
                    B.counts["tied"] = B.counts.get("tied", 0) - 1
                    B.tied_by_port[f"{B.F.cells[ci].module}.{port} <- literal"] -= 1
                    drop.add(f"TIED {B.F.cells[ci].path}.{port}[{j}] ")
                elif old[0] == "strap":
                    B.counts["strap"] = B.counts.get("strap", 0) - 1
                elif (inst, port) not in rw:
                    self.stats["live_overridden"] += 1
                    B.errors.append(f"PLAN_CELL_LIVE {p}: {inst}.{port}[{j}] has a live as-built driver {old[:2]} "
                                    f"but the plan drives it (not declared in rewired[])")
                else:
                    self.stats["rewired"] += 1
                B.sinks[(ci, port, j)] = ("plan", a)
                B.counts["plan_driven"] = B.counts.get("plan_driven", 0) + 1
        if drop:
            B.errors[:] = [e for e in B.errors if not any(e.startswith(d) for d in drop)]
        for k in [k for k, v in B.tied_by_port.items() if v <= 0]:
            del B.tied_by_port[k]

    # ---------------------------------------------------------------- emission
    def emit(self, p, tn, ins, outs, drv_w, rel_ci, decl, body, ub):
        """the plan cells of partition p (its module's type tn): returns {atom: SV expression} rendering"""
        B = self.B
        pt = self.ptype(p)
        if pt not in self.T:
            return None
        t = self.T[pt]
        cw = {}
        for inst, c in sorted(t["cells"].items()):
            mod = self.iface.get(c["module"])
            if mod is None:
                continue
            for port, (d, _r) in mod.ports.items():
                if d == "output":
                    w = self.width(c["module"], port, c.get("params", {})) or 1
                    nm = f"pc_{inst}__{port}"
                    cw[(inst, port)] = nm
                    decl.append(f"    wire [{w - 1}:0] {nm};")

        def undriven(why):
            nm = f"ub_{len(ub)}"
            ub.append(nm)
            decl.append(f"    wire {nm};  // UNBOUND plan: {why} (see bind_report errors)")
            B.errors.append(f"PLAN_CELL_REF {p} ({pt}): {why}")
            return nm

        def render(a):
            k = a[0]
            if k == "busq":
                return f"{a[1]}_q[{a[2]}]" if a[1] in ins else undriven(f"in bus {a[1]} carries no lane in this partition")
            if k == "eq":
                return f"{a[1]}_eq" if a[1] in ins else undriven(f"epoch of in bus {a[1]}: no lane in this partition")
            if k == "busd":
                return f"pb_{a[1]}[{a[2]}]" if a[1] in self.busdrv.get(pt, {}) else \
                    undriven(f"out bus {a[1]} is not plan-driven")
            if k == "net":
                return "clk" if a[1] == "clk" else "rst_n"
            if k == "leaf":
                ci = rel_ci.get(a[1])
                if ci is None or (ci, a[2]) not in drv_w:
                    return undriven(f"leaf output {a[1]}.{a[2]} not in the partition")
                return f"{drv_w[(ci, a[2])]}[{a[3]}]"
            if k == "cell":
                if (a[1], a[2]) not in cw:
                    return undriven(f"plan cell output {a[1]}.{a[2]} unknown")
                return f"{cw[(a[1], a[2])]}[{a[3]}]"
            return undriven(f"atom {a}")
        from bind import _concat
        for b, bits in sorted(self.busdrv.get(pt, {}).items()):
            if b not in outs:
                continue
            W = outs[b]
            decl.append(f"    wire [{W - 1}:0] pb_{b};")
            e = [render(bits[j]) if j in bits else undriven(f"out bus {b}[{j}] has no plan driver") for j in range(W)]
            body.append(f"    assign pb_{b} = {_concat(e)};  // plan-driven out bus")
        for inst, c in sorted(t["cells"].items()):
            mod = self.iface.get(c["module"])
            if mod is None:
                continue
            cs = []
            for port, (d, _r) in mod.ports.items():
                if d == "output":
                    cs.append(f"        .{port}({cw[(inst, port)]})")
                    continue
                ents = c.get("conns", {}).get(port)
                w = self.width(c["module"], port, c.get("params", {}))
                cd = self.celldrv[pt]
                if not ents and w and all((inst, port, j) in cd for j in range(w)):
                    atoms = [cd[(inst, port, j)] for j in range(w)]       # named as a sink of another cell's output
                elif not ents:
                    cs.append(f"        .{port}({undriven(f'{inst}.{port}: no driver in conns')})")
                    continue
                else:
                    atoms = [a for e in ents for a in self._atoms(pt, e)]
                if w is not None and len(atoms) != w:
                    B.errors.append(f"PLAN_CELL_WIDTH {pt}.{inst}.{port}: {len(atoms)} driver bits != port width {w}")
                cs.append(f"        .{port}({_concat([render(a) for a in atoms])})")
            ps = ", ".join(f".{k}({v})" for k, v in sorted(c.get("params", {}).items()))
            body.append(f"    // plan cell ({pt})\n    {c['module']}" + (f" #({ps})" if ps else "") +
                        f" u_{inst} (\n" + ",\n".join(cs) + "\n    );")
            self.stats["cells_emitted"] += 1
        return render
