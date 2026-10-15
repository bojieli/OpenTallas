#!/usr/bin/env python3
"""Cut the layout viewer's tile pack from a lossless extraction (lv_extract.py output).  Runs on the fleet host that
holds the DB (numpy + brotli; no OpenROAD), under ot-heavy:

    python3 lv_tile.py --raw <extract dir> --out <element>.lvp --element <id> [--quality 9] [--overview-only]

PACK (.lvp, schema opentallas.layout_viewer.pack.v1)
  bytes 0..23   magic b'OTLVPK01', u64 index offset, u64 index length (little endian)
  blobs         each blob brotli-compressed on its own; the index (brotli JSON {name: [offset, length]}) at the end.
  'header'      JSON: element, dbu, die / core, layer table with track grids, via-type table, master table, macros,
                the tile grid, per-tile shape counts, the raster pyramid and the DB truth summary (per-layer count,
                bbox and order-independent hash of the canonical expanded shape set)
  'names'       JSON: signal-type codes, bterm names / directions, net and instance counts
  'nn' / 'ni'   net / instance names, one per line, in index order (net i is line i - 1); 'nns' u8 signal-type code per net
                (served by name lookup / search on the server, never shipped whole to the client)
  'lint'        JSON: hierarchy-contract findings (lv_lint.py), each with layout geometry
  't/<tx>_<ty>/<s>'  geometry tile section (binary, see TILE below; one section each), leaf tiles of TILE_NM x TILE_NM;
                <s> = L<layer index> (that layer's rectangles), v (vias), c (std cells); the header lists each tile's sections
  'r/<l>/<ix>_<iy>'  density raster node of level l: one 256 x 256 u8 plane per non-empty layer (coverage 0..255)
  'cong'        routing-utilisation grid per routing layer (u8, percent of track capacity, signal wires)
  'ibb'         int32 columns over the instances: delta x0, delta y0, w, h, master (bbox for search / name lookup)
  'nbb'         int32 x 4 per net index (0 = none): bbox of its wires / vias / pins (search, net zoom)

TILE (little endian) : 'OTT1' i32 ox, oy (tile origin, absolute DBU) u32 size u16 nsec u16 0, then sections
  u8 type (1 rects, 2 vias, 3 cells) u8 layer u16 flags(bit0: vertical-major order) u32 count u32 nbytes, payload.
  Payloads are column streams of LEB128 varints (zz = zigzag):
  rects : zz(d major) zz(d minor | minor) w h zz(d net) kind clip [id for each clipped piece]
          major / minor = y0 / x0 on horizontal and cut layers, x0 / y0 on vertical layers (track-ordered delta coding);
          minor is a delta when the major coordinate repeats.  clip bits: 1 left 2 right 4 bottom 8 top were cut at a
          tile edge; a clipped piece carries the shape's id (its index in the layer's canonical order) so the decoder
          can re-join pieces into the exact DB rectangle.
  vias  : zz(dy) zz(dx | x) type zz(d net) kind              (owned by the tile holding the via origin)
  cells : zz(dy) zz(dx | x) orient master zz(d inst) flags, then the per-pin net list of every cell (zz d net)
          (std cells, owned by the tile holding the bbox centre; shapes come from the master table)
Coordinates in tiles are relative to the tile origin; everything is exact DBU (1 nm on ASAP7).
"""
import argparse, json, math, os, struct, sys, time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import brotli
except ImportError:  # hosts without the module: the orchestrator ships a wheel next to this script
    for p in Path(__file__).resolve().parent.glob('pylib*'):
        sys.path.insert(0, str(p))
    import brotli

TILE_NM = 25600
RASTER = 256
SCHEMA = 'opentallas.layout_viewer.pack.v1'
SERVER_SIDE = ('nn', 'ni', 'nns', 'ibb', 'nbb', 'names')
T0 = time.time()


def log(*a):
    print('[lv_tile %7.1fs]' % (time.time() - T0), *a, flush=True)


# ------------------------------------------------------------------ varints
def zz(v):
    v = np.asarray(v, dtype=np.int64)
    return ((v << 1) ^ (v >> 63)).astype(np.uint64)


