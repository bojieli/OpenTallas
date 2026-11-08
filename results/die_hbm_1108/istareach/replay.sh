#!/bin/bash
# DIE-HBM-91-REACH istareach_1108 replay: adds FIRM internal stations + PIN CYCLES (lane fixed_cycles) on the long
# current buses of the 25 istadrop_1107 types, on WHATEVER d44v plan of record the checkout carries (run on any main;
# never merge die_plan.json.gz by hand: re-run this), and writes asbuilt_t14 = asbuilt_t13 + internal_stations_types.
#   usage: results/die_hbm_1108/istareach/replay.sh BOUND_RTL_DIR [WORK_DIR]
#   BOUND_RTL_DIR = bound RTL of record of the HBM types (strict die bind out/rtl, e.g. DIE-HBM-90-REBIND bind_g)
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/../../.."
BRTL=$1; W=${2:-$(mktemp -d)}
D=physical/die_plan/hbm/plan_of_record/d44v
A=physical/die_plan/hbm/bind/d44v
mkdir -p "$W"
python3 -I - "$D" "$W" <<'PY'
import gzip, hashlib, sys, pathlib
d, w = map(pathlib.Path, sys.argv[1:])
b = gzip.open(d / "die_plan.json.gz").read()
sums = dict(reversed(l.split("  ", 1)) for l in (d / "SHA256SUMS").read_text().split("\n") if "  " in l)
h = hashlib.sha256(b).hexdigest()
if sums.get("die_plan.json") != h:
    raise SystemExit(f"d44v die_plan.json.gz ({h[:12]}) does not match SHA256SUMS ({sums.get('die_plan.json', '?')[:12]})")
if b"istareach_1108" in b:
    raise SystemExit("d44v already carries istareach_1108")
(w / "before.json").write_bytes(b)
PY
TYPES=$(python3 -I -c "import json;print(','.join(sorted(json.load(open('$D/istadrop_1107_ledger.json'))['types'])))")
python3 -I tools/die_plan/add_reach_istations.py "$W/before.json" "$W/die_plan.json" "$D/istareach_1108_ledger.json" \
    --bound-rtl "$BRTL" --types "$TYPES"
python3 -I - "$D" "$W" "$A" <<'PY'
import gzip, hashlib, json, sys, pathlib, shutil
d, w, a = map(pathlib.Path, sys.argv[1:])
led = json.loads((d / "istareach_1108_ledger.json").read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
with open(w / "die_plan.json", "rb") as f, gzip.GzipFile(d / "die_plan.json.gz", "wb", mtime=0) as g:
    shutil.copyfileobj(f, g)
# asbuilt_t14 = t13 + internal_stations_types (native source stations for the out-bus types)
ab = json.loads((a / "asbuilt_t13.json").read_text())
ab["internal_stations_types"] = led["native_types"]
ab["note"] = ("DIE-HBM-91-REACH t14 = t13 + internal_stations_types " + ",".join(led["native_types"]) +
              " (istareach_1108: out-bus stations materialised at the source, destination pad cut) | " + ab["note"])
(a / "asbuilt_t14.json").write_text(json.dumps(ab, indent=1) + "\n")
ev = dict(schema="opentallas.hbm_plan_event.v1", event="istareach_1108", plan="d44v",
          lane="DIE-HBM-91-REACH (under DIE-HBM-91)", date="2026-11-08",
          approved="DIE-HBM-91 GO 11-08 (A): one event, in + out buses, fixed_cycles = source + destination stations, asbuilt internal_stations_types",
          what=[f"{led['added_entries']} internal_stations entries ({led['added_stations']} FIRM stations, hops <= {led['reach_um']:g} um) on long current buses of {len(led['types'])} types",
                f"PIN CYCLES: lanes[].fixed_cycles += stations on {len(led['lanes_fixed_cycles'])} lanes ({sum(led['lanes_fixed_cycles'].values())} cycles); latency.lanes by the gen.latency_table delta ({len(led['latency_delta'])} lanes)",
                "asbuilt_t14.json = asbuilt_t13 + internal_stations_types " + ",".join(led["native_types"])],
          skipped=led["skipped"],
          why="DIE-HBM-91-REACH RESULT 11-08: after istadrop_1107 the re-routed buses carry 0 internal stations; 379 face->leaf links > 450 um, 368 estimated to miss setup at 833 ps",
          sha256={"die_plan.json.before": sha(w / "before.json"), "die_plan.json": sha(w / "die_plan.json"),
                  "asbuilt_t14.json": sha(a / "asbuilt_t14.json")},
          replay="results/die_hbm_1108/istareach/replay.sh BOUND_RTL_DIR")
(d / "istareach_1108_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = d / "README.md"
txt = rd.read_text()
if "Event istareach_1108" not in txt:
    txt += ("\nEvent istareach_1108 (DIE-HBM-91-REACH 11-08, under DIE-HBM-91; reach class of the DIE-HBM-90 PARKED post): "
            f"{led['added_entries']} FIRM internal_stations entries ({led['added_stations']} stations, every hop <= 405 um) on the "
            f"long current buses of the 25 istadrop types, PIN CYCLES lanes[].fixed_cycles += stations on {len(led['lanes_fixed_cycles'])} lanes "
            "(= source + destination stations); out-bus types in asbuilt_t14 internal_stations_types. Not stationed, listed in "
            f"istareach_1108_ledger.json: {dict(led['skipped'])}. Replay results/die_hbm_1108/istareach/replay.sh.\n")
    rd.write_text(txt)
lines = [l for l in (d / "SHA256SUMS").read_text().split("\n") if l]
names = {"die_plan.json": w / "die_plan.json", "README.md": rd, "istareach_1108_event.json": d / "istareach_1108_event.json",
         "istareach_1108_ledger.json": d / "istareach_1108_ledger.json"}
seen = {l.split("  ", 1)[1] for l in lines}
lines = [f"{sha(names[l.split('  ', 1)[1]])}  {l.split('  ', 1)[1]}" if l.split("  ", 1)[1] in names else l for l in lines] \
    + [f"{sha(p)}  {n}" for n, p in names.items() if n not in seen]
(d / "SHA256SUMS").write_text("\n".join(lines) + "\n")
print(json.dumps(ev["sha256"]))
PY
echo "istareach_1108 replayed in $D (work $W)"
