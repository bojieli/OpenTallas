"""Scope the module-level loop integers i/j/b of ot_hgi_fp4qdq into each always block that uses them (0-cycle change)."""
import re, sys
p = sys.argv[1]; s = open(p).read()
assert s.count("    integer i, j, b;\n") == 1
s = s.replace("    integer i, j, b;\n", "    // HBM-CORES-KITS-1: loop integers are process-local (rtl_lint check -assert: shared module-scope\n"
              "    // integers were multi-driven across clocked processes); behaviour unchanged.\n")
lines = s.split("\n"); out = []; k = 0; n = 0
while k < len(lines):
    L = lines[k]
    m = re.match(r"^(\s*)always (@\([^)]*\)) begin\s*$", L)
    if m:
        # find the block end by begin/end depth
        d = 0; e = k
        for e in range(k, len(lines)):
            d += len(re.findall(r"\bbegin\b", lines[e])) - len(re.findall(r"\bend\b", lines[e]))
            if d == 0: break
        body = "\n".join(lines[k + 1:e])
        used = [v for v in ("i", "j", "b") if re.search(r"(?<![\w.\['])%s\s*=(?!=)" % v, body)]
        if used:
            n += 1
            L = f"{m.group(1)}always {m.group(2)} begin : p_lv{n}\n{m.group(1)}    integer {', '.join(used)};"
    out.append(L); k += 1
open(p, "w").write("\n".join(out)); print("scoped blocks", n)
