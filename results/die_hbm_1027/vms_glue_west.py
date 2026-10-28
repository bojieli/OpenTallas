"""DIE-HBM-2 C20e: vms_glue E-face cap (REPACK minimum, CHECKED count there: E 8897 pins vs cap 8316 at 5.5/um)
-> move whole E-face ports to the W face, the ports whose partners lie furthest WEST first (mean over the 4 instances
q_hub_nw/ne u_hb_vms_Q__q0/q1, partner = core centre from core_conns 'core:' targets), until E <= cap.
Moved pins keep their y when that M4 track is free on W (>= 0.144 um from every W pin), else the nearest free track
(offset 0.024, pitch 0.048).  New pins file name ..._c20e.json; the 4 hard cores point to it.
usage: vms_glue_west.py PLAN_DIR(in place)"""
import json, re, sys, collections, bisect, hashlib
from pathlib import Path
D = Path(sys.argv[1]); raw = json.load(open(D / "die_plan.json")); T = raw["partition_types"]
cc = json.load(open(D / "core_conns.json"))
OLD = "cores/hfd_hgi_vms_glue_nw_t__777.6x1529.28__c19.json"; NEW = OLD.replace(".json", "__c20e.json")
d = json.load(open(D / OLD)); pins = d["pins"] if isinstance(d, dict) else d
W, H = 777.6, 1529.28; CAP = int(5.5 * H) - 95   # 8316 (REPACK cap) minus a small guard
def face(p): return min((p["x"], "W"), (W - p["x"], "E"), (p["y"], "S"), (H - p["y"], "N"))[1]
def port(n): return re.sub(r"\[\d+\]$", "", n)
inst = [(tn, h) for tn in ("q_hub_nw", "q_hub_ne") for h in T[tn]["hard_cores"] if h.get("pins_file") == OLD]
cent = {tn: {h["inst"]: (h["origin_um"][0] + h["outline_um"][0] / 2, h["origin_um"][1] + h["outline_um"][1] / 2)
             for h in T[tn]["hard_cores"]} for tn in ("q_hub_nw", "q_hub_ne")}
score = collections.defaultdict(list)
for tn, h in inst:
    cx = cent[tn][h["inst"]][0]
    for pt, tg in (cc.get(tn, {}).get(h["inst"]) or {}).items():
        for t in (tg if isinstance(tg, list) else [tg]):
            if isinstance(t, str) and t.startswith("core:"):
                c = cent[tn].get(t[5:].split(".")[0])
                if c: score[pt].append(c[0] - cx)
E = collections.defaultdict(list)
for p in pins:
    if face(p) == "E": E[port(p["name"])].append(p)
nE = sum(len(v) for v in E.values()); need = nE - CAP
cand = sorted((sum(score[k]) / len(score[k]), k) for k in E if score.get(k))
moved_ports, n = [], 0
for s, k in cand:
    if n >= need: break
    if s >= 0: break                      # never move a port whose partners lie east
    moved_ports.append((k, round(s, 1), len(E[k]))); n += len(E[k])
wy = sorted(p["y"] for p in pins if face(p) == "W")
def free(y):
    i = bisect.bisect_left(wy, y)
    return all(abs(wy[j] - y) >= 0.144 - 1e-9 for j in (i - 1, i) if 0 <= j < len(wy))
for k, _, _ in moved_ports:
    for p in E[k]:
        y0 = p["y"]; best = None
        for dk in range(0, 4000):
            for sg in (1, -1):
                y = round(0.024 + 0.048 * (round((y0 - 0.024) / 0.048) + sg * dk), 3)
                if 8.0 <= y <= H - 8.0 and free(y): best = y; break
            if best is not None: break
        p["x"] = 0.096; p["y"] = best; bisect.insort(wy, best)
(D / NEW).write_text(json.dumps(d, indent=1))
for tn, h in inst: h["pins_file"] = NEW
(D / "die_plan.json").write_text(json.dumps(raw, indent=1))
(D / "die_plan.sha256").write_text(hashlib.sha256((D / "die_plan.json").read_bytes()).hexdigest() + "\n")
cnt = collections.Counter(face(p) for p in pins)
rep = dict(table=NEW, E_before=nE, cap=CAP, moved_pins=n, moved_ports=moved_ports, faces_after=dict(cnt),
           dens_after={f: round(cnt[f] / (H if f in "EW" else W), 3) for f in cnt}, instances=[f"{tn}/{h['inst']}" for tn, h in inst])
(D / "vms_glue_west_report.json").write_text(json.dumps(rep, indent=1)); print(json.dumps(rep)[:1500])
