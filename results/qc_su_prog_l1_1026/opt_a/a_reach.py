# QC-SU-PROG-L1 option (a) reach check: maze distance (su_tree_uf_ls maze, macros + 2.2 halo blocked) from two equal-length
# W/E trunk nodes in the y~135 SRAM gap to every ls island of the k5/k6 prog plans. Plan-only.
import json, runpy, sys
sys.argv = ["su_tree_uf_ls", "/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/r2/prog_m0.geo", "/dev/null", "100", "6", "6", "64", "/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/lib"]
g = runpy.run_path("/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/code/results/qc_su_kits/r4/su_tree_uf_ls.py", run_name="x")
cell, md, xy = g["cell"], g["md"], g["xy"]
ent = cell(g["entry"])
for k in (5, 6):
    gj = json.load(open("/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/sweep_mr2/prog_ls_k%d_S13.gate.json" % k))
    isl = [tuple(i["plan_xy"]) for i in gj["gates"]["G2_island_rows"]["islands"]]
    print("k", k, "entry->island", [round(md(ent, cell(p)), 1) for p in isl])
    for off in (30, 60, 86.4):
        W_, E_ = cell((177.12 - off, 135.0)), cell((177.12 + off, 135.0))
        dW, dE = md(ent, W_), md(ent, E_)
        rows = []
        for q, p in enumerate(isl):
            a, b = md(W_, cell(p)), md(E_, cell(p))
            rows.append(("Q%d" % q, "W" if a <= b else "E", round(min(a, b), 1)))
        L = [r[2] for r in rows]
        print("  trunk +-%.1f (W %s %.1f, E %s %.1f) trunk->island" % (off, xy(W_), dW, xy(E_), dE), rows, "spread %.1f" % (max(L) - min(L)))
