#!/usr/bin/env python3
"""HBM-MU-QUAD-4: TYPE-REDUCTION + HUB-REPIN plan delta (owner 10-27: one canonical design per family, < ~80 designs;
no new pin-hash types; mirrored variants = orientation views).

Usage: type_reduce.py IN_PLAN_DIR OUT_PLAN_DIR --tools B1N_TOOLS_DIR --wt WORKTREE [--report R.json]

Family = functional identity of a hard core:
  * split pieces: the piece's functional module (+params) from physical/die_plan/hbm/over_cap_split/*.split.json
    (e.g. 64 ot_hbm_idx_score_quarter_static__rXcY_kZhH pieces = ot_hidx_score_hcol #(HALF 0|1): 2 designs);
  * pure-wiring split wrappers (physical/die_plan/hbm_arch_cores/wrappers): grouped by canonical top AND by the
    index-normalised port set; wrappers that differ only in constant ties (lane_lane_id) are ONE design whose
    constants become strap_* pins tied at the parent (OWNER 10-25 ID straps rule B);
  * otherwise the module itself (several pin tables of one module collapse to one).
Per family ONE canonical pin table (track lattice, M4 W/E, M5 N/S, 0.048 pitch, 8.64 end keep-out, <= 0.6 track use
per face) whose faces are chosen top-down from the plan partners (same partner model as check.py core_faces), and per
instance an orientation view (R0/MX/MY/R180) maximising pins facing partners.  Clock/reset pins keep the reference
member's coordinates (the die tap is the plan centre entry, orientation-invariant).  Port references of renamed
(index-normalised) ports are rewritten in the plan (internal_stations launch/capture, buses leaf, core_conns.json).
Deterministic; no outline or origin changes."""
import argparse, collections, copy, glob, hashlib, json, math, os, re, shutil, sys
from pathlib import Path

PITCH, OFF, INSET, END, TRK_MAX = 0.048, 0.024, 0.019, 8.64, 0.6
NORMAL = dict(N=(0.0, 1.0), S=(0.0, -1.0), E=(1.0, 0.0), W=(-1.0, 0.0))
OPP = dict(N="S", S="N", E="W", W="E")
ORIENTS = ("R0", "MX", "MY", "R180")
CLOCKISH = re.compile(r"^(clk|rst|clock|reset)", re.I)
IDXRE = re.compile(r"_(bank|lane)_([0-9]+)_")
RMAPS = {}          # module -> {index: rank} (index-normalised wrapper families)


def rmap_of(text):
    return {i: r for r, i in enumerate(sorted({int(m.group(2)) for m in IDXRE.finditer(text)}))}


def rsub(mod, p):
    rm = RMAPS.get(mod)
    return IDXRE.sub(lambda m: f"_{m.group(1)}_k{rm[int(m.group(2))]}_", p) if rm is not None else p


def tface(o, f):           # core-local face -> type-frame face under orient (check._core_face convention)
    if o in ("MX", "R180") and f in "NS":
        f = OPP[f]
    if o in ("MY", "R180") and f in "EW":
        f = OPP[f]
    return f


def lface(x, y, w, h):
    return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]


def base(n):
    return re.sub(r"\[\d+\]$", "", n)


def load_pins(plan, f):
    j = json.loads((plan / f).read_text())
    j = j.get("pins", j) if isinstance(j, dict) else j
    for p in j:
        if "name" not in p:
            p["name"] = p["bus"] if p.get("bit") is None else f"{p['bus']}[{p['bit']}]"
    return j


