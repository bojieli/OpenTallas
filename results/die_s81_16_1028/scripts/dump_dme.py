"""DIE-S81-16 probe: run the go14 kit argv up to attach_region_dme, pickle every dme_region_tree call (site, taps, kw),
continue each region in HANG mode (fast), then stop.  Usage: dump_dme.py <tool_dir> <dump_dir> -- <die_trial argv>"""
import pickle, sys, time
tool, dump = sys.argv[1], sys.argv[2]
argv = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, tool)
sys.setrecursionlimit(100000)
import die_trial as D
orig = D.dme_region_tree
n = [0]
def wrap(site, taps, **kw):
    n[0] += 1
    with open(f"{dump}/call_{n[0]:03d}.pkl", "wb") as f:
        pickle.dump(dict(site=site, taps=taps, kw=kw), f)
    # trivial placeholder tree (root + one leaf per tap) so the run reaches the next region fast; output discarded
    q = (taps[0][2], taps[0][3])
    out = [dict(x=q[0], y=q[1], kids=list(range(1, len(taps) + 1)), taps=[], S=0.0, Smin=0.0, W=0.0)]
    out += [dict(x=t[2], y=t[3], kids=[], taps=[t], S=0.0, Smin=0.0, W=0.0) for t in taps]
    print(f"call {n[0]} taps {len(taps)}", flush=True)
    return out, 0, dict(snakes=0, snake_wire_um=0.0, snake_buffers=0, merges=0, imbalanced=0, worst_imbalance_um=0.0, extra_wire_um=0.0, topology={}, spread_um=0.0)
D.dme_region_tree = wrap
oa = D.attach_region_dme
def stop(*a, **k):
    r = oa(*a, **k)
    print("DONE attach_region_dme", n[0], flush=True)
    sys.exit(0)
D.attach_region_dme = stop
sys.argv = ["die_trial.py"] + argv
D.main()