def varint(u):
    """LEB128 of a uint64 array, vectorised"""
    u = np.asarray(u, dtype=np.uint64)
    if u.size == 0: return b''
    nb = np.ones(u.shape, dtype=np.int64)
    for k in range(1, 10):
        nb += (u >= np.uint64(1) << np.uint64(7 * k))
    pos = np.zeros(u.shape, dtype=np.int64); pos[1:] = np.cumsum(nb)[:-1]
    out = np.zeros(int(nb.sum()), dtype=np.uint8)
    for k in range(int(nb.max())):
        m = nb > k
        b = ((u[m] >> np.uint64(7 * k)) & np.uint64(0x7f)).astype(np.uint8)
        b |= np.where(nb[m] > k + 1, 0x80, 0).astype(np.uint8)
        out[pos[m] + k] = b
    return out.tobytes()


# ------------------------------------------------------------------ hash (identical in lv_decode.js)
M1_, M2_ = np.uint32(0x5bd1e995), np.uint32(0x85ebca6b)


def rect_hash(a):
    """a: (n, 5) int array layer, x0, y0, x1, y1 -> (h1, h2) uint32 sums (order independent)"""
    if len(a) == 0: return 0, 0
    a = a.astype(np.int64).astype(np.uint32)
    with np.errstate(over='ignore'):
        h1 = np.full(len(a), 0x9747b28c, dtype=np.uint32); h2 = np.full(len(a), 0x1b873593, dtype=np.uint32)
        for k in range(5):
            h1 = (h1 ^ a[:, k]) * M1_; h1 ^= h1 >> np.uint32(15)
            h2 = (h2 ^ a[:, k]) * M2_; h2 ^= h2 >> np.uint32(13)
        h1 ^= h1 >> np.uint32(16); h1 *= np.uint32(0x85ebca6b); h1 ^= h1 >> np.uint32(13)
        h2 ^= h2 >> np.uint32(16); h2 *= np.uint32(0xc2b2ae35); h2 ^= h2 >> np.uint32(16)
        return int(h1.astype(np.uint64).sum() & 0xffffffff), int(h2.astype(np.uint64).sum() & 0xffffffff)


# ------------------------------------------------------------------ orientation (odb dbTransform convention)
def orient_apply(code, x, y):
    if code == 0: return x, y
    if code == 1: return -y, x
    if code == 2: return -x, -y
    if code == 3: return y, -x
    if code == 4: return -x, y
    if code == 5: return -y, -x
    if code == 6: return x, -y
    return y, x


def expand_master(boxes, code, ox, oy):
    """master boxes (k, 4) -> placed boxes, the transform odb applies (rotate/mirror about the origin, then offset)"""
    xa, ya = orient_apply(code, boxes[:, 0], boxes[:, 1])
    xb, yb = orient_apply(code, boxes[:, 2], boxes[:, 3])
    return np.stack([np.minimum(xa, xb) + ox, np.minimum(ya, yb) + oy, np.maximum(xa, xb) + ox, np.maximum(ya, yb) + oy], 1)


# ------------------------------------------------------------------ load
def load(raw):
    raw = Path(raw)
    meta = json.loads((raw / 'meta.json').read_text())
    def arr(n, w):
        a = np.fromfile(raw / (n + '.i32'), dtype='<i4')
        return a.reshape(-1, w) if w else a
    return meta, arr('rects', 7), arr('vias', 5), arr('insts', 9), arr('inets', 0), (arr('truth', 5) if (raw / 'truth.i32').exists() else None)


def macro_rects(meta, insts, inets):
    """expanded pin / OBS rectangles of every macro instance: (n, 7) like rects.i32, kind 7 macro pin, 8 macro OBS"""
    masters = meta['masters']
    npins = np.array([len(m['pins']) for m in masters], dtype=np.int64)
    ioff = np.zeros(len(insts) + 1, dtype=np.int64); ioff[1:] = np.cumsum(npins[insts[:, 3]])
    out = []
    for i in np.nonzero(insts[:, 8] & 1)[0]:
        m = masters[insts[i, 3]]
        if not m['boxes']: continue
        b = np.array(m['boxes'], dtype=np.int64)
        pb = expand_master(b[:, 1:5], int(insts[i, 2]), int(insts[i, 0]), int(insts[i, 1]))
        pins = b[:, 5]
        net = np.where(pins >= 0, inets[ioff[i] + np.maximum(pins, 0)] if len(inets) else 0, 0)
        out.append(np.column_stack([b[:, 0], pb, net, np.where(pins >= 0, 7, 8)]))
    return np.concatenate(out) if out else np.zeros((0, 7), dtype=np.int64)


