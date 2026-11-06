#!/usr/bin/env python3
"""DIE-HBM-82-G0C d44v part 43 packaging: event record, README line, SHA256SUMS.   fin_p43.py REPO"""
import gzip, hashlib, json, sys
from pathlib import Path
R = Path(sys.argv[1]); D = R / "physical/die_plan/hbm/plan_of_record/d44v"
L42 = json.loads((R / "results/die_hbm_1106/street_p43/ledger_p43.json").read_text())
ev = {"schema": "opentallas.hbm_plan_event.part43", "by": "DIE-HBM-82-G0C 11-06 (G0C class F street_die_leg)",
      "change": "F1: explicit bit-site slots, each station point inside a core -> the real bit site of that stage with the smallest worst neighbour hop (no bit cell moves); "
                "F3: q_b102 (+pv1) bit-site-less normal slots, stations in the N-edge clock keep-out moved by ft_nudge.nudge_explicit",
      "slots": {k: [f"{r['type']}/{r['slot']}" for r in L42 if r["sub"] == k] for k in ("F1", "F3")},
      "not_changed_F2": "normal-slot S0 = input-face site inside a core abutting the face (q_b111/__pv1 sfucore lanes W/E, q_b102 idx ra S) "
                        "or the q_b102 N-edge clock keep-out: needs a window re-pin, separate event",
      "pin_cycles": "none (station counts unchanged)", "ledger": "results/die_hbm_1106/street_p43/ledger_p43.json",
      "replay": "results/die_hbm_1106/street_p43/replay_p43.sh"}
(D / "part43_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 43 (DIE-HBM-82-G0C 11-06, G0C class F street_die_leg): lane stations off the hard cores with the least "
              "move: bit-site slots get a real bit site of the stage (smallest worst hop) as regs_um (no cell moves), q_b102 N-edge keep-out stations nudged "
              "(ft_nudge.nudge_explicit); station counts unchanged, 0 pin cycles; normal-slot S0 under an abutting core left for a window re-pin; part43_event.json.\n")
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
sha = lambda b: hashlib.sha256(b).hexdigest()
new = {"die_plan.json": sha(gzip.decompress((D / "die_plan.json.gz").read_bytes())), "part43_event.json": sha((D / "part43_event.json").read_bytes())}
for i, (a, n) in enumerate(L):
    if n in new:
        L[i] = [new[n], n]
if "part43_event.json" not in {n for _, n in L}:
    L.append([new["part43_event.json"], "part43_event.json"])
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS updated")
