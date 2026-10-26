"""PATH-S81 a8 repack: ft_corridor on every type the joint re-lay changed (plan a7/plan_a8.json in a copy of a1_src).
Stations per slot = max(current, ceil((|in-out offset| + crossing span) / (0.98*405))); on 'no chain' +1 (max +4),
then a jog sweep over core-free channel rows (a6 channels()). Each added station = +1 cycle (gen latency reprices)."""
import json, math, re, signal, subprocess, sys, time, traceback
from multiprocessing import get_context
from pathlib import Path
M = Path(__import__("os").environ.get("A8_WORK", "."))
dst = M / sys.argv[1]; planin = M / sys.argv[2]
if not dst.exists():
    subprocess.run(["cp", "-a", "--reflink=auto", str(M / "a1_src"), str(dst)], check=True)
p = dst / "physical/die_plan/s81/die_plan.json"
p.write_text(planin.read_text())
sys.path[:0] = [str(dst / "tools/die_plan"), str(dst), str(dst / "physical/die_plan/s81"), str(M)]
import ft_corridor, compact_plan
from delta_dieft_a6_sweep_lib import channels
raw = json.loads(p.read_text())
types = json.load(open(str(planin) + ".report.json"))["changed"]
types = [t for t in types if raw["partition_types"][t].get("ft_slots")]
OPP = dict(N="S", S="N", E="W", W="E")
def work(tn):
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError("timeout")))
    t0 = time.time(); ty = raw["partition_types"][tn]; w, h = ty["outline_um"]
    base = {s["name"]: s["stations"] for s in ty["ft_slots"]}
    for s in ty["ft_slots"]:
        a, b = sum(s["in_window_um"]) / 2, sum(s["out_window_um"]) / 2
        if OPP[s["in_face"]] == s["out_face"]:
            L = abs(a - b) + (h if s["in_face"] in "NS" else w)
        else:
            L = (w + h) / 2
        s["stations"] = max(s["stations"], math.ceil(L / (0.98 * 405)))
    sb = {f"{tn}/{s['name']}": 128 for s in ty["ft_slots"] if s["width"] >= 256}
    jogs, tried, adds, err = {}, {}, {}, None
    while time.time() - t0 < 1800:
        try:
            signal.alarm(300)
            led = ft_corridor.place(raw, [tn], split_bits=sb, jogs=jogs); signal.alarm(0)
            add = {s["name"]: (base[s["name"]], s["stations"]) for s in ty["ft_slots"] if s["stations"] != base[s["name"]]}
            return tn, ty, dict(added=add, jogs=jogs, ledger=led), time.time() - t0
        except Exception as e:
            signal.alarm(0); err = traceback.format_exc()[-300:]
            m = re.match(r"(ft\d+)", str(e))
            if not m: break
            sn = m.group(1); key = f"{tn}/{sn}"; slot = next(s for s in ty["ft_slots"] if s["name"] == sn)
            if OPP[slot["in_face"]] == slot["out_face"]:
                cands, _ = channels(ty, slot)
                t = tried.setdefault((sn, slot["stations"]), [])
                nxt = [c for c in cands if c not in t]
                if nxt: t.append(nxt[0]); jogs[key] = nxt[0]; continue
                jogs.pop(key, None)
            if adds.get(sn, 0) >= 4: break
            slot["stations"] += 1; adds[sn] = adds.get(sn, 0) + 1
    return tn, None, dict(error=err), time.time() - t0
out = dict(added={}, jogs={}, placed=[], failed={}, ledger=[])
with get_context("fork").Pool(min(24, len(types))) as pool:
    for tn, ty, info, dt in pool.imap_unordered(work, types):
        if ty is None:
            out["failed"][tn] = info["error"]; print(f"FAIL {tn} {dt:.0f}s {info['error'].strip().splitlines()[-1]}", flush=True)
        else:
            raw["partition_types"][tn] = ty; out["placed"].append(tn); out["ledger"] += info["ledger"]
            out["added"][tn] = info["added"]; out["jogs"][tn] = info["jogs"]
            print(f"OK {tn} {dt:.0f}s added {info['added']} jogs {info['jogs']}", flush=True)
p.write_text(compact_plan.dumps(raw))
json.dump(out, open(M / f"{sys.argv[1]}_report.json", "w"), indent=1)
print("A8R placed", len(out["placed"]), "failed", len(out["failed"]), "stations added", sum(b - a for t in out["added"].values() for a, b in t.values()), flush=True)
