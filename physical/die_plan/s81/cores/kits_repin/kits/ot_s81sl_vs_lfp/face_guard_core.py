"""kits_repin wrapper of tools/die_plan/face_guard.py (copied beside it, unmodified): guard the Yosys netlist with this
core's clock / reset skip set; planned bits from pins.json (scalar ports by bare name).
    python3 -I face_guard_core.py NETLIST TOP SKIP_RE pins.json OUT.json      exit 1 = FAIL"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_guard as G
net, top, skip, pins, out = sys.argv[1:6]
r = G.guard(Path(net).read_text(), top, skip_re=skip)
want = {(p["bus"] if p.get("bit") is None else f"{p['bus']}[{p['bit']}]") for p in json.load(open(pins))
        if not re.match(skip, p["bus"])}
T = G.parse(Path(net).read_text())[top]
have = {b for p in T.ports if not re.match(skip, p) for b in G._bits_of(T, p)}
r["planned_bits"], r["missing_ports"], r["extra_ports"] = len(want), sorted(want - have)[:50], sorted(have - want)[:50]
r["missing_n"], r["extra_n"] = len(want - have), len(have - want)
if r["missing_n"] or r["extra_n"]:
    r["verdict"] = "FAIL"
# self-loop classification (kits_repin, reported, never a PASS): a 'shared' output flop whose extra loads reach
# (combinationally) nothing but its OWN D pin = a sticky / hold bit (e.g. fault <= fault | ...).  The face_guard
# verdict stays FAIL; run_kit.sh continues the physical run only when every failure is such a self-loop, and the
# result row carries the FAIL with this classification for a ruling.
from collections import defaultdict as _dd
mods = G.parse(Path(net).read_text())
F = G.Flat(mods, top)
drv, loads = _dd(list), _dd(list)
for ci, (m, path, pp) in enumerate(F.cells):
    for pn, (d, bits) in pp.items():
        for b_ in bits:
            (drv if d == "out" else loads)[F.find(b_)].append((ci, pn))
port_roots = {F.find(b_): b_ for p in T.ports for b_ in G._bits_of(T, p)}
self_loops, other = [], []
for cls, lst in r["fails"].items():
    for f in lst:
        bit = f.split(":")[0]
        if cls != "shared" or bit not in port_roots.values():
            other.append(f); continue
        cur, ff = F.find(bit), None
        for _ in range(G.MAX_CHAIN + 2):
            if len(drv[cur]) != 1: break
            ci, pn = drv[cur][0]
            m, path, pp = F.cells[ci]
            if G.is_ff(m): ff = ci; break
            ins = [v for k, (dd, v) in pp.items() if dd == "in"]
            if len(ins) != 1: break
            cur = F.find(ins[0][0])
        if ff is None:
            other.append(f); continue
        qn = [F.find(v[0]) for k, (dd, v) in F.cells[ff][2].items() if dd == "out"]
        seen, stack, ends, ok = set(qn), list(qn), set(), True
        while stack and ok:
            n_ = stack.pop()
            if n_ in port_roots and port_roots[n_] != bit:
                ok = False; break
            for ci, pn in loads[n_]:
                m, path, pp = F.cells[ci]
                if G.is_ff(m):
                    ends.add((ci, pn))
                    continue
                for k, (dd, v) in pp.items():
                    if dd == "out":
                        for b_ in v:
                            rr = F.find(b_)
                            if rr not in seen:
                                seen.add(rr); stack.append(rr)
        if ok and ends and all(ci == ff for ci, pn in ends):
            self_loops.append(f"{bit}: flop {F.cells[ff][1]} feeds back only into its own D ({len(seen)} nets)")
        else:
            other.append(f)
r["self_loop_only"] = bool(self_loops) and not other and not r.get("missing_n") and not r.get("extra_n")
r["self_loops"], r["non_self_loop_fails"] = self_loops, other[:50]
r["netlist"] = net
Path(out).write_text(json.dumps(r, indent=1) + "\n")
print(f"FACE_GUARD {r['verdict']} top {top} bits {r['checked']} ok {r['ok']} fails {r['fail_counts']} "
      f"missing {r['missing_n']} extra {r['extra_n']}")
print(f"FACE_GUARD self_loops {len(self_loops)} other {len(other)} self_loop_only {r['self_loop_only']}")
sys.exit(0 if r["verdict"] == "PASS" else 3 if r["self_loop_only"] else 1)
