#!/usr/bin/env python3
"""Split capture-vector FFs at exact HC pair boundaries before submod.

Slang represents wdat/xdat as one wide $dff, while the old read_verilog cut had
per-group cells. Splitting D/Q in the same order preserves every edge and bit;
clock/reset/control connections are retained verbatim. No arithmetic is edited.
"""
import argparse
import copy
import json
from pathlib import Path


def split(top):
    nets = top["netnames"]
    groups = {}
    for k in range(8):
        cap = nets["u_c.u_b.wdat"]["bits"][k * 512:(k + 1) * 512]
        cap += nets["u_c.u_b.xdat"]["bits"][k * 256:(k + 1) * 256]
        for b in cap:
            if b in groups and groups[b] != k:
                raise ValueError("capture bit belongs to two physical pairs")
            groups[b] = k
    changed = []
    for name, cell in list(top["cells"].items()):
        if cell["type"] not in ("$dff", "$adff"):
            continue
        q = cell["connections"]["Q"]
        if not any(b in groups for b in q):
            continue
        by = {}
        for i, b in enumerate(q):
            by.setdefault(groups.get(b, "remainder"), []).append(i)
        if len(by) == 1:
            continue
        del top["cells"][name]
        for k, indices in by.items():
            c = copy.deepcopy(cell)
            for port in ("D", "Q"):
                c["connections"][port] = [cell["connections"][port][i] for i in indices]
            p = c["parameters"]
            p["WIDTH"] = format(len(indices), "032b")
            if "ARST_VALUE" in p:
                old = str(p["ARST_VALUE"]).zfill(len(q))
                p["ARST_VALUE"] = "".join(old[-1-i] for i in reversed(indices))
            new = name + "__hc128_" + str(k)
            if new in top["cells"]:
                raise ValueError("physical split cell name collision")
            top["cells"][new] = c
        changed.append(dict(cell=name, bits=len(q), chunks=[len(v) for v in by.values()]))
    return changed


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("source", type=Path)
    a.add_argument("--out", required=True, type=Path)
    a.add_argument("--top", default="ot_hbm_hc_bankq_static")
    o = a.parse_args()
    data = json.loads(o.source.read_text())
    changes = split(data["modules"][o.top])
    o.out.write_text(json.dumps(data))
    print(json.dumps(dict(split_cycles=0, changed=changes)))


if __name__ == "__main__":
    main()
