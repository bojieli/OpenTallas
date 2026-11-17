#!/usr/bin/env python3
"""Re-read an exported gate-level netlist (6_final.v / native V) and fail closed on alias cycles.

SPEPRD3 11-16: an output BTerm moved onto an inserted delay buffer's net while the old internal net kept the port
name; write_verilog then wrote `HB4 (.A(xw_o[0]), .Y(n)); assign xw_o[0] = n;` for 566 pads: every padded output
resolved back to itself through the buffer.  The ODB was correct, the exported view was not.

FAIL when, in any module:
  * the `assign` alias graph has a cycle (a = b; b = a), or an assign aliases a net to itself;
  * an assigned net reaches itself again through one-input/one-output cells (buffers / inverters / delay cells):
    `assign p = n` with a BUF/INV/HB driving n from p (the output alias resolves back to itself).
Constants, concatenations and part selects with expressions are not aliases and are skipped.
Usage: netlist_alias_check.py NETLIST.v [--json OUT]   exit 0 PASS, 1 FAIL, 2 unreadable."""
import argparse
import json
import re
import sys
from pathlib import Path

ID = r"(?:\\\S+|[A-Za-z_][A-Za-z0-9_$]*)(?:\s*\[\s*\d+\s*\])?"
ASSIGN = re.compile(r"^\s*assign\s+(" + ID + r")\s*=\s*(" + ID + r")\s*$", re.S)
INST = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_$]*)\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\((.*)\)\s*$", re.S)
PIN = re.compile(r"\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*(" + ID + r")?\s*\)")
# one-input / one-output standard cells: the input pin and the output pin (ASAP7 BUF / INV / HB / CKINVDC / ...)
BUF_PINS = {("A", "Y")}
KEYWORDS = {"module", "endmodule", "input", "output", "inout", "wire", "reg", "assign", "supply0", "supply1", "tri"}


def norm(n):
    n = n.strip()
    if n.startswith("\\"):
        return n.rstrip()
    return re.sub(r"\s+", "", n)


def statements(text):
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    mod, buf = None, []
    for raw in text.split(";"):
        s = raw.strip()
        while s.startswith("endmodule"):
            yield mod, "endmodule"
            mod, s = None, s[len("endmodule"):].strip()
        m = re.match(r"module\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)", s)
        if m:
            mod = m.group(1)
            yield mod, "module"
            continue
        if s:
            yield mod, s


def check(text):
    mods = {}
    for mod, s in statements(text):
        if s in ("module", "endmodule"):
            if s == "module":
                mods.setdefault(mod, dict(assign=[], buf=[]))
            continue
        d = mods.setdefault(mod, dict(assign=[], buf=[]))
        m = ASSIGN.match(s)
        if m:
            d["assign"].append((norm(m.group(1)), norm(m.group(2))))
            continue
        w = s.split(None, 1)[0] if s.split() else ""
        if w in KEYWORDS:
            continue
        m = INST.match(s)
        if m:
            pins = {p: norm(n) for p, n in PIN.findall(m.group(3)) if n}
            if len(pins) == 2 and tuple(sorted(pins)) in {tuple(sorted(x)) for x in BUF_PINS}:
                for i, o in BUF_PINS:
                    if i in pins and o in pins:
                        d["buf"].append((m.group(2), pins[i], pins[o]))
    problems, stats = [], dict(modules=len(mods), assigns=0, buffers=0)
    for mod, d in mods.items():
        stats["assigns"] += len(d["assign"])
        stats["buffers"] += len(d["buf"])
        # alias graph: rhs -> lhs (value flows from rhs into lhs), buffers: in -> out
        g = {}
        for lhs, rhs in d["assign"]:
            if lhs == rhs:
                problems.append(dict(module=mod, kind="self_alias", net=lhs))
            g.setdefault(rhs, []).append(("assign", lhs))
        for inst, i, o in d["buf"]:
            g.setdefault(i, []).append((inst, o))
        assigned = {lhs for lhs, _ in d["assign"]}
        # iterative DFS cycle search over the alias + buffer graph; report each cycle once (by its first node)
        color, seen_cycles = {}, set()
        for start in list(g):
            if color.get(start):
                continue
            stack, path, onpath = [(start, iter(g.get(start, ())))], [start], {start: 0}
            color[start] = 1
            while stack:
                node, it = stack[-1]
                nxt = next(it, None)
                if nxt is None:
                    stack.pop(); path.pop(); onpath.pop(node, None); color[node] = 2
                    continue
                via, n2 = nxt
                if n2 in onpath:
                    cyc = path[onpath[n2]:]
                    key = frozenset(cyc)
                    if key not in seen_cycles and (any(x in assigned for x in cyc)):
                        seen_cycles.add(key)
                        problems.append(dict(module=mod, kind="alias_cycle", nets=cyc + [n2]))
                    continue
                if color.get(n2):
                    continue
                color[n2] = 1
                onpath[n2] = len(path); path.append(n2)
                stack.append((n2, iter(g.get(n2, ()))))
    return problems, stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("netlist")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    try:
        text = Path(a.netlist).read_text(errors="replace")
    except OSError as e:
        print(f"NETLIST_ALIAS UNREADABLE {a.netlist}: {e}")
        return 2
    problems, stats = check(text)
    if not stats["modules"]:
        problems.append(dict(kind="no_module", net=None))       # zero objects measured is never a PASS
    rec = dict(netlist=str(Path(a.netlist).resolve()), verdict="FAIL" if problems else "PASS",
               problems=len(problems), first=problems[:20], **stats)
    if a.json:
        Path(a.json).write_text(json.dumps(rec, indent=1) + "\n")
    print(f"NETLIST_ALIAS {rec['verdict']} problems {len(problems)} modules {stats['modules']} assigns {stats['assigns']} "
          f"buffers {stats['buffers']}" + (f" first {json.dumps(problems[0])}" if problems else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
