#!/usr/bin/env python3
"""DIE-QC-2: clock-only SPEF from the combo GRT estimate (estimate_parasitics -global_routing -spef_file), with an
NDR what-if: R x rf and C x cf on the selected clock nets (16w: rf 0.0625, cf 2.2 = die_clock_mesh.py NDR table, the
same factors the INFRA-FIRST-QC mesh used).  Net/instance names lose the combo 'ck_' prefix so the SPEF annotates
clk/ctree.v directly.  usage: spef_ck.py IN_SPEF OUT_SPEF MODE(none|trunk|all) TREE_JSON CTREE_V [rf cf]"""
import json, re, sys
inp, outp, mode, treej, ctv = sys.argv[1:6]
rf, cf = (float(sys.argv[6]), float(sys.argv[7])) if len(sys.argv) > 7 else (0.0625, 2.2)
sel = set()
if mode != "none":
    t = json.load(open(treej)); N = t["nodes"]
    spine = {int(k) for k, n in N.items() if n.get("spine")} | {0}
    for m in re.finditer(r"BUFx\w+\s+(\w+)\s*\(\.A\((\w+)\),\s*\.Y\((\w+)\)\);", open(ctv).read()):
        inst, a, y = m.groups()
        if mode == "all":
            sel.add(y); continue
        mb = re.fullmatch(r"b(\d+)", inst); mr = re.fullmatch(r"r(\d+)_(\d+)", inst)
        if (mb and int(mb.group(1)) in spine) or (mr and N[mr.group(1)]["parent"] in spine):
            sel.add(y)
names = {}
out = open(outp, "w")
hdr, keep, cur, buf, nsel, nck = True, False, None, [], 0, 0
def unk(s):
    return names.get(s, s)
def strip(s):                        # *123 -> name; ck_X -> X ; ck_b1:Y -> b1:Y
    s = unk(s)
    return s[3:] if s.startswith("ck_") else s
def node(x):
    p = x.split(":"); p[0] = strip(p[0]); return ":".join(p)
sec = None
for line in open(inp):
    if hdr:
        if line.startswith("*NAME_MAP"):
            sec = "map"; continue
        if sec == "map":
            m = re.match(r"(\*\d+)\s+(\S+)", line)
            if m:
                names[m.group(1)] = m.group(2).replace("\\", ""); continue
            if line.strip() == "":
                continue
            sec = None
        if line.startswith("*D_NET"):
            hdr = False
        else:
            if line.startswith("*PORTS"):
                sec = "ports"; out.write(line); continue
            if sec == "ports" and line.strip() and not line.startswith("*"):
                if line.split()[0].startswith("t_") or line.split()[0] == "root":
                    out.write(line)
                continue
            if not line.startswith(("*NAME_MAP",)):
                out.write(line)
            continue
    if line.startswith("*D_NET"):
        _, n, c = line.split()[:3]
        nm = unk(n)
        keep = nm.startswith("ck_") or nm == "root" or nm.startswith("t_")
        cur = strip(n); s = cur in sel
        if keep:
            nck += 1; nsel += s
            out.write(f"*D_NET {cur} {float(c) * (cf if s else 1.0):.6g}\n")
        continue
    if not keep:
        continue
    st = line.split()
    if line.startswith(("*CONN", "*CAP", "*RES", "*END")):
        sec = line.strip()
        out.write(line); continue
    if line.startswith(("*I ", "*P ")):
        out.write(f"{st[0]} {node(st[1])} " + " ".join(st[2:]) + "\n"); continue
    if not st:
        out.write(line); continue
    if sec == "*CONN":
        out.write(f"{st[0]} {node(st[1])} " + " ".join(st[2:]) + "\n")
    elif sec == "*CAP" and len(st) == 3:
        out.write(f"{st[0]} {strip_node(st[1]) if False else ':'.join([strip(st[1].split(':')[0])] + st[1].split(':')[1:])} {float(st[2]) * (cf if s else 1.0):.6g}\n")
    elif sec == "*RES" and len(st) == 4:
        a, b = node(st[1]), node(st[2])
        out.write(f"{st[0]} {a} {b} {float(st[3]) * (rf if s else 1.0):.6g}\n")
    else:
        out.write(line)
out.close()
print("clock nets", nck, "scaled", nsel, "mode", mode, "rf", rf, "cf", cf)
