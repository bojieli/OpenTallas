"""DIE-QC-15 FF hold ESTIMATE (no build): trial11 proof taps + plan core->tap map. Intra (same partition) damage per pair
= capture late - launch late at the tap, as the gate's declared-budget model (same core latency both sides), versus
the same with each early-tapped core's REAL insertion (CORELAT-SQ-1 signed / model means) added on its side.
Calibration: gate worst intra hold -281.85 FF at damage 250.43 -> hold ~= -(damage) - 31.4 (ocv/unc/CPPR remainder).
usage: hold_est.py PLAN TAPS_FF.json CORELAT_TSV GATE_JSON"""
import json, sys, collections, statistics as st
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-qc15-1028/tools/die_plan")
import die_sta_related as R
plan = json.load(open(sys.argv[1])); TF = json.load(open(sys.argv[2]))
taps = {t["port"]: t for t in TF["taps"]}
core = {}
for i, l in enumerate(open(sys.argv[3])):
    p = l.rstrip("\n").split("\t")
    if i == 0: H = p; continue
    r = dict(zip(H, p)); core[r["module"]] = (float(r["TT_mean"]), float(r["FF_mean"]), float(r["early_FF"]))
cm = R.map_cores_to_taps(plan, taps)
tapmods = collections.defaultdict(set)
for (part, inst), (mod, port, d, pf) in cm.items():
    if port: tapmods[port].add(mod)
DECL = 202.5
def eff(port, real):
    a = taps[port]["late_ps"]
    if not real: return a + DECL
    ms = [m for m in tapmods.get(port, ()) if m in core]
    return a + (max(core[m][1] for m in ms) if ms else DECL)
bypart = collections.defaultdict(list)
for p, t in taps.items(): bypart[t["part"]].append(p)
rows = []
for part, ps in bypart.items():
    if len(ps) < 2: continue
    for real in (False, True):
        v = [eff(p, real) for p in ps]
        rows.append((part, real, round(max(v) - min(v), 1)))
d = collections.defaultdict(dict)
for part, real, s in rows: d[part]["real" if real else "decl"] = s
worst_decl = max(d.items(), key=lambda x: x[1]["decl"]); worst_real = max(d.items(), key=lambda x: x[1]["real"])
fam = collections.defaultdict(list)
for part, v in d.items(): fam[part.split("_", 2)[-1] if part.startswith("sl_") else part.split("_")[0] + "_" + (part.split("_")[-2] if part.startswith("c_") else "")].append(v)
print("early-tapped modules on taps:", sorted({m for s in tapmods.values() for m in s if m in core}))
print("worst intra damage declared: %s %.1f | with real core insertion: %s %.1f" % (worst_decl[0], worst_decl[1]["decl"], worst_real[0], worst_real[1]["real"]))
for f, vs in sorted(fam.items()):
    print("%-14s n=%3d  decl max %.1f med %.1f | real max %.1f med %.1f" % (f, len(vs), max(x["decl"] for x in vs), st.median(x["decl"] for x in vs), max(x["real"] for x in vs), st.median(x["real"] for x in vs)))
g = json.load(open(sys.argv[4])); gi = g["corners"]["FF"]["classes"]["intra"]
k = -gi["worst_hold_slack_ps"] - gi["skew_diag_max_ps"]
print("calibration: gate hold %.2f damage %.2f -> remainder %.1f; tap-delta model damage at the gate worst pair: %.1f" % (gi["worst_hold_slack_ps"], gi["skew_diag_max_ps"], k, taps[gi["worst_hold"]["capture"]]["late_ps"] - taps[gi["worst_hold"]["launch"]]["late_ps"]))
print("ESTIMATE intra FF hold with real core insertion: ~%.0f (worst), sl_*_su_c parts:" % (-(worst_real[1]["real"]) * gi["skew_diag_max_ps"] / max(1e-9, (taps[gi["worst_hold"]["capture"]]["late_ps"] - taps[gi["worst_hold"]["launch"]]["late_ps"])) - k))
for part in sorted(p for p in d if "su_c" in p): print("  ", part, d[part])
