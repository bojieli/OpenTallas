"""CLOCK-KV hm_r26q4 part (d) D-KV-STRAP-FORM-2 (COORD 10-27 11:4x): every pin on a face whose pins are all edge form
(d = 0: x = 0 / x = W / y = 0 / y = H) moves 0.096 um inward to the centre form that the GEOM-passed kits use
(0.096 / 215.904).  Asserted: only kv3_head_eighth_e0/e2/e6 strap_* pins move; x along the face, layer, size unchanged.
New files <old>_r26q4.json; hard_cores pins_file repointed.  Prints canon_pins sha256 old -> new per file.
    q4_straps.py PD PLAN_IN PLAN_OUT"""
import json, sys
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/kv-plan-q3-1027/tools/die_plan")
import die_sta_related as D
pd, pin, pout = sys.argv[1:4]
P = json.load(open(f"{pd}/{pin}"))
D_IN = 0.096
files = {}
for t in P["partition_types"].values():
    for hc in t.get("hard_cores", []):
        if hc.get("pins_file"):
            files.setdefault(hc["pins_file"], (hc["module"], tuple(hc["outline_um"])))
rep, report = {}, []
for pf, (mod, (w, h)) in sorted(files.items()):
    d = json.load(open(f"{pd}/{pf}"))
    faces = {}
    for q in d["pins"]:
        dd, face = min((h - q["y"], "N"), (q["y"], "S"), (w - q["x"], "E"), (q["x"], "W"))
        if dd < 0.5:
            faces.setdefault(face, []).append((dd, q))
    moved = []
    for face, lst in faces.items():
        if all(dd <= 1e-4 for dd, _ in lst) and any(dd > 1e-4 for l2 in faces.values() for dd, _ in l2) \
                and all(q["name"].startswith("strap_") for _, q in lst):
            for _, q in lst:
                assert mod in ("kv3_head_eighth_e0", "kv3_head_eighth_e2", "kv3_head_eighth_e6", "kv3_astk") \
                    and q["name"].startswith("strap_"), (pf, q)
                k, v = {"N": ("y", h - D_IN), "S": ("y", D_IN), "E": ("x", w - D_IN), "W": ("x", D_IN)}[face]
                q[k] = round(v, 4); moved.append(f"{q['name']}@{face}")
    if not moved:
        continue
    old = D.canon_sha256(D.canon_pins(json.load(open(f"{pd}/{pf}")), (w, h)))
    new = D.canon_sha256(D.canon_pins(d, (w, h)))
    d["source"] = d.get("source", "") + (" | CLOCK-KV hm_r26q4 10-27 D-KV-STRAP-FORM-2: edge-only faces -> centre form "
                                         f"(0.096 inward): {', '.join(moved)}")
    dst = pf.replace(".json", "_r26q4.json")
    open(f"{pd}/{dst}", "w").write(json.dumps(d, indent=1) + "\n")
    rep[pf] = dst
    report.append(dict(file=pf, new_file=dst, module=mod, moved=moved, canon_old=old, canon_new=new))
n = 0
for t in P["partition_types"].values():
    for hc in t.get("hard_cores", []):
        if hc.get("pins_file") in rep:
            hc["pins_file"] = rep[hc["pins_file"]]; n += 1
P["note"] = P.get("note", "") + " | hm_r26q4 (CLOCK-KV 10-27): D-KV-STRAP-FORM-2 e0/e2/e6 strap pins centre form"
open(f"{pd}/{pout}", "w").write(json.dumps(P, indent=1) + "\n")
json.dump(dict(repointed=n, files=report), open(f"{pd}/q4_straps_report.json", "w"), indent=1)
for r in report: print(r["file"], "->", r["new_file"], r["moved"], r["canon_old"][:8], "->", r["canon_new"])
print("repointed", n)
