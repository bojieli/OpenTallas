#!/usr/bin/env python3
"""cmp_p45.py R : io.tcl clock pin centres vs the plan pin table, per core, base and new kits; io.tcl base->new diff lines."""
import json, re, sys, glob
from pathlib import Path
R = Path(sys.argv[1])
MODS = ["ot_hbm_svc_vm_kshare_splitstrap__v8e478a", "ot_hbm_svc_vm_kshare_splitstrap__v700685", "ot_hgi_sm_xload_cl2_ctlx",
        "ot_svgr_bk", "ot_wbq_root", "ot_wbq_sw"]
rx = re.compile(r"place_pin -pin_name \{([^}]*)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}")
def io(p):
    return {m.group(1): (float(m.group(3)), float(m.group(4))) for m in rx.finditer(p.read_text())}
P = json.load(open(R / "plan_new/die_plan.json"))
CE = json.load(open(R / "plan_new/clock_entries.json"))
for m in MODS:
    pf = {h["pins_file"] for T in P["partition_types"].values() for h in T.get("hard_cores", []) if h.get("module") == m}.pop()
    tab = {q["name"]: q for q in json.load(open(R / "plan_new" / pf))}
    sites = next(e["clock_pin_sites_um"] for b in CE.values() for e in b.values() if isinstance(e, dict) and e.get("module") == m)
    res = {}
    for N in ("base", "new"):
        f = Path(glob.glob(str(R / f"kits_{N}/{m}/*/io.tcl"))[0])
        a = io(f)
        res[N] = a
        bad = {n: (a[n], (tab[n]["x"], tab[n]["y"])) for n in sites if abs(a[n][0] - tab[n]["x"]) > 1e-4 or abs(a[n][1] - tab[n]["y"]) > 1e-4}
        print(f"{N:4} {m}: clock pins {', '.join(f'{n} io {a[n][0]:.3f}' for n in sorted(sites))}; table {', '.join(f'{n} {tab[n][chr(120)]:.3f}' for n in sorted(sites))}; "
              + ("MATCH" if not bad else f"MISMATCH {len(bad)}"))
    d = sorted(n for n in set(res["base"]) | set(res["new"]) if res["base"].get(n) != res["new"].get(n))
    print(f"     io.tcl pins changed base->new: {d} (of {len(res['new'])})")
