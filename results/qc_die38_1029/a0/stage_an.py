"""DIE-QC-38 A0: per-stage measured clock delay vs the plan stage model (gen_a0_tree21.py STAGE TT 36.154 / FF 27.549)."""
import csv, sys, statistics as st, collections, json
D = sys.argv[1]
PLAN = {"tt": 36.154, "ff": 27.549}
def load(t, c):
    return {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_{c}.tsv"), delimiter="\t")}
def man(a, b): return abs(float(a["x"]) - float(b["x"])) + abs(float(a["y"]) - float(b["y"]))
out = {}
for t in ("nl", "nk"):
    for c in ("tt", "ff"):
        T = load(t, c)
        cls = collections.defaultdict(list)   # (class) -> (cell, wire, leg)
        for n, r in T.items():
            if r["kind"] != "node" or r["parent"] == "port:ck": continue
            p = T[r["parent"]]
            wire = float(r["in_max_r"]) - float(p["out_max_r"])
            cell = float(r["out_max_r"]) - float(r["in_max_r"])
            nm = r["inst"]
            k = ("ICG" if r["master"].startswith("ICG") else
                 "leaf_root" if nm.startswith("mp_a0_lr") else "leaf_dom" if nm.startswith("mp_a0_ld") else
                 "macro_chain" if nm.startswith("mp_a0_m") else "spread_s" if nm.startswith("mp_a0_s") else
                 "spread_d" if nm.startswith("mp_a0_d") else "other:" + r["master"])
            cls[k].append((cell, wire, man(p, r), int(r["fanout"]), cell + wire))
        # leaf -> sink wire (sink pin arrival - leaf out)
        ls = collections.defaultdict(list)
        for n, r in T.items():
            if r["kind"] != "sink": continue
            p = T[r["parent"]]
            k = "macro" if r["master"].startswith("ot_qwen") else "reg"
            ls[k].append((float(r["in_min_r"]) - float(p["out_min_r"]), man(p, r), float(r["in_min_r"]), r["depth"]))
        res = {}
        for k, v in sorted(cls.items()):
            stage = [x[4] for x in v]
            res[k] = dict(n=len(v), cell_mean=round(st.mean(x[0] for x in v), 2), wire_mean=round(st.mean(x[1] for x in v), 2),
                          stage_mean=round(st.mean(stage), 2), stage_min=round(min(stage), 2), stage_max=round(max(stage), 2),
                          leg_mean=round(st.mean(x[2] for x in v), 1), leg_max=round(max(x[2] for x in v), 1),
                          fan_mean=round(st.mean(x[3] for x in v), 1), vs_plan=round(st.mean(stage) - PLAN[c], 2))
        allst = [x[4] for v in cls.values() for x in v]
        res["ALL_nodes"] = dict(n=len(allst), stage_mean=round(st.mean(allst), 2), plan=PLAN[c])
        for k, v in ls.items():
            arr = [x[2] for x in v]
            res["sinkleg_" + k] = dict(n=len(v), wire_mean=round(st.mean(x[0] for x in v), 2), wire_max=round(max(x[0] for x in v), 2),
                                       leg_mean=round(st.mean(x[1] for x in v), 1), leg_max=round(max(x[1] for x in v), 1),
                                       arr_min=round(min(arr), 1), arr_max=round(max(arr), 1), arr_mean=round(st.mean(arr), 1),
                                       depths=dict(collections.Counter(x[3] for x in v)))
        # wire delay vs leg regression (spread nodes)
        pts = [(x[2], x[1]) for k in cls for x in cls[k]]
        mx = st.mean(p[0] for p in pts); my = st.mean(p[1] for p in pts)
        b = sum((p[0]-mx)*(p[1]-my) for p in pts) / sum((p[0]-mx)**2 for p in pts)
        res["wire_fit_ps_per_100um"] = round(b * 100, 2); res["wire_fit_icpt_ps"] = round(my - b * mx, 2)
        out[f"{t}_{c}"] = res
json.dump(out, open(f"{D}/stage_summary.json", "w"), indent=1)
for k, v in out.items():
    print("==", k)
    for kk, vv in v.items(): print("  ", kk, vv)
