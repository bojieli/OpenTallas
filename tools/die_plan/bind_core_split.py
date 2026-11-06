"""DIE-KV-66 11-04 (opt-in asbuilt.core_splits, default absent = nothing runs): one as-built hard leaf -> two hard leaves.

RF-KV3 splits qkd_kvs_pc into PCC + PCF. The as-built elaboration only knows the old leaf, so this pass replaces it after
substitute_inst, before compose and Graph: PCC keeps the path and every port except the split buses; PCF is a new leaf at
<path>_f; a fresh net vector joins them. Schedule change (+2 edges on the read return) is the compiler's, not this pass.
Spec: {"from": module, "pcc": module, "pcf": module, "face": {"port": name, "width": n},
       "split": {port: {"pcc": [bits], "pcf": [bits], "pcc_port": name, "pcf_port": name}},
       "shared": {port: [bits or null=all]},  # ports PCF also connects
       "reset_gate": [ports],  # optional, both new leaves: see gate_ports
       "view_drop": [ports],  # optional: PCC view has no such pin (die-clock aliases collapsed inside the view): not emitted
       "view_parts": {port: {view port: [bits]}}}  # optional: PCC view keeps only these bits, under these names; other bits dead
view_drop/view_parts (DIE-KV-67 11-04): the as-built leaf ports are not the hardened view ports (kvspc_face_ports). Without these
the parent instance names pins the child does not have and rtl_lint stops the kit. view_drop pins stay in the connectivity graph so
their lanes and lane epochs stay as planned (plan cells read them); only the emitted instance leaves them out.
reset_gate (DIE-KV-67 11-04, COORD LOOP-GAP 05:20 (4), option b): the PC reset pins come from a reset-less data lane, so the die
reset contract does not cover them. Each listed pin gets one ot_dp_rgate: q <= lane & local wavefront tap. Lane function kept,
one edge later; while the die reset holds the tap low the pin is held low, so the wavefront proof covers it by construction.
"""
import re
from types import SimpleNamespace

from bind_elab import Cell


class CoreSplitError(ValueError):
    pass


def gate_ports(specs):
    """{leaf module: set(reset pins that take the wavefront gate)} of the specs that ask for it."""
    out = {}
    for s in specs:
        if s.get("reset_gate"):
            for m in (s["pcc"], s["pcf"]):
                out.setdefault(m, set()).update(s["reset_gate"])
    return out


def gate_tap(relays, xy, consumer_taps):
    """the wavefront tap net rst_n_t<k> nearest to xy, among the consumer taps k < consumer_taps.  Taps at or above
    that are the type's registered reset outs: they are emitted as rr_t<k> face flops and may feed nothing else.  All
    consumer taps release on the same edge, so the choice only sets the wire length."""
    taps = [r for r in relays if re.fullmatch(r"rst_n_t\d+", str(r.get("q", "")))
            and int(str(r["q"])[len("rst_n_t"):]) < consumer_taps]
    if not taps:
        raise CoreSplitError("reset_gate: the type has no wavefront consumer tap")
    best = min(taps, key=lambda r: (abs(r["xy"][0] - xy[0]) + abs(r["xy"][1] - xy[1]), r["q"]))
    return best["q"]


def view_hidden(specs):
    """{PCC module: set(pins the emitted instance leaves out)}."""
    return {s["pcc"]: set(s["view_drop"]) for s in specs if s.get("view_drop")}


def fit_view(c, s, pc, dc):
    """PCC ports as the hardened view has them: rename the live bits of view_parts.  Dead bits lose their load."""
    for port in s.get("view_drop", []):
        if port not in pc:
            raise CoreSplitError(f"{c.path}: no view_drop port {port}")
    for port, parts in (s.get("view_parts") or {}).items():
        if port not in pc:
            raise CoreSplitError(f"{c.path}: no view_parts port {port}")
        bits, d = pc.pop(port), dc.pop(port)
        for name, sel in parts.items():
            if not sel or max(sel) >= len(bits) or min(sel) < 0:
                raise CoreSplitError(f"{c.path}.{port}: view_parts {name} bits outside {len(bits)}")
            pc[name], dc[name] = [bits[i] for i in sel], d


