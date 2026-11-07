#!/usr/bin/env python3
"""DIE-HBM-82 d44v part 50 packaging (after mk_p50.py): event record, README line, SHA256SUMS.   fin_p50.py REPO"""
import gzip, hashlib, json, sys
from pathlib import Path
D = Path(sys.argv[1]) / "physical/die_plan/hbm/plan_of_record/d44v"
sha = lambda b: hashlib.sha256(b).hexdigest()
CE = json.loads(gzip.decompress((D / "clock_entries.json.gz").read_bytes()))
MODS = ["ot_hbm_idx_qctl_static", "ot_hbm_static_cfg_collar_idx256r", "ot_pdie_serdes_rx_bm3_rest"]
QNEW = "cores/ot_hbm_idx_qctl_static__194.832x82.08__d44v_centry_p50.json"
sites = {}
for m in MODS:
    es = [e for b in CE.values() if isinstance(b, dict) for e in b.values() if isinstance(e, dict) and e.get("module") == m]
    sites[m] = dict(entries=len(es), clock_pin_sites_um=es[0]["clock_pin_sites_um"])
ev = {"schema": "opentallas.hbm_plan_event.part50",
      "by": "DIE-HBM-82 11-06 (plan owner; scan by DIE-HBM-82-P40: --clock-pin-entry io.tcl vs pin table, 84 d44v views)",
      "bug": "clock_entries.json without clock_pin_sites_um: gen_core_kit_hbm.py --clock-pin-entry on spreads the clock pins "
             "around the entry xy, so kits of these cores miss their own table by 1-2 clock pins (uncountable rebuilds)",
      "change": {"ot_hbm_static_cfg_collar_idx256r, ot_pdie_serdes_rx_bm3_rest": "clock_pin_sites_um = the pin-table clock "
                 "pin points (table and entry xy unchanged)",
                 "ot_hbm_idx_qctl_static": "plan entry and die clock taps are the core centre (99.36, 64.8) and the counted DB "
                 "sits there under the release_tree_plan APPROVED_PIN_EVENTS centre-entry exception (COORD 11-03 00:1x); the "
                 "table had the clock pins on the S face.  New table " + QNEW + " = the d35a table with clk_program / "
                 "clk_program_mem at (99.384, 64.8) / (99.48, 64.8) (the generator's entry points), 4 instances repointed, "
                 "sites = those points.  The APPROVED_PIN_EVENTS qctl entry can be removed once this is on main."},
      "modules": sites,
      "not_touched": {"ot_hbm_sm_vm_wr_q_t_lanes4": "6 clock pins are M4 E-face table pins (x 142.464, y 13.85-14.86); "
                      "the clock_pin_sites_um form is M5-only, so a site entry cannot express them; reported to DIE-HBM-82"},
      "proof": "results/die_hbm_1106/clkpin_sites_p50/cmp_p50.txt",
      "pin_cycles": "none",
      "replay": "results/die_hbm_1106/clkpin_sites_p50/replay_p50.sh"}
(D / "part50_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 50 (DIE-HBM-82 11-06, clock-site scan): clock_entries.json gets "
              "clock_pin_sites_um = the plan clock pin points for static_cfg_collar_idx256r and pdie_serdes_rx_bm3_rest "
              "(table points) and idx_qctl_static (centre entry; new table " + QNEW + " with the two clock pins at the "
              "entry, 4 instances repointed, lands the COORD 11-03 centre-entry pin event); --clock-pin-entry kits of these "
              "cores matched neither; no pin cycles; part50_event.json; replay results/die_hbm_1106/clkpin_sites_p50.\n")
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
new = {"clock_entries.json": sha(gzip.decompress((D / "clock_entries.json.gz").read_bytes())),
       "die_plan.json": sha(gzip.decompress((D / "die_plan.json.gz").read_bytes())),
       "part50_event.json": sha((D / "part50_event.json").read_bytes()),
       QNEW: sha((D / QNEW).read_bytes())}
ch = []
for i, (a, n) in enumerate(L):
    if n in new and new[n] != a:
        L[i] = [new[n], n]; ch.append(n)
for n in ("part50_event.json", QNEW):
    if n not in {x for _, x in L}:
        L.append([new[n], n]); ch.append(n + " (new)")
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS changed", ch)
