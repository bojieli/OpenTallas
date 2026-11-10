# HBM-COLLECT-1 N4-PLAN 11-10 (COORD ruling A): die-local plan event n4ext1110.
# Adopt the signed-off n4ext RE-FORM outline 293.76 x 250.56 (origin kept 734.4, 5503.68; grows E and N only) into a
# COPY of the HBM wave plan: plan_r2_restore -> plan_r2_n4ext.  The delta is DIE-HBM-89's mk_plan_n4rf.py (copied here
# unchanged), re-applied on this base as DIE-HBM-97 ruled 11-10 03:49:
#   type root: hard_cores/contents u_mu_fused_root outline + pins_file, internal_stations bus:n4x_up_ne_i /
#   bus:n4x_dn_ne_o landing x 950.4 -> 1028.16, clock tap u_mu_fused_root.clk; clock_entries root.u_mu_fused_root;
#   core_macros ot_hnx_fused_hub_n4ext; the new pins table (444 E pins x -> W-0.096, rst_n y -> H-0.096, clk entry).
# Nothing else changes.  The pins table equals the signed 6_final.odb on all 1126 signal pins (name, layer, position).
# usage: apply_event.py BASE_PLAN NEW_PLAN EVENT_JSON
import gzip, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
BASE, NEW, EV = (Path(a) for a in sys.argv[1:4])
PINS = "cores/ot_hnx_fused_hub_n4ext__293.76x250.56__n4rf.json"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not NEW.exists(), NEW
tmp = Path(tempfile.mkdtemp(prefix="n4ext1110_"))
out = subprocess.check_output([sys.executable, "-I", str(HERE / "mk_plan_n4rf.py"), str(BASE), str(tmp)], text=True)
delta = json.loads(out.strip().splitlines()[-1])
subprocess.check_call(["cp", "-a", str(BASE), str(NEW)])
# die_plan.json: keep the base layout (indent=1) and its .gz twin
plan = json.load(open(tmp / "die_plan.json"))
(NEW / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
ce = json.load(open(tmp / "clock_entries.json"))
(NEW / "clock_entries.json").write_text(json.dumps(ce) + "\n")
(NEW / "core_macros.json").write_bytes((tmp / "core_macros.json").read_bytes())
(NEW / PINS).write_bytes((tmp / PINS).read_bytes())
for f in ("die_plan.json", "clock_entries.json"):
    if (NEW / (f + ".gz")).exists():
        with open(NEW / f, "rb") as s, gzip.GzipFile(NEW / (f + ".gz"), "wb", 9, mtime=0) as g: g.write(s.read())
sp = NEW / "SHA256SUMS"
if sp.exists():
    rows = []
    for ln in sp.read_text().splitlines():
        h, name = ln.split(None, 1); name = name.lstrip("*")
        rows.append("%s  %s" % (sha(NEW / name) if (NEW / name).exists() else h, name))
    if not any(r.endswith("  " + PINS) for r in rows): rows.append("%s  %s" % (sha(NEW / PINS), PINS))
    sp.write_text("\n".join(rows) + "\n")
ev = {"schema": "opentallas.hbm_plan_event.v1", "event": "n4ext1110", "lane": "HBM-COLLECT-1 (N4-PLAN)",
      "ruling": "COORD 11-10 (A): adopt the grown n4ext outline at the same origin by a die-local plan event; no rebuild",
      "status": "READY (die-local)", "base_plan": str(BASE), "base_plan_sha256": sha(BASE / "die_plan.json"),
      "new_plan": str(NEW), "new_plan_sha256": sha(NEW / "die_plan.json"),
      "delta_tool": "mk_plan_n4rf.py (DIE-HBM-89-N4RF, unchanged), sha256 " + sha(HERE / "mk_plan_n4rf.py"),
      "module": "ot_hnx_fused_hub_n4ext", "inst": "root.u_mu_fused_root", "origin_um": [734.4, 5503.68],
      "outline_um": {"from": [216.0, 207.36], "to": [293.76, 250.56]}, "pins_file": PINS,
      "pins_file_sha256": sha(NEW / PINS), "pin_cycles_added": 0, "delta": delta,
      "files_changed": ["die_plan.json(.gz)", "clock_entries.json(.gz)", "core_macros.json", PINS, "SHA256SUMS"]}
EV.write_text(json.dumps(ev, indent=1) + "\n")
subprocess.call(["rm", "-rf", str(tmp)])
print(json.dumps({k: ev[k] for k in ("new_plan_sha256", "pins_file_sha256", "delta")}))
