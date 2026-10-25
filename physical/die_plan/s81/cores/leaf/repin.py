#!/usr/bin/env python3
"""S81-CORES 10-24: leaf re-pin of the closed sub-leaf cores whose pin faces cannot face their partners in any leaf
placement (GEOM-REVIEW8 21:04 ot_s81sl_leaf FAIL, fix "ask the core owners for a re-pin"):
  vs: ve_r/ve_p (vs N) and ve_o (vs S) sit on opposite faces, and ve's own ports are on ve W (r, p) and E (a, o): for
      every ve position one of the ve<->vs ports faces away (cos -1).  New vs faces: N = all ve ports + the leaf-bus
      ports (s, e, g, fault), W = vq (u, um) + the leaf store extension (x_*), E = vsw (sw_*), S = rx lane (ra_*) + clk/rst.
  vq: xf (276 b to the leaf bus) sat on vq E, vq W carried both y (vn) and u (vs): new vq faces W = y (vn), E = u / um
      (vs), N = xf / k / sid / m / fault (leaf bus) + clk/rst.
Same module, same RTL, same port list and widths (read from the closed view's pin table); only the pin positions move.
Pins are spread evenly per face group on the kit tracks after the plan core offset [0.108, 0.012] (CORE-KS):
V layers (N/S faces) alternate M3 / M5, every second track; H layers (E/W faces) M4, every second track.  Pin shapes
follow the closed views (M3 0.018 x 0.038, M4 0.084 x 0.024, M5 0.024 x 0.084, on the outline edge).
Writes inputs/core_pins/<module>_lfp.json (plan pin table) and cores/leaf/lef/<module>_lfp.lef (stub abstract LEF:
pins + OBS M1-M7 over the core, for plan / G1 / leaf-kit placement until the re-pinned view closes).
usage (repo root): python3 physical/die_plan/s81/cores/leaf/repin.py [MODULE ...]   (default: all)"""
import json, os, re, sys
D = "physical/die_plan/s81"
OFF = (0.108, 0.012)
LAY = {"M3": (0.036, 0.009), "M4": (0.048, 0.024), "M5": (0.048, 0.024)}
EDGE = {"M3": 0.019, "M4": 0.042, "M5": 0.042}
RECT = {"M3": (0.018, 0.038), "M4": (0.084, 0.024), "M5": (0.024, 0.084)}   # (w, h) in x, y for an N/S or E/W pin
# face groups in face order: N/S low x -> high x, E/W low y -> high y
SPEC = {
    "ot_s81sl_vs": dict(size=(172.8, 172.8), faces=dict(
        N=["ve_rv", "ve_rc", "ve_rh", "ve_rk", "ve_rw", "ve_pv", "ve_pc", "ve_phh", "ve_pkk", "ve_pdd",
           "s_v", "s_d", "g_v", "g_c", "g_d", "e_v", "e_c", "e_d", "fault",
           "ve_fi", "ve_ov", "ve_oc", "ve_oy", "ve_av", "ve_ac", "ve_ah", "ve_aval", "ve_ag"],
        W=["x_rv", "x_ra", "x_qv", "x_qd", "x_wv", "x_wa", "x_wm", "x_wd", "u_v", "u_i", "u", "um_v", "um_q", "um_b", "um_i"],
        E=["sw_v", "sw_d", "sw_w", "sw_lim", "sw_vi", "sw_ri", "sw_fi"],
        S=["ra_v", "ra_x", "ra_vi", "ra_ri", "ra_fi"]),
        # S81/LEAFPLAN 10-24: clk / rst_n at the S-face pin-count middle (were the S-W corner; KITS eg_c FAIL class)
        move={"clk": "S", "rst_n": "S"}),
    "ot_s81sl_vq": dict(size=(172.8, 129.6), faces=dict(
        W=["y_v", "y_i", "y"],
        E=["u_v", "u_i", "u", "um_v", "um_q", "um_b", "um_i"],
        N=["k", "sid", "m_v", "m_q", "m_b", "m_i", "fault", "xf_v", "xf_s", "xf"],
        S=[]),
        move={"clk": "N", "rst_n": "N"}),
    # svc (S81-CORES): the score-exchange half row re-floorplanned from 216 x 216 to 138.24 x 164.16 so the 8 half rows
    # sit in the svc centre band between the 4 + 4 hcore rows (the exchange's hop geometry assumes the leaf cluster at the
    # slice centre: dsdv_svc_sx 'pins at the slice centre line'); faces kept (lanes face their svc face), order kept
    # C slices (S81/LEAFPLAN 10-24, S81/KITS r6 geom FAIL ot_s81sl_eg_c): the closed-view pins put clk + rst_n at the W-top
    # corner (0, 250), ~360 um from the far flops of the 33k-flop core, and the S face in 3 narrow clusters (peak 26.5
    # pins/um > 24.3 cap). Faces and face order kept, every face spread evenly over its length, clk / rst_n moved to the
    # S-face centre (the face of the data clusters; centre-fed clock / reset)
    "ot_s81sl_eg": dict(size=(259.2, 259.2), keep_faces=True, suffix="_c", dir="cores/eg/lef", move={"clk": "S", "rst_n": "S"},
                        src_lef="physical/ref_tile/s81sl_eg/views/ot_s81sl_eg/ot_s81sl_eg.lef"),
    # S81-KITS-C3 10-24 (S81/KITS request): eng E core: rst_n / ck sat at the W-bottom corner (0.1, 21.7 / 23.1) of the
    # 345.6 x 466.56 core; moved to the S-face middle (S = the data face: hx_res / hx_w to h0 / h1, 1220 of 2690
    # pins).  move_only: every other pin keeps its exact position (S hx_res / hx_w abut h0 / h1 N in_w / hit_res; a
    # keep_faces re-spread moved hx_w 160 um and hx_res up to 39.5 um); ck / rst_n take the free M3 tracks (the S face
    # is all M5) nearest the face middle.  The table is rewritten in place (inputs/core_pins/dsdv_eng_rr_e.json).
    "dsdv_eng_rr_e": dict(size=(345.6, 466.56), move_only=True, suffix="", dir="cores/eng/lef",
                          move={"ck": "S", "rst_n": "S"}, src_lef="physical/die_plan/s81/cores/eng/lef/dsdv_eng_rr_e.lef"),
    "dsdv_svc_sx_hrow": dict(size=(138.24, 164.16), keep_faces=True, suffix="_c",
                             src_lef="physical/ref_tile/dsdv_svc_sx_hrow/views/dsdv_svc_sx_hrow/dsdv_svc_sx_hrow.lef"),
}


