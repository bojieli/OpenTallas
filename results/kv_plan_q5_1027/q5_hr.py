"""KV-PLAN-DELTA-3 hm_r26q5 part (c) D-KV-HR-PIN-FORM (COORD 12:23 ruling on KV-KITS-7/HR 12:04 ASK):
(1) every qkd_hr_* pin file: each edge-form pin (centre ON the outline, d = 0) moves 0.096 um inward along the face normal
    to the centre form the kits emit (gen_core_kit_kv io.tcl: edge -/+ half pin length; PREFLIGHT-2 pins_canonical saw
    exactly 0.096 on 1577/1577 phy_pad pins).  x/y along the face, layer, names unchanged; interior pins untouched.
(2) qkd_hr_phy_pad: the 12.8a centre entry named in the file's source (KV-CORE-SLICE-1) was never applied -- ck_phy[0] sat
    on the N edge (43.224, 95.04), rst_n[0] on the S edge (71.112, 0).  Both -> the core-centre entry in the host_qm form
    (clock on the M5 track at the centre, reset 0.384 east, same y): ck_phy[0] (43.224, 47.52), rst_n[0] (43.608, 47.52).
    Plan outline of record = 86.4 x 95.04 @ (77.76, 120.96) (KV-CORE-SLICE-1 ASK-3 APPROVED); the 138.24 x 129.6 the
    HR triage saw is the pre-slice outline in a stale die_plan copy, not in hm_r26q4/q5 (checked: hm_r26q4 hard_cores).
(3) kv3_hub_Wi clock taps that name an hr core pin get their xy recomputed from the moved pin (instance orient applied).
    q5_hr.py PD PLAN_IN PLAN_OUT"""
import json, sys, copy
pd, pin_, pout = sys.argv[1:4]
D_IN, EPS = 0.096, 1e-4
P = json.load(open(pin_)); q = copy.deepcopy(P)
files, insts = {}, []
for tn, t in P["partition_types"].items():
    for hc in t.get("hard_cores", []):
        if hc["module"].startswith("qkd_hr_"):
            files.setdefault(hc["pins_file"], (hc["module"], tuple(hc["outline_um"])))
            insts.append((tn, hc))
rep, report = {}, []
for pf, (mod, (w, h)) in sorted(files.items()):
    d = json.load(open(f"{pd}/{pf}"))
    moved = dict(N=0, S=0, E=0, W=0); special = []
    for p in d["pins"]:
        if mod == "qkd_hr_phy_pad" and p["name"] in ("ck_phy[0]", "rst_n[0]"):
            old = (p["x"], p["y"])
            p["x"], p["y"] = (43.224, 47.52) if p["name"] == "ck_phy[0]" else (43.608, 47.52)
            assert abs(p["x"] - 0.024 - round((p["x"] - 0.024) / 0.048) * 0.048) < 1e-6 and p["layer"] == "M5"
            special.append(f"{p['name']} {old} -> ({p['x']}, {p['y']}) centre entry"); continue
        dd, f = min((h - p["y"], "N"), (p["y"], "S"), (w - p["x"], "E"), (p["x"], "W"))
        if dd < -EPS: raise SystemExit(f"{pf} {p} outside")
        if dd <= EPS:
            k, v = {"N": ("y", h - D_IN), "S": ("y", D_IN), "E": ("x", w - D_IN), "W": ("x", D_IN)}[f]
            p[k] = round(v, 4); moved[f] += 1
    if not any(moved.values()) and not special: continue
    d["source"] = d.get("source", "") + (f" | KV-PLAN-DELTA-3 hm_r26q5 10-27 D-KV-HR-PIN-FORM: edge -> centre form 0.096 inward "
                                         f"{ {k: v for k, v in moved.items() if v} }" + (f"; {'; '.join(special)}" if special else ""))
    dst = pf.replace(".json", "_r26q5.json"); assert dst != pf
    open(f"{pd}/{dst}", "w").write(json.dumps(d, indent=1) + "\n")
    rep[pf] = (dst, {p["name"]: (p["x"], p["y"]) for p in d["pins"]})
    report.append(dict(file=pf, new_file=dst, module=mod, moved=moved, special=special))
def img(o, w, h, x, y):
    return ({"R0": x, "MX": x, "MY": w - x, "R180": w - x}[o], {"R0": y, "MY": y, "MX": h - y, "R180": h - y}[o])
ntap = 0
for tn, hc in insts:
    if hc["pins_file"] not in rep: continue
    dst, pins = rep[hc["pins_file"]]; hc["pins_file"] = dst
    w, h = hc["outline_um"]; o = hc.get("orient", "R0"); ox, oy = hc["origin_um"]
    for tp in P["partition_types"][tn]["clock"]["taps"]:
        if tp["name"].startswith(hc["inst"] + "."):
            pn = tp["name"][len(hc["inst"]) + 1:]
            if pn in pins:
                x, y = img(o, w, h, *pins[pn]); new = [round(ox + x, 4), round(oy + y, 4)]
                if new != tp["xy"]:
                    tp["note"] = tp.get("note", "") + f" | hm_r26q5 D-KV-HR-PIN-FORM: xy {tp['xy']} -> {new} (pin moved)"
                    tp["xy"] = new; ntap += 1
for k in P:
    if k != "partition_types": assert P[k] == q[k], k
for tn in P["partition_types"]:
    if tn != "kv3_hub_Wi": assert P["partition_types"][tn] == q["partition_types"][tn], tn
P["note"] = P.get("note", "") + " | hm_r26q5 D-KV-HR-PIN-FORM qkd_hr pins centre form + phy_pad centre clock/reset entry"
open(pout, "w").write(json.dumps(P, indent=1) + "\n")
json.dump(dict(files=report, taps_moved=ntap), open(f"{pd}/q5_hr_report.json", "w"), indent=1)
for r in report: print(r["module"], r["new_file"], r["moved"], r["special"])
print("files", len(report), "taps moved", ntap)
