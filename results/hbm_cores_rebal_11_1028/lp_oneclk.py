#!/usr/bin/env python3
"""HBM-CORES-REBAL-4 die-local plan delta (same form as HBM-CORES-REBAL-2 side_oneclk.py): lanes__canon_cf1e77 clock
buses clk_bank[3:0] / clk_bank_macro[23:0] / clk_insert[15:0] / clk_lane[31:0] (76 bits) are aliases of ONE clock
(kit SDC create_clock clk on all 4 ports; plan clock entry merges the 4 ports at one tap) -> ONE scalar input pin
clk_bank at the clk_bank[0] site.  Non-clock pins byte-identical.  Also writes the oneclk canon wrapper (scalar
clk_bank replicated onto the 4 internal buses) into WRAPDIR.
  lanes_oneclk.py PLANDIR(copy, edited) CANON_WRAPPER_IN WRAPDIR_OUT"""
import json, re, sys, hashlib
from pathlib import Path
d, win, wdir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
MOD = "ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526"
BUS = {"clk_bank": 4, "clk_bank_macro": 24, "clk_insert": 16, "clk_lane": 32}
isck = lambda n: n.split("[")[0] in BUS and "[" in n
dig = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()
p = json.loads((d / "die_plan.json").read_text())
rep, done = [], {}
for tn, t in p["partition_types"].items():
    for h in t.get("hard_cores", []):
        if h["module"] != MOD:
            continue
        old = h["pins_file"]
        new = old[:-5] + "__oneclk.json"
        if old not in done:
            pins = json.loads((d / old).read_text())
            ck = [v for v in pins if isck(v["name"])]
            assert len(ck) == sum(BUS.values()), len(ck)
            data = [v for v in pins if not isck(v["name"])]
            assert not any(v["name"] in BUS for v in data)
            c = dict(next(v for v in ck if v["name"] == "clk_bank[0]")); c["name"] = "clk_bank"
            out = []
            for v in pins:
                if isck(v["name"]):
                    if v["name"] == "clk_bank[0]":
                        out.append(c)
                    continue
                out.append(v)
            assert [v for v in out if v["name"] != "clk_bank"] == data
            (d / new).write_text(json.dumps(out, indent=1) + "\n")
            done[old] = new
            rep.append(dict(module=MOD, old=old, new=new, clock_bits_old=len(ck), clock_bits_new=1, clk_site=c,
                            nonclock=len(data), nonclock_sha256=dig(data)))
        h["pins_file"] = done[old]
        h["note"] = h.get("note", "") + " | HBM-CORES-REBAL-4: 76 clock alias bits -> scalar clk_bank (oneclk pins)"
assert done, "module not in plan"
(d / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
ce = json.loads((d / "clock_entries.json").read_text()); n = 0
for part in ce.values():
    if isinstance(part, dict):
        for e in part.values():
            if isinstance(e, dict) and e.get("module") == MOD:
                assert sorted(e.get("merged_clock_ports") or []) == sorted(BUS), e
                e["merged_clock_ports"] = ["clk_bank"]; n += 1
(d / "clock_entries.json").write_text(json.dumps(ce, indent=1) + "\n")
# wrapper: scalar clk_bank port; the 4 buses become internal replicas of it
s = win.read_text()
head, body = s.split(");", 1)
for b, w in BUS.items():
    pat = re.compile(r"^\s*input\s+wire\s+\[" + str(w - 1) + r":0\]\s+" + b + r"\s*,?\s*$\n", re.M)
    assert len(pat.findall(head)) == 1, b
    head = pat.sub("" if b != "clk_bank" else "    input wire clk_bank,\n", head)
head = re.sub(r",(\s*)$", r"\1", head)                       # no dangling comma before ');'
for b in BUS:
    body = re.sub(r"\b" + b + r"\b", b + "_v", body)
decl = "\n" + "".join(f"    wire [{w - 1}:0] {b}_v = {{{w}{{clk_bank}}}};  // HBM-CORES-REBAL-4 oneclk alias\n"
                      for b, w in BUS.items())
wdir.mkdir(parents=True, exist_ok=True)
(wdir / f"{MOD}.sv").write_text(head + ");" + decl + body)
(d / "lanes_oneclk_report.json").write_text(json.dumps(dict(pins=rep, clock_entries_edited=n), indent=1) + "\n")
print(json.dumps(dict(pins=[(r["module"], r["clock_bits_old"], r["nonclock"]) for r in rep], entries=n)))
