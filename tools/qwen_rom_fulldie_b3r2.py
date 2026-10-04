"""Qwen3-8B ROM full die, b3 r2: congestion closure source (default off; the b2 generator is not edited).

Builds on the b3 selection of tools/qwen_rom_fulldie_b3.py (codex/qwen-fulldie-pg-repair-20261003):
  F1  one pipelined reset wire per tile column instead of 64 (corridor 637 -> 388 bits),
  F2  the 379-bit column instruction as two 190-bit beats into a 2-deep column FIFO (tap 511 -> 325 bits),
  VCH the spine vertical link channel 174.096 -> 260.064 um,
  (c) the lower (south) hub<->stack link split over both edges of the channel,
and adds, in this file:
  pins   real signal interfaces for the ten abstracts b3_launch_r2 refused as signal-empty
         (constants_sequencer, port_tiles_6, scale_rom_0..7), taken from the RTL port lists:
           scale ROM  per result-port group: scale_gre 1 + scale_addr AW 24 (port -> ROM), scale_q W*16 = 256
                      (ROM -> port), shared scale_re 1     (rtl/hdc/ot_qwen_me_array_w12.sv ot_qwen_me_spine_w12)
           constant ROM  crom_re SW + crom_addr SW*AW (SU -> ROM), crom_q SW*64 (ROM -> SU), SW = 64
                      (rtl/hdc/ot_hdc_core_vector_weight.sv)
           sequencer  ME instruction ib 379 + go + valid/ready to the head-chain x root (vector memory),
                      the non-ME ISA fields (tools/hdc_isa.FIELDS) + valid/ready to SU64, collective descriptor
                      64 + start/done (rtl/rom/ot_rom_tp_seq.sv), ME/SU done back to the sequencer
         and the port-group -> slab map by area (slab 6 holds the overflow groups of bands 2 and 5, whose words
         the b2/b3 generator sent to slabs 2 and 5 regardless of capacity);
  meso   clock regions of decision C (origin/main d99237f66, rom_die_clocking_decision_20261003): one region per
         4 x 4-tile block, per spine band, per strip third, per IO block; FIFO slots that carry the decision's
         2.53 mm2 (tile-tap FIFOs inside a taller station frame, block-word FIFOs in the port slabs, strip-return
         FIFOs in a taller strip FIFO frame);
  band   (variant) port and scale slabs re-packed next to the block-row band they serve.  The b2/b3 packing puts
         all six band port slabs south of the hub, so bands 3-5's 24,576 block-word bits run 10-25 mm down the
         spine: 35,840 vertical bits cross y = 8.8 mm in the spine against 2,112 link bits (cut census below).
"""
import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_fulldie as F          # noqa: E402
import qwen_rom_fulldie_pg_r3 as PG   # noqa: E402

SCHEMA = 'opentallas.qwen-rom-fulldie.b3r2.v1'
CLOCKING = 'results/uarch/rom_die_clocking_decision_20261003.json @ d99237f66'
# decision C FIFO inventory (derivation.area.qwen.C): 3,332,608 bits -> 2.53 mm2 (gross, depth 4)
FIFO_MM2_PER_BIT = 2.53 / 3332608
TAP_FIFO_BITS = 509 * 4            # one per tile tap (1,536)
BW_FIFO_BITS = 512 * 4             # one per block word (96)
STRIP_FIFO_BITS = 544 * 4          # one per strip return (4)
# F2 station storage: 388 corridor flops + 379 assembly + one extra 190-bit beat entry, against 637 before
F2_STATION_EXTRA_BITS = 388 + 379 + 190 - 637
PORT_GROUPS, GROUPS_PER_BAND, BANDS = 96, 16, 6
SC_IN = 1 + 24                      # scale_gre + scale_addr, per group
SC_OUT = 16 * 16                    # scale_q W*16, per group
SW, AW = 64, 24
CROM_IN, CROM_OUT = SW + SW * AW, SW * 64
REGION_MAX_MM = 5.25


def _isa_bits():
    import hdc_isa as I
    me = sum(w for n, w in I.FIELDS if n.startswith('me_'))
    return sum(w for n, w in I.FIELDS), me


