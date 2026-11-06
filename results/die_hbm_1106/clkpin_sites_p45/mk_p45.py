#!/usr/bin/env python3
"""DIE-HBM-82 d44v part 45: clock_pin_sites_um for the p35 clock-pin cores (class fix, pattern 658aba8470).

Part 35 (510f347b9f) moved one clock pin in the pin tables of 12 cores (0.096-0.48 um along x, so the two clock pins of
each core no longer coincide) but left d44v/clock_entries.json as it was: xy = the old merged entry, no
clock_pin_sites_um.  gen_core_kit_hbm.py --clock-pin-entry on then spreads the named clock pins its own way around the
entry (every 2nd M5 track) and the kit never matches its own table, so every new build of those cores is uncountable.
Fix: add clock_pin_sites_um = the CURRENT main pin-table positions of exactly the clock pins the generator selects
(port + merged_clock_ports), on every clock entry of the module; xy / island / everything else unchanged.
Cores: kshare v8e478a, kshare v700685, xload ctlx, svgr_bk, wbq_root, wbq_sw.  Not touched: inj_idx_join_rg and
tkm root (already carry sites = table, 658aba8470 / tkm_clock_pin_sites_1106), split3 lane_core master idpin and
serdes rx (tables no longer in the plan), lane_core_fr (DIE-HBM-82-B128 reverts its tables to pre-p35 separately).
    mk_p45.py D44V_DIR"""
import gzip, json, re, sys
from pathlib import Path
D = Path(sys.argv[1])
ld = lambda p: json.loads(gzip.decompress(p.read_bytes()) if p.name.endswith(".gz") else p.read_text())
MODS = ["ot_hbm_svc_vm_kshare_splitstrap__v8e478a", "ot_hbm_svc_vm_kshare_splitstrap__v700685", "ot_hgi_sm_xload_cl2_ctlx",
        "ot_svgr_bk", "ot_wbq_root", "ot_wbq_sw"]
P = ld(D / "die_plan.json.gz")
CE = ld(D / "clock_entries.json.gz")
base = lambda n: re.sub(r"\[\d+\]$", "", n)
log = []
for m in MODS:
    pf = {h["pins_file"] for T in P["partition_types"].values() for h in T.get("hard_cores", []) if h.get("module") == m}
    assert len(pf) == 1, (m, pf)
    pf = pf.pop()
    p = D / pf
    tab = ld(p if p.exists() else Path(str(p) + ".gz"))
    ents = [e for b in CE.values() if isinstance(b, dict) for e in b.values() if isinstance(e, dict) and e.get("module") == m]
    sigs = {json.dumps([e.get("xy_um"), e.get("port"), sorted(e.get("merged_clock_ports") or [])]) for e in ents}
    assert ents and len(sigs) == 1, (m, sigs)
    assert all("clock_pin_sites_um" not in e for e in ents), m
    named = set(ents[0].get("merged_clock_ports") or []) | ({ents[0]["port"]} if ents[0].get("port") else set())
    sel = [q for q in tab if base(q["name"]) in named]
    assert len(sel) >= 2 and all(q["layer"] == "M5" for q in sel), (m, sel)
    sites = {q["name"]: [q["x"], q["y"]] for q in sorted(sel, key=lambda q: q["name"])}
    assert len({tuple(v) for v in sites.values()}) == len(sites), (m, sites)
    for e in ents:
        e["clock_pin_sites_um"] = sites
    log.append((m, len(ents), pf, sites))
b = (json.dumps(CE) + "\n").encode()
with open(D / "clock_entries.json.gz", "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
    g.write(b)
for x in log:
    print("P45", x[0], "entries", x[1], json.dumps(x[3]))
