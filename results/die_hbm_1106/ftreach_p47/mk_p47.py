#!/usr/bin/env python3
"""DIE-HBM-82-G0C d44v part 47: G0C class A (ft reach) -- ONE ft_s0_resite.py pass over every type with a G0C
'stations' finding (real normal input S0->S1 > 405 um; the same rows drive hops / reach).

ft_s0_resite.py (DIE-HBM-58 class tool) re-sites the k-1 internal stations of each normal FT slot whose per-bit chain
[input site, S1..S(k-1), output pin] has a hop > 0.9 x 405 = 364.5 um (DP along the in->out path among positions
where the whole bit band is on free legal sites; obstacles = placement_obstacles; every other slot's sites reserved).
The station count is kept when a chain fits, else +1..+3 stations = PIN CYCLES (ledger); a slot no count fits is KEPT
unchanged and listed.  It was run once per type (--types T, in parallel; a type only touches its own ft_slots).
This script takes, per type, ONLY the re-sited slots from that run and puts them into the d44v plan, then adds to the
plan's stored latency.lanes the delta of schema.Plan.lane_latency (= gen.py latency) event - base, and lists every
lane whose cycles change (pin-cycle ledger).  Windows, pins, outlines and cores never change.
    mk_p47.py POR_PLAN.json D44V_DIR RUN_DIR LEDGER.json   (RUN_DIR holds <type>.plan.json + <type>.ledger.json)"""
import copy, gzip, json, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan"); sys.path.insert(0, ".")
import schema as S  # noqa: E402
from gen import latency_table  # noqa: E402

por, D, run, ledger_f = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
raw = json.loads(gzip.decompress((D / "die_plan.json.gz").read_bytes()))
porraw = S.load(por)
tab0 = latency_table(S.Plan(copy.deepcopy(porraw), Path(por)))   # base lane latency (unmodified POR)
# the class tool's obstacles do not hold the type clock keep-outs / die clock leg repeaters: two re-sites the G0 diff
# showed landing on them are left out (base kept), so the event adds 0 errors in the other classes
EXCLUDE = {("q_b102__physical_v1", "L5091x6"): "2 new stations inside the NE_b102 N-edge clock keep-out (street_die_leg)",
           ("root", "L22mx4"): "bit sites within the 2 um halo of root tkm clock leg repeaters u_tkmclk_L150_c3_r24_1__ha/hb (clock)"}
slots_led, kept, nslot = [], [], 0
for lf in sorted(run.glob("*.ledger.json")):
    tn = lf.name[:-len(".ledger.json")]
    L = json.loads(lf.read_text())
    res = [r for r in L["slots"] if "stations_after" in r and (tn, r["slot"]) not in EXCLUDE]
    kept += [f"{tn}/{r['slot']}" for r in L["slots"] if "kept" in r]
    if not res:
        continue
    out = json.loads((run / f"{tn}.plan.json").read_text())["partition_types"][tn]
    new = {s["name"]: s for s in out["ft_slots"]}
    for tgt in (raw, porraw):
        t = tgt["partition_types"][tn]
        for i, s in enumerate(t["ft_slots"]):
            if s["name"] in {r["slot"] for r in res}:
                ns = copy.deepcopy(new[s["name"]])
                if tgt is raw:
                    ns["note"] = (ns.get("note", "") + " | DIE-HBM-82-G0C d44v part 47: ft_s0_resite (G0C class A)").lstrip(" |")
                t["ft_slots"][i] = ns
    nslot += len(res)
    for r in res:
        slots_led.append(dict(type=tn, slot=r["slot"], stations=[r["stations_before"], r["stations_after"]],
                              added_cycles=r.get("added_cycles", 0), hop_um=[r.get("hop_before_um"), r.get("hop_after_um")]))
# latency regen on the result (gen.py latency semantics, schema.Plan.lane_latency)
P = S.Plan(porraw, Path(por))
tab = latency_table(P)
lat_led = []
# the stored latency.lanes carry folds (R8 pad, landing cycles) a bare regen does not; so apply only the DELTA
# lane_latency(event) - lane_latency(base) to the stored row (cycles / natural / stations), lanes with a delta only
for lid, d in tab.items():
    b0 = tab0[lid]
    dc, ds = d["cycles"] - b0["cycles"], d["stations"] - b0["stations"]
    if dc or ds:
        old = raw["latency"]["lanes"][lid]
        new = dict(old, cycles=old["cycles"] + dc, stations=old["stations"] + ds)
        if "natural" in old:
            new["natural"] = old["natural"] + dc
        lat_led.append(dict(lane=lid, param=old.get("param"), cycles=[old["cycles"], new["cycles"]], stations=[old["stations"], new["stations"]]))
        raw["latency"]["lanes"][lid] = new
b = (json.dumps(raw) + "\n").encode()
with open(D / "die_plan.json.gz", "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
    g.write(b)
summ = dict(slots_resited=nslot, slots_with_added_stations=sum(1 for r in slots_led if r["added_cycles"]),
            added_station_cycles=sum(r["added_cycles"] for r in slots_led), lanes_latency_changed=len(lat_led), kept=kept, excluded={f"{t}/{n}": why for (t, n), why in EXCLUDE.items()})
Path(ledger_f).write_text(json.dumps(dict(summary=summ, slots=slots_led, pin_cycles_lanes=lat_led), indent=1) + "\n")
print("P47", json.dumps({k: v for k, v in summ.items() if k != "kept"}), "kept", len(kept))
