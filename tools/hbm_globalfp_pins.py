#!/usr/bin/env python3
"""GLOBAL-FP-H: publish die-level pin positions and the block <-> operator mapping for one floorplan candidate.

Pins (top-down pin assignment input for the HBM die lead): every graph link gets one pin segment on each end block,
on the face nearest its peer (the closest-outline point of the scored candidate), centred there, of length
bits / PIN_DENSITY; segments on one face are packed in 1-D (sorted by wanted centre, pushed apart, clamped to the
face, then re-centred) so they never overlap.  Face utilisation = sum(pin length) / face length (> 1.0 = the face
cannot carry its links at this density: re-shape or move the block).  Coordinates are die-absolute (um, lower-left
origin) and block-local (offset along the face from the block's lower-left corner, R0).

Operator map: every (unit, op) of the compiled HGI-1 programs (Qwen3-8B TP4 P8191, DS-V4.1 TP96 1M) -> the die
blocks that execute or serve it in this candidate's graph (attention-on-SM aware), with record counts per token.

  python3 tools/hbm_globalfp_pins.py --graph G.json --placement P.json --qwen-prog Q.json --ds-prog D.json --out DIR --tag T
"""
import argparse, collections, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_globalfp as F

PIN_DENSITY = 10.0      # pins per um of face: one signal layer pair at 2x minimum pitch (M4/M6 or M5/M7), 50% left for PG/OBS


def face_of(r, p, peer):
    x0, y0, x1, y1 = r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']
    d = {'W': abs(p[0] - x0), 'E': abs(p[0] - x1), 'S': abs(p[1] - y0), 'N': abs(p[1] - y1)}
    best = min(d.values())
    cands = [f for f, v in d.items() if v <= best + 1e-6]
    if len(cands) > 1 or best > 1e-3:       # interior / corner / abutting midpoint: face toward the peer centre
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = peer[0] - cx, peer[1] - cy
        cands = [('E' if dx > 0 else 'W') if abs(dx) / max(r['w'], 1) >= abs(dy) / max(r['h'], 1) else ('N' if dy > 0 else 'S')]
    return cands[0]


def pins(G, P, m):
    per_face = collections.defaultdict(list)
    for l, d, ps, pt in m['_per']:
        for end, pp, other, peer in (('src', ps, 'dst', pt), ('dst', pt, 'src', ps)):
            b = l[end]; r = P[b]
            o = P[l[other]]
            pc = (o['x'] + o['w'] / 2, o['y'] + o['h'] / 2)
            f = face_of(r, pp, pc if d == 0 else peer)
            along = (pp[1] - r['y']) if f in ('W', 'E') else (pp[0] - r['x'])
            flen = r['h'] if f in ('W', 'E') else r['w']
            per_face[(b, f)].append(dict(link=l['id'], cls=l['cls'], peer=l[other], dir='out' if end == 'src' else 'in', bits=l['bits'],
                                         want=min(max(along, 0.0), flen), length=l['bits'] / PIN_DENSITY))
    out = {}
    faces = []
    for (b, f), L in per_face.items():
        r = P[b]
        flen = r['h'] if f in ('W', 'E') else r['w']
        tot = sum(p['length'] for p in L)
        L.sort(key=lambda p: p['want'])
        pos = []
        cur = 0.0
        for p in L:                                   # forward pass: no overlap
            lo = max(cur, p['want'] - p['length'] / 2)
            pos.append(lo); cur = lo + p['length']
        over = cur - flen
        if over > 0:                                  # shift back into the face (or spread evenly if it cannot fit)
            if tot <= flen:
                cur = flen
                for k in range(len(L) - 1, -1, -1):
                    pos[k] = min(pos[k], cur - L[k]['length']); cur = pos[k]
            else:
                sc = flen / tot; cur = 0.0
                for k in range(len(L)):
                    pos[k] = cur; cur += L[k]['length'] * sc
        for k, p in enumerate(L):
            ln = min(p['length'], flen) if tot <= flen else p['length'] * flen / tot
            c = pos[k] + ln / 2
            if f in ('W', 'E'):
                x = r['x'] if f == 'W' else r['x'] + r['w']; y = r['y'] + c
            else:
                y = r['y'] if f == 'S' else r['y'] + r['h']; x = r['x'] + c
            p.update(offset_um=round(pos[k], 2), span_um=round(ln, 2), x=round(x, 1), y=round(y, 1))
            p.pop('want'); p.pop('length')
        out.setdefault(b, {})[f] = dict(face_len_um=round(flen, 1), bits=sum(p['bits'] for p in L), utilisation=round(tot / flen, 3), pins=L)
        faces.append((b, f, round(tot / flen, 3), sum(p['bits'] for p in L)))
    faces.sort(key=lambda t: -t[2])
    return out, faces


