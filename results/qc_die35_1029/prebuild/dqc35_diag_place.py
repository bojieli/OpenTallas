"""DIE-QC-35 diagnostic: run fixed_tree_provider with TrackRouter.place instrumented; on each failed
(non-dry) place, record the blocking shapes of the nearest candidate tracks. No behaviour change."""
import sys, json, collections, math
src, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, src+'/tools/die_plan'); sys.path.insert(0, src+'/tools/clk')
import die_clock_128 as C
orig = C.TrackRouter.place
rows = []; kinds = collections.Counter()
def place(self, layer, ideal, a0, a1, net, avoid=(), keep=None, dry=False):
    r = orig(self, layer, ideal, a0, a1, net, avoid=avoid, keep=keep, dry=dry)
    if r[0] is None and not dry:
        tr = self.tracks[layer]; p, o = tr['pitch_um'], tr['offset_um']
        k0 = round((ideal-o)/p); cand = []
        for k in range(k0-40, k0+41):
            c = round(o+k*p, 4)
            if keep is not None and not (keep[0]-1e-9 <= c <= keep[1]+1e-9): continue
            sh = C.seg_shapes(layer, c, a0, a1, net, self.nd, self.shield)
            hs = self.ix.hits(sh[0])
            hk = collections.Counter((self.ix.shapes[k_][2], self.ix.shapes[k_][1]) for k_, _ in hs)
            for key in hk: kinds[key] += 1
            if len(cand) < 12 and abs(c-ideal) < 1.7:
                cand.append(dict(c=c, metal_hits=[list(self.ix.shapes[k_])+[t] for k_, t in hs[:4]], n=len(hs),
                                 flank=C.flanked(self.pg, sh[0], C.flank_gap(self.nd))))
        if len(rows) < 400:
            rows.append(dict(layer=layer, ideal=ideal, span=[a0, a1], net=net, keep=keep, cands=cand))
    return r
C.TrackRouter.place = place
import fixed_tree_provider as F
try:
    F.main(sys.argv[3:])
finally:
    json.dump(dict(blocking_kind_counts={f'{a}|{b}': v for (a, b), v in kinds.most_common(40)}, rows=rows),
              open(out, 'w'), indent=1)
