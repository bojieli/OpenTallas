import sys, json
sys.path.insert(0, "/srv/opentallas-scratch2/claude/die-hbm-1027/est/src/tools/die_plan"); sys.argv=["locality.py"]
import locality as Lc
plan, tag, mp, out, v = sys.argv[0:0] or __import__("os").environ["A"].split("|")
D0 = Lc.load_plan(plan)
reg = Lc.load_regions(mp, D0)
Lc.propose = lambda *a, **k: reg
Lc.run_v3(plan, "hbm", float(v), out, maps_in=[(tag, mp)], tree_cfgs=(), feeds=("fish",), render_png=False, v_note="single-map score x1.05 spice")