def cell_rects(meta, insts):
    """expanded shapes of every std-cell instance (for rasters only; the tiles carry cells, not shapes)"""
    masters = meta['masters']
    out = []
    sc = insts[(insts[:, 8] & 1) == 0]
    for mi in np.unique(sc[:, 3]):
        m = masters[mi]
        if not m['boxes']: continue
        b = np.array(m['boxes'], dtype=np.int64)
        sel = sc[sc[:, 3] == mi]
        for code in np.unique(sel[:, 2]):
            s2 = sel[sel[:, 2] == code]
            for bb in b:
                pb = expand_master(bb[None, 1:5].repeat(len(s2), 0), int(code), s2[:, 0], s2[:, 1])
                out.append(np.column_stack([np.full(len(s2), bb[0]), pb]))
    return np.concatenate(out) if out else np.zeros((0, 5), dtype=np.int64)


# ------------------------------------------------------------------ rasters
def coverage(rects, ox, oy, px, gx, gy):
    """exact per-pixel area coverage (fraction) of a rect list on a gx x gy grid of px DBU pixels from (ox, oy); the sum
    over rects (overlaps add), clamped by the caller.  Each corner deposits its 2x2 bilinear impulse; two cumulative sums
    per axis turn the impulses into the ramp products whose 2-D difference is the covered area."""
    if len(rects) == 0: return np.zeros((gy, gx))
    X0 = (rects[:, 0] - ox) / px; Y0 = (rects[:, 1] - oy) / px; X1 = (rects[:, 2] - ox) / px; Y1 = (rects[:, 3] - oy) / px
    X0, X1 = np.clip(X0, 0, gx), np.clip(X1, 0, gx); Y0, Y1 = np.clip(Y0, 0, gy), np.clip(Y1, 0, gy)
    W, H = gx + 3, gy + 3
    acc = np.zeros(W * H)
    for xs, sx in ((X0, 1.0), (X1, -1.0)):
        fx = np.floor(xs); ax = xs - fx; ix = fx.astype(np.int64)
        for ys, sy in ((Y0, 1.0), (Y1, -1.0)):
            fy = np.floor(ys); ay = ys - fy; iy = fy.astype(np.int64)
            s = sx * sy
            for dx, wx in ((1, 1 - ax), (2, ax)):
                for dy, wy in ((1, 1 - ay), (2, ay)):
                    acc += np.bincount((iy + dy) * W + (ix + dx), weights=s * wx * wy, minlength=W * H)
    A = acc.reshape(H, W)
    A = np.cumsum(np.cumsum(A, 1), 1); A = np.cumsum(np.cumsum(A, 0), 0)
    F = A[:gy + 1, :gx + 1]           # F[j, i] = covered area inside [0, i] x [0, j] (pixel units)
    return F[1:, 1:] - F[:-1, 1:] - F[1:, :-1] + F[:-1, :-1]


