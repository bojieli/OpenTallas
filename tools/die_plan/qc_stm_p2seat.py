#!/usr/bin/env python3
"""QC-INT-R2-HCSETUP 11-26, class C-LEG405 (intra-core): derive the STM P2 leaf -> complete-tree partition from a type's own
placed p2l seats.

qfd_dv_stream_tile has NK = 9 complete trees (cloud of 64 slot-hit + 64 mask flops each) and NL2 = 235 P2 leaves p2l[i].
Index order (i / 27) mixes leaves that sit at the east pin column (x ~ 550 um) with leaves at the tree cloud (x ~ 190..290 um),
and the cloud follows the near leaves, so the complete -> p2l leg is 540..700 um (sle_stm_v2 cl7b3062fa / cl55be2264).
OT_QC_STM_P2SEAT gives the far leaves (this script's FAR set) a tree of their own and keeps the near leaves in index order
over the other 8 trees.  The RTL carries the FAR set as P2FAR; --check compares it with the seat table.

  qc_stm_p2seat.py SEATS.tsv [--far-x 400] [--png OUT.png] [--rtl rtl/qwen_dv/qfd_dv_stream_tile.sv]
SEATS.tsv: lines "p2l <i> <x_um> <y_um>" and "shq <i> <x_um> <y_um>" (from a placed ODB: u_stream.p2l[i] / u_stream.shq_t[i]).
Prints JSON: far leaves, old / new per-tree leaf box and worst leg to the tree cloud centroid.  Exit 1 when --rtl is given and
its P2FAR differs from the derived set.
"""
import argparse, json, re, statistics as st, sys

NK, NL2 = 9, 235


def load(p):
    p2, sh = {}, {}
    for l in open(p):
        f = l.split()
        if len(f) == 4 and f[0] in ("p2l", "shq"):
            (p2 if f[0] == "p2l" else sh)[int(f[1])] = (float(f[2]), float(f[3]))
    return p2, sh


def parts(far):
    lpt = (NL2 + NK - 1) // NK
    old = {i: i // lpt for i in range(NL2)}
    lpn = (NL2 - len(far) + NK - 2) // (NK - 1)
    new, n = {}, 0
    for i in range(NL2):
        if i in far:
            new[i] = NK - 1
        else:
            new[i] = n // lpn
            n += 1
    return old, new


def legs(part, p2, cloud):
    out = []
    for k in range(NK):
        pts = [p2[i] for i in part if part[i] == k and i in p2]
        if not pts:
            continue
        cx, cy = cloud[k]
        out.append(dict(tree=k, leaves=len(pts), x=[round(min(p[0] for p in pts)), round(max(p[0] for p in pts))],
                        y=[round(min(p[1] for p in pts)), round(max(p[1] for p in pts))],
                        worst_leg_um=round(max(abs(p[0] - cx) + abs(p[1] - cy) for p in pts))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seats"); ap.add_argument("--far-x", type=float, default=400.0)
    ap.add_argument("--png"); ap.add_argument("--rtl")
    a = ap.parse_args()
    p2, sh = load(a.seats)
    far = sorted(i for i, (x, y) in p2.items() if x > a.far_x)
    old, new = parts(set(far))
    cloud = {k: (st.mean(sh[i][0] for i in range(64 * k, 64 * k + 64)), st.mean(sh[i][1] for i in range(64 * k, 64 * k + 64)))
             for k in range(NK)}
    # the cloud of a tree sits at the near leaves it serves; the far tree's cloud is the open question (needs a place probe)
    res = dict(far=far, old=legs(old, p2, cloud), new=legs(new, p2, cloud))
    print(json.dumps(res))
    if a.png:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(12, 9), sharey=True)
        cm = plt.get_cmap("tab10")
        for axx, part, ttl in ((ax[0], old, "index order i/27"), (ax[1], new, "P2SEAT (far leaves = tree 8)")):
            for i, (x, y) in p2.items():
                axx.scatter(x, y, s=22, color=cm(part[i]), edgecolor="k" if i in far else "none", linewidth=1.2)
            for k in range(NK):
                axx.scatter(*cloud[k], marker="s", s=70, color=cm(k), edgecolor="k")
            axx.set_title(ttl + "  (square = tree cloud, circle = p2l leaf, outlined = far)"); axx.set_xlabel("x um")
            axx.set_xlim(0, 613); axx.grid(alpha=.3)
        ax[0].set_ylabel("y um"); fig.tight_layout(); fig.savefig(a.png, dpi=70)
    if a.rtl:
        s = open(a.rtl).read()
        got = sorted(int(x) for x in re.findall(r"<< (\d+)\)", s.split("P2FAR =")[1].split(";")[0]))
        if got != far:
            print("P2FAR MISMATCH rtl %s seats %s" % (got, far)); return 1
        print("P2FAR matches the seat table")
    return 0


if __name__ == "__main__":
    sys.exit(main())
