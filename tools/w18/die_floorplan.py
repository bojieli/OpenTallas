#!/usr/bin/env python3
"""W18: V4.1 ROM layer-die floorplan built from REAL element abstracts (floorplan -> element -> replicate).

W1's pack (W10 re-fit mode) reserves the ROM field as [ROM | MAC strip | ROM] pair slots at a 485.136 x
120.96 um pitch, with the MAC strip as soft logic.  The hardened element pair (W10 p5, routed) is a hard
macro of its own size, with its 734 signal pins on its bottom (south) edge and its power on M6.  This tool
replicates THAT abstract to the model's count (the pack's used pair rows: 7,102) in the same die, around
the same hub, HBM PHY/service bands, link strips and vertical HBM corridors, and groups the pairs into
clusters: a cluster is one column segment of up to ``rows`` pairs between two horizontal spine corridors,
each pair row with a pin channel under it (the pair's pins face south).

Everything that is not the pair (hub partitions, HBM service bands, SerDes, UCIe) keeps the pack's rectangle
and is a LABELLED PLACEHOLDER until its hardened abstract lands (W11 hub elements, W15 link ports).

    python3 tools/w18/die_floorplan.py --pack results/floorplan/v41_pack_refit_w18_e8p5.json \
        --pair-lef <ot_v41_rom_elem_q.lef> --output results/floorplan/v41_w18_die_floorplan.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import v41_floorplan_pack as PK  # noqa: E402
from chip_assembly import floorplans as FP  # noqa: E402

X_STEP, Y_STEP = PK.X_STEP, PK.Y_STEP
PERIOD_PS, UNC_PS = 920.0, 60.0
# W1/W10 model crossings to compare with (results/floorplan pack latency_crossings, root's 16/22/16)
MODEL_CYCLES = {"vm_to_farthest_rom": 16, "coll_to_serdes": 22, "coll_to_ucie": 16}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def snap_up(v, s):
    return round(math.ceil(v / s - 1e-9) * s, 6)


def snap_dn(v, s):
    return round(math.floor(v / s + 1e-9) * s, 6)


def lef_macro(path: Path) -> dict:
    t = Path(path).read_text()
    name = re.search(r"^MACRO (\S+)", t, re.M).group(1)
    w, h = map(float, re.search(r"SIZE ([0-9.]+) BY ([0-9.]+)", t).groups())
    pins = {}
    for m in re.finditer(r"  PIN (\S+)\n(.*?)  END \1\n", t, re.S):
        body = m.group(2)
        use = re.search(r"USE (\w+)", body)
        rects = [(l, tuple(map(float, r.split()))) for l, rr in
                 re.findall(r"LAYER (\S+) ;\n((?:\s+RECT [^\n]+\n)+)", body)
                 for r in re.findall(r"RECT\s+([-0-9. ]+?)\s*;", rr)]
        pins[m.group(1)] = dict(use=use.group(1) if use else "SIGNAL", rects=rects)
    sig = [p for p in pins.values() if p["use"] not in ("POWER", "GROUND")]
    edges = {"S": 0, "N": 0, "W": 0, "E": 0}
    for p in sig:
        _, (x0, y0, x1, y1) = p["rects"][0]
        if y0 <= 0.2:
            edges["S"] += 1
        elif y1 >= h - 0.2:
            edges["N"] += 1
        elif x0 <= 0.2:
            edges["W"] += 1
        else:
            edges["E"] += 1
    pw_layers = sorted({l for p in pins.values() if p["use"] in ("POWER", "GROUND") for l, _ in p["rects"]})
    return dict(name=name, w=w, h=h, signal_pins=len(sig), pin_edges=edges, power_layers=pw_layers,
                obs_layers=sorted(set(re.findall(r"LAYER (M\d) ;", t.split("  OBS")[-1])) if "  OBS" in t else []))


def plan(pack_rec: dict, pair: dict, rows: int, row_ch: float, col_gap: float, spine_h: float,
         pairs_needed: int | None = None, bf16: dict | None = None, bf16_pairs: int = 0) -> dict:
    g = pack_rec["geometry"]
    die_w, die_h = g["die_w_um"], g["die_h_um"]
    cx0, cy0, cx1, cy1 = g["core"]
    soft = {s[0]: dict(x=s[2], y=s[3], w=s[4], h=s[5], kind=s[1]) for s in pack_rec["soft_regions"]}
    hub = g["hub"]
    halo = g["hub_halo_um"]
    chans = {c[0]: dict(kind=c[1], x=c[2], y=c[3], w=c[4], h=c[5]) for c in pack_rec["channel_rects"]}
    vcorr = [c for c in chans.values() if c["kind"] == "vertical_hbm_corridor"]
    blockers = [(hub[0] - halo, hub[1] - halo, hub[2] + 2 * halo, hub[3] + 2 * halo)] + \
               [(c["x"], c["y"], c["w"], c["h"]) for c in vcorr]
    need = pairs_needed or pack_rec["capacity"]["used_pair_rows"]
    kinds = [pair] + ([bf16] if bf16 else [])
    two_sided = any(k["pin_edges"]["N"] and k["pin_edges"]["S"] for k in kinds)
    # per kind: the column width (pair origins on the joint grid, pins on track) and the row pitch (one pair +
    # its pin channel; with pins on both N and S edges adjacent rows share the channel between them and the
    # band gets one more channel on top).  BF16 column pairs may be wider and taller than the q pair.
    geo = {}
    for kn, k in (("q", pair), ("bf16", bf16)):
        if k:
            w_ = snap_up(k["w"], X_STEP)
            geo[kn] = dict(w=w_, rp=snap_up(k["h"] + row_ch, Y_STEP), cp=snap_up(w_ + col_gap, X_STEP))
    cl_w, row_pitch, col_pitch = geo["q"]["w"], geo["q"]["rp"], geo["q"]["cp"]
    band_h = rows * row_pitch
    bands = []
    y = cy0
    top_ch = snap_up(row_ch, Y_STEP) if two_sided else 0.0
    while y + row_pitch + top_ch <= cy1 + 1e-6:
        n = min(rows, int((cy1 - y - top_ch + 1e-6) // row_pitch))
        bands.append((y, n))
        y = snap_up(y + n * row_pitch + top_ch + spine_h, Y_STEP)
    spines = [snap_up(b + n * row_pitch + top_ch, Y_STEP) for b, n in bands[:-1]]

    def clear(x, y, w, h):
        return all(not (x < bx + bw and bx < x + w and y < by + bh and by < y + h) for bx, by, bw, bh in blockers)

    vm = soft["HUB_VM"]
    hx, hy = vm["x"] + vm["w"] / 2, vm["y"] + vm["h"] / 2

    def layout(seq):
        """seq: list of column kinds west to east; returns the clusters (column segments between spines)."""
        span = sum(geo[k]["cp"] for k in seq) - col_gap
        xc = snap_dn(cx0 + ((cx1 - cx0) - span) / 2, X_STEP)
        out = []
        for c, kn in enumerate(seq):
            gk = geo[kn]
            for b, (yb, n) in enumerate(bands):
                nr = int((n * row_pitch + 1e-6) // gk["rp"])
                segs, cur = [], []
                for r in range(nr):
                    if clear(xc, yb + r * gk["rp"], gk["w"], gk["rp"]):
                        cur.append(r)
                    elif cur:
                        segs.append(cur)
                        cur = []
                if cur:
                    segs.append(cur)
                for s in segs:
                    y0c = yb + s[0] * gk["rp"]
                    cl = dict(col=c, band=b, x=round(xc, 3), y=round(y0c, 3), w=gk["w"], h=round(len(s) * gk["rp"], 3),
                              rows=len(s), row_pitch_um=gk["rp"], kind=kn)
                    cl["dist_um"] = round(abs(cl["x"] + cl["w"] / 2 - hx) + abs(cl["y"] + cl["h"] / 2 - hy), 1)
                    out.append(cl)
            xc += gk["cp"]
        return out

    ncols = int((cx1 - cx0 + col_gap) // col_pitch)
    seq = ["q"] * ncols
    clusters = layout(seq)
    bf16_cols = []
    if bf16 and bf16_pairs:
        # dedicated BF16 COLUMNS (root, 2026-09-30): whole columns, spread evenly over the columns ordered by
        # their distance from VM (so the BF16 slots see the same distance mix as the q slots); a BF16 column
        # takes the place of ceil(cp_bf / cp_q) q columns
        take = math.ceil(geo["bf16"]["cp"] / col_pitch - 1e-9)
        dist = {}
        for cl in clusters:
            dist[cl["col"]] = min(dist.get(cl["col"], 1e18), cl["dist_um"])
        order = sorted(dist, key=lambda c: dist[c])
        for k in range(1, ncols // take + 1):
            step = len(order) / k
            pick = sorted({order[int(i * step)] for i in range(k)})
            s2, c = [], 0
            while c < ncols:
                if c in pick and c + take <= ncols:
                    s2.append("bf16")
                    c += take
                else:
                    s2.append("q")
                    c += 1
            # the BF16 columns replace q columns, so the row stays inside the core
            while sum(geo[x]["cp"] for x in s2) - col_gap > cx1 - cx0 + 1e-6:
                i = max(i for i, x in enumerate(s2) if x == "q")
                s2.pop(i)
            cand = layout(s2)
            if sum(cl["rows"] for cl in cand if cl["kind"] == "bf16") >= bf16_pairs:
                break
        seq, clusters = s2, cand
        bf16_cols = [i for i, x in enumerate(seq) if x == "bf16"]
    clusters.sort(key=lambda c: (c["dist_um"], c["x"], c["y"]))
    used = []
    left = {"q": need - bf16_pairs, "bf16": bf16_pairs}
    for cl in clusters:
        if left[cl["kind"]] <= 0:
            continue
        take = min(left[cl["kind"]], cl["rows"])
        u = dict(cl, used_rows=take, name=f"cl_c{cl['col']}_b{cl['band']}_y{int(cl['y'])}")
        used.append(u)
        left[cl["kind"]] -= take
    short = {k: max(0, v) for k, v in left.items()}
    left = sum(short.values())
    cap = sum(c["rows"] for c in clusters)
    # crossings with the real cluster extents (worst corner of the farthest used cluster from VM)
    wm = FP.wire_delay_model()
    reach = (PERIOD_PS - UNC_PS - wm["overhead_ps"]) / wm["ps_per_um"]

    def cyc(L):
        return math.ceil(L / reach)

    far = max(used, key=lambda c: max(abs(xx - hx) + abs(yy - hy) for xx in (c["x"], c["x"] + c["w"])
                                      for yy in (c["y"], c["y"] + c["h"])))
    far_L = max(abs(xx - hx) + abs(yy - hy) for xx in (far["x"], far["x"] + far["w"])
                for yy in (far["y"], far["y"] + far["h"]))
    return dict(
        die=dict(w_um=die_w, h_um=die_h, core=g["core"]),
        bf16=dict(bf16, pairs=bf16_pairs, columns=bf16_cols, pitch_um=[geo["bf16"]["cp"], geo["bf16"]["rp"]],
                  slots=sum(c["rows"] for c in clusters if c["kind"] == "bf16")) if bf16 else None,
        pin_channels="shared between rows, one extra per band (pins on N and S)" if two_sided else "south of each row",
        pair=dict(pair, pitch_um=[col_pitch, row_pitch],
                  pack_pitch_um=[g["pair_pitch_um"], g["rom_v_pitch_um"]],
                  pitch_vs_pack=[round(col_pitch / g["pair_pitch_um"], 4), round(row_pitch / g["rom_v_pitch_um"], 4)]),
        cluster_rule=dict(rows=rows, row_channel_um=row_ch, col_gap_um=col_gap, spine_h_um=spine_h,
                          row_pitch_um=row_pitch, col_pitch_um=col_pitch, columns=len(seq), bands=len(bands),
                          column_kinds="".join("B" if k == "bf16" else "q" for k in seq)),
        capacity=dict(pairs_needed=need, pair_slots=cap, closes=left <= 0, short=max(0, left), short_by_kind=short,
                      clusters_used=len(used), clusters_total=len(clusters),
                      full_clusters_used=sum(1 for c in used if c["used_rows"] == rows)),
        clusters=used, spines_y=spines,
        hub=dict(rect=hub, parts={k: v for k, v in soft.items() if k.startswith("HUB_")}),
        service={k: v for k, v in soft.items() if k.startswith("HBM_SERVICE")},
        vcorr=vcorr,
        crossings=dict(reach_um=round(reach, 1), wire_model=wm,
                       vm_to_farthest_cluster=dict(L_um=round(far_L, 1), cycles=cyc(far_L), cluster=far["name"],
                                                   model_cycles=MODEL_CYCLES["vm_to_farthest_rom"])),
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pack", type=Path, required=True, help="W10 re-fit pack record (tools/w18/pack.py)")
    ap.add_argument("--pair-lef", type=Path, required=True)
    ap.add_argument("--rows", type=int, default=16)
    ap.add_argument("--row-channel-um", type=float, default=8.64)
    ap.add_argument("--col-gap-um", type=float, default=8.64)
    ap.add_argument("--spine-um", type=float, default=PK.SPINE_H)
    ap.add_argument("--pairs-needed", type=int, default=0,
                    help="pairs to place (default: the pack's used pair rows); the element is whatever --pair-lef "
                         "is, so a different ROM macro depth enters through its pair abstract and count")
    ap.add_argument("--bf16-lef", type=Path, help="BF16 column-pair element abstract (dedicated columns)")
    ap.add_argument("--bf16-pairs", type=int, default=0, help="how many of --pairs-needed are BF16 column pairs")
    ap.add_argument("--label", default="")
    ap.add_argument("--slots-out", type=Path, help="per-slot list (x, y, kind, distance) for W10's bank map")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    rec = json.loads(a.pack.read_text())
    pair = lef_macro(a.pair_lef)
    bf = lef_macro(a.bf16_lef) if a.bf16_lef else None
    out = plan(rec, pair, a.rows, a.row_channel_um, a.col_gap_um, a.spine_um, a.pairs_needed or None, bf,
               a.bf16_pairs)
    out = dict(schema="opentallas.v41.w18_die_floorplan.v1",
               status="floorplan_from_real_element_abstract",
               label=a.label or None,
               inputs=dict(pack=str(a.pack), pack_sha256=sha(a.pack), pair_lef=str(a.pair_lef),
                           pair_lef_sha256=sha(a.pair_lef), tool_sha256=sha(Path(__file__)),
                           **(dict(bf16_lef=str(a.bf16_lef), bf16_lef_sha256=sha(a.bf16_lef)) if a.bf16_lef else {})),
               placeholders=["hub partitions (W11 hardened hub elements pending)",
                             "HBM service bands (K-arb / KV streamer / index-key control)",
                             "SerDes lanes and UCIe-A modules (W15 link ports pending)"],
               **out)
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    if a.slots_out:
        vm = out["hub"]["parts"]["HUB_VM"]
        hx, hy = vm["x"] + vm["w"] / 2, vm["y"] + vm["h"] / 2
        slots = [dict(cluster=c["name"], x=c["x"], y=round(c["y"] + r * c["row_pitch_um"], 3), kind=c["kind"],
                      dist_um=round(abs(c["x"] + c["w"] / 2 - hx) + abs(c["y"] + (r + 0.5) * c["row_pitch_um"] - hy), 1))
                 for c in out["clusters"] for r in range(c["used_rows"])]
        slots.sort(key=lambda s: (s["dist_um"], s["x"], s["y"]))
        a.slots_out.write_text(json.dumps(dict(schema="opentallas.v41.w18_slot_list.v1", floorplan=str(a.output),
                                               floorplan_sha256=sha(a.output), vm_centre_um=[hx, hy],
                                               basis="pair slot origin (x, y); distance = Manhattan from the VM "
                                                     "centre to the slot centre", slots=slots), indent=0) + "\n")
    c = out["capacity"]
    print(json.dumps(dict(pair=out["pair"]["pitch_um"], vs_pack=out["pair"]["pitch_vs_pack"], cap=c,
                          cross=out["crossings"]["vm_to_farthest_cluster"], rule=out["cluster_rule"]), indent=1))


if __name__ == "__main__":
    main()
