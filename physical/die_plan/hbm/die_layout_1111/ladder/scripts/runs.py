"""bank-run extraction from a plan (old geometry) -> list of runs with fixed neighbour windows."""
import math
import lgeom as G


def bank_set(side):
    return {f'{side}_{b}' for b in G.BANKS}


def runs(P, S):
    """P = schema.Plan of the OLD plan.  Each run: dict(lane, side, width, i0, i1 (port index range replaced: ports
    i0..i1-1 are dropped), start=('bank', part) | ('win', part, die_face_of_neighbour, (lo, hi), port), end=...,
    old_cycles)."""
    out = []
    for lid, ln in P.lanes.items():
        hp = [P.ports[q] for q in ln['ports']]
        chain = [hp[0]['src']['part']] + [x['dst']['part'] for x in hp]
        for side in ('NE', 'NW'):
            B = bank_set(side)
            if not any(c in B for c in chain):
                continue
            k = 0
            while k < len(chain):
                if chain[k] not in B:
                    k += 1
                    continue
                j = k
                while j + 1 < len(chain) and chain[j + 1] in B:
                    j += 1
                # bank run chain[k..j]; ports touching it: k-1 (into chain[k]) .. j (out of chain[j])
                if k == 0:
                    start = ('bank', chain[0])
                    i0 = 0
                else:
                    pr = hp[k - 1]
                    segs = S.port_segments(pr)
                    lo = min(min(w) for _, _, w in segs)
                    hi = max(max(w) for _, _, w in segs)
                    start = ('win', chain[k - 1], pr['face'], (lo, hi), pr['id'])
                    i0 = k - 1
                if j == len(chain) - 1:
                    end = ('bank', chain[j])
                    i1 = len(hp)
                else:
                    pr = hp[j]
                    segs = S.port_segments(pr)
                    lo = min(min(w) for _, _, w in segs)
                    hi = max(max(w) for _, _, w in segs)
                    end = ('win', chain[j + 1], G.OPP[pr['face']], (lo, hi), pr['id'])
                    i1 = j + 1
                out.append(dict(lane=lid, side=side, width=hp[0]['width'], chain=chain, run=chain[k:j + 1],
                                i0=i0, i1=i1, start=start, end=end))
                k = j + 1
    return out


def win_point(P, part, nface, win):
    """die point at the centre of a neighbour-side window; nface = neighbour's die face toward the bank."""
    x0, y0, x1, y1 = P.rect(part)
    c = (win[0] + win[1]) / 2
    return {'E': (x1, c), 'W': (x0, c), 'N': (c, y1), 'S': (c, y0)}[nface]


def entry_bank(R, nface, win, pt, tol=0.5):
    """bank of the new geometry whose edge (facing the neighbour) holds the whole window, else None."""
    bf = G.OPP[nface]               # bank's die face toward the neighbour
    lo, hi = sorted(win)
    for b, (x0, y0, x1, y1) in R.items():
        line = {'E': x1, 'W': x0, 'N': y1, 'S': y0}[bf]
        c = pt[0] if bf in 'EW' else pt[1]
        if abs(line - c) > tol:
            continue
        a, z = (y0, y1) if bf in 'EW' else (x0, x1)
        if a - tol <= lo and hi <= z + tol:
            return b
    return None