def op_map(G, progs):
    N = G['nodes']
    sm_att = (G.get('attention') or {}).get('mode') == 'sm'
    ids = lambda *pre: sorted(i for i in N if i.startswith(pre))
    M = {
        ('SM', 'MATVEC'): (ids('sm_', 'pc_', 'phy_') + ids('vmb_'), 'SM matvec: W streamed PHY -> PC -> own SM; x from the quadrant VM banks'),
        ('SU', 'VOP'): (ids('su_', 'vmb_'), 'SU vector ops on the quadrant VM through the LG near taps'),
        ('FUSED', 'ROW_NORM'): (ids('su_', 'vmb_'), 'fused row norm on SU'),
        ('FUSED', 'HC_PRE_NORM'): (ids('su_', 'hc_', 'vmb_'), 'HC pre-norm (SU + HC tap)'),
        ('FUSED', 'HC_POST'): (ids('su_', 'hc_', 'vmb_'), 'HC post (SU + HC tap)'),
        ('FUSED', 'QDQ_FP8'): (ids('quant_', 'vmb_NW'), 'QUANT host on NW RG4/WG2'),
        ('SFU', 'GLU'): (ids('sfu_', 'vmb_'), 'SFU GLU on LG1'),
        ('HC', 'HC_MIX'): (ids('hc_', 'vmb_'), 'HC mix: LG tap clients + HC arithmetic engine'),
        ('IDX', 'INDEX'): (ids('idx_', 'vmb_SW'), 'IDX scheduled static on SW RG4'),
        ('IDX', 'TOPK'): (ids('idx_', 'coll_SW'), 'IDX top-k -> SW COLL delivery'),
        ('DMA', 'LOAD'): (ids('pc_', 'phy_', 'vmh_', 'vmb_'), 'HBM -> VM delivery'),
        ('DMA', 'STORE'): (ids('vmh_', 'pc_', 'phy_'), 'VM -> HBM writeback (DMA back)'),
        ('DMA', 'KVWB_DS'): (ids('vmh_', 'pc_', 'phy_'), 'KV writeback' + (' to all four stacks (stack-local KV replica)' if sm_att else '')),
        ('DMA', 'FENCE'): ([], 'ordering only'),
        ('ARGMAX', 'LOCAL'): (ids('su_', 'vmb_'), 'ARGMAX client on the VM (SU-side; own client per H-DIE ARGMAX join)'),
        ('CTL', 'LOOP'): ([], 'control'), ('CTL', 'ENDLOOP'): ([], 'control'), ('CTL', 'END'): ([], 'control'), ('CTL', 'NOP'): ([], 'control'),
    }
    for op in ('ALL_REDUCE_SUM', 'ALL_GATHER', 'ARGMAX_MERGE', 'GROUP_REDUCE_MCAST', 'ROW_GATHER', 'TOPK_MERGE'):
        M[('COLL', op)] = (ids('coll_', 'ep_', 'lk_', 'vmh_', 'vmb_'), 'quadrant COLL engines + 2x2 ring + SerDes endpoints')
    if sm_att:
        M[('ATT', 'QK')] = (ids('sm_', 'pc_', 'phy_', 'vmb_', 'vmh_'), 'attention on SM: SM.MATVEC QK mode, KV rows from own-stack PCs, q on x-load, scores to VM, KV descriptors from the hub')
        M[('ATT', 'PV')] = (ids('sm_', 'pc_', 'phy_', 'vmb_', 'su_'), 'attention on SM: SM.ACC PV mode (P on x-load), PV partials reduced by SU; softmax on SU.VOP')
    else:
        M[('ATT', 'QK')] = (ids('att_', 'pc_', 'vmb_NE'), 'dedicated ATT tiles')
        M[('ATT', 'PV')] = (ids('att_', 'vmb_NE'), 'dedicated ATT tiles')
    cnt = {}
    for wl, path, loop_n in progs:
        R = json.load(open(path))['records_listing']
        inloop = False
        for r in R:
            if r['op'] == 'LOOP':
                inloop = True
            if r['op'] == 'ENDLOOP':
                inloop = False
            k = (r['unit'], r['op'])
            cnt.setdefault(k, {'qwen': 0, 'ds': 0})[wl] += loop_n if inloop and r['op'] not in ('LOOP',) else 1
    out = {}
    for k in sorted(set(cnt) | set(M)):
        blocks, note = M.get(k, ([], 'UNMAPPED'))
        kinds = sorted(set(N[b]['kind'] for b in blocks))
        out['.'.join(k)] = dict(records_per_token=cnt.get(k, {'qwen': 0, 'ds': 0}), kinds=kinds, blocks=blocks, note=note)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', required=True); ap.add_argument('--placement', required=True); ap.add_argument('--ref', required=True)
    ap.add_argument('--qwen-prog', required=True); ap.add_argument('--ds-prog', required=True)
    ap.add_argument('--die-h', type=float, default=None)
    ap.add_argument('--out', required=True); ap.add_argument('--tag', required=True)
    a = ap.parse_args()
    if a.die_h:
        F.set_die(a.die_h)
    G = json.load(open(a.graph)); P = json.load(open(a.placement)); ref = json.load(open(a.ref))
    m = F.score(G, P, ref)
    pp, faces = pins(G, P, m)
    om = op_map(G, [('qwen', a.qwen_prog, 36), ('ds', a.ds_prog, 1)])
    os.makedirs(a.out, exist_ok=True)
    doc = dict(schema='opentallas.hbm_globalfp.pins.v1', candidate=a.tag, die_outline_um=[F.W_DIE, F.H_DIE], pin_density_per_um=PIN_DENSITY,
               rule='one pin segment per link end on the face nearest its peer, centred at the closest-outline point, 1-D packed',
               blocks={b: dict(x=round(P[b]['x'], 1), y=round(P[b]['y'], 1), w=G['nodes'][b]['w'], h=G['nodes'][b]['h'], kind=G['nodes'][b]['kind'],
                               orient=P[b].get('orient', 'R0'), faces=pp.get(b, {})) for b in G['nodes']},
               faces_over_1=[dict(block=b, face=f, utilisation=u, bits=bits) for b, f, u, bits in faces if u > 1.0],
               worst_faces=[dict(block=b, face=f, utilisation=u, bits=bits) for b, f, u, bits in faces[:20]])
    json.dump(doc, open(os.path.join(a.out, f'{a.tag}.pins.json'), 'w'), indent=1)
    with open(os.path.join(a.out, f'{a.tag}.pins.tsv'), 'w') as f:
        f.write('block\tface\toffset_um\tspan_um\tx_um\ty_um\tbits\tdir\tclass\tpeer\tlink\n')
        for b, fs in sorted(pp.items()):
            for fc, d in sorted(fs.items()):
                for p in d['pins']:
                    f.write(f"{b}\t{fc}\t{p['offset_um']}\t{p['span_um']}\t{p['x']}\t{p['y']}\t{p['bits']}\t{p['dir']}\t{p['cls']}\t{p['peer']}\t{p['link']}\n")
    json.dump(dict(schema='opentallas.hbm_globalfp.op_map.v1', candidate=a.tag, attention=G.get('attention'), ops=om),
              open(os.path.join(a.out, f'{a.tag}.op_map.json'), 'w'), indent=1)
    print(a.tag, 'faces', len(faces), 'over 1.0:', len(doc['faces_over_1']), 'worst', faces[:3], 'unmapped ops',
          [k for k, v in om.items() if v['note'] == 'UNMAPPED'])


if __name__ == '__main__':
    main()