def rasters(meta, shapes, nlay, die, L):
    """density pyramid: level l nodes cover E / 2^l, RASTER px each; finest raster level = L - 2 (0.4 um px at 25.6 um
    tiles).  shapes (n, 5) layer, x0, y0, x1, y1.  Returns {(l, ix, iy): bytes}, level table"""
    E = TILE_NM << L
    Lr = max(0, L - 2)
    G = RASTER << Lr
    px = E / G
    ox, oy = die[0], die[1]
    gx = min(G, int(math.ceil((die[2] - die[0]) / px))); gy = min(G, int(math.ceil((die[3] - die[1]) / px)))
    # pad to whole nodes
    nnx, nny = -(-gx // RASTER), -(-gy // RASTER)
    GX, GY = nnx * RASTER, nny * RASTER
    planes = np.zeros((nlay, GY, GX), dtype=np.float32)
    for li in range(nlay):
        r = shapes[shapes[:, 0] == li][:, 1:5]
        if len(r): planes[li, :gy, :gx] = np.clip(coverage(r, ox, oy, px, gx, gy), 0, 1)
    out, levels = {}, []
    cur = planes
    for l in range(Lr, -1, -1):
        ny_, nx_ = cur.shape[1] // RASTER, cur.shape[2] // RASTER
        present = []
        for iy in range(ny_):
            for ix in range(nx_):
                blk = cur[:, iy * RASTER:(iy + 1) * RASTER, ix * RASTER:(ix + 1) * RASTER]
                q = np.round(blk * 255).astype(np.uint8)
                mask = [li for li in range(nlay) if q[li].any()]
                if not mask: continue
                filt = q[mask].astype(np.int16)
                filt[:, :, 1:] = (filt[:, :, 1:] - q[mask][:, :, :-1].astype(np.int16)) & 0xff   # horizontal delta filter
                hdr = struct.pack('<4sHH', b'OTR1', len(mask), RASTER) + bytes(mask)
                out['r/%d/%d_%d' % (l, ix, iy)] = hdr + filt.astype(np.uint8).tobytes()
                present.append([ix, iy])
        levels.append(dict(level=l, node_nm=E / (1 << l), px_nm=E / (1 << l) / RASTER, nx=nx_, ny=ny_, nodes=present))
        if l == 0: break
        # 2x2 average down; pad to an even node count
        c = cur
        if (c.shape[1] // RASTER) % 2: c = np.concatenate([c, np.zeros((nlay, RASTER, c.shape[2]), np.float32)], 1)
        if (c.shape[2] // RASTER) % 2: c = np.concatenate([c, np.zeros((nlay, c.shape[1], RASTER), np.float32)], 2)
        cur = c.reshape(nlay, c.shape[1] // 2, 2, c.shape[2] // 2, 2).mean((2, 4))
    return out, dict(E=E, finest=Lr, raster=RASTER, levels=levels[::-1])


def congestion(meta, rects, vias_exp, die, nlay):
    """routing utilisation per routing layer: signal-wire track usage over track capacity per bin
    (coverage x pitch / width; 100 = every track of the bin fully used along the bin)"""
    W, H = die[2] - die[0], die[3] - die[1]
    bin_nm = max(1080, int(math.ceil(max(W, H) / 384.0 / 108.0)) * 108)
    gx, gy = -(-W // bin_nm), -(-H // bin_nm)
    planes, info = [], []
    for li, l in enumerate(meta['layers']):
        if l['type'] != 'ROUTING' or not l.get('pitch'): continue
        r = rects[(rects[:, 0] == li) & (rects[:, 6] == 0)][:, 1:5]
        cov = coverage(r, die[0], die[1], bin_nm, gx, gy) if len(r) else np.zeros((gy, gx))
        util = cov * l['pitch'] / max(1, l['width'])
        q = np.clip(np.round(util * 100), 0, 255).astype(np.uint8)
        planes.append(q); info.append(dict(layer=li, name=l['name'], p50=float(np.percentile(util, 50) * 100), p99=float(np.percentile(util, 99) * 100),
                                           max=float(util.max() * 100), over100=int((util > 1.0).sum())))
    blob = struct.pack('<4sHHHI', b'OTC1', len(planes), gx, gy, bin_nm) + bytes([i['layer'] for i in info]) + b''.join(p.tobytes() for p in planes)
    return blob, dict(bin_nm=bin_nm, nx=int(gx), ny=int(gy), layers=info,
                      basis='signal-wire track utilisation per bin: routed signal metal area x layer pitch / wire width / bin area '
                            '(100 = every track of the bin used along its full length); special nets excluded')


# ------------------------------------------------------------------ tiles
def build_tiles(meta, rects, vias, insts, inets, mrects, quality):
    die = meta['die']; ox, oy = die[0], die[1]
    S = TILE_NM
    nx = max(1, -(-(die[2] - die[0]) // S)); ny = max(1, -(-(die[3] - die[1]) // S))
    nlay = len(meta['layers'])
    vert = np.array([l.get('dir') == 'VERTICAL' for l in meta['layers']])
    allr = np.concatenate([rects, mrects]) if len(mrects) else rects
    # canonical per-layer order (= shape id): sort by layer, then the same key as the tile order
    key_major = np.where(vert[allr[:, 0]], allr[:, 1], allr[:, 2]); key_minor = np.where(vert[allr[:, 0]], allr[:, 2], allr[:, 1])
    order = np.lexsort((allr[:, 6], allr[:, 5], allr[:, 4], allr[:, 3], key_minor, key_major, allr[:, 0]))
    allr = allr[order]
    lay_start = np.searchsorted(allr[:, 0], np.arange(nlay + 1))
    sid = np.arange(len(allr)) - lay_start[allr[:, 0]]
    # tile ranges; edge tiles extend to infinity so nothing outside the die is cut away
    def trange(lo, hi, o, n):
        a = np.clip((lo - o) // S, 0, n - 1); b = np.clip((np.maximum(hi - 1, lo) - o) // S, 0, n - 1)
        return a, b
    tx0, tx1 = trange(allr[:, 1], allr[:, 3], ox, nx); ty0, ty1 = trange(allr[:, 2], allr[:, 4], oy, ny)
    nxs, nys = tx1 - tx0 + 1, ty1 - ty0 + 1
    rep = nxs * nys
    idx = np.repeat(np.arange(len(allr)), rep)
    off = np.arange(len(idx)) - np.repeat(np.cumsum(rep) - rep, rep)
    tx = tx0[idx] + off % nxs[idx]; ty = ty0[idx] + off // nxs[idx]
    P = allr[idx].copy()
    big = np.int64(1) << 40
    lx = np.where(tx > 0, ox + tx * S, -big); hx = np.where(tx < nx - 1, ox + (tx + 1) * S, big)
    ly = np.where(ty > 0, oy + ty * S, -big); hy = np.where(ty < ny - 1, oy + (ty + 1) * S, big)
    clip = (P[:, 1] < lx).astype(np.int64) | ((P[:, 3] > hx).astype(np.int64) << 1) | ((P[:, 2] < ly).astype(np.int64) << 2) | ((P[:, 4] > hy).astype(np.int64) << 3)
    P[:, 1] = np.maximum(P[:, 1], lx); P[:, 3] = np.minimum(P[:, 3], hx); P[:, 2] = np.maximum(P[:, 2], ly); P[:, 4] = np.minimum(P[:, 4], hy)
    P[:, 3] = np.maximum(P[:, 3], P[:, 1]); P[:, 4] = np.maximum(P[:, 4], P[:, 2])   # degenerate pieces stay degenerate
    psid = sid[idx]
    tid = ty * nx + tx
    # vias: owner = tile of the origin
    vtx = np.clip((vias[:, 0] - ox) // S, 0, nx - 1); vty = np.clip((vias[:, 1] - oy) // S, 0, ny - 1); vtid = vty * nx + vtx
    # std cells: owner = tile of the bbox centre
    masters = meta['masters']
    npins = np.array([len(m['pins']) for m in masters], dtype=np.int64)
    ioff = np.zeros(len(insts) + 1, dtype=np.int64); ioff[1:] = np.cumsum(npins[insts[:, 3]])
    std = np.nonzero((insts[:, 8] & 1) == 0)[0]
    ccx = (insts[std, 4] + insts[std, 6]) // 2; ccy = (insts[std, 5] + insts[std, 7]) // 2
    ctid = np.clip((ccy - oy) // S, 0, ny - 1) * nx + np.clip((ccx - ox) // S, 0, nx - 1)
    # group
    po = np.lexsort((psid, P[:, 0], tid)); P, clip, psid, tid = P[po], clip[po], psid[po], tid[po]
    vo = np.argsort(vtid, kind='stable'); V, vtid = vias[vo], vtid[vo]
    co = np.argsort(ctid, kind='stable'); C, ctid = std[co], ctid[co]
    pb = np.searchsorted(tid, np.arange(nx * ny + 1)); vb = np.searchsorted(vtid, np.arange(nx * ny + 1)); cb = np.searchsorted(ctid, np.arange(nx * ny + 1))
    blobs, index = {}, []
    raw_total = 0
    for t in range(nx * ny):
        txi, tyi = t % nx, t // nx
        tox, toy = ox + txi * S, oy + tyi * S
        secs = []
        counts = [0] * nlay
        p = P[pb[t]:pb[t + 1]]; pc = clip[pb[t]:pb[t + 1]]; ps = psid[pb[t]:pb[t + 1]]
        if len(p):
            lb = np.searchsorted(p[:, 0], np.arange(nlay + 1))
            for li in range(nlay):
                a, b = lb[li], lb[li + 1]
                if a == b: continue
                q, qc, qs = p[a:b], pc[a:b], ps[a:b]
                v = bool(vert[li])
                maj = (q[:, 1] if v else q[:, 2]) - (tox if v else toy)
                mnr = (q[:, 2] if v else q[:, 1]) - (toy if v else tox)
                o = np.lexsort((q[:, 4] - q[:, 2], q[:, 3] - q[:, 1], mnr, maj)); q, qc, qs, maj, mnr = q[o], qc[o], qs[o], maj[o], mnr[o]
                dmaj = np.diff(maj, prepend=0)
                same = np.concatenate([[False], dmaj[1:] == 0])
                dmnr = np.where(same, mnr - np.concatenate([[0], mnr[:-1]]), mnr)
                net = q[:, 5]; dnet = np.diff(net, prepend=0)
                body = b''.join([varint(zz(dmaj)), varint(zz(dmnr)), varint(q[:, 3] - q[:, 1]), varint(q[:, 4] - q[:, 2]),
                                 varint(zz(dnet)), varint(q[:, 6]), varint(qc), varint(qs[qc != 0])])
                secs.append(('L%d' % li, struct.pack('<BBHII', 1, li, 1 if v else 0, len(q), len(body)) + body))
                counts[li] = int(len(q))
        v = V[vb[t]:vb[t + 1]]
        if len(v):
            o = np.lexsort((v[:, 2], v[:, 0], v[:, 1])); v = v[o]
            y = v[:, 1] - toy; x = v[:, 0] - tox
            dy = np.diff(y, prepend=0); same = np.concatenate([[False], dy[1:] == 0])
            dx = np.where(same, x - np.concatenate([[0], x[:-1]]), x)
            body = b''.join([varint(zz(dy)), varint(zz(dx)), varint(v[:, 2]), varint(zz(np.diff(v[:, 3], prepend=0))), varint(v[:, 4])])
            secs.append(('v', struct.pack('<BBHII', 2, 255, 0, len(v), len(body)) + body))
        c = C[cb[t]:cb[t + 1]]
        if len(c):
            I = insts[c]
            o = np.lexsort((c, I[:, 0], I[:, 1])); c, I = c[o], I[o]
            y = I[:, 1] - toy; x = I[:, 0] - tox
            dy = np.diff(y, prepend=0); same = np.concatenate([[False], dy[1:] == 0])
            dx = np.where(same, x - np.concatenate([[0], x[:-1]]), x)
            pn = npins[I[:, 3]]
            if pn.sum():
                sel = np.repeat(ioff[c], pn) + (np.arange(pn.sum()) - np.repeat(np.cumsum(pn) - pn, pn))
                nets = inets[sel]
            else:
                nets = np.zeros(0, np.int64)
            body = b''.join([varint(zz(dy)), varint(zz(dx)), varint(I[:, 2]), varint(I[:, 3]), varint(zz(np.diff(c, prepend=0))), varint(I[:, 8]),
                             varint(zz(np.diff(nets, prepend=0)))])
            secs.append(('c', struct.pack('<BBHII', 3, 255, 0, len(c), len(body)) + body))
        if not secs: continue
        # one blob per section (per layer / vias / cells): the client fetches only the layers it shows
        for nm, sec in secs:
            raw = struct.pack('<4siiIHH', b'OTT1', int(tox), int(toy), S, 1, 0) + sec
            raw_total += len(raw)
            blobs['t/%d_%d/%s' % (txi, tyi, nm)] = raw
        nphys = int((insts[C[cb[t]:cb[t + 1]], 8] & 4).astype(bool).sum())
        index.append(dict(x=txi, y=tyi, n=counts, v=int(vb[t + 1] - vb[t]), c=int(cb[t + 1] - cb[t]) - nphys, cp=nphys, s=[nm for nm, _ in secs]))
    L = int(math.ceil(math.log2(max(nx, ny)))) if max(nx, ny) > 1 else 0
    return blobs, dict(size=S, ox=ox, oy=oy, nx=int(nx), ny=int(ny), L=L, tiles=index, raw_bytes=raw_total,
                       pieces=int(len(P)), shapes=int(len(allr)))


def write_pack(path, blobs, quality):
    tmp = Path(str(path) + '.tmp')
    index = {}
    with open(tmp, 'wb') as fh:
        fh.write(b'\0' * 24)
        for k, v in blobs.items():
            if isinstance(v, (dict, list)): v = json.dumps(v, separators=(',', ':')).encode()
            q = min(quality, 4) if k in SERVER_SIDE else quality   # name tables / search sides never leave the server
            c = brotli.compress(v, quality=q, lgwin=22)
            index[k] = [fh.tell(), len(c), len(v)]
            fh.write(c)
        io = fh.tell()
        ib = brotli.compress(json.dumps(index, separators=(',', ':')).encode(), quality=quality)
        fh.write(ib)
        fh.seek(0); fh.write(struct.pack('<8sQQ', b'OTLVPK01', io, len(ib)))
    os.replace(tmp, path)
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--raw', required=True); ap.add_argument('--out', required=True); ap.add_argument('--element', required=True)
    ap.add_argument('--quality', type=int, default=9); ap.add_argument('--overview-only', action='store_true')
    ap.add_argument('--meta-json', help='extra JSON merged into the header (job, host, db)')
    a = ap.parse_args()
    meta, rects, vias, insts, inets, truth = load(a.raw)
    die = meta['die']; nlay = len(meta['layers'])
    log('loaded: %d rects %d vias %d insts %d truth' % (len(rects), len(vias), len(insts), 0 if truth is None else len(truth)))
    mrects = macro_rects(meta, insts, inets)
    blobs = {}
    if not a.overview_only:
        tb, grid = build_tiles(meta, rects, vias, insts, inets, mrects, a.quality)
        blobs.update(tb)
        log('tiles: %d non-empty of %d x %d, %d pieces of %d shapes, %.1f MB raw' % (len(tb), grid['nx'], grid['ny'], grid['pieces'], grid['shapes'], grid['raw_bytes'] / 1e6))
    else:
        S = TILE_NM; nx = max(1, -(-(die[2] - die[0]) // S)); ny = max(1, -(-(die[3] - die[1]) // S))
        grid = dict(size=S, ox=die[0], oy=die[1], nx=int(nx), ny=int(ny), L=int(math.ceil(math.log2(max(nx, ny)))) if max(nx, ny) > 1 else 0, tiles=None)
    # shapes for rasters: the DB truth set when present, else our own expansion
    if truth is not None and len(truth):
        shapes = truth
    else:
        vt = meta['vias']
        vexp = [np.column_stack([np.full(len(vias), b[0]), vias[:, 0] + b[1], vias[:, 1] + b[2], vias[:, 0] + b[3], vias[:, 1] + b[4]])[vias[:, 2] == k]
                for k, v in enumerate(vt) for b in v['boxes']]
        shapes = np.concatenate([rects[:, :5], mrects[:, :5]] + vexp + [cell_rects(meta, insts)])
    rb, rinfo = rasters(meta, shapes, nlay, die, grid['L'])
    if a.overview_only:
        keep = {k: v for k, v in rb.items() if int(k.split('/')[1]) <= 1}
        rb = keep
    blobs.update(rb)
    log('rasters: %d nodes, finest level %d' % (len(rb), rinfo['finest']))
    cblob, cinfo = congestion(meta, rects, None, die, nlay)
    blobs['cong'] = cblob
    # truth summary
    tsum = None
    if truth is not None:
        tsum = []
        for li in range(nlay):
            t = truth[truth[:, 0] == li]
            h = rect_hash(t)
            tsum.append(dict(n=int(len(t)), bbox=[int(t[:, 1].min()), int(t[:, 2].min()), int(t[:, 3].max()), int(t[:, 4].max())] if len(t) else None, h=list(h)))
    try:
        import lv_lint
        lint = lv_lint.lint(meta, rects, vias, insts, inets, mrects)
    except Exception as e:  # never lose the pack over the overlay
        import traceback
        lint = dict(error='%s: %s' % (type(e).__name__, e), trace=traceback.format_exc()[-1200:], findings=[])
    blobs['lint'] = lint
    log('lint: %d findings' % len(lint.get('findings', [])))
    # search side tables: instance bbox + master, net bbox (wires, vias, pins)
    # columns (delta x0, delta y0, w, h, master) compress ~4x better than rows: placement order is spatially coherent
    cols = [np.diff(insts[:, 4], prepend=0), np.diff(insts[:, 5], prepend=0), insts[:, 6] - insts[:, 4], insts[:, 7] - insts[:, 5], insts[:, 3]]
    blobs['ibb'] = b''.join(np.ascontiguousarray(c_.astype('<i4')).tobytes() for c_ in cols)
    nn = len(meta['nets']) + 1
    g = np.concatenate([rects[:, [5, 1, 2, 3, 4]], np.column_stack([vias[:, 3], vias[:, 0], vias[:, 1], vias[:, 0], vias[:, 1]])])
    nbb = np.zeros((nn, 4), dtype=np.int64); nbb[:, 0] = nbb[:, 1] = 1 << 40; nbb[:, 2] = nbb[:, 3] = -(1 << 40)
    np.minimum.at(nbb[:, 0], g[:, 0], g[:, 1]); np.minimum.at(nbb[:, 1], g[:, 0], g[:, 2])
    np.maximum.at(nbb[:, 2], g[:, 0], g[:, 3]); np.maximum.at(nbb[:, 3], g[:, 0], g[:, 4])
    nbb[nbb[:, 0] > nbb[:, 2]] = 0
    blobs['nbb'] = nbb.astype('<i4').tobytes()
    sigs = sorted(set(meta['net_sig']))
    blobs['names'] = dict(sig_codes=sigs, bterms=meta['bterms'], bterm_io=meta['bterm_io'], n_nets=len(meta['nets']), n_insts=len(meta['insts']))
    blobs['nn'] = '\n'.join(meta['nets']).encode() + b'\n'
    blobs['ni'] = '\n'.join(meta['insts']).encode() + b'\n'
    sc = {s_: k for k, s_ in enumerate(sigs)}
    blobs['nns'] = bytes(sc[s_] for s_ in meta['net_sig'])
    lcount = np.bincount(rects[:, 0], minlength=nlay).tolist()
    header = dict(schema=SCHEMA, element=a.element, top=meta['top'], db=meta['db'], dbu=meta['dbu'], die=die, core=meta['core'],
                  layers=meta['layers'], vias=meta['vias'], masters=meta['masters'], macros=meta['macros'], orients=meta['orients'],
                  grid=grid, raster=rinfo, congestion=cinfo, truth=tsum, overview_only=bool(a.overview_only),
                  counts=dict(meta['counts'], layer_rects=lcount, macro_rects=int(len(mrects)), nets=len(meta['nets']),
                              insts=len(meta['insts']), bterms=len(meta['bterms'])),
                  lint_summary=dict(n=len(lint.get('findings', [])), fail=sum(1 for f in lint.get('findings', []) if f.get('sev') == 'FAIL'),
                                    error=lint.get('error')),
                  made=time.strftime('%Y-%m-%dT%H:%M:%S%z'), extract_seconds=meta.get('seconds'))
    if a.meta_json: header.update(json.loads(a.meta_json))
    blobs = dict([('header', header)] + list(blobs.items()))
    idx = write_pack(a.out, blobs, a.quality)
    tot = sum(v[1] for v in idx.values())
    log('pack %s: %d blobs, %.2f MB (header %.0f kB)' % (a.out, len(idx), tot / 1e6, idx['header'][1] / 1e3))


if __name__ == '__main__':
    main()