def selected(enabled=False, band=False):
    if not enabled:
        raise ValueError('b3r2 selection is default off')
    spec = importlib.util.spec_from_file_location('qfd_b3r2_private', F.__file__)
    v = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v)
    # ---- Codex b3 selection (tools/qwen_rom_fulldie_b3.py selected()), unchanged
    old_vch = v.VCH
    v.VCH = v.up(260, v.GX)
    v.SPINE_W_R2 += v.VCH - old_vch
    v.LST_V = (v.VCH, v.LST_V[1])
    v.CORRIDOR_BITS = 388
    v.TAP_BITS = 325
    v.REGION_PG = {r: (.48 / PG.bump_pitch(c, 90) if c else 0.) for r, c in F.REGION_PG.items()}
    # ---- meso FIFO slots and F2 storage
    st_extra_um2 = (TAP_FIFO_BITS + F2_STATION_EXTRA_BITS) * FIFO_MM2_PER_BIT * 1e6
    st_extra_h = v.up(st_extra_um2 / v.CORR, v.GY)
    v.STATION = (v.CORR, v.STATION[1] + st_extra_h)
    sf_extra_h = v.up(STRIP_FIFO_BITS * FIFO_MM2_PER_BIT * 1e6 / v.FIFO[0], v.GY)
    v.FIFO = (v.FIFO[0], v.FIFO[1] + sf_extra_h)
    bw_mm2 = PORT_GROUPS * BW_FIFO_BITS * FIFO_MM2_PER_BIT
    v.SPINE_BLOCKS = [(n, (a + bw_mm2) if n == 'port_tiles' else a, d, s) for n, a, d, s in v.SPINE_BLOCKS]
    m = v.build(tree_mode='banded')
    _split_south(v, m)
    if band:
        # the band repack loses the sub-group slivers of each interval: widen the spine on the 0.432 um lattice
        # until every slab packs (the step count is recorded with the die)
        w0 = m['geo']['spine_w_needed']
        for step in range(0, 400):
            m = v.build(spine_w=round(w0 + 4 * step * v.GX, 3), tree_mode='banded')
            m['geo']['spine_w_needed'] = w0
            _split_south(v, m)
            try:
                _repack_band(v, m)
            except SystemExit:
                continue
            m['geo']['band_repack_spine_w'] = round(w0 + 4 * step * v.GX, 3)
            m['geo']['band_repack_widen_um'] = round(4 * step * v.GX, 3)
            break
        else:
            raise SystemExit('band repack does not pack')
    groups = _group_map(v, m)
    _spine_buses(v, m, groups)
    m['clock_regions'] = clock_regions(v, m)
    m['die']['budget_mm2'] = 858
    m['die']['margin_mm2'] = round(858 - m['die']['mm2'], 3)
    m['b3r2'] = dict(station_frame_um=list(v.STATION), station_extra_h_um=st_extra_h, strip_fifo_frame_um=list(v.FIFO),
                     strip_fifo_extra_h_um=sf_extra_h, bw_fifo_mm2=round(bw_mm2, 4), band=band, groups=groups)
    _wrap_masters(v, m)
    return v, m


def _split_south(v, m):
    """tools/qwen_rom_fulldie_b3.py selected(): south leg split over both channel edges (verbatim logic)."""
    half = v.VCH / 2
    oldleg, oldcorner = m['legs'][0]
    removed = {i.name for i in oldleg} | {oldcorner.name}
    m['insts'] = [i for i in m['insts'] if i.name not in removed]
    splits = {}
    for side, dx in [('W', 0), ('E', half)]:
        leg = []
        for i in oldleg:
            q = v.Inst(i.name + '_' + side, 'qfd_lst_v_split', i.x + dx, i.y, half - v.SHAVE, i.h, kind='link_station',
                       region='hub')
            leg.append(q)
            m['insts'].append(q)
        corner = v.Inst('lc_S' + side, 'qfd_lst_c_split', oldcorner.x + dx, oldcorner.y, half - v.SHAVE, oldcorner.h,
                        oldcorner.orient, kind='link_station', region='hub')
        m['insts'].append(corner)
        splits[side] = (leg, corner)
    buses = []
    for bid, cl, bits, eps in m['buses']:
        if bid.startswith('lnkv_0_'):
            continue
        if bid.startswith('lnkh_0W_'):
            eps = [(splits['W'][1].name, p) if i == oldcorner.name else (i, p) for i, p in eps]
        if bid.startswith('lnkh_0E_'):
            eps = [(splits['E'][1].name, p) if i == oldcorner.name else (i, p) for i, p in eps]
        buses.append((bid, cl, bits, eps))
    for side in ['W', 'E']:
        leg, corner = splits[side]
        prev = ('hub_el', 'lsw' if side == 'W' else 'lse')
        for k, i in enumerate(leg):
            buses.append((f'lnkv_0_{side}_{k}', 'link_spine', v.LINK_TRACKS, [prev, (i.name, 'b')]))
            prev = (i.name, 'a')
        buses.append((f'lnkv_0_{side}_c', 'link_spine', v.LINK_TRACKS, [prev, (corner.name, 'v')]))
    m['buses'] = buses
    m['south_split'] = {s: dict(stations=[i.name for i in l], corner=c.name) for s, (l, c) in splits.items()}


# ------------------------------------------------------------------------------------------------ spine slabs
def _spine_free(v, m, keep):
    """free [lo, hi) intervals per spine column after the kept instances, channel crossings and the hub."""
    g = m['geo']
    cols = {'W': g['x_spine'], 'E': g['x_vch'] + v.VCH}
    ch = g['ch_y']
    segs = [(g['y0'], ch[0]), (ch[0] + v.HCH, ch[1]), (ch[1] + v.HCH, g['y_top'])]
    hub = m['hub']
    free = {}
    for c, x in cols.items():
        iv = [list(s) for s in segs]
        blocks = [(i.y, i.y + i.h + v.SHAVE) for i in keep if abs(i.x - x) < 1]
        if c == 'W':
            blocks.append((hub.y, hub.y + hub.h + v.SHAVE))
        for lo, hi in blocks:
            nxt = []
            for a, b in iv:
                if hi <= a or lo >= b:
                    nxt.append([a, b])
                    continue
                if lo > a:
                    nxt.append([a, lo])
                if hi < b:
                    nxt.append([hi, b])
            iv = nxt
        free[c] = [x_ for x_ in iv if x_[1] - x_[0] > v.GY]
    return cols, free


