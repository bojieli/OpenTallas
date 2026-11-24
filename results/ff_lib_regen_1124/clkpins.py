import re, sys
t = open(sys.argv[1], errors="replace").read()
ms = list(re.finditer(r'\bpin\s*\(\s*"?([^")]+)"?\s*\)\s*\{', t))
out = []
for i, m in enumerate(ms):
    end = ms[i + 1].start() if i + 1 < len(ms) else len(t)
    head = t[m.end():end].split("timing")[0]
    if re.search(r'^\s*clock\s*:\s*true\s*;', head, re.M) and m.group(1) not in ("VDD", "VSS"):
        out.append(m.group(1))
print("\n".join(out))