def tracks(layer, lo, hi, vertical):
    p, o = LAY[layer]
    sh = OFF[0] if vertical else OFF[1]
    k0 = int((lo + sh - o) / p) + 1
    out = []
    while True:
        c = o + k0 * p - sh
        if c > hi:
            return out
        out.append(round(c, 4))
        k0 += 1


def build(mod, spec):
    src = json.load(open(os.path.join(D, "inputs/core_pins/%s.json" % mod)))
    if spec.get("move_only"):
        # only the moved scalar ports change: each goes to the free every-second track (either face layer, no same-layer
        # pin within 0.2 um) nearest the face middle; every other pin keeps its position
        W, H = spec["size"]
        keep = [p for p in src["pins"] if p["name"] not in spec["move"]]
        pins = [dict(p) for p in keep]
        for b, face in spec["move"].items():
            vert = face in "NS"
            mid = (W if vert else H) / 2.0
            e_ = {"N": lambda q: H - q["y"], "S": lambda q: q["y"], "E": lambda q: W - q["x"], "W": lambda q: q["x"]}[face]
            on = [q for q in pins if e_(q) < 0.2]
            best = None
            for L in (["M3", "M5"] if vert else ["M4"]):
                taken = [q["x"] if vert else q["y"] for q in on if q["layer"] == L]
                for c in tracks(L, 4.32, (W if vert else H) - 4.32, vert)[::2]:
                    if all(abs(c - u) > 0.2 for u in taken):
                        k = (abs(c - mid), L, c)
                        best = min(best, k) if best else k
            _, L, c = best
            e = EDGE[L]
            x, y = {"N": (c, H - e), "S": (c, e), "E": (W - e, c), "W": (e, c)}[face]
            pins.append(dict(name=b, layer=L, x=round(x, 4), y=round(y, 4)))
        if len(pins) != len(src["pins"]):
            raise SystemExit("%s: %d pins of %d" % (mod, len(pins), len(src["pins"])))
        pins.sort(key=lambda p: p["name"])
        return pins, src
    names = [p["name"] for p in src["pins"]]
    base = {}
    for n in names:
        base.setdefault(re.sub(r"\[\d+\]$", "", n), []).append(n)
    for b in base:
        base[b].sort(key=lambda n: int(re.search(r"\[(\d+)\]$", n).group(1)) if "[" in n else -1)
    if spec.get("keep_faces"):
        W0, H0 = spec["size"] if "move" in spec else (max(p["x"] for p in src["pins"]) + 0.042,
                                                       max(p["y"] for p in src["pins"]) + 0.019)
        fc = {}
        for p in src["pins"]:
            f = min([(p["x"], "W"), (W0 - p["x"], "E"), (p["y"], "S"), (H0 - p["y"], "N")])[1]
            b = re.sub(r"\[\d+\]$", "", p["name"])
            fc.setdefault(f, {}).setdefault(b, []).append(p["x"] if f in "NS" else p["y"])
        spec = dict(spec, faces={f: sorted(g, key=lambda b: sum(g[b]) / len(g[b])) for f, g in fc.items()})
    if spec.get("move"):
        spec = dict(spec, faces={f: list(g) for f, g in spec["faces"].items()})
        for b, f in spec["move"].items():
            # a port moved to face f, at the pin middle of that face (clock / reset centre-fed; splits a wide group)
            for g in spec["faces"].values():
                if b in g:
                    g.remove(b)
            spec["faces"].setdefault(f, []).append(b)
        spec["faces"] = {f: g for f, g in spec["faces"].items() if g}
    want = [b for f in spec["faces"].values() for b in f]
    miss, extra = set(base) - set(want), set(want) - set(base)
    if miss or extra:
        raise SystemExit("%s: port mismatch missing %s extra %s" % (mod, sorted(miss), sorted(extra)))
    W, H = spec["size"]
    pins = []
    for face, groups in spec["faces"].items():
        mid = [b for b in groups if b in spec.get("move", {})]
        seq = [n for b in groups if b not in mid for n in base[b]]
        k = len(seq) // 2
        seq[k:k] = [n for b in mid for n in base[b]]
        if not seq:
            continue
        vert = face in "NS"
        span = (4.32, (W if vert else H) - 4.32)
        if vert:
            lay = ["M3", "M5"]
            slots = {L: tracks(L, *span, True)[::2] for L in lay}
        else:
            lay = ["M4"]
            slots = {"M4": tracks("M4", *span, False)[::2]}
        n = len(seq)
        used = {L: set() for L in lay}
        for i, nm in enumerate(seq):
            L = lay[i % len(lay)]
            sl = slots[L]
            want_c = span[0] + (span[1] - span[0]) * (i + 0.5) / n
            j = min(range(len(sl)), key=lambda k: (abs(sl[k] - want_c) if k not in used[L] else 1e9))
            if j in used[L]:
                raise SystemExit("%s: face %s out of tracks" % (mod, face))
            used[L].add(j)
            c = sl[j]
            e = EDGE[L]
            x, y = {"N": (c, H - e), "S": (c, e), "E": (W - e, c), "W": (e, c)}[face]
            pins.append(dict(name=nm, layer=L, x=round(x, 4), y=round(y, 4)))
    if len(pins) != len(names):
        raise SystemExit("%s: %d pins placed of %d" % (mod, len(pins), len(names)))
    pins.sort(key=lambda p: p["name"])
    return pins, src


