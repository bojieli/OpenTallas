import json, sys, math
p = json.load(open(sys.argv[1]))
out = {}
for tn in ("kv3_sys_SD", "kv3_sys_SD_v1"):
    t = p["partition_types"][tn]
    c = t["contents"][0]; ox, oy = c["origin_um"]; w, h = c["outline_um"]
    H = 4.32
    mac = (ox, oy, ox + w, oy + h); mach = (ox - H, oy - H, ox + w + H, oy + h + H)
    isl = t["clock"]["die_islands_um"]
    ov = lambda r, m: r[0] < m[2] and r[2] > m[0] and r[1] < m[3] and r[3] > m[1]
    inside = [r for r in isl if ov(r, mach)]
    # cluster by 20 um proximity
    cl = []
    for r in sorted(inside):
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        for g in cl:
            if abs(g["cx"] - cx) < 20 and abs(g["cy"] - cy) < 20:
                g["n"] += 1; g["rects"].append(r); break
        else:
            cl.append(dict(cx=cx, cy=cy, n=1, rects=[r]))
    for g in cl:
        cx, cy = g["cx"], g["cy"]
        # nearest legal exit: W rim, E channel, S rim, N rim (outside halo)
        d = {"W": cx - mach[0], "E": mach[2] - cx, "S": cy - mach[1], "N": mach[3] - cy}
        g["exit"], g["move_um"] = min(d.items(), key=lambda kv: kv[1])
        g["exit_xy"] = {"W": (mach[0] - 1.5, cy), "E": (mach[2] + 1.5, cy), "S": (cx, mach[1] - 1.5), "N": (cx, mach[3] + 1.5)}[g["exit"]]
        del g["rects"]
    outside = len(isl) - len(inside)
    out[tn] = dict(macro=mac, macro_halo=mach, outline=t["outline_um"], islands=len(isl), on_macro=len(inside), off_macro=outside,
                   clusters=sorted(cl, key=lambda g: (g["cy"], g["cx"])))
    print(tn, "islands", len(isl), "on macro(+halo)", len(inside), "clusters", len(cl))
    for g in out[tn]["clusters"]:
        print("  c(%.1f,%.1f) n=%d exit %s move %.1f" % (g["cx"], g["cy"], g["n"], g["exit"], g["move_um"]))
    offs = [r for r in isl if not ov(r, mach)]
    print("  off-macro:", [[round(v,1) for v in r] for r in offs][:20])
json.dump(out, open(sys.argv[2], "w"), indent=1)
