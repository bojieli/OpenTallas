"""DIE-QC-84 QC over-cap tap class: measured register inventory (retained 3_place) -> density taps (cap 1200,
target 900, radius 200) for every over-cap type; model old-vs-new load/reach; emit clock_patches.json (hash-guarded)."""
import json, sys, hashlib, glob, os, copy
from pathlib import Path
from collections import Counter
WT = Path(sys.argv[1]); DUMPS = Path(sys.argv[2]); PLAN = Path(sys.argv[3]); EV = WT / sys.argv[4]; CENSUS = Path(sys.argv[5])
sys.path.insert(0, str(WT / "tools/die_plan"))
import taps as T, schema as S
EV.mkdir(parents=True, exist_ok=True); (EV / "bins").mkdir(exist_ok=True)
raw = json.loads(PLAN.read_text())
H = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
old_max = {}
for l in CENSUS.read_text().splitlines():
    f = l.split("\t")
    if len(f) > 4 and f[4] != "none":
        m = max(int(x.split(":")[1]) for x in f[4].split())
        old_max[f[1]] = max(old_max.get(f[1], 0), m)
patches, report = {}, []
only = set(sys.argv[6].split(",")) if len(sys.argv) > 6 else None
for dump in sorted(DUMPS.glob("*.json")):
    tn = dump.stem
    if only and tn not in only: continue
    t = raw["partition_types"].get(tn)
    if t is None: report.append(dict(type=tn, status="NOT_IN_POR")); continue
    base = copy.deepcopy(t)
    d = json.loads(dump.read_text())
    ox, oy = d["outline"][:2]
    pts = [((c[1] + c[3]) / 2 - ox, (c[2] + c[4]) / 2 - oy) for c in d["cells"]]
    B = 8.64
    cnt = Counter((int(x // B), int(y // B)) for x, y in pts)
    bins = dict(bin_um=B, n=len(pts), src=d.get("odb", ""),
                bins=[[round((i + .5) * B, 3), round((j + .5) * B, 3), n] for (i, j), n in sorted(cnt.items())])
    bf = EV / "bins" / f"{tn}.json"
    bf.write_text(json.dumps(bins, separators=(",", ":")) + "\n")
    c = copy.deepcopy(t.get("clock", {}))
    cap = min(int(base.get("clock", {}).get("tap_max_sinks") or 1200), 1200)
    c.update(sink_bins_file=str(bf.relative_to(WT)), tap_mode="density", tap_max_sinks=cap, tap_target_sinks=int(0.75 * cap), tap_radius_um=200.0, tap_chain_affinity=dict(radius_um=200.0, max_group=128))
    t["clock"] = c
    row = dict(type=tn, sinks=len(pts), old_max_load_actual=old_max.get(tn), old_mode=base.get("clock", {}).get("tap_mode"),
               old_cap=base.get("clock", {}).get("tap_max_sinks"))
    # radius 191 = 200 - one 8.64 um bin (bin centre -> member register L1 <= 8.64): the actual-sink reach then stays
    # <= 200 although density_taps sees bin centres (the 3 first-run reach misses were 0.8-6.9 um bin quantisation)
    for rad, frac in [(200.0, f) for f in (0.75, 0.65, 0.55)] + [(191.0, f) for f in (0.75, 0.65)]:
        c["tap_target_sinks"] = int(frac * cap); c["tap_radius_um"] = rad; c["tap_chain_affinity"] = dict(radius_um=rad, max_group=128); t["clock"] = c
        try:
            P = S.Plan(raw, str(PLAN))
            new = T.density_taps(P, tn, False)
            load, far, _ = T.assign(new, [(x, y, 1) for x, y in pts], cap, 200, max_distance_um=200)
            ok = max(load) <= cap and max(far) <= 200.0 + 1e-6
            row.update(cap=cap, target=c["tap_target_sinks"], radius=c["tap_radius_um"], status="OK" if ok else "OVER", new_taps=len(new),
                       new_max_load=int(max(load)), new_max_reach_um=round(max(far), 3), error="")
            if ok:
                break
        except Exception as e:
            row.update(status="ERROR", error=f"{type(e).__name__}: {e}"[:300])
    if row["status"] == "OK":
        patches[tn] = dict(base_type_sha256=H(base), clock=copy.deepcopy(c), model=dict(sinks=len(pts), taps=row["new_taps"], max_load=row["new_max_load"], max_reach_um=row["new_max_reach_um"]))
    t["clock"] = base.get("clock", {}) if "clock" in base else t.pop("clock")
    if "clock" not in base: t.pop("clock", None)
    report.append(row); print(json.dumps(row), flush=True)
if only and (EV / "clock_patches.json").exists():   # partial re-run: keep the other types' patches
    patches = {**json.loads((EV / "clock_patches.json").read_text()), **patches}
(EV / "clock_patches.json").write_text(json.dumps(patches, indent=1, sort_keys=True) + "\n")
if only and (EV / "model.json").exists():
    keep = [r for r in json.loads((EV / "model.json").read_text())["rows"] if r["type"] not in only]
    report = sorted(keep + report, key=lambda r: r["type"])
(EV / "model.json").write_text(json.dumps(dict(plan=str(PLAN), plan_sha256=hashlib.sha256(PLAN.read_bytes()).hexdigest(), rows=report), indent=1) + "\n")