def lef(mod, W, H, pins, dirs):
    o = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;", "MACRO %s" % mod, "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", "  FOREIGN %s 0 0 ;" % mod, "  SIZE %.3f BY %.3f ;" % (W, H), "  SYMMETRY X Y ;"]
    for p in pins:
        w, h = RECT[p["layer"]]
        if p["layer"] == "M4":
            pass
        o += ["  PIN %s" % p["name"], "    DIRECTION %s ;" % dirs.get(p["name"], "INOUT"), "    USE SIGNAL ;",
              "    PORT", "      LAYER %s ;" % p["layer"],
              "        RECT %.4f %.4f %.4f %.4f ;" % (p["x"] - w / 2, p["y"] - h / 2, p["x"] + w / 2, p["y"] + h / 2),
              "    END", "  END %s" % p["name"]]
    o += ["  OBS"] + ["    LAYER %s ;\n      RECT 0.5 0.5 %.3f %.3f ;" % (L, W - 0.5, H - 0.5)
                     for L in ("M1", "M2", "M3", "M4", "M5", "M6", "M7")] + ["  END", "END %s" % mod, "END LIBRARY", ""]
    return "\n".join(o)


def lef_dirs(path):
    d, cur = {}, None
    for ln in open(path):
        t = ln.split()
        if t[:1] == ["PIN"]:
            cur = t[1]
        elif t[:1] == ["DIRECTION"] and cur:
            d[cur] = t[1]
    return d