def families(wt, mods):
    fk = {}
    for f in glob.glob(str(wt / "physical/die_plan/hbm/over_cap_split/*.split.json")):
        j = json.loads(Path(f).read_text())
        for c in j["cores"]:
            fk[f"{j['master']}__{c['core_label']}"] = dict(fn=c.get("module"), src="split:" + Path(f).name,
                                                          rename=False)
    for f in glob.glob(str(wt / "physical/die_plan/hbm_arch_cores/wrappers/*.sv")):
        m = Path(f).stem
        s = Path(f).read_text()
        mm = re.search(r"canonical top (\w+)", s)
        if not mm or m in fk:
            continue
        body = re.sub(r"//.*", "", s)
        rm = rmap_of(body)
        nz = lambda x: IDXRE.sub(lambda mm: f"_{mm.group(1)}_k{rm[int(mm.group(2))]}_", x)
        ports = sorted(nz(l.strip().rstrip(",")) for l in body.splitlines()
                       if re.match(r"\s*(input|output) ", l))
        consts = {}
        for l in body.splitlines():
            c = re.match(r"\s*\.(\w+)\((\{[^}]*\}|\d+'[bhd][0-9a-fA-F_]+)\)", l.strip())
            if c:
                consts[c.group(1)] = c.group(2)
        conns = [nz(l.strip()) for l in body.splitlines() if l.strip().startswith(".")]
        shape = [re.sub(r"\{[^}]*\}|\d+'[bhd][0-9a-fA-F_]+", "K", c) for c in conns]
        key = hashlib.sha1(json.dumps([ports, shape]).encode()).hexdigest()[:6]
        fk[m] = dict(fn=f"{mm.group(1)}#{key}", src="wrapper", rename=True, consts=consts, rmap=rm)
    fam = collections.defaultdict(list)
    for m in mods:
        e = fk.get(m, dict(fn=m, src="self", rename=False))
        fam[e["fn"]].append((m, e))
    # straps: constants that differ between members of one wrapper family
    straps = {}
    for fn, mem in fam.items():
        if len(mem) > 1 and mem[0][1]["src"] == "wrapper":
            keys = set().union(*[set(e["consts"]) for _, e in mem])
            straps[fn] = sorted(k for k in keys if len({e["consts"].get(k) for _, e in mem}) > 1)
    return fam, straps


def lit_val(lit):
    if lit.startswith("{"):
        bits = [x.strip().split("'")[1][1:] for x in lit[1:-1].split(",") if x.strip()]
        return len(bits), int("".join(bits), 2)
    w, v = lit.split("'")
    return int(w), int(v[1:].replace("_", ""), {"b": 2, "h": 16, "d": 10}[v[0].lower()])


LANEK = re.compile(r"^lane([0-9]+)_lane_id$")


def strap_decl(cons, keys):
    d = {k: dict(zip(("width", "value"), lit_val(cons[k]))) for k in keys}
    # 4-lane groups: lane k id = {lane_lane_id, 2'dk} (ids consecutive, 4-aligned) -> ONE approved ID strap (rule B)
    if keys and all(LANEK.match(k) for k in keys):
        n = len(keys); sh = (n - 1).bit_length(); w0 = d["lane0_lane_id"]["width"]; base = d["lane0_lane_id"]["value"]
        assert base % n == 0 and all(d[f"lane{i}_lane_id"]["value"] == base + i for i in range(n)), d
        return {"lane_lane_id": {"width": w0 - sh, "value": base >> sh}}
    return d


def canon_name(fn, mem):
    ms = sorted(m for m, _ in mem)
    if len(ms) == 1:
        return ms[0]
    pre = os.path.commonprefix(ms)
    suf = os.path.commonprefix([m[len(pre):][::-1] for m in ms])[::-1]
    tag = re.sub(r"[^A-Za-z0-9]+", "_", fn.split("#")[0]).strip("_")
    if fn.startswith("ot_hidx_score_hcol"):
        return "ot_hbm_idx_score_hcol_h" + re.search(r"HALF (\d)", fn).group(1)
    if "#" in fn:
        return f"{pre.rstrip('_')}__canon_{fn.split('#')[1]}"
    return f"{pre}x{suf}" if pre else tag


