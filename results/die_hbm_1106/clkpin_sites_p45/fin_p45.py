#!/usr/bin/env python3
"""DIE-HBM-82 d44v part 45 packaging (after mk_p45.py): event record, README line, SHA256SUMS.   fin_p45.py REPO"""
import gzip, hashlib, json, sys
from pathlib import Path
D = Path(sys.argv[1]) / "physical/die_plan/hbm/plan_of_record/d44v"
sha = lambda b: hashlib.sha256(b).hexdigest()
CE = json.loads(gzip.decompress((D / "clock_entries.json.gz").read_bytes()))
MODS = ["ot_hbm_svc_vm_kshare_splitstrap__v8e478a", "ot_hbm_svc_vm_kshare_splitstrap__v700685", "ot_hgi_sm_xload_cl2_ctlx",
        "ot_svgr_bk", "ot_wbq_root", "ot_wbq_sw"]
sites = {}
for m in MODS:
    es = [e for b in CE.values() if isinstance(b, dict) for e in b.values() if isinstance(e, dict) and e.get("module") == m]
    sites[m] = dict(entries=len(es), clock_pin_sites_um=es[0]["clock_pin_sites_um"])
ev = {"schema": "opentallas.hbm_plan_event.part45",
      "by": "DIE-HBM-82 11-06 (p35 clock_pin_sites_um class, found by DIE-HBM-82-B128 14:34)",
      "bug": "part 35 (510f347b9f) moved one clock pin per core in the pin tables but left clock_entries.json without "
             "clock_pin_sites_um, so gen_core_kit_hbm.py --clock-pin-entry on spread the clock pins around the old entry "
             "and every new kit missed its own table by one clock pin (uncountable)",
      "change": "clock_entries.json: clock_pin_sites_um = the current main pin-table positions of the entry's clock pins "
                "(port + merged_clock_ports), on every entry of the module; xy_um / island / ports unchanged; pin tables and "
                "die_plan.json unchanged (pattern 658aba8470)",
      "modules": sites,
      "not_touched": {"ot_hgi_coll_inj_idx_join_rg": "sites = table already (658aba8470)",
                      "ot_hgi_coll_tkm_m_tp192__root": "sites = table already",
                      "ot_hgi_sfu_split3_lane_core__idpin__master table, ot_pdie_serdes_rx table": "no longer used by the plan",
                      "ot_hgi_sfu_split3_lane_core_fr": "DIE-HBM-82-B128 reverts its two tables to pre-p35 (signed DB site) separately"},
      "proof": "results/die_hbm_1106/clkpin_sites_p45/cmp_p45.txt: kits by gen_core_kit_hbm.py --clock-pin-entry on, base (main) "
               "6/6 MISMATCH one clock pin, part 45 6/6 MATCH; io.tcl base->new differs only in that one pin per core",
      "pin_cycles": "none",
      "replay": "results/die_hbm_1106/clkpin_sites_p45/replay_p45.sh"}
(D / "part45_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 45 (DIE-HBM-82 11-06, p35 clock-site class): clock_entries.json gets "
              "clock_pin_sites_um = the current pin-table clock pin positions for kshare v8e478a / v700685, xload ctlx, svgr_bk, "
              "wbq_root, wbq_sw (part 35 moved one clock pin per table but not the entries, so --clock-pin-entry kits missed "
              "their tables); entry xy, tables and die_plan unchanged; no pin cycles; part45_event.json; replay "
              "results/die_hbm_1106/clkpin_sites_p45.\n")
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
new = {"clock_entries.json": sha(gzip.decompress((D / "clock_entries.json.gz").read_bytes())),
       "part45_event.json": sha((D / "part45_event.json").read_bytes())}
ch = []
for i, (a, n) in enumerate(L):
    if n in new and new[n] != a:
        L[i] = [new[n], n]; ch.append(n)
if "part45_event.json" not in {n for _, n in L}:
    L.append([new["part45_event.json"], "part45_event.json"])
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS changed", ch)
