#!/usr/bin/env python3
"""ot-clk leaf-drivers: no register sinks on clock-tree trunk legs (generic, config-driven).

Rule (12.16 safe by design): a clock-tree trunk net carries only clock cells. Every group of register CLK pins that the
packed provider netlist hangs on a trunk net gets its own planned leaf driver pair (two inverters = polarity kept):
trunk-side inverter (A on the original trunk bit) -> leaf-side inverter -> new leaf net -> the cluster's CLK pins.
Routers treat a clock net with register sinks as a leaf (signal-layer) net, so without this rule long trunk legs drop
off the clock layers (measured: OpenROAD GRT isNonLeafClock).

Clusters: the registers of one provider clock bit; bits on the same trunk net merge while the merged bbox half-perimeter
stays <= merge_um. Sizing:
  fixed        trunk_cell -> leaf_cell from the config;
  stage_model  both stages = the registry entry's cell (the cell the stage model was fitted for) and merge_um = the span
               whose modelled tap delay (k1*d + k2*d^2, entry 'tap') equals one extra node fanout (entry leg[3]), i.e.
               merging two groups costs no more than a separate driver adds at the trunk node.
Placement: legal sites of R0 rows nearest the cluster centroid (leaf side) and next to it (trunk side), avoiding every
rect of the provider-import preflight (lower OBS, hard keep-outs, existing cells, lower PG) plus all placed provider cells;
lower OBS grow by obs_halo_um so each driver's own rail keeps a PG-access stack site (a cell hugging a partition's M1/M3
OBS gets a legal body but no rail contact).
Inputs are the provider import inputs (inventory ot_start_provider_cells/1, yosys mapped netlist, placements
ot_provider_placement/1, source constraints, bit->net map); outputs are new import inputs, so the unchanged import chain
builds the drivers like every other provider cell (rails, PG access, routing).
"""
import collections
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = "ot_clk_leaf_drivers/1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def lef_sizes(text):
    out = {}
    for m in re.finditer(r"\bMACRO\s+(\S+)(.*?)(?=\bEND\s+\1\b)", text, re.S):
        s = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;", m[2])
        if s:
            out[m[1]] = tuple(map(float, s.groups()))
    return out


def stage_model_sizing(entry):
    """registry entry -> (cell, merge_um): span d where k1*d + k2*d^2 == kf (one extra fanout at the trunk node)."""
    k1, k2 = entry["tap"][:2]
    kf = entry["leg"][3]
    if k2 > 0:
        d = (-k1 + math.sqrt(k1 * k1 + 4 * k2 * kf)) / (2 * k2)
    else:
        d = kf / k1
    return entry["key"]["cell"], round(d, 3)


def clusters(inv, places, bitnet, merge_dbu, dbu):
    def bb(ffs):
        r = [places[c["inst"]]["bbox_dbu"] for c in ffs]
        return [min(x[0] for x in r), min(x[1] for x in r), max(x[2] for x in r), max(x[3] for x in r)]

    def hp(r):
        return r[2] - r[0] + r[3] - r[1]

    bybit = collections.defaultdict(list)
    for c in inv["cells"]:
        if c["sequential"]:
            bybit[c["connections"]["CLK"][0]].append(c)
    bynet = collections.defaultdict(list)
    for bit, ffs in bybit.items():
        bynet[bitnet[str(bit)]].append((bit, ffs))
    out = []
    for net in sorted(bynet):
        cl = [[bit, list(ffs)] for bit, ffs in sorted(bynet[net])]
        while len(cl) > 1:
            best = None
            for i in range(len(cl)):
                for j in range(i + 1, len(cl)):
                    h = hp(bb(cl[i][1] + cl[j][1]))
                    if h <= merge_dbu and (best is None or h < best[0]):
                        best = (h, i, j)
            if not best:
                break
            _, i, j = best
            cl[i][1] += cl[j][1]
            del cl[j]
        for bit, ffs in cl:
            out.append(dict(net=net, bit=bit, ffs=ffs, bbox=bb(ffs), hpwl_um=hp(bb(ffs)) / dbu))
    return out, len(bynet)


