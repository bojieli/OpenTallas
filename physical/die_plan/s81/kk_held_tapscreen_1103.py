import json, sys, time
sys.path.insert(0, "tools/die_plan")
import schema as S, added_tap_recentre as AT
raw = json.load(open("physical/die_plan/s81/plan_h2_2249.json")); P = S.Plan(raw, "x")
ev = json.load(open("physical/die_plan/s81/h2_2249/relay_bay_cycle_event_1103.json"))
T = sorted(t for t, ss in ev["slots"].items() if any(v["extra_cycles"] for v in ss.values()))
bad = []
for tn in T:
    t0 = time.time()
    try:
        r = AT.check(P, tn)
    except Exception as e:
        r = repr(e)[:200]
    if r:
        bad.append((tn, str(r)[:200]))
    print(tn, round(time.time() - t0, 1), "FAIL" if r else "ok", flush=True)
print("BAD", json.dumps(bad))
