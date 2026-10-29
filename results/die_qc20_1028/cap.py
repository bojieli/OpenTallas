# DIE-QC-20 probe: run the trial13 kit up to attach_region_dme, pickle its inputs, stop.
import sys, pickle, runpy
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-qc19-1028/tools/die_plan")
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-qc19-1028/tools")
sys.setrecursionlimit(100000)
import die_trial as D
def cap(nodes, site, taps, regions, **kw):
    pickle.dump(dict(nodes=nodes, site=site, taps=taps, regions=regions, kw=kw), open("cap.pkl", "wb"))
    print("CAPTURED", len(taps), flush=True); raise SystemExit(0)
D.attach_region_dme = cap
sys.argv = ["die_trial.py"] + sys.argv[1:]
D.main()