class Sites:
    """Legal R0-row slots against fixed blockers + cells added so far."""

    def __init__(self, rows, rects, height, search_dbu):
        from shapely.geometry import box
        from shapely.strtree import STRtree
        self.box = box
        self.rows = collections.defaultdict(list)
        for r in rows:
            if r["orient"] == "R0":
                self.rows[r["origin"][1]].append(r)
        self.ys = sorted(self.rows)
        self.rects = rects
        self.tree = STRtree([box(*r) for r in rects])
        self.new = collections.defaultdict(list)
        self.H = height
        self.S = search_dbu
        self.B = 8000

    def _bk(self, r):
        for x in range(r[0] // self.B, (r[2] - 1) // self.B + 1):
            for y in range(r[1] // self.B, (r[3] - 1) // self.B + 1):
                yield x, y

    def place(self, w, tx, ty):
        S, H = self.S, self.H
        win = [tx - S, ty - S, tx + S, ty + S + H]
        near_all = [self.rects[int(i)] for i in self.tree.query(self.box(*win))]
        for k in self._bk(win):
            near_all += self.new[k]
        best = None
        for y in sorted((y for y in self.ys if ty - S <= y <= ty + S), key=lambda y: abs(y + H / 2 - ty)):
            if best and abs(y + H / 2 - ty) >= best[0]:
                break
            near = [r for r in near_all if y < r[3] and r[1] < y + H]
            for row in self.rows[y]:
                rb, dx = row["bbox"], row["spacing"]
                iv = [(max(tx - S, rb[0]), min(tx + S, rb[2]) - w)]
                for r in near:
                    lo, hi = r[0] - w, r[2]
                    nxt = []
                    for lo_, up in iv:
                        if hi <= lo_ or up <= lo:
                            nxt.append((lo_, up))
                            continue
                        if lo_ < lo:
                            nxt.append((lo_, lo))
                        if hi < up:
                            nxt.append((hi, up))
                    iv = nxt
                for lo_, up in iv:
                    kl, ku = math.ceil((lo_ - rb[0]) / dx), math.floor((up - rb[0]) / dx)
                    if kl > ku:
                        continue
                    k = max(kl, min(ku, round((tx - w / 2 - rb[0]) / dx)))
                    x = rb[0] + k * dx
                    r = [x, y, x + w, y + H]
                    if any(hit(r, q) for q in near):
                        continue
                    cost = abs(x + w / 2 - tx) + abs(y + H / 2 - ty)
                    if best is None or cost < best[0]:
                        best = (cost, r)
        if not best:
            return None
        for k in self._bk(best[1]):
            self.new[k].append(best[1])
        return best[1]


def plan(lc, registry=None, stage_entry=None):
    """lc = config leaf_drivers section (paths + sizing). Returns (inventory, mapped, placements, record)."""
    inv = json.loads(Path(lc["inventory"]).read_text())
    M = json.loads(Path(lc["mapped"]).read_text())
    mod = M["modules"][lc["top"]]
    pl = json.loads(Path(lc["placements"]).read_text())
    g = json.loads(Path(lc["constraints"]).read_text())
    bitnet = json.loads(Path(lc["bit_nets"]).read_text())
    sizes = lef_sizes(Path(lc["lef"]).read_text())
    D = g["dbu"]
    if pl["inventory_sha256"] != sha(lc["inventory"]):
        raise ValueError("placements are not for this inventory")
    sizing = lc.get("sizing", "fixed")
    if sizing == "fixed":
        trunk, leaf, merge_um = lc["trunk_cell"], lc["leaf_cell"], float(lc["merge_um"])
    elif sizing == "stage_model":
        e = (registry or {}).get(stage_entry)
        if e is None or "tap" not in e:
            raise ValueError(f"stage-model sizing needs a registry entry with a tap model: {stage_entry!r}")
        cell, merge_um = stage_model_sizing(e)
        trunk = leaf = cell
    else:
        raise ValueError(f"unknown leaf_drivers.sizing {sizing!r}")
    wh = {}
    for m in (trunk, leaf):
        w, h = sizes[m]
        wh[m] = (round(w * D), round(h * D))
    H = {h for _, h in wh.values()}
    if len(H) != 1:
        raise ValueError("leaf driver masters must be single-row cells of one height")
    H = H.pop()
    places = {c["inst"]: c for c in pl["cells"]}
    cls, ntrunk = clusters(inv, places, bitnet, round(merge_um * D), D)
    halo = round(float(lc.get("obs_halo_um", 0)) * D)    # PG-access clearance: the rail stack (V1/M2/V2/M3) must clear lower OBS
    rects = ([[r[2] - halo, r[3] - halo, r[4] + halo, r[5] + halo] for r in g["actual_lower_OBS"]] + [r[1:] for r in g["hard_forbidden"]] + [r[2:] for r in g["existing_cells"]]
             + [r[2:] for r in g["actual_lower_PG"]] + [c["bbox_dbu"] for c in pl["cells"]])
    sites = Sites(g["rows"], rects, H, round(float(lc.get("search_um", 40)) * D))
    nb = 1 + max(max(b for c in mod["cells"].values() for v in c["connections"].values() for b in v if isinstance(b, int)),
                 max(b for q in mod["ports"].values() for b in q["bits"] if isinstance(b, int)))
    prefix, oprefix = lc.get("inst_prefix", "ot_leaf_ck"), lc.get("odb_prefix", "")
    newinv, newpl, rec, ffnew, failed = [], [], [], {}, []
    for k, cl in enumerate(cls):
        bx = [places[c["inst"]]["bbox_dbu"] for c in cl["ffs"]]
        cx = sum(b[0] + b[2] for b in bx) // (2 * len(bx))
        cy = sum(b[1] + b[3] for b in bx) // (2 * len(bx))
        rb = sites.place(wh[leaf][0], cx, cy)
        ra = sites.place(wh[trunk][0], (rb[0] + rb[2]) // 2, (rb[1] + rb[3]) // 2) if rb else None
        if not (ra and rb):
            failed.append(dict(cluster=k, net=cl["net"]))
            continue
        mid, lf = nb, nb + 1
        nb += 2
        stage = cl["ffs"][0]["stage"]
        for nm, ms, cn, rr in ((f"{prefix}{k}_a", trunk, {"A": [cl["bit"]], "Y": [mid]}, ra),
                               (f"{prefix}{k}_b", leaf, {"A": [mid], "Y": [lf]}, rb)):
            newinv.append(dict(inst=nm, stage=stage, role="clock_leaf", master=ms, wh_um=[wh[ms][0] / D, H / D],
                               area_um2=wh[ms][0] * H / D / D, sequential=False, connections=cn,
                               directions={"A": "input", "Y": "output"}))
            md = max(abs(xx - cx) + abs(yy - cy) for xx in (rr[0], rr[2]) for yy in (rr[1], rr[3])) / D
            newpl.append(dict(inst=nm, odb_inst=oprefix + nm, stage=stage, master=ms, bbox_dbu=rr, xy_dbu=rr[:2], orient="R0",
                              sequential=False, legacy_ff_window=False, max_anchor_displacement_um=md, soft_OBS_hosts=[]))
        for c in cl["ffs"]:
            ffnew[c["inst"]] = lf
        r = cl["bbox"]
        lr = [min(r[0], rb[0]), min(r[1], rb[1]), max(r[2], rb[2]), max(r[3], rb[3])]
        rec.append(dict(cluster=k, net=cl["net"], port_bit=cl["bit"], ffs=len(cl["ffs"]), ff_hpwl_um=cl["hpwl_um"],
                        leaf_hpwl_um=(lr[2] - lr[0] + lr[3] - lr[1]) / D, trunk_cell=ra, leaf_cell=rb, centroid=[cx, cy],
                        x16_to_centroid_um=(abs((rb[0] + rb[2]) / 2 - cx) + abs((rb[1] + rb[3]) / 2 - cy)) / D,
                        a_to_b_um=(abs(ra[0] - rb[0]) + abs(ra[1] - rb[1])) / D))
    if failed:
        raise ValueError(f"no legal leaf-driver slot for {len(failed)} clusters, e.g. {failed[:3]}")
    for c in inv["cells"]:
        if c["inst"] in ffnew:
            c["connections"]["CLK"] = [ffnew[c["inst"]]]
    inv["cells"] += newinv
    inv["counts"]["cells"] = len(inv["cells"])
    inv["counts"]["comb"] += len(newinv)
    inv["cells_count_note"] = "ot-clk leaf-drivers: +%d clock leaf driver cells (role clock_leaf)" % len(newinv)
    for n, c in mod["cells"].items():
        if n in ffnew:
            c["connections"]["CLK"] = [ffnew[n]]
    for q in newinv:
        mod["cells"][q["inst"]] = dict(hide_name=0, type=q["master"], parameters={}, attributes={"ot_role": "clock_leaf"},
                                       port_directions=dict(q["directions"]),
                                       connections={k: list(v) for k, v in q["connections"].items()})
        mod["netnames"][q["inst"] + "_Y"] = dict(hide_name=0, bits=list(q["connections"]["Y"]), attributes={})
    pl["cells"] += newpl
    pl["summary"]["all_cells"] = pl["summary"]["placed"] = len(pl["cells"])
    pl["summary"]["comb"] += len(newpl)
    pl["summary"]["leaf_note"] = "ot-clk leaf-drivers: +%d clock leaf cells" % len(newpl)
    hpw = sorted(r["leaf_hpwl_um"] for r in rec)
    per = collections.Counter(r["net"] for r in rec)
    summ = dict(schema=SCHEMA, trunk_nets=ntrunk, clusters=len(rec), new_cells=len(newinv),
                ffs=sum(r["ffs"] for r in rec), clusters_per_net=dict(collections.Counter(per.values())),
                ffs_per_cluster=dict(collections.Counter(r["ffs"] for r in rec)), leaf_hpwl_um_max=hpw[-1] if hpw else 0,
                leaf_hpwl_um_median=hpw[len(hpw) // 2] if hpw else 0,
                x16_to_centroid_um_max=max((r["x16_to_centroid_um"] for r in rec), default=0),
                a_to_b_um_max=max((r["a_to_b_um"] for r in rec), default=0), merge_um=merge_um,
                new_area_um2=sum(q["area_um2"] for q in newinv))
    summ.update(sizing=sizing, trunk_cell=trunk, leaf_cell=leaf, obs_halo_um=halo / D)
    return inv, M, pl, dict(summary=summ, clusters=rec)


FILES = ("provider_cells_leaf.json", "provider_mapped_leaf.json", "placements_leaf.json")


def run(lc, out, registry=None, stage_entry=None):
    out = Path(out)
    if (out / FILES[0]).exists():
        raise ValueError(f"preserve existing leaf-driver inputs in {out}")
    out.mkdir(parents=True, exist_ok=True)
    inv, M, pl, rec = plan(lc, registry, stage_entry)
    json.dump(inv, open(out / FILES[0], "w"), separators=(",", ":"))
    json.dump(M, open(out / FILES[1], "w"), separators=(",", ":"))
    pl["inventory_sha256"] = sha(out / FILES[0])
    json.dump(pl, open(out / FILES[2], "w"), separators=(",", ":"))
    rec["summary"]["inputs"] = {k: sha(lc[k]) for k in ("inventory", "mapped", "placements", "constraints")}
    rec["summary"]["outputs"] = {f: sha(out / f) for f in FILES}
    json.dump(rec, open(out / "leaf_clusters.json", "w"), indent=0)
    return rec["summary"]
