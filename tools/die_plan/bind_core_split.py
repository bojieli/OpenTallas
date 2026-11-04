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


def apply(binder, specs):
    F, R = binder.F, binder.R
    by = {s["from"]: s for s in specs}
    out, receipts = [], []
    for c in F.cells:
        s = by.get(c.module) if c.kind == "leaf" else None
        if s is None:
            out.append(c)
            continue
        fp, n = s["face"]["port"], int(s["face"]["width"])
        base = F.new(n)
        face = list(range(base, base + n))
        pc, pf = dict(c.ports), {}
        dc, df = dict(c.dirs), {}
        for port, m in s["split"].items():
            if port not in c.ports:
                raise CoreSplitError(f"{c.path}: no port {port}")
            bits, d = c.ports[port], c.dirs[port]
            if sorted(m["pcc"] + m["pcf"]) != list(range(len(bits))):
                raise CoreSplitError(f"{c.path}.{port}: split does not cover {len(bits)} bits exactly once")
            pc.pop(port), dc.pop(port)
            pc[m["pcc_port"]], dc[m["pcc_port"]] = [bits[i] for i in m["pcc"]], d
            pf[m["pcf_port"]], df[m["pcf_port"]] = [bits[i] for i in m["pcf"]], d
        for port, sel in s["shared"].items():
            if port not in c.ports:
                raise CoreSplitError(f"{c.path}: no shared port {port}")
            bits = c.ports[port]
            pf[port], df[port] = (list(bits) if sel is None else [bits[i] for i in sel]), c.dirs[port]
        fit_view(c, s, pc, dc)
        pc[fp], dc[fp] = list(face), "output"
        pf[fp], df[fp] = list(face), "input"
        lp, part = c.path + "_f", R.part_of(c.path)
        if part is None:
            raise CoreSplitError(f"{c.path}: leaf is in no partition")
        R.parts[lp] = [part, (R.local_of(c.path) or c.path) + "_f"]
        out.append(Cell(c.path, s["pcc"], dict(c.params), pc, dc, "leaf", ytype=s["pcc"], yparams=dict(c.yparams or {}), src=c.src))
        out.append(Cell(lp, s["pcf"], {}, pf, df, "leaf", ytype=s["pcf"], yparams={}, src=c.src))
        receipts.append(dict(leaf=c.path, pcc=s["pcc"], pcf=s["pcf"], part=part))
    F.cells[:] = out
    return receipts