def _repack_band(v, m):
    """Port and scale slabs in band order, filled bottom-up through both spine columns (central blocks and the hub
    stay).  Each band is four units: its west-half and east-half port groups (block columns 0-7 / 8-15, so a block
    word enters the column on its own side) and the matching scale halves.  A unit goes to the column whose fill
    cursor is lower (its own side on a tie within one group height) and is split at interval ends on whole port
    groups; the first port fragment of a band is that band's primary (result word to the tree top)."""
    g = m['geo']
    cw = g['cw']
    central = [i for i in m['insts'] if i.kind == 'spine_block' and not i.name.startswith(('sp_port_tiles', 'sp_scale_rom'))]
    m['insts'] = [i for i in m['insts'] if not i.name.startswith(('sp_port_tiles', 'sp_scale_rom'))]
    cols, free = _spine_free(v, m, central)
    rows = g['row_y']
    tgt = [(rows[4 * b] + rows[4 * b + 3] + v.TILE_SLOT[1]) / 2 for b in range(BANDS)]
    port_g = next(a for n, a, *_ in v.SPINE_BLOCKS if n == 'port_tiles') / PORT_GROUPS
    scale_g = next(a for n, a, *_ in v.SPINE_BLOCKS if n == 'scale_rom') / PORT_GROUPS
    for c in free:
        free[c].sort()
    cur = {c: 0 for c in free}            # index of the interval being filled
    parts = []
    m['band_slabs'] = {}
    nfrag = {}

    def start(c, per):
        """lowest y where one group of `per` mm2 fits in column c (skipping slivers), or None."""
        h = v.up(per * 1e6 / cw, v.GY)
        while cur[c] < len(free[c]) and free[c][cur[c]][1] - free[c][cur[c]][0] < h - 1e-6:
            cur[c] += 1
        return free[c][cur[c]][0] if cur[c] < len(free[c]) else None

    for b in range(BANDS):
        for kind, per in (('port', port_g), ('scale', scale_g)):
            for side in ('W', 'E'):
                left = GROUPS_PER_BAND // 2
                gidx = [GROUPS_PER_BAND * b + (0 if side == 'W' else 8) + j for j in range(8)]
                while left:
                    hg = v.up(per * 1e6 / cw, v.GY)
                    st = {c: start(c, per) for c in free}
                    opts = [c for c in st if st[c] is not None]
                    if not opts:
                        raise SystemExit(f'spine: band {b} {kind} does not pack')
                    c = min(opts, key=lambda c_: (st[c_] - (hg if c_ == side else 0)))
                    iv = free[c][cur[c]]
                    n = min(left, int((iv[1] - iv[0]) * cw / 1e6 / per + 1e-9))
                    h = v.up(n * per * 1e6 / cw, v.GY)
                    if h > iv[1] - iv[0] + 1e-6:
                        n -= 1
                        h = v.up(n * per * 1e6 / cw, v.GY)
                    y = iv[0]
                    iv[0] = y + h
                    key = (kind, b)
                    k = nfrag.get(key, 0)
                    nfrag[key] = k + 1
                    base = f'sp_{"port_tiles" if kind == "port" else "scale_rom"}_{b}'
                    name = base if k == 0 else f'{base}_f{k}'
                    it = v.Inst(name, 'qfd' + name[2:], cols[c], y, cw - v.SHAVE, h - v.SHAVE, kind='spine_block',
                                region='hub')
                    m['insts'].append(it)
                    gs, gidx = gidx[:n], gidx[n:]
                    m['band_slabs'].setdefault(key, []).append((it, gs))
                    parts.append(dict(name=name[3:], kind=kind, band=b, side=side, col=c, groups=gs, y=round(y, 3),
                                      h=round(h, 3), target_y=round(tgt[b], 1), offset_um=round(y + h / 2 - tgt[b], 1)))
                    left -= n
    m['geo']['spine_parts_band'] = parts


def _take(lst, iv, lo, hi):
    i = lst.index(iv)
    new = []
    if lo - iv[0] > v_GY:
        new.append([iv[0], lo])
    if iv[1] - hi > v_GY:
        new.append([hi, iv[1]])
    lst[i:i + 1] = new


v_GY = F.GY


