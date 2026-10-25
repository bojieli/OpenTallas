#!/usr/bin/env python3
"""B2p = the HBM one-path plan delta (PATH-HBM, COORD ruling 2026-10-25 10:04): derived from the master-ID plan
(B2p_base_ids = B2o@ecfb97d718 + tools/hbm_b2/master_ids.py, die_plan sha256 4768c4fa...) by

    python3 physical/die_plan/hbm_arch/path_hbm_b2p.py --src B2p_base_ids --out B2p --chain DIR [--hubnw MODULE.py]

Step A (root partition, TKM chain; GEOM [PATH-HBM-TKMCHAIN] PASS-COND 08:20 + lattice snap 08:54):
  A1 u_tkm_SW_root + 32 tiles move to the reviewed 4-column snake (DIR/tkm_chain_placement.json, R0 up / MX down);
     tiles 0..30 = ONE common master ot_hgi_coll_tkm_tp192_tile_core__idpin (strap tile_tid at the parent, owner B),
     tile31 = the terminal master (__terminal_idpin, up_in 0 / ovf open inside the master); pin files = the common
     chain templates (DIR/*_repin.json: tile S clr/conv_o/ins/up_out, N clr_o/conv/ovf/up_in at the same x; root N
     tile0 pins copy the tile S x bit for bit).
  A2 internal stations: the 907 B2o 'R3-INTERNAL' stations on tile_clk (a clock treated as data: 7ff73a8320) are
     dropped; chain buses are face-to-face (0 stations, worst hop 345.6 um); conv = ONE registered 1-bit relay
     root -> tile31 (DIR/tkm_conv_tree.json, stations <= 400 um, TOKEN CB21); clr is systolic in-tile (1 flop/hop).
  A3 core_conns: tile_clk removed from the data graph; the chain (ovf->ins, up_out->up_in, clr_o->clr, conv_o->conv)
     and root<->tile0 / root conv -> tile31 written explicitly.
  A4 clock: one core tap per TKM core at its tile_clk pin (budget 250 ps = kit common latency; kit CTS pending) and the
     P7 CTS hop table (every launch/capture core pair of the chain: tap distance, column/turn, CPPR divergence).
  A5 soft leaves that overlap the snake (+8.64 halo) move to the nearest free lattice site.
Step B (NW hub, optional --hubnw): q_hub_nw (q3 collective pieces facing root) via MODULE.apply(plan, out_dir).
"""
import argparse, copy, hashlib, importlib.util, json, math, re, shutil, sys
from pathlib import Path

LAT = 8.64
HALO = 8.64
W, H = 319.68, 345.6
TILE_M = "ot_hgi_coll_tkm_tp192_tile_core__idpin"
TERM_M = "ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin"
ROOT_M = "ot_hgi_coll_tkm_m_tp192__root"
TILE_PINS = f"cores/{TILE_M}__chain.json"
TERM_PINS = f"cores/{TERM_M}__chain.json"
ROOT_PINS = f"cores/{ROOT_M}__chain.json"
BUDGET_PS = 250.0
NB = 344


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def xform(pt, origin, orient, w=W, h=H):
    x, y = pt
    if orient == "MX":          # mirror about the x axis: y flips
        y = h - y
    elif orient == "MY":
        x = w - x
    elif orient == "R180":
        x, y = w - x, h - y
    return [round(origin[0] + x, 3), round(origin[1] + y, 3)]


def overlap(a, b, g=0.0):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw + g - 1e-6 and bx < ax + aw + g - 1e-6 and ay < by + bh + g - 1e-6 and by < ay + ah + g - 1e-6


def stations_along(path, step=400.0):
    """registered relay stations every <= step um along a rectilinear path (first/last = the core pins)."""
    segs, L = [], 0.0
    for a, b in zip(path, path[1:]):
        d = abs(b[0] - a[0]) + abs(b[1] - a[1])
        segs.append((a, b, d))
        L += d
    n = math.ceil(L / step) - 1
    pitch = L / (n + 1)
    regs, k, acc = [], 1, 0.0
    for a, b, d in segs:
        while k <= n and acc + d >= k * pitch - 1e-9:
            t = (k * pitch - acc) / d if d else 0
            regs.append([round(a[0] + (b[0] - a[0]) * t, 3), round(a[1] + (b[1] - a[1]) * t, 3)])
            k += 1
        acc += d
    return regs, L, pitch


