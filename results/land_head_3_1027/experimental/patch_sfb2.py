p="tools/die_plan/die_trial.py"; s=open(p).read()
def rep(a,b,n=1):
    global s
    assert s.count(a)==n,(a[:80],s.count(a)); s=s.replace(a,b)
rep('''            xa = (D + lb - la) / 2
            if xa < 0 or xa > D:
                clamp = max(clamp, abs(min(xa, D - xa)))
                xa = min(max(xa, 0.0), D)
            nxt.append((ya + xa, max(la + xa, lb + D - xa), ("m", ya + xa, sa, sb)))''','''            xa = (D + lb - la) / 2
            da = db = 0.0
            if xa < 0 or xa > D:
                clamp = max(clamp, abs(min(xa, D - xa)))
                if matched:       # matched: balance by a detour leg on the shorter side (no clamp skew)
                    db, da = (la - lb - D, 0.0) if xa < 0 else (0.0, lb - la - D)
                xa = min(max(xa, 0.0), D)
            nxt.append((ya + xa, max(la + xa + da, lb + D - xa + db), ("m", ya + xa, sa, sb, da, db)))''')
rep('''        _, y, sa, sb = st
        i = parent if abs(nodes[parent]["y"] - y) < 1e-6 else mk(sx, y, parent, level, spine=True)
        place(sa, i, nodes[i]["level"] + 1)
        place(sb, i, nodes[i]["level"] + 1)''','''        _, y, sa, sb, da, db = st
        i = parent if abs(nodes[parent]["y"] - y) < 1e-6 else mk(sx, y, parent, level, spine=True)
        for ch, det in ((sa, da), (sb, db)):
            par = i
            if det > 1e-6:      # detour node beside the spine at the child's y: leg = |dy| + det/2, back det/2
                par = mk(sx + det / 2 if sx + det / 2 < P.W else sx - det / 2, ch[1], i, nodes[i]["level"] + 1,
                         spine=True, detour_um=round(det, 1))
            place(ch, par, nodes[par]["level"] + 1)''')
rep('''    def place(st, parent, level):
        if st[0] == "rib":
            i = parent if abs(nodes[parent]["y"] - st[1]) < 1e-6 else mk(sx, st[1], parent, level, spine=True)''','''    def place(st, parent, level):
        if st[0] == "rib":
            i = parent if (abs(nodes[parent]["y"] - st[1]) < 1e-6 and abs(nodes[parent]["x"] - sx) < 1e-6) else \\
                mk(sx, st[1], parent, level, spine=True)''')
open(p,"w").write(s)
