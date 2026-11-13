"""QC-S28-ROUTE: R1/R2 variant table on HF-1c (measured on the plan's own port windows, check.py G0 faces rule).
Per variant and column: for each touched seam, pins after, design density (pins / seam), the free length for the
moved ports vs their window_for() length at 6 pins/um (no foreign window moved), and the full-repack bound
(pins / (seam - 2 x 4.32 core inset) <= 6.0, i.e. even with every foreign window re-sized)."""
import sys, json
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/qc-s28-route/tools/die_plan")
import schema as S
raw = json.load(open(sys.argv[1])); P = S.Plan(raw)
OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}; G = 0.96; M = 4.32
PER = P.budgets["face_pins_per_um"]
def wl(n): return S.window_for(0.0, n, ["M7", "M5"], P.layers, per_um=PER, track_max=P.budgets["pin_track_max"])
idx = {}
for pid, pr in P.ports.items():
    f = pr["face"]
    if pr["src"]["part"] != "@die": idx.setdefault((pr["src"]["part"], f), []).append(pid)
    if pr["dst"]["part"] != "@die": idx.setdefault((pr["dst"]["part"], OPP[f]), []).append(pid)
B = {"x": "__x_fw_ctl__", "p1": "__x_fw_ctl_p1__", "p2": "__x_fw_ctl_p2__", "r": "__x_su_l1_ctl__"}
W = {"x": 536, "p1": 536, "p2": 536, "r": 456}
def seam(c, a, b):
    pa, pb = f"sl_{c}_{a}", f"sl_{c}_{b}"
    ax0, ay0, ax1, ay1 = P.rect(pa); bx0, by0, bx1, by1 = P.rect(pb)
    lo, hi = max(ax0, bx0), min(ax1, bx1)
    ids = [p for p in idx.get((pa, "N"), []) if pb in (P.ports[p]["src"]["part"], P.ports[p]["dst"]["part"])]
    return hi - lo, ids
# seam -> buses on it per variant (direct entry seams into the ctl row + the su detour seams)
SE = [("fw", "st_a"), ("stm", "ctl"), ("sc", "ctl"), ("fe", "st_b")]
VAR = {
    "a_none":                 {"fw|st_a": "x", "stm|ctl": "", "sc|ctl": "p1 r", "fe|st_b": "p2"},
    "b_R2":                   {"fw|st_a": "x", "stm|ctl": "r", "sc|ctl": "p1", "fe|st_b": "p2"},
    "c_R2+p2_st_a":           {"fw|st_a": "x p2", "stm|ctl": "r", "sc|ctl": "p1", "fe|st_b": ""},
    "d_R2+p1_stm+p2_st_a":    {"fw|st_a": "x p2", "stm|ctl": "r p1", "sc|ctl": "", "fe|st_b": ""},
    "R1_as_drawn(p1,p2_stm)+R2": {"fw|st_a": "x", "stm|ctl": "r p1 p2", "sc|ctl": "", "fe|st_b": ""},
    "e1_p2_sc+R2_detour_fe_st_b": {"fw|st_a": "x", "stm|ctl": "", "sc|ctl": "p1 p2", "fe|st_b": "r"},
    "e2_p2_st_a_only":        {"fw|st_a": "x p2", "stm|ctl": "", "sc|ctl": "p1 r", "fe|st_b": ""},
    "e3_p2_sc_only":          {"fw|st_a": "x", "stm|ctl": "", "sc|ctl": "p1 p2 r", "fe|st_b": ""},
}
cols = [f"{s}{i}" for s in "EW" for i in range(6)]
print("variant\tcolumn\tseam\tseam_um\tpins_other\tmine\tpins_after\tpins_per_um\tneed_um\tfree_um(no foreign move)\tfits_as_is\trepack_bound_per_um\tfits_repacked")
summary = {}
for v, asg in VAR.items():
    ok_all, ok_rep = True, True
    for c in cols:
        for a, b in SE:
            L, ids = seam(c, a, b)
            mine_ids = [p for p in ids if any(t in p for t in B.values())]
            oth = [p for p in ids if p not in mine_ids]
            po = sum(P.ports[p]["width"] for p in oth)
            used = sum(abs(P.ports[p]["window_um"][1] - P.ports[p]["window_um"][0]) for p in oth) + G * len(oth)
            free = L - 2 * M - used + G
            ms = asg[f"{a}|{b}"].split()
            pm = sum(W[m] for m in ms)
            need = sum(wl(W[m]) for m in ms) + G * max(0, len(ms) - 1)
            fit = need <= free + 1e-6
            rep = (po + pm) / (L - 2 * M)
            fr = rep <= PER + 1e-9
            ok_all &= fit; ok_rep &= fr
            print(f"{v}\t{c}\t{a}|{b}\t{L:.2f}\t{po}\t{'+'.join(ms) or '-'}\t{po + pm}\t{(po + pm) / L:.2f}\t{need:.1f}\t{free:.1f}\t{'PASS' if fit else 'FAIL'}\t{rep:.2f}\t{'PASS' if fr else 'FAIL'}")
    summary[v] = (ok_all, ok_rep)
for v, (a, b) in summary.items():
    print(f"# {v}: G0 faces as-is (my ports only) {'PASS' if a else 'FAIL'}; with every foreign window on the seam re-sized {'PASS' if b else 'FAIL'}", file=sys.stderr)