def step_a(plan, out, chain, log):
    T = plan["partition_types"]["root"]
    pl = json.load(open(chain / "tkm_chain_placement.json"))
    conv = json.load(open(chain / "tkm_conv_tree.json"))
    # A1 pin files
    (out / "cores").mkdir(exist_ok=True)
    srcs = {TILE_PINS: chain / f"{TILE_M}__repin.json", TERM_PINS: chain / f"{TERM_M}__repin.json",
            ROOT_PINS: chain / f"{ROOT_M}__repin.json"}
    pins = {}
    for dst, src in srcs.items():
        shutil.copyfile(src, out / dst)
        pins[dst] = {q["name"]: q for q in json.load(open(src))}
        log["pin_files"][dst] = dict(src=str(src), sha256=sha(out / dst), pins=len(pins[dst]))
    place = {pl["root"]["inst"]: pl["root"]}
    place.update({t["inst"]: t for t in pl["tiles"]})
    HC = {c["inst"]: c for c in T["hard_cores"]}
    for inst, q in place.items():
        c = HC[inst]
        old = (list(c["origin_um"]), c.get("orient", "R0"), c["module"])
        c["origin_um"] = [round(q["origin_um"][0], 3), round(q["origin_um"][1], 3)]
        if q["orient"] == "R0":
            c.pop("orient", None)
        else:
            c["orient"] = q["orient"]
        if inst == "u_tkm_SW_root":
            c["pins_file"] = ROOT_PINS
        else:
            k = int(inst.rsplit("tile", 1)[1])
            c["module"] = TERM_M if k == 31 else TILE_M
            c["pins_file"] = TERM_PINS if k == 31 else TILE_PINS
            ps = c.get("parent_id_straps", {})
            if ps.get("tile_tid", {}).get("value") != k:
                raise SystemExit(f"{inst}: parent_id_straps tile_tid != {k}: {ps}")
        c["note"] = (c.get("note", "") + f" | B2p PATH-HBM snake: {old[0]}/{old[1]} -> {c['origin_um']}/{q['orient']}").strip(" |")
        log["moved"].append(dict(inst=inst, frm=old[0], to=c["origin_um"], orient=q["orient"], module=c["module"]))
    # snake legality: no overlap among all hard cores (+halo)
    rects = {c["inst"]: (c["origin_um"][0], c["origin_um"][1], c["outline_um"][0], c["outline_um"][1]) for c in T["hard_cores"]}
    bad = []
    names = sorted(rects)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            tka, tkb = a.startswith("u_tkm_SW"), b.startswith("u_tkm_SW")
            if (tka != tkb) and overlap(rects[a], rects[b], HALO - 1e-3):
                bad.append((a, b))      # (non-TKM pairs keep their B2o spacing; not this delta's scope)
            elif a.startswith("u_tkm_SW") and b.startswith("u_tkm_SW") and overlap(rects[a], rects[b], 0.0):
                bad.append((a, b))
    ow, oh = T["outline_um"]
    for n, r in rects.items():
        if r[0] < -1e-6 or r[1] < -1e-6 or r[0] + r[2] > ow + 1e-6 or r[1] + r[3] > oh + 1e-6:
            bad.append((n, "outline"))
    if bad:
        raise SystemExit(f"A1 overlaps: {bad[:10]}")
    # A5 soft leaves overlapping the TKM cores
    tk = [r for n, r in rects.items() if n.startswith("u_tkm_SW")]
    hard = list(rects.values())
    for c in T["contents"]:
        if c["inst"] == "u_tkm_SW" or "origin_um" not in c:
            continue
        r = (c["origin_um"][0], c["origin_um"][1], c["outline_um"][0], c["outline_um"][1])
        if not any(overlap(r, t, HALO) for t in tk):
            continue
        best = None
        cw, ch = c["outline_um"]
        softs = [(d["origin_um"][0], d["origin_um"][1], d["outline_um"][0], d["outline_um"][1]) for d in T["contents"]
                 if d is not c and d["inst"] not in ("u_tkm_SW", "u_hc_eng") and "origin_um" in d]
        for i in range(int(ow / LAT)):
            for j in range(int(oh / LAT)):
                x, y = i * LAT, j * LAT
                if x + cw > ow or y + ch > oh:
                    continue
                q = (x, y, cw, ch)
                if any(overlap(q, h, HALO) for h in hard) or any(overlap(q, s, 0) for s in softs):
                    continue
                d = abs(x - r[0]) + abs(y - r[1])
                if best is None or d < best[0]:
                    best = (d, [round(x, 3), round(y, 3)])
        if best is None:
            raise SystemExit(f"A5 no site for {c['inst']}")
        log["soft_moved"].append(dict(inst=c["inst"], frm=c["origin_um"], to=best[1], dist_um=round(best[0], 2)))
        c["origin_um"] = best[1]
    # A2 stations
    before = len(T["internal_stations"])
    T["internal_stations"] = [s for s in T["internal_stations"] if not s["conn"].startswith("u_tkm_SW_") or
                              not any(k in s["conn"] for k in (".tile_clk", "|u_tkm_SW_"))]
    dropped = before - len(T["internal_stations"])
    path = conv["path"]
    regs, L, pitch = stations_along(path, 400.0)
    rootc = HC["u_tkm_SW_root"]
    t31 = HC["u_tkm_SW_tile31"]
    src = xform((pins[ROOT_PINS]["x_u_u_g_tiles_0_e86_u_tile_conv"]["x"], pins[ROOT_PINS]["x_u_u_g_tiles_0_e86_u_tile_conv"]["y"]),
                rootc["origin_um"], rootc.get("orient", "R0"))
    dst = xform((pins[TERM_PINS]["tile_conv"]["x"], pins[TERM_PINS]["tile_conv"]["y"]), t31["origin_um"], t31.get("orient", "R0"))
    T["internal_stations"].append(dict(
        conn="u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv|u_tkm_SW_tile31", from_um=src, to_um=dst, regs_um=regs, bits=1,
        launch="u_tkm_SW_root.x_u_u_g_tiles_0_e86_u_tile_conv", capture="u_tkm_SW_tile31.tile_conv",
        note=f"B2p PATH-HBM conv relay root -> tile31 (TOKEN CB21): {L:.1f} um, {len(regs)} stations, pitch {pitch:.1f} um "
             f"<= 400 on halo-free sites (E channel / top band / x349.92 corridor)"))
    hops = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip([src] + regs, regs + [dst])]
    log["stations"] = dict(dropped_tile_clk=dropped, conv_stations=len(regs), conv_path_um=round(L, 1),
                           conv_worst_hop_um=round(max(hops), 1), conv_src=src, conv_dst=dst, conv_tree_src=path[0], conv_tree_dst=path[-1])
    hard_r = [r for n, r in rects.items()]
    inside = [s for s in regs if any(r[0] < s[0] < r[0] + r[2] and r[1] < s[1] < r[1] + r[3] for r in hard_r)]
    if inside:
        raise SystemExit(f"A2 conv stations inside hard cores: {inside}")
    # A3 core_conns
    ccp = out / "core_conns.json"
    CC = json.load(open(ccp))
    R = CC["root"]
    for inst in list(R):
        if inst.startswith("u_tkm_SW_"):
            R[inst].pop("tile_clk", None)
    for k in range(32):
        a = R.setdefault(f"u_tkm_SW_tile{k}", {})
        if k < 31:
            a["tile_ovf_b"] = [f"core:u_tkm_SW_tile{k + 1}"]
            a["tile_ovf_v"] = [f"core:u_tkm_SW_tile{k + 1}"]
            a["tile_clr_o"] = [f"core:u_tkm_SW_tile{k + 1}"]
            a["tile_up_in"] = [f"core:u_tkm_SW_tile{k + 1}"]
        else:
            a["tile_clr_o"] = []
        prev = "core:u_tkm_SW_root" if k == 0 else f"core:u_tkm_SW_tile{k - 1}"
        a["tile_up_out"] = [prev]
        a["tile_ins_b"] = [prev]
        a["tile_ins_v"] = [prev]
        a["tile_clr"] = [prev]                     # systolic clr: root -> tile0 -> ... -> tile31
        a["tile_conv"] = ["core:u_tkm_SW_root"] if k == 31 else [f"core:u_tkm_SW_tile{k + 1}"]   # relay -> tile31, then up
        a["tile_conv_o"] = [] if k == 0 else [f"core:u_tkm_SW_tile{k - 1}"]   # conv enters at tile31 (relay), shifts up to tile0
    r0 = R.setdefault("u_tkm_SW_root", {})
    r0["x_u_u_g_tiles_0_e86_u_tile_conv"] = ["core:u_tkm_SW_tile31"]
    json.dump(CC, open(ccp, "w"), indent=1)
    # A4 clock taps + hop table
    taps = T["clock"].setdefault("taps", [])
    taps[:] = [t for t in taps if not t["name"].startswith("u_tkm_SW_")]
    tapxy = {}
    for inst in sorted(place, key=lambda n: (n != "u_tkm_SW_root", int(n.rsplit("tile", 1)[1]) if "tile" in n else -1)):
        c = HC[inst]
        pf = ROOT_PINS if inst == "u_tkm_SW_root" else (TERM_PINS if c["module"] == TERM_M else TILE_PINS)
        clk = pins[pf]["clk" if inst == "u_tkm_SW_root" and "clk" in pins[pf] else "tile_clk"]
        xy = xform((clk["x"], clk["y"]), c["origin_um"], c.get("orient", "R0"))
        tapxy[inst] = xy
        taps.append(dict(name=inst, kind="core", xy=xy, insertion_ps=BUDGET_PS, budget_owner=c["module"],
                         note="B2p PATH-HBM: TKM chain core tap at the core clock pin; insertion = kit common_latency budget "
                              "(core kit CTS pending, measured value replaces it)"))
    ptap = T["clock"]["tap_um"]
    col = {x: i for i, x in enumerate(sorted({round(HC[n]["origin_um"][0], 2) for n in place}))}
    pairs = [("u_tkm_SW_root", "u_tkm_SW_tile0")] + [(f"u_tkm_SW_tile{k}", f"u_tkm_SW_tile{k + 1}") for k in range(31)]
    table = []
    for a, b in pairs:
        ca, cb = HC[a], HC[b]
        same = round(ca["origin_um"][0], 2) == round(cb["origin_um"][0], 2)
        da = abs(tapxy[a][0] - ptap[0]) + abs(tapxy[a][1] - ptap[1])
        db = abs(tapxy[b][0] - ptap[0]) + abs(tapxy[b][1] - ptap[1])
        table.append(dict(launch=a, capture=b, kind="column" if same else "turn",
                          col=[col[round(ca["origin_um"][0], 2)], col[round(cb["origin_um"][0], 2)]],
                          tap_launch=tapxy[a], tap_capture=tapxy[b],
                          tap_dist_um=round(abs(tapxy[a][0] - tapxy[b][0]) + abs(tapxy[a][1] - tapxy[b][1]), 2),
                          root_dist_um=[round(da, 1), round(db, 1)], root_dist_delta_um=round(db - da, 1),
                          data_hop_um=345.6 if same else None, both_dirs=True))
    log["cts_hop_table"] = dict(partition_tap_um=ptap, pairs=table,
                                worst_tap_dist_um=max(t["tap_dist_um"] for t in table),
                                worst_root_delta_um=max(abs(t["root_dist_delta_um"]) for t in table),
                                rule="related-pair skew <= 20 ps after CPPR (decision 5); each chain hop is face flop -> face flop in "
                                     "BOTH directions (ovf/ins/clr down, up_out/conv up), so a pair needs |skew| inside the hold "
                                     "window either way: balance per pair, not just per sink")
    return T


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--hubnw")
    a = ap.parse_args(argv)
    src, out, chain = Path(a.src), Path(a.out), Path(a.chain)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    plan = json.load(open(out / "die_plan.json"))
    log = dict(src=str(src), src_plan_sha256=sha(src / "die_plan.json"), pin_files={}, moved=[], soft_moved=[])
    step_a(plan, out, chain, log)
    if a.hubnw:
        spec = importlib.util.spec_from_file_location("hubnw", a.hubnw)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        log["hubnw"] = m.apply(plan, out)
    plan["note"] = (plan.get("note", "") + " | B2p: PATH-HBM one-path delta (TKM snake, conv relay, chain taps"
                    + (", q_hub_nw" if a.hubnw else "") + ")")
    json.dump(plan, open(out / "die_plan.json", "w"), indent=1)
    log["out_plan_sha256"] = sha(out / "die_plan.json")
    json.dump(log, open(out / "b2p_report.json", "w"), indent=1)
    print(json.dumps(dict(moved=len(log["moved"]), soft_moved=log["soft_moved"], stations=log["stations"],
                          worst_tap_dist=log["cts_hop_table"]["worst_tap_dist_um"],
                          worst_root_delta=log["cts_hop_table"]["worst_root_delta_um"], plan=log["out_plan_sha256"][:8])))


if __name__ == "__main__":
    main()
