"""DIE-QC-23 QC plan event (COORD 10-28 19:26 ASK default YES): ev_a0meas (die-qc20 plan, sha ccadb037) + clock.tap_window
{window_ps 180} (one window intra + seam, S81 value, <= T/4) + clock.seam_hold {sender_ps 25, seam_ps 180} (partitions;
hard-core kits keep --seam-hold 25,25 per the 19:05 ruling).  Estimate first: results hb_est23.json (max 1.53 % of a
partition area, < 5 %).   usage: plan_event23.py IN OUT"""
import hashlib, json, sys
from pathlib import Path
src, out = sys.argv[1:3]
P = json.load(open(src))
assert not P["clock"].get("tap_window") and not P["clock"].get("seam_hold"), "plan already has a window"
P["clock"]["seam_hold"] = dict(sender_ps=25.0, seam_ps=180.0,
                               note="DIE-QC-23 (COORD 10-28 19:26): partition seam contract, one window for intra + seam; "
                                    "hard-core kits keep sender 25 / seam 25 (19:05 ruling)")
P["clock"]["tap_window"] = dict(window_ps=180.0,
                                note="DIE-QC-23 (COORD 10-28 19:26): one standard window (S81 value) for every type; "
                                     "kit hold repair covers cross-tap pairs within 180 ps; <= T/4")
s = json.dumps(P, indent=1) + "\n"
Path(out).write_text(s)
print("PLAN_EVENT", out, hashlib.sha256(s.encode()).hexdigest()[:12], "src", hashlib.sha256(open(src, "rb").read()).hexdigest()[:12])
