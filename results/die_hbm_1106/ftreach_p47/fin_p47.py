#!/usr/bin/env python3
"""DIE-HBM-82-G0C d44v part 47 packaging: event record, README line, SHA256SUMS.   fin_p47.py REPO"""
import gzip, hashlib, json, sys
from pathlib import Path
R = Path(sys.argv[1]); D = R / "physical/die_plan/hbm/plan_of_record/d44v"
L = json.loads((R / "results/die_hbm_1106/ftreach_p47/ledger_p47.json").read_text())
s = L["summary"]
ev = {"schema": "opentallas.hbm_plan_event.part47", "by": "DIE-HBM-82-G0C 11-06 (G0C class A: ft reach, stations/hops/reach)",
      "change": "ft_s0_resite.py per type (normal FT slots whose real per-bit chain has a hop > 364.5 um): internal stations re-sited on free "
                "legal sites; +1..+3 stations where no count fits (PIN CYCLES); slots no count fits are kept and listed",
      "summary": s, "pin_cycles": "see ledger pin_cycles_lanes (latency.lanes += delta of schema.Plan.lane_latency (gen.py latency) event - base)",
      "compiler": "the added lane cycles are not folded into ext/crossing_latency / compiler_core_delta here (TOK lane, as part 37)",
      "ledger": "results/die_hbm_1106/ftreach_p47/ledger_p47.json", "replay": "results/die_hbm_1106/ftreach_p47/replay_p47.sh"}
(D / "part47_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + f"\n\nEvent part 47 (DIE-HBM-82-G0C 11-06, G0C class A ft reach): one ft_s0_resite.py pass over the {len((R / 'results/die_hbm_1106/ftreach_p47/types_p47.txt').read_text().split())} types with a "
              f"'stations' row: {s['slots_resited']} slots re-sited, {s['slots_with_added_stations']} with added stations (+{s['added_station_cycles']} station cycles), "
              f"{s['lanes_latency_changed']} lanes' latency.lanes changed (PIN CYCLES, ledger_p47.json), {len(s['kept'])} slots kept (no chain fits); part47_event.json.\n")
S = D / "SHA256SUMS"
Ls = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
sha = lambda b: hashlib.sha256(b).hexdigest()
new = {"die_plan.json": sha(gzip.decompress((D / "die_plan.json.gz").read_bytes())), "part47_event.json": sha((D / "part47_event.json").read_bytes())}
for i, (a, n) in enumerate(Ls):
    if n in new:
        Ls[i] = [new[n], n]
if "part47_event.json" not in {n for _, n in Ls}:
    Ls.append([new["part47_event.json"], "part47_event.json"])
S.write_text("".join(f"{a}  {n}\n" for a, n in Ls))
print("SHA256SUMS updated")
