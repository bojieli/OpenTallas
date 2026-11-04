#!/usr/bin/env python3
"""DIE-HBM-65 11-04, COORD 07:34 (2): wrapper diff for the oneclk plan event.
    oneclk_wrapper_diff.py NEW.sv (--ref OLD.sv | --pass-through)
--ref: the unified line diff against the old wrapper; every changed line must be a comment, a removed clock input, the added
`input wire clk`, or a connection whose new value is clk / {N{clk}} and whose old value names only clock buses.
--pass-through: NEW has no old wrapper (RTL top had the plan name): every connection must be .n(n) or .n(clk / {N{clk}}).
Prints the changed lines and OK or the lines that break the rule; exit 1 on any."""
import argparse, difflib, re, sys
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("new"); ap.add_argument("--ref"); ap.add_argument("--pass-through", action="store_true"); a = ap.parse_args()
CK = r"(clk|clk_[a-z0-9_]+|[a-z0-9_]*_clk|ck|ck_[a-z0-9_]+|[a-z0-9_]*clk_[a-z0-9_]*)"
NEWCONN = re.compile(r"\.\w+\(\s*(clk|\{\d+\{clk\}\})\s*\),?")
new = Path(a.new).read_text().splitlines()
bad, shown, k = [], [], 0
def strip(l): return re.sub(r"//.*", "", l).strip()
if a.pass_through:
    for l in new:
        for m in re.finditer(r"\.(\w+)\(\s*([^()]*?)\s*\)", strip(l)):
            k += 1
            if m[2] == m[1]: continue
            if re.fullmatch(r"clk|\{\d+\{clk\}\}", m[2]) and re.fullmatch(CK, m[1]): shown.append(l.strip()); continue
            bad.append(l.strip())
else:
    old = [re.sub(r"(?m)^module (\S+?)__fcore\b", r"module \1", x) for x in Path(a.ref).read_text().splitlines()]
    for d in difflib.unified_diff([strip(x) for x in old], [strip(x) for x in new], lineterm="", n=0):
        if d.startswith(("---", "+++", "@@")) or not d[1:].strip(): continue
        k += 1; t = d[1:].strip(); shown.append(d)
        if d[0] == "-" and re.fullmatch(r"input\s+wire\s*(\[\d+:0\])?\s*" + CK + r"\s*,?", t): continue
        if d[0] == "+" and re.fullmatch(r"input\s+wire\s+clk\s*,?", t): continue
        if d[0] == "+" and NEWCONN.fullmatch(t): continue
        if d[0] == "-":
            m = re.fullmatch(r"\.\w+\(\s*(.*?)\s*\),?", t)
            names = re.findall(r"[A-Za-z_]\w*", re.sub(r"\[[^\]]*\]", "", m[1])) if m else []
            if m and names and all(re.fullmatch(CK, n) for n in names): continue
        bad.append(d)
for s in shown: print(s)
print(("OK" if not bad else "FAIL"), "connections checked" if a.pass_through else "changed lines", k, "clock lines shown", len(shown), "off-rule", len(bad))
for b in bad[:40]: print("OFF-RULE", b)
sys.exit(1 if bad else 0)
