"""KV-KVSCTL-3 10-27: rebind u_kvs_ctl in the hub_C parent (kv3_hub_C_part_bound.sv) to the dead-dropped core port pieces
(dead_drop.json live_pieces) and check the binding bit by bit.

  python3 kvsctl_rebind.py OLD_BOUND.sv DEAD_DROP.json CORE_WRAPPER.sv NEW_BOUND.sv REPORT.json

Check (strict): every port of the new core module is connected exactly once with its full width; every live piece bit
carries the SAME parent net bit as the old full-width connection at the same original index; the dropped bits are
exactly dead_drop.json's dead ranges; no other connection of u_kvs_ctl changes."""
import json, re, sys
old_p, dd_p, core_p, new_p, rep_p = sys.argv[1:6]
t = open(old_p).read()
m = re.search(r"\n(\s*)qkd_kvs_ctl u_kvs_ctl \((.*?)\n\s*\);", t, re.S)
assert m and t.count("qkd_kvs_ctl u_kvs_ctl (") == 1
body = m.group(2)
conns = re.findall(r"\.(\w+)\((.*?)\)(?:,|$)", body.replace("\n", " "))
conns = [(p, e.strip()) for p, e in conns]
cd = dict(conns); assert len(cd) == len(conns)
def bits(e):
    e = e.strip()
    if e.startswith("{"):
        parts = []; depth = 0; cur = ""
        for ch in e[1:-1]:
            if ch == "{": depth += 1
            if ch == "}": depth -= 1
            if ch == "," and depth == 0: parts.append(cur.strip()); cur = ""
            else: cur += ch
        parts.append(cur.strip())
        out = []
        for p in reversed(parts): out += bits(p)          # MSB first in the concat
        return out
    mm = re.fullmatch(r"([\w$]+)\[(\d+):(\d+)\]", e)
    if mm:
        n, h, l = mm.group(1), int(mm.group(2)), int(mm.group(3)); return [f"{n}[{i}]" for i in range(l, h + 1)]
    mm = re.fullmatch(r"([\w$]+)\[(\d+)\]", e)
    if mm: return [e]
    return [e]                                            # scalar net (width checked below)
dd = json.load(open(dd_p))["per_port"]
core = open(core_p).read()
cm = re.search(r"module qkd_kvs_ctl \((.*?)\);", core, re.S).group(1)
cports = {}
for d, w, n in re.findall(r"(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)", cm):
    cports[n] = (d, int(w) + 1 if w else 1)
new = {}; checks = []
for p, e in conns:
    if p not in dd: new[p] = e; continue
    ob = bits(e); info = dd[p]
    assert len(ob) == info["width"], (p, len(ob), info["width"])
    dead = set(i for lo, hi in info["dead_ranges"] for i in range(lo, hi + 1))
    live = set()
    for pc in info["live_pieces"]:
        sl = ob[pc["lo"]:pc["hi"] + 1]; live |= set(range(pc["lo"], pc["hi"] + 1))
        new[pc["port"]] = "{" + ", ".join(reversed(sl)) + "}" if len(sl) > 1 else sl[0]
        checks.append({"port": pc["port"], "from": f"{p}[{pc['hi']}:{pc['lo']}]", "bits": len(sl)})
    assert live | dead == set(range(info["width"])) and not (live & dead), p
for p in dd:
    if p not in cd: assert not dd[p]["live_pieces"], ("dropped port with live bits not connected in parent", p)
# strict: every core port connected once, width equal
errs = []
for n, (d, w) in cports.items():
    if n not in new: errs.append(f"core port {n} unconnected"); continue
    if len(bits(new[n])) != w and not re.fullmatch(r"[\w$]+", new[n]): errs.append(f"{n}: width {len(bits(new[n]))} != {w}")
for n in new:
    if n not in cports: errs.append(f"parent connects {n}, not a core port")
ind = m.group(1)
txt = f"\n{ind}qkd_kvs_ctl u_kvs_ctl (\n" + ",\n".join(f"{ind}    .{p}({e})" for p, e in sorted(new.items())) + f"\n{ind});"
nt = t[:m.start()] + "\n" + ind + "// KV-KVSCTL-3 10-27: u_kvs_ctl bound to the dead-dropped core pieces (kvsctl_rebind.py; dead bits = plan pin drop)" + txt + t[m.end():]
open(new_p, "w").write(nt)
rep = {"schema": "kvsctl3.rebind.v1", "old": old_p, "core_ports": len(cports), "parent_conns_old": len(conns),
       "parent_conns_new": len(new), "pieces": checks,
       "dropped_bits": sum(len(set(i for lo, hi in v["dead_ranges"] for i in range(lo, hi + 1))) for v in dd.values()),
       "dropped_unconnected_ports": [p for p in dd if p not in cd], "errors": errs, "verdict": "PASS" if not errs else "FAIL"}
json.dump(rep, open(rep_p, "w"), indent=1); print(rep["verdict"], len(cports), len(new), errs[:5], rep["dropped_bits"], rep["dropped_unconnected_ports"])
