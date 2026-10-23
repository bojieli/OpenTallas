#!/usr/bin/env python3
"""Die connectivity + geometry dump for the feedthrough census (FT-TOOL, owner 10-23).

Runs INSIDE OpenROAD's Python (`openroad -python -exit odb_dump.py`), configured by environment:
    FT_ODB   die ODB (read-only)
    FT_OUT   output directory
    FT_BUF_RE  optional regex of pass-through std-cell masters (default ASAP7 BUF/INV/HB/CKBUF/CKINV)
    FT_HIFAN   optional fanout above which a driver is summarised, not expanded (default 64)

Outputs (all plain TSV, gz where large; the census reads them with dump_io.py):
  die.json        dbu, die / core box (um), counts, layer list (name, direction, pitch)
  blocks.tsv      inst master x y w h orient                   (every BLOCK-type instance, um, placed bbox)
  masters.tsv     master w h npins pin_layers obs_layers obs_cover   (BLOCK masters; obs_cover = per-layer
                  sum(rect area)/master area, clipped to 1.0: 1.0 = full-footprint blanket)
  mpins.tsv.gz    master bus dir nbits layers face lo hi      (BLOCK master signal pins grouped by bus name
                  = pin name with the trailing [i] stripped; face = nearest outline edge N/S/E/W/A(area);
                  lo/hi = along-face offset range in um, master frame)
  bundles.tsv.gz  src_inst src_bus dst_inst dst_bus bits nbuf_max nbuf_sum sigtype
                  one line per (driver inst/bus, sink inst/bus) after collapsing pass-through buffers.
                  inst "PORT" = a die BTerm (bus = port bus name); a non-buffer std cell sink is "CELL:<master>"
                  (inst name dropped, aggregated per master).
  hifan.tsv       src_inst src_bus nets sinks nbuf sigtype      (drivers whose collapsed fanout > FT_HIFAN)
  stdcells.tsv    master count                                  (top-level std-cell instances by master)
"""
import gzip
import json
import os
import re
import sys
import time
from collections import defaultdict

import odb  # noqa: E402  (OpenROAD python)

BUS_RE = re.compile(r"^(.*?)(\[\d+\])+$")
DEF_BUF_RE = r"^(BUF|INV|HB\d|CKBUF|CKINV)\w*_ASAP7"


def bus_of(name):
    m = BUS_RE.match(name)
    return m.group(1) if m else name


