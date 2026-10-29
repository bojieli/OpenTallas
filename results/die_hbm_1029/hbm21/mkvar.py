#!/usr/bin/env python3
"""DIE-HBM-17: kit-variant plan views from c25c_d16k (NOT plan candidates: stations are not re-sited; the winning
variant becomes a plan event with station_resite). Per variant: new core outline, edge pins scaled along their own
face (order kept, layer kept, track residue kept, >= 0.096 um same-layer spacing), N/E pins follow the new edge,
interior pins scaled; instance origin = nearest legal 4.32-lattice origin (non-overlap incl 4.32 halo); clock entry =
nearest 4.32-lattice point to the core centre whose 8.64 island clears every macro + 4.32 halo.
usage: mkvar.py BASE_DIR OUT_DIR SPEC_JSON"""
import json, os, sys, shutil, math, copy
G = 4.32; HALO = 4.32
base, out, spec = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
if os.path.exists(out): shutil.rmtree(out)
shutil.copytree(base, out, copy_function=os.link)
def rw(path, obj):
    os.unlink(path); json.dump(obj, open(path, "w"), indent=1)
plan = json.load(open(out + "/die_plan.json"))
cmf = json.load(open(out + "/core_macros.json")); ce = json.load(open(out + "/clock_entries.json")); ent = json.load(open(out + "/entries.json"))
PITCH = {"M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}
rep = {"base": base, "variants": []}
def scale_pins(pins, w, h, nw, nh):
    faces = {}
    for i, r in enumerate(pins):
        x, y = r["x"], r["y"]
        dd = {"W": x, "E": w - x, "S": y, "N": h - y}
        f = min(dd, key=dd.get)
        if dd[f] > 1.5: f = "I"
        faces.setdefault((f, r["layer"]), []).append(i)
    new = copy.deepcopy(pins)
    for (f, lay), idx in faces.items():
        p = PITCH.get(lay, 0.048)
        along = "x" if f in "SNI" else "y"
        L, nL = (w, nw) if along == "x" else (h, nh)
        idx.sort(key=lambda i: pins[i][along])
        prev = -1e9
        for i in idx:
            v = pins[i][along]; res = v % p
            t = v * nL / L
            t = res + round((t - res) / p) * p
            mind = 2 * p if f != "I" else p
            if t < prev + mind - 1e-9: t = prev + mind
            t = res + math.ceil((t - res) / p - 1e-9) * p
            new[i][along] = round(t, 4); prev = t
        mx = max(new[i][along] for i in idx)
        endc = min(0.5, L - max(pins[i][along] for i in idx))
        if f != "I" and mx > nL - endc + 1e-6:
            raise SystemExit(f"face {f}/{lay}: {len(idx)} pins do not fit on {nL} (last {mx:.3f})")
        for i in idx:
            if f == "N": new[i]["y"] = round(pins[i]["y"] - h + nh, 4)
            if f == "E": new[i]["x"] = round(pins[i]["x"] - w + nw, 4)
            if f == "I":
                o = "y" if along == "x" else "x"
                new[i][o] = round(pins[i][o] * (nh if o == "y" else nw) / (h if o == "y" else w), 4)
    return new
def free(nx, ny, nw, nh, rects, me):
    for (j, x2, y2, w2, h2) in rects:
        if j != me and nx < x2 + w2 + HALO and x2 < nx + nw + HALO and ny < y2 + h2 + HALO and y2 < ny + nh + HALO:
            return False
    return True
for v in spec:
    mod, nw, nh = v["module"], v["w"], v["h"]
    newpf = {}
    for tn, t in plan["partition_types"].items():
        hcs = t.get("hard_cores", [])
        for hc in hcs:
            if hc["module"] != mod: continue
            w, h = hc["outline_um"]; pf = hc["pins_file"]
            if pf not in newpf:
                nf = pf[:-5] + "__" + v["tag"] + ".json"
                json.dump(scale_pins(json.load(open(out + "/" + pf)), w, h, nw, nh), open(out + "/" + nf, "w"))
                newpf[pf] = nf
            W, H = t["outline_um"]
            rects = [(o["inst"], o["origin_um"][0], o["origin_um"][1], o["outline_um"][0], o["outline_um"][1]) for o in hcs]
            x, y = hc["origin_um"]; cx, cy = x + w / 2, y + h / 2; best = None
            for dx in range(-40, 41):
                for dy in range(-40, 41):
                    nx, ny = x + dx * 2 * G, y + dy * 2 * G
                    if nx < 0 or ny < 0 or nx + nw > W or ny + nh > H: continue
                    d = abs(nx + nw / 2 - cx) + abs(ny + nh / 2 - cy)
                    if best and d >= best[0]: continue
                    if free(nx, ny, nw, nh, rects, hc["inst"]): best = (d, nx, ny)
            if not best: raise SystemExit(f"{tn} {hc['inst']}: no legal origin within 345 um")
            hc["origin_um"] = [round(best[1], 4), round(best[2], 4)]; hc["outline_um"] = [nw, nh]; hc["pins_file"] = newpf[pf]
            hc["note"] = hc.get("note", "") + f" | DIE-HBM-17 kit variant {v['tag']} {nw}x{nh} (shift {best[0]:.2f} um; stations NOT re-sited)"
            rep["variants"].append(dict(tag=v["tag"], type=tn, inst=hc["inst"], shift_um=round(best[0], 3), origin=hc["origin_um"]))
    macros = v.get("macros")
    c = cmf["cores"].setdefault(mod, {})
    if macros is not None:
        c["macros"] = [dict(m) for m in macros]
    c["outline_um"] = [nw, nh]
    ms = [m["rect_um"] for m in c.get("macros", [])]
    for m in ms:
        assert m[2] <= nw - 4.32 + 1e-6 and m[3] <= nh - 4.32 + 1e-6, (mod, m)
    best = None
    for i in range(int(nw / G) + 1):
        for j in range(int(nh / G) + 1):
            ex, ey = i * G, j * G
            isl = (ex - G, ey - G, ex + G, ey + G)
            if isl[0] < 4.32 or isl[1] < 4.32 or isl[2] > nw - 4.32 or isl[3] > nh - 4.32: continue
            if any(isl[0] < m[2] + HALO and m[0] - HALO < isl[2] and isl[1] < m[3] + HALO and m[1] - HALO < isl[3] for m in ms): continue
            d = abs(ex - nw / 2) + abs(ey - nh / 2)
            if not best or d < best[0]: best = (d, ex, ey)
    ex, ey = round(best[1], 4), round(best[2], 4)
    ent[mod] = {"source": f"DIE-HBM-17 kit variant {v['tag']}: nearest macro-free 4.32 point to centre", "xy": [ex, ey]}
    for tn in ce:
        for k, e in ce[tn].items():
            if isinstance(e, dict) and e.get("module") == mod:
                e["xy_um"] = [ex, ey]; e["island_um"] = [round(ex - G, 4), round(ey - G, 4), round(ex + G, 4), round(ey + G, 4)]
                e["source"] = e.get("source", "") + f" | DIE-HBM-17 variant {v['tag']}"
    rep.setdefault("entries", {})[v["tag"]] = [ex, ey]
rw(out + "/die_plan.json", plan); rw(out + "/core_macros.json", cmf); rw(out + "/clock_entries.json", ce); rw(out + "/entries.json", ent)
json.dump(rep, open(out + "/mkvar_report.json", "w"), indent=1)
print(json.dumps(rep)[:3000])