def _group_map(v, m):
    """port group -> (port slab inst, scale slab inst); block b of band b//16 slot j = b % 16 is group 16*band + j."""
    if 'band_slabs' in m:
        port, scale = {}, {}
        for (kind, b), frags in m['band_slabs'].items():
            for it, gs in frags:
                for g in gs:
                    (port if kind == 'port' else scale)[g] = it.name
        return dict(port=port, scale=scale, primary={b: m['band_slabs'][('port', b)][0][0].name for b in range(BANDS)})
    by = {i.name: i for i in m['insts']}
    per = next(a for n, a, *_ in v.SPINE_BLOCKS if n == 'port_tiles') / PORT_GROUPS
    port, over = {}, []
    for b in range(BANDS):
        it = by[f'sp_port_tiles_{b}']
        cap = min(GROUPS_PER_BAND, int((it.w + v.SHAVE) * (it.h + v.SHAVE) / 1e6 / per + 1e-6))
        for j in range(GROUPS_PER_BAND):
            g = GROUPS_PER_BAND * b + j
            if j < cap:
                port[g] = it.name
            else:
                over.append(g)
    extra = sorted(n for n in by if n.startswith('sp_port_tiles_') and int(n.rsplit('_', 1)[1]) >= BANDS)
    for g in over:   # overflow groups -> the remaining port slab(s), in order
        port[g] = extra[0]
    scales = sorted((n for n in by if n.startswith('sp_scale_rom_')), key=lambda n: int(n.rsplit('_', 1)[1]))
    tot = sum((by[n].w + v.SHAVE) * (by[n].h + v.SHAVE) for n in scales)
    scale, acc, gi = {}, 0.0, 0
    for n in scales:
        acc += (by[n].w + v.SHAVE) * (by[n].h + v.SHAVE)
        while gi < PORT_GROUPS and (gi + 0.5) / PORT_GROUPS <= acc / tot + 1e-9:
            scale[gi] = n
            gi += 1
    return dict(port=port, scale=scale, primary={b: f'sp_port_tiles_{b}' for b in range(BANDS)},
                overflow_groups=over, overflow_slab=extra[0] if extra else None)


def _spine_buses(v, m, gm):
    """block words to the slab holding their port group; fragment -> band primary; scale per group pair;
    sequencer / constant ROM interfaces."""
    total, me_bits = _isa_bits()
    B = []
    for bid, cl, bits, eps in m['buses']:
        if bid.startswith('bword_') or bid.startswith('pword_'):
            continue
        B.append((bid, cl, bits, eps))
    for bid, cl, bits, eps in m['buses']:
        if bid.startswith('bword_'):
            blk = int(bid.split('_')[1])
            # block_roots enumerate c0 (16 block columns) outer, r0 (6 bands) inner: blk = 6 * cidx + band.
            # Port group = 16 * band + cidx.  (The b2/b3 generator used port bw{blk % 16}, which puts two block
            # words of one band on the same slab pin, e.g. blocks 0 and 48 on port_tiles_0.bw0.)
            g = GROUPS_PER_BAND * (blk % BANDS) + blk // BANDS
            slab = gm['port'][g]
            # the overflow slab holds groups of two bands: its pins are named by port group
            pin = f'g{g}' if slab == gm.get('overflow_slab') else f'bw{g % GROUPS_PER_BAND}'
            B.append((bid, cl, bits, [eps[0], (slab, pin)]))
    for b in range(BANDS):
        prim = gm['primary'][b]
        B.append((f'pword_{b}', 'tree_spine', v.TREE_BITS, [(prim, 'rw'), ('sp_tree_top', f'bw{b}')]))
        frags = sorted({gm['port'][GROUPS_PER_BAND * b + j] for j in range(GROUPS_PER_BAND)} - {prim})
        for f in frags:
            B.append((f'pfrag_{b}_{f[3:]}', 'tree_spine', v.TREE_BITS, [(f, f'cw{b}'), (prim, f'cf{f[-1]}')]))
    pairs = {}
    for g in range(PORT_GROUPS):
        pairs.setdefault((gm['port'][g], gm['scale'][g]), []).append(g)
    for (p, s), gs in sorted(pairs.items()):
        tag = f'{p[3:]}__{s[3:]}'
        B.append((f'sca_{tag}', 'scale', len(gs) * SC_IN + 1, [(p, f'sa_{s[3:]}'), (s, f'a_{p[3:]}')]))
        B.append((f'scq_{tag}', 'scale', len(gs) * SC_OUT, [(s, f'q_{p[3:]}'), (p, f'sq_{s[3:]}')]))
    seq = 'sp_constants_sequencer'
    B.append(('seq_ib', 'sequencer', 379 + 3, [(seq, 'ib'), ('sp_vector_memory', 'ib')]))
    B.append(('seq_su', 'sequencer', total - me_bits + 2, [(seq, 'su'), ('sp_su64_sfu', 'si')]))
    B.append(('seq_done', 'sequencer', 2, [('sp_tree_top', 'md'), (seq, 'md')]))
    B.append(('seq_sud', 'sequencer', 2, [('sp_su64_sfu', 'sd'), (seq, 'sd')]))
    B.append(('seq_coll', 'sequencer', 64 + 2, [(seq, 'cd'), ('io_collective', 'sd')]))
    B.append(('crom_a', 'crom', CROM_IN, [('sp_su64_sfu', 'ca'), (seq, 'ca')]))
    B.append(('crom_q', 'crom', CROM_OUT, [(seq, 'cq'), ('sp_su64_sfu', 'cq')]))
    m['buses'] = B
    m['isa_bits'] = dict(total=total, me=me_bits, su_and_control=total - me_bits)