def main():
    odb_path = os.environ["FT_ODB"]
    out = os.environ["FT_OUT"]
    buf_re = re.compile(os.environ.get("FT_BUF_RE", DEF_BUF_RE))
    hifan = int(os.environ.get("FT_HIFAN", "64"))
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    db = odb.dbDatabase.create()
    odb.read_db(db, odb_path)
    blk = db.getChip().getBlock()
    tech = db.getTech()
    dbu = float(tech.getDbUnitsPerMicron())
    um = lambda v: round(v / dbu, 3)  # noqa: E731
    print(f"read {odb_path} in {time.time()-t0:.0f}s", flush=True)

    die = blk.getDieArea()
    core = blk.getCoreArea()
    layers = []
    for L in tech.getLayers():
        if L.getType() == "ROUTING":
            layers.append(dict(name=L.getName(), dir=L.getDirection(), pitch=um(L.getPitch()),
                               width=um(L.getWidth())))

    # ---- masters -------------------------------------------------------------------------------------------
    is_block = {}
    is_buf = {}
    std_count = defaultdict(int)
    bmasters = {}
    for inst in blk.getInsts():
        m = inst.getMaster()
        n = m.getName()
        if n in is_block:
            if not is_block[n]:
                std_count[n] += 1
            continue
        blkm = bool(m.isBlock())
        is_block[n] = blkm
        if blkm:
            bmasters[n] = m
            continue
        std_count[n] += 1
        sig = [mt for mt in m.getMTerms() if mt.getSigType() not in ("POWER", "GROUND")]
        ins = [mt for mt in sig if mt.getIoType() == "INPUT"]
        outs = [mt for mt in sig if mt.getIoType() == "OUTPUT"]
        is_buf[n] = bool(buf_re.search(n)) and len(ins) == 1 and len(outs) == 1
    with open(os.path.join(out, "stdcells.tsv"), "w") as f:
        for n, c in sorted(std_count.items(), key=lambda x: -x[1]):
            f.write(f"{n}\t{c}\t{int(is_buf.get(n, False))}\n")

    with open(os.path.join(out, "masters.tsv"), "w") as fm, gzip.open(os.path.join(out, "mpins.tsv.gz"), "wt") as fp:
        for n, m in sorted(bmasters.items()):
            W, H = m.getWidth(), m.getHeight()
            area = float(W) * float(H) or 1.0
            pl = defaultdict(int)
            bus = {}
            np_ = 0
            for mt in m.getMTerms():
                if mt.getSigType() in ("POWER", "GROUND"):
                    continue
                np_ += 1
                b = bus_of(mt.getName())
                rec = bus.setdefault(b, dict(dir=mt.getIoType(), n=0, layers=set(), faces=defaultdict(int),
                                            lo=None, hi=None, sig=mt.getSigType()))
                rec["n"] += 1
                for p in mt.getMPins():
                    bb = p.getBBox()
                    cx, cy = (bb.xMin() + bb.xMax()) / 2, (bb.yMin() + bb.yMax()) / 2
                    for g in p.getGeometry():
                        L = g.getTechLayer()
                        if L is not None:
                            pl[L.getName()] += 1
                            rec["layers"].add(L.getName())
                    d = dict(S=cy, N=H - cy, W=cx, E=W - cx)
                    face = min(d, key=d.get)
                    if d[face] > 0.05 * min(W, H) and d[face] > 2 * dbu:
                        face = "A"
                    rec["faces"][face] += 1
                    off = cx if face in "NS" else cy
                    rec["lo"] = off if rec["lo"] is None else min(rec["lo"], off)
                    rec["hi"] = off if rec["hi"] is None else max(rec["hi"], off)
                    break  # first pin shape is enough for face/offset
            ob = defaultdict(float)
            for g in m.getObstructions():
                L = g.getTechLayer()
                if L is None:
                    continue
                ob[L.getName()] += float(g.getDX()) * float(g.getDY())
            obs_layers = ",".join(sorted(ob))
            obs_cover = ",".join(f"{k}:{min(1.0, v/area):.3f}" for k, v in sorted(ob.items()))
            pls = ",".join(f"{k}:{v}" for k, v in sorted(pl.items()))
            fm.write(f"{n}\t{um(W)}\t{um(H)}\t{np_}\t{pls}\t{obs_layers}\t{obs_cover}\n")
            for b, r in sorted(bus.items()):
                face = max(r["faces"], key=r["faces"].get) if r["faces"] else "?"
                fp.write(f"{n}\t{b}\t{r['dir']}\t{r['n']}\t{','.join(sorted(r['layers']))}\t{face}\t"
                         f"{um(r['lo'] or 0)}\t{um(r['hi'] or 0)}\t{r['sig']}\n")
    print(f"masters done {time.time()-t0:.0f}s", flush=True)

    nblk = 0
    with open(os.path.join(out, "blocks.tsv"), "w") as f:
        for inst in blk.getInsts():
            if not is_block[inst.getMaster().getName()]:
                continue
            nblk += 1
            b = inst.getBBox()
            f.write(f"{inst.getName()}\t{inst.getMaster().getName()}\t{um(b.xMin())}\t{um(b.yMin())}\t"
                    f"{um(b.xMax()-b.xMin())}\t{um(b.yMax()-b.yMin())}\t{inst.getOrient()}\t"
                    f"{inst.getPlacementStatus()}\n")

    # ---- connectivity: collapse pass-through buffers from every block output / die input --------------------
    def sinks_of(net):
        """-> list of (kind, inst, pin, nbuf) reached from net through pass-through buffers."""
        res = []
        stack = [(net, 0)]
        seen = 0
        while stack:
            n, k = stack.pop()
            seen += 1
            if seen > 200000:
                break
            for it in n.getITerms():
                mt = it.getMTerm()
                if mt.getIoType() != "INPUT" and mt.getIoType() != "INOUT":
                    continue
                inst = it.getInst()
                mn = inst.getMaster().getName()
                if is_block[mn]:
                    res.append(("B", inst.getName(), mt.getName(), k))
                elif is_buf.get(mn):
                    for o in inst.getITerms():
                        if o.getMTerm().getIoType() == "OUTPUT" and o.getNet() is not None:
                            stack.append((o.getNet(), k + 1))
                else:
                    res.append(("C", "CELL:" + mn, mt.getName(), k))
            for bt in n.getBTerms():
                if bt.getIoType() in ("OUTPUT", "INOUT"):
                    res.append(("P", "PORT", bt.getName(), k))
        return res

    agg = {}
    hf = []
    ndrv = 0

    def add(src_inst, src_pin, net):
        nonlocal ndrv
        ndrv += 1
        st = net.getSigType()
        sk = sinks_of(net)
        sb = bus_of(src_pin)
        if len(sk) > hifan:
            hf.append((src_inst, src_pin, len(sk), max((s[3] for s in sk), default=0), st))
            return
        for kind, di, dp, k in sk:
            key = (src_inst, sb, di, bus_of(dp), st)
            r = agg.get(key)
            if r is None:
                agg[key] = [1, k, k]
            else:
                r[0] += 1
                r[1] = max(r[1], k)
                r[2] += k

    for inst in blk.getInsts():
        if not is_block[inst.getMaster().getName()]:
            continue
        nm = inst.getName()
        for it in inst.getITerms():
            mt = it.getMTerm()
            if mt.getIoType() != "OUTPUT" or mt.getSigType() in ("POWER", "GROUND"):
                continue
            net = it.getNet()
            if net is not None:
                add(nm, mt.getName(), net)
    for bt in blk.getBTerms():
        if bt.getIoType() == "INPUT" and bt.getSigType() not in ("POWER", "GROUND") and bt.getNet() is not None:
            add("PORT", bt.getName(), bt.getNet())
    print(f"connectivity {ndrv} drivers, {len(agg)} bundles, {len(hf)} hifan, {time.time()-t0:.0f}s", flush=True)

    with gzip.open(os.path.join(out, "bundles.tsv.gz"), "wt") as f:
        for (si, sb, di, db_, st), (n, kmax, ksum) in agg.items():
            f.write(f"{si}\t{sb}\t{di}\t{db_}\t{n}\t{kmax}\t{ksum}\t{st}\n")
    # high fanout: aggregate per (inst, bus)
    hagg = {}
    for si, sp, n, k, st in hf:
        key = (si, bus_of(sp), st)
        r = hagg.setdefault(key, [0, 0, 0])
        r[0] += 1
        r[1] += n
        r[2] = max(r[2], k)
    with open(os.path.join(out, "hifan.tsv"), "w") as f:
        for (si, sb, st), (nn, ns, k) in hagg.items():
            f.write(f"{si}\t{sb}\t{nn}\t{ns}\t{k}\t{st}\n")

    json.dump(dict(schema="opentallas.die_feedthrough.dump.v1", odb=odb_path, design=blk.getName(), dbu=dbu,
                   die=[um(die.xMin()), um(die.yMin()), um(die.xMax()), um(die.yMax())],
                   core=[um(core.xMin()), um(core.yMin()), um(core.xMax()), um(core.yMax())],
                   n_blocks=nblk, n_block_masters=len(bmasters), n_std=sum(std_count.values()),
                   n_drivers=ndrv, n_bundles=len(agg), n_hifan=len(hf), layers=layers,
                   seconds=round(time.time() - t0, 1)),
              open(os.path.join(out, "die.json"), "w"), indent=1)
    print(f"done {time.time()-t0:.0f}s", flush=True)


main()
