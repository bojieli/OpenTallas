"""DIE-HBM-10 hubplace legality check: per grid cell, pack the placed hard cores (plan outlines, no rotation) into the cell
interior (halo off every internal cut line, 0 at the hub outline, 2 um core spacing) with a deterministic MaxRects
bottom-left packer. Writes legal rects per core; a cell that does not pack is reported. Cores bigger than a cell keep
their (straddling) rect and are listed."""
import json, sys
SP = 2.0
def _cut(free, r):
    nf = []
    for (fx, fy, fw, fh) in free:
        if r[0] >= fx + fw or r[2] <= fx or r[1] >= fy + fh or r[3] <= fy: nf.append((fx, fy, fw, fh)); continue
        if r[0] > fx: nf.append((fx, fy, r[0] - fx, fh))
        if r[2] < fx + fw: nf.append((r[2], fy, fx + fw - r[2], fh))
        if r[1] > fy: nf.append((fx, fy, fw, r[1] - fy))
        if r[3] < fy + fh: nf.append((fx, r[3], fw, fy + fh - r[3]))
    return [a for a in nf if not any(b != a and b[0] <= a[0] and b[1] <= a[1] and b[0] + b[2] >= a[0] + a[2] and b[1] + b[3] >= a[1] + a[3] for b in nf)]
def pack(bw, bh, items, obst=()):
    """obst = rects (x0, y0, x1, y1) in box coordinates that no core may overlap (e.g. a fixed core bigger than a cell, +halo)"""
    free = [(0.0, 0.0, bw, bh)]; outp = {}
    for o in obst: free = _cut(free, o)
    for nm, w, h in sorted(items, key=lambda t: (-t[2], -t[1], t[0])):
        best = None
        for (fx, fy, fw, fh) in free:
            if w <= fw + 1e-6 and h <= fh + 1e-6:
                k = (fy, fx)
                if best is None or k < best[0]: best = (k, fx, fy)
        if best is None: return None
        _, x, y = best; outp[nm] = (x, y); r = (x, y, x + w + SP, y + h + SP); nf = []
        for (fx, fy, fw, fh) in free:
            if r[0] >= fx + fw or r[2] <= fx or r[1] >= fy + fh or r[3] <= fy: nf.append((fx, fy, fw, fh)); continue
            if r[0] > fx: nf.append((fx, fy, r[0] - fx, fh))
            if r[2] < fx + fw: nf.append((r[2], fy, fx + fw - r[2], fh))
            if r[1] > fy: nf.append((fx, fy, fw, r[1] - fy))
            if r[3] < fy + fh: nf.append((fx, r[3], fw, fy + fh - r[3]))
        free = [a for a in nf if not any(b != a and b[0] <= a[0] and b[1] <= a[1] and b[0] + b[2] >= a[0] + a[2] and b[1] + b[3] >= a[1] + a[3] for b in nf)]
    return outp
def main():
    d = json.load(open(sys.argv[1])); halo = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
    nx, ny = map(int, d["grid"].split("x")); res = {}
    for tn, r in d["types"].items():
        W, H = r["outline_um"]; cw, ch = W / nx, H / ny; S = r["A+B_net"]; cells = {}; big = []
        for h, rc in r["hrect"].items():
            c = S["place"].get("H/" + h)
            if c is None: continue
            w, hh = rc[2] - rc[0], rc[3] - rc[1]
            if w + 2 * halo > cw or hh + 2 * halo > ch: big.append(h); continue
            cells.setdefault(tuple(c), []).append((h, w, hh))
        rows = []; legal = {}
        for c in sorted(cells):
            x0 = c[0] * cw + (halo + 1 if c[0] > 0 else 0); x1 = (c[0] + 1) * cw - (halo + 1 if c[0] < nx - 1 else 0)
            y0 = c[1] * ch + (halo + 1 if c[1] > 0 else 0); y1 = (c[1] + 1) * ch - (halo + 1 if c[1] < ny - 1 else 0)
            ob = []
            for h in big:
                rc = r["hrect"][h]; pc = S["place"]["H/" + h]
                c0 = (min(nx - 1, max(0, int((rc[0] + rc[2]) / 2 / cw))), min(ny - 1, max(0, int((rc[1] + rc[3]) / 2 / ch))))
                dx, dy = (pc[0] - c0[0]) * cw, (pc[1] - c0[1]) * ch
                ob.append((rc[0] + dx - halo - x0, rc[1] + dy - halo - y0, rc[2] + dx + halo - x0, rc[3] + dy + halo - y0))
                if not (0 <= rc[0] + dx and rc[2] + dx <= W and 0 <= rc[1] + dy and rc[3] + dy <= H): print("BIG CORE OUTSIDE OUTLINE", tn, h)
            p = pack(x1 - x0, y1 - y0, cells[c], ob)
            a = sum(w * h for _, w, h in cells[c])
            rows.append(dict(cell=list(c), cores=len(cells[c]), fill=round(a / (cw * ch), 3), packed=p is not None))
            if p: legal.update({h: [x0 + x, y0 + y] for h, (x, y) in p.items()})
        res[tn] = dict(cells=rows, packed_cells=sum(x["packed"] for x in rows), n_cells=len(rows), big_straddling=big, legal_origin_um=legal)
        print(tn, "packed", res[tn]["packed_cells"], "/", len(rows), "unpacked", [x for x in rows if not x["packed"]], "big", big)
    json.dump(res, open(sys.argv[2], "w"), indent=1)

if __name__ == "__main__":
    main()
