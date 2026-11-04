#!/usr/bin/env python3
"""DIE-HBM-63/REFORM 11-04 (OWNER TWO-STRIKES RE-FORM, class PORT-TREE-SKEW): one plan clock pin for a native multi-port core.

    mk_oneclk.py PLAN_DIR MODULE WRAPPER_OUT [--wrap OLD_WRAP.sv | --rename-top NEW_TOP --portlist PORTLIST]

Per-port CTS trees of unequal depth are the root of the reg2reg hold stops on the pgslice lanes and split3 ctl: every clock
port is the same 1.2-GHz domain and clock_entries.json already merges them at one centre entry.  The safe form is one tree:
  * PLAN_DIR/cores/<table>__oneclk.json: all CLK_RE pins removed, one pin `clk` at the middle clock pin's shape; every
    hard_cores[] row of MODULE repointed to it (die_plan.json, in PLAN_DIR, a plan copy);
  * WRAPPER_OUT: plan module MODULE with `clk` + the other plan pins; the same wiring as before, every clock bit from `clk`.
    From --wrap (text edit of the old wrapper, which becomes the wrapper itself) or, when the RTL top has the plan name,
    a pass-through around the renamed top (--rename-top, recipe field rename_top).
No arithmetic, no reset and no data pin changes; 0 added cycles.  Prints the new table sha256 for wrapper_by_pins_sha256."""
import argparse, hashlib, json, re
from pathlib import Path
CLK_RE = r"^(clk|clk_[a-z0-9_]+|[a-z0-9_]*_clk|ck|ck_[a-z0-9_]+|[a-z0-9_]*clk_[a-z0-9_]*)$"   # gen_core_kit_hbm.CLK_RE
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("module"); ap.add_argument("out")
ap.add_argument("--wrap"); ap.add_argument("--rename-top"); ap.add_argument("--portlist"); a = ap.parse_args()
pd = Path(a.plan); D = json.loads((pd / "die_plan.json").read_text())
rows = [c for t in D["partition_types"].values() for c in (t.get("hard_cores") or []) if c.get("module") == a.module and c.get("pins_file")]
files = sorted({c["pins_file"] for c in rows})
if len(files) != 1: raise SystemExit(f"{a.module}: pin tables {files}")
bus = lambda n: re.sub(r"\[\d+\]$", "", n)
T = json.loads((pd / files[0]).read_text())
ck = [p for p in T if re.match(CLK_RE, bus(p["name"]))]
if len({bus(p["name"]) for p in ck}) + len(ck) < 3: raise SystemExit(f"{a.module}: already one clock: {[p['name'] for p in ck]}")
mid = dict(sorted(ck, key=lambda p: (p["x"], p["y"]))[len(ck) // 2]); mid["name"] = "clk"
N = [p for p in T if p not in ck] + [mid]
nf = files[0][:-5] + "__oneclk.json"; (pd / nf).write_text(json.dumps(N, indent=1) + "\n")
for c in rows: c["pins_file"] = nf
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
sha = hashlib.sha256((pd / nf).read_bytes()).hexdigest()
ckbus = sorted({bus(p["name"]) for p in ck})
HDR = (f"// DIE-HBM-63/REFORM 11-04: planned common-root wiring; pin table {sha}.\n// Clock replicas {', '.join(ckbus)} all from clk "
       "(one 1.2-GHz domain, clock_entries merged_clock_ports); no other wiring changed.\n")
def width(expr, w):
    e = expr.strip()
    if e.startswith("{"): return sum(width(x, w) for x in e[1:-1].split(","))
    m = re.fullmatch(r"(\w+)\[(\d+):(\d+)\]", e)
    if m: return int(m[2]) - int(m[3]) + 1
    if re.fullmatch(r"\w+\[\d+\]", e): return 1
    return w[e]
if a.wrap:
    s = Path(a.wrap).read_text(); s = re.sub(r"(?m)^module (\S+?)__fcore\b", r"module \1", s)
    w = {}
    for m in re.finditer(r"input\s+wire\s*(?:\[(\d+):0\])?\s*(\w+)\s*,?", s):
        if m[2] in ckbus: w[m[2]] = int(m[1] or 0) + 1
    if set(w) != set(ckbus): raise SystemExit(f"{a.module}: clock decls {sorted(w)} != {ckbus}")
    s = re.sub(r"(?m)^\s*input\s+wire\s*(?:\[\d+:0\])?\s*(" + "|".join(map(re.escape, ckbus)) + r")\s*,?\s*(//.*)?\n", "", s)
    s, k = re.subn(r"(module\s+" + re.escape(a.module) + r"\s*\(\s*\n)", r"\1    input wire clk,\n", s, count=1)
    if k != 1: raise SystemExit(f"{a.module}: module header not found")
    names = "|".join(map(re.escape, ckbus))
    def conn(m):
        e = m[2]
        if not re.search(r"\b(" + names + r")\b", e): return m[0]
        n = width(e, w)
        return f".{m[1]}({'clk' if n == 1 else '{%d{clk}}' % n})"
    s = re.sub(r"\.(\w+)\(\s*([^()]*?)\s*\)", conn, s)
    left = re.sub(r"\.\w+\(", "(", re.sub(r"//.*", "", s))   # instance port names may keep the clock's name
    if re.search(r"\b(" + "|".join(re.escape(n) for n in ckbus if n != "clk") + r")\b", left): raise SystemExit(f"{a.module}: clock name left in wrapper")
    txt = HDR + s
else:
    if not (a.rename_top and a.portlist): raise SystemExit("--wrap or --rename-top + --portlist")
    d, c = ["    input wire clk"], []
    for l in Path(a.portlist).read_text().splitlines()[1:]:
        k, wd, n = l.split(); w_ = int(wd[1:].split(":")[0]) + 1
        if n in ckbus:
            c.append(f"        .{n}({'clk' if w_ == 1 else '{%d{clk}}' % w_})"); continue
        d.append(f"    {k} wire {'[%d:0] ' % (w_ - 1) if w_ > 1 else ''}{n}"); c.append(f"        .{n}({n})")
    txt = HDR + "`default_nettype none\nmodule " + a.module + " (\n" + ",\n".join(d) + "\n);\n    " + a.rename_top + " u_core (\n" + ",\n".join(c) + "\n    );\nendmodule\n`default_nettype wire\n"
Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(txt)
print(a.module, "table", nf, "sha", sha, "pins", len(T), "->", len(N), "clock buses", ckbus, "rows", len(rows))
