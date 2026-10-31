#!/usr/bin/env python3
"""DIE-HBM-42 d41v (from DIE-HBM-41 lane_e.py): V-A hop-chain lanes for the SFU/IDX pairs (COORD 16:0x), chains = DIE-HBM-37 va_route_lengths.tsv NW paths. Original doc: DIE-HBM-41 d41b: hub<->spb0 SerDes flit hop-chain lanes (12.13 far link as a registered hop chain).
NW lanes: lane_add.Builder (unchanged tool) on the NW rows with the shared-type guard lifted (the only shared type on
the chain is q_spb1, NW_spb1 R0 / NE_spb1 MY); NE lanes: exact die mirror x' = W - x of each NW lane (same bus /
slot names as the plan's existing mirror lanes, e.g. L120/L120m): shared types reuse the NW slot (type-frame identity
asserted), own NE types get the mirrored bus / slot (+ regs) in their own frame.
    lane_e.py PLANDIR rows.json OUTDIR FIRST_ID
"""
import copy, math, json, os, shutil, sys, hashlib
from pathlib import Path
T = '/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan'
sys.path.insert(0, T)
import schema as S, lane_add as LA

def sha12(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]

def main():
    plan, rows, out, first = Path(sys.argv[1]), json.load(open(sys.argv[2]))['rows'], Path(sys.argv[3]), int(sys.argv[4])
    raw = json.loads((plan / 'die_plan.json').read_text())
    W = float(raw['die']['outline_um'][0])
    va = {}
    for ln in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'va_route_lengths.tsv')).read().splitlines()[1:]:
        f = ln.split('\t'); va[(f[0], f[1])] = f[6].split('>')
    nw = [r for r in rows if r['src'].startswith('NW_') and r['dst'].startswith('NW_')]
    B = LA.Builder(raw, near_um=1e9, max_hops=14, first_id=first)
    B.shared = set()
    _sf = LA.Builder.stations_for
    def _stations_for(self, part, din, win_in, dout, win_out):
        k, seg, L = _sf(self, part, din, win_in, dout, win_out)
        return k + int(math.ceil(k * getattr(self, '_infl', 0.0))), seg, L
    LA.Builder.stations_for = _stations_for

    import numpy as _np, station_resite as _SR, check as _C
    def _resite(self, chain, slots, start, end):
        """DIE-HBM-42: even stations along the chain's own z-route (no straight-line ideal), each snapped to the
        nearest macro-free 4.32 lattice point (+halo) of the partition it falls in; None if a hop > reach."""
        P, G, H = self.P, _SR.G, _SR.HALO
        pts_seq = [start]
        segs = []
        for sl in slots:
            part = sl[0]
            _, seg, L = self.stations_for(part, LA.OPP[sl[2]], sl[3], sl[5], sl[6])
            segs.append((part, seg, L))
        R = self.reach - 0.5
        out = [[] for _ in slots]
        prev = tuple(start)
        md = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
        for k, (part, seg, L) in enumerate(segs):
            x0, y0, x1, y1 = P.rect(part)
            xs = _np.arange(_np.ceil((x0 + H) / G) * G, x1 - H, G); ys = _np.arange(_np.ceil((y0 + H) / G) * G, y1 - H, G)
            free = _np.ones((len(xs), len(ys)), bool)
            for bx0, by0, bx1, by1 in S.placed_macro_boxes(P.ptype(part), halo=H).values():
                c0, c1 = P.to_die(part, (bx0, by0)), P.to_die(part, (bx1, by1))
                ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
                free &= ~((xs[:, None] > ux0 - 1e-6) & (xs[:, None] < ux1 + 1e-6) & (ys[None, :] > uy0 - 1e-6) & (ys[None, :] < uy1 + 1e-6))
            if not free.any():
                return None
            tgt = segs[k + 1][1][0] if k + 1 < len(segs) else end
            X0, Y0 = float(xs[0]), float(ys[0])
            aa = (prev[0] - X0, prev[1] - Y0); bb = (tgt[0] - X0, tgt[1] - Y0)
            dmin = md(prev, tgt)
            regs = None
            m0 = max(1, int(math.ceil(L / self.smax - 1e-9)), int(math.ceil(dmin / R)) - 1 + (1 if k + 1 < len(segs) else 0))
            for m in range(m0, m0 + 12):
                regs = _SR.route(free, aa, bb, m, R)
                if regs is not None:
                    break
            if regs is None:
                if os.environ.get("VADBG"): print("NOROUTE", part, prev, tgt)
                return None
            out[k] = [(round(x + X0, 4), round(y + Y0, 4)) for x, y in regs]
            prev = out[k][-1]
        pts = [start] + [r for o in out for r in o] + [end]
        if os.environ.get("VADBG"): print("PTS", [len(o) for o in out], [round(md(p, q)) for p, q in zip(pts, pts[1:])], [round(sl[10]) for sl in slots])
        if max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])) > self.reach + 1e-6:
            return None
        for sl, r in zip(slots, out):
            if sl[10] / len(r) > self.smax + 1e-6:
                return None
        return out
    LA.Builder.resite = _resite
    built, failed = [], []
    for r in sorted(nw, key=lambda r: -int(r['unplanned_bits'])):
        a_, b_, bits = r['src'], r['dst'], int(r['unplanned_bits'])
        chain = va.get((a_, b_)) or B.path(a_, b_)
        if not chain or 'root' in chain:
            failed.append(dict(src=a_, dst=b_, bits=bits, why='no V-A chain')); continue
        ok = False; why = []
        for infl, k in [(f, k) for f in (0.0,) for k in (1, 2, 3, 4, 6)]:
            B._infl = infl
            saved = copy.deepcopy(B.raw); st = copy.deepcopy(B.taken); ids, nx = dict(B.ids), B.next_id
            parts = [bits // k + (1 if i < bits % k else 0) for i in range(k)]
            got = []
            for i, w in enumerate(parts):
                r1 = B.build_one(a_, b_, w, chain, 'path', None, record=False, part=i)
                if r1 is None: why.append(f'k={k}: {B._why}'); break
                got.append(r1)
            if len(got) == k:
                for g in got: g['station_inflation'] = infl
                mx = max(g['cycles'] for g in got)
                for g in got:
                    e = B.raw['latency']['lanes'][g['lane']]; e['pad'] = mx - e['natural']; e['cycles'] = mx
                    g['padded_to'] = mx; g['split'] = k
                built.extend(got); ok = True; break
            B.raw.clear(); B.raw.update(saved); B.P = S.Plan(B.raw); B.taken = st; B.ids, B.next_id = ids, nx
        if not ok:
            failed.append(dict(src=a_, dst=b_, bits=bits, chain=chain, why=why[-3:]))
        print('PAIR', a_, b_, bits, chain, 'OK' if ok else 'FAIL', (why[-1] if not ok else [(g['lane'], g['cycles']) for g in got]), flush=True)
    B.report['built'] = built; B.report['failed'] = failed
    rep = dict(base=str(plan), base_sha=sha12(plan / 'die_plan.json'), nw=B.report, ne=[])
    raw = B.raw; P = S.Plan(raw)
    flipo = {'lsb_low': 'lsb_high', 'lsb_high': 'lsb_low'}
    for b in B.report['built']:
        lid = b['lane']; mid = lid + 'm'
        ln = P.lanes[lid]; hp = [P.ports[q] for q in ln['ports']]
        m = lambda n: 'NE_' + n[3:] if n.startswith('NW_') else n
        newports = []
        for x in hp:
            y = copy.deepcopy(x); y['id'] = x['id'].replace(lid + '_', mid + '_', 1)
            y['src'] = dict(part=m(x['src']['part']), bus=x['src']['bus']); y['dst'] = dict(part=m(x['dst']['part']), bus=x['dst']['bus'])
            if x['face'] in 'NS':
                lo, hi = sorted(x['window_um']); y['window_um'] = [round(W - hi, 4), round(W - lo, 4)]
                if 'order' in y: y['order'] = flipo[y['order']]
            else:
                y['face'] = LA.OPP[x['face']]
            newports.append(y)
        rawp = {p['id']: p for p in raw['ports']}
        for x, y in zip(hp, newports):
            keep = set(rawp[x['id']].keys())
            raw['ports'].append({k: v for k, v in y.items() if k in keep})
        raw['lanes'].append(dict(id=mid, ports=[p['id'] for p in newports], note=f"DIE-HBM-42 d41v mirror of {lid}"))
        P2 = S.Plan(raw)
        # type buses / slots of the NE parts
        for i, x in enumerate(hp):
            pass
        for part_nw in [hp[0]['src']['part']] + [x['dst']['part'] for x in hp]:
            pne = m(part_nw); tnw, tne = P2.parts[part_nw]['type'], P2.parts[pne]['type']
            tw, te = raw['partition_types'][tnw], raw['partition_types'][tne]
            names = [bb['name'] for bb in tw.get('buses', []) if bb['name'].startswith(lid + '_')]
            snames = [s['name'] for s in tw.get('ft_slots', []) if s['name'].startswith(lid + 'x')]
            if tnw == tne:
                # shared type: the NE port windows must map onto the very same type-frame bus / slot windows
                for p in newports:
                    for end, df in (('src', p['face']), ('dst', LA.OPP[p['face']])):
                        if p[end]['part'] != pne: continue
                        tf, twin, flip = LA.to_type_window(P2, pne, df, p['window_um'])
                        bn = p[end]['bus']
                        bb = next((q for q in tw.get('buses', []) if q['name'] == bn), None)
                        if bb is not None:
                            assert bb['face'] == tf and all(abs(u - v) < 1e-3 for u, v in zip(bb['window_um'], twin)), (bn, bb['face'], bb['window_um'], tf, twin)
                        else:
                            sn, io = bn.rsplit('_', 1)
                            sl = next(q for q in tw['ft_slots'] if q['name'] == sn)
                            k = 'in' if io == 'i' else 'out'
                            assert sl[k + '_face'] == tf and all(abs(u - v) < 1e-3 for u, v in zip(sl[k + '_window_um'], twin)), (bn, sl[k + '_face'], sl[k + '_window_um'], tf, twin)
                rep['ne'].append(dict(lane=mid, part=pne, type=tne, shared_reuse=names + snames, frame_identity='asserted')); continue
            for bn in names:
                bb = next(q for q in tw['buses'] if q['name'] == bn)
                # die-frame window of the NE port that uses this bus
                pr = next(p for p in newports if (p['src']['part'] == pne and p['src']['bus'] == bn) or (p['dst']['part'] == pne and p['dst']['bus'] == bn))
                df = pr['face'] if pr['src']['part'] == pne else LA.OPP[pr['face']]
                tf, twin, flip = LA.to_type_window(P2, pne, df, pr['window_um'])
                nb = copy.deepcopy(bb); nb.update(face=tf, window_um=twin)   # order: NE is the exact MY image of NW -> NW type-frame order kept
                assert not any(q['name'] == bn for q in te.get('buses', []))
                te.setdefault('buses', []).append(nb)
                rep['ne'].append(dict(lane=mid, part=pne, type=tne, bus=bn, face=tf, window=twin))
            for sn in snames:
                s = next(q for q in tw['ft_slots'] if q['name'] == sn)
                pin = next(p for p in newports if p['dst']['part'] == pne and p['dst']['bus'] == sn + '_i')
                pout = next(p for p in newports if p['src']['part'] == pne and p['src']['bus'] == sn + '_o')
                tfi, twi, fi = LA.to_type_window(P2, pne, LA.OPP[pin['face']], pin['window_um'])
                tfo, two, fo = LA.to_type_window(P2, pne, pout['face'], pout['window_um'])
                ns = copy.deepcopy(s)
                ns.update(in_face=tfi, in_window_um=twi, out_face=tfo, out_window_um=two)   # NW type-frame orders kept
                if s.get('regs_um'):
                    regs = []
                    for r in s['regs_um']:
                        dx, dy = P2.to_die(part_nw, tuple(r)); regs.append([round(v, 4) for v in P2.to_type(pne, (W - dx, dy))])
                    ns['regs_um'] = regs
                assert not s.get('bit_sites_um')
                assert not any(q['name'] == sn for q in te.get('ft_slots', []))
                te.setdefault('ft_slots', []).append(ns)
                rep['ne'].append(dict(lane=mid, part=pne, type=tne, slot=sn))
        P3 = S.Plan(raw)
        nat = P3.lane_natural(mid)
        ent_nw = raw['latency']['lanes'][lid]
        assert nat['cycles'] == ent_nw['natural'], (mid, nat['cycles'], ent_nw['natural'])
        raw['latency']['lanes'][mid] = dict(nat, natural=nat['cycles'], pad=ent_nw['pad'], cycles=ent_nw['cycles'],
                                            param='LAT_' + mid.upper())
        rep['ne'].append(dict(lane=mid, cycles=nat['cycles'], nw_cycles=raw['latency']['lanes'][lid]['cycles']))
    # one word over k split lanes keeps ONE latency: R8 latency group (plan convention, e.g. SOUTHERN_VMS_*), NW + NE
    grp = {}
    for bb in B.report['built']:
        if bb.get('split', 1) > 1 and bb.get('padded_to'):
            grp.setdefault((bb['src'], bb['dst']), []).append(bb['lane'])
    for (s_, d_), lids in grp.items():
        for side, ls in (('NW', lids), ('NE', [l + 'm' for l in lids])):
            raw.setdefault('latency_groups', []).append(dict(
                name=f"EP_FLIT_{s_.replace('NW_', side + '_')}_TO_{d_.replace('NW_', side + '_')}", kind='bus', lanes=ls,
                source='DIE-HBM-42 d41v va_build split', note='one as-built bus split over parallel hop-chain lanes; '
                'the shorter lane is padded to the group cycles (R8)'))
    raw['die']['label'] = 'DIE-HBM-42 d41v V-A SFU/IDX hop chains | ' + raw['die'].get('label', '')
    out.mkdir(parents=True, exist_ok=False)
    for f in plan.iterdir():
        if f.name == 'die_plan.json': continue
        shutil.copy2(f, out / f.name) if f.is_file() else os.symlink(f.resolve(), out / f.name)
    (out / 'die_plan.json').write_text(json.dumps(raw, indent=1))
    rep['out_sha'] = sha12(out / 'die_plan.json')
    (out / 'd41v_va_report.json').write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(dict(built=[(b['lane'], b['bits'], b['cycles'], b.get('padded_to'), b['chain'], b['crossings']) for b in B.report['built']],
                          failed=B.report['failed'], ne=rep['ne'], sha=rep['out_sha']), indent=0, default=str)[:6000])

if __name__ == '__main__':
    main()
