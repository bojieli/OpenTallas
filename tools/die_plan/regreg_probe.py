"""R3-INTERNAL reg-reg probe (S81-P10 10-24; OpenROAD python): every register/macro -> register/macro connection of a
placed partition ODB, through combinational cells only, with the Manhattan distance launch output pin -> capture input pin.

    openroad -python -exit tools/die_plan/regreg_probe.py   env ODB=<3_place.odb> OUT=<json> [LIMIT_UM=750] [TOP=40]

Classes F>F, F>M, M>F, M>M (F = std-cell sequential, M = block macro); capture pins split into data (D / macro inputs)
and async (RESETN / SETN / ...).  Clock pins are not captures.  Output: per class n / max / over-limit, and the over-limit
pairs grouped by (launch hierarchy, capture hierarchy) with bit count and max um.
"""
import json
import os
import re
from collections import defaultdict

import odb  # noqa: E402

ASYNC = re.compile(r"^(RESETN|SETN|RN|SN|CLRN|PRE.*)$")
CLK = re.compile(r"^(CLK|CK|clk|ck.*|GCLK)$")


def group(name):
    s = re.sub(r"\[[0-9]+\]", "[*]", name)
    s = re.sub(r"(_reg|_q)?(\\\[[0-9]+\\\])*$", "", s)
    parts = re.split(r"[./]", s)
    return ".".join(parts[:3])


def main():
    db = odb.dbDatabase.create()
    db = odb.read_db(db, os.environ["ODB"])
    blk = db.getChip().getBlock()
    dbu = blk.getDefUnits()
    lim = float(os.environ.get("LIMIT_UM", 750))
    kind = {}
    for inst in blk.getInsts():
        m = inst.getMaster()
        if m.isBlock():
            kind[inst.getName()] = "M"
        elif m.isSequential():
            kind[inst.getName()] = "F"
    stats = defaultdict(lambda: dict(n=0, max_um=0.0, over=0))
    over = defaultdict(lambda: dict(bits=0, max_um=0.0, ex=None))
    for inst in blk.getInsts():
        lk = kind.get(inst.getName())
        if not lk:
            continue
        for it in inst.getITerms():
            if not it.isOutputSignal():
                continue
            net = it.getNet()
            if net is None or net.getSigType() in ("POWER", "GROUND", "CLOCK"):
                continue
            ok, lx, ly = it.getAvgXY()
            if not ok:
                continue
            seen = set()
            stack = [net]
            caps = []
            while stack and len(seen) < 50000:
                n = stack.pop()
                if n.getId() in seen:
                    continue
                seen.add(n.getId())
                for s in n.getITerms():
                    if not s.isInputSignal():
                        continue
                    si = s.getInst()
                    ck = kind.get(si.getName())
                    mn = s.getMTerm().getName()
                    if ck:
                        if CLK.match(mn) or s.getMTerm().getSigType() == "CLOCK":
                            continue
                        caps.append((s, ck, "async" if ASYNC.match(mn) else "data"))
                    else:
                        for o in si.getITerms():
                            if o.isOutputSignal() and o.getNet() is not None:
                                stack.append(o.getNet())
            for s, ck, cls in caps:
                ok2, cx, cy = s.getAvgXY()
                if not ok2:
                    continue
                d = (abs(cx - lx) + abs(cy - ly)) / dbu
                key = f"{lk}>{ck} {cls}"
                st = stats[key]
                st["n"] += 1
                st["max_um"] = max(st["max_um"], round(d, 1))
                if d > lim:
                    st["over"] += 1
                    g = over[(key, group(inst.getName()), group(s.getInst().getName()))]
                    g["bits"] += 1
                    if d >= g["max_um"]:
                        g["ex"] = [round(lx / dbu, 1), round(ly / dbu, 1), round(cx / dbu, 1), round(cy / dbu, 1)]
                    g["max_um"] = max(g["max_um"], round(d, 1))
    top = int(os.environ.get("TOP", 40))
    rows = sorted(over.items(), key=lambda kv: -kv[1]["bits"])
    out = dict(odb=os.environ["ODB"], limit_um=lim, classes=dict(sorted(stats.items())),
               over_total=sum(v["over"] for v in stats.values()),
               over_data=sum(v["over"] for k, v in stats.items() if k.endswith("data")),
               over_groups=[dict(cls=k[0], launch=k[1], capture=k[2], **v) for k, v in rows[:top]],
               over_lines=[[k[0]] + v["ex"] for k, v in rows])
    json.dump(out, open(os.environ["OUT"], "w"), indent=1)
    print(json.dumps(dict(classes=out["classes"], over_total=out["over_total"], over_data=out["over_data"])))


main()
