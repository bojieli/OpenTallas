"""Register fanout gate on the Yosys netlist of a kit (FLOW-CANARY, COORD 2026-10-25).

    python3 tools/die_plan/reg_fanout_gate.py NETLIST.v [--top MOD] [--max 64] [--out reg_fanout.json]   # exit 1 = FAIL

Why: GEOM-REVIEW-3 found Yosys merged the replicated registers of kv3_astk B back into one (the keep attribute misses
registers inside parameterised modules, memory 'yosys-keep-parameterised-modules'): every B mirror got ~1k slew
violations from registers driving 2048 loads.  A replicated-register design never needs one register to drive more
than a few dozen leaves, so a register whose Q/QN net reaches more than --max leaf DATA pins right after synthesis is a
merge (or a missing replica) and the kit stops before floorplan.
Counted: cell input pins on the register output net, through the flattened hierarchy.  Not counted: clock pins and
async set/reset pins (a reset relay driving its reset leaves is the reset tree, decision 2), and partition output ports.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_guard as FG  # noqa: E402

MAX_LOADS = 64
CTRL_PIN_RE = re.compile(r"^(CLK|CK|C|RESETN?|SETN?|RN|SN|R|S|CLR|PRE)$", re.I)
FF_OUT = {"Q", "QN"}


def fanout(text, top=None, max_loads=MAX_LOADS, straps=()):
    """straps: declared ID strap ports (OWNER 10-25 option B).  A register whose D is a strap port bit is the strap's
    quasi-static landing copy, not a merged replica: it is exempt (listed under strap_landing).  Nothing else is."""
    mods = FG.parse(text)
    if top is None:
        used = {typ for M in mods.values() for typ, _, _ in M.cells}
        tops = [m for m in mods if m not in used]
        if len(tops) != 1:
            raise ValueError(f"cannot pick the top module: {tops}")
        top = tops[0]
    F = FG.Flat(mods, top)
    sl = FG.strap_list(straps)
    strap_roots = {F.find(bt) for x in sl for bt in FG._bits_of(mods[top], x)}
    strap_q = set()
    data_loads, ctrl_loads, ff_drv = defaultdict(int), defaultdict(int), defaultdict(list)
    for ci, (m, path, pp) in enumerate(F.cells):
        ff = FG.is_ff(m)
        for p, (d, bits) in pp.items():
            for b in bits:
                r = F.find(b)
                if d == "out":
                    if ff and p.upper() in FF_OUT:
                        ff_drv[r].append(f"{path}.{p}")
                        if strap_roots and any(F.find(x) in strap_roots for x in pp.get("D", (None, ()))[1]):
                            strap_q.add(r)
                elif CTRL_PIN_RE.match(p):
                    ctrl_loads[r] += 1
                else:
                    data_loads[r] += 1
    n_ff = len({x.rsplit(".", 1)[0] for v in ff_drv.values() for x in v})
    over = sorted(((data_loads[r], r, ff_drv[r]) for r in ff_drv if data_loads[r] > max_loads and r not in strap_q),
                  reverse=True)
    hist = defaultdict(int)
    for r in ff_drv:
        n = data_loads[r]
        hist["0" if n == 0 else "1" if n == 1 else "2-8" if n <= 8 else "9-64" if n <= 64 else
             "65-256" if n <= 256 else ">256"] += 1
    return dict(schema="opentallas.reg_fanout_gate.v1", top=top, max_loads=max_loads, registers=n_ff,
                reg_nets=len(ff_drv), over=len(over), verdict="PASS" if not over else "FAIL",
                worst=[dict(loads=n, net=r, regs=d[:4], ctrl_loads=ctrl_loads[r]) for n, r, d in over[:200]],
                hist=dict(hist), straps=sorted(sl),
                strap_landing=[dict(loads=data_loads[r], net=r, regs=ff_drv[r][:4]) for r in sorted(strap_q)])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("netlist")
    ap.add_argument("--top")
    ap.add_argument("--max", type=int, default=MAX_LOADS)
    ap.add_argument("--out")
    ap.add_argument("--straps", help="kit dir or straps.json: declared ID straps (OWNER 10-25 option B)")
    a = ap.parse_args(argv)
    try:
        sl = FG.kit_strap_list(Path(a.straps).parent if a.straps.endswith(".json") else a.straps) if a.straps else []
        r = fanout(Path(a.netlist).read_text(), a.top, a.max, straps=sl)
    except Exception as e:                       # a crash is NOT RUN (2), never a PASS
        r = dict(verdict="ERROR", error=f"{type(e).__name__}: {e}")
    r["netlist"] = a.netlist
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    if r["verdict"] == "ERROR":
        print(f"REG_FANOUT ERROR {r['error']}")
        return 2
    print(f"REG_FANOUT {r['verdict']} top={r['top']} registers={r['registers']} over_{r['max_loads']}={r['over']} "
          f"hist={r['hist']}")
    for w in r["worst"][:20]:
        print(f"  {w['loads']:6d} data loads  {w['regs'][0]}  (net {w['net']})")
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
