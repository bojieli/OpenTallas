p="tools/die_plan/die_trial.py"; s=open(p).read()
def rep(a,b,n=1):
    global s
    assert s.count(a)==n,(a[:80],s.count(a)); s=s.replace(a,b)
rep('''def build_spine_fishbone(P, taps, col_um=60.0, merge_um=800.0):''','''def build_spine_fishbone(P, taps, col_um=60.0, merge_um=800.0, matched=False, station_max_taps=24):''')
rep('''    items = [(r, 0.0, ("rib", r)) for r in ribs]''','''    # LAND-HEAD-3 matched=True (12.13b phase-matched rib heads): (a) a rib with <= station_max_taps taps (a station row,
    # pitch ~1.4 mm, too long for a travelling rib) is a 1-D zero-skew DME along the row; (b) on a channel rib the spine
    # partition entry gets a detour leg equal to the column-0 trunk + mean stub, so it is in phase with o0/b0;
    # (c) the spine DME balances the rib HEAD lengths (the entries that cross between ribs), not just the rib roots.
    head_len, row_dme = {}, {}
    if matched:
        for r in ribs:
            tl = by_rib[r]
            if len(tl) <= station_max_taps:
                its = sorted(((t[2], abs(t[3] - r), ("tap", t)) for t in tl), key=lambda v: v[0])
                while len(its) > 1:
                    nx = []
                    for k2 in range(0, len(its) - 1, 2):
                        (xa, la_, sa), (xb, lb_, sb) = its[k2], its[k2 + 1]
                        D = xb - xa
                        xa2 = min(max((D + lb_ - la_) / 2, 0.0), D)
                        nx.append((xa + xa2, max(la_ + xa2, lb_ + D - xa2), ("m", xa + xa2, sa, sb)))
                    if len(its) % 2:
                        nx.append(its[-1])
                    its = nx
                row_dme[r] = its[0]
                head_len[r] = abs(its[0][0] - sx) + its[0][1]
            else:
                cx0 = min((abs(t[2] - sx) for t in tl if abs(t[2] - sx) > col_um), default=0.0)
                stubs = [abs(t[3] - r) for t in tl if abs(abs(t[2] - sx) - cx0) <= col_um]
                head_len[r] = cx0 + (sum(stubs) / len(stubs) if stubs else 0.0)
    items = [(r, head_len.get(r, 0.0), ("rib", r)) for r in ribs]''')
rep('''    # (2) ribs
    for r in ribs:
        r0 = rib_root[r]''','''    # (2) ribs
    for r in ribs:
        r0 = rib_root[r]
        if r in row_dme:          # matched station row: 1-D zero-skew DME hung below the rib root
            xr, _, st = row_dme[r]
            top = mk(xr, r, r0, nodes[r0]["level"] + 1, rib=r) if abs(xr - nodes[r0]["x"]) > 1e-6 else r0
            stk = [(st, top)]
            while stk:
                s2, par = stk.pop()
                if s2[0] == "tap":
                    t = s2[1]
                    lf = mk(t[2], t[3], par, nodes[par]["level"] + 1, rib=r)
                    nodes[lf]["taps"].append(t)
                else:
                    i = mk(s2[1], r, par, nodes[par]["level"] + 1, rib=r) if abs(s2[1] - nodes[par]["x"]) > 1e-6 else par
                    stk += [(s2[2], i), (s2[3], i)]
            continue''')
rep('''                if abs(cx - sx) <= col_um and prev == r0:
                    tn = r0''','''                if abs(cx - sx) <= col_um and prev == r0 and matched and head_len.get(r, 0) > 2 * col_um:
                    h2 = head_len[r] / 2
                    q = mk(sx, r + h2 if r + h2 < P.H else r - h2, r0, nodes[r0]["level"] + 1, rib=r, detour_um=round(h2 * 2, 1))
                    tn = mk(sx, r, q, nodes[q]["level"] + 1, rib=r)
                    for t in c:
                        nodes[tn]["taps"].append(t)
                    continue
                if abs(cx - sx) <= col_um and prev == r0:
                    tn = r0''')
rep('''    nodes = (build_spine_fishbone(P, taps) if tree_form == "spine_fishbone" else''','''    nodes = (build_spine_fishbone(P, taps, **(tree_opts or {})) if tree_form == "spine_fishbone" else''')
open(p,"w").write(s)
