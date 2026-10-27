import sys, json, time, collections
sys.path.insert(0, "/w/die_plan")
import qc_clk_mesh3 as M
ap = M.argparse.ArgumentParser(); M.add_common(ap)
a = ap.parse_args(("--r2 inputs/r2_plan_w.json --stage inputs/stage_table.json --no-spine --top-w 16w --top-m 2 --top-reach 450 " + " ".join(sys.argv[1:])).split())
t0 = time.time()
st = M.Stage(a.stage); B = M.build(a, st)
print("build s", round(time.time() - t0, 1), "groot_x", B.get("groot_x"))
I = B["islands"]
if I: print("slots", len(I.slots), "types", len(I.types))
tp, by = M.paths(B["top_nodes"])
for c in ("TT", "FF"):
    arr = [sum(0 for e in ch) for ch in tp.values()]
stg = collections.Counter(sum(e["nseg"] for e in ch) for ch in tp.values())
print("stages", stg)
print("root T", B["top_root"]["T"], "imb max", max(abs(n.get("imbalance_TT") or 0) for n in B["top_nodes"]))
bad = [ (n["tag"], n["xy"], n.get("nseg"), n.get("leg")) for n in B["top_nodes"] if n.get("nseg") and n.get("leg") and n["nseg"] > M.math.ceil(n["leg"]/450)+2]
print("overstaged legs", len(bad), bad[:6])
cy = I.col_y(B["top_root"]["xy"][0]); print("trunk col slots", len(cy), cy[:5], "maxgap", max(b-a for a,b in zip(cy,cy[1:])) if len(cy)>1 else None)
cells, ls = M.legalize(B)
print(json.dumps({k: v for k, v in ls.items() if k != "islands"}, default=str)[:1500])
if ls.get("islands"):
    d = dict(ls["islands"]); pt = d.pop("per_type")
    print(json.dumps(d, default=str))
    worst = sorted(pt.items(), key=lambda kv: -kv[1]["used_slots_union"])[:6]
    print(json.dumps(worst))
