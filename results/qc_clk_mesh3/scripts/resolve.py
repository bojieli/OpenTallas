"""R12 re-solve on snapped sites: build -> legalize (island slots) -> per-edge legal-minus-model delay (TT, FF) ->
write corr json for the next build; reports model and legal leaf-arrival spread per iteration.  UNCHECKED."""
import sys, json, collections
sys.path.insert(0, "/w/die_plan")
import qc_clk_mesh3 as M
out = sys.argv[1]; extra = sys.argv[2:]
ap = M.argparse.ArgumentParser(); M.add_common(ap)
a = ap.parse_args(("--r2 inputs/r2_plan_w.json --stage inputs/stage_table.json --no-spine --top-w 16w --top-m 2 --top-reach 450 --islands type " + " ".join(extra)).split())
st = M.Stage(a.stage); B = M.build(a, st)
I = B["islands"]; top = B["et"]["top"]
cells, ls = M.legalize(B); B["cells"] = cells
PE = M.phys_edges(B)
by = {n["tag"]: n for n in B["top_nodes"]}
old = M.CORR[0]
corr, res = {}, {}
for c in ("TT", "FF"):
    dm, dlg = {}, {}
    for n in B["top_nodes"]:
        if not n.get("parent"): continue
        p = by[n["parent"]]["xy"]; q = n["xy"]; hor = abs(p[1]-q[1]) < 1e-6
        ax = "x" if hor else "y"; i = 0 if hor else 1
        dm[n["tag"]] = (I.chain_delay(top, c, ax, p[1-i], p[i], q[i], n["nseg"]) if (hor or abs(p[0]-q[0]) < 1e-6) else top.delay(n["leg"], c, n["nseg"])) + old.get(n["tag"], {}).get(c, 0.0)
        dlg[n["tag"]] = sum(top.st.seg(top.w, top.m, c, L) for _, _, L in PE[("t", n["tag"])])
        corr.setdefault(n["tag"], {})[c] = round(old.get(n["tag"], {}).get(c, 0.0) + dlg[n["tag"]] - dm[n["tag"]], 4)
    tp, _ = M.paths(B["top_nodes"])
    ms = [sum(dm[e["tag"]] for e in ch) for ch in tp.values()]
    lg = [sum(dlg[e["tag"]] for e in ch) for ch in tp.values()]
    res[c] = dict(model_spread=round(max(ms)-min(ms), 3), legal_top_spread=round(max(lg)-min(lg), 3), legal_max=round(max(lg), 2))
stg = collections.Counter(sum(e["nseg"] for e in ch) for ch in tp.values())
isl = {k: v for k, v in (ls.get("islands") or {}).items() if k != "per_type"}
json.dump(dict(corr=corr, res=res, stages=dict(stg), islands=isl, label="UNCHECKED"), open(out, "w"))
print(json.dumps(dict(res=res, stages=dict(stg), islands={k: isl.get(k) for k in ("groups_on_slots", "max_move_um", "moved_gt_1um")})))
