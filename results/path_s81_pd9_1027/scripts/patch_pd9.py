import sys
fn = sys.argv[1]
s = open(fn).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:100]
    s = s.replace(old, new)

# 1. opt-in key parse
rep('''                      off_core=bool(lattice.get("off_core_resite", False)),''',
'''                      off_core=bool(lattice.get("off_core_resite", False)),
                      # PATH-S81-PD9 (opt-in, COORD RULING PATH-S81-PD8 ASK1 (b)): a leaf mesh driver with no die-top site
                      # (V strap or M8 row within drv_reach) is DROPPED instead of becoming an in-core island; the continuous
                      # mesh is driven there by its neighbours (its leaf-node sibling must remain)
                      off_core_drop=bool(lattice.get("off_core_drop_driver", False)),
                      # PATH-S81-PD9 (opt-in): a leg repeater with no die-top site on its leg L takes the alternate L
                      # orientation of the same leg (same length, same stage count) before any in-core pushdown
                      alt_l=bool(lattice.get("off_core_alt_l", False)),''')

# 2. driver drop
rep('''                isl = None
                if q is None:
                    q, d, isl = (x, y), 0.0, core_at(ko, (x, y))
                    if lg.get("canon"):''', '''                isl = None
                if q is None and lg.get("off_core_drop"):
                    out.setdefault("dropped_drivers", []).append(dict(name=f"ckm_d_{i}_{j}", i=i, j=j,
                                                                      ideal=[round(x, 3), round(y, 3)],
                                                                      core=core_at(ko, (x, y))))
                    continue
                if q is None:
                    q, d, isl = (x, y), 0.0, core_at(ko, (x, y))
                    if lg.get("canon"):''')

# 3. rec_lg leaf: tolerate a dropped driver
rep('''            if (kr[1] - kr[0]) * (kr[3] - kr[2]) == 1:
                dvr = out["drivers"][f"{kr[0]}_{kr[2]}"]
                b = tuple(dvr["site"])''', '''            if (kr[1] - kr[0]) * (kr[3] - kr[2]) == 1:
                dvr = out["drivers"].get(f"{kr[0]}_{kr[2]}")
                if dvr is None and lg.get("off_core_drop"):
                    # PATH-S81-PD9: dropped driver (no die-top site) -> no leaf leg; the sibling keeps the node loaded
                    out["htree"].append(dict(level=level + 1, tag=tag, a=list(here), b=list(kp), len_um=0.0,
                                             n_seg=1, reps=[], leaf=True, dropped=f"ckm_d_{kr[0]}_{kr[2]}"))
                    continue
                b = tuple(dvr["site"])''')

# 4. leg repeaters: alternate L
rep('''            reps, prev, first = [], None, None
            for k in range(1, n_seg):
                s0 = L * k / n_seg
                rq, rd = None, None''', '''            reps, prev, first = [], None, None
            if lg.get("alt_l") and n_seg > 1:
                def _rep_free(pl_):
                    for k_ in range(1, n_seg):
                        s_ = L * k_ / n_seg
                        ok_ = any(not hitf(K, poly_point(pl_, s_ + sg * kk * STEP_UM))
                                  for kk in range(0, int(L / n_seg / 2 / STEP_UM) + 1) for sg in (1, -1))
                        if not ok_ and free_near(K, poly_point(pl_, s_), limit=max(0.0, (lg["hop_reach"] - L / n_seg) / 2),
                                                 step=STEP_UM * 2)[0] is None:
                            return False
                    return True
                if not _rep_free(poly):
                    c2 = list(here)
                    c2[inc] = q[inc]
                    p2 = [tuple(here), tuple(c2), tuple(q)]
                    if _rep_free(p2):
                        poly = p2
                        out.setdefault("alt_l_legs", []).append(dict(tag=tag, level=level + 1, corner=[round(c2[0], 3), round(c2[1], 3)],
                                                                    first_axis="x" if inc == 0 else "y"))
            for k in range(1, n_seg):
                s0 = L * k / n_seg
                rq, rd = None, None''')

# 5. drop-safety check after rec_lg: a leaf node net must keep at least one driver
rep('''        rec_lg(0, nx, 0, nty, 0, n0, "h", (cells[n0]["x"] + BUF_W / 2, cells[n0]["y"] + ROW_Y / 2), 0.0)
        pl = [dv["path_um"] for dv in out["drivers"].values()]''', '''        rec_lg(0, nx, 0, nty, 0, n0, "h", (cells[n0]["x"] + BUF_W / 2, cells[n0]["y"] + ROW_Y / 2), 0.0)
        if out.get("dropped_drivers"):
            for n_ in nets:
                if not n_["loads"]:
                    out["unplaced"].append([n_["name"], "STRUCTURAL dropped drivers left a loadless tree net"])
            out["meta"]["dropped_drivers"] = [d_["name"] for d_ in out["dropped_drivers"]]
        pl = [dv["path_um"] for dv in out["drivers"].values()]''')
open(fn, "w").write(s)
print("patched pd9")