def main():
    only = sys.argv[1:]
    for mod, spec in SPEC.items():
        if only and mod not in only:
            continue
        pins, src = build(mod, spec)
        W, H = spec["size"]
        if spec.get("move_only"):
            # move_only: patch the source table / LEF in place -- only the moved ports' entries and PIN blocks change
            # (repin's own LEF writer redraws every pin with the repin shapes and its OBS set)
            import hashlib
            mv = {q["name"]: q for q in pins if q["name"] in spec["move"]}
            lp = src["lef"]
            lt = open(lp).read()
            for nm, q in mv.items():
                w, h = RECT[q["layer"]]
                blk = re.search(r"(?ms)^  PIN %s\s*$.*?^  END %s\s*$" % (re.escape(nm), re.escape(nm)), lt)
                d = re.search(r"DIRECTION (\S+)", blk.group(0)).group(1)
                u = (re.search(r"USE (\S+)", blk.group(0)) or re.search("(SIGNAL)", "SIGNAL")).group(1)
                new = "\n".join(["  PIN %s" % nm, "    DIRECTION %s ;" % d, "    USE %s ;" % u, "    PORT",
                                 "      LAYER %s ;" % q["layer"],
                                 "        RECT %.4f %.4f %.4f %.4f ;" % (q["x"] - w / 2, q["y"] - h / 2, q["x"] + w / 2, q["y"] + h / 2),
                                 "    END", "  END %s" % nm])
                lt = lt[:blk.start()] + new + lt[blk.end():]
            open(lp, "w").write(lt)
            src["pins"] = [mv.get(q["name"], q) for q in src["pins"]]
            src["pinhash"] = hashlib.sha256(json.dumps(src["pins"], sort_keys=True).encode()).hexdigest()[:12]
            note = "; S81-KITS-C3 10-24 repin.py move_only: %s moved to face middle" % spec["move"]
            if note not in src["source"]:
                src["source"] += note
            jp = os.path.join(D, "inputs/core_pins/%s%s.json" % (mod, spec.get("suffix", "_lfp")))
            json.dump(src, open(jp, "w"), indent=0)
            print("wrote (move_only)", jp, lp, {k: (v["layer"], v["x"], v["y"]) for k, v in mv.items()})
            continue
        sfx = spec.get("suffix", "_lfp")
        if spec.get("src_lef"):
            dirs = lef_dirs(spec["src_lef"])
        else:
            rt = {"ot_s81sl_vs": "s81sl_vs", "ot_s81sl_vq": "s81sl_vq"}[mod]
            dirs = lef_dirs("physical/ref_tile/%s/views/%s/%s.lef" % (rt, mod, mod))
        lp = os.path.join(D, spec.get("dir", "cores/%s/lef" % ("svc" if sfx == "_c" else "leaf")), "%s%s.lef" % (mod, sfx))
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        # the source pin table already carries the OWNER DECISION 8 drops / renames (src["const_rename"] = renames applied):
        # the new table and LEF continue from that count, so drop() below applies only renames appended since
        done = int(src.get("const_rename") or 0)
        open(lp, "w").write(("# OT const_rename %d: inherited from the source pin table\n" % done if done else "") +
                            lef(mod, W, H, pins, dirs))
        import hashlib
        j = dict(module=mod, lef=lp, source="S81-CORES 10-24 re-pin (cores/leaf/repin.py) of %s: same ports, "
                 "%gx%g, faces %s" % (src["lef"], W, H, {f: len(g) for f, g in spec["faces"].items()}
                                       if "faces" in spec else "kept"),
                 pinhash=hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12], pins=pins)
        if done:
            j["const_rename"] = done
        sys.path.insert(0, D)
        import drop_const_pins            # OWNER DECISION 8: constant pins are not plan pins
        drop_const_pins.drop(j, lp)
        jp = os.path.join(D, "inputs/core_pins/%s%s.json" % (mod, sfx))
        json.dump(j, open(jp, "w"), indent=0)
        print("wrote", jp, lp, len(pins))


if __name__ == "__main__":
    main()