def partner_dirs(C, S, plan_dir, raw):
    """{(type, inst): {port: [(ux,uy)]}} with check.py core_faces partner model."""
    P = S.Plan(raw, plan_dir / "die_plan.json")
    side = C.load_core_conns(str(plan_dir), None)
    res = {}
    for tn, t in P.types.items():
        hcs = t.get("hard_cores", [])
        if not hcs:
            continue
        w, h = t["outline_um"]
        boxes = {hc["inst"]: (hc["origin_um"][0] + hc.get("track_offset_um", [0, 0])[0] + hc["outline_um"][0] / 2,
                              hc["origin_um"][1] + hc.get("track_offset_um", [0, 0])[1] + hc["outline_um"][1] / 2)
                 for hc in hcs}
        cent = dict(boxes)
        for c in t.get("contents", []):
            if c["inst"] not in cent and "origin_um" in c and "outline_um" in c:
                cent[c["inst"]] = (c["origin_um"][0] + c["outline_um"][0] / 2, c["origin_um"][1] + c["outline_um"][1] / 2)
        ist_bus = [e for e in t.get("internal_stations", []) if str(e.get("conn", "")).startswith("bus:") and e.get("regs_um")]
        ist_last = {e["conn"][4:]: tuple(e["regs_um"][-1]) for e in ist_bus
                    if not e.get("capture") or str(e["capture"]).startswith("face bus ")}
        ist_cap = {(e["conn"][4:], str(e["capture"])): tuple(e["regs_um"][-1]) for e in ist_bus
                   if e.get("capture") and not str(e["capture"]).startswith("face bus ")}
        conns, net_ends = {}, {}
        for b in t.get("buses", []):
            if b.get("leaf") and "." in b["leaf"]:
                li, lp = b["leaf"].split(".", 1)
                conns.setdefault((li, lp), []).append(("bus", b["name"]))
        for c in t.get("contents", []):
            for lp, v in c.get("bind", {}).items():
                k, _, nm = v.partition(":")
                if k in ("bus", "epoch") and nm:
                    conns.setdefault((c["inst"], lp), []).append(("bus", nm))
                elif k == "net" and nm:
                    conns.setdefault((c["inst"], lp), []).append(("net", nm))
                    net_ends.setdefault(nm, set()).add(c["inst"])
        for ci, ports in side.get(tn, {}).items():
            for lp, lst in ports.items():
                for v in lst:
                    k, _, nm = v.partition(":")
                    conns.setdefault((ci, lp), []).append((k, nm))
        bt = C._bus_targets(P, tn)
        for hc in hcs:
            ci = hc["inst"]
            cx, cy = boxes[ci]
            mine = collections.defaultdict(list)
            for (li, lp), tg in conns.items():
                if li == ci or ci.startswith(li + "_"):
                    mine[lp].extend(tg)
            out = {}
            for lp, tg in mine.items():
                pts = []
                for kind, nm in tg:
                    if kind == "bus":
                        if (nm, ci + "." + lp) in ist_cap:
                            pts.append(ist_cap[(nm, ci + "." + lp)])
                        elif (nm, ci) in ist_cap:
                            pts.append(ist_cap[(nm, ci)])
                        elif nm in ist_last:
                            pts.append(ist_last[nm])
                        elif nm in bt:
                            pts.append(bt[nm][1])
                    elif kind == "net":
                        pts += [cent[oi] for oi in sorted(net_ends.get(nm, ())) if oi != ci and not ci.startswith(oi + "_") and oi in cent]
                    elif kind in ("core", "leaf") and nm in cent and nm != ci:
                        pts.append(cent[nm])
                    elif kind == "face" and nm in NORMAL:
                        pts.append(dict(N=(cx, h), S=(cx, 0.0), E=(w, cy), W=(0.0, cy))[nm])
                d = []
                for tx, ty in pts:
                    r = math.hypot(tx - cx, ty - cy)
                    if r > 1e-6:
                        d.append(((tx - cx) / r, (ty - cy) / r))
                if d:
                    out[lp] = d
            res[(tn, ci)] = out
    return res


def score(dirs, f):
    nx, ny = NORMAL[f]
    return max(nx * ux + ny * uy for ux, uy in dirs)


