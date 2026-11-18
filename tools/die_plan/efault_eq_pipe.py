#!/usr/bin/env python3
"""efault_eq_pipe: set the eq input pipe depth of the ot_dp_efault plan cells in a plan-cell-conns file (bind_plancells.py).

ot_dp_efault (rtl/lib) takes EQ_PIPE (uniform) and EQ_PIPE_V (4 bits per eq bit, added): bit i is delayed D_i = EQ_PIPE +
EQ_PIPE_V[4i +: 4] flops and checked from AGE + D_i, so AGE is unchanged and the data lanes get no cycle (the eq path is a monitor
path).  This tool writes EQ_PIPE_V as a Verilog literal into params of every efault cell whose eq conns name a listed in-bus epoch.
usage: efault_eq_pipe.py CONNS_IN CONNS_OUT ROWS_OUT BUS=DEPTH [BUS=DEPTH ...] [--types t1,t2]  (default off: no BUS= -> no change)
ROWS_OUT: [{"file", "pointer", "old", "new"}] JSON-pointer rows (RFC 6901) of every changed param."""
import json
import sys

MODULE = "ot_dp_efault"
PARAM = "EQ_PIPE_V"


def eq_vector(eq_conns, depth_by_bus):
    """(literal, depths): per eq bit the depth of its epoch bus (0 when unlisted); packed 4 bits per bit, bit 0 lowest."""
    depths = []
    for e in eq_conns:
        if "epoch" not in e:
            depths.append(0)
            continue
        d = int(depth_by_bus.get(e["epoch"], 0))
        if not 0 <= d <= 15:
            raise ValueError(f"eq pipe depth {d} for {e['epoch']} outside 0..15")
        depths.append(d)
    n = len(depths)
    v = sum(d << (4 * i) for i, d in enumerate(depths))
    return f"{4 * n}'h{v:0{(4 * n + 3) // 4}x}", depths


def apply(doc, depth_by_bus, types=None, file="plan_cell_conns.json"):
    """Return (new doc, rows).  A cell with no listed bus keeps its params unchanged (EQ_PIPE_V absent = pipe off)."""
    doc = json.loads(json.dumps(doc))
    rows = []
    unknown = set(depth_by_bus)
    for tn, t in sorted(doc["types"].items()):
        if types is not None and tn not in types:
            continue
        for inst, c in sorted(t["cells"].items()):
            if c.get("module") != MODULE:
                continue
            eq = c["conns"]["eq"]
            hit = {e["epoch"] for e in eq if e.get("epoch") in depth_by_bus}
            unknown -= hit
            if not hit:
                continue
            if int(c["params"]["N"]) != len(eq):
                raise ValueError(f"{tn}.{inst}: N {c['params']['N']} != {len(eq)} eq conns")
            lit, _ = eq_vector(eq, depth_by_bus)
            old = c["params"].get(PARAM)
            if old != lit:
                c["params"][PARAM] = lit
                rows.append(dict(file=file, pointer=f"/types/{tn}/cells/{inst}/params/{PARAM}", old=old, new=lit))
    if unknown and types is None:
        raise ValueError(f"buses in no efault eq conns: {sorted(unknown)}")
    return doc, rows


def main(argv):
    types = None
    if "--types" in argv:
        i = argv.index("--types")
        types = set(argv[i + 1].split(","))
        del argv[i:i + 2]
    src, dst, rows_out, *pairs = argv
    depth = {k: int(v) for k, v in (p.split("=") for p in pairs)}
    doc, rows = apply(json.load(open(src)), depth, types, file=src)
    json.dump(doc, open(dst, "w"), indent=1, sort_keys=False)
    json.dump(rows, open(rows_out, "w"), indent=1)
    print(f"{len(rows)} rows")


if __name__ == "__main__":
    main(sys.argv[1:])
