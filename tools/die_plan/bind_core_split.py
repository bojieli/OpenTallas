"""DIE-KV-66 11-04 (opt-in asbuilt.core_splits, default absent = nothing runs): one as-built hard leaf -> two hard leaves.

RF-KV3 splits qkd_kvs_pc into PCC + PCF. The as-built elaboration only knows the old leaf, so this pass replaces it after
substitute_inst, before compose and Graph: PCC keeps the path and every port except the split buses; PCF is a new leaf at
<path>_f; a fresh net vector joins them. Schedule change (+2 edges on the read return) is the compiler's, not this pass.
Spec: {"from": module, "pcc": module, "pcf": module, "face": {"port": name, "width": n},
       "split": {port: {"pcc": [bits], "pcf": [bits], "pcc_port": name, "pcf_port": name}},
       "shared": {port: [bits or null=all]}}  # ports PCF also connects
"""
from bind_elab import Cell


class CoreSplitError(ValueError):
    pass


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
