#!/usr/bin/env python3
"""HEAD-CORE-LAT-R5 /ELEMB: port-bind check of a synthesized core netlist against the die-bound abstract LEF.
Compares bit-level signal ports (name[bit], direction) of module TOP in NETLIST with the LEF MACRO pins (POWER/GROUND
excluded).  Ports listed with --ft (the 12.2a1 island feed-through ports) are reported separately, not as mismatches;
--removed lists abstract pins the island kit intentionally replaces (clk -> ft_mstrap_i).
usage: head_bind_check.py NETLIST.v TOP ABSTRACT.lef OUT.json [--ft p1,p2,..] [--removed clk]"""
import json
import re
import sys


def lef_pins(t):
    out = {}
    for name, blk in re.findall(r"^\s*PIN (\S+)\n(.*?)^\s*END \1\s*$", t, re.M | re.S):
        if re.search(r"USE (POWER|GROUND)", blk):
            continue
        out[name] = re.search(r"DIRECTION (\w+)", blk).group(1).upper()
    return out


def net_ports(t, top):
    m = re.search(r"\bmodule\s+\\?%s\s*\((.*?)\);(.*?)\bendmodule" % re.escape(top), t, re.S)
    assert m, "module %s not found" % top
    body = m.group(2)
    out = {}
    for d, rng, names in re.findall(r"^\s*(input|output|inout)\s+(?:wire\s+)?(\[\s*\d+\s*:\s*\d+\s*\])?\s*([^;]+);", body, re.M):
        for n in [x.strip().lstrip("\\") for x in names.split(",") if x.strip()]:
            if rng:
                hi, lo = map(int, re.findall(r"\d+", rng))
                for b in range(min(hi, lo), max(hi, lo) + 1):
                    out["%s[%d]" % (n, b)] = d.upper()
            else:
                out[n] = d.upper()
    return out


a = sys.argv[1:]
opt = {}
for k in ("--ft", "--removed"):
    if k in a:
        i = a.index(k)
        opt[k] = [x for x in a[i + 1].split(",") if x]
        del a[i:i + 2]
nl, top, lef, out = a
N = net_ports(open(nl).read(), top)
L = lef_pins(open(lef).read())
ft, rem = set(opt.get("--ft", [])), set(opt.get("--removed", []))
only_n = sorted(p for p in N if p not in L and p not in ft)
only_l = sorted(p for p in L if p not in N and p not in rem)
dir_bad = sorted(p for p in N if p in L and N[p] != L[p])
r = dict(netlist=nl, top=top, abstract=lef, netlist_signal_bits=len(N), abstract_signal_bits=len(L),
         ft_ports=sorted(ft & set(N)), removed_by_island=sorted(rem & set(L)), only_in_netlist=only_n,
         only_in_abstract=only_l, direction_mismatch=dir_bad,
         verdict="PASS" if not (only_n or only_l or dir_bad) else "FAIL")
json.dump(r, open(out, "w"), indent=1)
print("BIND", r["verdict"], "netlist", len(N), "abstract", len(L), "only_netlist", len(only_n), "only_abstract", len(only_l),
      "dir", len(dir_bad), "ft", len(r["ft_ports"]), "removed", r["removed_by_island"])
