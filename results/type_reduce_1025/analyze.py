#!/usr/bin/env python3
"""TYPE-REDUCE 10-25: distinct-design census of release-die plans (read-only).
usage: analyze.py ROOT OUTDIR   (ROOT = tree with physical/die_plan/...)"""
import json, sys, re, hashlib, collections, csv, os
sys.path.insert(0, os.path.join(sys.argv[1], 'tools/die_plan'))
import dedup as D
ROOT, OUT = sys.argv[1], sys.argv[2]
DIES = [("s81", "s81"), ("s81_head", "s81_head"), ("qwen_compute", "qwen_compute"), ("qwen_kvsys", "qwen_kvsys"), ("hbm", "hbm_arch/B2n")]
H = lambda x: hashlib.sha1(D._canon(x).encode()).hexdigest()[:10]
ORI = ("R0", "MX", "MY", "R180")

def pin_tab(path, w, h, ori="R0"):
    try:
        pins = json.load(open(path))
    except Exception as e:
        return None
    if isinstance(pins, dict):
        pins = pins.get("pins", [])
    out = []
    for p in pins:
        x, y = float(p["x"]), float(p["y"])
        if ori in ("MY", "R180"): x = w - x
        if ori in ("MX", "R180"): y = h - y
        out.append((p["name"], p.get("layer"), round(x, 2), round(y, 2)))
    return tuple(sorted(out))

def face_tab(path, w, h):
    """name -> face (N/S/E/W) of the pin, orientation-free signature on face sets"""
    pins = json.load(open(path))
    if isinstance(pins, dict): pins = pins.get("pins", [])
    f = {}
    for p in pins:
        x, y = float(p["x"]), float(p["y"])
        d = {"W": x, "E": w - x, "S": y, "N": h - y}
        f[p["name"]] = min(d, key=d.get)
    return f

def base(k):
    return re.sub(r"__t\d+$", "", k)

summary = {}
rows_t, rows_c = [], []
for die, pd in DIES:
    pdir = os.path.join(ROOT, "physical/die_plan", pd)
    P = json.load(open(os.path.join(pdir, "die_plan.json")))
    T = P["partition_types"]
    ninst = collections.Counter(p["type"] for p in P["partitions"])
    lv = collections.defaultdict(set)
    for k, t in T.items():
        nk = D.netlist_key(t)
        nk_noslot = D.netlist_key(t, slots=False)
        nk_noparam = D.netlist_key(t, params=False, slots=False)
        rtl = H(dict(c=sorted(D._canon(D._strip(c, D.CONTENT_GEOM)) for c in t.get("contents", [])),
                     cores=sorted(c["module"] for c in t.get("hard_cores", []))))
        rtl_mod = H(dict(c=sorted(c["module"] for c in t.get("contents", [])),
                         cores=sorted(set(c["module"] for c in t.get("hard_cores", [])))))
        iface = H(sorted(D._canon({a: b.get(a) for a in ("name", "dir", "width", "kind")}) for b in t.get("buses", [])))
        pint = H(dict(b=sorted(D._canon({a: b.get(a) for a in ("name", "face", "window_um", "layers", "order")}) for b in t.get("buses", [])),
                      s=sorted(D._canon(D._strip(s, {"bit_sites_um", "regs_um", "note", "stations"})) for s in t.get("ft_slots", []))))
        ftset = H(sorted((s.get("width"), s.get("in_face"), s.get("out_face")) for s in t.get("ft_slots", [])))
        anon = H(dict(o=t["outline_um"], c=sorted((c["module"], D._canon(c.get("params"))) for c in t.get("contents", [])),
                      hc=sorted(c["module"] for c in t.get("hard_cores", [])),
                      b=sorted((b["dir"], b["width"], b.get("kind")) for b in t.get("buses", [])),
                      s=sorted((s["width"], s.get("stations")) for s in t.get("ft_slots", []))))
        r = dict(die=die, type=k, family=base(k), module=t.get("module"), n_inst=ninst.get(k, 0),
                 w=t["outline_um"][0], h=t["outline_um"][1], area_mm2=round(t["outline_um"][0] * t["outline_um"][1] / 1e6, 4),
                 n_bus=len(t.get("buses", [])), n_ft=len(t.get("ft_slots", [])), ft_bits=sum(s.get("width", 0) for s in t.get("ft_slots", [])),
                 n_cont=len(t.get("contents", [])), n_cores=len(t.get("hard_cores", [])),
                 k_netlist=H(nk), k_anon=anon, k_noslot=H(nk_noslot), k_noparam=H(nk_noparam), k_rtl=rtl, k_rtlmod=rtl_mod,
                 k_iface=iface, k_pins=pint, k_ftset=ftset,
                 k_rtl_iface=H([rtl, iface]), k_rtlmod_iface=H([rtl_mod, iface]))
        rows_t.append(r)
        for key in ("type", "k_anon", "k_netlist", "k_noslot", "k_noparam", "k_rtl", "k_rtlmod", "k_rtl_iface", "k_rtlmod_iface", "family"):
            lv[key].add(r[key])
    # cores
    insts = collections.defaultdict(list)
    for k, t in T.items():
        for h in t.get("hard_cores", []):
            insts[h["module"]].append((k, h))
    cm = {}
    for m, L in sorted(insts.items()):
        outl = {tuple(h["outline_um"]) for _, h in L}
        w, hh = list(outl)[0]
        tabs, cls, faces = set(), [], set()
        for k, h in L:
            pf = os.path.join(pdir, h["pins_file"]) if h.get("pins_file") else None
            tab = pin_tab(pf, w, hh) if pf else None
            tabs.add(H(tab))
            if tab is not None:
                # orient class: min hash over 4 orients
                cls.append(min(H(pin_tab(pf, w, hh, o)) for o in ORI))
                ft = face_tab(pf, w, hh)
                faces.add(H(sorted(collections.Counter(ft.values()).items())))
            else:
                cls.append(None)
        r = dict(die=die, core=m, n_inst=len(L), n_types=len({k for k, _ in L}), n_outlines=len(outl),
                 outline=";".join("x".join(map(str, o)) for o in sorted(outl)),
                 n_pin_tables=len(tabs), n_pin_tables_mod_orient=len(set(cls)),
                 n_face_profiles=len(faces))
        rows_c.append(r)
    summary[die] = dict(types=len(T), parts=len(P["partitions"]), **{"lvl_" + k: len(v) for k, v in lv.items()},
                        cores=len(insts), core_insts=sum(len(v) for v in insts.values()),
                        core_pin_tables=sum(r["n_pin_tables"] for r in rows_c if r["die"] == die),
                        core_pin_tables_mod_orient=sum(r["n_pin_tables_mod_orient"] for r in rows_c if r["die"] == die))
os.makedirs(OUT, exist_ok=True)
for name, rows in (("types.csv", rows_t), ("cores.csv", rows_c)):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
for d, s in summary.items(): print(d, s)