def split_ports(path, ports, dirs, s, face):
    """(pcc ports, pcc dirs, pcf ports, pcf dirs) of one split leaf: the pure port transform of apply.  ports maps a
    port to its bit list (any ids), face is the bit list of the new PCC->PCF face vector."""
    fp = s["face"]["port"]
    pc, pf = dict(ports), {}
    dc, df = dict(dirs), {}
    for port, m in s["split"].items():
        if port not in ports:
            raise CoreSplitError(f"{path}: no port {port}")
        bits, d = ports[port], dirs[port]
        if sorted(m["pcc"] + m["pcf"]) != list(range(len(bits))):
            raise CoreSplitError(f"{path}.{port}: split does not cover {len(bits)} bits exactly once")
        pc.pop(port), dc.pop(port)
        pc[m["pcc_port"]], dc[m["pcc_port"]] = [bits[i] for i in m["pcc"]], d
        pf[m["pcf_port"]], df[m["pcf_port"]] = [bits[i] for i in m["pcf"]], d
    for port, sel in s["shared"].items():
        if port not in ports:
            raise CoreSplitError(f"{path}: no shared port {port}")
        bits = ports[port]
        pf[port], df[port] = (list(bits) if sel is None else [bits[i] for i in sel]), dirs[port]
    fit_view(SimpleNamespace(path=path), s, pc, dc)
    pc[fp], dc[fp] = list(face), "output"
    pf[fp], df[fp] = list(face), "input"
    return pc, dc, pf, df


def emitted_ifaces(cells, specs):
    """{split leaf module: {"params": [names], "ports": {port: [dir, width]}}} as the bound parents instantiate them
    (view_drop pins left out), from the final bind cells.  bind_verify stubs these: the split leaves have no source."""
    mods = {m for s in specs for m in (s["pcc"], s["pcf"])}
    hide = view_hidden(specs)
    out = {}
    for c in cells:
        if c.kind != "leaf" or c.module not in mods:
            continue
        e = out.setdefault(c.module, {"params": set(), "ports": {}})
        e["params"] |= set(c.params or {})
        for pn, bits in c.ports.items():
            if pn in hide.get(c.module, ()):
                continue
            w = max(len(bits), e["ports"].get(pn, [None, 0])[1])
            e["ports"][pn] = [c.dirs[pn], w]
    return {m: {"params": sorted(e["params"]), "ports": dict(sorted(e["ports"].items()))} for m, e in sorted(out.items())}


def derived_ifaces(specs, iface_of):
    """emitted_ifaces without the bind cells (bind outputs written before bind recorded them): the same split_ports
    transform on the interface of each spec's source leaf.  iface_of(module) -> {port: (dir, width)} or None."""
    out = {}
    for s in specs:
        src = iface_of(s["from"])
        if not src:
            raise CoreSplitError(f"no interface of split source {s['from']}: re-run bind to record core_split_ifaces")
        ports = {p: list(range(w)) for p, (d, w) in src.items()}
        dirs = {p: d for p, (d, w) in src.items()}
        pc, dc, pf, df = split_ports(s["from"], ports, dirs, s, list(range(int(s["face"]["width"]))))
        hide = set(s.get("view_drop", ()))
        out[s["pcc"]] = {"params": [], "ports": {p: [dc[p], len(b)] for p, b in sorted(pc.items()) if p not in hide}}
        out[s["pcf"]] = {"params": [], "ports": {p: [df[p], len(b)] for p, b in sorted(pf.items())}}
    return out


def apply(binder, specs):
    F, R = binder.F, binder.R
    by = {s["from"]: s for s in specs}
    out, receipts = [], []
    for c in F.cells:
        s = by.get(c.module) if c.kind == "leaf" else None
        if s is None:
            out.append(c)
            continue
        n = int(s["face"]["width"])
        base = F.new(n)
        pc, dc, pf, df = split_ports(c.path, c.ports, c.dirs, s, list(range(base, base + n)))
        lp, part = c.path + "_f", R.part_of(c.path)
        if part is None:
            raise CoreSplitError(f"{c.path}: leaf is in no partition")
        R.parts[lp] = [part, (R.local_of(c.path) or c.path) + "_f"]
        out.append(Cell(c.path, s["pcc"], dict(c.params), pc, dc, "leaf", ytype=s["pcc"], yparams=dict(c.yparams or {}), src=c.src))
        out.append(Cell(lp, s["pcf"], {}, pf, df, "leaf", ytype=s["pcf"], yparams={}, src=c.src))
        receipts.append(dict(leaf=c.path, pcc=s["pcc"], pcf=s["pcf"], part=part))
    F.cells[:] = out
    return receipts
