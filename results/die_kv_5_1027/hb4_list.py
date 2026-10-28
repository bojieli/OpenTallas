"""DIE-KV-5 HB4 PREP: kit-contract hold pairs -> HB4 input list for the KV partition kits (ASK1 form, COORD 22:43:
HB4 placed and routed in the kits, not modelled).  Input: hb4_dump.py record of the MAIN die_sta_related run (spice clock,
--cppr-lca, table OCV, shared droop, TT 250 / FF 202.5) + plan + proof mesh (seam pairs per plan port).
Per pair: deficit_nom = damage - W (kit-contract form, = the tool's neg pairs) and deficit_ocv = damage + clock OCV - W
(R18 additive form).  k = ceil(deficit / HB4 FF early 44.6 ps) per bit.  Kits are per TYPE (template replicas): the kit
input is the MAX over the type's instances, per (launch tap, capture tap) for intra and per receiving input bus for seam.
    hb4_list.py DUMP PLAN PROOF_DIR TOOLDIR OUT_JSON"""
import json, math, sys
from collections import defaultdict
from pathlib import Path
dump, planf, proof, tool, outf = sys.argv[1:6]
sys.path.insert(0, tool)
import die_clock as DC
import schema as S
HB = dict(cell="HB4xp67_ASAP7_75t_R", ff_early_ps=44.6, tt_late_ps=91.3, area_um2=0.1021)
D = json.load(open(dump)); plan = json.load(open(planf))
ptype = {p["name"]: p["type"] for p in plan["partitions"]}
ports = {p["id"]: p for p in plan["ports"]}
intra, seam = D["kit"][0], D["kit"][1]
assert intra["neg_pairs_tool"] == 24 and seam["neg_pairs_tool"] == 339, "not the DIE-KV-4 spice run"
M = json.loads((Path(proof) / "mesh.json").read_text())
tb = defaultdict(list)
tapset = {r["launch"] for r in seam["pairs"]} | {r["capture"] for r in seam["pairs"]}
for t in M["taps"]:
    if t["port"] in tapset:
        tb[t["part"]].append(dict(port=t["port"], part=t["part"], xy=t["xy"]))
sp = DC.seam_pairs(S.Plan(S.load(planf)), tb)          # (src tap, dst tap, port id) -> bits
by_pair = defaultdict(list)
for (a, b, pid), n in sp.items():
    by_pair[(a, b)].append((pid, n))


def k_of(d):
    return max(0, math.ceil(d / HB["ff_early_ps"] - 1e-9)) if d > 0 else 0


def local(tap):
    return tap.split("__", 1)[1] if "__" in tap else tap


res = {}
for cls, rec in (("intra", intra), ("seam", seam)):
    W = rec["window_ps"]
    rows = []
    for r in rec["pairs"]:
        dn, do = r["damage_ps"] - W, r["damage_ps"] + r["ocv_hold_ps"] - W
        if do <= 0 and dn <= 0:
            continue
        x = dict(r, deficit_nom_ps=round(dn, 2), deficit_ocv_ps=round(do, 2), k_nom=k_of(dn), k_ocv=k_of(do),
                 capture_type=ptype[r["capture_part"]], launch_type=ptype[r["launch_part"]])
        if cls == "seam":
            x["ports"] = [dict(port=pid, bits=n, dst_bus=ports[pid]["dst"]["bus"], src_bus=ports[pid]["src"]["bus"])
                          for pid, n in sorted(by_pair.get((r["launch"], r["capture"]), []))]
            x["bits"] = sum(p["bits"] for p in x["ports"])
        rows.append(x)
    nom = [x for x in rows if x["deficit_nom_ps"] > 0]
    kit = defaultdict(dict)
    for x in rows:
        t = x["capture_type"]
        keys = ([(local(x["launch"]), local(x["capture"]))] if cls == "intra" else
                [(x["launch_type"] + "." + p["src_bus"], p["dst_bus"]) for p in x["ports"]] or [("?", "?")])
        for kk in keys:
            ks = "->".join(kk)
            e = kit[t].setdefault(ks, dict(deficit_nom_ps=-1e9, deficit_ocv_ps=-1e9, instances=[]))
            e["deficit_nom_ps"] = max(e["deficit_nom_ps"], x["deficit_nom_ps"])
            e["deficit_ocv_ps"] = max(e["deficit_ocv_ps"], x["deficit_ocv_ps"])
            e["instances"].append(x["capture_part"])
    for t in kit.values():
        for e in t.values():
            e.update(k_nom=k_of(e["deficit_nom_ps"]), k_ocv=k_of(e["deficit_ocv_ps"]), instances=sorted(set(e["instances"])))
    summ = dict(window_ps=W, pairs_kit_contract_nom=len(nom), pairs_kit_contract_ocv=len(rows),
                worst_deficit_nom_ps=max((x["deficit_nom_ps"] for x in rows), default=0),
                worst_deficit_ocv_ps=max((x["deficit_ocv_ps"] for x in rows), default=0),
                k_nom_hist={str(k): sum(1 for x in nom if x["k_nom"] == k) for k in sorted({x["k_nom"] for x in nom})},
                k_ocv_hist={str(k): sum(1 for x in rows if x["k_ocv"] == k) for k in sorted({x["k_ocv"] for x in rows})},
                capture_types=len(kit), kit_entries=sum(len(v) for v in kit.values()))
    if cls == "seam":
        summ.update(bits_nom=sum(x["bits"] for x in nom), cells_nom=sum(x["bits"] * x["k_nom"] for x in nom),
                    bits_ocv=sum(x["bits"] for x in rows), cells_ocv=sum(x["bits"] * x["k_ocv"] for x in rows),
                    pairs_without_seam_bits=sum(1 for x in rows if not x["ports"]))
    res[cls] = dict(summary=summ, pairs=sorted(rows, key=lambda x: -x["deficit_ocv_ps"]),
                    kit_inputs={t: dict(sorted(v.items())) for t, v in sorted(kit.items())})
out = dict(hb4=HB, source=dict(dump=dump, plan=planf, proof=proof,
           sta="main die_sta_related (wt die-kv-5 = main 810b714798 + meso-reconcile 32e8cbb16) --clock-cal spice --cppr-lca "
               "--clock-ocv table --clock-droop shared --hold-buffers HB4 --core-latency-ff 202.5"),
           use="kit SDC input: intra = per (launch tap, capture tap) extra early window beyond plan tap_window W (kit hold "
               "repair places HB4 on those reg->reg D pins); seam = per receiving input bus extra hold (set_input_delay -min "
               "reduced by deficit) so the receiving kit places HB4 at its input face register; size with deficit_ocv "
               "(safe form), deficit_nom = the tool's kit-contract neg pairs", **res)
json.dump(out, open(outf, "w"), indent=1)
for c in ("intra", "seam"):
    print(c, json.dumps(res[c]["summary"]))
    print("  types:", {t: len(v) for t, v in res[c]["kit_inputs"].items()})
