import sys
D = sys.argv[1]
def patch(p, pairs):
    s = open(D + "/" + p).read()
    for a, b in pairs:
        assert s.count(a) == 1, (p, a[:60], s.count(a))
        s = s.replace(a, b)
    open(D + "/" + p, "w").write(s)
patch("count_align_plan.py", [
("""         skew_clean=False, _pad_pass=False, tree_parent=None):""",
 """         skew_clean=False, _pad_pass=False, tree_parent=None, max_depth=8):"""),
("""    gets its crossing as the start edge itself (no path ambiguity); refused if the src lies in the child's subtree.\"\"\"""",
 """    gets its crossing as the start edge itself (no path ambiguity); refused if the src lies in the child's subtree.
    max_depth (DIE-S81-11, METHODOLOGY 12.16 b(iii), opt-in): largest standard ring DEPTH, 8 (default, unchanged) or 16
    (RTL proof: results/die_s81_11_1028/D16.md, ot_dp_clk_landing_ca lag sweep [0.5, 15.5] T, mutants caught); a
    crossing takes the smallest of 4 / 8 / 16 whose window holds L_hi with ap (16 only when max_depth = 16).\"\"\"
    if max_depth not in (8, 16):
        raise ValueError(f"max_depth {max_depth}: standard ring depths are 8 or 16")"""),
("""        s0, out0, regs0 = plan([dict(r) for r in rows], *args, edge_pad, start_skew, True, True, tree_parent)""",
 """        s0, out0, regs0 = plan([dict(r) for r in rows], *args, edge_pad, start_skew, True, True, tree_parent, max_depth)"""),
("""        summ, out, regs = plan(rows, *args, ep, start_skew, True, True, tree_parent)""",
 """        summ, out, regs = plan(rows, *args, ep, start_skew, True, True, tree_parent, max_depth)"""),
("""        sn, outn, _ = plan([dict(r) for r in rows], *args, edge_pad, start_skew, tree_parent=tree_parent)""",
 """        sn, outn, _ = plan([dict(r) for r in rows], *args, edge_pad, start_skew, tree_parent=tree_parent,
                           max_depth=max_depth)"""),
("""        dep = 4 if L_hi <= 3.5 * T - nh + 1e-9 else (8 if L_hi <= 7.5 * T - nh + 1e-9 else None)""",
 """        dep = next((dd for dd in (4, 8, 16) if dd <= max_depth and L_hi <= (dd - 0.5) * T - nh + 1e-9), None)"""),
("""                depth8=sum(1 for o in ok if o["depth"] == 8), fail=len(out) - len(ok),""",
 """                depth8=sum(1 for o in ok if o["depth"] == 8), depth16=sum(1 for o in ok if o["depth"] == 16),
                max_depth=max_depth, fail=len(out) - len(ok),"""),
("""    ap.add_argument("--mc-chips", type=int, default=0)""",
 """    ap.add_argument("--max-depth", type=int, choices=(8, 16), default=8,
                    help="DIE-S81-11 / 12.16 b(iii) opt-in: largest standard ring DEPTH (16 needs its RTL proof; default 8)")
    ap.add_argument("--mc-chips", type=int, default=0)"""),
("""                           a.start_skew, a.start_skew_clean, tree_parent=parse_edge_pad(a.tree_parent, str) or None)""",
 """                           a.start_skew, a.start_skew_clean, tree_parent=parse_edge_pad(a.tree_parent, str) or None,
                           max_depth=a.max_depth)"""),
])
patch("count_align_bind.py", [("""for k in (4, 8)},""", """for k in (4, 8, 16)},""")])
patch("clock_landings.py", [("""                if int(c["depth"]) not in (4, 8):
                    raise LandingError(f"count-aligned landing {pid}: DEPTH {c['depth']} not 4/8")""",
"""                if int(c["depth"]) not in (4, 8, 16):
                    raise LandingError(f"count-aligned landing {pid}: DEPTH {c['depth']} not 4/8/16")""")])
print("patched")