def place_face(names, side, w, h, used, fixed_tracks):
    length = h if side in "WE" else w
    lo, hi = END, length - END
    layer = "M4" if side in "WE" else "M5"
    n = len(names)
    cap = int((hi - lo) / PITCH)
    pins = []
    if n == 0:
        return pins
    if n > cap - len(fixed_tracks):
        raise ValueError(f"{side}: {n} pins > {cap} tracks")
    for i, name in enumerate(names):
        k = round((lo + (i + .5) * (hi - lo) / n - OFF) / PITCH)
        while k in used or k in fixed_tracks:
            k += 1
        used.add(k)
        pos = round(OFF + k * PITCH, 6)
        x, y = {"W": (INSET, pos), "E": (w - INSET, pos), "S": (pos, INSET), "N": (pos, h - INSET)}[side]
        pins.append(dict(name=name, layer=layer, x=round(x, 6), y=round(y, 6)))
    return pins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--tools", required=True); ap.add_argument("--wt", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--keep-orient", action="store_true")
    ap.add_argument("--override", default=None, help="JSON list: {type, inst, outline_um, origin_um, pins_src?, clk_xy?, regs_shift?}")
    ap.add_argument("--freeze-modules", default="", help="regex: groups of these modules stay exactly as they are (outline, pins, orient, module)")
    ap.add_argument("--regen-all", action="store_true", help="regenerate every table (default keeps a family's single existing table when no port faces away)")
    a = ap.parse_args()
    sys.path.insert(0, a.tools)
    import schema as S, check as C
    inp, out, wt = Path(a.inp), Path(a.out), Path(a.wt)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(inp, out)
    raw = json.loads((out / "die_plan.json").read_text())
    overrides = json.loads(Path(a.override).read_text()) if a.override else []
    for ov in overrides:
        t = raw["partition_types"][ov["type"]]
        hc = next(h for h in t["hard_cores"] if h["inst"] == ov["inst"])
        hc["_old_outline"] = list(hc["outline_um"])
        hc["outline_um"] = ov.get("outline_um", hc["outline_um"]); hc["origin_um"] = ov.get("origin_um", hc["origin_um"])
        if ov.get("pins_src"):
            dst = out / "cores" / Path(ov["pins_src"]).name
            shutil.copyfile(ov["pins_src"], dst); hc["pins_file"] = f"cores/{dst.name}"; hc["_keep"] = True
        elif ov.get("outline_um"):
            hc["_resize"] = True
        if ov.get("clk_xy"):
            hc["_clk_xy"] = ov["clk_xy"]
        for rs in ov.get("regs_shift", []):
            for e in t.get("internal_stations", []):
                if e.get("conn") == rs["conn"] and str(e.get("capture", "")).startswith(ov["inst"]):
                    e["regs_um"] = [[round(r[0] + rs["dx"], 3), r[1]] if abs(r[0] - rs["match_x"]) < 1e-6 else r for r in e["regs_um"]]
                    e["note"] = (e.get("note", "") + f" | HBM-MU-QUAD-4: column x {rs['match_x']} -> {rs['match_x'] + rs['dx']:.2f} for the {ov['inst']} re-pack").strip(" |")
        hc["plan_delta"] = ov.get("why", "HBM-MU-QUAD-4 override")
    ninst = collections.Counter(x["type"] for x in raw["partitions"])
    hcs = [(tn, hc) for tn, t in raw["partition_types"].items() for hc in t.get("hard_cores", [])]
    mods = sorted({hc["module"] for _, hc in hcs})
    fam, straps = families(wt, mods)
    m2f = {m: fn for fn, mem in fam.items() for m, _ in mem}
    rename = {fn: mem[0][1]["rename"] for fn, mem in fam.items()}

    for fn_, mem_ in fam.items():
        for m_, e_ in mem_:
            if e_.get("rename"):
                RMAPS[m_] = e_["rmap"]

    def cport(mod, p):
        return rsub(mod, p)

    before = collections.Counter()
    for tn, hc in hcs:
        pf = hc.get("pins_file")
        ph = hashlib.sha1((out / pf).read_bytes()).hexdigest()[:10] if pf else "NONE"
        before[(hc["module"], tuple(hc["outline_um"]), ph)] += ninst[tn]
    dirs = partner_dirs(C, S, out, raw)

    # group members by (family, outline, normalised bit set): variants only where function / ports differ
    groups = collections.defaultdict(list)
    for tn, hc in hcs:
        fn = m2f[hc["module"]]
        if hc.get("pins_file"):
            pins = load_pins(out, hc["pins_file"])
            bits = tuple(sorted(cport(hc["module"], p["name"]) for p in pins))
        else:
            pins, bits = [], ("<no pins>",)
        groups[(fn, tuple(hc["outline_um"]), hashlib.sha1(json.dumps(bits).encode()).hexdigest()[:6])].append((tn, hc, pins))
    fam_var = collections.Counter(k[0] for k in groups)
    report = dict(schema="opentallas.hbm.type_reduce.v1", lane="HBM-MU-QUAD-4", groups=[], blockers=[])
    newfiles = {}
    for key in sorted(groups):
        fn, (w, h), bh = key
        mem = groups[key]
        name = canon_name(fn, fam[fn]) + (f"__v{bh}" if fam_var[fn] > 1 else "")
        if not mem[0][2]:
            report["blockers"].append(dict(family=fn, canonical=name, why="no pins (keybuf: serialisation pending)",
                                           instances=[f"{t}:{h_['inst']}" for t, h_, _ in mem]))
            for tn, hc, _ in mem:
                hc["module_family"] = fn
            continue
        if a.freeze_modules and all(re.search(a.freeze_modules, hc["module"]) for _, hc, _ in mem):
            first = {}
            for _, hc, _ in mem:      # identical-content tables -> one file (pins unchanged, byte-identical)
                hh = hashlib.sha1((out / hc["pins_file"]).read_bytes()).hexdigest()
                hc["pins_file"] = first.setdefault(hh, hc["pins_file"])
            report["groups"].append(dict(family=fn, canonical="(frozen as-is)", outline=[w, h], frozen=True,
                                         members=sorted({hc["module"] for _, hc, _ in mem}), instances=sum(ninst[tn] for tn, _, _ in mem),
                                         tables=sorted({hc["pins_file"] for _, hc, _ in mem}), ports_away_before=None, ports_away=None, straps=[]))
            continue
        ref = mem[0][2]
        rmod = mem[0][1]["module"]
        # keep policy: one existing table, nothing facing away, no resize -> keep it byte-identical (no new pin hash)
        tabs = {hashlib.sha1((out / hc["pins_file"]).read_bytes()).hexdigest() for _, hc, _ in mem}
        cur_away = 0
        for tn, hc, pins in mem:
            dd = {}
            for lp, v in dirs.get((tn, hc["inst"]), {}).items():
                dd.setdefault(base(lp), []).extend(v)
            grp = collections.defaultdict(list)
            for p in pins:
                grp[base(p["name"])].append(score(dd[base(p["name"])], tface(hc.get("orient", "R0"), lface(p["x"], p["y"], w, h)))
                                           if base(p["name"]) in dd else None)
            cur_away += sum(1 for b, v in grp.items() if v[0] is not None and sum(v) / len(v) < -0.1)
        keep = any(hc.get("_keep") for _, hc, _ in mem) or (
            not a.regen_all and len(tabs) == 1 and cur_away == 0 and not any(hc.get("_resize") for _, hc, _ in mem))
        if keep:
            fnm = mem[0][1]["pins_file"]
            for tn, hc, _ in mem:
                hc["module_family"] = fn
                if hc["module"] != name:
                    hc["module_view_of"] = hc["module"]
                hc["module"] = name; hc["pins_file"] = fnm
                for k_ in ("_keep", "_old_outline", "_clk_xy"):
                    hc.pop(k_, None)
                if fn in straps and straps[fn]:
                    cons = dict(fam[fn]).get(hc.get("module_view_of", name), {}).get("consts", {})
                    hc["parent_id_straps"] = strap_decl(cons, straps[fn])
                if rename[fn]:
                    hc["port_rename"] = {str(k): f"k{v}" for k, v in RMAPS[hc.get("module_view_of", name)].items()}
            report["groups"].append(dict(family=fn, canonical=name, outline=[w, h], kept_table=True, pins_file=fnm,
                                         members=sorted({hc.get("module_view_of", hc["module"]) for _, hc, _ in mem}),
                                         instances=sum(ninst[tn] for tn, _, _ in mem), ports_away_before=cur_away, ports_away=cur_away,
                                         straps=straps.get(fn, [])))
            continue
        rs = mem[0][1].get("_old_outline") if mem[0][1].get("_resize") else None
        if rs:
            ref = [dict(p, x=round(p["x"] * w / rs[0], 3), y=round(p["y"] * h / rs[1], 3)) for p in ref]
        bybase = collections.OrderedDict()
        clk_pins = []
        for p in ref:
            cb = base(cport(rmod, p["name"]))
            if CLOCKISH.match(cb):
                q = dict(name=cport(rmod, p["name"]), layer=p["layer"], x=p["x"], y=p["y"])
                cxy = mem[0][1].get("_clk_xy")
                if cxy:
                    q.update(layer="M5", x=round(cxy[0] + 0.048 * len(clk_pins), 3), y=cxy[1])
                clk_pins.append(q)
            else:
                bybase.setdefault(cb, []).append(cport(rmod, p["name"]))
        ref_face = {b: collections.Counter(lface(p["x"], p["y"], w, h) for p in ref
                                           if base(cport(rmod, p["name"])) == b).most_common(1)[0][0] for b in bybase}
        # instance port dirs in canonical names
        idirs = []
        for tn, hc, _ in mem:
            d = {}
            for lp, v in dirs.get((tn, hc["inst"]), {}).items():
                d.setdefault(cport(hc["module"], base(lp)), []).extend(v)
            idirs.append(d)
        orient = [hc.get("orient", "R0") for _, hc, _ in mem]
        weight = [ninst[tn] for tn, _, _ in mem]
        faces = dict(ref_face)
        for _it in range(6):
            for b, bl in bybase.items():
                tot = {f: 0.0 for f in NORMAL}
                seen = False
                for i, d in enumerate(idirs):
                    if b in d:
                        seen = True
                        for f in NORMAL:
                            tot[f] += weight[i] * score(d[b], tface(orient[i], f))
                if seen:
                    faces[b] = max(sorted(tot), key=lambda f: (tot[f], f == ref_face[b]))
            if a.keep_orient:
                break
            for i, d in enumerate(idirs):
                def osc(o):
                    return sum(len(bybase[b]) * score(d[b], tface(o, faces[b])) for b in bybase if b in d)
                cur = orient[i]
                orient[i] = max(ORIENTS, key=lambda o: (osc(o) + (1e-6 if o == cur else 0)))
        # capacity: spill lowest-gain ports to next best face
        fixed = collections.defaultdict(set)
        for p in clk_pins:
            f = lface(p["x"], p["y"], w, h)
            pos = p["y"] if f in "WE" else p["x"]
            fixed[f].add(round((pos - OFF) / PITCH))
        def cap(f):
            L = h if f in "WE" else w
            return int(TRK_MAX * int((L - 2 * END) / PITCH)) - len(fixed[f])
        load = collections.Counter()
        for b, f in faces.items():
            load[f] += len(bybase[b])
        spilled = []
        for f in list(NORMAL):
            while load[f] > cap(f):
                cand = [b for b in bybase if faces[b] == f]
                def gain(b, g):
                    return sum(weight[i] * score(d[b], tface(orient[i], g)) for i, d in enumerate(idirs) if b in d)
                best = None
                for b in cand:
                    for g in NORMAL:
                        if g == f or load[g] + len(bybase[b]) > cap(g):
                            continue
                        loss = gain(b, f) - gain(b, g)
                        if best is None or loss < best[0]:
                            best = (loss, b, g)
                if best is None:
                    report["blockers"].append(dict(family=fn, canonical=name, why=f"face {f} over capacity {load[f]}>{cap(f)}"))
                    break
                _, b, g = best
                faces[b] = g; load[f] -= len(bybase[b]); load[g] += len(bybase[b]); spilled.append((b, f, g))
        pins = list(clk_pins)
        for f in ("W", "E", "S", "N"):
            names = [n for b in bybase if faces[b] == f for n in bybase[b]]
            # order along the face by mean partner tangent (fewer crossings), stable by name
            pins += place_face(names, f, w, h, set(), fixed[f])
        assert sorted(p["name"] for p in pins) == sorted(cport(rmod, p["name"]) for p in ref), name
        assert len({p["name"] for p in pins}) == len(pins), ("duplicate pin names", name)
        s = json.dumps(pins) + "\n"
        fnm = f"cores/{name}__{w:g}x{h:g}__canon.json"
        (out / fnm).write_text(s)
        newfiles[fnm] = hashlib.sha256(s.encode()).hexdigest()
        # quality: pins facing partners per instance
        away = tot_b = 0
        for i, d in enumerate(idirs):
            for b in bybase:
                if b in d:
                    tot_b += 1
                    away += score(d[b], tface(orient[i], faces[b])) < -0.1
        for i, (tn, hc, _) in enumerate(mem):
            old_mod = hc["module"]
            hc["module_family"] = fn
            if old_mod != name:
                hc["module_view_of"] = old_mod
            hc["module"] = name
            hc["pins_file"] = fnm
            for k_ in ("_keep", "_old_outline", "_clk_xy", "_resize"):
                hc.pop(k_, None)
            if orient[i] == "R0":
                hc.pop("orient", None)
            else:
                hc["orient"] = orient[i]
            if fn in straps and straps[fn]:
                cons = dict(fam[fn])[old_mod]["consts"] if old_mod in dict(fam[fn]) else {}
                hc["parent_id_straps"] = strap_decl(cons, straps[fn])
            if rename[fn]:
                hc["port_rename"] = {str(k): f"k{v}" for k, v in RMAPS[old_mod].items()}
        report["groups"].append(dict(family=fn, canonical=name, outline=[w, h], members=sorted({hc.get("module_view_of", hc["module"]) for _, hc, _ in mem}),
                                     instances=sum(weight), pins=len(pins), faces=dict(load), orients=dict(collections.Counter(orient)),
                                     ports_away_before=cur_away, ports_away=away, ports_checked=tot_b, spilled=spilled, straps=straps.get(fn, []), pins_file=fnm))
    # rewrite port references of renamed cores
    nref = 0
    for tn, t in raw["partition_types"].items():
        renm = {hc["inst"]: hc.get("module_view_of", hc["module"]) for hc in t.get("hard_cores", []) if hc.get("port_rename")}
        ren = set(renm)
        if not ren:
            continue
        pat = re.compile(r"\b(" + "|".join(map(re.escape, sorted(ren, key=len, reverse=True))) + r")\.(\w+)")
        def fix(o):
            nonlocal nref
            if isinstance(o, str):
                n2 = pat.sub(lambda m: m.group(1) + "." + rsub(renm[m.group(1)], m.group(2)), o)
                nref += n2 != o
                return n2
            if isinstance(o, list):
                return [fix(x) for x in o]
            if isinstance(o, dict):
                return {k: fix(v) for k, v in o.items()}
            return o
        for k in ("internal_stations", "buses", "ft_slots", "clock", "reset", "contents"):
            if k in t:
                t[k] = fix(t[k])
    cc = out / "core_conns.json"
    if cc.exists():
        J = json.loads(cc.read_text())
        ren = {(tn, hc["inst"]): hc.get("module_view_of", hc["module"]) for tn, t in raw["partition_types"].items() for hc in t.get("hard_cores", []) if hc.get("port_rename")}
        body = J.get("types", J) if isinstance(J, dict) else J
        for tn, insts in body.items():
            if not isinstance(insts, dict):
                continue
            for ci in list(insts):
                if (tn, ci) in ren and isinstance(insts[ci], dict):
                    insts[ci] = {rsub(ren[(tn, ci)], p): v for p, v in insts[ci].items()}
                    nref += 1
        cc.write_text(json.dumps(J, indent=1) + "\n")
    # drop pin tables no core references any more
    used = {hc.get("pins_file") for _, hc in hcs}
    for f in (out / "cores").glob("*.json"):
        if f"cores/{f.name}" not in used:
            f.unlink()
    after = collections.Counter()
    for tn, hc in hcs:
        after[(hc["module"], tuple(hc["outline_um"]), hashlib.sha1((out / hc["pins_file"]).read_bytes()).hexdigest()[:10] if hc.get("pins_file") else "NONE")] += ninst[tn]
    report["census"] = dict(before_designs=len(before), before_modules=len({k[0] for k in before}),
                            after_designs=len(after), after_modules=len({k[0] for k in after}),
                            families=len(fam), instances=sum(before.values()), port_refs_rewritten=nref)
    views = {}
    for tn, t in raw["partition_types"].items():
        for hc in t.get("hard_cores", []):
            v = {k: hc.pop(k) for k in ("module_family", "module_view_of", "port_rename", "plan_delta") if k in hc}
            if v:
                views.setdefault(tn, {})[hc["inst"]] = v
                if v.get("module_view_of") or v.get("plan_delta"):
                    hc["note"] = (hc.get("note", "") + " | HBM-MU-QUAD-4: " + (f"canonical view of {v['module_view_of']}" if v.get("module_view_of") else "") +
                                  (f"; {v['plan_delta']}" if v.get("plan_delta") else "")).strip(" |")
    (out / "type_views.json").write_text(json.dumps(dict(schema="opentallas.hbm.type_views.v1", lane="HBM-MU-QUAD-4", views=views), indent=1) + "\n")
    s = json.dumps(raw, indent=1) + "\n"
    (out / "die_plan.json").write_text(s)
    (out / "die_plan.sha256").write_text(hashlib.sha256(s.encode()).hexdigest() + "  die_plan.json\n")
    report["plan_sha256"] = hashlib.sha256(s.encode()).hexdigest()
    report["new_pin_tables"] = newfiles
    Path(a.report or out / "type_reduce_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report["census"]), "blockers", len(report["blockers"]))
    for g in report["groups"]:
        if g["ports_away"]:
            print("away", g["canonical"], g["ports_away_before"], "->", g["ports_away"], "/", g.get("ports_checked"), g.get("orients", "kept"))


if __name__ == "__main__":
    main()