def _wrap_masters(v, m):
    """Every endpoint port that the b3 masters do not define becomes a pin group on the face toward the far
    endpoint (M4 on W/E), stacked from the top of the face so no two groups overlap."""
    base = v.masters
    by = {i.name: i for i in m['insts']}

    def masters(model, k=1, port_bits=None):
        out = base(model, k, port_bits)
        hub = out['qfd_hub']
        if 'lsw' not in hub.ports:
            hub.face('lsw', v.LINK_TRACKS, 'W', 'M4', hub.h / 8, 1)
            hub.face('lse', v.LINK_TRACKS, 'E', 'M4', hub.h / 2, 1)
        half = v.VCH / 2
        sv = v.Master('qfd_lst_v_split', half - v.SHAVE, v.LST_V[1] - v.SHAVE, 3, 'b3 one lower stack link, half channel')
        sv.face('a', v.LINK_TRACKS, 'S', 'M5', sv.w / 2, 1)
        sv.face('b', v.LINK_TRACKS, 'N', 'M5', sv.w / 2, 1)
        sc = v.Master('qfd_lst_c_split', half - v.SHAVE, v.HCH - v.SHAVE, 3, 'b3 lower corner, one stack link')
        sc.face('v', v.LINK_TRACKS, 'S', 'M5', sc.w / 2, 1)
        sc.face('w', v.LINK_TRACKS, 'W', 'M4', sc.h / 2, 1)
        sc.face('e', v.LINK_TRACKS, 'E', 'M4', sc.h / 2, 1)
        out[sv.name] = sv
        out[sc.name] = sc
        # spine slabs created by the band repack (fragments) need masters
        for it in model['insts']:
            if it.kind == 'spine_block' and it.master not in out:
                b = v.Master(it.master, it.w, it.h, 7, f'spine reservation slab {it.master}')
                out[it.master] = b
                if it.master.startswith('qfd_sp_port_tiles'):
                    for i in range(16):
                        b.area(f'bw{i}', v.TREE_BITS, 20.0 + (b.w - 40.0) * (i % 8) / 8, b.h * ((i // 8) + 0.5) / 2, 1)
        cursor = {}
        bits = {}
        far = {}
        for bid, cl, nb, eps in model['buses']:
            for idx, (inst, port) in enumerate(eps):
                mst = by[inst].master if inst in by else None
                if mst is None or mst not in out or port.lstrip('*') in out[mst].ports:
                    continue
                other = eps[1 - idx][0] if len(eps) == 2 else eps[0][0]
                bits[(mst, port)] = max(bits.get((mst, port), 0), nb)
                far[(mst, port)] = (by[inst], by[other])
        for (mst, port), nb in sorted(bits.items()):
            M = out[mst]
            me, ot = far[(mst, port)]
            face = 'E' if ot.cx >= me.cx else 'W'
            layer = 'M4'
            step = 0.048 * k
            span = max(1, math.ceil(nb / k)) * step if k > 1 else nb * 0.048
            c = cursor.get((mst, face), M.h - 4.0)
            centre = c - span / 2 - 1.0
            cursor[(mst, face)] = centre - span / 2 - 1.0
            if centre - span / 2 < 1.0:
                raise ValueError(f'{mst}.{port}: face {face} full')
            M.face(port, nb, face, layer, centre, 1)
        return out
    v.masters = masters


# ------------------------------------------------------------------------------------------------ clock regions
def clock_regions(v, m):
    """Decision C regions: 4 x 4-tile blocks (with their corridors), spine bands, strip thirds, IO blocks."""
    g = m['geo']
    rows, colx = g['row_y'], m['col_x']
    R = []
    for c0 in range(0, v.COLS, 4):
        for r0 in range(0, v.ROWS, 4):
            x0 = colx(c0)
            x1 = colx(c0 + 3) + v.TILE_SLOT[0]
            y0, y1 = rows[r0], rows[r0 + 3] + v.TILE_SLOT[1]
            R.append(dict(name=f'creg_t{c0 // 4}_{r0 // 4}', kind='tile_block', rect=[x0, y0, x1, y1]))
    for b in range(BANDS):
        y0 = rows[4 * b] if b else g['y0']
        y1 = rows[4 * b + 3] + v.TILE_SLOT[1] if b < BANDS - 1 else g['y_top']
        R.append(dict(name=f'creg_spine_{b}', kind='spine_band', rect=[g['x_spine'], y0, g['x_arr_e'], y1]))
    for st, res in m['renges'].items():
        for k in range(3):
            parts = res[2 * k:2 * k + 2] + ([m['lfifos'][st]] if k == 1 else [])
            R.append(dict(name=f'creg_strip_{st}_{k}', kind='strip', rect=[min(i.x for i in parts), min(i.y for i in parts),
                     max(i.x + i.w for i in parts), max(i.y + i.h for i in parts)]))
    for name, it in m['io'].items():
        n = max(1, math.ceil(it.w / (REGION_MAX_MM * 1000)))
        for k in range(n):
            R.append(dict(name=f'creg_io_{name}_{k}', kind='io', rect=[it.x + it.w * k / n, it.y, it.x + it.w * (k + 1) / n,
                                                                       it.y + it.h]))
    for r in R:
        x0, y0, x1, y1 = r['rect']
        r['rect'] = [round(z, 3) for z in r['rect']]
        r['extent_mm'] = round(max(x1 - x0, y1 - y0) / 1000, 4)
        r['within_5p25'] = r['extent_mm'] <= REGION_MAX_MM + 1e-9
    return R


def fifo_accounting(v, m):
    st = sum(1 for i in m['insts'] if i.kind == 'station')
    sf = len(m['lfifos'])
    ext = m['b3r2']
    return dict(
        source=CLOCKING, mm2_per_bit=FIFO_MM2_PER_BIT,
        tile_tap=dict(count=st, bits_each=TAP_FIFO_BITS, mm2=round(st * TAP_FIFO_BITS * FIFO_MM2_PER_BIT, 4),
                      slot='inside the station frame (station height + extra, with the F2 storage)'),
        block_word=dict(count=PORT_GROUPS, bits_each=BW_FIFO_BITS, mm2=ext['bw_fifo_mm2'], slot='port_tiles slab area'),
        strip_return=dict(count=sf, bits_each=STRIP_FIFO_BITS, mm2=round(sf * STRIP_FIFO_BITS * FIFO_MM2_PER_BIT, 4),
                          slot='strip FIFO frame height'),
        total_mm2=round((st * TAP_FIFO_BITS + PORT_GROUPS * BW_FIFO_BITS + sf * STRIP_FIFO_BITS) * FIFO_MM2_PER_BIT, 4),
        f2_station_extra=dict(bits_each=F2_STATION_EXTRA_BITS, mm2=round(st * F2_STATION_EXTRA_BITS * FIFO_MM2_PER_BIT, 4)),
        station_frame_um=ext['station_frame_um'], station_frame_extra_h_um=ext['station_extra_h_um'],
        station_slot_mm2_added=round(st * v.CORR * ext['station_extra_h_um'] / 1e6, 4),
        head_frame_note='column heads share the station frame (64 x the same extra height: the head-side 2-deep F2 '
                        'column FIFO)')


def spine_cut(m, ys):
    """vertical bits crossing horizontal cuts inside the spine x range (2-pin legs, vertical run at the spine end)."""
    g = m['geo']
    by = {i.name: i for i in m['insts']}
    out = {}
    for y in ys:
        d = {}
        for bid, cl, bits, eps in m['buses']:
            if cl == 'tap':
                continue
            pts = [(by[i].cx, by[i].cy) for i, _ in eps]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                if min(y0, y1) < y < max(y0, y1):
                    xv = x1 if g['x_spine'] <= x1 <= g['x_arr_e'] else x0
                    if g['x_spine'] <= xv <= g['x_arr_e']:
                        d[cl] = d.get(cl, 0) + bits
        out[str(round(y))] = dict(sorted(d.items()), total=sum(d.values()))
    return out


def latency(points=(0, 1)):
    """F2 exposed cost in the unified model: +1 cycle on every ME op's instruction path (beat 2 trails beat 1 by
    one cycle, cut-through per hop) when the instruction is not prefetched; 0 when the static schedule fills the
    2-deep column FIFO during the previous op.  qwen_tp_point(4, 6144, board, 1.2 GHz, me_lat_extra 167, SU64) is
    the probe the clocking decision used."""
    import uarch_model as u
    r = {}
    for e in points:
        p = u.qwen_tp_point(4, 6144, 'board', clock_hz=u.PRODUCT_CLOCK_HZ, me_lat_extra=167 + e, su_width=64)
        r[e] = dict(cycles=p['cycles'], tok_s_b1=p['tokens_s_b1'])
    d = r[1]['cycles'] - r[0]['cycles']
    return dict(probe='uarch_model.qwen_tp_point(4, 6144, "board", PRODUCT_CLOCK_HZ, me_lat_extra=167(+1), su_width=64)',
                unified_model_sha256=hashlib.sha256((ROOT / 'tools/uarch_model.py').read_bytes()).hexdigest(),
                base=r[0], plus_one=r[1], me_ops_on_token_path=d,
                exposed_no_prefetch=dict(cycles_per_token=d, us=round(d / 1.2e3, 4),
                                         rate_delta_pct=round(100 * (r[1]['tok_s_b1'] / r[0]['tok_s_b1'] - 1), 4)),
                exposed_static_prefetch=dict(cycles_per_token=0,
                                             why='instruction words are static program fields (go is a separate wire); '
                                                 'the sequencer streams op i+1 into the 2-deep column FIFO while op i '
                                                 'runs (every ME op occupies >= 2 cycles), so only beats issued after a '
                                                 'pipeline drain are exposed'),
                f1_reset=dict(cycles_per_token=0, why='reset is not on the token path; release takes <= 44 pipelined '
                                                      'hops once at power-on'),
                adopted_figure='bound +%d cycles/token (%.3f%%) until the RTL prefetch is measured' %
                               (d, -100 * (r[1]['tok_s_b1'] / r[0]['tok_s_b1'] - 1)))


def write_def_regions(v, m, path):
    v.write_def_floorplan(m, path)
    txt = Path(path).read_text()
    head, rest = txt.split('REGIONS ', 1)
    n, rest2 = rest.split(' ;', 1)
    regs = [f'- {r["name"]} ( {round(r["rect"][0] * 1000)} {round(r["rect"][1] * 1000)} ) ( {round(r["rect"][2] * 1000)} '
            f'{round(r["rect"][3] * 1000)} ) + TYPE GUIDE ;' for r in m['clock_regions']]
    txt = head + f'REGIONS {int(n) + len(regs)} ;' + rest2.replace('END REGIONS', '\n'.join(regs) + '\nEND REGIONS', 1)
    Path(path).write_text(txt)


def record(v, m):
    die = m['die']
    by_kind = {}
    for r in m['clock_regions']:
        e = by_kind.setdefault(r['kind'], dict(count=0, max_extent_mm=0, over_5p25=[]))
        e['count'] += 1
        e['max_extent_mm'] = max(e['max_extent_mm'], r['extent_mm'])
        if not r['within_5p25']:
            e['over_5p25'].append(r['name'])
    return dict(schema=SCHEMA, tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                b2_generator_sha256=F.sha('tools/qwen_rom_fulldie.py'), b3_selection_sha256=F.sha('tools/qwen_rom_fulldie_b3.py'),
                die=die, vch_um=v.VCH, corridor_bits=v.CORRIDOR_BITS, tap_bits=v.TAP_BITS, band_repack=m['b3r2']['band'],
                instances=len(m['insts']), isa_bits=m['isa_bits'],
                group_map={k: v_ for k, v_ in m['b3r2']['groups'].items() if k in ('primary', 'overflow_groups', 'overflow_slab')},
                spine_parts=m['geo'].get('spine_parts_band') or m['geo']['spine_parts'],
                fifo=fifo_accounting(v, m), clock_regions_summary=by_kind, clock_regions=m['clock_regions'],
                spine_vertical_cut_bits=spine_cut(m, [3000, 8800, 12000, 18000, 25000]),
                link_stages=v.link_stages(m))


def summarize(work):
    """Per-layer GRT overflow (final congestion report) and 4x4-gcell window use/capacity (gcell_usage.txt:
    `L <layer> <row> cap/use ...`, capacity first)."""
    import gzip
    work = Path(work)
    log = (work / 'run.log').read_text(errors='replace')
    i = log.rfind('Final congestion report')
    layers = {}
    if i >= 0:
        for ln in log[i:].splitlines()[3:14]:
            f = ln.split()
            if len(f) >= 9 and (f[0].startswith('M') or f[0] == 'Total'):
                layers[f[0]] = dict(resource=int(f[1]), demand=int(f[2]), usage_pct=float(f[3].rstrip('%')),
                                    max_h=int(f[4]), max_v=int(f[6]), overflow=int(f[8]))
    gp = work / 'gcell_usage.txt'
    op = gzip.open if not gp.exists() else open
    gp = gp if gp.exists() else work / 'gcell_usage.txt.gz'
    gx = gy = None
    win = {}
    with op(gp, 'rt') as fh:
        for ln in fh:
            if ln.startswith('GRIDX'):
                gx = [int(x) for x in ln.split()[1].split(',')]
                continue
            if ln.startswith('GRIDY'):
                gy = [int(x) for x in ln.split()[1].split(',')]
                continue
            f = ln.split()
            layer, row = f[1], int(f[2])
            e = win.setdefault(layer, dict(windows=0, over=0, zero_cap_used=0, max_ratio=0.0, at=None, over_xy=[]))
            for ci, cu in enumerate(f[3:]):
                cap, use = (float(z) for z in cu.split('/'))
                e['windows'] += 1
                if cap == 0:
                    e['zero_cap_used'] += use > 0
                    continue
                r = use / cap
                if r > 1:
                    e['over'] += 1
                    e['over_xy'].append((gx[4 * ci] / 1000, gy[row] / 1000))
                if r > e['max_ratio']:
                    e['max_ratio'], e['at'] = r, [gx[4 * ci] / 1000, gy[row] / 1000]
    for e in win.values():
        xy = e.pop('over_xy')
        e['max_ratio'] = round(e['max_ratio'], 4)
        if xy:
            e['over_bbox_um'] = [min(x for x, _ in xy), min(y for _, y in xy), max(x for x, _ in xy), max(y for _, y in xy)]
    ex = (work / 'run.log.exit').read_text().strip() if (work / 'run.log.exit').exists() else None
    t = re.search(r'OT_TIME grt_s=(\d+)', log)
    rss = re.search(r'Maximum resident set size \(kbytes\): (\d+)', log)
    return dict(case=work.name, exit=ex, grt_s=int(t.group(1)) if t else None,
                peak_rss_gb=round(int(rss.group(1)) / 2**20, 1) if rss else None, layers=layers, windows=win)


def case_pdn(v, m, work, bump_um):
    """Real-technology die (legality, track assert, pin access) with power abstracts (VDD/VSS M7 + M8 rails on every
    element, tools/qwen_rom_fulldie_pg_r3.powered_lef) and the full-die pdn.tcl with one bump-aligned macro grid per
    instance (pg_r3.write_pdn at the bump pitch of the IR PASS case); run_pdn.tcl runs pdngen + check_power_grid."""
    man = v.case_real(m, work)
    M = v.masters(m, 1)
    pw = v.port_widths(m, 1)
    parts = []
    for name, mst in M.items():
        text, _ = PG.powered_lef(mst, 1, {q: pw.get((name, q), 0) for q in mst.order})
        parts.append(text)
    (work / 'elements.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(parts) +
                                       'END LIBRARY\n')
    def aligned(coverage, vp=bump_um):
        # case_ir(align=True) rule: largest pitch <= the coverage pitch with an odd count per per-net bump pitch,
        # on the 1 nm grid (lattice drift over the die <= 380 bumps x 7 x 0.0005 um = 1.3 um, inside a 20 um bump)
        raw = v.dn(0.48 / coverage, 0.160)
        n = math.ceil(vp / raw - 1e-9)
        n += (n % 2 == 0)
        return round(vp / n, 3)
    orig = PG.bump_pitch
    PG.bump_pitch = aligned
    try:
        meta = PG.write_pdn(work / 'pdn.tcl', m, bump_um)
    finally:
        PG.bump_pitch = orig
    # pdngen matches -instances as a pattern: the grid of t_0_1 claims t_0_10..t_0_19 (PDN-0182, then PDN-0217 on
    # the emptied grid; b3r2b_pdn run_pdn.log).  Define the macro grids longest name first so every grid keeps its
    # own instance.
    txt = (work / 'pdn.tcl').read_text().split('\n')
    head, blocks, cur = [], [], None
    for ln in txt:
        if ln.startswith('define_pdn_grid -macro'):
            cur = [ln]
            blocks.append(cur)
        elif cur is not None and ln.startswith(('add_pdn_stripe', 'add_pdn_connect')):
            cur.append(ln)
        elif ln:
            head.append(ln)
    key = lambda b: -len(re.search(r'-instances \{(\S+)\}', b[0]).group(1))
    blocks.sort(key=key)
    (work / 'pdn.tcl').write_text('\n'.join(head + [ln for b in blocks for ln in b]) + '\n')
    (work / 'run_pdn.tcl').write_text("""# full-die PDN with macro grids on the placed floorplan
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\\s+(\\d+)} $s -> r; puts "OTMEM $tag [expr {$r/1024}] MB [clock seconds]" }
read_db /work/floorplan.odb
mem read
set t0 [clock seconds]
if {[catch {source /work/pdn.tcl; pdngen} err]} { puts "OT_PDN FAIL $err" } else {
  set nsw 0; foreach net [[ord::get_db_block] getNets] { foreach sw [$net getSWires] { incr nsw [llength [$sw getWires]] } }
  puts "OT_PDN PASS special_shapes=$nsw" }
puts "OT_TIME pdn_s=[expr {[clock seconds]-$t0}]"
mem pdn
foreach net {VDD VSS} { if {[catch {check_power_grid -net $net} err]} { puts "OT_PGCHECK $net FAIL $err" } else { puts "OT_PGCHECK $net PASS" } }
mem check
write_db /work/floorplan_pdn.odb
""")
    man.update(case='a_pdn', bump_um=bump_um, macro_grids=len(meta), producer=__file__, die=m['die'],
               execution_order=['run.tcl', 'run_pdn.tcl'])
    (work / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    return man


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'grt', 'real', 'pdn', 'ir', 'latency', 'summary'])
    ap.add_argument('--window', default='tile_field')
    ap.add_argument('--vdd-pitch', type=float, default=63.64,
                    help='per-net bump pitch: 63.64 = 45 um array, every core bump power (the IR PASS cases ir_*_align_b45)')
    ap.add_argument('--enable-b3r2', action='store_true')
    ap.add_argument('--band', action='store_true', help='band-local port/scale slabs')
    ap.add_argument('--work', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--iters', type=int, default=5)
    ap.add_argument('--tag', default='b3r2')
    a = ap.parse_args(argv)
    if a.mode == 'summary':
        print(json.dumps(summarize(a.work), indent=1))
        return 0
    if a.mode == 'latency':
        print(json.dumps(latency(), indent=1))
        return 0
    v, m = selected(a.enable_b3r2, band=a.band)
    if a.mode == 'plan':
        out = a.out
        out.mkdir(parents=True, exist_ok=True)
        rec = record(v, m)
        (out / 'plan.json').write_text(json.dumps(rec, indent=1) + '\n')
        write_def_regions(v, m, out / 'floorplan.def')
        v.svg(m, out / 'floorplan.svg')
        print(json.dumps(dict(die=rec['die'], fifo=rec['fifo']['total_mm2'], regions=rec['clock_regions_summary'],
                              cut=rec['spine_vertical_cut_bits']), indent=1))
        return 0
    work = a.work.resolve()
    if work.exists() and any(work.iterdir()):
        raise SystemExit('refuse existing output')
    if a.mode == 'grt':
        man = v.case_grt(m, work, a.k, a.tag, a.iters)
        man.update(b3r2=record(v, m), producer=__file__)
        (work / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
        print(json.dumps({k: man[k] for k in ('tag', 'instances', 'bundle_pins', 'bundle_nets', 'wires')}))
    elif a.mode == 'ir':
        # the IR PASS recipe of the b2 floorplan (cases ir_*_align_b45): bump-aligned straps, every core bump power
        man = v.case_ir(m, work, a.window, align=True, vdd_pitch=a.vdd_pitch)
        man['b3r2'] = dict(producer=__file__, band=a.band, die=m['die'])
        (work / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
        print(json.dumps({k: man[k] for k in ('window', 'power_w', 'bump_sites')}))
    elif a.mode == 'pdn':
        print(json.dumps(case_pdn(v, m, work, a.vdd_pitch)))
    else:
        man = v.case_real(m, work)
        print(json.dumps(man))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
