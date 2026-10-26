"""S81-KITS-RTLB survey: main face_guard.py (no 'pair' ext, untruncated) on a kit's RAW Yosys netlist (1_2_yosys.v);
fails grouped by bus + class, with sub-classification:
  output shared  -> 'hold' (flop's extra loads reach only its own D = sticky/hold bit) | 'fanout' (flop also feeds other logic)
  input shared   -> 'copies' (all loads are flop D pins via <=0 logic = same-D capture copies) | 'comb' (loads logic)
  merged         -> list the other port bits on the same flop (pair kits: in->out 1-station)
    python3 survey_fg.py FACE_GUARD_DIR KITDIR OUT.json"""
import json, re, sys
from collections import defaultdict
from pathlib import Path
fgdir, kd, out = sys.argv[1:4]
sys.path.insert(0, fgdir)
import face_guard as G
src = Path(G.__file__).read_text()
# untruncated copy of guard(): drop the [:50] cut
ns = {}
code = src.replace('res["fails"] = {k: v[:50] for k, v in res["fails"].items()}', 'pass')
exec(compile(code, "face_guard_untrunc", "exec"), ns)
kd = Path(kd)
top = re.search(r"^export DESIGN_NAME = (\S+)", (kd / "config.mk").read_text(), re.M).group(1)
skip = (kd / "face_guard_skip.txt").read_text().strip()
net = sorted(kd.glob("run/results/asap7/*/base/1_2_yosys.v"))[-1]
text = net.read_text()
r = ns["guard"](text, top, skip_re=skip, ft1=set())
mods = ns["parse"](text); T = mods[top]; F = ns["Flat"](mods, top)
drv, loads = defaultdict(list), defaultdict(list)
for ci, (m, path, pp) in enumerate(F.cells):
    for pn, (d, bits) in pp.items():
        for b_ in bits:
            (drv if d == "out" else loads)[F.find(b_)].append((ci, pn))
port_roots = {F.find(b_): b_ for p in T.ports for b_ in ns["_bits_of"](T, p)}
def out_class(bit):
    cur, ff = F.find(bit), None
    for _ in range(ns["MAX_CHAIN"] + 2):
        if len(drv[cur]) != 1: break
        ci, pn = drv[cur][0]; m, path, pp = F.cells[ci]
        if ns["is_ff"](m): ff = ci; break
        ins = [v for k, (dd, v) in pp.items() if dd == "in"]
        if len(ins) != 1: break
        cur = F.find(ins[0][0])
    if ff is None: return "nonflop", None
    qn = [F.find(v[0]) for k, (dd, v) in F.cells[ff][2].items() if dd == "out"]
    seen, stack, ends, ok = set(qn), list(qn), set(), True
    while stack and ok:
        n_ = stack.pop()
        if n_ in port_roots and port_roots[n_] != bit: ok = False; break
        for ci, pn in loads[n_]:
            m, path, pp = F.cells[ci]
            if ns["is_ff"](m): ends.add(ci); continue
            for k, (dd, v) in pp.items():
                if dd == "out":
                    for b_ in v:
                        rr = F.find(b_)
                        if rr not in seen: seen.add(rr); stack.append(rr)
    if ok and ends and ends == {ff}: return "hold", F.cells[ff][1]
    return "fanout", F.cells[ff][1]
def in_class(bit):
    ld = loads[F.find(bit)]
    kinds = set()
    for ci, pn in ld:
        m = F.cells[ci][0]
        kinds.add("ffD" if ns["is_ff"](m) and pn == "D" else "ffctl" if ns["is_ff"](m) else "buf" if ns["is_buf"](m) else "logic")
    return ("copies" if kinds <= {"ffD", "buf"} else "comb"), len(ld)
groups = defaultdict(list)
for cls, lst in r["fails"].items():
    for f in lst:
        bit = f.split(":")[0]
        bus = re.sub(r"\[\d+\]$", "", bit)
        d = T.dirs.get(bus, "?")
        sub = ""
        if cls == "shared" and d == "output": sub = out_class(bit)[0]
        elif cls == "shared" and d == "input": c, n = in_class(bit); sub = f"{c}"
        elif cls == "merged": sub = re.sub(r"\[\d+\]", "", f.split("also registers ")[-1])
        groups[(bus, d, cls, sub)].append(bit)
def rng(bits):
    idx = sorted(int(m.group(1)) for b in bits for m in [re.search(r"\[(\d+)\]$", b)] if m)
    if not idx: return ""
    out_, s = [], idx[0]; p = s
    for i in idx[1:] + [None]:
        if i is None or i != p + 1:
            out_.append(f"{s}" if s == p else f"{s}..{p}"); s = i
        p = i if i is not None else p
    return "[" + ",".join(out_) + "]"
rows = [dict(bus=k[0], dir=k[1], cls=k[2], sub=k[3], n=len(v), bits=rng(v)) for k, v in sorted(groups.items())]
res = dict(kit=str(kd), top=top, netlist=str(net), verdict=r["verdict"], checked=r["checked"], ok=r["ok"],
           fail_counts={k: len(v) for k, v in r["fails"].items()}, groups=rows)
Path(out).write_text(json.dumps(res, indent=1) + "\n")
print(f"{top} {r['verdict']} checked {r['checked']} ok {r['ok']} fails {res['fail_counts']}")
for x in rows: print(f"   {x['dir']:6s} {x['cls']:9s} {x['sub'][:40]:40s} {x['bus']}{x['bits']} ({x['n']})")
